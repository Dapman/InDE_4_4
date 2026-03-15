"""
InDE MVP v3.4 - Discovery API Routes
Endpoints for Innovator Discovery & Team Formation Service (IDTFS).

Endpoints:
- GET /orgs/{org_id}/discovery/search - Search for innovators
- GET /orgs/{org_id}/discovery/profiles - List innovator profiles
- GET /orgs/{org_id}/discovery/profiles/{user_id} - Get specific profile
- PUT /orgs/{org_id}/discovery/profiles/{user_id} - Update profile
- POST /orgs/{org_id}/discovery/profiles/{user_id}/availability - Update availability
- POST /orgs/{org_id}/vouching - Create vouch
- GET /orgs/{org_id}/vouching/{user_id} - Get vouches for user
- GET /orgs/{org_id}/discovery/expertise-types - Get expertise types
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from core.database import db
from discovery.idtfs import (
    get_profile_manager, get_vouching_service,
    get_expertise_calculator, get_expertise_matcher, get_discovery_query,
    AvailabilityStatus, VouchingType, ExpertiseType
)
from middleware.rbac import require_permission
from core.config import IDTFS_CONFIG

logger = logging.getLogger("inde.api.discovery")

router = APIRouter(tags=["discovery"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DiscoverySearchRequest(BaseModel):
    """Discovery search request."""
    gap_description: Optional[str] = Field(None, description="Natural language description of gap/need")
    required_tags: List[str] = Field(default_factory=list, description="Required expertise tags")
    preferred_expertise_types: List[str] = Field(default_factory=list, description="Preferred expertise types")
    min_availability: float = Field(0.0, ge=0.0, le=1.0, description="Minimum availability ratio")
    min_behavioral_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum behavioral expertise score")
    include_vouching: bool = Field(True, description="Include vouching in scoring")
    max_results: int = Field(20, ge=1, le=50, description="Maximum results to return")


class DiscoveryCandidateResponse(BaseModel):
    """Discovery candidate response."""
    user_id: str
    display_name: str
    composite_score: float
    pillar_scores: Dict[str, float]
    matched_tags: List[str]
    expertise_types: List[str]
    availability_status: str
    vouching_summary: Dict[str, Any]


class DiscoverySearchResponse(BaseModel):
    """Discovery search response."""
    query_id: str
    candidates: List[DiscoveryCandidateResponse]
    total_found: int
    search_criteria: Dict[str, Any]


class ProfileResponse(BaseModel):
    """Innovator profile response."""
    user_id: str
    org_id: str
    declared_expertise_tags: List[str]
    inferred_expertise_tags: List[str]
    expertise_types: List[str]
    availability_status: str
    availability_hours_per_week: float
    availability_until: Optional[str]
    discovery_opt_in: bool
    profile_completeness: float
    last_updated: str


class UpdateProfileRequest(BaseModel):
    """Update profile request."""
    declared_expertise_tags: Optional[List[str]] = None
    expertise_types: Optional[List[str]] = None
    discovery_opt_in: Optional[bool] = None
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None


class UpdateAvailabilityRequest(BaseModel):
    """Update availability request."""
    status: str = Field(..., description="FULL_TIME, PART_TIME, LIMITED, UNAVAILABLE")
    hours_per_week: Optional[float] = Field(None, ge=0, le=60)
    available_until: Optional[str] = Field(None, description="ISO date until which available")
    notes: Optional[str] = None


class CreateVouchRequest(BaseModel):
    """Create vouch request."""
    vouchee_user_id: str = Field(..., description="User being vouched for")
    vouch_type: str = Field(..., description="EXPERTISE, CHARACTER, COLLABORATION, DELIVERY")
    expertise_tags: List[str] = Field(default_factory=list, description="Specific tags being vouched")
    strength: str = Field("STANDARD", description="STRONG, STANDARD, QUALIFIED")
    context: Optional[str] = Field(None, description="Context for the vouch")


class VouchResponse(BaseModel):
    """Vouch response."""
    vouch_id: str
    voucher_id: str
    voucher_name: str
    vouch_type: str
    expertise_tags: List[str]
    strength: str
    created_at: str


class VouchingSummaryResponse(BaseModel):
    """Vouching summary response."""
    user_id: str
    total_vouches: int
    vouch_by_type: Dict[str, int]
    vouched_expertise: Dict[str, int]
    reputation_score: float
    vouches: List[VouchResponse]


class ExpertiseTypeResponse(BaseModel):
    """Expertise type response."""
    type_id: str
    name: str
    description: str
    category: str


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_current_user(request) -> Dict:
    """Get current user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def verify_org_access(org_id: str, current_user: Dict) -> Dict:
    """Verify user has access to organization."""
    membership = db.get_user_membership_in_org(current_user["user_id"], org_id)
    if not membership or membership.get("status") != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return membership


