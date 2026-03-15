"""
InDE v3.2 - IKF Insights Provider
Provides IKF-powered insights to scaffolding and coaching modules.

Features:
- Phase duration benchmarks for temporal guidance
- Common risk patterns for proactive warnings
- Success patterns for positive reinforcement
- Effectiveness data for intervention selection
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger("inde.ikf.insights")


class IKFInsightsProvider:
    """
    Provides IKF-powered insights to scaffolding modules.

    Used by:
    - MomentDetector: Risk pattern matching
    - HealthMonitor: Benchmark comparisons
    - AdaptiveManager: Intervention effectiveness
    - PredictiveGuidance: Success pattern matching
    """

    def __init__(self, db, ikf_client=None):
        """
        Initialize insights provider.

        Args:
            db: Database instance
            ikf_client: Optional IKFServiceClient instance
        """
        self._db = db
        self._client = ikf_client
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour cache

    async def _get_client(self):
        """Get or create IKF client."""
        if self._client is None:
            from ikf.service_client import IKFServiceClient
            self._client = IKFServiceClient(self._db)
        return self._client

    async def get_phase_benchmarks(
        self,
        methodology: str,
        phase: str,
        industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get benchmark durations for a phase.

        Used by HealthMonitor to compare actual vs expected durations.

        Args:
            methodology: Innovation methodology
            phase: Current phase
            industry: Optional industry filter

        Returns:
            Benchmark data with p25, p50, p75 durations
        """
        cache_key = f"benchmarks:{methodology}:{phase}:{industry}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        client = await self._get_client()
        result = await client.get_benchmarks(methodology, phase, industry)

        self._set_cached(cache_key, result)
        return result

    async def get_common_risks(
        self,
        phase: str,
        methodology: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get common risks for a phase.

        Used by MomentDetector to proactively surface risk warnings.

        Args:
            phase: Current phase
            methodology: Optional methodology filter
            limit: Maximum risks to return

        Returns:
            List of risk indicators with categories and frequencies
        """
        cache_key = f"risks:{phase}:{methodology}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        client = await self._get_client()
        result = await client.get_risk_indicators(phase, methodology)

        risks = result.get("indicators", [])[:limit]
        self._set_cached(cache_key, risks)
        return risks

    async def get_success_patterns(
        self,
        methodology: str,
        phase: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get success patterns for a phase.

        Used by PredictiveGuidance to provide positive reinforcement.

        Args:
            methodology: Innovation methodology
            phase: Current phase
            limit: Maximum patterns to return

        Returns:
            List of success patterns
        """
        cache_key = f"success_patterns:{methodology}:{phase}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        client = await self._get_client()
        result = await client.search_patterns(
            methodology=methodology,
            phase=phase,
            package_type="pattern_contribution",
            limit=limit * 2  # Request more to filter
        )

        # Filter for success patterns
        patterns = [
            p.get("pattern", {})
            for p in result.get("patterns", [])
            if p.get("pattern", {}).get("success_indicator", False)
        ][:limit]

        self._set_cached(cache_key, patterns)
        return patterns

    async def get_warning_patterns(
        self,
        methodology: str,
        phase: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get warning patterns for a phase.

        Used by MomentDetector to surface early warnings.

        Args:
            methodology: Innovation methodology
            phase: Current phase
            limit: Maximum patterns to return

        Returns:
            List of warning patterns
        """
        cache_key = f"warning_patterns:{methodology}:{phase}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        client = await self._get_client()
        result = await client.search_patterns(
            methodology=methodology,
            phase=phase,
            package_type="pattern_contribution",
            limit=limit * 2
        )

        # Filter for warning patterns
        patterns = [
            p.get("pattern", {})
            for p in result.get("patterns", [])
            if not p.get("pattern", {}).get("success_indicator", True)
        ][:limit]

        self._set_cached(cache_key, patterns)
        return patterns

    async def get_intervention_effectiveness(
        self,
        intervention_type: str,
        methodology: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get effectiveness data for an intervention type.

        Used by AdaptiveManager to select optimal interventions.

        Args:
            intervention_type: Type of intervention
            methodology: Optional methodology filter

        Returns:
            Effectiveness rate and sample size
        """
        cache_key = f"effectiveness:{intervention_type}:{methodology}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        client = await self._get_client()
        result = await client.get_effectiveness(intervention_type, methodology)

        self._set_cached(cache_key, result)
        return result

    async def get_phase_guidance(
        self,
        pursuit_id: str,
        methodology: str,
        phase: str,
        industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive phase guidance.

        Combines multiple IKF data sources for rich guidance.

        Args:
            pursuit_id: Current pursuit
            methodology: Innovation methodology
            phase: Current phase
            industry: Optional industry filter

        Returns:
            Comprehensive guidance with benchmarks, risks, and patterns
        """
        # Gather all insights
        benchmarks = await self.get_phase_benchmarks(methodology, phase, industry)
        risks = await self.get_common_risks(phase, methodology)
        success_patterns = await self.get_success_patterns(methodology, phase)
        warning_patterns = await self.get_warning_patterns(methodology, phase)

        # Build guidance
        guidance = {
            "pursuit_id": pursuit_id,
            "phase": phase,
            "methodology": methodology,
            "benchmarks": {
                "typical_duration_days": benchmarks.get("p50"),
                "fast_track_days": benchmarks.get("p25"),
                "extended_duration_days": benchmarks.get("p75"),
                "sample_size": benchmarks.get("sample_size", 0),
                "source": benchmarks.get("source", "unknown")
            },
            "common_risks": [
                {
                    "category": r.get("category"),
                    "frequency": r.get("frequency"),
                    "mitigation_hint": self._get_risk_mitigation(r.get("category"))
                }
                for r in risks
            ],
            "success_indicators": [
                {
                    "pattern": p.get("pattern_text", p.get("description", "")),
                    "category": p.get("category")
                }
                for p in success_patterns
            ],
            "warning_signs": [
                {
                    "pattern": p.get("pattern_text", p.get("description", "")),
                    "category": p.get("category")
                }
                for p in warning_patterns
            ],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        return guidance

    def _get_risk_mitigation(self, category: str) -> str:
        """Get mitigation hint for a risk category."""
        mitigations = {
            "RESOURCE_CONSTRAINT": "Consider phased rollout or MVP approach",
            "MARKET_UNCERTAINTY": "Validate assumptions with customer interviews",
            "TECHNICAL_COMPLEXITY": "Prototype critical components early",
            "STAKEHOLDER_ALIGNMENT": "Schedule alignment workshop",
            "TIMELINE_PRESSURE": "Re-prioritize scope or extend timeline",
            "COMPETITIVE_THREAT": "Accelerate differentiation efforts",
            "REGULATORY_COMPLIANCE": "Engage compliance early in design",
            "TEAM_CAPABILITY": "Identify training or hiring needs"
        }
        return mitigations.get(category, "Review risk mitigation strategies")

    # === Caching ===

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if still valid."""
        if key in self._cache:
            entry = self._cache[key]
            age = (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds()
            if age < self._cache_ttl:
                return entry["value"]
        return None

    def _set_cached(self, key: str, value: Any):
        """Cache a value."""
        self._cache[key] = {
            "value": value,
            "timestamp": datetime.now(timezone.utc)
        }

    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        logger.info("IKF insights cache cleared")

    async def close(self):
        """Close resources."""
        if self._client:
            await self._client.close()
