"""
InDE MVP v3.3 - Organization Service
Organization lifecycle management and membership operations.

Organization states: CREATED -> ACTIVE -> SUSPENDED -> ARCHIVED
- CREATED: Creator becomes admin. Org has no other members.
- ACTIVE: At least one member beyond the creator.
- SUSPENDED: Admin action. View-only. IKF paused.
- ARCHIVED: Read-only. Historical data preserved.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from database import db
from organizations.models import (
    Organization, OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    Membership, MembershipCreate, MembershipResponse,
    OrganizationSettings, OrganizationStats, MemberPermissions,
    generate_slug
)

logger = logging.getLogger("inde.organizations.service")


class OrganizationService:
    """
    Organization lifecycle management.

    Handles organization CRUD, membership lifecycle, and org state transitions.
    Publishes events to Redis Streams for team activity tracking.
    """

    def __init__(self, event_dispatcher=None):
        """
        Initialize organization service.

        Args:
            event_dispatcher: Optional event dispatcher for publishing team events
        """
        self.db = db
        self.event_dispatcher = event_dispatcher

    async def create_organization(self, user_id: str,
                                    org_data: OrganizationCreate) -> OrganizationResponse:
        """
        Create a new organization. Creator becomes admin.

        Args:
            user_id: ID of the creating user (becomes admin)
            org_data: Organization creation data

        Returns:
            Created organization with creator's membership

        Raises:
            ValueError: If slug already exists
        """
        # Generate URL-safe slug from name
        base_slug = generate_slug(org_data.name)
        slug = base_slug

        # Ensure slug uniqueness by appending counter if needed
        counter = 1
        while self.db.get_organization_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Prepare organization data
        settings = org_data.settings or OrganizationSettings()
        org_dict = {
            "name": org_data.name,
            "slug": slug,
            "description": org_data.description,
            "created_by": user_id,
            "settings": settings.model_dump()
        }

        # Create organization
        org_id = self.db.create_organization(org_dict)
        logger.info(f"Created organization '{org_data.name}' with ID {org_id}")

        # Create admin membership for creator
        membership_data = {
            "org_id": org_id,
            "user_id": user_id,
            "role": "admin",
            "invited_by": user_id,  # Self-invited (creator)
            "status": "active",
            "permissions": {
                "can_create_pursuits": True,
                "can_invite_members": True,
                "can_manage_org_settings": True,
                "can_review_ikf_contributions": True
            }
        }
        self.db.create_membership(membership_data)

        # Publish org.created event
        if self.event_dispatcher:
            await self._publish_event("org.created", {
                "org_id": org_id,
                "org_name": org_data.name,
                "created_by": user_id
            })

        # Return organization
        org = self.db.get_organization(org_id)
        return self._to_response(org, user_role="admin")

    async def get_organization(self, org_id: str,
                                user_id: str) -> Optional[OrganizationResponse]:
        """
        Get organization details. Verify user is a member.

        Args:
            org_id: Organization ID
            user_id: Requesting user ID

        Returns:
            Organization with user's role, or None if not found/not a member
        """
        org = self.db.get_organization(org_id)
        if not org:
            return None

        # Check user membership
        membership = self.db.get_user_membership_in_org(user_id, org_id)
        if not membership or membership.get("status") != "active":
            return None

        return self._to_response(org, user_role=membership.get("role"))

    async def list_user_organizations(self, user_id: str) -> List[OrganizationResponse]:
        """
        List all organizations user belongs to (active memberships).

        Args:
            user_id: User ID

        Returns:
            List of organizations with user's roles
        """
        orgs = self.db.get_user_organizations(user_id)
        return [self._to_response(org, user_role=org.get("user_role")) for org in orgs]

    async def update_organization(self, org_id: str, user_id: str,
                                    updates: OrganizationUpdate) -> Optional[OrganizationResponse]:
        """
        Update organization settings. Requires admin role.

        Args:
            org_id: Organization ID
            user_id: Requesting user ID
            updates: Fields to update

        Returns:
            Updated organization, or None if not found/unauthorized

        Raises:
            PermissionError: If user is not admin
        """
        # Verify admin role
        membership = self.db.get_user_membership_in_org(user_id, org_id)
        if not membership or membership.get("role") != "admin":
            raise PermissionError("Only admins can update organization settings")

        # Build update dict (only non-None values)
        update_dict = {}
        if updates.name is not None:
            update_dict["name"] = updates.name
        if updates.description is not None:
            update_dict["description"] = updates.description
        if updates.settings is not None:
            update_dict["settings"] = updates.settings.model_dump()
        if updates.status is not None:
            update_dict["status"] = updates.status

        if update_dict:
            self.db.update_organization(org_id, update_dict)
            logger.info(f"Updated organization {org_id}: {list(update_dict.keys())}")

        org = self.db.get_organization(org_id)
        return self._to_response(org, user_role="admin")

    async def invite_member(self, org_id: str, inviter_id: str,
                             invite_data: MembershipCreate) -> MembershipResponse:
        """
        Invite user to organization. Direct add by user_id.

        Args:
            org_id: Organization ID
            inviter_id: Inviting user's ID
            invite_data: Membership creation data

        Returns:
            Created membership (pending status)

        Raises:
            PermissionError: If inviter lacks invite permission
            ValueError: If user already has membership
        """
        # Verify inviter has invite permission
        inviter_membership = self.db.get_user_membership_in_org(inviter_id, org_id)
        if not inviter_membership:
            raise PermissionError("You are not a member of this organization")

        if not inviter_membership.get("permissions", {}).get("can_invite_members", False):
            raise PermissionError("You do not have permission to invite members")

        # Check if target user already has membership
        existing = self.db.get_user_membership_in_org(invite_data.user_id, org_id)
        if existing:
            status = existing.get("status")
            if status == "active":
                raise ValueError("User is already a member of this organization")
            elif status == "pending":
                raise ValueError("User already has a pending invitation")
            # If departed, allow re-invite

        # Determine permissions based on role
        permissions = invite_data.permissions
        if not permissions:
            permissions = MemberPermissions(
                can_create_pursuits=True,
                can_invite_members=invite_data.role in ["admin", "member"],
                can_manage_org_settings=invite_data.role == "admin",
                can_review_ikf_contributions=invite_data.role == "admin"
            )

        # Create pending membership
        membership_dict = {
            "org_id": org_id,
            "user_id": invite_data.user_id,
            "role": invite_data.role,
            "invited_by": inviter_id,
            "status": "pending",
            "permissions": permissions.model_dump()
        }
        membership_id = self.db.create_membership(membership_dict)

        logger.info(f"Created invitation for user {invite_data.user_id} to org {org_id}")

        membership = self.db.get_membership(membership_id)
        return self._membership_to_response(membership)

    async def accept_invitation(self, user_id: str, org_id: str) -> MembershipResponse:
        """
        Accept pending membership invitation.

        Args:
            user_id: User accepting invitation
            org_id: Organization ID

        Returns:
            Updated membership (active status)

        Raises:
            ValueError: If no pending invitation exists
        """
        membership = self.db.get_user_membership_in_org(user_id, org_id)
        if not membership:
            raise ValueError("No invitation found for this organization")

        if membership.get("status") != "pending":
            raise ValueError(f"Invitation is {membership.get('status')}, not pending")

        # Accept invitation
        self.db.accept_membership(membership["membership_id"])

        # Update org stats
        self.db.increment_org_stat(org_id, "total_members", 1)

        # Check if org should transition to ACTIVE
        org = self.db.get_organization(org_id)
        if org and org.get("status") == "CREATED":
            members = self.db.get_org_members(org_id, status="active")
            if len(members) >= 2:
                self.db.update_organization(org_id, {"status": "ACTIVE"})
                logger.info(f"Organization {org_id} transitioned to ACTIVE")

        # Publish org.member.joined event
        if self.event_dispatcher:
            await self._publish_event("org.member.joined", {
                "org_id": org_id,
                "user_id": user_id,
                "role": membership.get("role")
            })

        logger.info(f"User {user_id} accepted invitation to org {org_id}")

        membership = self.db.get_user_membership_in_org(user_id, org_id)
        return self._membership_to_response(membership)

    async def update_member_role(self, org_id: str, admin_id: str,
                                   user_id: str, new_role: str) -> MembershipResponse:
        """
        Change member's organization role. Requires admin.

        Args:
            org_id: Organization ID
            admin_id: Admin user making the change
            user_id: User whose role is being changed
            new_role: New role (admin | member | viewer)

        Returns:
            Updated membership

        Raises:
            PermissionError: If requester is not admin
            ValueError: If role is invalid or user not found
        """
        # Verify admin role
        admin_membership = self.db.get_user_membership_in_org(admin_id, org_id)
        if not admin_membership or admin_membership.get("role") != "admin":
            raise PermissionError("Only admins can change member roles")

        # Validate new role
        if new_role not in ["admin", "member", "viewer"]:
            raise ValueError("Role must be admin, member, or viewer")

        # Get target membership
        membership = self.db.get_user_membership_in_org(user_id, org_id)
        if not membership or membership.get("status") != "active":
            raise ValueError("User is not an active member of this organization")

        # Prevent removing last admin
        if membership.get("role") == "admin" and new_role != "admin":
            admins = [m for m in self.db.get_org_members(org_id, status="active")
                      if m.get("role") == "admin"]
            if len(admins) <= 1:
                raise ValueError("Cannot demote the last admin")

        # Update role
        self.db.change_membership_role(membership["membership_id"], new_role)

        logger.info(f"Changed role for user {user_id} in org {org_id}: {membership.get('role')} -> {new_role}")

        membership = self.db.get_user_membership_in_org(user_id, org_id)
        return self._membership_to_response(membership)

    async def remove_member(self, org_id: str, requester_id: str,
                             user_id: str) -> None:
        """
        Remove member (admin action or self-departure).

        Args:
            org_id: Organization ID
            requester_id: User requesting removal
            user_id: User being removed

        Raises:
            PermissionError: If requester is not admin and not self
            ValueError: If trying to remove last admin
        """
        # Check if self-departure or admin action
        is_self = requester_id == user_id

        if not is_self:
            admin_membership = self.db.get_user_membership_in_org(requester_id, org_id)
            if not admin_membership or admin_membership.get("role") != "admin":
                raise PermissionError("Only admins can remove other members")

        # Get target membership
        membership = self.db.get_user_membership_in_org(user_id, org_id)
        if not membership or membership.get("status") != "active":
            raise ValueError("User is not an active member of this organization")

        # Prevent removing last admin
        if membership.get("role") == "admin":
            admins = [m for m in self.db.get_org_members(org_id, status="active")
                      if m.get("role") == "admin"]
            if len(admins) <= 1:
                raise ValueError("Cannot remove the last admin. Transfer admin role first.")

        # Mark as departed (soft delete)
        self.db.depart_membership(membership["membership_id"])

        # Update org stats
        self.db.increment_org_stat(org_id, "total_members", -1)

        # Publish team.member.departed event
        if self.event_dispatcher:
            await self._publish_event("team.member.departed", {
                "org_id": org_id,
                "user_id": user_id,
                "departure_type": "self" if is_self else "removed"
            })

        logger.info(f"Member {user_id} departed from org {org_id} ({'self' if is_self else 'removed'})")

    async def get_org_members(self, org_id: str, user_id: str,
                               status: str = "active") -> List[MembershipResponse]:
        """
        List organization members.

        Args:
            org_id: Organization ID
            user_id: Requesting user ID
            status: Filter by status (default: active)

        Returns:
            List of memberships

        Raises:
            PermissionError: If user is not a member
        """
        # Verify requester is a member
        membership = self.db.get_user_membership_in_org(user_id, org_id)
        if not membership or membership.get("status") != "active":
            raise PermissionError("You are not a member of this organization")

        members = self.db.get_org_members(org_id, status=status)
        return [self._membership_to_response(m) for m in members]

    def _to_response(self, org: Dict, user_role: str = None) -> OrganizationResponse:
        """Convert org dict to response model."""
        settings = OrganizationSettings(**(org.get("settings") or {}))
        stats = OrganizationStats(**(org.get("stats") or {}))

        return OrganizationResponse(
            org_id=org.get("org_id"),
            name=org.get("name"),
            slug=org.get("slug"),
            description=org.get("description", ""),
            status=org.get("status", "CREATED"),
            created_at=org.get("created_at"),
            updated_at=org.get("updated_at"),
            settings=settings,
            stats=stats,
            user_role=user_role
        )

    def _membership_to_response(self, membership: Dict) -> MembershipResponse:
        """Convert membership dict to response model."""
        permissions = MemberPermissions(**(membership.get("permissions") or {}))

        # Try to get user details
        user = self.db.get_user(membership.get("user_id"))
        user_name = user.get("name") if user else None
        user_email = user.get("email") if user else None

        return MembershipResponse(
            membership_id=membership.get("membership_id"),
            org_id=membership.get("org_id"),
            user_id=membership.get("user_id"),
            role=membership.get("role"),
            status=membership.get("status"),
            invited_at=membership.get("invited_at"),
            accepted_at=membership.get("accepted_at"),
            permissions=permissions,
            user_name=user_name,
            user_email=user_email
        )

    async def _publish_event(self, event_type: str, payload: Dict) -> None:
        """Publish event to Redis Streams."""
        if self.event_dispatcher:
            try:
                await self.event_dispatcher.emit(event_type, payload)
            except Exception as e:
                logger.warning(f"Failed to publish event {event_type}: {e}")
