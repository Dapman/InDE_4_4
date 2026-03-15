"""
InDE v4.2 - Coaching API Routes
Real-time coaching interactions for pursuit development.

v4.2: Added re-entry opening endpoint for returning users.
v3.15: Added Getting Started checklist integration.
v3.14: Added onboarding metrics instrumentation.
v3.7.4: Full ScaffoldingEngine integration for AI-powered coaching.
v3.13: Added conversation search endpoint.
"""

from datetime import datetime, timezone
from typing import Optional, List
import logging

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel

from auth.middleware import get_current_user
from core.llm_interface import LLMInterface
from scaffolding.engine import ScaffoldingEngine
from modules.search.conversation_search import ConversationSearchService
from modules.diagnostics.onboarding_metrics import OnboardingMetricsService
from api.user_discovery import update_checklist_item_async

# v4.2: Re-entry module for personalized session openings
from modules.reentry import ReentryGenerator, ReentryContextAssembler

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy-initialized scaffolding engine (initialized on first use with db)
_scaffolding_engine: Optional[ScaffoldingEngine] = None
_llm_interface: Optional[LLMInterface] = None


def get_scaffolding_engine(db) -> ScaffoldingEngine:
    """Get or create the scaffolding engine singleton."""
    global _scaffolding_engine, _llm_interface
    if _scaffolding_engine is None:
        _llm_interface = LLMInterface()
        _scaffolding_engine = ScaffoldingEngine(db, _llm_interface)
    return _scaffolding_engine


class CoachingMessageRequest(BaseModel):
    message: str
    mode: Optional[str] = "coaching"
    context: Optional[dict] = None


class CoachingResponse(BaseModel):
    response: str
    pursuit_id: str
    pursuit_title: Optional[str] = None
    intervention: Optional[dict] = None
    artifacts_generated: List[str] = []
    retrospective_mode: bool = False
    retrospective_progress: int = 0
    health_zone: Optional[str] = None
    timestamp: datetime
    error: bool = False  # v3.15: Signals frontend that response is an error message


