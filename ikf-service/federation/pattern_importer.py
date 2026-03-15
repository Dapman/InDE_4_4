"""
Pattern Importer - Inbound Pattern Reception Pipeline

Every pattern from the IKF passes through this pipeline before
reaching the coaching engine. Patterns are guilty until proven innocent.

Pipeline stages:
1. RECEIVE  -> Raw pattern from IKF push or sync/pull
2. VALIDATE -> Schema validation, required fields, confidence minimum
3. STAGE    -> Store in ikf_federation_patterns with status STAGED
4. DEDUP    -> SHA256 content hash check for duplicates
5. INTEGRATE -> Move to INTEGRATED status, available to coaching engine

v3.6.0: Added biomimicry_pattern type for importing nature-inspired
        innovation patterns from the federation.

Rejected patterns are logged with reasons but never reach coaching.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("inde.ikf.pattern_importer")

# Minimum requirements for pattern acceptance
MIN_CONFIDENCE_SCORE = 0.5
MAX_PATTERN_PAYLOAD_BYTES = 1_000_000  # 1MB max per pattern
REQUIRED_FIELDS = ["pattern_id", "type", "content", "confidence"]
VALID_PATTERN_TYPES = [
    "success_pattern",
    "failure_pattern",
    "predictive_pattern",
    "process_pattern",
    "domain_bridge",
    # v3.6.0: Biomimicry pattern types
    "biomimicry_pattern",
    "biomimicry_application",
]


class PatternImporter:
    """
    Validates, deduplicates, stages, and integrates inbound IKF patterns.

    The PatternImporter is the gatekeeper - nothing reaches the coaching
    engine without clearing it.
    """

    def __init__(self, db, config, event_publisher):
        """
        Initialize the PatternImporter.

        Args:
            db: MongoDB database instance
            config: Configuration object
            event_publisher: Event publisher for notifications
        """
        self._db = db
        self._config = config
        self._publisher = event_publisher

        # Get max cache size from config or environment
        import os
        self._max_cache_size = getattr(
            config, 'IKF_MAX_PATTERN_CACHE_SIZE',
            int(os.environ.get('IKF_MAX_PATTERN_CACHE_SIZE', '1000'))
        )

    async def import_patterns(self, patterns: list, source: str = "IKF_PUSH") -> dict:
        """
        Process a batch of inbound patterns through the import pipeline.

        Args:
            patterns: List of pattern dicts from IKF
            source: "IKF_PUSH" (server-initiated) or "IKF_PULL" (client-initiated sync)

        Returns:
            {accepted: int, rejected: int, deduplicated: int, errors: list}
        """
        results = {"accepted": 0, "rejected": 0, "deduplicated": 0, "errors": []}

        for pattern in patterns:
            try:
                result = await self._import_one(pattern, source)
                results[result] += 1
            except Exception as e:
                results["errors"].append({
                    "pattern_id": pattern.get("pattern_id", "unknown"),
                    "error": str(e)
                })
                logger.warning(f"Pattern import error: {e}")

        if results["accepted"] > 0:
            try:
                await self._publisher.publish_ikf_event("pattern.batch_imported", {
                    "source": source,
                    "accepted": results["accepted"],
                    "rejected": results["rejected"],
                    "deduplicated": results["deduplicated"]
                })
            except Exception as e:
                logger.warning(f"Failed to publish batch_imported event: {e}")

        logger.info(
            f"Pattern import: {results['accepted']} accepted, "
            f"{results['rejected']} rejected, {results['deduplicated']} deduplicated"
        )
        return results

    async def _import_one(self, pattern: dict, source: str) -> str:
        """Import a single pattern. Returns 'accepted', 'rejected', or 'deduplicated'."""

        # Stage 1: VALIDATE
        validation = self._validate(pattern)
        if not validation["valid"]:
            self._log_rejection(pattern, validation["reason"])
            return "rejected"

        # Stage 2: DEDUP - check content hash
        content_hash = self._compute_hash(pattern)
        existing = self._db.ikf_federation_patterns.find_one(
            {"content_hash": content_hash}
        )
        if existing:
            # Update version if newer
            existing_version = existing.get("version", 0)
            incoming_version = pattern.get("version", 1)
            if incoming_version > existing_version:
                self._db.ikf_federation_patterns.update_one(
                    {"content_hash": content_hash},
                    {"$set": {
                        "version": incoming_version,
                        "updated_at": datetime.now(timezone.utc),
                        "content": pattern.get("content"),
                        "confidence": pattern.get("confidence")
                    }}
                )
                logger.info(
                    f"Pattern {pattern.get('pattern_id')} updated "
                    f"(v{existing_version} -> v{incoming_version})"
                )
            return "deduplicated"

        # Stage 3: STAGE - store with STAGED status
        federation_pattern = {
            "pattern_id": pattern["pattern_id"],
            "ikf_pattern_id": pattern.get("pattern_id"),  # Original IKF ID
            "type": pattern["type"],
            "title": pattern.get("title", "Untitled Pattern"),
            "content": pattern["content"],
            "confidence": pattern["confidence"],
            "applicability": pattern.get("applicability", {}),
            "source": "IKF",
            "source_detail": source,
            "content_hash": content_hash,
            "version": pattern.get("version", 1),
            "status": "STAGED",
            "received_at": datetime.now(timezone.utc),
            "staged_at": datetime.now(timezone.utc),
            "integrated_at": None,
            "feedback": [],
            "application_count": 0,
            "dismissal_count": 0
        }

        # Check cache capacity
        current_count = self._db.ikf_federation_patterns.count_documents({})
        if current_count >= self._max_cache_size:
            self._evict_oldest()

        self._db.ikf_federation_patterns.insert_one(federation_pattern)

        # Stage 4: INTEGRATE - auto-integrate if quality threshold met
        if pattern["confidence"] >= MIN_CONFIDENCE_SCORE:
            self._db.ikf_federation_patterns.update_one(
                {"pattern_id": pattern["pattern_id"]},
                {"$set": {
                    "status": "INTEGRATED",
                    "integrated_at": datetime.now(timezone.utc)
                }}
            )

            try:
                await self._publisher.publish_ikf_event("pattern.integrated", {
                    "pattern_id": pattern["pattern_id"],
                    "type": pattern["type"],
                    "confidence": pattern["confidence"],
                    "source": source
                })
            except Exception as e:
                logger.warning(f"Failed to publish integrated event: {e}")

            return "accepted"
        else:
            # Below threshold - stays STAGED for admin review
            logger.info(
                f"Pattern {pattern['pattern_id']} staged (confidence {pattern['confidence']} "
                f"< threshold {MIN_CONFIDENCE_SCORE})"
            )
            return "accepted"  # Counts as accepted (staged, not rejected)

    def _validate(self, pattern: dict) -> dict:
        """Validate inbound pattern schema and constraints."""
        # Size check
        payload_size = len(json.dumps(pattern).encode())
        if payload_size > MAX_PATTERN_PAYLOAD_BYTES:
            return {"valid": False, "reason": f"Payload too large ({payload_size} bytes)"}

        # Required fields
        missing = [f for f in REQUIRED_FIELDS if f not in pattern]
        if missing:
            return {"valid": False, "reason": f"Missing fields: {missing}"}

        # Type check
        if pattern.get("type") not in VALID_PATTERN_TYPES:
            return {"valid": False, "reason": f"Invalid type: {pattern.get('type')}"}

        # Confidence range
        confidence = pattern.get("confidence", 0)
        if not (0.0 <= confidence <= 1.0):
            return {"valid": False, "reason": f"Invalid confidence: {confidence}"}

        # Content must be dict with at least summary
        content = pattern.get("content", {})
        if not isinstance(content, dict):
            return {"valid": False, "reason": "Content must be a dictionary"}

        return {"valid": True, "reason": None}

    def _compute_hash(self, pattern: dict) -> str:
        """Compute SHA256 hash of pattern content for deduplication."""
        # Hash the content and type - not metadata like timestamps
        hashable = json.dumps({
            "type": pattern.get("type"),
            "content": pattern.get("content")
        }, sort_keys=True)
        return hashlib.sha256(hashable.encode()).hexdigest()

    def _evict_oldest(self):
        """Remove oldest non-applied pattern when cache is full."""
        oldest = self._db.ikf_federation_patterns.find_one(
            {"application_count": 0, "status": "INTEGRATED"},
            sort=[("received_at", 1)]
        )
        if oldest:
            self._db.ikf_federation_patterns.delete_one({"_id": oldest["_id"]})
            logger.info(f"Evicted pattern {oldest.get('pattern_id')} (cache full)")

    def _log_rejection(self, pattern: dict, reason: str):
        """Log rejected patterns for admin visibility."""
        self._db.ikf_pattern_rejections.insert_one({
            "pattern_id": pattern.get("pattern_id", "unknown"),
            "reason": reason,
            "rejected_at": datetime.now(timezone.utc),
            "payload_preview": str(pattern)[:500]  # Truncated for safety
        })
        logger.warning(f"Pattern rejected: {pattern.get('pattern_id')} - {reason}")

    def get_cache_stats(self) -> dict:
        """Return pattern cache statistics."""
        return {
            "total": self._db.ikf_federation_patterns.count_documents({}),
            "staged": self._db.ikf_federation_patterns.count_documents({"status": "STAGED"}),
            "integrated": self._db.ikf_federation_patterns.count_documents({"status": "INTEGRATED"}),
            "max_capacity": self._max_cache_size,
            "rejections": self._db.ikf_pattern_rejections.count_documents({})
        }

    def get_integrated_patterns(
        self,
        pattern_type: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 10
    ) -> List[dict]:
        """
        Retrieve integrated patterns for coaching context.

        Args:
            pattern_type: Filter by pattern type
            industry: Filter by industry applicability
            limit: Maximum patterns to return

        Returns:
            List of integrated patterns
        """
        query = {"status": "INTEGRATED"}

        if pattern_type:
            query["type"] = pattern_type

        if industry:
            query["$or"] = [
                {"applicability.industries": industry},
                {"applicability.industries": "ALL"}
            ]

        patterns = list(self._db.ikf_federation_patterns.find(
            query,
            {"_id": 0, "content_hash": 0}
        ).sort("confidence", -1).limit(limit))

        return patterns

    async def record_feedback(
        self,
        pattern_id: str,
        feedback_type: str,
        pursuit_id: Optional[str] = None
    ):
        """
        Record innovator feedback on an IKF pattern.

        Args:
            pattern_id: The pattern being rated
            feedback_type: "applied" | "explored" | "dismissed"
            pursuit_id: Optional pursuit context
        """
        update = {"$push": {"feedback": {
            "type": feedback_type,
            "pursuit_id": pursuit_id,
            "timestamp": datetime.now(timezone.utc)
        }}}

        if feedback_type == "applied":
            update["$inc"] = {"application_count": 1}
        elif feedback_type == "dismissed":
            update["$inc"] = {"dismissal_count": 1}

        self._db.ikf_federation_patterns.update_one(
            {"pattern_id": pattern_id},
            update
        )

        logger.info(f"Pattern {pattern_id} feedback recorded: {feedback_type}")

    # =========================================================================
    # v3.6.0: Biomimicry Pattern Import
    # =========================================================================

    async def import_biomimicry_patterns(
        self,
        patterns: List[Dict[str, Any]],
        source: str = "IKF_FEDERATION"
    ) -> Dict[str, Any]:
        """
        Import biomimicry patterns from the IKF federation.

        Unlike regular patterns, biomimicry patterns are stored in the
        biomimicry_patterns collection and enriched with TRIZ connections.

        Args:
            patterns: List of biomimicry pattern dicts from IKF
            source: Source identifier

        Returns:
            Import statistics
        """
        results = {
            "accepted": 0,
            "rejected": 0,
            "deduplicated": 0,
            "enriched": 0,
            "errors": []
        }

        for pattern in patterns:
            try:
                result = await self._import_biomimicry_pattern(pattern, source)
                if result == "enriched":
                    results["enriched"] += 1
                    results["accepted"] += 1
                else:
                    results[result] += 1
            except Exception as e:
                results["errors"].append({
                    "pattern_id": pattern.get("pattern_id", "unknown"),
                    "error": str(e)
                })
                logger.warning(f"Biomimicry pattern import error: {e}")

        if results["accepted"] > 0:
            try:
                await self._publisher.publish_ikf_event("biomimicry.patterns_imported", {
                    "source": source,
                    "accepted": results["accepted"],
                    "enriched": results["enriched"],
                    "deduplicated": results["deduplicated"]
                })
            except Exception as e:
                logger.warning(f"Failed to publish biomimicry import event: {e}")

        logger.info(
            f"Biomimicry import: {results['accepted']} accepted, "
            f"{results['enriched']} enriched, {results['deduplicated']} deduplicated"
        )
        return results

    async def _import_biomimicry_pattern(
        self,
        pattern: Dict[str, Any],
        source: str
    ) -> str:
        """
        Import a single biomimicry pattern into the local database.

        Returns: 'accepted', 'rejected', 'deduplicated', or 'enriched'
        """
        # Validate required fields
        required = ["pattern_id", "organism", "category", "strategy_name"]
        missing = [f for f in required if f not in pattern]
        if missing:
            logger.warning(f"Biomimicry pattern missing fields: {missing}")
            return "rejected"

        pattern_id = pattern["pattern_id"]

        # Check for existing pattern
        existing = self._db.biomimicry_patterns.find_one({"pattern_id": pattern_id})

        if existing:
            # Check if federation version has higher acceptance_rate
            existing_rate = existing.get("acceptance_rate", 0)
            incoming_rate = pattern.get("acceptance_rate", 0)

            if incoming_rate > existing_rate:
                # Enrich with federation data
                self._db.biomimicry_patterns.update_one(
                    {"pattern_id": pattern_id},
                    {"$set": {
                        "acceptance_rate": incoming_rate,
                        "match_count": max(
                            existing.get("match_count", 0),
                            pattern.get("match_count", 0)
                        ),
                        "federation_synced_at": datetime.now(timezone.utc),
                        "federation_source": source
                    }}
                )
                return "enriched"
            return "deduplicated"

        # New pattern - insert with federation source
        now = datetime.now(timezone.utc)
        new_pattern = {
            "pattern_id": pattern_id,
            "organism": pattern["organism"],
            "category": pattern["category"],
            "strategy_name": pattern["strategy_name"],
            "description": pattern.get("description", ""),
            "mechanism": pattern.get("mechanism", ""),
            "functions": pattern.get("functions", []),
            "applicable_domains": pattern.get("applicable_domains", []),
            "known_applications": pattern.get("known_applications", []),
            "innovation_principles": pattern.get("innovation_principles", []),
            "triz_connections": pattern.get("triz_connections", []),
            "source": "ikf_federation",
            "federation_source": source,
            "confidence": pattern.get("confidence", 0.6),
            "acceptance_rate": pattern.get("acceptance_rate", 0.0),
            "match_count": pattern.get("match_count", 0),
            "feedback_scores": [],
            "created_at": now,
            "federation_synced_at": now
        }

        self._db.biomimicry_patterns.insert_one(new_pattern)
        logger.info(f"Imported biomimicry pattern: {pattern_id} ({pattern['organism']})")
        return "accepted"

    async def _enrich_biomimicry_database(
        self,
        federation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich local biomimicry database with federation intelligence.

        This is called when receiving biomimicry_application contributions
        from the federation. It updates:
        1. Pattern effectiveness scores based on cross-org outcomes
        2. Domain applicability from successful applications
        3. TRIZ connections discovered by other organizations

        Args:
            federation_data: Biomimicry application data from federation

        Returns:
            Enrichment results
        """
        results = {
            "patterns_updated": 0,
            "domains_added": 0,
            "triz_added": 0
        }

        applications = federation_data.get("biomimicry_applications", [])

        for app in applications:
            pattern_id = app.get("pattern_id")
            if not pattern_id:
                continue

            pattern = self._db.biomimicry_patterns.find_one({"pattern_id": pattern_id})
            if not pattern:
                continue

            updates = {}

            # Update acceptance rate with federation signal
            if app.get("feedback_rating"):
                rating = app["feedback_rating"]
                existing_scores = pattern.get("feedback_scores", [])
                # Weight federation feedback slightly lower (0.8x)
                weighted_rating = rating * 0.8
                updates["$push"] = {"feedback_scores": weighted_rating}

            # Add new domain if not present
            app_domain = federation_data.get("domain")
            if app_domain:
                existing_domains = set(pattern.get("applicable_domains", []))
                if app_domain not in existing_domains:
                    if "$addToSet" not in updates:
                        updates["$addToSet"] = {}
                    updates["$addToSet"]["applicable_domains"] = app_domain
                    results["domains_added"] += 1

            # Add new TRIZ connections if discovered
            new_triz = app.get("triz_connections", [])
            if new_triz:
                existing_triz = set(pattern.get("triz_connections", []))
                for triz in new_triz:
                    if triz not in existing_triz:
                        if "$addToSet" not in updates:
                            updates["$addToSet"] = {}
                        if "triz_connections" not in updates["$addToSet"]:
                            updates["$addToSet"]["triz_connections"] = {"$each": []}
                        updates["$addToSet"]["triz_connections"]["$each"].append(triz)
                        results["triz_added"] += 1

            if updates:
                updates["$set"] = {"federation_enriched_at": datetime.now(timezone.utc)}
                self._db.biomimicry_patterns.update_one(
                    {"pattern_id": pattern_id},
                    updates
                )
                results["patterns_updated"] += 1

        logger.info(
            f"Biomimicry enrichment: {results['patterns_updated']} patterns updated, "
            f"{results['domains_added']} domains added, {results['triz_added']} TRIZ added"
        )
        return results

    def get_biomimicry_federation_stats(self) -> Dict[str, Any]:
        """Get statistics about federated biomimicry patterns."""
        total = self._db.biomimicry_patterns.count_documents({})
        federated = self._db.biomimicry_patterns.count_documents({
            "source": "ikf_federation"
        })
        enriched = self._db.biomimicry_patterns.count_documents({
            "federation_enriched_at": {"$exists": True}
        })

        return {
            "total_patterns": total,
            "federated_patterns": federated,
            "locally_enriched": enriched,
            "curated_patterns": total - federated
        }
