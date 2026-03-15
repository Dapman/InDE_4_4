"""
InDE v3.7.0 - IKF API Routes
Innovation Knowledge Fabric contribution management and federation access.

Features:
- Contribution CRUD and approval workflow
- Federation pattern queries
- Benchmark lookups
- Risk indicator aggregation
- User IKF preferences

v3.7.0 changes:
- Integrated Response Transform Middleware for human-readable display
- All internal identifiers stripped from responses
- Enum codes translated to user-friendly labels
"""

from datetime import datetime, timezone
from typing import Optional, List
import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from auth.middleware import get_current_user
from middleware.response_transform import ResponseTransformMiddleware
from shared.display_labels import DisplayLabels

logger = logging.getLogger("inde.api.ikf")

router = APIRouter()


class IKFContributionResponse(BaseModel):
    contribution_id: str
    pursuit_id: str
    package_type: str
    status: str
    generalization_level: int
    created_at: datetime


@router.get("/contributions")
async def list_contributions(
    request: Request,
    user: dict = Depends(get_current_user),
    status: Optional[str] = None
):
    """
    List all IKF contributions for the current user.

    v3.7.0: Response is transformed to use human-readable labels
    and strip internal identifiers.
    """
    db = request.app.state.db

    query = {"user_id": user["user_id"]}
    if status:
        query["status"] = status

    contributions = list(db.db.ikf_contributions.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1))

    # v3.7.0: Transform each contribution for display
    transformed = [
        ResponseTransformMiddleware.transform_contribution_for_display(c)
        for c in contributions
    ]

    return {"contributions": transformed}


