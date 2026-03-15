"""
InDE v4.3 - Depth API Routes

Provides depth-framed progress indicators for pursuits.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from auth.middleware import get_current_user
from modules.depth import DepthCalculator, DepthDimension

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class DimensionScoreResponse(BaseModel):
    """Single dimension score for API response."""
    dimension: str
    score: float = Field(..., ge=0.0, le=1.0)
    signal_count: int = Field(..., ge=0)
    strongest_signal: Optional[str] = None
    display_label: str
    richness_phrase: str


class PursuitDepthResponse(BaseModel):
    """Complete depth snapshot for API response."""
    pursuit_id: str
    overall_depth: float = Field(..., ge=0.0, le=1.0)
    dimensions: List[DimensionScoreResponse]
    top_strength: str
    active_frontier: str
    depth_narrative: str
    computed_at: str
    experience_mode: str


@router.get("/pursuits/{pursuit_id}/depth", response_model=PursuitDepthResponse)
async def get_pursuit_depth(
    pursuit_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Returns the current depth snapshot for a pursuit.

    Experience mode is read from the requesting user's preferences.
    Returns 404 if pursuit not found or user lacks access.
    """
    db = request.app.state.db

    # Verify pursuit exists and user has access
    pursuit = db.db.pursuits.find_one({"pursuit_id": pursuit_id})
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Check ownership or team membership
    if pursuit.get("user_id") != current_user["user_id"]:
        # Check team membership
        is_team_member = db.db.team_members.find_one({
            "pursuit_id": pursuit_id,
            "user_id": current_user["user_id"]
        })
        if not is_team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get user's experience mode preference
    user = db.db.users.find_one({"user_id": current_user["user_id"]})
    experience_mode = (
        user.get("preferences", {}).get("experience_mode", "novice")
        if user else "novice"
    )

    # Compute depth snapshot
    calculator = DepthCalculator(db)
    snapshot = calculator.compute_depth_snapshot(
        pursuit_id=pursuit_id,
        experience_mode=experience_mode
    )

    # Convert to response model
    dimension_responses = [
        DimensionScoreResponse(
            dimension=d.dimension.value,
            score=d.score,
            signal_count=d.signal_count,
            strongest_signal=d.strongest_signal,
            display_label=d.display_label,
            richness_phrase=d.richness_phrase,
        )
        for d in snapshot.dimensions
    ]

    return PursuitDepthResponse(
        pursuit_id=snapshot.pursuit_id,
        overall_depth=snapshot.overall_depth,
        dimensions=dimension_responses,
        top_strength=snapshot.top_strength,
        active_frontier=snapshot.active_frontier,
        depth_narrative=snapshot.depth_narrative,
        computed_at=snapshot.computed_at,
        experience_mode=snapshot.experience_mode,
    )