@router.post("/{pursuit_id}/message", response_model=CoachingResponse)
async def send_coaching_message(
    request: Request,
    pursuit_id: str,
    data: CoachingMessageRequest,
    user: dict = Depends(get_current_user)
):
    """
    Send a message to the coaching engine and get a response.

    This is the main coaching interaction endpoint. It:
    1. Validates pursuit ownership
    2. Processes message through ScaffoldingEngine
    3. Extracts scaffolding elements from the message
    4. Detects coaching moments and terminal states
    5. Generates an AI-powered coaching response
    6. Records the conversation
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Get scaffolding engine
    engine = get_scaffolding_engine(db)
    engine.set_user_id(user["user_id"])

    # v3.9: Set user's LLM provider preference
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    llm_preference = "auto"
    if user_doc:
        llm_preference = user_doc.get("preferences", {}).get("llm_provider", "auto")
    engine.set_llm_preference(llm_preference)

    # v3.14: Check if this is the first coaching message for onboarding tracking
    is_first_message = db.db.conversation_history.count_documents({
        "pursuit_id": pursuit_id
    }) == 0

    # Process message through scaffolding engine
    try:
        result = engine.process_message(
            message=data.message,
            current_pursuit_id=pursuit_id,
            user_id=user["user_id"]
        )

        # v3.14: Record onboarding metrics for first coaching turn
        if is_first_message:
            try:
                metrics_service = OnboardingMetricsService(db)
                await metrics_service.record_screen_reached(user["user_id"], 2)
            except Exception as e:
                logger.warning(f"Onboarding metrics recording failed: {e}")

            # v3.15: Update Getting Started checklist
            try:
                await update_checklist_item_async(user["user_id"], "coaching_conversation_started")
            except Exception as e:
                logger.warning(f"Discovery checklist update failed: {e}")

        # v3.15: Check for LLM error marker in response
        response_text = result.get("response", "I'm here to help. Tell me more about what you're working on.")
        if response_text.startswith("[COACHING_ERROR]"):
            # Extract user-friendly error message
            error_msg = response_text.replace("[COACHING_ERROR]", "").strip()
            logger.warning(f"LLM error returned to user: {error_msg}")
            return CoachingResponse(
                response=error_msg,
                pursuit_id=pursuit_id,
                pursuit_title=pursuit.get("title"),
                intervention=None,
                artifacts_generated=[],
                retrospective_mode=False,
                retrospective_progress=0,
                health_zone=result.get("health_zone"),
                timestamp=datetime.now(timezone.utc),
                error=True  # v3.15: Signal frontend that this is an error
            )

        return CoachingResponse(
            response=response_text,
            pursuit_id=result.get("pursuit_id", pursuit_id),
            pursuit_title=result.get("pursuit_title", pursuit.get("title")),
            intervention={"type": result.get("intervention_made")} if result.get("intervention_made") else None,
            artifacts_generated=result.get("artifacts_generated", []),
            retrospective_mode=result.get("retrospective_mode", False),
            retrospective_progress=result.get("retrospective_progress", 0),
            health_zone=result.get("health_zone"),
            timestamp=datetime.now(timezone.utc)
        )

    except Exception as e:
        print(f"[Coaching API] Error processing message: {e}")
        import traceback
        traceback.print_exc()

        # Fallback response on error
        return CoachingResponse(
            response="I encountered an issue processing your message. Could you try rephrasing that?",
            pursuit_id=pursuit_id,
            pursuit_title=pursuit.get("title"),
            intervention=None,
            artifacts_generated=[],
            retrospective_mode=False,
            retrospective_progress=0,
            timestamp=datetime.now(timezone.utc)
        )


@router.get("/{pursuit_id}/history")
async def get_coaching_history(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user),
    limit: int = 50
):
    """
    Get coaching conversation history for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    history = list(db.db.conversation_history.find(
        {"pursuit_id": pursuit_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit))

    # Reverse to get chronological order
    history.reverse()

    return {"pursuit_id": pursuit_id, "history": history}


@router.get("/{pursuit_id}/context")
async def get_coaching_context(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get full coaching context for a pursuit.

    Returns scaffolding state, health info, maturity context,
    and any active interventions.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Get scaffolding state
    scaffolding = db.get_scaffolding_state(pursuit_id)

    # Get latest health score
    health = db.db.health_scores.find_one(
        {"pursuit_id": pursuit_id},
        sort=[("calculated_at", -1)]
    )

    # Get user maturity
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    maturity_level = user_doc.get("maturity_level", "NOVICE") if user_doc else "NOVICE"

    # Check for active crisis
    active_crisis = db.db.crisis_sessions.find_one({
        "pursuit_id": pursuit_id,
        "resolved_at": None
    })

    return {
        "pursuit_id": pursuit_id,
        "pursuit_title": pursuit["title"],
        "scaffolding_completeness": _calculate_completeness(scaffolding) if scaffolding else {},
        "health": {
            "score": health.get("score") if health else None,
            "zone": health.get("zone") if health else None
        } if health else None,
        "maturity_level": maturity_level,
        "crisis_active": active_crisis is not None,
        "crisis_type": active_crisis.get("crisis_type") if active_crisis else None
    }


def _calculate_completeness(scaffolding: dict) -> dict:
    """Calculate scaffolding completeness percentages."""
    if not scaffolding:
        return {"vision": 0, "fears": 0, "hypothesis": 0}

    vision = scaffolding.get("vision_elements", {})
    fears = scaffolding.get("fear_elements", {})
    hypothesis = scaffolding.get("hypothesis_elements", {})

    def pct(elements):
        if not elements:
            return 0
        filled = sum(1 for v in elements.values() if v is not None)
        return int(filled / len(elements) * 100) if elements else 0

    return {
        "vision": pct(vision),
        "fears": pct(fears),
        "hypothesis": pct(hypothesis)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# v3.13: CONVERSATION SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{pursuit_id}/search")
async def search_conversations(
    request: Request,
    pursuit_id: str,
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user)
):
    """
    Search coaching conversation history within a pursuit.

    Returns windowed results with context turns around each match.
    The search uses MongoDB full-text search for relevance-ranked results.

    Args:
        pursuit_id: Pursuit to search within
        q: Search query (minimum 2 characters)
        limit: Maximum results per page (1-50, default 20)
        offset: Pagination offset

    Returns:
        {
            "total_matches": int,
            "query": str,
            "pursuit_id": str,
            "results": [...]
        }
    """
    db = request.app.state.db
    service = ConversationSearchService(db)
    return service.search(
        pursuit_id=pursuit_id,
        user_id=user["user_id"],
        query=q,
        limit=limit,
        offset=offset
    )


# ═══════════════════════════════════════════════════════════════════════════════
# v4.2: RE-ENTRY OPENING — PERSONALIZED SESSION START
# ═══════════════════════════════════════════════════════════════════════════════

class OpeningResponse(BaseModel):
    opening: str
    is_returning: bool
    momentum_tier: Optional[str] = None
    gap_tier: Optional[str] = None
    pursuit_id: str
    pursuit_title: Optional[str] = None


@router.get("/{pursuit_id}/opening", response_model=OpeningResponse)
async def get_session_opening(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    v4.2: Get the coach's opening turn for a session.

    For returning users (those with prior conversation history on this pursuit):
    Returns a personalized, momentum-aware opening using the ReentryGenerator.

    For new users or first sessions on this pursuit:
    Returns a standard opening to begin exploration.

    This endpoint should be called when a user opens the coaching interface
    for a pursuit, BEFORE they send their first message.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Check if this is a returning user (has prior conversation history)
    prior_turns = db.db.conversation_history.count_documents({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })
    is_returning = prior_turns > 0

    if not is_returning:
        # First session on this pursuit — standard opening
        return OpeningResponse(
            opening=_get_first_session_opening(pursuit),
            is_returning=False,
            momentum_tier=None,
            gap_tier=None,
            pursuit_id=pursuit_id,
            pursuit_title=pursuit.get("title")
        )

    # Returning user — generate personalized re-entry opening
    try:
        assembler = ReentryContextAssembler(db)
        context = assembler.assemble(user["user_id"], pursuit_id)

        generator = ReentryGenerator()
        opening = generator.generate(context)

        # Log re-entry event for telemetry
        try:
            db.db.reentry_events.insert_one({
                "pursuit_id":    pursuit_id,
                "user_id":       user["user_id"],
                "momentum_tier": context.get("momentum_tier"),
                "gap_tier":      context.get("gap_tier"),
                "gap_hours":     context.get("gap_hours"),
                "timestamp":     datetime.now(timezone.utc),
                "event_type":    "opening_delivered"
            })
        except Exception as e:
            logger.warning(f"Re-entry telemetry failed: {e}")

        return OpeningResponse(
            opening=opening,
            is_returning=True,
            momentum_tier=context.get("momentum_tier"),
            gap_tier=context.get("gap_tier"),
            pursuit_id=pursuit_id,
            pursuit_title=pursuit.get("title")
        )

    except Exception as e:
        logger.error(f"Re-entry opening failed for user={user['user_id']}: {e}")
        # Safe fallback — use standard opening rather than surfacing error
        return OpeningResponse(
            opening=_get_first_session_opening(pursuit),
            is_returning=True,  # Still mark as returning for analytics
            momentum_tier=None,
            gap_tier=None,
            pursuit_id=pursuit_id,
            pursuit_title=pursuit.get("title")
        )


def _get_first_session_opening(pursuit: dict) -> str:
    """
    Generate the standard opening for a first session on a pursuit.

    This is the existing behavior — unchanged from v4.0/v4.1.
    """
    title = pursuit.get("title", "")
    spark = pursuit.get("spark_text", "")

    if spark:
        return (
            f"I see you've started working on \"{title}\". "
            f"You mentioned: \"{spark[:100]}{'...' if len(spark) > 100 else ''}\". "
            f"What's the part of this idea that you find most compelling?"
        )
    elif title:
        return (
            f"Let's explore \"{title}\" together. "
            f"What's the core problem you're trying to solve here?"
        )
    else:
        return (
            "I'm ready to help you develop your idea. "
            "What's the thing you're most excited about working on?"
        )
