"""
InDE v3.1 - Timeline API Routes
Temporal Intelligence Module (TIM) endpoints.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from auth.middleware import get_current_user

# v3.11: Import permission enforcement
from scaffolding.permissions import (
    require_milestone_edit_permission,
    check_can_edit_milestone
)

router = APIRouter()


class TimeAllocationRequest(BaseModel):
    pursuit_id: str
    total_days: int
    vision_percent: float = 15.0
    de_risk_percent: float = 35.0
    deploy_percent: float = 40.0
    buffer_percent: float = 10.0


@router.post("/allocation")
async def set_time_allocation(
    request: Request,
    data: TimeAllocationRequest,
    user: dict = Depends(get_current_user)
):
    """
    Set time allocation for a pursuit's phases.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": data.pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Validate percentages sum to 100
    total = data.vision_percent + data.de_risk_percent + data.deploy_percent + data.buffer_percent
    if abs(total - 100.0) > 0.1:
        raise HTTPException(status_code=400, detail="Percentages must sum to 100")

    allocation = {
        "pursuit_id": data.pursuit_id,
        "user_id": user["user_id"],
        "total_days": data.total_days,
        "phases": {
            "VISION": {
                "percent": data.vision_percent,
                "days": int(data.total_days * data.vision_percent / 100),
                "status": "NOT_STARTED"
            },
            "DE_RISK": {
                "percent": data.de_risk_percent,
                "days": int(data.total_days * data.de_risk_percent / 100),
                "status": "NOT_STARTED"
            },
            "DEPLOY": {
                "percent": data.deploy_percent,
                "days": int(data.total_days * data.deploy_percent / 100),
                "status": "NOT_STARTED"
            },
            "BUFFER": {
                "percent": data.buffer_percent,
                "days": int(data.total_days * data.buffer_percent / 100)
            }
        },
        "created_at": datetime.now(timezone.utc)
    }

    # Upsert allocation
    db.db.time_allocations.update_one(
        {"pursuit_id": data.pursuit_id},
        {"$set": allocation},
        upsert=True
    )

    return allocation


