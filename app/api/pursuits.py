"""
InDE v3.14 - Pursuits API Routes
CRUD operations for innovation pursuits with user scoping.

v3.14: Added onboarding metrics instrumentation.
v3.13: Added archive/restore endpoints for workspace organization.
"""

from datetime import datetime, timezone
from typing import Optional, List
import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field

from fastapi.responses import StreamingResponse, Response

from auth.middleware import get_current_user
from modules.pursuit.archive import PursuitArchiveService
from modules.pursuit.export import PursuitExportService
from modules.diagnostics.onboarding_metrics import OnboardingMetricsService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class CreatePursuitRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    storage_election: Optional[str] = "FULL_PARTICIPATION"


class UpdatePursuitRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    storage_election: Optional[str] = None
    status: Optional[str] = None


class PursuitResponse(BaseModel):
    pursuit_id: str
    user_id: str
    title: str
    description: Optional[str]
    status: str
    storage_election: str
    created_at: datetime
    updated_at: datetime
    artifact_ids: List[str] = []
    health_score: Optional[float] = None
    health_zone: Optional[str] = None
    crisis_active: bool = False
    is_archived: bool = False  # v3.13: Archive support
    gii_id: Optional[str] = None  # v3.16: Global Innovator Identifier


class PursuitListResponse(BaseModel):
    pursuits: List[PursuitResponse]
    total: int


