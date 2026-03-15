"""
InDE v3.11 - Timeline Milestone Permission Enforcement

Rules:
- Solo pursuits: requesting user is always the creator. All checks pass.
- Team pursuits: only the pursuit creator may make structural milestone changes.
  Structural changes: update target_date, update milestone_type, update title,
                      delete milestone.
  Non-structural (permitted to all team members):
  - Mark status: completed (if assigned or creator)
  - Add completion_notes

Usage:
    await require_milestone_edit_permission(user_id, pursuit_id, db)
    # Raises HTTP 403 if permission denied.
    # Returns silently if permitted.

TD-014: Team Pursuit Milestone Permissions
"""

import logging
from typing import Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def get_pursuit_owner(pursuit_id: str, db) -> Optional[str]:
    """
    Return the owner/creator user_id for a pursuit.
    Checks common field names: created_by, owner_id, user_id.
    Returns None if pursuit not found or owner field absent.

    Args:
        pursuit_id: ID of the pursuit
        db: Database instance
    """
    pursuit = db.db.pursuits.find_one(
        {"pursuit_id": pursuit_id},
        {"created_by": 1, "owner_id": 1, "user_id": 1, "team_mode": 1, "team_members": 1}
    )
    if not pursuit:
        return None
    return (
        pursuit.get("created_by") or
        pursuit.get("owner_id") or
        pursuit.get("user_id")
    )


def is_team_pursuit(pursuit_id: str, db) -> bool:
    """Return True if this pursuit has team members (team mode enabled)."""
    pursuit = db.db.pursuits.find_one(
        {"pursuit_id": pursuit_id},
        {"team_mode": 1, "team_members": 1}
    )
    if not pursuit:
        return False
    if pursuit.get("team_mode") is True:
        return True
    members = pursuit.get("team_members", [])
    return isinstance(members, list) and len(members) > 0


def require_milestone_edit_permission(
    requesting_user_id: str,
    pursuit_id: str,
    db
) -> None:
    """
    Raise HTTP 403 if the requesting user does not have permission to make
    structural changes to milestones in the given pursuit.

    For solo pursuits: always permitted (short-circuit).
    For team pursuits: only the pursuit creator is permitted.

    Args:
        requesting_user_id: The user attempting the operation.
        pursuit_id: The pursuit containing the milestone.
        db: Database instance.

    Raises:
        HTTPException(403) if permission denied.
    """

    # Short-circuit for solo pursuits — no permission overhead
    if not is_team_pursuit(pursuit_id, db):
        return

    owner_id = get_pursuit_owner(pursuit_id, db)

    if owner_id is None:
        # Pursuit not found or owner unknown — fail open (log warning, permit)
        logger.warning(
            f"Could not determine owner for pursuit {pursuit_id}. "
            f"Permitting edit by user {requesting_user_id}."
        )
        return

    if str(requesting_user_id) != str(owner_id):
        logger.info(
            f"Milestone edit denied: user {requesting_user_id} is not creator "
            f"({owner_id}) of team pursuit {pursuit_id}."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "milestone_edit_not_permitted",
                "message": "Only the pursuit creator can change milestone dates, types, or delete milestones.",
                "pursuit_id": pursuit_id,
                "owner_id": owner_id
            }
        )

    # Requesting user is the creator — permit
    return


def require_milestone_complete_permission(
    requesting_user_id: str,
    pursuit_id: str,
    milestone: dict,
    db
) -> None:
    """
    Marking a milestone complete is permitted to:
    - The pursuit creator
    - The user assigned to the milestone (if milestone.assigned_to is set)
    - Any team member if milestone.assigned_to is None (unassigned)

    Raises HTTPException(403) only when: team pursuit, milestone is assigned
    to a specific user, and requesting user is neither that user nor the creator.
    """

    if not is_team_pursuit(pursuit_id, db):
        return

    owner_id = get_pursuit_owner(pursuit_id, db)
    assigned_to = milestone.get("assigned_to")

    # Creator can always mark complete
    if owner_id and str(requesting_user_id) == str(owner_id):
        return

    # Unassigned milestone — any team member can mark complete
    if not assigned_to:
        return

    # Assigned milestone — only assigned user or creator
    if str(requesting_user_id) != str(assigned_to):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "milestone_complete_not_permitted",
                "message": "This milestone is assigned to another team member.",
            }
        )


def check_can_edit_milestone(user_id: str, pursuit_id: str, db) -> dict:
    """
    Check if user can edit milestones (non-exception version for UI).

    Returns:
        {
            "can_edit": bool,
            "reason": str or None,
            "is_creator": bool,
            "is_team_pursuit": bool
        }
    """
    is_team = is_team_pursuit(pursuit_id, db)

    if not is_team:
        return {
            "can_edit": True,
            "reason": None,
            "is_creator": True,
            "is_team_pursuit": False
        }

    owner_id = get_pursuit_owner(pursuit_id, db)
    is_creator = owner_id and str(user_id) == str(owner_id)

    if is_creator:
        return {
            "can_edit": True,
            "reason": None,
            "is_creator": True,
            "is_team_pursuit": True
        }

    return {
        "can_edit": False,
        "reason": "Only the pursuit creator can edit milestone dates and structure.",
        "is_creator": False,
        "is_team_pursuit": True
    }