@router.get("/{pursuit_id}/allocation")
async def get_time_allocation(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get time allocation for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    allocation = db.db.time_allocations.find_one(
        {"pursuit_id": pursuit_id},
        {"_id": 0}
    )

    if not allocation:
        return {"message": "No time allocation set for this pursuit"}

    return allocation


@router.get("/{pursuit_id}/velocity")
async def get_velocity_metrics(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get velocity metrics for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Get latest velocity metric
    velocity = db.db.velocity_metrics.find_one(
        {"pursuit_id": pursuit_id},
        sort=[("calculated_at", -1)]
    )

    if not velocity:
        return {
            "pursuit_id": pursuit_id,
            "message": "No velocity data available yet"
        }

    if "_id" in velocity:
        del velocity["_id"]

    return velocity


@router.get("/{pursuit_id}/events")
async def get_temporal_events(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user),
    limit: int = 50
):
    """
    Get temporal events for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    events = list(db.db.temporal_events.find(
        {"pursuit_id": pursuit_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit))

    return {"pursuit_id": pursuit_id, "events": events}


# =============================================================================
# v3.9: MILESTONE ENDPOINTS
# =============================================================================

class MilestoneUpdateRequest(BaseModel):
    status: Optional[str] = None
    target_date: Optional[str] = None
    title: Optional[str] = None


@router.get("/{pursuit_id}/milestones")
async def get_milestones(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user),
    status: Optional[str] = None,
    limit: int = 50
):
    """
    Get extracted milestones for a pursuit.
    Returns milestones with days_until calculation for UI display.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Get milestones from database
    milestones = db.get_milestones(pursuit_id, status=status, limit=limit)

    # Enrich with days_until calculation
    now = datetime.now(timezone.utc)
    for m in milestones:
        if m.get("target_date"):
            try:
                # Parse ISO 8601 date
                target_str = m["target_date"]
                if "T" not in target_str:
                    target_str += "T23:59:59Z"
                if not target_str.endswith("Z") and "+" not in target_str:
                    target_str += "Z"
                target = datetime.fromisoformat(target_str.replace("Z", "+00:00"))
                delta = (target - now).days
                m["days_until"] = delta
                m["is_overdue"] = delta < 0
            except (ValueError, TypeError):
                m["days_until"] = None
                m["is_overdue"] = False
        else:
            m["days_until"] = None
            m["is_overdue"] = False

    return {"pursuit_id": pursuit_id, "milestones": milestones}


@router.patch("/{pursuit_id}/milestones/{milestone_id}")
async def update_milestone(
    request: Request,
    pursuit_id: str,
    milestone_id: str,
    data: MilestoneUpdateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update a milestone's status, date, or title.

    v3.11: Structural changes (target_date, title) require creator permission in team pursuits.
    """
    db = request.app.state.db

    # Verify pursuit exists and user has access
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Verify milestone exists and belongs to pursuit
    milestone = db.db.pursuit_milestones.find_one({
        "milestone_id": milestone_id,
        "pursuit_id": pursuit_id
    })

    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # v3.11: Check permissions for structural changes (date, title)
    is_structural_change = data.target_date is not None or data.title is not None
    if is_structural_change:
        require_milestone_edit_permission(user["user_id"], pursuit_id, db)

    # Build update dict
    updates = {}
    if data.status is not None:
        valid_statuses = ["pending", "at_risk", "completed", "missed"]
        if data.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )
        updates["status"] = data.status

    if data.target_date is not None:
        updates["target_date"] = data.target_date
        updates["date_precision"] = "exact"

    if data.title is not None:
        updates["title"] = data.title[:100]

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    # Apply updates
    success = db.update_milestone(milestone_id, updates)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update milestone")

    return {"success": True, "milestone_id": milestone_id, "updates": updates}


@router.delete("/{pursuit_id}/milestones/{milestone_id}")
async def delete_milestone(
    request: Request,
    pursuit_id: str,
    milestone_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Delete a milestone.

    v3.11: Requires creator permission in team pursuits.
    """
    db = request.app.state.db

    # Verify pursuit exists and user has access
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # v3.11: Check permission for deletion (structural change)
    require_milestone_edit_permission(user["user_id"], pursuit_id, db)

    # Verify milestone exists and belongs to pursuit
    milestone = db.db.pursuit_milestones.find_one({
        "milestone_id": milestone_id,
        "pursuit_id": pursuit_id
    })

    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # Delete milestone
    success = db.delete_milestone(milestone_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete milestone")

    return {"success": True, "milestone_id": milestone_id}


# =============================================================================
# v3.10: TIMELINE INTEGRITY ENDPOINTS
# =============================================================================

class ConflictResolutionRequest(BaseModel):
    """Request to resolve a milestone conflict."""
    choice: str  # "accept_new" | "keep_existing" | "keep_both"
    pending_milestone: dict  # The milestone that was held pending resolution
    existing_milestone_id: str  # The ID of the conflicting existing milestone


class InconsistencyResolutionRequest(BaseModel):
    """Request to resolve a timeline inconsistency."""
    source_of_truth: str  # "allocation" | "milestone"


class RelativeDateConfirmationRequest(BaseModel):
    """Request to confirm or correct a relative date."""
    milestone_id: str
    confirmed_date: Optional[str] = None  # If None, original resolved date is confirmed


@router.post("/{pursuit_id}/resolve-conflict")
async def resolve_milestone_conflict(
    request: Request,
    pursuit_id: str,
    data: ConflictResolutionRequest,
    user: dict = Depends(get_current_user)
):
    """
    Resolve a pending milestone conflict.

    Called when the innovator confirms or rejects a pending milestone that
    conflicted with an existing milestone.

    choice options:
    - "accept_new": Supersede old milestone with new one
    - "keep_existing": Discard the pending milestone
    - "keep_both": Store both milestones (treats them as distinct)

    v3.11: Requires creator permission in team pursuits.
    """
    db = request.app.state.db

    # Verify pursuit exists and user has access
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # v3.11: Check permission for conflict resolution (structural change)
    require_milestone_edit_permission(user["user_id"], pursuit_id, db)

    # Validate choice
    valid_choices = ["accept_new", "keep_existing", "keep_both"]
    if data.choice not in valid_choices:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid choice. Must be one of: {valid_choices}"
        )

    # Import conflict resolver
    from scaffolding.conflict_resolver import TemporalConflictResolver

    resolver = TemporalConflictResolver(db)
    result = resolver.resolve_conflict(
        pursuit_id=pursuit_id,
        choice=data.choice,
        pending_milestone=data.pending_milestone,
        existing_milestone_id=data.existing_milestone_id
    )

    # Log resolution event
    from tim.event_logger import TemporalEventLogger
    event_logger = TemporalEventLogger(db)
    event_logger.log_conflict_resolved(
        pursuit_id=pursuit_id,
        phase=pursuit.get("phase", "VISION"),
        resolution_data={
            "choice": data.choice,
            "action": result.get("action"),
            "existing_milestone_id": data.existing_milestone_id,
            "new_milestone_id": result.get("new_milestone_id"),
            "resolved_at": result.get("resolved_at")
        }
    )

    return {
        "success": True,
        "pursuit_id": pursuit_id,
        "resolution": result
    }


@router.post("/{pursuit_id}/resolve-inconsistency")
async def resolve_timeline_inconsistency(
    request: Request,
    pursuit_id: str,
    data: InconsistencyResolutionRequest,
    user: dict = Depends(get_current_user)
):
    """
    Resolve a timeline inconsistency between time_allocations.target_end
    and the latest release milestone.

    source_of_truth options:
    - "milestone": Update time_allocations to match release milestone
    - "allocation": Update release milestone to match time_allocations

    v3.11: Requires creator permission in team pursuits.
    """
    db = request.app.state.db

    # Verify pursuit exists and user has access
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # v3.11: Check permission for inconsistency resolution (structural change)
    require_milestone_edit_permission(user["user_id"], pursuit_id, db)

    # Validate source_of_truth
    valid_sources = ["milestone", "allocation"]
    if data.source_of_truth not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_of_truth. Must be one of: {valid_sources}"
        )

    # Import consistency validator
    from scaffolding.consistency_validator import TimelineConsistencyValidator

    validator = TimelineConsistencyValidator(db)
    await validator.resolve(pursuit_id, data.source_of_truth, db)

    # Log resolution event
    from tim.event_logger import TemporalEventLogger
    event_logger = TemporalEventLogger(db)
    event_logger.log_inconsistency_resolved(
        pursuit_id=pursuit_id,
        phase=pursuit.get("phase", "VISION"),
        resolution_data={
            "source_of_truth": data.source_of_truth,
            "resolved_at": datetime.now(timezone.utc).isoformat() + "Z"
        }
    )

    return {
        "success": True,
        "pursuit_id": pursuit_id,
        "source_of_truth": data.source_of_truth
    }


@router.post("/{pursuit_id}/confirm-relative-date")
async def confirm_relative_date(
    request: Request,
    pursuit_id: str,
    data: RelativeDateConfirmationRequest,
    user: dict = Depends(get_current_user)
):
    """
    Confirm or correct a relative date milestone.

    If confirmed_date is None, the original resolved date is confirmed.
    If confirmed_date is provided, the milestone is updated to that date.

    In both cases, date_precision is upgraded to "exact" and
    requires_recalculation is set to False.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Verify milestone exists and belongs to pursuit
    milestone = db.db.pursuit_milestones.find_one({
        "milestone_id": data.milestone_id,
        "pursuit_id": pursuit_id
    })

    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # Import recalculator
    from scaffolding.relative_date_recalculator import RelativeDateRecalculator

    recalculator = RelativeDateRecalculator()
    await recalculator.confirm_relative_date(
        milestone_id=data.milestone_id,
        confirmed_date=data.confirmed_date,
        db=db
    )

    # Log confirmation event
    from tim.event_logger import TemporalEventLogger
    event_logger = TemporalEventLogger(db)
    event_logger.log_relative_date_confirmed(
        pursuit_id=pursuit_id,
        phase=pursuit.get("phase", "VISION"),
        confirmation_data={
            "milestone_id": data.milestone_id,
            "original_date": milestone.get("target_date"),
            "confirmed_date": data.confirmed_date or milestone.get("target_date"),
            "date_expression": milestone.get("date_expression"),
            "confirmed_at": datetime.now(timezone.utc).isoformat() + "Z"
        }
    )

    return {
        "success": True,
        "milestone_id": data.milestone_id,
        "confirmed_date": data.confirmed_date or milestone.get("target_date")
    }


@router.get("/{pursuit_id}/pending-conflicts")
async def get_pending_conflicts(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get any pending milestone conflicts that need resolution.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Get from scaffolding engine's pending conflicts (stored in session)
    # For now, return empty - this would need integration with engine state
    return {
        "pursuit_id": pursuit_id,
        "pending_conflicts": []
    }


@router.get("/{pursuit_id}/consistency-check")
async def check_timeline_consistency(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Check for timeline inconsistency between time_allocations and milestones.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Import consistency validator
    from scaffolding.consistency_validator import TimelineConsistencyValidator

    validator = TimelineConsistencyValidator(db)
    result = await validator.validate(pursuit_id)

    return {
        "pursuit_id": pursuit_id,
        "is_consistent": result.is_consistent,
        "allocation_end": result.allocation_end,
        "milestone_end": result.milestone_end,
        "day_difference": result.day_difference,
        "coaching_prompt": result.coaching_prompt
    }


@router.get("/{pursuit_id}/stale-relative-dates")
async def get_stale_relative_dates(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get milestones with unconfirmed relative dates that need confirmation.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Import recalculator
    from scaffolding.relative_date_recalculator import RelativeDateRecalculator

    recalculator = RelativeDateRecalculator()
    stale_dates = await recalculator.check_stale_relative_dates(pursuit_id, db)

    return {
        "pursuit_id": pursuit_id,
        "stale_relative_dates": stale_dates
    }


# =============================================================================
# v3.11: MILESTONE PERMISSION ENDPOINT
# =============================================================================

@router.get("/{pursuit_id}/milestone-permissions")
async def get_milestone_permissions(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Check if current user can edit milestones for this pursuit.

    Returns permission status for UI to determine field editability.

    v3.11: TD-014 Team Pursuit Milestone Permissions
    """
    db = request.app.state.db

    # Verify pursuit exists and user has access
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Get permission status
    permission_status = check_can_edit_milestone(user["user_id"], pursuit_id, db)

    return {
        "pursuit_id": pursuit_id,
        **permission_status
    }
