"""
Cross-Organization Discovery Service - Federated Talent Search

Extends v3.4 IDTFS to search across organizational boundaries when local
talent gaps remain unfilled. Requires active trust relationships and
appropriate verification level.

CRITICAL PRIVACY ENFORCEMENT:
- UNAVAILABLE innovators MUST NEVER appear in cross-org results
- Cross-org results always rank BELOW equivalent local results
- Introductions are MEDIATED through IKF (no direct contact)

IKF Endpoints (from IKF-IML Spec Section 6.1.3):
- POST /identity/search            - Search federated innovator profiles
- POST /identity/introduction      - Request mediated introduction
- GET  /identity/introduction/{id} - Check introduction status

Prerequisites:
- ACTIVE trust relationship with target org(s)
- CONTRIBUTOR or STEWARD verification level
- Organization setting: cross_org_discovery_enabled = true
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger("inde.ikf.cross_org_discovery")


class CrossOrgDiscoveryService:
    """
    Service for discovering innovators across trusted organizations.

    This service searches the IKF's federated innovator index when local
    talent pools cannot fill identified gaps. All results are privacy-filtered
    and introductions are mediated.
    """

    def __init__(self, db, trust_manager, connection_manager,
                 circuit_breaker, http_client, config):
        """
        Initialize the Cross-Org Discovery Service.

        Args:
            db: MongoDB database instance
            trust_manager: Trust relationship manager
            connection_manager: Federation connection manager
            circuit_breaker: Circuit breaker for resilience
            http_client: HTTP client for IKF requests
            config: Configuration object
        """
        self._db = db
        self._trust_manager = trust_manager
        self._conn_manager = connection_manager
        self._breaker = circuit_breaker
        self._http_client = http_client
        self._config = config

    async def discover_cross_org(self, gap_context: dict,
                                  local_results: List[dict] = None,
                                  max_results: int = 10) -> dict:
        """
        Discover innovators across trusted organizations.

        This method is called when local IDTFS search returns insufficient
        results for identified talent gaps.

        Args:
            gap_context: Context describing the talent gap
                - required_skills: List of skill requirements
                - methodology_alignment: Optional methodology filter
                - industry_focus: Optional industry filter
                - minimum_experience: Optional experience threshold
            local_results: Results from local IDTFS (for deduplication)
            max_results: Maximum cross-org results to return

        Returns:
            dict with:
                - results: List of anonymized cross-org profiles
                - total_found: Total matches (may exceed max_results)
                - search_scope: Organizations searched
                - prerequisites_met: bool
                - attribution: Source attribution for coaching
        """
        # Check prerequisites
        prereqs = await self._check_prerequisites()
        if not prereqs["met"]:
            return {
                "results": [],
                "total_found": 0,
                "search_scope": [],
                "prerequisites_met": False,
                "reason": prereqs["reason"],
                "attribution": None
            }

        # Build search parameters
        search_params = self._build_search_params(gap_context, prereqs)

        # Execute federated search
        try:
            response = await self._breaker.call(
                self._http_client.post,
                f"{self._get_ikf_base_url()}/v1/identity/search",
                json=search_params,
                headers=self._create_outbound_headers()
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("profiles", [])

                # Filter out any UNAVAILABLE (should not happen but enforce)
                results = self._enforce_availability_filter(results)

                # Rank results (cross-org always below local equivalents)
                ranked = self._rank_cross_org_results(results, local_results or [])

                # Limit results
                final_results = ranked[:max_results]

                return {
                    "results": final_results,
                    "total_found": data.get("totalCount", len(results)),
                    "search_scope": data.get("searchedOrgs", []),
                    "prerequisites_met": True,
                    "attribution": self._build_attribution(data)
                }
            else:
                logger.warning(f"Cross-org search failed: {response.status_code}")
                return {
                    "results": [],
                    "total_found": 0,
                    "search_scope": [],
                    "prerequisites_met": True,
                    "reason": "Search request failed",
                    "attribution": None
                }

        except Exception as e:
            logger.error(f"Cross-org discovery error: {e}")
            return {
                "results": [],
                "total_found": 0,
                "search_scope": [],
                "prerequisites_met": True,
                "reason": str(e),
                "attribution": None
            }

    async def request_introduction(self, target_gii: str,
                                    context: str,
                                    purpose: str) -> dict:
        """
        Request a mediated introduction to a cross-org innovator.

        POST /identity/introduction

        Introductions are MEDIATED - the IKF facilitates contact without
        exposing direct contact information. The target innovator must
        accept the introduction request.

        Args:
            target_gii: Global Innovator ID of target
            context: Context for the introduction request
            purpose: Purpose of the introduction

        Returns:
            dict with introduction request status
        """
        prereqs = await self._check_prerequisites()
        if not prereqs["met"]:
            return {
                "success": False,
                "reason": prereqs["reason"]
            }

        payload = {
            "targetGii": target_gii,
            "context": context,
            "purpose": purpose,
            "requestedAt": datetime.now(timezone.utc).isoformat()
        }

        try:
            response = await self._breaker.call(
                self._http_client.post,
                f"{self._get_ikf_base_url()}/v1/identity/introduction",
                json=payload,
                headers=self._create_outbound_headers()
            )

            if response.status_code == 201:
                data = response.json()
                # Cache introduction request locally
                await self._cache_introduction_request(data)
                logger.info(f"Introduction requested for {target_gii}")
                return {
                    "success": True,
                    "introduction_id": data.get("introductionId"),
                    "status": data.get("status"),
                    "message": "Introduction request submitted"
                }
            elif response.status_code == 403:
                return {
                    "success": False,
                    "reason": "Target innovator not available for introductions"
                }
            else:
                return {
                    "success": False,
                    "reason": f"Request failed: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Introduction request error: {e}")
            return {
                "success": False,
                "reason": str(e)
            }

    async def get_introduction_status(self, introduction_id: str) -> Optional[dict]:
        """
        Check the status of an introduction request.

        GET /identity/introduction/{id}

        Args:
            introduction_id: The introduction request ID

        Returns:
            Status dict or None if not found
        """
        try:
            response = await self._breaker.call(
                self._http_client.get,
                f"{self._get_ikf_base_url()}/v1/identity/introduction/{introduction_id}",
                headers=self._create_outbound_headers()
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            logger.warning(f"Introduction status check failed: {e}")
            return None

    async def _check_prerequisites(self) -> dict:
        """
        Check prerequisites for cross-org discovery.

        Requirements:
        1. Connected to IKF
        2. At least one ACTIVE trust relationship
        3. CONTRIBUTOR or STEWARD verification level
        4. Org setting: cross_org_discovery_enabled = true

        Returns:
            dict with 'met' bool and 'reason' if not met
        """
        # Check connection
        if not self._conn_manager.is_connected:
            return {
                "met": False,
                "reason": "Not connected to federation"
            }

        # Check trust prerequisites
        trust_prereqs = await self._trust_manager.check_trust_prerequisites()

        if not trust_prereqs.get("has_active_trust"):
            return {
                "met": False,
                "reason": "No active trust relationships"
            }

        if not trust_prereqs.get("can_use_cross_org_idtfs"):
            verification = trust_prereqs.get("verification_level", "UNKNOWN")
            return {
                "met": False,
                "reason": f"Cross-org IDTFS requires CONTRIBUTOR or STEWARD level (current: {verification})"
            }

        # Check org setting
        org_settings = self._db.organization_settings.find_one({})
        if org_settings and not org_settings.get("cross_org_discovery_enabled", True):
            return {
                "met": False,
                "reason": "Cross-org discovery disabled by organization"
            }

        return {
            "met": True,
            "trusted_orgs": trust_prereqs.get("trusted_org_ids", []),
            "verification_level": trust_prereqs.get("verification_level")
        }

    def _build_search_params(self, gap_context: dict, prereqs: dict) -> dict:
        """
        Build search parameters for IKF identity search.

        Args:
            gap_context: The talent gap context
            prereqs: Prerequisites check result

        Returns:
            dict of search parameters
        """
        params = {
            "searchScope": prereqs.get("trusted_orgs", []),
            "availabilityFilter": ["AVAILABLE", "LIMITED"],  # NEVER include UNAVAILABLE
            "includeAnonymized": True
        }

        if gap_context.get("required_skills"):
            params["skills"] = gap_context["required_skills"]

        if gap_context.get("methodology_alignment"):
            params["methodologyAlignment"] = gap_context["methodology_alignment"]

        if gap_context.get("industry_focus"):
            params["industryFocus"] = gap_context["industry_focus"]

        if gap_context.get("minimum_experience"):
            params["minimumExperience"] = gap_context["minimum_experience"]

        return params

    def _enforce_availability_filter(self, results: List[dict]) -> List[dict]:
        """
        Enforce availability filter on results.

        CRITICAL: UNAVAILABLE innovators must NEVER appear in cross-org results.
        This is a defense-in-depth check - the IKF should already filter these.

        Args:
            results: Raw search results

        Returns:
            Filtered results (UNAVAILABLE removed)
        """
        filtered = []
        for profile in results:
            availability = profile.get("availability", "UNAVAILABLE")
            if availability == "UNAVAILABLE":
                # Log violation for audit
                logger.warning(
                    f"PRIVACY VIOLATION: UNAVAILABLE profile in cross-org results "
                    f"(GII: {profile.get('gii', 'unknown')})"
                )
                continue
            filtered.append(profile)

        return filtered

    def _rank_cross_org_results(self, cross_org: List[dict],
                                 local: List[dict]) -> List[dict]:
        """
        Rank cross-org results below local equivalents.

        Cross-org results are inherently lower priority than local results
        due to introduction overhead and reduced context.

        Args:
            cross_org: Cross-org search results
            local: Local IDTFS results for comparison

        Returns:
            Ranked cross-org results
        """
        # Get local GIIs for deduplication
        local_giis = {r.get("gii") for r in local if r.get("gii")}

        # Filter duplicates and rank
        ranked = []
        for profile in cross_org:
            gii = profile.get("gii")
            if gii in local_giis:
                continue  # Skip duplicates

            # Add cross-org indicator and rank penalty
            profile["source"] = "cross_org"
            profile["rank_penalty"] = 0.2  # 20% rank penalty for cross-org

            # Calculate effective score
            base_score = profile.get("matchScore", 0.5)
            profile["effective_score"] = base_score * (1 - profile["rank_penalty"])

            ranked.append(profile)

        # Sort by effective score
        ranked.sort(key=lambda x: x.get("effective_score", 0), reverse=True)

        return ranked

    def _build_attribution(self, data: dict) -> dict:
        """
        Build attribution for cross-org discovery results.

        Args:
            data: IKF response data

        Returns:
            Attribution dict for coaching context
        """
        return {
            "source": "IKF Cross-Org Discovery",
            "searched_orgs": len(data.get("searchedOrgs", [])),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Results from trusted partner organizations"
        }

    async def _cache_introduction_request(self, data: dict):
        """Cache introduction request locally for tracking."""
        self._db.ikf_introduction_requests.update_one(
            {"introduction_id": data.get("introductionId")},
            {"$set": {
                "introduction_id": data.get("introductionId"),
                "target_gii": data.get("targetGii"),
                "status": data.get("status"),
                "requested_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    def _get_ikf_base_url(self) -> str:
        """Get the IKF base URL from config or environment."""
        if self._config and hasattr(self._config, 'ikf_base_url'):
            return self._config.ikf_base_url
        return os.environ.get("IKF_REMOTE_NODE_URL", "http://localhost:8081/ikf-hub")

    def _create_outbound_headers(self) -> dict:
        """Create headers for outbound IKF requests."""
        if self._config and hasattr(self._config, 'create_outbound_headers'):
            return self._config.create_outbound_headers()
        return {"Content-Type": "application/json"}