# =============================================================================
# DISCOVERY SEARCH ENDPOINTS
# =============================================================================

@router.post("/orgs/{org_id}/discovery/search", response_model=DiscoverySearchResponse)
async def search_innovators(
    org_id: str,
    request: DiscoverySearchRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Search for innovators matching specified criteria.

    Uses IDTFS six-pillar scoring to rank candidates.
    """
    # Verify org access
    await verify_org_access(org_id, current_user)

    # Check permission
    if not require_permission(current_user["user_id"], org_id, "can_discover_members"):
        raise HTTPException(status_code=403, detail="Permission denied: can_discover_members required")

    # Execute search
    discovery = get_discovery_query()
    candidates = discovery.search(
        org_id=org_id,
        gap_description=request.gap_description,
        required_tags=request.required_tags,
        preferred_expertise_types=request.preferred_expertise_types,
        min_availability=request.min_availability,
        min_behavioral_score=request.min_behavioral_score,
        include_vouching=request.include_vouching,
        max_results=request.max_results
    )

    # Build response
    import uuid
    query_id = str(uuid.uuid4())

    candidate_responses = []
    for candidate in candidates:
        # Get user display name
        user = db.get_user(candidate.user_id)
        display_name = user.get("display_name", user.get("email", "Unknown")) if user else "Unknown"

        # Get vouching summary
        vouching_service = get_vouching_service()
        vouch_summary = vouching_service.get_user_reputation(candidate.user_id, org_id)

        candidate_responses.append(DiscoveryCandidateResponse(
            user_id=candidate.user_id,
            display_name=display_name,
            composite_score=candidate.composite_score,
            pillar_scores=candidate.pillar_scores,
            matched_tags=candidate.matched_tags,
            expertise_types=candidate.expertise_types,
            availability_status=candidate.availability_status,
            vouching_summary={
                "total_vouches": vouch_summary.get("total_vouches", 0),
                "reputation_score": vouch_summary.get("reputation_score", 0.5)
            }
        ))

    logger.info(f"Discovery search in org {org_id} by user {current_user['user_id']}: {len(candidates)} results")

    return DiscoverySearchResponse(
        query_id=query_id,
        candidates=candidate_responses,
        total_found=len(candidates),
        search_criteria={
            "gap_description": request.gap_description,
            "required_tags": request.required_tags,
            "preferred_expertise_types": request.preferred_expertise_types,
            "min_availability": request.min_availability,
            "min_behavioral_score": request.min_behavioral_score
        }
    )


# =============================================================================
# PROFILE MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/orgs/{org_id}/discovery/profiles", response_model=List[ProfileResponse])
async def list_profiles(
    org_id: str,
    discovery_opt_in_only: bool = Query(True, description="Only show opted-in profiles"),
    current_user: Dict = Depends(get_current_user)
):
    """
    List innovator profiles in organization.
    """
    await verify_org_access(org_id, current_user)

    profile_manager = get_profile_manager()
    profiles = profile_manager.list_profiles(org_id, discovery_opt_in_only=discovery_opt_in_only)

    return [ProfileResponse(
        user_id=p.user_id,
        org_id=p.org_id,
        declared_expertise_tags=p.declared_expertise_tags,
        inferred_expertise_tags=p.inferred_expertise_tags,
        expertise_types=[et.value for et in p.expertise_types],
        availability_status=p.availability_status.value,
        availability_hours_per_week=p.availability_hours_per_week,
        availability_until=p.availability_until.isoformat() if p.availability_until else None,
        discovery_opt_in=p.discovery_opt_in,
        profile_completeness=p.profile_completeness,
        last_updated=p.last_updated.isoformat()
    ) for p in profiles]


@router.get("/orgs/{org_id}/discovery/profiles/{user_id}", response_model=ProfileResponse)
async def get_profile(
    org_id: str,
    user_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get specific innovator profile.
    """
    await verify_org_access(org_id, current_user)

    profile_manager = get_profile_manager()
    profile = profile_manager.get_profile(user_id, org_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileResponse(
        user_id=profile.user_id,
        org_id=profile.org_id,
        declared_expertise_tags=profile.declared_expertise_tags,
        inferred_expertise_tags=profile.inferred_expertise_tags,
        expertise_types=[et.value for et in profile.expertise_types],
        availability_status=profile.availability_status.value,
        availability_hours_per_week=profile.availability_hours_per_week,
        availability_until=profile.availability_until.isoformat() if profile.availability_until else None,
        discovery_opt_in=profile.discovery_opt_in,
        profile_completeness=profile.profile_completeness,
        last_updated=profile.last_updated.isoformat()
    )


@router.put("/orgs/{org_id}/discovery/profiles/{user_id}", response_model=ProfileResponse)
async def update_profile(
    org_id: str,
    user_id: str,
    request: UpdateProfileRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Update innovator profile.

    Users can only update their own profile unless they have admin permissions.
    """
    membership = await verify_org_access(org_id, current_user)

    # Check authorization
    if current_user["user_id"] != user_id and membership.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Can only update your own profile")

    profile_manager = get_profile_manager()

    # Get or create profile
    profile = profile_manager.get_profile(user_id, org_id)
    if not profile:
        profile = profile_manager.create_profile(user_id, org_id)

    # Update fields
    updates = {}
    if request.declared_expertise_tags is not None:
        updates["declared_expertise_tags"] = request.declared_expertise_tags
    if request.expertise_types is not None:
        updates["expertise_types"] = request.expertise_types
    if request.discovery_opt_in is not None:
        updates["discovery_opt_in"] = request.discovery_opt_in
    if request.bio is not None:
        updates["bio"] = request.bio
    if request.linkedin_url is not None:
        updates["linkedin_url"] = request.linkedin_url

    updated_profile = profile_manager.update_profile(user_id, org_id, updates)

    return ProfileResponse(
        user_id=updated_profile.user_id,
        org_id=updated_profile.org_id,
        declared_expertise_tags=updated_profile.declared_expertise_tags,
        inferred_expertise_tags=updated_profile.inferred_expertise_tags,
        expertise_types=[et.value for et in updated_profile.expertise_types],
        availability_status=updated_profile.availability_status.value,
        availability_hours_per_week=updated_profile.availability_hours_per_week,
        availability_until=updated_profile.availability_until.isoformat() if updated_profile.availability_until else None,
        discovery_opt_in=updated_profile.discovery_opt_in,
        profile_completeness=updated_profile.profile_completeness,
        last_updated=updated_profile.last_updated.isoformat()
    )


@router.post("/orgs/{org_id}/discovery/profiles/{user_id}/availability")
async def update_availability(
    org_id: str,
    user_id: str,
    request: UpdateAvailabilityRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Update user availability status.
    """
    membership = await verify_org_access(org_id, current_user)

    # Check authorization
    if current_user["user_id"] != user_id and membership.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Can only update your own availability")

    # Validate status
    valid_statuses = ["FULL_TIME", "PART_TIME", "LIMITED", "UNAVAILABLE"]
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    profile_manager = get_profile_manager()

    # Parse date if provided
    available_until = None
    if request.available_until:
        try:
            available_until = datetime.fromisoformat(request.available_until)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format for available_until")

    result = profile_manager.update_availability(
        user_id=user_id,
        org_id=org_id,
        status=AvailabilityStatus(request.status),
        hours_per_week=request.hours_per_week,
        available_until=available_until
    )

    return {
        "message": "Availability updated successfully",
        "new_status": request.status,
        "hours_per_week": request.hours_per_week
    }


# =============================================================================
# VOUCHING ENDPOINTS
# =============================================================================

@router.post("/orgs/{org_id}/vouching")
async def create_vouch(
    org_id: str,
    request: CreateVouchRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a vouch for another user.

    Cannot vouch for yourself.
    """
    await verify_org_access(org_id, current_user)

    # Cannot vouch for self
    if current_user["user_id"] == request.vouchee_user_id:
        raise HTTPException(status_code=400, detail="Cannot vouch for yourself")

    # Validate vouchee is in org
    vouchee_membership = db.get_user_membership_in_org(request.vouchee_user_id, org_id)
    if not vouchee_membership or vouchee_membership.get("status") != "active":
        raise HTTPException(status_code=404, detail="Vouchee not found in organization")

    # Validate vouch type
    valid_types = ["EXPERTISE", "CHARACTER", "COLLABORATION", "DELIVERY"]
    if request.vouch_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid vouch type. Must be one of: {valid_types}")

    # Validate strength
    valid_strengths = ["STRONG", "STANDARD", "QUALIFIED"]
    if request.strength not in valid_strengths:
        raise HTTPException(status_code=400, detail=f"Invalid strength. Must be one of: {valid_strengths}")

    vouching_service = get_vouching_service()

    result = vouching_service.create_vouch(
        voucher_id=current_user["user_id"],
        vouchee_id=request.vouchee_user_id,
        org_id=org_id,
        vouch_type=VouchingType(request.vouch_type),
        expertise_tags=request.expertise_tags,
        strength=request.strength,
        context=request.context
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create vouch"))

    logger.info(
        f"Vouch created: {current_user['user_id']} vouched for {request.vouchee_user_id} "
        f"({request.vouch_type}) in org {org_id}"
    )

    return {
        "message": "Vouch created successfully",
        "vouch_id": result.get("vouch_id")
    }


@router.get("/orgs/{org_id}/vouching/{user_id}", response_model=VouchingSummaryResponse)
async def get_user_vouches(
    org_id: str,
    user_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get vouching summary for a user.
    """
    await verify_org_access(org_id, current_user)

    vouching_service = get_vouching_service()

    # Get vouches received
    vouches = vouching_service.get_vouches_for_user(user_id, org_id)

    # Get reputation
    reputation = vouching_service.get_user_reputation(user_id, org_id)

    # Build response
    vouch_responses = []
    for vouch in vouches:
        voucher = db.get_user(vouch.voucher_id)
        voucher_name = voucher.get("display_name", voucher.get("email", "Unknown")) if voucher else "Unknown"

        vouch_responses.append(VouchResponse(
            vouch_id=vouch.vouch_id,
            voucher_id=vouch.voucher_id,
            voucher_name=voucher_name,
            vouch_type=vouch.vouch_type.value,
            expertise_tags=vouch.expertise_tags,
            strength=vouch.strength,
            created_at=vouch.created_at.isoformat()
        ))

    return VouchingSummaryResponse(
        user_id=user_id,
        total_vouches=reputation.get("total_vouches", 0),
        vouch_by_type=reputation.get("vouch_by_type", {}),
        vouched_expertise=reputation.get("vouched_expertise", {}),
        reputation_score=reputation.get("reputation_score", 0.5),
        vouches=vouch_responses
    )


# =============================================================================
# EXPERTISE TYPE ENDPOINTS
# =============================================================================

@router.get("/orgs/{org_id}/discovery/expertise-types", response_model=List[ExpertiseTypeResponse])
async def get_expertise_types(
    org_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get available expertise types for discovery.
    """
    await verify_org_access(org_id, current_user)

    expertise_types = [
        ExpertiseTypeResponse(
            type_id="DOMAIN",
            name="Domain Expert",
            description="Deep expertise in a specific industry or field",
            category="knowledge"
        ),
        ExpertiseTypeResponse(
            type_id="TECHNICAL",
            name="Technical Specialist",
            description="Technical skills in engineering, development, or technology",
            category="skills"
        ),
        ExpertiseTypeResponse(
            type_id="CREATIVE",
            name="Creative Thinker",
            description="Innovative ideation and design thinking",
            category="mindset"
        ),
        ExpertiseTypeResponse(
            type_id="ANALYTICAL",
            name="Analytical Mind",
            description="Data analysis, research, and critical thinking",
            category="mindset"
        ),
        ExpertiseTypeResponse(
            type_id="CONNECTOR",
            name="Connector",
            description="Network building and cross-functional collaboration",
            category="social"
        ),
        ExpertiseTypeResponse(
            type_id="EXECUTOR",
            name="Executor",
            description="Implementation and delivery excellence",
            category="execution"
        ),
        ExpertiseTypeResponse(
            type_id="MENTOR",
            name="Mentor",
            description="Guidance and development of others",
            category="social"
        ),
        ExpertiseTypeResponse(
            type_id="VISIONARY",
            name="Visionary",
            description="Strategic thinking and future orientation",
            category="mindset"
        )
    ]

    return expertise_types


# =============================================================================
# BEHAVIORAL EXPERTISE ENDPOINTS
# =============================================================================

@router.get("/orgs/{org_id}/discovery/profiles/{user_id}/behavioral-score")
async def get_behavioral_score(
    org_id: str,
    user_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get behavioral expertise score for a user.

    Calculated from IKF contributions and coaching interactions.
    """
    await verify_org_access(org_id, current_user)

    calculator = get_expertise_calculator()
    score = calculator.calculate_expertise_score(user_id, org_id)

    return {
        "user_id": user_id,
        "org_id": org_id,
        "overall_score": score.overall_score,
        "component_scores": score.component_scores,
        "evidence_count": score.evidence_count,
        "confidence": score.confidence,
        "last_calculated": score.last_calculated.isoformat()
    }
