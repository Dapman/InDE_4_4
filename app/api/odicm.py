"""
InDE MVP v3.4 - ODICM Extensions API Routes
Endpoints for On-Demand Innovation Coaching Module extensions.

Endpoints:
- POST /coaching/sessions/{session_id}/context - Build coaching context
- POST /coaching/sessions/{session_id}/enhance - Enhance coaching response
- GET /orgs/{org_id}/coaching/best-practices - Get org best practices
- GET /orgs/{org_id}/coaching/patterns - Get org coaching patterns
- GET /pursuits/{pursuit_id}/coaching/similar - Find similar pursuits
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from core.database import db
from coaching.odicm_extensions import (
    get_convergence_coach, get_org_intelligence,
    CoachingContext, EnhancedCoachingResponse
)
from coaching.convergence import ConvergencePhase

logger = logging.getLogger("inde.api.odicm")

router = APIRouter(tags=["odicm"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ConversationMessage(BaseModel):
    """A message in the conversation."""
    role: str = Field(..., description="user or assistant")
    content: str
    timestamp: Optional[str] = None


class BuildContextRequest(BaseModel):
    """Request to build coaching context."""
    conversation_history: List[ConversationMessage] = Field(default_factory=list)


class CoachingContextResponse(BaseModel):
    """Coaching context response."""
    pursuit_id: str
    user_id: str
    org_id: str
    methodology_archetype: str
    current_phase: str
    coaching_mode: str
    convergence_signals: List[Dict]
    portfolio_context: Dict[str, Any]
    methodology_guidance: Dict[str, Any]
    recent_outcomes: List[Dict]


class EnhanceResponseRequest(BaseModel):
    """Request to enhance a coaching response."""
    base_response: str = Field(..., min_length=1, description="Base coaching response to enhance")
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    include_portfolio_insights: bool = Field(True, description="Include portfolio insights")


class EnhancedResponseOutput(BaseModel):
    """Enhanced coaching response output."""
    message: str
    coaching_mode: str
    convergence_phase: str
    suggested_actions: List[str]
    methodology_hints: List[str]
    convergence_prompt: Optional[str]
    portfolio_insights: Optional[str]
    metadata: Dict[str, Any]


class BestPracticeResponse(BaseModel):
    """Best practice response."""
    source_pursuit_id: str
    source_pursuit_name: str
    insight: str
    methodology: str
    stage: str


class BestPracticesListResponse(BaseModel):
    """List of best practices."""
    org_id: str
    practices: List[BestPracticeResponse]
    total: int


class CoachingPatternsResponse(BaseModel):
    """Organization coaching patterns response."""
    org_id: str
    common_outcome_types: Dict[str, int]
    avg_outcomes_per_session: float
    successful_methodologies: List[Dict]
    challenging_stages: List[Dict]


class SimilarPursuitResponse(BaseModel):
    """Similar pursuit response."""
    pursuit_id: str
    name: str
    status: str
    health_score: float
    similarity_score: float


class SimilarPursuitsListResponse(BaseModel):
    """List of similar pursuits."""
    pursuit_id: str
    similar_pursuits: List[SimilarPursuitResponse]
    total: int


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_current_user(request) -> Dict:
    """Get current user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def verify_session_access(session_id: str, current_user: Dict) -> Dict:
    """Verify user has access to coaching session."""
    session = db.get_coaching_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return session


# =============================================================================
# COACHING CONTEXT ENDPOINTS
# =============================================================================

