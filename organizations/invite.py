"""
InDE MVP v3.3 - Invite Service
Token-based organization invitation management.

Token Flow:
1. Admin/member generates invite token with role + expiry + max_uses
2. Token is shareable link (e.g., /join/inde_abc123xyz)
3. New user redeems token -> creates pending membership
4. User accepts -> active membership

Security:
- Tokens expire after configurable days (default: 7)
- Tokens have use count limits
- Tokens can be revoked by admins
- Tokens cannot grant admin role (direct invite only)
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
import logging

from database import db
from config import TEAM_CONFIG
from organizations.models import InviteCreate, InviteResponse, InviteToken

logger = logging.getLogger("inde.organizations.invite")


class InviteService:
    """
    Token-based invitation management.

    Handles token generation, validation, redemption, and revocation.
    """

    # Token prefix for identification
    TOKEN_PREFIX = "inde_"
    TOKEN_LENGTH = 24  # Total length of random portion

    def __init__(self):
        """Initialize invite service."""
        self.db = db
        self.default_expiry_days = TEAM_CONFIG.get("invite_token_expiry_days", 7)

    def generate_token(self, org_id: str, creator_id: str,
                        invite_data: InviteCreate) -> InviteResponse:
        """
        Generate new invite token.

        Args:
            org_id: Organization ID
            creator_id: User creating the token
            invite_data: Token configuration

        Returns:
            Invite token response

        Raises:
            PermissionError: If creator lacks invite permission
        """
        # Verify creator has invite permission
        membership = self.db.get_user_membership_in_org(creator_id, org_id)
        if not membership or membership.get("status") != "active":
            raise PermissionError("You are not a member of this organization")

        if not membership.get("permissions", {}).get("can_invite_members", False):
            raise PermissionError("You do not have permission to generate invite tokens")

        # Generate secure random token
        random_part = secrets.token_urlsafe(self.TOKEN_LENGTH)
        token = f"{self.TOKEN_PREFIX}{random_part}"

        # Calculate expiry
        expires_at = datetime.now(timezone.utc) + timedelta(days=invite_data.expires_in_days)

        # Create token record
        token_record = {
            "token": token,
            "org_id": org_id,
            "role": invite_data.role,
            "created_by": creator_id,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "max_uses": invite_data.max_uses,
            "current_uses": 0,
            "used_by": [],
            "revoked": False
        }

        # Store in system_config collection as invite_tokens
        # Using a dedicated namespace to separate from other config
        self.db.db.system_config.insert_one({
            "key": f"invite_token:{token}",
            "value": token_record,
            "created_at": datetime.now(timezone.utc)
        })

        logger.info(f"Generated invite token for org {org_id} by user {creator_id}")

        return InviteResponse(
            token=token,
            org_id=org_id,
            role=invite_data.role,
            created_by=creator_id,
            created_at=token_record["created_at"],
            expires_at=expires_at,
            max_uses=invite_data.max_uses,
            current_uses=0
        )

    def validate_token(self, token: str) -> Optional[InviteToken]:
        """
        Validate invite token.

        Args:
            token: Token string

        Returns:
            Token data if valid, None if invalid/expired/exhausted
        """
        # Look up token
        record = self.db.db.system_config.find_one({"key": f"invite_token:{token}"})
        if not record:
            logger.debug(f"Token not found: {token[:20]}...")
            return None

        token_data = record.get("value", {})

        # Check revoked
        if token_data.get("revoked", False):
            logger.debug(f"Token revoked: {token[:20]}...")
            return None

        # Check expiry
        expires_at = token_data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if expires_at and expires_at < datetime.now(timezone.utc):
            logger.debug(f"Token expired: {token[:20]}...")
            return None

        # Check use count
        if token_data.get("current_uses", 0) >= token_data.get("max_uses", 1):
            logger.debug(f"Token exhausted: {token[:20]}...")
            return None

        return InviteToken(**token_data)

    def redeem_token(self, token: str, user_id: str) -> Dict:
        """
        Redeem invite token for user.

        Args:
            token: Token string
            user_id: User redeeming the token

        Returns:
            Created membership info

        Raises:
            ValueError: If token invalid/expired/exhausted or user already member
        """
        # Validate token
        token_data = self.validate_token(token)
        if not token_data:
            raise ValueError("Invalid or expired invitation token")

        org_id = token_data.org_id

        # Check if user already has membership
        existing = self.db.get_user_membership_in_org(user_id, org_id)
        if existing:
            status = existing.get("status")
            if status == "active":
                raise ValueError("You are already a member of this organization")
            elif status == "pending":
                raise ValueError("You already have a pending invitation")

        # Check if user already used this token
        if user_id in token_data.used_by:
            raise ValueError("You have already used this invitation token")

        # Create pending membership
        membership_data = {
            "org_id": org_id,
            "user_id": user_id,
            "role": token_data.role,
            "invited_by": token_data.created_by,
            "status": "pending",
            "permissions": {
                "can_create_pursuits": True,
                "can_invite_members": token_data.role == "member",
                "can_manage_org_settings": False,
                "can_review_ikf_contributions": False
            }
        }
        membership_id = self.db.create_membership(membership_data)

        # Update token usage
        self.db.db.system_config.update_one(
            {"key": f"invite_token:{token}"},
            {
                "$inc": {"value.current_uses": 1},
                "$push": {"value.used_by": user_id}
            }
        )

        logger.info(f"Token redeemed by user {user_id} for org {org_id}")

        return {
            "membership_id": membership_id,
            "org_id": org_id,
            "role": token_data.role,
            "status": "pending"
        }

    def revoke_token(self, token: str, revoker_id: str) -> bool:
        """
        Revoke an invite token.

        Args:
            token: Token string
            revoker_id: Admin user revoking

        Returns:
            True if revoked successfully

        Raises:
            PermissionError: If revoker is not admin
            ValueError: If token not found
        """
        # Look up token
        record = self.db.db.system_config.find_one({"key": f"invite_token:{token}"})
        if not record:
            raise ValueError("Token not found")

        token_data = record.get("value", {})
        org_id = token_data.get("org_id")

        # Verify admin role
        membership = self.db.get_user_membership_in_org(revoker_id, org_id)
        if not membership or membership.get("role") != "admin":
            raise PermissionError("Only admins can revoke invite tokens")

        # Revoke token
        result = self.db.db.system_config.update_one(
            {"key": f"invite_token:{token}"},
            {"$set": {
                "value.revoked": True,
                "value.revoked_at": datetime.now(timezone.utc),
                "value.revoked_by": revoker_id
            }}
        )

        logger.info(f"Token revoked by admin {revoker_id} for org {org_id}")

        return result.modified_count > 0

    def list_org_tokens(self, org_id: str, user_id: str,
                         include_expired: bool = False) -> List[InviteResponse]:
        """
        List invite tokens for an organization.

        Args:
            org_id: Organization ID
            user_id: Requesting user ID
            include_expired: Include expired/revoked tokens

        Returns:
            List of invite tokens

        Raises:
            PermissionError: If user is not admin
        """
        # Verify admin role
        membership = self.db.get_user_membership_in_org(user_id, org_id)
        if not membership or membership.get("role") != "admin":
            raise PermissionError("Only admins can list invite tokens")

        # Find all tokens for org
        # Using a query pattern since we stored with key prefix
        all_records = list(self.db.db.system_config.find({"key": {"$regex": "^invite_token:"}}))

        tokens = []
        for record in all_records:
            token_data = record.get("value", {})
            if token_data.get("org_id") != org_id:
                continue

            # Filter out expired/revoked unless requested
            if not include_expired:
                if token_data.get("revoked", False):
                    continue
                expires_at = token_data.get("expires_at")
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expires_at and expires_at < datetime.now(timezone.utc):
                    continue
                if token_data.get("current_uses", 0) >= token_data.get("max_uses", 1):
                    continue

            tokens.append(InviteResponse(
                token=token_data.get("token"),
                org_id=org_id,
                role=token_data.get("role"),
                created_by=token_data.get("created_by"),
                created_at=token_data.get("created_at"),
                expires_at=token_data.get("expires_at"),
                max_uses=token_data.get("max_uses", 1),
                current_uses=token_data.get("current_uses", 0)
            ))

        return tokens

    def get_org_from_token(self, token: str) -> Optional[Dict]:
        """
        Get organization info from token (for pre-join preview).

        Args:
            token: Token string

        Returns:
            Basic org info if token valid, None otherwise
        """
        token_data = self.validate_token(token)
        if not token_data:
            return None

        org = self.db.get_organization(token_data.org_id)
        if not org:
            return None

        return {
            "org_id": org.get("org_id"),
            "org_name": org.get("name"),
            "org_description": org.get("description"),
            "role_offered": token_data.role
        }


# Singleton instance
invite_service = InviteService()
