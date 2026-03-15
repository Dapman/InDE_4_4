"""
InDE v3.6 - IKF Contribution Preparer
Prepares contribution packages by running the generalization pipeline.

Supports:
- Manual preparation via API
- Auto-preparation triggered by events (pursuit.completed, retrospective.completed)
- Rate limiting to prevent contribution fatigue
- v3.6.0: Biomimicry application packages for nature-inspired innovations
"""

import logging
import uuid
import httpx
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from contribution.rate_limiter import ContributionRateLimiter

logger = logging.getLogger("inde.ikf.preparer")

# Package type definitions
PACKAGE_TYPES = {
    "temporal_benchmark": {
        "description": "Phase timing patterns and duration benchmarks",
        "data_source": "phase_history",
    },
    "pattern_contribution": {
        "description": "Success/failure patterns from pursuit lifecycle",
        "data_source": "pursuit",
    },
    "risk_intelligence": {
        "description": "Risk indicators and mitigation patterns",
        "data_source": "fears",
    },
    "effectiveness_metrics": {
        "description": "Coaching intervention effectiveness metrics",
        "data_source": "interventions",
    },
    "retrospective_wisdom": {
        "description": "Retrospective learnings and insights",
        "data_source": "retrospective",
    },
    # v3.6.0: Biomimicry application packages
    "biomimicry_application": {
        "description": "Nature-inspired innovation applications and outcomes",
        "data_source": "biomimicry",
    },
}


