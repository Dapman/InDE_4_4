"""
InDE v3.1 - Health Monitor API Routes
Pursuit health scoring and zone management.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from auth.middleware import get_current_user

router = APIRouter()


class HealthScoreResponse(BaseModel):
    pursuit_id: str
    score: float
    zone: str
    components: dict
    calculated_at: datetime


@router.get("/{pursuit_id}")
async def get_pursuit_health(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get current health score for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Get latest health score
    health = db.db.health_scores.find_one(
        {"pursuit_id": pursuit_id},
        sort=[("calculated_at", -1)]
    )

    if not health:
        # Calculate on-demand
        health = _calculate_health(db, pursuit_id)

    if "_id" in health:
        del health["_id"]

    return health


@router.get("/{pursuit_id}/history")
async def get_health_history(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user),
    limit: int = 30
):
    """
    Get health score history for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    history = list(db.db.health_scores.find(
        {"pursuit_id": pursuit_id},
        {"_id": 0}
    ).sort("calculated_at", -1).limit(limit))

    return {"pursuit_id": pursuit_id, "history": history}


@router.post("/{pursuit_id}/recalculate")
async def recalculate_health(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Force recalculation of pursuit health.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    health = _calculate_health(db, pursuit_id, store=True)

    # Update pursuit with new health
    db.db.pursuits.update_one(
        {"pursuit_id": pursuit_id},
        {"$set": {
            "health_score": health["score"],
            "health_zone": health["zone"]
        }}
    )

    return health


def _calculate_health(db, pursuit_id: str, store: bool = False) -> dict:
    """Calculate health score for a pursuit."""
    # Placeholder calculation
    # Full implementation would use:
    # - velocity_health (30%)
    # - element_coverage (25%)
    # - phase_timing (20%)
    # - engagement_rhythm (15%)
    # - risk_posture (10%)

    score = 50.0  # Default neutral score

    health = {
        "pursuit_id": pursuit_id,
        "score": score,
        "zone": _zone_from_score(score),
        "components": {
            "velocity_health": 50,
            "element_coverage": 50,
            "phase_timing": 50,
            "engagement_rhythm": 50,
            "risk_posture": 50
        },
        "calculated_at": datetime.now(timezone.utc)
    }

    if store:
        db.db.health_scores.insert_one(health.copy())

    return health


def _zone_from_score(score: float) -> str:
    """Convert health score to zone."""
    if score >= 80:
        return "THRIVING"
    elif score >= 60:
        return "HEALTHY"
    elif score >= 40:
        return "ATTENTION"
    elif score >= 20:
        return "AT_RISK"
    else:
        return "CRITICAL"
