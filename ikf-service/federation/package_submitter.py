"""
InDE v3.2 - IKF Package Submitter
Handles submission of approved packages to the federation.

Submission Flow:
1. Package reaches IKF_READY status (human-approved)
2. PackageSubmitter validates package integrity
3. Submits to federation hub (or queues if offline)
4. Tracks submission status and retries
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger("inde.ikf.submitter")


class PackageSubmitter:
    """
    Submits IKF-ready packages to the federation.

    Features:
    - Validates package integrity before submission
    - Batches submissions for efficiency
    - Handles offline mode with local queuing
    - Tracks submission status and retries
    """

    def __init__(self, db, federation_node):
        """
        Initialize submitter.

        Args:
            db: MongoDB database instance
            federation_node: LocalFederationNode instance
        """
        self._db = db
        self._node = federation_node
        self._max_retries = 3
        self._retry_delay = timedelta(minutes=15)

    async def submit(self, contribution_id: str) -> Dict[str, Any]:
        """
        Submit a single contribution to federation.

        Args:
            contribution_id: Contribution to submit

        Returns:
            Submission result
        """
        # Fetch contribution
        contribution = self._db.ikf_contributions.find_one({
            "contribution_id": contribution_id
        })

        if not contribution:
            return {"success": False, "error": "Contribution not found"}

        # Validate status
        if contribution["status"] != "IKF_READY":
            return {
                "success": False,
                "error": f"Invalid status: {contribution['status']}. Must be IKF_READY."
            }

        # Validate integrity
        integrity_check = self._validate_integrity(contribution)
        if not integrity_check["valid"]:
            return {"success": False, "error": integrity_check["error"]}

        # Check federation connectivity
        if not self._node.is_connected:
            # Queue for later submission
            self._queue_for_submission(contribution_id)
            return {
                "success": True,
                "queued": True,
                "message": "Federation offline - queued for later submission"
            }

        # Submit to federation
        try:
            result = await self._node._submit_to_federation(contribution)

            if result:
                self._db.ikf_contributions.update_one(
                    {"contribution_id": contribution_id},
                    {"$set": {
                        "federation_status": "SUBMITTED",
                        "submitted_at": datetime.now(timezone.utc),
                        "submission_node": self._node.node_id
                    }}
                )
                logger.info(f"Submitted contribution {contribution_id} to federation")
                return {"success": True, "status": "SUBMITTED"}
            else:
                return {"success": False, "error": "Federation rejected submission"}

        except Exception as e:
            logger.error(f"Submission failed for {contribution_id}: {e}")
            self._mark_retry(contribution_id, str(e))
            return {"success": False, "error": str(e), "will_retry": True}

    def _validate_integrity(self, contribution: Dict) -> Dict[str, Any]:
        """Validate package integrity before submission."""
        errors = []

        # Check required fields
        required = ["generalized_data", "package_type", "confidence"]
        for field in required:
            if not contribution.get(field):
                errors.append(f"Missing required field: {field}")

        # Verify hash matches
        if contribution.get("original_hash"):
            original_data = contribution.get("original_data", {})
            current_hash = hashlib.sha256(
                json.dumps(original_data, sort_keys=True, default=str).encode()
            ).hexdigest()[:16]

            if current_hash != contribution["original_hash"]:
                errors.append("Original data hash mismatch - data may have been modified")

        # Check PII scan passed
        pii_scan = contribution.get("pii_scan", {})
        if not pii_scan.get("passed", True):
            if contribution.get("pii_override"):
                logger.warning(f"Submitting package with PII override: {contribution['contribution_id']}")
            else:
                errors.append("PII scan did not pass and no override present")

        # Check confidence threshold
        min_confidence = 0.5
        if contribution.get("confidence", 0) < min_confidence:
            logger.warning(f"Low confidence package: {contribution['confidence']}")
            # Not blocking, just warning

        if errors:
            return {"valid": False, "error": "; ".join(errors)}

        return {"valid": True}

    def _queue_for_submission(self, contribution_id: str):
        """Queue contribution for later submission when online."""
        self._db.ikf_contributions.update_one(
            {"contribution_id": contribution_id},
            {"$set": {
                "federation_status": "PENDING",
                "queued_at": datetime.now(timezone.utc)
            }}
        )
        logger.info(f"Queued {contribution_id} for federation submission")

    def _mark_retry(self, contribution_id: str, error: str):
        """Mark contribution for retry after failure."""
        self._db.ikf_contributions.update_one(
            {"contribution_id": contribution_id},
            {
                "$set": {
                    "federation_status": "RETRY_PENDING",
                    "last_error": error,
                    "retry_after": datetime.now(timezone.utc) + self._retry_delay
                },
                "$inc": {"retry_count": 1}
            }
        )

    async def submit_batch(self, contribution_ids: List[str]) -> Dict[str, Any]:
        """
        Submit multiple contributions.

        Args:
            contribution_ids: List of contribution IDs

        Returns:
            Batch submission result
        """
        results = {
            "total": len(contribution_ids),
            "submitted": 0,
            "queued": 0,
            "failed": 0,
            "details": []
        }

        for cid in contribution_ids:
            result = await self.submit(cid)
            result["contribution_id"] = cid
            results["details"].append(result)

            if result.get("success"):
                if result.get("queued"):
                    results["queued"] += 1
                else:
                    results["submitted"] += 1
            else:
                results["failed"] += 1

        return results

    async def process_retry_queue(self) -> Dict[str, int]:
        """
        Process contributions pending retry.

        Returns:
            {"processed": count, "succeeded": count, "failed": count}
        """
        now = datetime.now(timezone.utc)

        # Find contributions ready for retry
        ready_for_retry = list(self._db.ikf_contributions.find({
            "federation_status": "RETRY_PENDING",
            "retry_after": {"$lte": now},
            "retry_count": {"$lt": self._max_retries}
        }))

        processed = 0
        succeeded = 0
        failed = 0

        for contribution in ready_for_retry:
            processed += 1
            result = await self.submit(contribution["contribution_id"])

            if result.get("success") and not result.get("queued"):
                succeeded += 1
            else:
                failed += 1

        # Mark contributions that exceeded max retries as failed
        exceeded = self._db.ikf_contributions.update_many(
            {
                "federation_status": "RETRY_PENDING",
                "retry_count": {"$gte": self._max_retries}
            },
            {"$set": {
                "federation_status": "SUBMISSION_FAILED",
                "failed_at": now
            }}
        )

        if exceeded.modified_count:
            logger.warning(f"Marked {exceeded.modified_count} contributions as SUBMISSION_FAILED")

        return {
            "processed": processed,
            "succeeded": succeeded,
            "failed": failed,
            "exceeded_retries": exceeded.modified_count
        }

    def get_submission_stats(self) -> Dict[str, Any]:
        """Get submission statistics."""
        pipeline = [
            {"$group": {
                "_id": "$federation_status",
                "count": {"$sum": 1}
            }}
        ]

        results = list(self._db.ikf_contributions.aggregate(pipeline))
        stats = {r["_id"] or "NONE": r["count"] for r in results}

        return {
            "by_status": stats,
            "pending": stats.get("PENDING", 0),
            "submitted": stats.get("SUBMITTED", 0),
            "retry_pending": stats.get("RETRY_PENDING", 0),
            "failed": stats.get("SUBMISSION_FAILED", 0)
        }
