"""
InDE MVP v3.4 - Formation API Routes
Endpoints for Team Formation Flow and Composition Patterns.

Endpoints:
- POST /pursuits/{pursuit_id}/formation/analyze-gaps - Analyze team gaps
- POST /pursuits/{pursuit_id}/formation/recommend - Generate recommendations
- GET /pursuits/{pursuit_id}/formation/recommendations - Get recommendations
- POST /formation/recommendations/{recommendation_id}/accept - Accept recommendation
- POST /formation/recommendations/{recommendation_id}/reject - Reject recommendation
- GET /orgs/{org_id}/formation/patterns - Get composition patterns
- POST /orgs/{org_id}/formation/patterns/analyze - Analyze org patterns
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from core.database import db
from discovery.formation import (
    get_pattern_analyzer, get_gap_analyzer, get_formation_orchestrator,
    FormationStatus, GapSeverity, PatternType
)
from middleware.rbac import require_permission

logger = logging.getLogger("inde.api.formation")

router = APIRouter(tags=["formation"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class AnalyzeGapsRequest(BaseModel):
    """Request to analyze team gaps."""
    include_recommendations: bool = Field(False, description="Also generate recommendations")


class GapResponse(BaseModel):
    """Expertise gap response."""
    gap_id: str
    pursuit_id: str
    gap_description: str
    required_tags: List[str]
    required_expertise_types: List[str]
    severity: str
    identified_at: str
    resolved: bool


class GapAnalysisResponse(BaseModel):
    """Gap analysis response."""
    pursuit_id: str
    gaps: List[GapResponse]
    total_gaps: int
    critical_count: int


class GenerateRecommendationsRequest(BaseModel):
    """Request to generate formation recommendations."""
    gap_id: Optional[str] = Field(None, description="Specific gap to address")
    max_recommendations: int = Field(3, ge=1, le=5, description="Max recommendations to generate")


class RecommendedMemberResponse(BaseModel):
    """Recommended member in formation."""
    user_id: str
    composite_score: float
    matched_tags: List[str]
    expertise_types: List[str]
    availability_status: str


class FormationRecommendationResponse(BaseModel):
    """Formation recommendation response."""
    recommendation_id: str
    pursuit_id: str
    org_id: str
    gap_id: Optional[str]
    recommended_members: List[RecommendedMemberResponse]
    rationale: str
    composition_score: float
    pattern_matches: List[str]
    status: str
    created_at: str
    created_by: str


class RecommendationsListResponse(BaseModel):
    """List of formation recommendations."""
    pursuit_id: str
    recommendations: List[FormationRecommendationResponse]
    total: int


class AcceptRecommendationRequest(BaseModel):
    """Request to accept a recommendation."""
    pass  # No additional fields needed


class RejectRecommendationRequest(BaseModel):
    """Request to reject a recommendation."""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection")


class CompositionPatternResponse(BaseModel):
    """Composition pattern response."""
    pattern_id: str
    pattern_type: str
    pattern_data: Dict[str, Any]
    effectiveness_score: float
    sample_size: int
    confidence: float
    last_updated: str


class PatternListResponse(BaseModel):
    """List of composition patterns."""
    org_id: str
    patterns: List[CompositionPatternResponse]
    total: int


class ScoreTeamRequest(BaseModel):
    """Request to score a team composition."""
    member_ids: List[str] = Field(..., min_items=1, description="User IDs of team members")


class TeamScoreResponse(BaseModel):
    """Team composition score response."""
    composite_score: float
    pattern_scores: Dict[str, float]
    matches: List[str]
    gaps: List[str]
    team_size: int


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_current_user(request) -> Dict:
    """Get current user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def verify_pursuit_access(pursuit_id: str, current_user: Dict) -> Dict:
    """Verify user has access to pursuit."""
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Check ownership or team membership
    if pursuit.get("user_id") == current_user["user_id"]:
        return pursuit

    team_members = pursuit.get("sharing", {}).get("team_members", [])
    if any(m.get("user_id") == current_user["user_id"] for m in team_members):
        return pursuit

    raise HTTPException(status_code=403, detail="Access denied")