class IKFContributionPreparer:
    """
    Prepares IKF contribution packages by running the generalization pipeline.

    Features:
    - Fetches pursuit data from inde-app
    - Runs 4-stage generalization + PII scan
    - Stores package as DRAFT for human review
    - Publishes preparation event
    """

    def __init__(self, db, publisher, llm_client=None):
        """
        Initialize preparer.

        Args:
            db: MongoDB database instance
            publisher: Event publisher for IKF events
            llm_client: Optional httpx client for LLM gateway
        """
        self._db = db
        self._publisher = publisher
        self._llm_client = llm_client or self._create_llm_client()
        self._rate_limiter = ContributionRateLimiter(db)

    def _create_llm_client(self):
        """Create httpx client for LLM gateway."""
        llm_url = os.environ.get("LLM_GATEWAY_URL", "http://inde-llm-gateway:8080")
        try:
            return httpx.AsyncClient(base_url=llm_url, timeout=30.0)
        except Exception as e:
            logger.warning(f"Failed to create LLM client: {e}")
            return None

    async def prepare(
        self,
        pursuit_id: str,
        package_type: str,
        auto_triggered: bool = False,
        trigger_priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Prepare a contribution package.

        Args:
            pursuit_id: Pursuit to create package from
            package_type: Type of package (temporal_benchmark, etc.)
            auto_triggered: Whether this was auto-triggered by an event
            trigger_priority: "high" for pursuit.completed, "normal" otherwise

        Returns:
            Package preparation result
        """
        logger.info(f"Preparing {package_type} package for pursuit {pursuit_id}")

        # Validate package type
        if package_type not in PACKAGE_TYPES:
            return {
                "success": False,
                "error": f"Invalid package type: {package_type}",
                "valid_types": list(PACKAGE_TYPES.keys())
            }

        # Get user_id from pursuit
        pursuit = await self._fetch_pursuit(pursuit_id)
        if not pursuit:
            return {"success": False, "error": "Pursuit not found"}

        user_id = pursuit.get("user_id", "unknown")

        # Check rate limits for auto-triggered packages
        if auto_triggered:
            allowed, reason = self._rate_limiter.can_auto_prepare(
                user_id, package_type, trigger_priority
            )
            if not allowed:
                logger.info(f"Rate limited: {reason}")
                return {"success": False, "error": reason, "rate_limited": True}

        # Extract relevant data based on package type
        raw_data = self._extract_data(pursuit, package_type)
        if not raw_data:
            return {"success": False, "error": "No relevant data to package"}

        # Build context
        context = {
            "pursuit_id": pursuit_id,
            "industry": pursuit.get("industry", ""),
            "methodology": pursuit.get("methodology", "LEAN_STARTUP"),
            "current_phase": pursuit.get("current_phase", ""),
        }

        # Run generalization pipeline
        from generalization.engine import GeneralizationEngine
        engine = GeneralizationEngine(llm_client=self._llm_client, db=self._db)

        try:
            result = await engine.generalize(raw_data, context)
        except Exception as e:
            logger.error(f"Generalization failed: {e}")
            # Fall back to sync version
            result = engine.generalize_sync(raw_data, context)

        # Create contribution package
        contribution_id = str(uuid.uuid4())[:12]
        package = {
            "contribution_id": contribution_id,
            "pursuit_id": pursuit_id,
            "user_id": user_id,
            "package_type": package_type,
            "schema_version": "3.5.0",
            "status": "DRAFT",
            "auto_triggered": auto_triggered,
            "trigger_priority": trigger_priority,
            "original_hash": result.get("original_hash"),
            "original_data": raw_data,
            "original_summary": self._generate_summary(raw_data),
            "generalized_data": result.get("generalized", {}),
            "generalized_summary": self._generate_summary(result.get("generalized", {})),
            "transformations_log": result.get("transformations_log", []),
            "confidence": result.get("confidence", 0.0),
            "pii_scan": result.get("pii_scan", {}),
            "warnings": result.get("warnings", []),
            "created_at": datetime.now(timezone.utc),
        }

        # Store package
        self._db.ikf_contributions.insert_one(package)
        logger.info(f"Created contribution package: {contribution_id}")

        # Publish preparation event
        try:
            await self._publisher.publish_ikf_event("ikf.package.prepared", {
                "contribution_id": contribution_id,
                "pursuit_id": pursuit_id,
                "user_id": user_id,
                "package_type": package_type,
                "auto_triggered": auto_triggered,
                "confidence": result.get("confidence", 0.0),
                "pii_passed": result.get("pii_scan", {}).get("passed", True)
            })
        except Exception as e:
            logger.warning(f"Failed to publish preparation event: {e}")

        return {
            "success": True,
            "contribution_id": contribution_id,
            "package_type": package_type,
            "status": "DRAFT",
            "confidence": result.get("confidence", 0.0),
            "pii_scan": result.get("pii_scan", {}),
            "warnings_count": len(result.get("warnings", []))
        }

    async def _fetch_pursuit(self, pursuit_id: str) -> Optional[Dict]:
        """Fetch pursuit data from inde-app or local cache."""
        # First check local cache
        cached = self._db.pursuit_cache.find_one({"pursuit_id": pursuit_id})
        if cached:
            return cached

        # Fetch from inde-app
        app_url = os.environ.get("INDE_APP_URL", "http://inde-app:8000")
        service_token = os.environ.get("SERVICE_TOKEN", "")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{app_url}/api/pursuits/{pursuit_id}",
                    headers={"X-Service-Token": service_token},
                    timeout=10.0
                )
                if response.status_code == 200:
                    pursuit = response.json()
                    # Cache for future use
                    pursuit["cached_at"] = datetime.now(timezone.utc)
                    self._db.pursuit_cache.update_one(
                        {"pursuit_id": pursuit_id},
                        {"$set": pursuit},
                        upsert=True
                    )
                    return pursuit
        except Exception as e:
            logger.warning(f"Failed to fetch pursuit {pursuit_id}: {e}")

        return None

    def _extract_data(self, pursuit: Dict, package_type: str) -> Optional[Dict]:
        """Extract relevant data from pursuit based on package type."""
        type_config = PACKAGE_TYPES.get(package_type, {})
        data_source = type_config.get("data_source", "pursuit")

        if data_source == "pursuit":
            # Full pursuit data (filtered)
            return {
                "title": pursuit.get("title", ""),
                "problem_context": pursuit.get("problem_context", {}),
                "current_phase": pursuit.get("current_phase", ""),
                "health_zone": pursuit.get("health_zone", ""),
                "fears": pursuit.get("fears", []),
                "stakeholders": len(pursuit.get("stakeholders", [])),
            }

        elif data_source == "phase_history":
            phases = pursuit.get("phase_history", [])
            if not phases:
                return None
            return {
                "phase_history": phases,
                "current_phase": pursuit.get("current_phase", ""),
                "started_at": pursuit.get("started_at"),
            }

        elif data_source == "fears":
            fears = pursuit.get("fears", [])
            if not fears:
                return None
            return {
                "fears": fears,
                "health_zone": pursuit.get("health_zone", ""),
            }

        elif data_source == "retrospective":
            retro = pursuit.get("retrospective", {})
            if not retro:
                return None
            return retro

        elif data_source == "interventions":
            interventions = pursuit.get("interventions", [])
            if not interventions:
                return None
            return {
                "interventions": interventions,
                "health_history": pursuit.get("health_history", []),
            }

        elif data_source == "biomimicry":
            # v3.6.0: Extract biomimicry application data
            return self._extract_biomimicry_data(pursuit)

        return None

    def _generate_summary(self, data: Dict) -> str:
        """Generate a brief summary of the data."""
        if not data:
            return ""

        parts = []

        if "title" in data:
            parts.append(f"Pursuit: {data['title'][:50]}")

        if "current_phase" in data:
            parts.append(f"Phase: {data['current_phase']}")

        if "fears" in data and isinstance(data["fears"], list):
            parts.append(f"Risks: {len(data['fears'])}")

        if "phase_history" in data and isinstance(data["phase_history"], list):
            parts.append(f"Phases: {len(data['phase_history'])}")

        if "extracted_patterns" in data and isinstance(data["extracted_patterns"], list):
            parts.append(f"Patterns: {len(data['extracted_patterns'])}")

        if "biomimicry_applications" in data and isinstance(data["biomimicry_applications"], list):
            parts.append(f"Biomimicry: {len(data['biomimicry_applications'])}")

        return " | ".join(parts)

    def _extract_biomimicry_data(self, pursuit: Dict) -> Optional[Dict]:
        """
        Extract biomimicry application outcomes from completed pursuit.

        v3.6.0: Only creates a package if:
        1. At least one biomimicry insight was ACCEPTED during the pursuit
        2. The pursuit has a documented outcome

        This federates valuable nature-inspired innovation applications
        to help other organizations discover effective biological strategies.

        Args:
            pursuit: The pursuit data

        Returns:
            Biomimicry application data if eligible, None otherwise
        """
        pursuit_id = pursuit.get("pursuit_id") or pursuit.get("_id")
        if not pursuit_id:
            return None

        # Query biomimicry matches for this pursuit
        matches = list(self._db.biomimicry_matches.find({
            "pursuit_id": str(pursuit_id),
            "innovator_response": {"$in": ["accepted", "explored"]}
        }))

        if not matches:
            logger.debug(f"No accepted/explored biomimicry insights for pursuit {pursuit_id}")
            return None

        # Separate accepted (strong signal) from explored (engagement signal)
        accepted_matches = [m for m in matches if m.get("innovator_response") == "accepted"]
        explored_matches = [m for m in matches if m.get("innovator_response") == "explored"]

        # Require at least one accepted insight for federation
        if not accepted_matches:
            logger.debug(f"No accepted biomimicry insights for pursuit {pursuit_id}")
            return None

        # Enrich with pattern details
        applications = []
        for match in accepted_matches:
            pattern = self._db.biomimicry_patterns.find_one({
                "pattern_id": match.get("pattern_id")
            })
            if pattern:
                applications.append({
                    "match_id": match.get("match_id"),
                    "pattern_id": match.get("pattern_id"),
                    "organism": pattern.get("organism"),
                    "strategy_name": pattern.get("strategy_name"),
                    "category": pattern.get("category"),
                    "functions_matched": match.get("matched_functions", []),
                    "match_score": match.get("match_score"),
                    "feedback_rating": match.get("feedback_rating"),
                    "innovation_principles": pattern.get("innovation_principles", []),
                    "triz_connections": pattern.get("triz_connections", []),
                })

        return {
            "pursuit_id": str(pursuit_id),
            "pursuit_outcome": pursuit.get("outcome", pursuit.get("status", "unknown")),
            "domain": pursuit.get("industry") or pursuit.get("domain", ""),
            "methodology": pursuit.get("methodology", ""),
            "biomimicry_applications": applications,
            "explored_patterns": len(explored_matches),
            "accepted_patterns": len(accepted_matches),
            "challenge_context": pursuit.get("challenge_text", "")[:500],
        }