@router.post("", response_model=PursuitResponse)
async def create_pursuit(
    request: Request,
    data: CreatePursuitRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create a new innovation pursuit.
    """
    db = request.app.state.db

    pursuit_id = str(uuid.uuid4())
    pursuit = {
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"],
        "title": data.title,
        "description": data.description,
        "status": "active",
        "storage_election": data.storage_election,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "artifact_ids": [],
        "health_score": None,
        "health_zone": None,
        "crisis_history": []
    }

    db.db.pursuits.insert_one(pursuit)

    # Initialize scaffolding state
    db._init_scaffolding_state(pursuit_id)

    # Update user's pursuit count
    db.db.users.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"pursuit_count": 1}}
    )

    # v3.14: Record onboarding metrics - session start + screen 1
    try:
        metrics_service = OnboardingMetricsService(db)
        await metrics_service.record_session_start(user["user_id"])
        await metrics_service.record_screen_reached(user["user_id"], 1)
    except Exception as e:
        logger.warning(f"Onboarding metrics recording failed: {e}")

    # v3.16: Fetch user's GII for response
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    user_gii_id = user_doc.get("gii_id") if user_doc else None

    return PursuitResponse(
        pursuit_id=pursuit["pursuit_id"],
        user_id=pursuit["user_id"],
        title=pursuit["title"],
        description=pursuit.get("description"),
        status=pursuit["status"],
        storage_election=pursuit["storage_election"],
        created_at=pursuit["created_at"],
        updated_at=pursuit["updated_at"],
        artifact_ids=pursuit["artifact_ids"],
        gii_id=user_gii_id  # v3.16: Include user's GII
    )


@router.get("", response_model=PursuitListResponse)
async def list_pursuits(
    request: Request,
    user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    include_archived: bool = Query(False, description="Include archived pursuits"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List all pursuits for the current user.
    By default, excludes archived pursuits. Use include_archived=true to show all.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[list_pursuits] user_id={user.get('user_id')}, include_archived={include_archived}")
    print(f"[list_pursuits] user_id={user.get('user_id')}, include_archived={include_archived}")

    db = request.app.state.db

    query = {"user_id": user["user_id"]}
    if status:
        query["status"] = status
    # v3.13: Exclude archived pursuits by default
    if not include_archived:
        query["is_archived"] = {"$ne": True}

    logger.info(f"[list_pursuits] query={query}")
    print(f"[list_pursuits] query={query}")

    total = db.db.pursuits.count_documents(query)
    logger.info(f"[list_pursuits] total={total}")
    print(f"[list_pursuits] total={total}")
    cursor = db.db.pursuits.find(query).sort("updated_at", -1).skip(offset).limit(limit)

    # v3.16: Fetch user's GII for inclusion in response
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    user_gii_id = user_doc.get("gii_id") if user_doc else None

    pursuits = []
    for p in cursor:
        # Check if pursuit has active crisis
        crisis_active = db.db.crisis_sessions.count_documents({
            "pursuit_id": p["pursuit_id"],
            "resolved_at": None
        }) > 0

        pursuits.append(PursuitResponse(
            pursuit_id=p["pursuit_id"],
            user_id=p["user_id"],
            title=p["title"],
            description=p.get("description"),
            status=p["status"],
            storage_election=p.get("storage_election", "FULL_PARTICIPATION"),
            created_at=p["created_at"],
            updated_at=p["updated_at"],
            artifact_ids=p.get("artifact_ids", []),
            health_score=p.get("health_score"),
            health_zone=p.get("health_zone"),
            crisis_active=crisis_active,
            is_archived=p.get("is_archived", False),  # v3.13: Include archive status
            gii_id=user_gii_id  # v3.16: Include user's GII
        ))

    return PursuitListResponse(pursuits=pursuits, total=total)


@router.get("/{pursuit_id}", response_model=PursuitResponse)
async def get_pursuit(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get a specific pursuit by ID.
    """
    db = request.app.state.db

    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    crisis_active = db.db.crisis_sessions.count_documents({
        "pursuit_id": pursuit_id,
        "resolved_at": None
    }) > 0

    # v3.16: Fetch user's GII for response
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    user_gii_id = user_doc.get("gii_id") if user_doc else None

    return PursuitResponse(
        pursuit_id=pursuit["pursuit_id"],
        user_id=pursuit["user_id"],
        title=pursuit["title"],
        description=pursuit.get("description"),
        status=pursuit["status"],
        storage_election=pursuit.get("storage_election", "FULL_PARTICIPATION"),
        created_at=pursuit["created_at"],
        updated_at=pursuit["updated_at"],
        artifact_ids=pursuit.get("artifact_ids", []),
        health_score=pursuit.get("health_score"),
        health_zone=pursuit.get("health_zone"),
        crisis_active=crisis_active,
        gii_id=user_gii_id  # v3.16: Include user's GII
    )


@router.patch("/{pursuit_id}", response_model=PursuitResponse)
async def update_pursuit(
    request: Request,
    pursuit_id: str,
    data: UpdatePursuitRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update a pursuit.
    """
    db = request.app.state.db

    # Verify ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Build update
    updates = {"updated_at": datetime.now(timezone.utc)}
    if data.title is not None:
        updates["title"] = data.title
    if data.description is not None:
        updates["description"] = data.description
    if data.storage_election is not None:
        updates["storage_election"] = data.storage_election
    if data.status is not None:
        updates["status"] = data.status

    db.db.pursuits.update_one(
        {"pursuit_id": pursuit_id},
        {"$set": updates}
    )

    # Get updated pursuit
    updated = db.db.pursuits.find_one({"pursuit_id": pursuit_id})

    # v3.16: Fetch user's GII for response
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    user_gii_id = user_doc.get("gii_id") if user_doc else None

    return PursuitResponse(
        pursuit_id=updated["pursuit_id"],
        user_id=updated["user_id"],
        title=updated["title"],
        description=updated.get("description"),
        status=updated["status"],
        storage_election=updated.get("storage_election", "FULL_PARTICIPATION"),
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
        artifact_ids=updated.get("artifact_ids", []),
        gii_id=user_gii_id  # v3.16: Include user's GII
    )


@router.delete("/{pursuit_id}")
async def delete_pursuit(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Delete a pursuit (soft delete - sets status to 'deleted').
    """
    db = request.app.state.db

    # Verify ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Soft delete
    db.db.pursuits.update_one(
        {"pursuit_id": pursuit_id},
        {"$set": {
            "status": "deleted",
            "deleted_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    return {"message": "Pursuit deleted successfully"}


@router.post("/{pursuit_id}/evaporate")
async def evaporate_pursuit(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    EVAPORATE a pursuit - complete and immediate deletion with no retrospective.
    Removes all pursuit data including artifacts, coaching history, and related records.
    This action is irreversible.
    """
    db = request.app.state.db

    # Verify ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    pursuit_title = pursuit.get("title", "Unknown")

    # Hard delete all related data
    # Delete coaching messages
    db.db.coaching_messages.delete_many({"pursuit_id": pursuit_id})

    # Delete artifacts
    db.db.artifacts.delete_many({"pursuit_id": pursuit_id})

    # Delete scaffolding state
    db.db.scaffolding_states.delete_many({"pursuit_id": pursuit_id})

    # Delete crisis sessions
    db.db.crisis_sessions.delete_many({"pursuit_id": pursuit_id})

    # Delete retrospectives (if any)
    db.db.retrospectives.delete_many({"pursuit_id": pursuit_id})

    # Delete health history
    db.db.health_history.delete_many({"pursuit_id": pursuit_id})

    # Delete the pursuit itself
    db.db.pursuits.delete_one({"pursuit_id": pursuit_id})

    # Update user's pursuit count
    db.db.users.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"pursuit_count": -1}}
    )

    return {
        "message": f"Pursuit '{pursuit_title}' has been evaporated",
        "pursuit_id": pursuit_id,
        "evaporated": True
    }


@router.delete("/user/all")
async def delete_all_user_pursuits(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Delete all pursuits for the current user (used for demo account cleanup).
    Completely removes all pursuit data.
    """
    db = request.app.state.db
    user_id = user["user_id"]

    # Get all pursuit IDs for this user
    pursuit_ids = [p["pursuit_id"] for p in db.db.pursuits.find(
        {"user_id": user_id},
        {"pursuit_id": 1}
    )]

    if not pursuit_ids:
        return {"message": "No pursuits to delete", "deleted_count": 0}

    # Delete all related data for all pursuits
    db.db.coaching_messages.delete_many({"pursuit_id": {"$in": pursuit_ids}})
    db.db.artifacts.delete_many({"pursuit_id": {"$in": pursuit_ids}})
    db.db.scaffolding_states.delete_many({"pursuit_id": {"$in": pursuit_ids}})
    db.db.crisis_sessions.delete_many({"pursuit_id": {"$in": pursuit_ids}})
    db.db.retrospectives.delete_many({"pursuit_id": {"$in": pursuit_ids}})
    db.db.health_history.delete_many({"pursuit_id": {"$in": pursuit_ids}})

    # Delete all pursuits
    result = db.db.pursuits.delete_many({"user_id": user_id})

    # Reset user's pursuit count
    db.db.users.update_one(
        {"user_id": user_id},
        {"$set": {"pursuit_count": 0, "completed_pursuits": 0}}
    )

    return {
        "message": "All pursuits deleted",
        "deleted_count": result.deleted_count
    }


class AbandonPursuitRequest(BaseModel):
    reason: Optional[str] = None


class RetrospectiveRequest(BaseModel):
    learnings: Optional[str] = None
    what_worked: Optional[str] = None
    what_didnt_work: Optional[str] = None
    would_do_differently: Optional[str] = None
    key_insights: Optional[List[str]] = []


@router.post("/{pursuit_id}/abandon")
async def abandon_pursuit(
    request: Request,
    pursuit_id: str,
    data: AbandonPursuitRequest,
    user: dict = Depends(get_current_user)
):
    """
    Abandon a pursuit. Sets status to 'abandoned' and prepares for retrospective.
    The pursuit remains in memory until retrospective is completed.
    """
    db = request.app.state.db

    # Verify ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    if pursuit.get("status") == "abandoned":
        raise HTTPException(status_code=400, detail="Pursuit is already abandoned")

    # Set status to abandoned and record abandonment details
    db.db.pursuits.update_one(
        {"pursuit_id": pursuit_id},
        {"$set": {
            "status": "abandoned",
            "abandoned_at": datetime.now(timezone.utc),
            "abandonment_reason": data.reason,
            "retrospective_pending": True,
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    return {
        "message": "Pursuit abandoned. Please complete the retrospective to archive.",
        "pursuit_id": pursuit_id,
        "status": "abandoned",
        "retrospective_pending": True
    }


@router.post("/{pursuit_id}/retrospective")
async def complete_retrospective(
    request: Request,
    pursuit_id: str,
    data: RetrospectiveRequest,
    user: dict = Depends(get_current_user)
):
    """
    Complete retrospective for an abandoned pursuit.
    After retrospective, the pursuit is archived and removed from active portfolio.
    """
    db = request.app.state.db

    # Verify ownership and that pursuit is abandoned
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    if pursuit.get("status") != "abandoned":
        raise HTTPException(status_code=400, detail="Pursuit must be abandoned before completing retrospective")

    # Store retrospective data
    retrospective = {
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"],
        "learnings": data.learnings,
        "what_worked": data.what_worked,
        "what_didnt_work": data.what_didnt_work,
        "would_do_differently": data.would_do_differently,
        "key_insights": data.key_insights or [],
        "completed_at": datetime.now(timezone.utc)
    }

    db.db.retrospectives.insert_one(retrospective)

    # Archive the pursuit (removes from active portfolio)
    db.db.pursuits.update_one(
        {"pursuit_id": pursuit_id},
        {"$set": {
            "status": "archived",
            "archived_at": datetime.now(timezone.utc),
            "retrospective_pending": False,
            "retrospective_completed": True,
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    return {
        "message": "Retrospective completed. Pursuit archived.",
        "pursuit_id": pursuit_id,
        "status": "archived"
    }


@router.get("/{pursuit_id}/retrospective")
async def get_retrospective(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get retrospective data for a pursuit.
    """
    db = request.app.state.db

    # Verify ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    retrospective = db.db.retrospectives.find_one({
        "pursuit_id": pursuit_id
    })

    if not retrospective:
        return {"pursuit_id": pursuit_id, "retrospective": None}

    # Remove MongoDB _id
    if "_id" in retrospective:
        del retrospective["_id"]

    return {"pursuit_id": pursuit_id, "retrospective": retrospective}


@router.get("/{pursuit_id}/scaffolding")
async def get_scaffolding_state(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get the scaffolding state for a pursuit.
    """
    db = request.app.state.db

    # Verify ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    state = db.get_scaffolding_state(pursuit_id)
    if not state:
        raise HTTPException(status_code=404, detail="Scaffolding state not found")

    # Remove MongoDB _id field
    if "_id" in state:
        del state["_id"]

    return state


# ═══════════════════════════════════════════════════════════════════════════════
# v3.13: ARCHIVE / RESTORE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{pursuit_id}/archive")
async def archive_pursuit(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Archive a pursuit — removes from active workspace, preserves all data.

    Archiving is a workspace organization action, not deletion.
    The pursuit and all its data remain fully intact and can be
    restored at any time.
    """
    print(f"[archive_pursuit] pursuit_id={pursuit_id}, user_id={user.get('user_id')}")
    db = request.app.state.db
    service = PursuitArchiveService(db)
    result = service.archive_pursuit(pursuit_id, user["user_id"])
    print(f"[archive_pursuit] result={result}")
    return result


@router.post("/{pursuit_id}/restore")
async def restore_pursuit(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Restore an archived pursuit to the active workspace.

    The pursuit will reappear in the active pursuits list.
    """
    db = request.app.state.db
    service = PursuitArchiveService(db)
    return service.restore_pursuit(pursuit_id, user["user_id"])


@router.get("/archived/list")
async def list_archived_pursuits(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user)
):
    """
    List archived pursuits for the current user, paginated.

    Returns summary information for each archived pursuit,
    ordered by most recently archived first.
    """
    db = request.app.state.db
    service = PursuitArchiveService(db)
    return service.get_archived_pursuits(user["user_id"], limit, offset)


@router.get("/{pursuit_id}/export")
async def export_pursuit(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Generate and download a complete pursuit export as a ZIP file.

    Contains: vision artifacts, fear register, milestones, coaching
    conversations, and all generated artifacts.

    Generated on-demand — not stored server-side.
    """
    from datetime import datetime, timezone

    db = request.app.state.db
    service = PursuitExportService(db)
    zip_buffer, filename = service.generate_export(pursuit_id, user["user_id"])

    # Read the full content from buffer
    content = zip_buffer.read()

    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Generated": datetime.now(timezone.utc).isoformat()
        }
    )
