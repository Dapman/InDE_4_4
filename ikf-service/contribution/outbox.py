"""
Contribution Outbox - Guaranteed Delivery for Federation Submissions

Implements the transactional outbox pattern:
1. When a contribution reaches IKF_READY, an outbox entry is created atomically
2. A background worker polls the outbox and submits to the remote IKF
3. Successful submission -> IKF_SUBMITTED, outbox entry marked delivered
4. Failed submission -> IKF_RETRY with exponential backoff
5. Max retries exceeded -> IKF_FAILED, innovator notified via ODICM

The outbox survives application restarts - undelivered entries are
picked up by the worker on startup.

When federation is DISCONNECTED, contributions accumulate in the outbox
with status IKF_READY. When connection resumes, the worker drains
the backlog automatically.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("inde.ikf.outbox")

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 30  # seconds
POLL_INTERVAL = 15  # seconds
BATCH_SIZE = 5  # submissions per poll


class ContributionOutbox:
    """
    Manages the contribution outbox for guaranteed federation delivery.

    Uses a background worker to drain pending entries when connected.
    Implements exponential backoff for retries.
    """

    def __init__(self, db, connection_manager, circuit_breaker,
                 event_publisher, http_client, config):
        """
        Initialize the contribution outbox.

        Args:
            db: MongoDB database instance
            connection_manager: Federation ConnectionManager
            circuit_breaker: Circuit breaker for resilience
            event_publisher: Event publisher for notifications
            http_client: HTTP client for outbound requests
            config: Configuration object with IKF settings
        """
        self._db = db
        self._conn_manager = connection_manager
        self._circuit_breaker = circuit_breaker
        self._publisher = event_publisher
        self._http_client = http_client
        self._config = config
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    def start_worker(self):
        """Start the background outbox drain worker."""
        if self._worker_task and not self._worker_task.done():
            logger.warning("Outbox worker already running")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._drain_loop())
        logger.info("Outbox worker started")

    def stop_worker(self):
        """Stop the outbox worker."""
        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            logger.info("Outbox worker stopped")

    async def enqueue(self, contribution_id: str):
        """
        Add a contribution to the outbox for federation submission.
        Called when a contribution reaches IKF_READY status.

        CRITICAL: This must be called in the same logical transaction
        as the status update to IKF_READY.

        Args:
            contribution_id: The contribution to enqueue
        """
        now = datetime.now(timezone.utc)

        self._db.ikf_contribution_outbox.update_one(
            {"contribution_id": contribution_id},
            {"$set": {
                "contribution_id": contribution_id,
                "status": "PENDING",
                "enqueued_at": now,
                "attempts": 0,
                "last_attempt": None,
                "next_attempt_after": now,  # Eligible immediately
                "error": None
            }},
            upsert=True
        )
        logger.info(f"Contribution {contribution_id} enqueued for federation submission")

    async def _drain_loop(self):
        """
        Background worker that polls the outbox and submits contributions.

        Runs every POLL_INTERVAL seconds. Only submits when federation is CONNECTED.
        MUST NEVER block coaching operations.
        """
        while self._running:
            try:
                await asyncio.sleep(POLL_INTERVAL)

                # Only submit when connected
                if not self._conn_manager.is_connected:
                    continue

                # Find pending outbox entries eligible for submission
                now = datetime.now(timezone.utc)
                pending = list(self._db.ikf_contribution_outbox.find({
                    "status": {"$in": ["PENDING", "RETRY"]},
                    "next_attempt_after": {"$lte": now}
                }).sort("enqueued_at", 1).limit(BATCH_SIZE))

                for entry in pending:
                    if not self._running:
                        break
                    await self._submit_one(entry)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Outbox drain error (non-blocking): {e}")

    async def _submit_one(self, outbox_entry: dict):
        """Submit a single contribution to the remote IKF."""
        contribution_id = outbox_entry["contribution_id"]

        # Load the full contribution
        contribution = self._db.ikf_contributions.find_one(
            {"contribution_id": contribution_id}
        )
        if not contribution:
            logger.error(f"Contribution {contribution_id} not found - removing from outbox")
            self._db.ikf_contribution_outbox.delete_one({"contribution_id": contribution_id})
            return

        # Update status to SUBMITTING
        self._db.ikf_contributions.update_one(
            {"contribution_id": contribution_id},
            {"$set": {"status": "IKF_SUBMITTING", "updated_at": datetime.now(timezone.utc)}}
        )

        try:
            # Publication boundary check - import here to avoid circular imports
            from contribution.publication_boundary import PublicationBoundary, PublicationBoundaryError
            boundary = PublicationBoundary(self._db)
            try:
                boundary.enforce(contribution, contribution.get("user_id"))
            except PublicationBoundaryError as e:
                # HARD BLOCK - do not submit, mark as failed
                self._db.ikf_contributions.update_one(
                    {"contribution_id": contribution_id},
                    {"$set": {
                        "status": "IKF_FAILED",
                        "failure_reason": f"Boundary violation: {e}",
                        "updated_at": datetime.now(timezone.utc)
                    }}
                )
                self._db.ikf_contribution_outbox.update_one(
                    {"contribution_id": contribution_id},
                    {"$set": {"status": "FAILED", "error": f"Boundary violation: {e}"}}
                )
                logger.error(f"Publication boundary blocked contribution {contribution_id}: {e}")
                return

            # Submit through circuit breaker
            from federation.auth import FederationAuthenticator
            auth = FederationAuthenticator(self._db, self._config)
            creds = auth.load_credentials()
            jwt_token = creds.get("federation_jwt") if creds else None

            remote_url = getattr(self._config, 'IKF_REMOTE_NODE_URL', None)
            if not remote_url:
                import os
                remote_url = os.environ.get("IKF_REMOTE_NODE_URL", "")

            instance_id = getattr(self._config, 'IKF_INSTANCE_ID', None)
            if not instance_id:
                import os
                instance_id = os.environ.get("IKF_INSTANCE_ID", "unknown")

            response = await self._circuit_breaker.call(
                self._http_client.post,
                f"{remote_url}/knowledge/contribute",
                json={
                    "contribution_id": contribution_id,
                    "package_type": contribution.get("package_type"),
                    "generalized_content": contribution.get("generalized_content") or contribution.get("generalized_data"),
                    "sharing_rights": contribution.get("sharing_rights", "ORG"),
                    "generalization_level": contribution.get("generalization_level", 1),
                    "applicability_context": contribution.get("applicability_context", {}),
                    "source_metadata": {
                        "instance_id": instance_id,
                        "org_id": contribution.get("org_id"),
                        "industry_codes": contribution.get("industry_codes", []),
                        "schema_version": "3.5.2"
                    },
                    "contributor_gii": contribution.get("gii_id"),
                    "submitted_at": datetime.now(timezone.utc).isoformat()
                },
                headers=auth.create_outbound_headers(jwt_token)
            )

            if response.status_code == 200:
                data = response.json()
                # Update contribution status
                self._db.ikf_contributions.update_one(
                    {"contribution_id": contribution_id},
                    {"$set": {
                        "status": "IKF_SUBMITTED",
                        "ikf_receipt_id": data.get("receipt_id"),
                        "submitted_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }}
                )
                # Mark outbox entry as delivered
                self._db.ikf_contribution_outbox.update_one(
                    {"contribution_id": contribution_id},
                    {"$set": {"status": "DELIVERED", "delivered_at": datetime.now(timezone.utc)}}
                )

                # Publish event
                await self._publisher.publish_ikf_event("contribution.submitted", {
                    "contribution_id": contribution_id,
                    "package_type": contribution.get("package_type"),
                    "receipt_id": data.get("receipt_id")
                })

                logger.info(f"Contribution {contribution_id} submitted successfully")

                # Handle immediate acceptance (hub simulator returns this)
                if data.get("status") == "ACCEPTED":
                    self._db.ikf_contributions.update_one(
                        {"contribution_id": contribution_id},
                        {"$set": {"status": "IKF_ACCEPTED", "updated_at": datetime.now(timezone.utc)}}
                    )
                    await self._publisher.publish_ikf_event("contribution.accepted", {
                        "contribution_id": contribution_id,
                        "receipt_id": data.get("receipt_id")
                    })
            else:
                raise ConnectionError(f"IKF returned {response.status_code}: {response.text}")

        except Exception as e:
            attempts = outbox_entry.get("attempts", 0) + 1

            if attempts >= MAX_RETRIES:
                # Max retries exceeded
                self._db.ikf_contributions.update_one(
                    {"contribution_id": contribution_id},
                    {"$set": {
                        "status": "IKF_FAILED",
                        "updated_at": datetime.now(timezone.utc),
                        "failure_reason": str(e)
                    }}
                )
                self._db.ikf_contribution_outbox.update_one(
                    {"contribution_id": contribution_id},
                    {"$set": {"status": "FAILED", "error": str(e)}}
                )
                await self._publisher.publish_ikf_event("contribution.failed", {
                    "contribution_id": contribution_id,
                    "reason": str(e),
                    "attempts": attempts
                })
                logger.error(f"Contribution {contribution_id} FAILED after {attempts} attempts: {e}")
            else:
                # Schedule retry with backoff
                backoff = RETRY_BACKOFF_BASE * (2 ** (attempts - 1))
                next_attempt = datetime.now(timezone.utc) + timedelta(seconds=backoff)

                self._db.ikf_contributions.update_one(
                    {"contribution_id": contribution_id},
                    {"$set": {"status": "IKF_RETRY", "updated_at": datetime.now(timezone.utc)}}
                )
                self._db.ikf_contribution_outbox.update_one(
                    {"contribution_id": contribution_id},
                    {"$set": {
                        "status": "RETRY",
                        "attempts": attempts,
                        "last_attempt": datetime.now(timezone.utc),
                        "next_attempt_after": next_attempt,
                        "error": str(e)
                    }}
                )
                logger.warning(f"Contribution {contribution_id} retry {attempts}/{MAX_RETRIES} in {backoff}s")

    def get_queue_status(self) -> dict:
        """Return current outbox status for admin dashboard."""
        return {
            "pending": self._db.ikf_contribution_outbox.count_documents({"status": "PENDING"}),
            "retry": self._db.ikf_contribution_outbox.count_documents({"status": "RETRY"}),
            "delivered": self._db.ikf_contribution_outbox.count_documents({"status": "DELIVERED"}),
            "failed": self._db.ikf_contribution_outbox.count_documents({"status": "FAILED"}),
            "worker_running": self._running
        }

    async def requeue_failed(self, contribution_id: str) -> dict:
        """
        Manually requeue a failed contribution for retry.

        Args:
            contribution_id: The failed contribution to retry

        Returns:
            Status of the requeue operation
        """
        entry = self._db.ikf_contribution_outbox.find_one(
            {"contribution_id": contribution_id, "status": "FAILED"}
        )
        if not entry:
            return {"success": False, "reason": "Not found or not in FAILED status"}

        now = datetime.now(timezone.utc)
        self._db.ikf_contribution_outbox.update_one(
            {"contribution_id": contribution_id},
            {"$set": {
                "status": "PENDING",
                "attempts": 0,
                "next_attempt_after": now,
                "error": None
            }}
        )

        self._db.ikf_contributions.update_one(
            {"contribution_id": contribution_id},
            {"$set": {"status": "IKF_READY", "updated_at": now, "failure_reason": None}}
        )

        logger.info(f"Contribution {contribution_id} requeued for retry")
        return {"success": True, "contribution_id": contribution_id}
