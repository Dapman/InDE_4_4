"""
Password Reset Service
Secure, time-limited, single-use password reset tokens.

v3.12: Account Trust & Completeness
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

EXPIRY_MINUTES = int(os.environ.get("PASSWORD_RESET_TOKEN_EXPIRY_MINUTES", "60"))


class PasswordResetService:
    """
    Manages password reset token lifecycle.

    Security features:
    - Tokens are SHA-256 hashed before storage (never store plaintext)
    - Single-use: tokens are marked as used after consumption
    - Time-limited: tokens expire after EXPIRY_MINUTES (default 60)
    - All existing sessions are revoked on password reset
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database instance (expects db.db for raw pymongo access)
        """
        self.db = db.db if hasattr(db, 'db') else db

    def _hash_token(self, token: str) -> str:
        """SHA-256 hash a token for storage. Never store plaintext tokens."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def create_reset_token(self, email: str, requesting_ip: str = "") -> Optional[dict]:
        """
        Create a password reset token for the given email.

        Returns {"token": str, "user": dict, "expires_at": str} if email found.
        Returns None if email not found (do NOT reveal this to the caller —
        always return a 200 to prevent email enumeration attacks).

        Args:
            email: The email address requesting password reset
            requesting_ip: IP address for audit logging

        Returns:
            dict with token, user, expires_at if found; None otherwise
        """
        user = self.db.users.find_one({
            "email": email.lower().strip(),
            "status": {"$in": ["active", None]}  # Allow users without status field (pre-v3.12)
        })

        if not user:
            # Return None but log — caller must return 200 regardless
            logger.info(f"Password reset requested for unknown/inactive email: {email}")
            return None

        user_id = user.get("user_id", str(user.get("_id")))

        # Invalidate any existing unused tokens for this user
        self.db.password_reset_tokens.update_many(
            {"user_id": user_id, "used": False},
            {"$set": {"used": True}}
        )

        # Generate token
        plaintext_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(plaintext_token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=EXPIRY_MINUTES)

        # Store hash (never the plaintext)
        self.db.password_reset_tokens.insert_one({
            "user_id": user_id,
            "token_hash": token_hash,
            "created_at": now,  # Store as datetime for TTL index
            "expires_at": expires_at,  # Store as datetime for TTL index
            "used": False,
            "ip_address": requesting_ip
        })

        logger.info(f"Password reset token created for user {user_id}")

        return {
            "token": plaintext_token,  # Only time plaintext exists — send in email, discard
            "user": user,
            "expires_at": expires_at.isoformat()
        }

    async def validate_and_consume_token(
        self,
        token: str,
        new_password: str
    ) -> dict:
        """
        Validate a reset token and update the password if valid.
        Consumes (invalidates) the token on success.

        Args:
            token: The plaintext token from the email link
            new_password: The new password (should already be validated >= 8 chars)

        Returns:
            dict with success bool and reason string
        """
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)

        token_doc = self.db.password_reset_tokens.find_one({
            "token_hash": token_hash,
            "used": False,
            "expires_at": {"$gt": now}
        })

        if not token_doc:
            logger.info("Password reset attempted with invalid or expired token")
            return {"success": False, "reason": "Token invalid or expired"}

        # Mark token as used (single-use enforcement)
        self.db.password_reset_tokens.update_one(
            {"_id": token_doc["_id"]},
            {"$set": {"used": True}}
        )

        # Update password — use existing password hashing utility
        from auth.password import hash_password
        new_hash = hash_password(new_password)

        user_id = token_doc["user_id"]

        self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "password_hash": new_hash,
                "last_active": now
            }}
        )

        # Revoke all existing sessions (password change = all sessions invalidated)
        result = self.db.sessions.update_many(
            {"user_id": user_id},
            {"$set": {"revoked": True}}
        )

        logger.info(f"Password reset completed for user {user_id}. {result.modified_count} sessions revoked.")
        return {"success": True}

    async def admin_generate_reset_link(self, user_id: str) -> Optional[str]:
        """
        Admin endpoint: generate a reset link for a user without sending email.
        For self-hosted recovery scenarios where SMTP is not configured.

        Args:
            user_id: The user to generate a reset link for

        Returns:
            The full reset URL, or None if user not found
        """
        from services.email_service import APP_BASE_URL

        user = self.db.users.find_one({
            "user_id": user_id,
            "status": {"$in": ["active", None]}
        })

        if not user:
            return None

        result = await self.create_reset_token(user["email"], "admin-generated")
        if not result:
            return None

        return f"{APP_BASE_URL}/reset-password?token={result['token']}"

    async def validate_token_only(self, token: str) -> dict:
        """
        Validate a reset token without consuming it.
        Used by the frontend to check if a token is valid before showing the form.

        Args:
            token: The plaintext token from the email link

        Returns:
            dict with valid bool
        """
        token_hash = self._hash_token(token)
        now = datetime.now(timezone.utc)

        token_doc = self.db.password_reset_tokens.find_one({
            "token_hash": token_hash,
            "used": False,
            "expires_at": {"$gt": now}
        })

        return {"valid": token_doc is not None}
