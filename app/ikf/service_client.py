"""
InDE v3.2 - IKF Service Client
Communicates with the IKF service container for federation operations.

Features:
- Pattern queries from federation
- Benchmark lookups
- Risk indicator aggregation
- Contribution submission tracking
- Local fallback when IKF service unavailable
"""

import logging
import os
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger("inde.ikf.client")


class IKFServiceClient:
    """
    Client for communicating with the IKF service.

    Provides:
    - Federation pattern queries
    - Benchmark lookups
    - Risk indicators
    - Contribution submission status
    - Graceful degradation when offline
    """

    def __init__(self, db=None):
        """
        Initialize IKF service client.

        Args:
            db: Database instance for local fallback
        """
        self._db = db
        self._base_url = os.environ.get("IKF_SERVICE_URL", "http://inde-ikf-service:8080")
        self._timeout = float(os.environ.get("IKF_CLIENT_TIMEOUT", "10.0"))
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Check if IKF service is available."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except Exception:
            return False

    # === Pattern Queries ===

    async def search_patterns(
        self,
        methodology: Optional[str] = None,
        industry: Optional[str] = None,
        phase: Optional[str] = None,
        package_type: str = "pattern_contribution",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search federation for patterns.

        Args:
            methodology: Filter by methodology
            industry: Filter by industry NAICS
            phase: Filter by phase
            package_type: Type of patterns
            limit: Maximum results

        Returns:
            Pattern search results
        """
        try:
            client = await self._get_client()
            response = await client.post("/ikf/federation/patterns/search", json={
                "methodology": methodology,
                "industry": industry,
                "phase": phase,
                "package_type": package_type,
                "limit": limit
            })

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Pattern search failed: {response.status_code}")
                return {"patterns": [], "source": "error", "error": response.text}

        except Exception as e:
            logger.error(f"Pattern search error: {e}")
            return {"patterns": [], "source": "error", "error": str(e)}

    # === Benchmark Queries ===

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
            Benchmark data with percentiles
        """
        try:
            client = await self._get_client()
            response = await client.post("/ikf/federation/benchmarks", json={
                "methodology": methodology,
                "phase": phase,
                "industry": industry
            })

            if response.status_code == 200:
                return response.json()
            else:
                return self._default_benchmarks(methodology, phase)

        except Exception as e:
            logger.error(f"Benchmark query error: {e}")
            return self._default_benchmarks(methodology, phase)

    def _default_benchmarks(self, methodology: str, phase: str) -> Dict[str, Any]:
        """Return default benchmarks when service unavailable."""
        # Default phase durations by methodology (in days)
        defaults = {
            "LEAN_STARTUP": {
                "PROBLEM_DISCOVERY": {"p25": 7, "p50": 14, "p75": 28},
                "SOLUTION_HYPOTHESIS": {"p25": 5, "p50": 10, "p75": 21},
                "MVP_DEVELOPMENT": {"p25": 14, "p50": 30, "p75": 60},
                "VALIDATION": {"p25": 21, "p50": 45, "p75": 90},
                "SCALING": {"p25": 30, "p50": 60, "p75": 120}
            },
            "DESIGN_THINKING": {
                "EMPATHIZE": {"p25": 7, "p50": 14, "p75": 21},
                "DEFINE": {"p25": 3, "p50": 7, "p75": 14},
                "IDEATE": {"p25": 5, "p50": 10, "p75": 21},
                "PROTOTYPE": {"p25": 7, "p50": 14, "p75": 30},
                "TEST": {"p25": 7, "p50": 14, "p75": 28}
            }
        }

        method_defaults = defaults.get(methodology, {})
        phase_defaults = method_defaults.get(phase, {"p25": 14, "p50": 30, "p75": 60})

        return {
            "methodology": methodology,
            "phase": phase,
            "source": "defaults",
            "sample_size": 0,
            **phase_defaults
        }

    # === Risk Indicators ===

    async def get_risk_indicators(
        self,
        phase: Optional[str] = None,
        methodology: Optional[str] = None,
        industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated risk indicators.

        Args:
            phase: Filter by phase
            methodology: Filter by methodology
            industry: Filter by industry

        Returns:
            Risk indicators by category
        """
        try:
            client = await self._get_client()
            response = await client.post("/ikf/federation/risks/indicators", json={
                "phase": phase,
                "methodology": methodology,
                "industry": industry
            })

            if response.status_code == 200:
                return response.json()
            else:
                return {"indicators": [], "source": "error"}

        except Exception as e:
            logger.error(f"Risk indicator query error: {e}")
            return {"indicators": [], "source": "error", "error": str(e)}

    # === Effectiveness Data ===

    async def get_effectiveness(
        self,
        intervention_type: str,
        methodology: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get intervention effectiveness data.

        Args:
            intervention_type: Type of intervention
            methodology: Filter by methodology

        Returns:
            Effectiveness statistics
        """
        try:
            client = await self._get_client()
            params = {}
            if methodology:
                params["methodology"] = methodology

            response = await client.get(
                f"/ikf/federation/effectiveness/{intervention_type}",
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"effectiveness_rate": None, "source": "error"}

        except Exception as e:
            logger.error(f"Effectiveness query error: {e}")
            return {"effectiveness_rate": None, "source": "error", "error": str(e)}

    # === Contribution Management ===

    async def get_contribution_status(self, contribution_id: str) -> Dict[str, Any]:
        """Get status of a contribution including federation status."""
        try:
            client = await self._get_client()
            response = await client.get(f"/ikf/contributions/{contribution_id}")

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "Not found", "status_code": response.status_code}

        except Exception as e:
            logger.error(f"Contribution status error: {e}")
            return {"error": str(e)}

    async def submit_to_federation(self, contribution_ids: List[str]) -> Dict[str, Any]:
        """Submit contributions to federation."""
        try:
            client = await self._get_client()
            response = await client.post("/ikf/federation/submit", json={
                "contribution_ids": contribution_ids
            })

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"Federation submission error: {e}")
            return {"success": False, "error": str(e)}

    async def get_federation_status(self) -> Dict[str, Any]:
        """Get federation node status."""
        try:
            client = await self._get_client()
            response = await client.get("/ikf/federation/status")

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "UNAVAILABLE",
                    "mode": "OFFLINE",
                    "message": "IKF service not responding"
                }

        except Exception as e:
            logger.error(f"Federation status error: {e}")
            return {
                "status": "UNAVAILABLE",
                "mode": "OFFLINE",
                "error": str(e)
            }

    # === Insights for Scaffolding ===

    async def get_phase_insights(
        self,
        methodology: str,
        phase: str,
        industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive insights for a phase.

        Combines benchmarks, risk indicators, and patterns
        for use in scaffolding guidance.

        Args:
            methodology: Innovation methodology
            phase: Current phase
            industry: Optional industry filter

        Returns:
            Combined insights for scaffolding
        """
        # Gather all insights in parallel would be ideal,
        # but for simplicity, sequential calls
        benchmarks = await self.get_benchmarks(methodology, phase, industry)
        risks = await self.get_risk_indicators(phase, methodology, industry)
        patterns = await self.search_patterns(
            methodology=methodology,
            phase=phase,
            package_type="pattern_contribution",
            limit=5
        )

        return {
            "phase": phase,
            "methodology": methodology,
            "benchmarks": benchmarks,
            "common_risks": risks.get("indicators", [])[:5],
            "success_patterns": [
                p.get("pattern", {})
                for p in patterns.get("patterns", [])
                if p.get("pattern", {}).get("success_indicator", False)
            ][:3],
            "warning_patterns": [
                p.get("pattern", {})
                for p in patterns.get("patterns", [])
                if not p.get("pattern", {}).get("success_indicator", True)
            ][:3],
            "data_sources": {
                "benchmarks": benchmarks.get("source", "unknown"),
                "risks": risks.get("source", "unknown"),
                "patterns": patterns.get("source", "unknown")
            }
        }
