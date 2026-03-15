"""
InDE MVP v3.3 - Shared Pursuit Engine
Multi-user pursuit management with role-based access.

Pursuit Sharing Model:
- Owner: Creator or transferred. Full control.
- Editor: Can chat with coach, contribute elements, generate reports.
- Viewer: Read-only access to pursuit and reports.

Concurrent Context:
- Tracks active users per pursuit (last_active timestamps)
- Prevents conflicts through element-level attribution
- Maintains coaching session isolation while sharing scaffolding
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import logging

from database import db
from config import PURSUIT_ROLES, PURSUIT_ROLE_PERMISSIONS

logger = logging.getLogger("inde.teams.shared_pursuit")


class SharedPursuitEngine:
    """
    Manages shared pursuit lifecycle and team membership.

    Handles pursuit sharing, team management, and concurrent access tracking.
    """

    def __init__(self, event_dispatcher=None):
        """
        Initialize shared pursuit engine.

        Args:
            event_dispatcher: Optional event dispatcher for team events
        """
        self.db = db
        self.event_dispatcher = event_dispatcher

    async def share_pursuit(self, pursuit_id: str, owner_id: str,
                             team_members: List[Dict]) -> Dict:
        """
        Share a pursuit with team members.

        Args:
            pursuit_id: Pursuit to share
            owner_id: Current owner (must be requesting user)
            team_members: List of {user_id, role} dicts

        Returns:
            Updated sharing configuration

        Raises:
            PermissionError: If requester is not owner
            ValueError: If pursuit not found or invalid roles
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError("Pursuit not found")

        if pursuit.get("user_id") != owner_id:
            raise PermissionError("Only the owner can share this pursuit")

        # Validate roles
        for member in team_members:
            if member.get("role") not in PURSUIT_ROLES:
                raise ValueError(f"Invalid role: {member.get('role')}. Must be one of {PURSUIT_ROLES}")

        # Build sharing config
        sharing = {
            "is_shared": True,
            "shared_at": datetime.now(timezone.utc),
            "shared_by": owner_id,
            "team_members": []
        }

        for member in team_members:
            user_id = member.get("user_id")
            if user_id == owner_id:
                continue  # Skip owner, they're implicit

            # Verify user exists
            user = self.db.get_user(user_id)
            if not user:
                logger.warning(f"User {user_id} not found, skipping")
                continue

            sharing["team_members"].append({
                "user_id": user_id,
                "role": member.get("role", "viewer"),
                "joined_at": datetime.now(timezone.utc),
                "invited_by": owner_id,
                "last_active_at": None
            })

        # Update pursuit
        self.db.update_pursuit_sharing(pursuit_id, sharing)

        # Publish team.member.added events
        if self.event_dispatcher:
            for member in sharing["team_members"]:
                await self._publish_event("team.member.added", {
                    "pursuit_id": pursuit_id,
                    "user_id": member["user_id"],
                    "role": member["role"],
                    "invited_by": owner_id
                })

        logger.info(f"Shared pursuit {pursuit_id} with {len(sharing['team_members'])} members")

        return sharing

    async def add_team_member(self, pursuit_id: str, requester_id: str,
                               user_id: str, role: str = "editor") -> Dict:
        """
        Add a team member to a shared pursuit.

        Args:
            pursuit_id: Pursuit ID
            requester_id: User making the request (must be owner)
            user_id: User to add
            role: Role to grant (editor | viewer)

        Returns:
            Updated team member entry

        Raises:
            PermissionError: If requester is not owner
            ValueError: If user already on team or invalid role
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError("Pursuit not found")

        if pursuit.get("user_id") != requester_id:
            raise PermissionError("Only the owner can add team members")

        if role not in PURSUIT_ROLES:
            raise ValueError(f"Invalid role: {role}")

        # Check if user already on team
        sharing = pursuit.get("sharing", {})
        team_members = sharing.get("team_members", [])

        for member in team_members:
            if member.get("user_id") == user_id:
                raise ValueError("User is already a team member")

        # Add member
        self.db.add_pursuit_team_member(pursuit_id, user_id, role)

        # Publish event
        if self.event_dispatcher:
            await self._publish_event("team.member.added", {
                "pursuit_id": pursuit_id,
                "user_id": user_id,
                "role": role,
                "invited_by": requester_id
            })

        logger.info(f"Added {user_id} to pursuit {pursuit_id} as {role}")

        return {
            "user_id": user_id,
            "role": role,
            "joined_at": datetime.now(timezone.utc)
        }

    async def remove_team_member(self, pursuit_id: str, requester_id: str,
                                   user_id: str) -> None:
        """
        Remove a team member from a shared pursuit.

        Args:
            pursuit_id: Pursuit ID
            requester_id: User making the request (owner or self)
            user_id: User to remove

        Raises:
            PermissionError: If requester is not owner and not self
            ValueError: If user not on team
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError("Pursuit not found")

        is_owner = pursuit.get("user_id") == requester_id
        is_self = requester_id == user_id

        if not is_owner and not is_self:
            raise PermissionError("Only the owner can remove other team members")

        # Prevent owner from removing themselves
        if user_id == pursuit.get("user_id"):
            raise ValueError("Owner cannot be removed. Transfer ownership first.")

        # Check if user is on team
        sharing = pursuit.get("sharing", {})
        team_members = sharing.get("team_members", [])

        member_found = False
        for member in team_members:
            if member.get("user_id") == user_id:
                member_found = True
                break

        if not member_found:
            raise ValueError("User is not a team member")

        # Remove member
        self.db.remove_pursuit_team_member(pursuit_id, user_id)

        # Publish event
        if self.event_dispatcher:
            await self._publish_event("team.member.departed", {
                "pursuit_id": pursuit_id,
                "user_id": user_id,
                "departure_type": "self" if is_self else "removed"
            })

        logger.info(f"Removed {user_id} from pursuit {pursuit_id}")

    async def change_member_role(self, pursuit_id: str, owner_id: str,
                                   user_id: str, new_role: str) -> Dict:
        """
        Change a team member's role.

        Args:
            pursuit_id: Pursuit ID
            owner_id: Owner making the change
            user_id: User whose role is changing
            new_role: New role

        Returns:
            Updated member entry

        Raises:
            PermissionError: If requester is not owner
            ValueError: If invalid role or user not found
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError("Pursuit not found")

        if pursuit.get("user_id") != owner_id:
            raise PermissionError("Only the owner can change roles")

        if new_role not in PURSUIT_ROLES:
            raise ValueError(f"Invalid role: {new_role}")

        if user_id == pursuit.get("user_id"):
            raise ValueError("Cannot change owner's role. Use transfer ownership instead.")

        # Update role
        success = self.db.update_pursuit_team_member_role(pursuit_id, user_id, new_role)
        if not success:
            raise ValueError("User is not a team member")

        # Publish event
        if self.event_dispatcher:
            await self._publish_event("team.role.changed", {
                "pursuit_id": pursuit_id,
                "user_id": user_id,
                "new_role": new_role
            })

        logger.info(f"Changed role for {user_id} in pursuit {pursuit_id} to {new_role}")

        return {
            "user_id": user_id,
            "role": new_role
        }

    async def transfer_ownership(self, pursuit_id: str, current_owner_id: str,
                                   new_owner_id: str) -> None:
        """
        Transfer pursuit ownership to another team member.

        Args:
            pursuit_id: Pursuit ID
            current_owner_id: Current owner
            new_owner_id: New owner (must be current team member)

        Raises:
            PermissionError: If requester is not owner
            ValueError: If new owner not on team
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError("Pursuit not found")

        if pursuit.get("user_id") != current_owner_id:
            raise PermissionError("Only the current owner can transfer ownership")

        # Verify new owner is on team
        sharing = pursuit.get("sharing", {})
        team_members = sharing.get("team_members", [])

        new_owner_found = False
        for member in team_members:
            if member.get("user_id") == new_owner_id:
                new_owner_found = True
                break

        if not new_owner_found:
            raise ValueError("New owner must be a current team member")

        # Transfer ownership
        # 1. Change pursuit user_id
        self.db.update_pursuit(pursuit_id, {"user_id": new_owner_id})

        # 2. Remove new owner from team_members (they're now implicit owner)
        self.db.remove_pursuit_team_member(pursuit_id, new_owner_id)

        # 3. Add old owner as editor
        self.db.add_pursuit_team_member(pursuit_id, current_owner_id, "editor")

        logger.info(f"Transferred ownership of {pursuit_id} from {current_owner_id} to {new_owner_id}")

    def get_team_members(self, pursuit_id: str) -> List[Dict]:
        """
        Get all team members for a pursuit.

        Returns list including implicit owner.
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return []

        owner_id = pursuit.get("user_id")
        owner = self.db.get_user(owner_id)

        members = [{
            "user_id": owner_id,
            "user_name": owner.get("name") if owner else "Unknown",
            "role": "owner",
            "joined_at": pursuit.get("created_at"),
            "is_owner": True
        }]

        sharing = pursuit.get("sharing", {})
        for member in sharing.get("team_members", []):
            user = self.db.get_user(member.get("user_id"))
            members.append({
                "user_id": member.get("user_id"),
                "user_name": user.get("name") if user else "Unknown",
                "role": member.get("role"),
                "joined_at": member.get("joined_at"),
                "last_active_at": member.get("last_active_at"),
                "is_owner": False
            })

        return members

    def get_active_users(self, pursuit_id: str, window_minutes: int = 15) -> List[str]:
        """
        Get users active in pursuit within time window.

        Args:
            pursuit_id: Pursuit ID
            window_minutes: Activity window (default 15 min)

        Returns:
            List of user IDs
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        active = []

        # Check owner's last activity
        owner_active = pursuit.get("last_activity_at")
        if owner_active and owner_active > cutoff:
            active.append(pursuit.get("user_id"))

        # Check team members
        sharing = pursuit.get("sharing", {})
        for member in sharing.get("team_members", []):
            last_active = member.get("last_active_at")
            if last_active and last_active > cutoff:
                active.append(member.get("user_id"))

        return active

    def record_user_activity(self, pursuit_id: str, user_id: str) -> None:
        """
        Record user activity timestamp for concurrent tracking.

        Args:
            pursuit_id: Pursuit ID
            user_id: Active user
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return

        now = datetime.now(timezone.utc)

        if pursuit.get("user_id") == user_id:
            # Update owner's activity on pursuit
            self.db.update_pursuit(pursuit_id, {"last_activity_at": now})
        else:
            # Update team member's last_active_at
            self.db.db.pursuits.update_one(
                {"pursuit_id": pursuit_id, "sharing.team_members.user_id": user_id},
                {"$set": {"sharing.team_members.$.last_active_at": now}}
            )

    async def mark_pursuit_as_practice(self, pursuit_id: str, owner_id: str,
                                         is_practice: bool) -> None:
        """
        Mark/unmark a pursuit as practice (affects maturity weighting).

        Practice pursuits:
        - Have 50% maturity weight
        - Are excluded from IKF federation
        - Are clearly labeled in UI

        Args:
            pursuit_id: Pursuit ID
            owner_id: Owner making the change
            is_practice: True to mark as practice
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError("Pursuit not found")

        if pursuit.get("user_id") != owner_id:
            raise PermissionError("Only the owner can mark practice status")

        self.db.set_pursuit_practice_flag(pursuit_id, is_practice)

        logger.info(f"Pursuit {pursuit_id} practice status: {is_practice}")

    def get_user_role_in_pursuit(self, pursuit_id: str, user_id: str) -> Optional[str]:
        """
        Get user's role in a pursuit.

        Returns:
            Role string (owner | editor | viewer) or None
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        if pursuit.get("user_id") == user_id:
            return "owner"

        sharing = pursuit.get("sharing", {})
        for member in sharing.get("team_members", []):
            if member.get("user_id") == user_id:
                return member.get("role")

        return None

    def get_user_permissions(self, pursuit_id: str, user_id: str) -> Dict:
        """
        Get user's permissions for a pursuit.

        Returns:
            Permission dict from PURSUIT_ROLE_PERMISSIONS
        """
        role = self.get_user_role_in_pursuit(pursuit_id, user_id)
        if not role:
            return {}
        return PURSUIT_ROLE_PERMISSIONS.get(role, {})

    async def _publish_event(self, event_type: str, payload: Dict) -> None:
        """Publish event to Redis Streams."""
        if self.event_dispatcher:
            try:
                await self.event_dispatcher.emit(event_type, payload)
            except Exception as e:
                logger.warning(f"Failed to publish event {event_type}: {e}")


# Singleton instance
shared_pursuit_engine = SharedPursuitEngine()
