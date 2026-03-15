"""
Biomimicry API Routes

Provides endpoints for:
- Manual biomimicry pattern queries (for testing/dashboard)
- Feedback recording
- Pattern statistics
- Deferred insight retrieval

The primary biomimicry pathway is through coaching context (via
BiomimicryContextProvider), NOT through these API endpoints.
These are supplementary endpoints for:
1. Testing and development
2. Dashboard analytics
3. Manual exploration
4. Deferred insight management
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("inde.ikf.api.biomimicry")


# ==============================================================================
# Request/Response Models
# ==============================================================================

class AnalyzeChallengeRequest(BaseModel):
    """Request model for manual challenge analysis."""
    challenge_text: str = Field(..., min_length=10, description="The innovation challenge to analyze")
    domain: Optional[str] = Field(None, description="Innovation domain context")
    methodology: Optional[str] = Field(None, description="Active methodology")


class AnalyzeChallengeResponse(BaseModel):
    """Response model for challenge analysis."""
    matches: List[dict]
    extracted_functions: List[str] = []
    analysis_time_ms: float


class FeedbackRequest(BaseModel):
    """Request model for recording feedback."""
    match_id: str = Field(..., description="The biomimicry match ID")
    pattern_id: str = Field(..., description="The pattern ID")
    pursuit_id: str = Field(..., description="The pursuit ID")
    response: str = Field(..., description="Response: explored|accepted|deferred|dismissed")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Optional 1-5 rating")
    methodology: Optional[str] = Field(None, description="Active methodology")


class PatternStatsResponse(BaseModel):
    """Response model for pattern statistics."""
    total: int
    by_category: dict
    by_source: dict
    triz_coverage: str


# ==============================================================================
# Router Factory
# ==============================================================================

def create_biomimicry_router(analyzer, feedback, db) -> APIRouter:
    """
    Create the biomimicry API router with dependencies injected.

    Args:
        analyzer: BiomimicryAnalyzer instance
        feedback: BiomimicryFeedback instance
        db: MongoDB database instance

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/v1/biomimicry", tags=["biomimicry"])

    @router.post("/analyze", response_model=AnalyzeChallengeResponse)
    async def analyze_challenge(request: AnalyzeChallengeRequest):
        """
        Manually analyze a challenge for biomimicry opportunities.

        This endpoint is for testing and dashboard use. The primary
        biomimicry pathway is through coaching context.

        Returns matched biological strategies with relevance scores.
        """
        import time
        start = time.time()

        try:
            results = await analyzer.analyze_challenge(
                challenge_context=request.challenge_text,
                pursuit_domain=request.domain,
                active_methodology=request.methodology
            )

            elapsed_ms = (time.time() - start) * 1000

            return AnalyzeChallengeResponse(
                matches=[r.to_dict() for r in results],
                analysis_time_ms=round(elapsed_ms, 2)
            )

        except Exception as e:
            logger.error(f"Challenge analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/feedback")
    async def record_feedback(request: FeedbackRequest):
        """
        Record innovator response to biomimicry insight.

        Called when an innovator responds to a biomimicry coaching offer
        with: explored, accepted, deferred, or dismissed.
        """
        valid_responses = ["explored", "accepted", "deferred", "dismissed"]
        if request.response not in valid_responses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid response. Must be one of: {valid_responses}"
            )

        try:
            result = await feedback.record_response(
                match_id=request.match_id,
                pattern_id=request.pattern_id,
                pursuit_id=request.pursuit_id,
                response=request.response,
                feedback_rating=request.rating,
                methodology=request.methodology
            )
            return result

        except Exception as e:
            logger.error(f"Feedback recording failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/patterns/stats", response_model=PatternStatsResponse)
    async def get_pattern_stats():
        """
        Get biomimicry pattern database statistics.

        Returns counts by category, source, and TRIZ coverage percentage.
        """
        try:
            stats = await analyzer.get_pattern_stats()
            return PatternStatsResponse(**stats)

        except Exception as e:
            logger.error(f"Failed to get pattern stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/patterns")
    async def list_patterns(
        category: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 20
    ):
        """
        List biomimicry patterns with optional filtering.

        Args:
            category: Filter by category (e.g., THERMAL_REGULATION)
            source: Filter by source (curated, ikf_federation, org_contributed)
            limit: Maximum results (default 20)
        """
        query = {}
        if category:
            query["category"] = category
        if source:
            query["source"] = source

        patterns = list(
            db.biomimicry_patterns.find(query)
            .sort([("acceptance_rate", -1), ("match_count", -1)])
            .limit(limit)
        )

        # Remove MongoDB _id for serialization
        for p in patterns:
            p.pop("_id", None)
            # Convert datetime to ISO string
            if p.get("created_at"):
                p["created_at"] = p["created_at"].isoformat()
            if p.get("updated_at"):
                p["updated_at"] = p["updated_at"].isoformat()

        return {"patterns": patterns, "count": len(patterns)}

    @router.get("/patterns/{pattern_id}")
    async def get_pattern(pattern_id: str):
        """
        Get a specific biomimicry pattern by ID.
        """
        pattern = await analyzer.get_pattern_by_id(pattern_id)
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")

        pattern.pop("_id", None)
        if pattern.get("created_at"):
            pattern["created_at"] = pattern["created_at"].isoformat()
        if pattern.get("updated_at"):
            pattern["updated_at"] = pattern["updated_at"].isoformat()

        return pattern

    @router.get("/patterns/{pattern_id}/feedback")
    async def get_pattern_feedback(pattern_id: str):
        """
        Get feedback summary for a specific pattern.

        Returns match count, acceptance rate, response breakdown,
        and average rating.
        """
        try:
            summary = await feedback.get_pattern_feedback_summary(pattern_id)
            if summary.get("error"):
                raise HTTPException(status_code=404, detail=summary["error"])
            return summary

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get pattern feedback: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/deferred/{pursuit_id}")
    async def get_deferred_insights(pursuit_id: str):
        """
        Retrieve deferred biomimicry insights for a pursuit.

        Returns insights that were deferred for later consideration.
        """
        try:
            items = await feedback.get_deferred_insights(pursuit_id)

            # Clean for serialization
            for item in items:
                item.pop("_id", None)
                if item.get("created_at"):
                    item["created_at"] = item["created_at"].isoformat()

            return {"deferred_insights": items, "count": len(items)}

        except Exception as e:
            logger.error(f"Failed to get deferred insights: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/deferred/{pursuit_id}/{pattern_id}/activate")
    async def activate_deferred_insight(pursuit_id: str, pattern_id: str):
        """
        Activate a previously deferred biomimicry insight.

        Called when an innovator revisits a deferred insight
        and wants to explore or apply it.
        """
        try:
            success = await feedback.activate_deferred_insight(pursuit_id, pattern_id)
            if not success:
                raise HTTPException(
                    status_code=404,
                    detail="Deferred insight not found or already activated"
                )
            return {"status": "activated", "pattern_id": pattern_id}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to activate deferred insight: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/history/{pursuit_id}")
    async def get_pursuit_biomimicry_history(pursuit_id: str):
        """
        Get all biomimicry interactions for a pursuit.

        Returns chronological list of all biomimicry matches and responses.
        """
        try:
            history = await feedback.get_pursuit_biomimicry_history(pursuit_id)

            # Clean for serialization
            for item in history:
                if item.get("created_at"):
                    item["created_at"] = item["created_at"].isoformat()
                if item.get("responded_at"):
                    item["responded_at"] = item["responded_at"].isoformat()

            return {"history": history, "count": len(history)}

        except Exception as e:
            logger.error(f"Failed to get biomimicry history: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/categories")
    async def get_categories():
        """
        Get list of biomimicry categories with counts.
        """
        categories = [
            "THERMAL_REGULATION",
            "STRUCTURAL_STRENGTH",
            "WATER_MANAGEMENT",
            "ENERGY_EFFICIENCY",
            "SWARM_INTELLIGENCE",
            "SELF_HEALING",
            "COMMUNICATION",
            "ADAPTATION"
        ]

        result = []
        for cat in categories:
            count = db.biomimicry_patterns.count_documents({"category": cat})
            result.append({"category": cat, "count": count})

        return {"categories": result}

    @router.get("/functions")
    async def get_functions():
        """
        Get list of valid biomimicry functions for matching.
        """
        from biomimicry.challenge_analyzer import VALID_FUNCTIONS
        return {"functions": VALID_FUNCTIONS}

    return router
