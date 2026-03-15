"""
InDE v3.1 - Crisis Mode API Routes
Crisis detection, management, and intervention.
"""

from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from auth.middleware import get_current_user
from core.config import CRISIS_TYPES, CRISIS_PHASES

router = APIRouter()


class TriggerCrisisRequest(BaseModel):
    pursuit_id: str
    crisis_type: str
    trigger_reason: Optional[str] = None


class CrisisSessionResponse(BaseModel):
    session_id: str
    pursuit_id: str
    crisis_type: str
    urgency: str
    current_phase: str
    started_at: datetime
    resolved_at: Optional[datetime]


@router.post("/trigger", response_model=CrisisSessionResponse)
async def trigger_crisis(
    request: Request,
    data: TriggerCrisisRequest,
    user: dict = Depends(get_current_user)
):
    """
    Manually trigger crisis mode for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": data.pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Validate crisis type
    if data.crisis_type not in CRISIS_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid crisis type. Valid types: {list(CRISIS_TYPES.keys())}"
        )

    # Check for existing active crisis
    existing = db.db.crisis_sessions.find_one({
        "pursuit_id": data.pursuit_id,
        "resolved_at": None
    })

    if existing:
        raise HTTPException(
            status_code=400,
            detail="An active crisis session already exists for this pursuit"
        )

    crisis_config = CRISIS_TYPES[data.crisis_type]
    session_id = str(uuid.uuid4())

    session = {
        "session_id": session_id,
        "pursuit_id": data.pursuit_id,
        "user_id": user["user_id"],
        "crisis_type": data.crisis_type,
        "urgency": crisis_config["default_urgency"],
        "intervention_depth": crisis_config["intervention_depth"],
        "current_phase": CRISIS_PHASES[0],  # IMMEDIATE_TRIAGE
        "phase_history": [{
            "phase": CRISIS_PHASES[0],
            "entered_at": datetime.now(timezone.utc).isoformat()
        }],
        "trigger_reason": data.trigger_reason,
        "started_at": datetime.now(timezone.utc),
        "resolved_at": None,
        "resolution": None
    }

    db.db.crisis_sessions.insert_one(session)

    # Add to pursuit's crisis history
    db.db.pursuits.update_one(
        {"pursuit_id": data.pursuit_id},
        {"$push": {"crisis_history": {
            "session_id": session_id,
            "crisis_type": data.crisis_type,
            "started_at": datetime.now(timezone.utc).isoformat()
        }}}
    )

    return CrisisSessionResponse(
        session_id=session["session_id"],
        pursuit_id=session["pursuit_id"],
        crisis_type=session["crisis_type"],
        urgency=session["urgency"],
        current_phase=session["current_phase"],
        started_at=session["started_at"],
        resolved_at=None
    )


@router.get("/{pursuit_id}/active")
async def get_active_crisis(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get active crisis session for a pursuit, if any.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    session = db.db.crisis_sessions.find_one({
        "pursuit_id": pursuit_id,
        "resolved_at": None
    })

    if not session:
        return {"active": False, "message": "No active crisis session"}

    if "_id" in session:
        del session["_id"]

    return {"active": True, "session": session}


@router.post("/{session_id}/advance-phase")
async def advance_crisis_phase(
    request: Request,
    session_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Advance to the next crisis intervention phase.
    """
    db = request.app.state.db

    session = db.db.crisis_sessions.find_one({
        "session_id": session_id,
        "user_id": user["user_id"]
    })

    if not session:
        raise HTTPException(status_code=404, detail="Crisis session not found")

    if session.get("resolved_at"):
        raise HTTPException(status_code=400, detail="Crisis session already resolved")

    current_idx = CRISIS_PHASES.index(session["current_phase"])
    if current_idx >= len(CRISIS_PHASES) - 1:
        raise HTTPException(
            status_code=400,
            detail="Already at final phase (POST_CRISIS_MONITORING)"
        )

    next_phase = CRISIS_PHASES[current_idx + 1]

    db.db.crisis_sessions.update_one(
        {"session_id": session_id},
        {
            "$set": {"current_phase": next_phase},
            "$push": {"phase_history": {
                "phase": next_phase,
                "entered_at": datetime.now(timezone.utc).isoformat()
            }}
        }
    )

    return {
        "previous_phase": session["current_phase"],
        "current_phase": next_phase,
        "message": f"Advanced to {next_phase}"
    }


@router.post("/{session_id}/resolve")
async def resolve_crisis(
    request: Request,
    session_id: str,
    user: dict = Depends(get_current_user),
    resolution: Optional[str] = None
):
    """
    Resolve a crisis session.
    """
    db = request.app.state.db

    session = db.db.crisis_sessions.find_one({
        "session_id": session_id,
        "user_id": user["user_id"]
    })

    if not session:
        raise HTTPException(status_code=404, detail="Crisis session not found")

    if session.get("resolved_at"):
        raise HTTPException(status_code=400, detail="Crisis session already resolved")

    db.db.crisis_sessions.update_one(
        {"session_id": session_id},
        {"$set": {
            "resolved_at": datetime.now(timezone.utc),
            "resolution": resolution
        }}
    )

    return {"message": "Crisis session resolved", "resolution": resolution}


@router.get("/{pursuit_id}/history")
async def get_crisis_history(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get crisis history for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    sessions = list(db.db.crisis_sessions.find(
        {"pursuit_id": pursuit_id},
        {"_id": 0}
    ).sort("started_at", -1))

    return {"pursuit_id": pursuit_id, "sessions": sessions}
