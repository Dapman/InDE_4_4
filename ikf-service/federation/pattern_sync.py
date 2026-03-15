"""
Pattern Sync Service - Incremental Differential Pattern Pull

Implements two sync modes:
1. Periodic sync: Background task runs every IKF_SYNC_INTERVAL_MINUTES
2. On-demand sync: Triggered by coaching engine for specific domain/problem

Both modes use differential pull - only patterns newer than last_sync_timestamp
are requested, reducing bandwidth and processing overhead.

Finding 3.4: Implements incremental differential sync to replace stub endpoint.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("inde.ikf.pattern_sync")


class PatternSyncService:
    """
    Manages periodic and on-demand pattern synchronization from IKF.

    Uses differential pull to minimize data transfer - only requests
    patterns newer than the last successful sync.
    """

    def __init__(
        self,
        db,
        connection_manager,
        circuit_breaker,
        pattern_importer,
        http_client,
        config,
        event_publisher
    ):
        """
        Initialize the Pattern Sync Service.

        Args:
            db: MongoDB database instance
            connection_manager: Federation ConnectionManager
            circuit_breaker: Circuit breaker for resilience
            pattern_importer: PatternImporter instance for processing
            http_client: HTTP client for outbound requests
            config: Configuration object
            event_publisher: Event publisher for notifications
        """
        self._db = db
        self._conn_manager = connection_manager
        self._circuit_breaker = circuit_breaker
        self._importer = pattern_importer
        self._http_client = http_client
        self._config = config
        self._publisher = event_publisher
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False

        # Get sync interval from config or environment
        self._sync_interval_minutes = getattr(
            config, 'IKF_SYNC_INTERVAL_MINUTES',
            int(os.environ.get('IKF_SYNC_INTERVAL_MINUTES', '15'))
        )

    def start_periodic_sync(self):
        """Start periodic pattern sync background task."""
        if self._sync_task and not self._sync_task.done():
            logger.warning("Pattern sync already running")
            return

        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info(f"Periodic pattern sync started (interval: {self._sync_interval_minutes}m)")

    def stop_sync(self):
        """Stop the periodic sync task."""
        self._running = False
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            logger.info("Periodic pattern sync stopped")

    async def _sync_loop(self):
        """
        Periodic sync loop - runs every IKF_SYNC_INTERVAL_MINUTES.

        MUST NEVER block coaching operations.
        """
        interval = self._sync_interval_minutes * 60
        while self._running:
            try:
                await asyncio.sleep(interval)
                if self._conn_manager.is_connected:
                    await self.sync_now()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Periodic sync error (non-blocking): {e}")

    async def sync_now(self, domain_filter: Optional[str] = None) -> dict:
        """
        Execute an immediate pattern sync.

        Differential: only requests patterns newer than last_sync_timestamp.

        Args:
            domain_filter: Optional domain to filter patterns by

        Returns:
            {status: str, patterns: int, accepted: int, rejected: int, ...}
        """
        if not self._conn_manager.is_connected:
            return {"status": "SKIPPED", "reason": "Not connected"}

        sync_state = self._db.ikf_federation_state.find_one({"type": "sync"}) or {}
        last_sync = sync_state.get("last_sync_timestamp")

        try:
            # Build sync request parameters
            params = {}
            if last_sync:
                # Convert datetime to ISO string if needed
                if hasattr(last_sync, 'isoformat'):
                    params["since"] = last_sync.isoformat()
                else:
                    params["since"] = str(last_sync)
            if domain_filter:
                params["domain"] = domain_filter

            # Get auth headers
            from federation.auth import FederationAuthenticator
            auth = FederationAuthenticator(self._db, self._config)
            creds = auth.load_credentials()
            jwt_token = creds.get("federation_jwt") if creds else None

            # Get remote URL
            remote_url = getattr(self._config, 'IKF_REMOTE_NODE_URL', None)
            if not remote_url:
                remote_url = os.environ.get("IKF_REMOTE_NODE_URL", "")

            # Make the sync pull request through circuit breaker
            response = await self._circuit_breaker.call(
                self._http_client.get,
                f"{remote_url}/federation/sync/pull",
                params=params,
                headers=auth.create_outbound_headers(jwt_token)
            )

            if response.status_code == 200:
                data = response.json()
                patterns = data.get("patterns", [])

                # Import received patterns
                if patterns:
                    results = await self._importer.import_patterns(
                        patterns, source="IKF_PULL"
                    )
                else:
                    results = {"accepted": 0, "rejected": 0, "deduplicated": 0}

                # Update sync state
                self._db.ikf_federation_state.update_one(
                    {"type": "sync"},
                    {
                        "$set": {
                            "last_sync_timestamp": datetime.now(timezone.utc),
                            "last_sync_patterns_received": len(patterns),
                            "updated_at": datetime.now(timezone.utc)
                        },
                        "$inc": {
                            "total_patterns_received": len(patterns)
                        }
                    }
                )

                # Acknowledge receipt to IKF
                if patterns:
                    pattern_ids = [
                        p.get("pattern_id") for p in patterns
                        if p.get("pattern_id")
                    ]
                    if pattern_ids:
                        try:
                            await self._circuit_breaker.call(
                                self._http_client.post,
                                f"{remote_url}/federation/sync/acknowledge",
                                json={"pattern_ids": pattern_ids},
                                headers=auth.create_outbound_headers(jwt_token)
                            )
                        except Exception as e:
                            logger.warning(f"Failed to acknowledge patterns: {e}")

                # Publish sync completion event
                try:
                    await self._publisher.publish_ikf_event("pattern.sync_completed", {
                        "patterns_received": len(patterns),
                        "accepted": results.get("accepted", 0),
                        "rejected": results.get("rejected", 0),
                        "deduplicated": results.get("deduplicated", 0),
                        "differential": bool(last_sync)
                    })
                except Exception as e:
                    logger.warning(f"Failed to publish sync event: {e}")

                logger.info(
                    f"Pattern sync completed: {len(patterns)} received, "
                    f"{results.get('accepted', 0)} accepted"
                )
                return {
                    "status": "OK",
                    "patterns": len(patterns),
                    **results
                }
            else:
                raise ConnectionError(f"Sync pull failed: {response.status_code}")

        except Exception as e:
            logger.warning(f"Pattern sync failed: {e}")
            return {"status": "FAILED", "reason": str(e)}

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status for admin dashboard."""
        sync_state = self._db.ikf_federation_state.find_one({"type": "sync"}) or {}

        return {
            "last_sync": sync_state.get("last_sync_timestamp"),
            "last_patterns_received": sync_state.get("last_sync_patterns_received", 0),
            "total_patterns_received": sync_state.get("total_patterns_received", 0),
            "sync_interval_minutes": self._sync_interval_minutes,
            "sync_running": self._running,
            "connected": self._conn_manager.is_connected if self._conn_manager else False
        }

    async def sync_domain(self, domain: str) -> dict:
        """
        Request patterns for a specific domain.

        Called by coaching engine when domain-specific patterns are needed.

        Args:
            domain: The domain to request patterns for

        Returns:
            Sync result dict
        """
        return await self.sync_now(domain_filter=domain)
