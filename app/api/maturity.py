"""
InDE v3.1 - Maturity Model API Routes
Innovator maturity scoring and progression.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from auth.middleware import get_current_user
from core.config import MATURITY_LEVELS, MATURITY_DIMENSION_WEIGHTS

router = APIRouter()


class MaturityScoreResponse(BaseModel):
    user_id: str
    maturity_level: str
    composite_score: float
    dimensions: dict
    pursuit_count: int
    completed_pursuits: int
    calculated_at: datetime


@router.get("/me")
async def get_my_maturity(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get current user's maturity profile.
    """
    db = request.app.state.db

    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    scores = user_doc.get("maturity_scores", {})

    return MaturityScoreResponse(
        user_id=user["user_id"],
        maturity_level=user_doc.get("maturity_level", "NOVICE"),
        composite_score=scores.get("composite", 0.0),
        dimensions={
            "discovery_competence": scores.get("discovery_competence", 0.0),
            "validation_rigor": scores.get("validation_rigor", 0.0),
            "reflective_practice": scores.get("reflective_practice", 0.0),
            "velocity_management": scores.get("velocity_management", 0.0),
            "risk_awareness": scores.get("risk_awareness", 0.0),
            "knowledge_contribution": scores.get("knowledge_contribution", 0.0)
        },
        pursuit_count=user_doc.get("pursuit_count", 0),
        completed_pursuits=user_doc.get("completed_pursuits", 0),
        calculated_at=user_doc.get("last_active", datetime.now(timezone.utc))
    )


@router.post("/recalculate")
async def recalculate_maturity(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Force recalculation of maturity score.
    """
    db = request.app.state.db

    scores = _calculate_maturity_scores(db, user["user_id"])

    # Determine level (never regresses)
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    current_level = user_doc.get("maturity_level", "NOVICE")
    new_level = _determine_level(scores, user_doc)

    # Only update if level increases
    final_level = max(
        MATURITY_LEVELS.index(current_level),
        MATURITY_LEVELS.index(new_level)
    )
    final_level_name = MATURITY_LEVELS[final_level]

    db.db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "maturity_scores": scores,
            "maturity_level": final_level_name
        }}
    )

    return {
        "previous_level": current_level,
        "current_level": final_level_name,
        "scores": scores
    }


@router.get("/events")
async def get_maturity_events(
    request: Request,
    user: dict = Depends(get_current_user),
    limit: int = 50
):
    """
    Get maturity-affecting events.
    """
    db = request.app.state.db

    events = list(db.db.maturity_events.find(
        {"user_id": user["user_id"]},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit))

    return {"events": events}


def _calculate_maturity_scores(db, user_id: str) -> dict:
    """Calculate maturity scores based on user activity."""
    # Placeholder - full implementation would analyze:
    # - discovery_competence: Element extraction quality, time-to-vision
    # - validation_rigor: RVE experiments, hypothesis testing
    # - reflective_practice: Retrospective completion, learning capture
    # - velocity_management: Phase timing adherence, progress consistency
    # - risk_awareness: Fear identification, risk validation
    # - knowledge_contribution: IKF contributions

    user = db.db.users.find_one({"user_id": user_id})
    pursuit_count = user.get("pursuit_count", 0) if user else 0
    completed = user.get("completed_pursuits", 0) if user else 0

    # Simple heuristic scores
    base_score = min(pursuit_count * 5, 50)
    completion_bonus = min(completed * 10, 50)

    scores = {
        "discovery_competence": min(base_score + 10, 100),
        "validation_rigor": min(base_score + completion_bonus, 100),
        "reflective_practice": min(completed * 15, 100),
        "velocity_management": min(base_score, 100),
        "risk_awareness": min(base_score + 5, 100),
        "knowledge_contribution": 0  # Requires IKF contributions
    }

    # Calculate weighted composite
    composite = sum(
        scores[dim] * weight
        for dim, weight in MATURITY_DIMENSION_WEIGHTS.items()
    )
    scores["composite"] = round(composite, 1)

    return scores


def _determine_level(scores: dict, user_doc: dict) -> str:
    """Determine maturity level from scores and pursuit count."""
    from core.config import MATURITY_LEVEL_THRESHOLDS

    composite = scores.get("composite", 0)
    pursuit_count = user_doc.get("pursuit_count", 0) if user_doc else 0

    # Check thresholds in descending order
    for level in ["EXPERT", "PROFICIENT", "COMPETENT"]:
        threshold = MATURITY_LEVEL_THRESHOLDS[level]
        if composite >= threshold["min_score"] and pursuit_count >= threshold["min_pursuits"]:
            return level

    return "NOVICE"
