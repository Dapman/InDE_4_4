"""
Reputation Tracker - Organization & Innovator Reputation

Reputation is COMPUTED BY THE IKF and pushed to local instances.
Local instances do NOT compute their own reputation - they receive
it from the IKF as an aggregated score.

Reputation components (from IKF-IML Spec Section 7.2.2):
- contributionVolume (20%): Quantity of knowledge shared
- contributionQuality (30%): Downstream application success rates
- patternValidation (25%): Accuracy of pattern predictions
- communityEngagement (15%): Pattern review participation
- complianceRecord (10%): Adherence to sharing terms

Reputation influences:
- Pattern visibility in search results
- Verification level progression eligibility
- Trust relationship eligibility

IKF Endpoints:
- GET /reputation/organization/{orgId}
- GET /reputation/innovator/{gii}
- POST /reputation/contribution/{contributionId}/feedback
- GET /reputation/leaderboard (anonymized)
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger("inde.ikf.reputation_tracker")

REPUTATION_SYNC_INTERVAL = int(os.environ.get("REPUTATION_SYNC_INTERVAL", "3600"))  # Default 1 hour


class ReputationTracker:
    """
    Tracks and caches organization reputation from the IKF.

    Reputation scores are computed by the IKF based on contribution
    quality, engagement, and compliance. This class syncs those scores
    locally for display and eligibility checks.
    """

    def __init__(self, db, connection_manager, circuit_breaker, http_client, config):
        """
        Initialize the Reputation Tracker.

        Args:
            db: MongoDB database instance
            connection_manager: Federation connection manager
            circuit_breaker: Circuit breaker for resilience
            http_client: HTTP client for IKF requests
            config: Configuration object
        """
        self._db = db
        self._conn_manager = connection_manager
        self._breaker = circuit_breaker
        self._http_client = http_client
        self._config = config
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False

    def start_sync(self):
        """Start periodic reputation sync."""
        if self._sync_task and not self._sync_task.done():
            return
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info("Reputation sync started")

    def stop_sync(self):
        """Stop periodic reputation sync."""
        self._running = False
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
        logger.info("Reputation sync stopped")

    async def _sync_loop(self):
        """Periodically fetch reputation from IKF."""
        while self._running:
            try:
                if self._conn_manager.is_connected:
                    await self._refresh_reputation()
                await asyncio.sleep(REPUTATION_SYNC_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reputation sync error: {e}")
                await asyncio.sleep(REPUTATION_SYNC_INTERVAL)

    async def _refresh_reputation(self):
        """Fetch reputation data from IKF."""
        org_id = self._get_org_id()
        if not org_id:
            return

        try:
            response = await self._breaker.call(
                self._http_client.get,
                f"{self._get_ikf_base_url()}/v1/reputation/organization/{org_id}",
                headers=self._create_outbound_headers()
            )

            if response.status_code == 200:
                data = response.json()
                await self._cache_reputation("organization", org_id, data)
                logger.debug(f"Reputation refreshed for org {org_id}")
        except Exception as e:
            logger.warning(f"Reputation fetch failed: {e}")

    async def get_org_reputation(self) -> Optional[dict]:
        """Get cached organization reputation."""
        org_id = self._get_org_id()
        if not org_id:
            return None

        cached = self._db.ikf_reputation.find_one(
            {"entity_type": "organization", "entity_id": org_id}
        )
        return cached.get("data") if cached else None

    async def get_innovator_reputation(self, gii: str) -> Optional[dict]:
        """
        Get reputation for a specific innovator.

        Note: Innovator reputation is only available for innovators
        who have made federation contributions.
        """
        cached = self._db.ikf_reputation.find_one(
            {"entity_type": "innovator", "entity_id": gii}
        )

        if cached:
            return cached.get("data")

        # Try to fetch from IKF
        if self._conn_manager.is_connected:
            try:
                response = await self._breaker.call(
                    self._http_client.get,
                    f"{self._get_ikf_base_url()}/v1/reputation/innovator/{gii}",
                    headers=self._create_outbound_headers()
                )

                if response.status_code == 200:
                    data = response.json()
                    await self._cache_reputation("innovator", gii, data)
                    return data
            except Exception as e:
                logger.warning(f"Innovator reputation fetch failed: {e}")

        return None

    async def submit_contribution_feedback(self, contribution_id: str,
                                            feedback_type: str,
                                            effectiveness_rating: int = None,
                                            comments: str = None) -> bool:
        """
        Submit quality feedback for a received contribution.

        This closes the feedback loop from v3.5.2 pattern application.
        The IKF uses this feedback to update contributor reputation.

        Args:
            contribution_id: The contribution being rated
            feedback_type: "applied", "dismissed", "validated", "disputed"
            effectiveness_rating: 1-5 scale (optional)
            comments: Optional feedback comments

        Returns:
            True if feedback was submitted successfully
        """
        if not self._conn_manager.is_connected:
            logger.warning("Cannot submit feedback: not connected")
            return False

        payload = {
            "feedbackType": feedback_type,
            "effectivenessRating": effectiveness_rating,
            "comments": comments,
            "submittedAt": datetime.now(timezone.utc).isoformat()
        }

        try:
            response = await self._breaker.call(
                self._http_client.post,
                f"{self._get_ikf_base_url()}/v1/reputation/contribution/{contribution_id}/feedback",
                json=payload,
                headers=self._create_outbound_headers()
            )

            if response.status_code == 200:
                logger.info(f"Feedback submitted for contribution {contribution_id}")
                return True
            else:
                logger.error(f"Feedback submission failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Feedback submission error: {e}")
            return False

    async def get_leaderboard(self) -> Optional[List[dict]]:
        """
        Get anonymized reputation leaderboard.

        The leaderboard shows relative rankings without identifying
        individual organizations.
        """
        if not self._conn_manager.is_connected:
            return None

        try:
            response = await self._breaker.call(
                self._http_client.get,
                f"{self._get_ikf_base_url()}/v1/reputation/leaderboard",
                headers=self._create_outbound_headers()
            )

            if response.status_code == 200:
                return response.json().get("entries", [])
        except Exception as e:
            logger.warning(f"Leaderboard fetch failed: {e}")

        return None

    async def _cache_reputation(self, entity_type: str, entity_id: str, data: dict):
        """Cache reputation data locally."""
        self._db.ikf_reputation.update_one(
            {"entity_type": entity_type, "entity_id": entity_id},
            {"$set": {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "data": data,
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )

    def _get_org_id(self) -> Optional[str]:
        """Get the organization ID from federation state."""
        fed_state = self._db.ikf_federation_state.find_one({"type": "registration"})
        return fed_state.get("org_id") if fed_state else None

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
