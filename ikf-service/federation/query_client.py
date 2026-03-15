"""
InDE v3.2 - Federation Query Client
Queries the IKF federation for patterns and benchmarks.

Query Types:
- Pattern search: Find similar patterns by context
- Benchmark lookup: Get temporal benchmarks for phases
- Risk indicators: Get aggregated risk intelligence
- Effectiveness: Get intervention effectiveness data
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger("inde.ikf.query")


class FederationQueryClient:
    """
    Client for querying the IKF federation.

    Features:
    - Context-aware pattern search
    - Benchmark aggregation
    - Local caching for performance
    - Graceful fallback when offline
    """

    def __init__(self, db, federation_node, cache_ttl_hours: int = 24):
        """
        Initialize query client.

        Args:
            db: MongoDB database instance
            federation_node: LocalFederationNode instance
            cache_ttl_hours: How long to cache federation responses
        """
        self._db = db
        self._node = federation_node
        self._cache_ttl = timedelta(hours=cache_ttl_hours)

    async def search_patterns(
        self,
        context: Dict[str, Any],
        package_type: str = "pattern_contribution",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search federation for similar patterns.

        Args:
            context: Search context (industry, methodology, phase, etc.)
            package_type: Type of patterns to search
            limit: Maximum results

        Returns:
            Search results with matching patterns
        """
        # Check cache first
        cache_key = self._build_cache_key("patterns", context, package_type)
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f"Returning cached pattern results for {cache_key}")
            return cached

        # If offline, search local patterns only
        if not self._node.is_connected:
            return await self._search_local_patterns(context, package_type, limit)

        # Query federation
        try:
            client = self._node._http_client
            if not client:
                return await self._search_local_patterns(context, package_type, limit)

            response = await client.post("/patterns/search", json={
                "node_id": self._node.node_id,
                "context": context,
                "package_type": package_type,
                "limit": limit
            })

            if response.status_code == 200:
                result = response.json()
                self._cache_result(cache_key, result)
                return result
            else:
                logger.warning(f"Federation search failed: {response.status_code}")
                return await self._search_local_patterns(context, package_type, limit)

        except Exception as e:
            logger.error(f"Federation query error: {e}")
            return await self._search_local_patterns(context, package_type, limit)

    async def get_benchmarks(
        self,
        methodology: str,
        phase: str,
        industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get temporal benchmarks for a phase.

        Args:
            methodology: Innovation methodology
            phase: Phase to get benchmarks for
            industry: Optional industry filter

        Returns:
            Benchmark data (p25, p50, p75 durations, sample size)
        """
        context = {
            "methodology": methodology,
            "phase": phase
        }
        if industry:
            context["industry"] = industry

        cache_key = self._build_cache_key("benchmarks", context)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        if not self._node.is_connected:
            return self._get_local_benchmarks(methodology, phase, industry)

        try:
            client = self._node._http_client
            if not client:
                return self._get_local_benchmarks(methodology, phase, industry)

            response = await client.get("/benchmarks", params={
                "methodology": methodology,
                "phase": phase,
                "industry": industry
            })

            if response.status_code == 200:
                result = response.json()
                self._cache_result(cache_key, result)
                return result
            else:
                return self._get_local_benchmarks(methodology, phase, industry)

        except Exception as e:
            logger.error(f"Benchmark query error: {e}")
            return self._get_local_benchmarks(methodology, phase, industry)

    async def get_risk_indicators(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get aggregated risk indicators from federation.

        Args:
            context: Context for risk lookup (phase, industry, etc.)

        Returns:
            Risk indicators with aggregated patterns
        """
        cache_key = self._build_cache_key("risks", context)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        if not self._node.is_connected:
            return self._get_local_risk_indicators(context)

        try:
            client = self._node._http_client
            if not client:
                return self._get_local_risk_indicators(context)

            response = await client.post("/risks/indicators", json={
                "node_id": self._node.node_id,
                "context": context
            })

            if response.status_code == 200:
                result = response.json()
                self._cache_result(cache_key, result)
                return result
            else:
                return self._get_local_risk_indicators(context)

        except Exception as e:
            logger.error(f"Risk indicator query error: {e}")
            return self._get_local_risk_indicators(context)

    async def get_effectiveness_data(
        self,
        intervention_type: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Get intervention effectiveness data.

        Args:
            intervention_type: Type of intervention (question, challenge, etc.)
            context: Optional context filter

        Returns:
            Effectiveness statistics
        """
        cache_key = self._build_cache_key("effectiveness", {
            "type": intervention_type,
            **(context or {})
        })
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # For now, use local data only
        # Federation effectiveness queries can be added later
        return self._get_local_effectiveness(intervention_type, context)

    # === Local Fallback Methods ===

    async def _search_local_patterns(
        self,
        context: Dict,
        package_type: str,
        limit: int
    ) -> Dict[str, Any]:
        """Search patterns in local database."""
        query = {
            "package_type": package_type,
            "status": {"$in": ["IKF_READY", "SUBMITTED"]}
        }

        # Add context filters
        if context.get("methodology"):
            query["generalized_data.preserved_context.methodology"] = context["methodology"]
        if context.get("industry"):
            query["generalized_data.preserved_context.industry_naics"] = {
                "$regex": f"^{context['industry'][:2]}"  # Match first 2 digits of NAICS
            }

        patterns = list(
            self._db.ikf_contributions.find(query)
            .sort("confidence", -1)
            .limit(limit)
        )

        # Extract pattern data
        results = []
        for p in patterns:
            extracted = p.get("generalized_data", {}).get("extracted_patterns", [])
            for pattern in extracted:
                results.append({
                    "pattern": pattern,
                    "confidence": p.get("confidence", 0),
                    "source": "local",
                    "contribution_id": p.get("contribution_id")
                })

        return {
            "patterns": results[:limit],
            "source": "local",
            "count": len(results)
        }

    def _get_local_benchmarks(
        self,
        methodology: str,
        phase: str,
        industry: Optional[str]
    ) -> Dict[str, Any]:
        """Get benchmarks from local data."""
        query = {
            "package_type": "temporal_benchmark",
            "status": {"$in": ["IKF_READY", "SUBMITTED"]},
            "generalized_data.preserved_context.methodology": methodology
        }

        benchmarks = list(self._db.ikf_contributions.find(query))

        if not benchmarks:
            return {
                "methodology": methodology,
                "phase": phase,
                "sample_size": 0,
                "message": "No local benchmark data available",
                "source": "local"
            }

        # Aggregate phase durations
        durations = []
        for b in benchmarks:
            phase_data = b.get("generalized_data", {}).get("phase_history", [])
            for ph in phase_data:
                if ph.get("phase") == phase and ph.get("duration_days"):
                    durations.append(ph["duration_days"])

        if not durations:
            return {
                "methodology": methodology,
                "phase": phase,
                "sample_size": 0,
                "message": f"No duration data for phase {phase}",
                "source": "local"
            }

        durations.sort()
        n = len(durations)

        return {
            "methodology": methodology,
            "phase": phase,
            "p25": durations[int(n * 0.25)] if n > 0 else None,
            "p50": durations[int(n * 0.5)] if n > 0 else None,
            "p75": durations[int(n * 0.75)] if n > 0 else None,
            "min": durations[0] if n > 0 else None,
            "max": durations[-1] if n > 0 else None,
            "sample_size": n,
            "source": "local"
        }

    def _get_local_risk_indicators(self, context: Dict) -> Dict[str, Any]:
        """Get risk indicators from local data."""
        query = {
            "package_type": "risk_intelligence",
            "status": {"$in": ["IKF_READY", "SUBMITTED"]}
        }

        if context.get("phase"):
            query["generalized_data.preserved_context.current_phase"] = context["phase"]

        risk_packages = list(self._db.ikf_contributions.find(query))

        if not risk_packages:
            return {
                "indicators": [],
                "sample_size": 0,
                "source": "local"
            }

        # Aggregate fear patterns
        fear_counts = {}
        for pkg in risk_packages:
            patterns = pkg.get("generalized_data", {}).get("extracted_patterns", [])
            for p in patterns:
                if p.get("type") == "fear_pattern":
                    category = p.get("category", "unknown")
                    fear_counts[category] = fear_counts.get(category, 0) + 1

        indicators = [
            {"category": cat, "frequency": count}
            for cat, count in sorted(fear_counts.items(), key=lambda x: -x[1])
        ]

        return {
            "indicators": indicators,
            "sample_size": len(risk_packages),
            "source": "local"
        }

    def _get_local_effectiveness(
        self,
        intervention_type: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Get effectiveness data from local database."""
        query = {
            "package_type": "effectiveness_metrics",
            "status": {"$in": ["IKF_READY", "SUBMITTED"]}
        }

        effectiveness_packages = list(self._db.ikf_contributions.find(query))

        if not effectiveness_packages:
            return {
                "intervention_type": intervention_type,
                "sample_size": 0,
                "source": "local"
            }

        # Aggregate intervention effectiveness
        effective_count = 0
        total_count = 0

        for pkg in effectiveness_packages:
            interventions = pkg.get("generalized_data", {}).get("interventions", [])
            for i in interventions:
                if i.get("type") == intervention_type:
                    total_count += 1
                    if i.get("outcome") == "positive":
                        effective_count += 1

        effectiveness_rate = effective_count / total_count if total_count > 0 else None

        return {
            "intervention_type": intervention_type,
            "effectiveness_rate": effectiveness_rate,
            "effective_count": effective_count,
            "total_count": total_count,
            "sample_size": len(effectiveness_packages),
            "source": "local"
        }

    # === Caching ===

    def _build_cache_key(self, query_type: str, context: Dict, extra: str = "") -> str:
        """Build cache key from query parameters."""
        import hashlib
        import json

        key_data = {
            "type": query_type,
            "context": context,
            "extra": extra
        }
        key_hash = hashlib.sha256(
            json.dumps(key_data, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        return f"ikf_cache:{query_type}:{key_hash}"

    def _get_cached(self, cache_key: str) -> Optional[Dict]:
        """Get cached result if still valid."""
        doc = self._db.ikf_query_cache.find_one({"_id": cache_key})

        if doc:
            cached_at = doc.get("cached_at")
            if cached_at and datetime.now(timezone.utc) - cached_at < self._cache_ttl:
                return doc.get("result")

        return None

    def _cache_result(self, cache_key: str, result: Dict):
        """Cache a query result."""
        self._db.ikf_query_cache.update_one(
            {"_id": cache_key},
            {"$set": {
                "result": result,
                "cached_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    def clear_cache(self):
        """Clear all cached query results."""
        self._db.ikf_query_cache.delete_many({})
        logger.info("IKF query cache cleared")