# =============================================================================
# GAP ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/pursuits/{pursuit_id}/formation/analyze-gaps", response_model=GapAnalysisResponse)
async def analyze_gaps(
    pursuit_id: str,
    request: AnalyzeGapsRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Analyze expertise gaps in a pursuit's team.

    Identifies missing expertise based on pursuit requirements and
    organizational patterns.
    """
    pursuit = await verify_pursuit_access(pursuit_id, current_user)
    org_id = pursuit.get("org_id", "")

    gap_analyzer = get_gap_analyzer()
    gaps = gap_analyzer.analyze_pursuit_gaps(pursuit_id, org_id)

    gap_responses = [
        GapResponse(
            gap_id=g.gap_id,
            pursuit_id=g.pursuit_id,
            gap_description=g.gap_description,
            required_tags=g.required_tags,
            required_expertise_types=g.required_expertise_types,
            severity=g.severity.value,
            identified_at=g.identified_at.isoformat(),
            resolved=g.resolved
        )
        for g in gaps
    ]

    critical_count = len([g for g in gaps if g.severity == GapSeverity.CRITICAL])

    logger.info(f"Gap analysis for pursuit {pursuit_id}: {len(gaps)} gaps found")

    return GapAnalysisResponse(
        pursuit_id=pursuit_id,
        gaps=gap_responses,
        total_gaps=len(gaps),
        critical_count=critical_count
    )


# =============================================================================
# RECOMMENDATION ENDPOINTS
# =============================================================================

@router.post("/pursuits/{pursuit_id}/formation/recommend", response_model=RecommendationsListResponse)
async def generate_recommendations(
    pursuit_id: str,
    request: GenerateRecommendationsRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate team formation recommendations for a pursuit.

    Uses IDTFS six-pillar scoring to identify optimal candidates.
    """
    pursuit = await verify_pursuit_access(pursuit_id, current_user)
    org_id = pursuit.get("org_id", "")

    orchestrator = get_formation_orchestrator()
    recommendations = orchestrator.generate_recommendations(
        pursuit_id=pursuit_id,
        org_id=org_id,
        created_by=current_user["user_id"],
        gap_id=request.gap_id,
        max_recommendations=request.max_recommendations
    )

    rec_responses = [
        FormationRecommendationResponse(
            recommendation_id=r.recommendation_id,
            pursuit_id=r.pursuit_id,
            org_id=r.org_id,
            gap_id=r.gap_id,
            recommended_members=[
                RecommendedMemberResponse(**m) for m in r.recommended_members
            ],
            rationale=r.rationale,
            composition_score=r.composition_score,
            pattern_matches=r.pattern_matches,
            status=r.status.value,
            created_at=r.created_at.isoformat(),
            created_by=r.created_by
        )
        for r in recommendations
    ]

    logger.info(f"Generated {len(recommendations)} recommendations for pursuit {pursuit_id}")

    return RecommendationsListResponse(
        pursuit_id=pursuit_id,
        recommendations=rec_responses,
        total=len(recommendations)
    )


@router.get("/pursuits/{pursuit_id}/formation/recommendations", response_model=RecommendationsListResponse)
async def get_recommendations(
    pursuit_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get formation recommendations for a pursuit.
    """
    pursuit = await verify_pursuit_access(pursuit_id, current_user)

    # Get recommendations from database
    rec_dicts = db.get_pursuit_formation_recommendations(pursuit_id, status=status)

    rec_responses = [
        FormationRecommendationResponse(
            recommendation_id=r["recommendation_id"],
            pursuit_id=r["pursuit_id"],
            org_id=r["org_id"],
            gap_id=r.get("gap_id"),
            recommended_members=[
                RecommendedMemberResponse(**m) for m in r.get("recommended_members", [])
            ],
            rationale=r.get("rationale", ""),
            composition_score=r.get("composition_score", 0.0),
            pattern_matches=r.get("pattern_matches", []),
            status=r.get("status", "DRAFT"),
            created_at=r.get("created_at", datetime.now(timezone.utc).isoformat()),
            created_by=r.get("created_by", "")
        )
        for r in rec_dicts
    ]

    return RecommendationsListResponse(
        pursuit_id=pursuit_id,
        recommendations=rec_responses,
        total=len(rec_responses)
    )


@router.post("/formation/recommendations/{recommendation_id}/accept")
async def accept_recommendation(
    recommendation_id: str,
    request: AcceptRecommendationRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Accept a formation recommendation.

    Adds recommended members to the pursuit team.
    """
    # Verify access to the recommendation's pursuit
    rec = db.get_formation_recommendation(recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    await verify_pursuit_access(rec["pursuit_id"], current_user)

    orchestrator = get_formation_orchestrator()
    result = orchestrator.accept_recommendation(recommendation_id, current_user["user_id"])

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to accept recommendation"))

    return {
        "message": "Recommendation accepted",
        "members_added": result.get("members_added"),
        "pursuit_id": result.get("pursuit_id")
    }


@router.post("/formation/recommendations/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: str,
    request: RejectRecommendationRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Reject a formation recommendation.
    """
    # Verify access to the recommendation's pursuit
    rec = db.get_formation_recommendation(recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    await verify_pursuit_access(rec["pursuit_id"], current_user)

    orchestrator = get_formation_orchestrator()
    result = orchestrator.reject_recommendation(
        recommendation_id,
        current_user["user_id"],
        request.reason
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to reject recommendation"))

    return {"message": "Recommendation rejected"}


# =============================================================================
# COMPOSITION PATTERN ENDPOINTS
# =============================================================================

@router.get("/orgs/{org_id}/formation/patterns", response_model=PatternListResponse)
async def get_patterns(
    org_id: str,
    pattern_type: Optional[str] = Query(None, description="Filter by pattern type"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get composition patterns for an organization.
    """
    # Verify org membership
    membership = db.get_user_membership_in_org(current_user["user_id"], org_id)
    if not membership or membership.get("status") != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    pattern_analyzer = get_pattern_analyzer()
    patterns = pattern_analyzer.get_org_patterns(org_id)

    # Filter by type if specified
    if pattern_type:
        patterns = [p for p in patterns if p.pattern_type.value == pattern_type]

    pattern_responses = [
        CompositionPatternResponse(
            pattern_id=p.pattern_id,
            pattern_type=p.pattern_type.value,
            pattern_data=p.pattern_data,
            effectiveness_score=p.effectiveness_score,
            sample_size=p.sample_size,
            confidence=p.confidence,
            last_updated=p.last_updated.isoformat()
        )
        for p in patterns
    ]

    return PatternListResponse(
        org_id=org_id,
        patterns=pattern_responses,
        total=len(patterns)
    )


@router.post("/orgs/{org_id}/formation/patterns/analyze", response_model=PatternListResponse)
async def analyze_patterns(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Analyze and update composition patterns for an organization.

    Requires admin permission.
    """
    # Verify org membership with admin role
    membership = db.get_user_membership_in_org(current_user["user_id"], org_id)
    if not membership or membership.get("status") != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    if membership.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin permission required")

    pattern_analyzer = get_pattern_analyzer()
    patterns = pattern_analyzer.analyze_org_patterns(org_id)

    logger.info(f"Pattern analysis for org {org_id}: {len(patterns)} patterns identified")

    pattern_responses = [
        CompositionPatternResponse(
            pattern_id=p.pattern_id,
            pattern_type=p.pattern_type.value,
            pattern_data=p.pattern_data,
            effectiveness_score=p.effectiveness_score,
            sample_size=p.sample_size,
            confidence=p.confidence,
            last_updated=p.last_updated.isoformat()
        )
        for p in patterns
    ]

    return PatternListResponse(
        org_id=org_id,
        patterns=pattern_responses,
        total=len(patterns)
    )


@router.post("/orgs/{org_id}/formation/score-team", response_model=TeamScoreResponse)
async def score_team_composition(
    org_id: str,
    request: ScoreTeamRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Score a proposed team composition against known patterns.

    Useful for evaluating team composition before finalizing.
    """
    # Verify org membership
    membership = db.get_user_membership_in_org(current_user["user_id"], org_id)
    if not membership or membership.get("status") != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    pattern_analyzer = get_pattern_analyzer()
    result = pattern_analyzer.score_team_composition(org_id, request.member_ids)

    return TeamScoreResponse(
        composite_score=result.get("composite_score", 0.5),
        pattern_scores=result.get("pattern_scores", {}),
        matches=result.get("matches", []),
        gaps=result.get("gaps", []),
        team_size=result.get("team_size", len(request.member_ids))
    )
