"""
InDE v3.1 - Analytics API Routes
Portfolio analytics and cross-pursuit insights.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from auth.middleware import get_current_user

router = APIRouter()


class PortfolioAnalyticsResponse(BaseModel):
    user_id: str
    portfolio_health: float
    portfolio_zone: str
    pursuit_count: int
    active_pursuits: int
    terminal_pursuits: int
    calculated_at: datetime


@router.get("/portfolio")
async def get_portfolio_analytics(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get portfolio-level analytics for the current user.
    """
    db = request.app.state.db

    # Get latest portfolio analytics snapshot
    analytics = db.db.portfolio_analytics.find_one(
        {"user_id": user["user_id"]},
        sort=[("calculated_at", -1)]
    )

    if not analytics:
        # Calculate on-demand if not cached
        pursuits = list(db.db.pursuits.find({"user_id": user["user_id"]}))
        active = [p for p in pursuits if p.get("status") == "active"]
        terminal = [p for p in pursuits if p.get("status", "").startswith("COMPLETED") or p.get("status", "").startswith("TERMINATED")]

        # Simple average health calculation
        health_scores = [p.get("health_score", 50) for p in active if p.get("health_score")]
        avg_health = sum(health_scores) / len(health_scores) if health_scores else 50

        analytics = {
            "user_id": user["user_id"],
            "portfolio_health": avg_health,
            "portfolio_zone": _zone_from_score(avg_health),
            "pursuit_count": len(pursuits),
            "active_pursuits": len(active),
            "terminal_pursuits": len(terminal),
            "calculated_at": datetime.now(timezone.utc)
        }

    # Remove MongoDB _id
    if "_id" in analytics:
        del analytics["_id"]

    return analytics


@router.get("/cross-pursuit")
async def get_cross_pursuit_insights(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get cross-pursuit insights and patterns.
    """
    db = request.app.state.db

    pursuits = list(db.db.pursuits.find({
        "user_id": user["user_id"],
        "status": "active"
    }))

    if len(pursuits) < 2:
        return {
            "message": "Need at least 2 active pursuits for cross-pursuit insights",
            "insights": []
        }

    # Placeholder insights - full implementation would use pattern matching
    insights = []

    return {
        "pursuit_count": len(pursuits),
        "insights": insights
    }


@router.get("/effectiveness")
async def get_effectiveness_scorecard(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get innovation effectiveness scorecard.
    """
    db = request.app.state.db

    # Get user's completed pursuits for metrics
    completed = list(db.db.pursuits.find({
        "user_id": user["user_id"],
        "status": {"$regex": "^COMPLETED|^TERMINATED"}
    }))

    return {
        "total_pursuits_completed": len(completed),
        "metrics": {
            "learning_velocity_trend": None,
            "prediction_accuracy": None,
            "risk_validation_roi": None,
            "pattern_application_success": None,
            "fear_resolution_rate": None,
            "retrospective_completeness": None,
            "time_to_decision": None
        },
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }


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
