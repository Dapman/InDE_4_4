"""
InDE MVP v3.4 - Convergence API Routes
Endpoints for convergence protocol management.

Endpoints:
- GET /sessions/{session_id}/convergence - Get convergence state
- POST /sessions/{session_id}/convergence/trigger - Explicit convergence trigger
- POST /sessions/{session_id}/convergence/outcomes - Capture outcome
- POST /sessions/{session_id}/convergence/handoff - Complete handoff
- GET /pursuits/{pursuit_id}/convergence-history - Get convergence history
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from core.database import db
from coaching.convergence import (
    get_convergence_orchestrator, ConvergencePhase,
    OutcomeType
)
from core.config import CONVERGENCE_OUTCOME_TYPES

logger = logging.getLogger("inde.api.convergence")

router = APIRouter(tags=["convergence"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ConvergenceStateResponse(BaseModel):
    """Convergence state response."""
    session_id: str
    current_phase: str
    methodology_archetype: Optional[str] = None
    outcomes_captured: int = 0
    recent_signals: List[Dict] = []
    criteria_status: List[Dict] = []
    coaching_guidance: str = ""


class TriggerConvergenceRequest(BaseModel):
    """Request to trigger convergence."""
    source: str = Field("ui_button", description="Source of trigger (ui_button or message)")


class CaptureOutcomeRequest(BaseModel):
    """Request to capture a convergence outcome."""
    outcome_type: str = Field(..., description="Type: DECISION, INSIGHT, HYPOTHESIS, COMMITMENT, REFINEMENT")
    summary: str = Field(..., min_length=10, max_length=1000, description="Summary of the outcome")
    artifact_ref: Optional[str] = Field(None, description="Reference to related artifact")


class HandoffRequest(BaseModel):
    """Request to complete handoff."""
    next_activity: Optional[str] = Field(None, description="What activity follows")


class ConvergenceHistoryResponse(BaseModel):
    """Convergence history response."""
    pursuit_id: str
    sessions: List[Dict]
    total_outcomes: int
    avg_outcomes_per_session: float


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_current_user(request) -> Dict:
    """Get current user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# =============================================================================
# CONVERGENCE STATE ENDPOINTS
# =============================================================================

