"""
InDE v3.3 - Teams API Routes
Handles shared pursuit management and team collaboration.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from auth.middleware import get_current_user

router = APIRouter()


# ===========================================================================
# REQUEST/RESPONSE MODELS
# ===========================================================================

class TeamMemberRequest(BaseModel):
    user_id: str
    role: str = Field(default="editor", pattern="^(editor|viewer)$")


class SharePursuitRequest(BaseModel):
    team_members: List[TeamMemberRequest]


class TeamMemberResponse(BaseModel):
    user_id: str
    user_name: Optional[str] = None
    role: str
    joined_at: datetime
    last_active_at: Optional[datetime] = None
    is_owner: bool


class ChangeRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(owner|editor|viewer)$")


class TransferOwnershipRequest(BaseModel):
    new_owner_id: str


class PracticeStatusRequest(BaseModel):
    is_practice: bool


class ActivityEventResponse(BaseModel):
    event_id: str
    event_type: str
    pursuit_id: str
    org_id: Optional[str] = None
    actor_id: str
    actor_name: Optional[str] = None
    timestamp: datetime
    summary: str
    details: dict
    mentions: List[str]
    is_read: bool


# ===========================================================================
# SHARED PURSUIT ENDPOINTS
# ===========================================================================

@router.post("/pursuits/{pursuit_id}/share", status_code=201)
async def share_pursuit(
    pursuit_id: str,
    data: SharePursuitRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Share a pursuit with team members.

    Only the owner can share a pursuit.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from teams.shared_pursuit_engine import SharedPursuitEngine

    engine = SharedPursuitEngine()

    # Convert to list of dicts
    team_members = [m.model_dump() for m in data.team_members]

    try:
        sharing = await engine.share_pursuit(
            pursuit_id, current_user["user_id"], team_members
        )
        return {"status": "shared", "sharing": sharing}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pursuits/{pursuit_id}/team", response_model=List[TeamMemberResponse])
async def get_team_members(
    pursuit_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get all team members for a pursuit."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from teams.shared_pursuit_engine import SharedPursuitEngine
    from middleware.rbac import get_user_pursuit_context

    # Verify access
    context = get_user_pursuit_context(current_user["user_id"], pursuit_id)
    if not context:
        raise HTTPException(status_code=403, detail="No access to this pursuit")

    engine = SharedPursuitEngine()
    return engine.get_team_members(pursuit_id)


@router.post("/pursuits/{pursuit_id}/team", response_model=TeamMemberResponse, status_code=201)
async def add_team_member(
    pursuit_id: str,
    data: TeamMemberRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Add a team member to a shared pursuit. Owner only."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from teams.shared_pursuit_engine import SharedPursuitEngine

    engine = SharedPursuitEngine()

    try:
        member = await engine.add_team_member(
            pursuit_id, current_user["user_id"], data.user_id, data.role
        )
        return TeamMemberResponse(
            user_id=member["user_id"],
            user_name=None,
            role=member["role"],
            joined_at=member["joined_at"],
            last_active_at=None,
            is_owner=False
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/pursuits/{pursuit_id}/team/{user_id}", status_code=204)
async def remove_team_member(
    pursuit_id: str,
    user_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a team member from a shared pursuit.

    Owner can remove anyone. Members can remove themselves.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from teams.shared_pursuit_engine import SharedPursuitEngine

    engine = SharedPursuitEngine()

    try:
        await engine.remove_team_member(pursuit_id, current_user["user_id"], user_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/pursuits/{pursuit_id}/team/{user_id}/role")
async def change_team_member_role(
    pursuit_id: str,
    user_id: str,
    data: ChangeRoleRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Change a team member's role. Owner only."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from teams.shared_pursuit_engine import SharedPursuitEngine

    engine = SharedPursuitEngine()

    try:
        result = await engine.change_member_role(
            pursuit_id, current_user["user_id"], user_id, data.role
        )
        return {"status": "updated", **result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pursuits/{pursuit_id}/transfer-ownership")
async def transfer_ownership(
    pursuit_id: str,
    data: TransferOwnershipRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Transfer pursuit ownership to another team member.

    Current owner becomes editor.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from teams.shared_pursuit_engine import SharedPursuitEngine

    engine = SharedPursuitEngine()

    try:
        await engine.transfer_ownership(
            pursuit_id, current_user["user_id"], data.new_owner_id
        )
        return {"status": "transferred", "new_owner_id": data.new_owner_id}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/pursuits/{pursuit_id}/practice")
async def set_practice_status(
    pursuit_id: str,
    data: PracticeStatusRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark/unmark pursuit as practice.

    Practice pursuits have 50% maturity weight and are excluded from IKF.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from teams.shared_pursuit_engine import SharedPursuitEngine

    engine = SharedPursuitEngine()

    try:
        await engine.mark_pursuit_as_practice(
            pursuit_id, current_user["user_id"], data.is_practice
        )
        return {"status": "updated", "is_practice": data.is_practice}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===========================================================================
# ACTIVITY STREAM ENDPOINTS
# ===========================================================================

@router.get("/pursuits/{pursuit_id}/activity", response_model=List[ActivityEventResponse])
async def get_pursuit_activity(
    pursuit_id: str,
    limit: int = 50,
    offset: int = 0,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """Get activity stream for a pursuit."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from middleware.rbac import get_user_pursuit_context
    from core.database import db

    # Verify access
    context = get_user_pursuit_context(current_user["user_id"], pursuit_id)
    if not context:
        raise HTTPException(status_code=403, detail="No access to this pursuit")

    events = db.get_pursuit_activity(pursuit_id, limit, offset)

    # Mark which events are read by current user
    result = []
    for event in events:
        payload = event.get("payload", {})
        actor = db.get_user(event.get("actor_id"))
        result.append(ActivityEventResponse(
            event_id=event.get("event_id"),
            event_type=event.get("event_type"),
            pursuit_id=event.get("pursuit_id"),
            org_id=event.get("org_id"),
            actor_id=event.get("actor_id"),
            actor_name=actor.get("name") if actor else None,
            timestamp=event.get("timestamp"),
            summary=payload.get("summary", ""),
            details=payload.get("details", {}),
            mentions=payload.get("mentions", []),
            is_read=current_user["user_id"] in event.get("read_by", [])
        ))

    return result