@router.post("/coaching/sessions/{session_id}/context", response_model=CoachingContextResponse)
async def build_coaching_context(
    session_id: str,
    request: BuildContextRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Build comprehensive coaching context for a session.

    Combines pursuit, conversation, portfolio, and methodology context.
    """
    session = await verify_session_access(session_id, current_user)
    pursuit_id = session.get("pursuit_id", "")

    # Convert conversation history
    history = [
        {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
        for msg in request.conversation_history
    ]

    coach = get_convergence_coach()
    context = coach.build_coaching_context(
        pursuit_id=pursuit_id,
        session_id=session_id,
        user_id=current_user["user_id"],
        conversation_history=history
    )

    return CoachingContextResponse(
        pursuit_id=context.pursuit_id,
        user_id=context.user_id,
        org_id=context.org_id,
        methodology_archetype=context.methodology_archetype,
        current_phase=context.current_phase.value,
        coaching_mode=context.coaching_mode.value,
        convergence_signals=context.convergence_signals,
        portfolio_context=context.portfolio_context,
        methodology_guidance=context.methodology_guidance,
        recent_outcomes=context.recent_outcomes
    )


@router.post("/coaching/sessions/{session_id}/enhance", response_model=EnhancedResponseOutput)
async def enhance_coaching_response(
    session_id: str,
    request: EnhanceResponseRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Enhance a base coaching response with convergence awareness.

    Adds methodology-specific language, convergence prompts,
    and portfolio insights.
    """
    session = await verify_session_access(session_id, current_user)
    pursuit_id = session.get("pursuit_id", "")

    # Convert conversation history
    history = [
        {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
        for msg in request.conversation_history
    ]

    coach = get_convergence_coach()

    # Build context
    context = coach.build_coaching_context(
        pursuit_id=pursuit_id,
        session_id=session_id,
        user_id=current_user["user_id"],
        conversation_history=history
    )

    # Enhance response
    enhanced = coach.enhance_response(
        base_response=request.base_response,
        context=context,
        include_portfolio_insights=request.include_portfolio_insights
    )

    logger.info(f"Enhanced coaching response for session {session_id}")

    return EnhancedResponseOutput(
        message=enhanced.message,
        coaching_mode=enhanced.coaching_mode.value,
        convergence_phase=enhanced.convergence_phase.value,
        suggested_actions=enhanced.suggested_actions,
        methodology_hints=enhanced.methodology_hints,
        convergence_prompt=enhanced.convergence_prompt,
        portfolio_insights=enhanced.portfolio_insights,
        metadata=enhanced.metadata
    )


# =============================================================================
# ORG INTELLIGENCE ENDPOINTS
# =============================================================================

@router.get("/orgs/{org_id}/coaching/best-practices", response_model=BestPracticesListResponse)
async def get_best_practices(
    org_id: str,
    pursuit_type: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get organization best practices for coaching.

    Returns insights from successful pursuits.
    """
    # Verify org membership
    membership = db.get_user_membership_in_org(current_user["user_id"], org_id)
    if not membership or membership.get("status") != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    intelligence = get_org_intelligence()
    practices = intelligence.get_org_best_practices(org_id, pursuit_type)

    practice_responses = [
        BestPracticeResponse(
            source_pursuit_id=p.get("source_pursuit_id", ""),
            source_pursuit_name=p.get("source_pursuit_name", ""),
            insight=p.get("insight", ""),
            methodology=p.get("methodology", ""),
            stage=p.get("stage", "")
        )
        for p in practices
    ]

    return BestPracticesListResponse(
        org_id=org_id,
        practices=practice_responses,
        total=len(practice_responses)
    )


@router.get("/orgs/{org_id}/coaching/patterns", response_model=CoachingPatternsResponse)
async def get_coaching_patterns(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get organization-wide coaching patterns.

    Returns common themes, successful strategies, and areas for improvement.
    """
    # Verify org membership
    membership = db.get_user_membership_in_org(current_user["user_id"], org_id)
    if not membership or membership.get("status") != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    intelligence = get_org_intelligence()
    patterns = intelligence.get_org_coaching_patterns(org_id)

    return CoachingPatternsResponse(
        org_id=org_id,
        common_outcome_types=patterns.get("common_outcome_types", {}),
        avg_outcomes_per_session=patterns.get("avg_outcomes_per_session", 0),
        successful_methodologies=patterns.get("successful_methodologies", []),
        challenging_stages=patterns.get("challenging_stages", [])
    )


@router.get("/pursuits/{pursuit_id}/coaching/similar", response_model=SimilarPursuitsListResponse)
async def get_similar_pursuits(
    pursuit_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Find similar pursuits in the organization.

    Useful for learning from comparable initiatives.
    """
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Check access
    if pursuit.get("user_id") != current_user["user_id"]:
        team_members = pursuit.get("sharing", {}).get("team_members", [])
        if not any(m.get("user_id") == current_user["user_id"] for m in team_members):
            raise HTTPException(status_code=403, detail="Access denied")

    org_id = pursuit.get("org_id", "")
    if not org_id:
        return SimilarPursuitsListResponse(
            pursuit_id=pursuit_id,
            similar_pursuits=[],
            total=0
        )

    intelligence = get_org_intelligence()
    similar = intelligence.get_similar_pursuits(org_id, pursuit_id)

    similar_responses = [
        SimilarPursuitResponse(
            pursuit_id=p.get("pursuit_id", ""),
            name=p.get("name", ""),
            status=p.get("status", ""),
            health_score=p.get("health_score", 0.5),
            similarity_score=p.get("similarity_score", 0.0)
        )
        for p in similar
    ]

    return SimilarPursuitsListResponse(
        pursuit_id=pursuit_id,
        similar_pursuits=similar_responses,
        total=len(similar_responses)
    )