@router.get("/contributions/{contribution_id}")
async def get_contribution(
    request: Request,
    contribution_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get a specific IKF contribution.

    v3.7.0: Response is transformed to use human-readable labels.
    Note: contribution_id remains in URL for routing, but is stripped from response body.
    """
    db = request.app.state.db

    contribution = db.db.ikf_contributions.find_one({
        "contribution_id": contribution_id,
        "user_id": user["user_id"]
    })

    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")

    if "_id" in contribution:
        del contribution["_id"]

    # v3.7.0: Transform for display
    return ResponseTransformMiddleware.transform_contribution_for_display(contribution)


@router.post("/contributions/{contribution_id}/approve")
async def approve_contribution(
    request: Request,
    contribution_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Approve an IKF contribution for publication.
    Human review is MANDATORY - this is the approval step.
    """
    db = request.app.state.db

    contribution = db.db.ikf_contributions.find_one({
        "contribution_id": contribution_id,
        "user_id": user["user_id"]
    })

    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")

    if contribution["status"] != "REVIEWED":
        raise HTTPException(
            status_code=400,
            detail="Contribution must be in REVIEWED status to approve"
        )

    db.db.ikf_contributions.update_one(
        {"contribution_id": contribution_id},
        {"$set": {
            "status": "IKF_READY",
            "approved_at": datetime.now(timezone.utc),
            "approved_by": user["user_id"]
        }}
    )

    return {"message": "Contribution approved for IKF publication"}


@router.post("/contributions/{contribution_id}/reject")
async def reject_contribution(
    request: Request,
    contribution_id: str,
    user: dict = Depends(get_current_user),
    reason: Optional[str] = None
):
    """
    Reject an IKF contribution.
    """
    db = request.app.state.db

    contribution = db.db.ikf_contributions.find_one({
        "contribution_id": contribution_id,
        "user_id": user["user_id"]
    })

    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")

    db.db.ikf_contributions.update_one(
        {"contribution_id": contribution_id},
        {"$set": {
            "status": "REJECTED",
            "rejected_at": datetime.now(timezone.utc),
            "rejection_reason": reason
        }}
    )

    return {"message": "Contribution rejected"}


# === Federation Query Endpoints ===

class PatternSearchRequest(BaseModel):
    """Pattern search parameters."""
    methodology: Optional[str] = None
    industry: Optional[str] = None
    phase: Optional[str] = None
    package_type: str = "pattern_contribution"
    limit: int = 10


class BenchmarkRequest(BaseModel):
    """Benchmark query parameters."""
    methodology: str
    phase: str
    industry: Optional[str] = None


class RiskIndicatorRequest(BaseModel):
    """Risk indicator query parameters."""
    phase: Optional[str] = None
    methodology: Optional[str] = None
    industry: Optional[str] = None


class IKFPreferencesUpdate(BaseModel):
    """User IKF preferences."""
    sharing_level: str = "MODERATE"  # AGGRESSIVE, MODERATE, MINIMAL, NONE
    auto_prepare: bool = True
    notify_on_contribution: bool = True


@router.get("/federation/status")
async def get_federation_status(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get federation status and connectivity information.

    v3.7.0: Response transformed to human-readable labels.
    Internal instance_id and connection_state values are hidden.
    """
    from ikf.service_client import IKFServiceClient

    client = IKFServiceClient()
    try:
        status = await client.get_federation_status()
        # v3.7.0: Transform for innovator-friendly display
        return ResponseTransformMiddleware.transform_federation_status(status)
    finally:
        await client.close()


@router.post("/federation/patterns/search")
async def search_patterns(
    request: Request,
    search: PatternSearchRequest,
    user: dict = Depends(get_current_user)
):
    """
    Search federation for relevant patterns.

    Returns success and warning patterns from similar pursuits.

    v3.7.0: Pattern IDs stripped, source badges added.
    """
    from ikf.service_client import IKFServiceClient

    client = IKFServiceClient()
    try:
        result = await client.search_patterns(
            methodology=search.methodology,
            industry=search.industry,
            phase=search.phase,
            package_type=search.package_type,
            limit=search.limit
        )
        # v3.7.0: Transform patterns for display
        if "patterns" in result:
            result["patterns"] = [
                ResponseTransformMiddleware.transform_pattern_for_display(p)
                for p in result.get("patterns", [])
            ]
        return result
    finally:
        await client.close()


@router.post("/federation/benchmarks")
async def get_benchmarks(
    request: Request,
    benchmark: BenchmarkRequest,
    user: dict = Depends(get_current_user)
):
    """
    Get temporal benchmarks for a phase.

    Returns p25, p50, p75 duration statistics from federation data.
    """
    from ikf.service_client import IKFServiceClient

    client = IKFServiceClient()
    try:
        result = await client.get_benchmarks(
            methodology=benchmark.methodology,
            phase=benchmark.phase,
            industry=benchmark.industry
        )
        return result
    finally:
        await client.close()


@router.post("/federation/risks")
async def get_risk_indicators(
    request: Request,
    risk_req: RiskIndicatorRequest,
    user: dict = Depends(get_current_user)
):
    """
    Get aggregated risk indicators from federation.

    Returns common risks and their frequencies by category.
    """
    from ikf.service_client import IKFServiceClient

    client = IKFServiceClient()
    try:
        result = await client.get_risk_indicators(
            phase=risk_req.phase,
            methodology=risk_req.methodology,
            industry=risk_req.industry
        )
        return result
    finally:
        await client.close()


@router.get("/federation/effectiveness/{intervention_type}")
async def get_effectiveness(
    request: Request,
    intervention_type: str,
    methodology: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get intervention effectiveness data.

    Returns effectiveness rates for different intervention types.
    """
    from ikf.service_client import IKFServiceClient

    client = IKFServiceClient()
    try:
        result = await client.get_effectiveness(
            intervention_type=intervention_type,
            methodology=methodology
        )
        return result
    finally:
        await client.close()


@router.get("/insights/{pursuit_id}")
async def get_pursuit_insights(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get IKF-powered insights for a specific pursuit.

    Combines benchmarks, risk indicators, and relevant patterns
    based on the pursuit's context.
    """
    db = request.app.state.db

    # Get pursuit context
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    from ikf.service_client import IKFServiceClient

    client = IKFServiceClient()
    try:
        insights = await client.get_phase_insights(
            methodology=pursuit.get("methodology", "LEAN_STARTUP"),
            phase=pursuit.get("current_phase", ""),
            industry=pursuit.get("industry")
        )

        # Add pursuit-specific context
        insights["pursuit_id"] = pursuit_id
        insights["pursuit_title"] = pursuit.get("title", "")

        return insights
    finally:
        await client.close()


# === User Preferences ===

@router.get("/preferences")
async def get_ikf_preferences(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get user's IKF contribution preferences.

    v3.7.0: sharing_level includes human-readable label.
    """
    db = request.app.state.db

    user_doc = db.db.users.find_one({"_id": user["user_id"]})
    if not user_doc:
        # Return defaults
        prefs = {
            "sharing_level": "MODERATE",
            "auto_prepare": True,
            "notify_on_contribution": True
        }
    else:
        prefs = user_doc.get("ikf_preferences", {
            "sharing_level": "MODERATE",
            "auto_prepare": True,
            "notify_on_contribution": True
        })

    # v3.7.0: Add human-readable label for sharing level
    sharing_level = prefs.get("sharing_level", "MODERATE")
    prefs["sharing_level_label"] = DisplayLabels.get_with_icon("sharing_level", sharing_level)
    prefs["sharing_level_description"] = DisplayLabels.get("sharing_level", sharing_level, "description")

    return prefs


@router.put("/preferences")
async def update_ikf_preferences(
    request: Request,
    preferences: IKFPreferencesUpdate,
    user: dict = Depends(get_current_user)
):
    """
    Update user's IKF contribution preferences.

    Sharing levels:
    - AGGRESSIVE: Auto-prepare on all events
    - MODERATE: Auto-prepare on pursuit completion (default)
    - MINIMAL: Only prepare when explicitly requested
    - NONE: Disable all IKF contributions
    """
    db = request.app.state.db

    if preferences.sharing_level not in ("AGGRESSIVE", "MODERATE", "MINIMAL", "NONE"):
        raise HTTPException(
            status_code=400,
            detail="Invalid sharing level. Must be AGGRESSIVE, MODERATE, MINIMAL, or NONE"
        )

    db.db.users.update_one(
        {"_id": user["user_id"]},
        {"$set": {
            "ikf_preferences": {
                "sharing_level": preferences.sharing_level,
                "auto_prepare": preferences.auto_prepare,
                "notify_on_contribution": preferences.notify_on_contribution,
                "updated_at": datetime.now(timezone.utc)
            }
        }},
        upsert=True
    )

    logger.info(f"Updated IKF preferences for user {user['user_id']}: {preferences.sharing_level}")

    return {"message": "Preferences updated", "preferences": preferences.model_dump()}


# === Contribution Submission ===

@router.post("/contributions/submit")
async def submit_to_federation(
    request: Request,
    contribution_ids: List[str],
    user: dict = Depends(get_current_user)
):
    """
    Submit approved contributions to the federation.

    Only IKF_READY contributions can be submitted.
    """
    db = request.app.state.db

    # Verify all contributions belong to user and are ready
    valid_ids = []
    for cid in contribution_ids:
        contribution = db.db.ikf_contributions.find_one({
            "contribution_id": cid,
            "user_id": user["user_id"]
        })
        if contribution and contribution.get("status") == "IKF_READY":
            valid_ids.append(cid)

    if not valid_ids:
        raise HTTPException(
            status_code=400,
            detail="No valid IKF_READY contributions found"
        )

    from ikf.service_client import IKFServiceClient

    client = IKFServiceClient()
    try:
        result = await client.submit_to_federation(valid_ids)
        return result
    finally:
        await client.close()


@router.get("/contributions/stats")
async def get_contribution_stats(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get contribution statistics for the current user.

    v3.7.0: Status and type labels are human-readable.
    """
    db = request.app.state.db

    pipeline = [
        {"$match": {"user_id": user["user_id"]}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]

    results = list(db.db.ikf_contributions.aggregate(pipeline))
    stats = {r["_id"]: r["count"] for r in results}

    # Get package type breakdown
    type_pipeline = [
        {"$match": {"user_id": user["user_id"]}},
        {"$group": {
            "_id": "$package_type",
            "count": {"$sum": 1}
        }}
    ]

    type_results = list(db.db.ikf_contributions.aggregate(type_pipeline))
    by_type = {r["_id"]: r["count"] for r in type_results}

    # v3.7.0: Transform to human-readable labels
    stats_labeled = {
        DisplayLabels.get("contribution_status", status): count
        for status, count in stats.items()
    }
    types_labeled = {
        DisplayLabels.get("package_type", pkg_type): count
        for pkg_type, count in by_type.items()
    }

    return {
        "by_status": stats_labeled,
        "by_status_raw": stats,  # Keep raw for programmatic use
        "by_type": types_labeled,
        "by_type_raw": by_type,  # Keep raw for programmatic use
        "total": sum(stats.values())
    }