@router.get("/sessions/{session_id}/convergence", response_model=ConvergenceStateResponse)
async def get_convergence_state(
    session_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get the current convergence state for a coaching session.

    Returns phase, signals, criteria status, and coaching guidance.
    """
    orchestrator = get_convergence_orchestrator()

    # Get session from database
    session = db.get_convergence_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Convergence session not found")

    # Verify user access
    if session.get("user_id") != current_user["user_id"]:
        pursuit = db.get_pursuit(session.get("pursuit_id"))
        if pursuit and pursuit.get("user_id") != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get context from orchestrator
    context = orchestrator.get_convergence_context(session_id)

    return ConvergenceStateResponse(
        session_id=session_id,
        current_phase=session.get("current_phase", "EXPLORING"),
        methodology_archetype=session.get("methodology_archetype"),
        outcomes_captured=len(session.get("outcomes_captured", [])),
        recent_signals=session.get("signal_history", [])[-5:],
        criteria_status=session.get("criteria_snapshot", []),
        coaching_guidance=context.get("coaching_guidance", "")
    )


@router.post("/sessions/{session_id}/convergence/trigger")
async def trigger_convergence(
    session_id: str,
    request: TriggerConvergenceRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Explicitly trigger convergence (e.g., from UI button).

    Transitions from EXPLORING to CONSOLIDATING phase.
    """
    # Verify session exists and user has access
    session = db.get_convergence_session(session_id)
    if not session:
        # Try to get coaching session and create convergence session
        coaching_session = db.get_coaching_session(session_id)
        if not coaching_session:
            raise HTTPException(status_code=404, detail="Session not found")

        if coaching_session.get("user_id") != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Create convergence session
        orchestrator = get_convergence_orchestrator()
        orchestrator.get_or_create_session(
            session_id=session_id,
            pursuit_id=coaching_session.get("pursuit_id", ""),
            user_id=current_user["user_id"]
        )
    else:
        if session.get("user_id") != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    # Trigger convergence
    orchestrator = get_convergence_orchestrator()
    result = orchestrator.explicit_convergence_trigger(session_id, request.source)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to trigger convergence"))

    logger.info(f"Convergence triggered for session {session_id} by user {current_user['user_id']}")

    return {
        "message": "Convergence triggered successfully",
        "new_phase": result.get("new_phase")
    }


@router.post("/sessions/{session_id}/convergence/outcomes")
async def capture_outcome(
    session_id: str,
    request: CaptureOutcomeRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Capture a convergence outcome.

    Outcomes can be: DECISION, INSIGHT, HYPOTHESIS, COMMITMENT, REFINEMENT
    """
    # Validate outcome type
    if request.outcome_type not in CONVERGENCE_OUTCOME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid outcome type. Must be one of: {CONVERGENCE_OUTCOME_TYPES}"
        )

    # Verify session access
    session = db.get_convergence_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Convergence session not found")

    if session.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Capture outcome
    orchestrator = get_convergence_orchestrator()
    result = orchestrator.capture_outcome(
        session_id=session_id,
        outcome_type=request.outcome_type,
        summary=request.summary,
        artifact_ref=request.artifact_ref,
        captured_by=current_user["user_id"]
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to capture outcome"))

    logger.info(
        f"Outcome captured for session {session_id}: "
        f"{request.outcome_type} by user {current_user['user_id']}"
    )

    return {
        "message": "Outcome captured successfully",
        "outcome_id": result.get("outcome_id"),
        "current_phase": result.get("current_phase")
    }


@router.post("/sessions/{session_id}/convergence/handoff")
async def complete_handoff(
    session_id: str,
    request: HandoffRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Complete the convergence handoff.

    Transitions to HANDED_OFF phase and prepares for next activity.
    """
    # Verify session access
    session = db.get_convergence_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Convergence session not found")

    if session.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Complete handoff
    orchestrator = get_convergence_orchestrator()
    result = orchestrator.complete_handoff(session_id, request.next_activity)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to complete handoff"))

    logger.info(f"Handoff completed for session {session_id}")

    return {
        "message": "Handoff completed successfully",
        "outcomes_count": result.get("outcomes_count"),
        "next_activity": result.get("next_activity")
    }


# =============================================================================
# CONVERGENCE HISTORY ENDPOINTS
# =============================================================================

@router.get("/pursuits/{pursuit_id}/convergence-history", response_model=ConvergenceHistoryResponse)
async def get_convergence_history(
    pursuit_id: str,
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get convergence history for a pursuit.

    Returns list of convergence sessions with outcomes.
    """
    # Verify pursuit access
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    if pursuit.get("user_id") != current_user["user_id"]:
        # Check if user is a team member
        team_members = pursuit.get("sharing", {}).get("team_members", [])
        if not any(m.get("user_id") == current_user["user_id"] for m in team_members):
            raise HTTPException(status_code=403, detail="Access denied")

    # Get convergence sessions
    sessions = db.get_pursuit_convergence_sessions(pursuit_id, limit=limit)

    # Calculate statistics
    total_outcomes = sum(len(s.get("outcomes_captured", [])) for s in sessions)
    avg_outcomes = total_outcomes / len(sessions) if sessions else 0

    return ConvergenceHistoryResponse(
        pursuit_id=pursuit_id,
        sessions=[{
            "session_id": s.get("session_id"),
            "current_phase": s.get("current_phase"),
            "initiated_at": s.get("initiated_at"),
            "completed_at": s.get("completed_at"),
            "outcomes_count": len(s.get("outcomes_captured", []))
        } for s in sessions],
        total_outcomes=total_outcomes,
        avg_outcomes_per_session=round(avg_outcomes, 2)
    )


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@router.get("/convergence/outcome-types")
async def get_outcome_types():
    """Get list of available outcome types."""
    return {
        "outcome_types": [
            {"type": "DECISION", "description": "A decision made during the session"},
            {"type": "INSIGHT", "description": "An insight or realization"},
            {"type": "HYPOTHESIS", "description": "A new hypothesis to test"},
            {"type": "COMMITMENT", "description": "A commitment to action"},
            {"type": "REFINEMENT", "description": "A refinement to existing artifact"}
        ]
    }


@router.get("/convergence/phases")
async def get_convergence_phases():
    """Get list of convergence phases with descriptions."""
    return {
        "phases": [
            {
                "phase": "EXPLORING",
                "description": "Open-ended discovery, no convergence signals detected"
            },
            {
                "phase": "CONSOLIDATING",
                "description": "Convergence detected, awaiting criteria satisfaction"
            },
            {
                "phase": "COMMITTED",
                "description": "Criteria met, capturing outcomes"
            },
            {
                "phase": "HANDED_OFF",
                "description": "Session complete, ready for next activity"
            }
        ]
    }