@router.get("/organizations/{org_id}/activity", response_model=List[ActivityEventResponse])
async def get_org_activity(
    org_id: str,
    limit: int = 50,
    offset: int = 0,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """Get activity stream for an organization."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from middleware.rbac import check_org_permission
    from core.database import db

    # Verify membership
    membership = db.get_user_membership_in_org(current_user["user_id"], org_id)
    if not membership or membership.get("status") != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    events = db.get_org_activity(org_id, limit, offset)

    result = []
    for event in events:
        payload = event.get("payload", {})
        actor = db.get_user(event.get("actor_id"))
        result.append(ActivityEventResponse(
            event_id=event.get("event_id"),
            event_type=event.get("event_type"),
            pursuit_id=event.get("pursuit_id"),
            org_id=event.get("org_id"),
            actor_id=event.get("actor_id"),
            actor_name=actor.get("name") if actor else None,
            timestamp=event.get("timestamp"),
            summary=payload.get("summary", ""),
            details=payload.get("details", {}),
            mentions=payload.get("mentions", []),
            is_read=current_user["user_id"] in event.get("read_by", [])
        ))

    return result


@router.get("/notifications/mentions")
async def get_mentions(
    unread_only: bool = True,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """Get activity events that mention the current user."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from core.database import db

    events = db.get_user_mentions(current_user["user_id"], unread_only)

    result = []
    for event in events:
        payload = event.get("payload", {})
        actor = db.get_user(event.get("actor_id"))
        result.append(ActivityEventResponse(
            event_id=event.get("event_id"),
            event_type=event.get("event_type"),
            pursuit_id=event.get("pursuit_id"),
            org_id=event.get("org_id"),
            actor_id=event.get("actor_id"),
            actor_name=actor.get("name") if actor else None,
            timestamp=event.get("timestamp"),
            summary=payload.get("summary", ""),
            details=payload.get("details", {}),
            mentions=payload.get("mentions", []),
            is_read=current_user["user_id"] in event.get("read_by", [])
        ))

    return {"mentions": result, "unread_count": len([e for e in result if not e.is_read])}


@router.post("/notifications/mark-read")
async def mark_notifications_read(
    event_ids: List[str],
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Mark activity events as read."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from core.database import db

    count = db.mark_activity_read(event_ids, current_user["user_id"])
    return {"marked_read": count}


# ===========================================================================
# USER'S SHARED PURSUITS
# ===========================================================================

@router.get("/shared-pursuits")
async def list_shared_pursuits(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """List all pursuits the user is a team member of (not owner)."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from core.database import db

    shared = db.get_user_shared_pursuits(current_user["user_id"])

    # Filter out pursuits where user is owner
    result = []
    for p in shared:
        if p.get("user_id") != current_user["user_id"]:
            # Find user's role
            for member in p.get("sharing", {}).get("team_members", []):
                if member.get("user_id") == current_user["user_id"]:
                    p["user_role"] = member.get("role", "viewer")
                    break
            result.append(p)

    return {"shared_pursuits": result}
