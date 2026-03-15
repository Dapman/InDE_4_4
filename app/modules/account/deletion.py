"""
Account Deletion Service
Implements the two-phase account deletion flow:
Phase 1: Request → deactivate + schedule + email confirmation
Phase 2: Execute → permanent deletion after cooling-off period

All operations are idempotent and logged.

v3.12: Account Trust & Completeness
"""

import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

COOLING_OFF_DAYS = int(os.environ.get("ACCOUNT_DELETION_COOLING_OFF_DAYS", "14"))


class AccountDeletionService:
    """
    Manages the complete account deletion lifecycle.

    Two-phase deletion:
    1. Request: Deactivate account, schedule deletion, send confirmation email
    2. Execute: After cooling-off period, permanently delete/anonymize data
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database instance (expects db.db for raw pymongo access)
        """
        self.db = db.db if hasattr(db, 'db') else db

    async def request_deletion(self, user_id: str, requesting_ip: str = "") -> dict:
        """
        Phase 1: User initiates account deletion.

        - Sets account to deactivated
        - Schedules deletion date (now + COOLING_OFF_DAYS)
        - Generates cancellation token
        - Revokes all active sessions immediately

        Args:
            user_id: The user requesting deletion
            requesting_ip: IP address for audit logging

        Returns:
            dict with scheduled_for, cancellation_token, already_requested

        Raises:
            ValueError: If user not found or already deleted
        """
        user = self.db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError(f"User {user_id} not found")

        if user.get("status") == "deleted":
            raise ValueError("Account already deleted")

        if user.get("status") == "deactivated":
            # Already in cooling-off — return existing scheduled date
            return {
                "scheduled_for": user.get("deletion_scheduled_for"),
                "cancellation_token": user.get("deletion_cancellation_token"),
                "already_requested": True
            }

        # Generate cryptographically secure cancellation token
        cancellation_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        scheduled_for = (now + timedelta(days=COOLING_OFF_DAYS)).isoformat()

        # Deactivate account
        self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "status": "deactivated",
                "deletion_requested_at": now.isoformat(),
                "deletion_scheduled_for": scheduled_for,
                "deletion_cancellation_token": cancellation_token,
            }}
        )

        # Revoke all active sessions immediately
        self.db.sessions.update_many(
            {"user_id": user_id},
            {"$set": {"revoked": True}}
        )

        # Log the event
        self._log_event(user_id, "ACCOUNT_DELETION_REQUESTED", {
            "scheduled_for": scheduled_for,
            "requesting_ip": requesting_ip
        })

        logger.info(f"Account deletion requested for user {user_id}. Scheduled for {scheduled_for}.")

        return {
            "scheduled_for": scheduled_for,
            "cancellation_token": cancellation_token,
            "already_requested": False
        }

    async def cancel_deletion(self, cancellation_token: str) -> dict:
        """
        Cancel a pending account deletion using the cancellation token.
        Restores account to active status.

        Args:
            cancellation_token: The token from the cancellation email

        Returns:
            dict with success, display_name (if success), or reason (if failure)
        """
        user = self.db.users.find_one({
            "deletion_cancellation_token": cancellation_token,
            "status": "deactivated"
        })

        if not user:
            return {"success": False, "reason": "Token invalid or account already deleted"}

        user_id = user.get("user_id", str(user.get("_id")))

        # Restore account
        self.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "status": "active",
                "deletion_requested_at": None,
                "deletion_scheduled_for": None,
                "deletion_cancellation_token": None,
            }}
        )

        self._log_event(user_id, "ACCOUNT_DELETION_CANCELLED", {})

        logger.info(f"Account deletion cancelled for user {user_id}.")

        return {"success": True, "display_name": user.get("display_name", user.get("name", "Innovator"))}

    async def execute_deletion(self, user_id: str) -> dict:
        """
        Phase 2: Execute permanent account deletion.
        Called by the background job after the cooling-off period.

        IDEMPOTENT: Safe to call multiple times for the same user_id.

        Args:
            user_id: The user to delete

        Returns:
            dict with success, steps_completed, and any error info
        """
        user = self.db.users.find_one({"user_id": user_id})
        if not user:
            return {"success": False, "reason": "User not found"}

        if user.get("status") == "deleted":
            return {"success": True, "reason": "Already deleted", "steps_completed": []}

        if user.get("status") != "deactivated":
            return {"success": False, "reason": f"Account status is '{user.get('status')}', not 'deactivated'"}

        steps_completed = []
        anon_id = f"anon_{secrets.token_hex(16)}"
        original_email = user.get("email", "")
        display_name = user.get("display_name", user.get("name", "Innovator"))

        try:
            # Step 1: Revoke remaining sessions
            self.db.sessions.update_many(
                {"user_id": user_id},
                {"$set": {"revoked": True}}
            )
            steps_completed.append("sessions_revoked")

            # Step 2: Anonymize coaching sessions
            self.db.coaching_sessions.update_many(
                {"user_id": user_id},
                {"$set": {"user_id": anon_id, "user_email": None, "user_display_name": None}}
            )
            steps_completed.append("coaching_sessions_anonymized")

            # Step 3: Anonymize pursuits
            self.db.pursuits.update_many(
                {"user_id": user_id},
                {"$set": {"user_id": anon_id, "user_email": None}}
            )
            steps_completed.append("pursuits_anonymized")

            # Step 4: Delete private IML memory records (not yet contributed)
            self.db.memory_records.delete_many({
                "user_id": user_id,
                "publication_status": {"$in": ["PRIVATE", "PENDING"]}
            })
            steps_completed.append("private_memory_records_deleted")

            # Step 5: Anonymize published IML records (already in IKF pipeline)
            self.db.memory_records.update_many(
                {"user_id": user_id, "publication_status": "PUBLISHED"},
                {"$set": {"user_id": anon_id}}
            )
            steps_completed.append("published_memory_records_anonymized")

            # Step 6: Delete maturity events
            self.db.maturity_events.delete_many({"user_id": user_id})
            steps_completed.append("maturity_events_deleted")

            # Step 7: Delete password reset tokens
            self.db.password_reset_tokens.delete_many({"user_id": user_id})
            steps_completed.append("password_reset_tokens_deleted")

            # Step 8: Scrub user document (preserve as tombstone for audit)
            self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "status": "deleted",
                    "email": f"deleted_{user_id}@deleted.indeverse",
                    "name": "[Deleted User]",
                    "display_name": "[Deleted User]",
                    "password_hash": "",
                    "gii_id": None,
                    "organization_id": None,
                    "preferences": {},
                    "maturity_scores": {},
                    "deletion_cancellation_token": None,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                }}
            )
            steps_completed.append("user_document_scrubbed")

            # Step 9: Log completion
            self._log_event(user_id, "ACCOUNT_DELETION_COMPLETED", {
                "steps_completed": steps_completed,
                "anon_id_assigned": anon_id
            })
            steps_completed.append("audit_logged")

            logger.info(f"Account deletion completed for user {user_id}. Steps: {steps_completed}")

            # Send final notification email (best effort - don't fail if email fails)
            try:
                from services.email_service import send_deletion_completed_email
                send_deletion_completed_email(original_email, display_name)
            except Exception as e:
                logger.warning(f"Could not send deletion completion email: {e}")

            return {"success": True, "steps_completed": steps_completed}

        except Exception as e:
            logger.error(f"Account deletion failed at step {len(steps_completed)} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "steps_completed": steps_completed,
                "note": "Re-running execute_deletion is safe — completed steps are idempotent"
            }

    async def run_scheduled_deletions(self) -> dict:
        """
        Background job: find and execute all accounts past their deletion date.
        Called hourly by the application scheduler.

        Returns:
            dict with processed count and per-user results
        """
        now = datetime.now(timezone.utc).isoformat()

        due = list(self.db.users.find({
            "status": "deactivated",
            "deletion_scheduled_for": {"$lte": now}
        }).limit(100))

        results = []
        for user in due:
            user_id = user.get("user_id", str(user.get("_id")))
            result = await self.execute_deletion(user_id)
            results.append({"user_id": user_id, **result})

        logger.info(f"Scheduled deletion job: processed {len(due)} accounts.")
        return {"processed": len(due), "results": results}

    def _log_event(self, user_id: str, event_type: str, metadata: dict) -> None:
        """Write an account lifecycle event to the audit log."""
        try:
            self.db.audit_log.insert_one({
                "user_id": user_id,
                "event_type": event_type,
                "metadata": metadata,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to write audit log for {event_type}: {e}")
