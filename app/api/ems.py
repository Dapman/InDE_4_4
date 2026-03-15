"""
InDE EMS v3.7.2 - Observation & Inference API Endpoints

API endpoints for EMS process observation and pattern inference. These endpoints
are used by the UI to display observation status, retrieve observation
summaries, manage the observation lifecycle, and trigger pattern inference.

v3.7.1 Endpoints (Observation):
- GET /api/ems/pursuit/{pursuit_id}/status
- GET /api/ems/pursuit/{pursuit_id}/observations
- GET /api/ems/pursuit/{pursuit_id}/summary
- POST /api/ems/pursuit/{pursuit_id}/pause
- POST /api/ems/pursuit/{pursuit_id}/resume
- GET /api/ems/innovator/{innovator_id}/synthesis-eligibility
- GET /api/ems/innovator/{innovator_id}/adhoc-pursuits

v3.7.2 Endpoints (Inference & ADL):
- POST /api/ems/innovator/{innovator_id}/infer-patterns
- GET /api/ems/innovator/{innovator_id}/inference-result
- POST /api/ems/innovator/{innovator_id}/generate-archetype
- GET /api/ems/innovator/{innovator_id}/archetype
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ems.process_observer import get_process_observer, ObservationType
from ems.pattern_inference import get_pattern_inference_engine
from ems.adl_generator import get_adl_generator
from shared.display_labels import DisplayLabels
from middleware.response_transform import ResponseTransformMiddleware

logger = logging.getLogger("inde.api.ems")

router = APIRouter(prefix="/api/ems", tags=["EMS"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ObservationStatusResponse(BaseModel):
    """Response model for observation status."""
    pursuit_id: str
    is_adhoc: bool
    observation_enabled: bool
    observation_status: str
    observation_status_label: str
    observation_status_icon: str
    observation_count: int
    started_at: Optional[str] = None
    synthesis_eligible: bool = False


class ObservationSummaryResponse(BaseModel):
    """Response model for observation summary."""
    pursuit_id: str
    total_observations: int
    by_type: Dict[str, int]
    total_weight: float
    external_influence_count: int
    timeline_start: Optional[str]
    timeline_end: Optional[str]
    duration_hours: float


class ObservationListItem(BaseModel):
    """Single observation in list response."""
    sequence_number: int
    observation_type: str
    observation_type_label: str
    observation_type_icon: str
    timestamp: str
    signal_weight: float
    is_external_influence: bool
    details: Dict


class ObservationListResponse(BaseModel):
    """Response model for observation list."""
    pursuit_id: str
    observations: List[ObservationListItem]
    total_count: int


class SynthesisEligibilityResponse(BaseModel):
    """Response model for synthesis eligibility check."""
    innovator_id: str
    eligibility: str
    eligibility_label: str
    eligibility_icon: str
    eligibility_description: str
    completed_adhoc_pursuits: int
    threshold_for_eligibility: int
    threshold_for_high_confidence: int
    pursuits_until_eligible: int
    pursuits_until_high_confidence: int


class AdhocPursuitSummary(BaseModel):
    """Summary of an ad-hoc pursuit for list view."""
    pursuit_id: str
    name: str
    status: str
    observation_status: str
    observation_count: int
    created_at: str
    completed_at: Optional[str] = None


class AdhocPursuitsResponse(BaseModel):
    """Response model for ad-hoc pursuits list."""
    innovator_id: str
    pursuits: List[AdhocPursuitSummary]
    total_count: int


class ActionResponse(BaseModel):
    """Generic action response."""
    success: bool
    message: str
    pursuit_id: str


# =============================================================================
# v3.7.2: INFERENCE & ADL REQUEST/RESPONSE MODELS
# =============================================================================

class PatternSummary(BaseModel):
    """Summary of a discovered pattern."""
    pattern_type: str
    pattern_type_label: str
    count: int
    avg_frequency: float


class ConfidenceScores(BaseModel):
    """Confidence scores for inference results."""
    overall: float
    overall_label: str
    sample_size_score: float
    consistency_score: float
    outcome_association_score: float
    distinctiveness_score: float


class InferenceResultResponse(BaseModel):
    """Response model for pattern inference results."""
    innovator_id: str
    inference_timestamp: str
    sufficient_data: bool
    pursuit_count: int
    patterns_summary: List[PatternSummary]
    confidence: ConfidenceScores
    synthesis_ready: bool


class ArchetypePhase(BaseModel):
    """Phase definition in generated archetype."""
    id: str
    name: str
    sequence: int
    position: str
    description: str


class ArchetypeResponse(BaseModel):
    """Response model for generated archetype."""
    archetype_id: Optional[str]
    adl_version: str
    generated_at: str
    archetype_name: Optional[str]
    archetype_description: Optional[str]
    origin: str
    origin_label: str
    phases: List[ArchetypePhase]
    confidence_level: float
    confidence_label: str
    synthesis_ready: bool


class InferenceActionResponse(BaseModel):
    """Response for inference actions."""
    success: bool
    message: str
    innovator_id: str
    synthesis_ready: bool = False


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/pursuit/{pursuit_id}/status", response_model=ObservationStatusResponse)
async def get_observation_status(pursuit_id: str):
    """
    Get the observation status for a pursuit.

    Returns whether observation is active, the count of observations,
    and synthesis eligibility.
    """
    observer = get_process_observer()

    # Check if pursuit exists and is ad-hoc
    from core.database import db
    pursuit = db.get_pursuit(pursuit_id)

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    is_adhoc = pursuit.get("archetype") == "ad_hoc"
    adhoc_metadata = pursuit.get("adhoc_metadata", {})

    observation_status = adhoc_metadata.get("observation_status", "INACTIVE")
    observation_count = adhoc_metadata.get("observation_count", 0)
    started_at = adhoc_metadata.get("observation_started_at")

    # Check synthesis eligibility
    innovator_id = pursuit.get("user_id", "")
    synthesis_eligible = False
    if innovator_id and is_adhoc:
        eligibility = observer.get_synthesis_eligibility(innovator_id)
        synthesis_eligible = eligibility["eligibility"] in ["ELIGIBLE", "HIGH_CONFIDENCE"]

    return ObservationStatusResponse(
        pursuit_id=pursuit_id,
        is_adhoc=is_adhoc,
        observation_enabled=observer.is_observation_enabled(pursuit_id) if is_adhoc else False,
        observation_status=observation_status,
        observation_status_label=DisplayLabels.get("observation_status", observation_status),
        observation_status_icon=DisplayLabels.get("observation_status", observation_status, "icon"),
        observation_count=observation_count,
        started_at=started_at,
        synthesis_eligible=synthesis_eligible,
    )


@router.get("/pursuit/{pursuit_id}/observations", response_model=ObservationListResponse)
async def get_observations(
    pursuit_id: str,
    exclude_coaching: bool = Query(False, description="Exclude coaching interactions"),
    min_weight: float = Query(0.0, description="Minimum signal weight", ge=0.0, le=1.0),
    limit: int = Query(100, description="Maximum observations to return", ge=1, le=500),
    offset: int = Query(0, description="Offset for pagination", ge=0),
):
    """
    Get list of observations for a pursuit.

    Supports filtering by type, weight, and pagination.
    """
    observer = get_process_observer()

    if not observer.is_adhoc_pursuit(pursuit_id):
        raise HTTPException(status_code=400, detail="Not an ad-hoc pursuit")

    observations = observer.get_observations(
        pursuit_id=pursuit_id,
        exclude_coaching=exclude_coaching,
        min_weight=min_weight,
    )

    total_count = len(observations)

    # Apply pagination
    observations = observations[offset:offset + limit]

    # Transform to response format
    items = []
    for obs in observations:
        items.append(ObservationListItem(
            sequence_number=obs.sequence_number,
            observation_type=obs.observation_type.value,
            observation_type_label=DisplayLabels.get("observation_type", obs.observation_type.value),
            observation_type_icon=DisplayLabels.get("observation_type", obs.observation_type.value, "icon"),
            timestamp=obs.timestamp.isoformat(),
            signal_weight=obs.signal_weight,
            is_external_influence=obs.is_external_influence,
            details=obs.details,
        ))

    return ObservationListResponse(
        pursuit_id=pursuit_id,
        observations=items,
        total_count=total_count,
    )


@router.get("/pursuit/{pursuit_id}/summary", response_model=ObservationSummaryResponse)
async def get_observation_summary(pursuit_id: str):
    """
    Get aggregated summary of observations for a pursuit.

    Includes counts by type, total weight, timeline, and duration.
    """
    observer = get_process_observer()

    if not observer.is_adhoc_pursuit(pursuit_id):
        raise HTTPException(status_code=400, detail="Not an ad-hoc pursuit")

    summary = observer.get_observation_summary(pursuit_id)

    return ObservationSummaryResponse(
        pursuit_id=pursuit_id,
        total_observations=summary["total_observations"],
        by_type=summary["by_type"],
        total_weight=summary["total_weight"],
        external_influence_count=summary["external_influence_count"],
        timeline_start=summary["timeline_start"],
        timeline_end=summary["timeline_end"],
        duration_hours=summary["duration_hours"],
    )


@router.post("/pursuit/{pursuit_id}/pause", response_model=ActionResponse)
async def pause_observation(pursuit_id: str):
    """
    Pause observation for a pursuit.

    The innovator can resume observation at any time.
    """
    observer = get_process_observer()

    if not observer.is_adhoc_pursuit(pursuit_id):
        raise HTTPException(status_code=400, detail="Not an ad-hoc pursuit")

    success = observer.pause_observation(pursuit_id)

    return ActionResponse(
        success=success,
        message="Observation paused" if success else "Failed to pause observation",
        pursuit_id=pursuit_id,
    )


@router.post("/pursuit/{pursuit_id}/resume", response_model=ActionResponse)
async def resume_observation(pursuit_id: str):
    """
    Resume paused observation for a pursuit.
    """
    observer = get_process_observer()

    if not observer.is_adhoc_pursuit(pursuit_id):
        raise HTTPException(status_code=400, detail="Not an ad-hoc pursuit")

    success = observer.resume_observation(pursuit_id)

    return ActionResponse(
        success=success,
        message="Observation resumed" if success else "Failed to resume observation",
        pursuit_id=pursuit_id,
    )


@router.get("/innovator/{innovator_id}/synthesis-eligibility", response_model=SynthesisEligibilityResponse)
async def get_synthesis_eligibility(innovator_id: str):
    """
    Check if an innovator is eligible for methodology synthesis.

    Returns eligibility status and progress toward thresholds.
    """
    observer = get_process_observer()
    eligibility = observer.get_synthesis_eligibility(innovator_id)

    return SynthesisEligibilityResponse(
        innovator_id=innovator_id,
        eligibility=eligibility["eligibility"],
        eligibility_label=DisplayLabels.get("synthesis_eligibility", eligibility["eligibility"]),
        eligibility_icon=DisplayLabels.get("synthesis_eligibility", eligibility["eligibility"], "icon"),
        eligibility_description=DisplayLabels.get(
            "synthesis_eligibility", eligibility["eligibility"], "description"
        ),
        completed_adhoc_pursuits=eligibility["completed_adhoc_pursuits"],
        threshold_for_eligibility=eligibility["threshold_for_eligibility"],
        threshold_for_high_confidence=eligibility["threshold_for_high_confidence"],
        pursuits_until_eligible=eligibility["pursuits_until_eligible"],
        pursuits_until_high_confidence=eligibility["pursuits_until_high_confidence"],
    )


@router.get("/innovator/{innovator_id}/adhoc-pursuits", response_model=AdhocPursuitsResponse)
async def get_adhoc_pursuits(
    innovator_id: str,
    limit: int = Query(20, description="Maximum pursuits to return", ge=1, le=100),
):
    """
    Get list of ad-hoc pursuits for an innovator.

    Used in synthesis UI to show which pursuits will contribute to
    methodology discovery.
    """
    from core.database import db

    # Get all ad-hoc pursuits for this innovator
    pursuits = db.get_synthesis_eligible_pursuits(innovator_id)
    pursuits = pursuits[:limit]

    summaries = []
    for p in pursuits:
        adhoc_meta = p.get("adhoc_metadata", {})
        summaries.append(AdhocPursuitSummary(
            pursuit_id=p.get("pursuit_id", ""),
            name=p.get("name", "Untitled Pursuit"),
            status=p.get("status", "unknown"),
            observation_status=adhoc_meta.get("observation_status", "UNKNOWN"),
            observation_count=adhoc_meta.get("observation_count", 0),
            created_at=p.get("created_at", ""),
            completed_at=adhoc_meta.get("observation_ended_at"),
        ))

    return AdhocPursuitsResponse(
        innovator_id=innovator_id,
        pursuits=summaries,
        total_count=len(summaries),
    )


# =============================================================================
# v3.7.2: INFERENCE & ADL ENDPOINTS
# =============================================================================

@router.post("/innovator/{innovator_id}/infer-patterns", response_model=InferenceActionResponse)
async def infer_patterns(
    innovator_id: str,
    min_weight: float = Query(0.3, description="Minimum observation weight", ge=0.0, le=1.0),
):
    """
    Trigger pattern inference for an innovator.

    Analyzes all completed ad-hoc pursuits to discover methodology patterns
    using sequence mining, phase clustering, transition inference, and
    dependency mapping algorithms.
    """
    engine = get_pattern_inference_engine()

    try:
        result = engine.infer_patterns(innovator_id, min_weight=min_weight)

        # Store result for later retrieval
        from core.database import db
        db.store_inference_result(innovator_id, result)

        return InferenceActionResponse(
            success=True,
            message="Pattern inference completed",
            innovator_id=innovator_id,
            synthesis_ready=result.get("synthesis_ready", False),
        )

    except Exception as e:
        logger.error(f"Pattern inference failed for {innovator_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Pattern inference failed: {str(e)}"
        )


@router.get("/innovator/{innovator_id}/inference-result", response_model=InferenceResultResponse)
async def get_inference_result(innovator_id: str):
    """
    Get the latest pattern inference result for an innovator.

    Returns discovered patterns, confidence scores, and synthesis readiness.
    """
    from core.database import db

    result = db.get_latest_inference_result(innovator_id)

    if not result:
        # No stored result, run inference now
        engine = get_pattern_inference_engine()
        result = engine.infer_patterns(innovator_id)
        db.store_inference_result(innovator_id, result)

    # Build patterns summary
    patterns = result.get("patterns", {})
    patterns_summary = []

    sequences = patterns.get("sequences", [])
    if sequences:
        avg_freq = sum(s.get("frequency", 0) for s in sequences) / len(sequences)
        patterns_summary.append(PatternSummary(
            pattern_type="sequence",
            pattern_type_label=DisplayLabels.get("pattern_type", "sequence"),
            count=len(sequences),
            avg_frequency=round(avg_freq, 2),
        ))

    phases = patterns.get("phases", [])
    if phases:
        avg_freq = sum(p.get("frequency", 0) for p in phases) / len(phases)
        patterns_summary.append(PatternSummary(
            pattern_type="phase",
            pattern_type_label=DisplayLabels.get("pattern_type", "phase"),
            count=len(phases),
            avg_frequency=round(avg_freq, 2),
        ))

    transitions = patterns.get("transitions", [])
    if transitions:
        avg_freq = sum(t.get("frequency", 0) for t in transitions) / len(transitions)
        patterns_summary.append(PatternSummary(
            pattern_type="transition",
            pattern_type_label=DisplayLabels.get("pattern_type", "transition"),
            count=len(transitions),
            avg_frequency=round(avg_freq, 2),
        ))

    dependencies = patterns.get("dependencies", [])
    if dependencies:
        avg_strength = sum(d.get("strength", 0) for d in dependencies) / len(dependencies)
        patterns_summary.append(PatternSummary(
            pattern_type="dependency",
            pattern_type_label=DisplayLabels.get("pattern_type", "dependency"),
            count=len(dependencies),
            avg_frequency=round(avg_strength, 2),
        ))

    # Build confidence response
    conf = result.get("confidence", {})
    overall = conf.get("overall", 0)

    # Determine confidence level label
    if overall >= 0.8:
        conf_label = DisplayLabels.get("confidence_level", "very_high")
    elif overall >= 0.6:
        conf_label = DisplayLabels.get("confidence_level", "high")
    elif overall >= 0.4:
        conf_label = DisplayLabels.get("confidence_level", "moderate")
    else:
        conf_label = DisplayLabels.get("confidence_level", "low")

    confidence = ConfidenceScores(
        overall=overall,
        overall_label=conf_label,
        sample_size_score=conf.get("sample_size_score", 0),
        consistency_score=conf.get("consistency_score", 0),
        outcome_association_score=conf.get("outcome_association_score", 0),
        distinctiveness_score=conf.get("distinctiveness_score", 0),
    )

    return InferenceResultResponse(
        innovator_id=innovator_id,
        inference_timestamp=result.get("inference_timestamp", ""),
        sufficient_data=result.get("sufficient_data", False),
        pursuit_count=result.get("pursuit_count", 0),
        patterns_summary=patterns_summary,
        confidence=confidence,
        synthesis_ready=result.get("synthesis_ready", False),
    )


@router.post("/innovator/{innovator_id}/generate-archetype", response_model=InferenceActionResponse)
async def generate_archetype(
    innovator_id: str,
    archetype_name: Optional[str] = Query(None, description="Custom name for archetype"),
):
    """
    Generate a methodology archetype from inferred patterns.

    Transforms pattern inference results into an ADL (Archetype Definition
    Language) archetype that can be used for future guided pursuits.
    """
    generator = get_adl_generator()

    try:
        result = generator.generate_archetype(
            innovator_id=innovator_id,
            archetype_name=archetype_name,
        )

        # Store archetype if generated
        if result.get("archetype"):
            from core.database import db
            db.store_generated_archetype(innovator_id, result)

            return InferenceActionResponse(
                success=True,
                message=f"Archetype '{result['archetype']['name']}' generated",
                innovator_id=innovator_id,
                synthesis_ready=True,
            )
        else:
            return InferenceActionResponse(
                success=False,
                message=result.get("synthesis_metadata", {}).get("reason", "Insufficient data"),
                innovator_id=innovator_id,
                synthesis_ready=False,
            )

    except Exception as e:
        logger.error(f"Archetype generation failed for {innovator_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Archetype generation failed: {str(e)}"
        )


@router.get("/innovator/{innovator_id}/archetype", response_model=ArchetypeResponse)
async def get_archetype(innovator_id: str):
    """
    Get the latest generated archetype for an innovator.

    Returns the archetype definition including phases, tools, and artifacts.
    """
    from core.database import db

    result = db.get_latest_archetype(innovator_id)

    if not result:
        # No stored archetype, try to generate one
        generator = get_adl_generator()
        result = generator.generate_archetype(innovator_id)

        if result.get("archetype"):
            db.store_generated_archetype(innovator_id, result)

    archetype = result.get("archetype")
    synthesis_ready = archetype is not None

    if not archetype:
        # Return minimal response for insufficient data
        return ArchetypeResponse(
            archetype_id=None,
            adl_version=result.get("adl_version", "1.0"),
            generated_at=result.get("generated_at", ""),
            archetype_name=None,
            archetype_description=None,
            origin="synthesized",
            origin_label=DisplayLabels.get("archetype_origin", "synthesized"),
            phases=[],
            confidence_level=0,
            confidence_label=DisplayLabels.get("confidence_level", "low"),
            synthesis_ready=False,
        )

    # Build phases response
    phases = []
    for p in archetype.get("phases", []):
        phases.append(ArchetypePhase(
            id=p.get("id", ""),
            name=p.get("name", ""),
            sequence=p.get("sequence", 0),
            position=p.get("position", "middle"),
            description=p.get("description", ""),
        ))

    confidence_level = archetype.get("confidence_level", 0)
    if confidence_level >= 0.8:
        conf_label = DisplayLabels.get("confidence_level", "very_high")
    elif confidence_level >= 0.6:
        conf_label = DisplayLabels.get("confidence_level", "high")
    elif confidence_level >= 0.4:
        conf_label = DisplayLabels.get("confidence_level", "moderate")
    else:
        conf_label = DisplayLabels.get("confidence_level", "low")

    return ArchetypeResponse(
        archetype_id=archetype.get("id"),
        adl_version=result.get("adl_version", "1.0"),
        generated_at=result.get("generated_at", ""),
        archetype_name=archetype.get("name"),
        archetype_description=archetype.get("description"),
        origin=archetype.get("origin", "synthesized"),
        origin_label=DisplayLabels.get("archetype_origin", archetype.get("origin", "synthesized")),
        phases=phases,
        confidence_level=confidence_level,
        confidence_label=conf_label,
        synthesis_ready=True,
    )


# =============================================================================
# v3.7.3: REVIEW SESSION ENDPOINTS
# =============================================================================

class StartReviewRequest(BaseModel):
    """Request to start a review session."""
    inference_result_id: Optional[str] = None  # If None, uses latest


class StartReviewResponse(BaseModel):
    """Response from starting a review session."""
    session_id: str
    status: str
    review_stage: str
    coaching_message: str


class CoachingExchangeRequest(BaseModel):
    """Request for a coaching exchange."""
    message: str
    current_stage: str = "REVIEWING_PHASES"
    current_phase_index: int = 0


class CoachingExchangeResponse(BaseModel):
    """Response from a coaching exchange."""
    coaching_message: str
    next_stage: str
    current_phase_index: int
    refinements_applied: int = 0


class NamingRequest(BaseModel):
    """Request to set methodology naming."""
    name: str
    description: Optional[str] = None
    key_principles: Optional[List[str]] = None


class VisibilityRequest(BaseModel):
    """Request to set visibility."""
    visibility: str  # PERSONAL | TEAM | ORGANIZATION | IKF_SHARED


class ApproveResponse(BaseModel):
    """Response from approving publication."""
    success: bool
    archetype_id: str
    archetype_name: str
    version_string: str
    visibility: str


class ReviewStatusResponse(BaseModel):
    """Review session status."""
    session_id: str
    status: str
    review_stage: str
    refinement_count: int
    methodology_name: Optional[str] = None
    visibility: str = "PERSONAL"


@router.post("/review/start/{innovator_id}", response_model=StartReviewResponse)
async def start_review_session(
    innovator_id: str,
    request: Optional[StartReviewRequest] = None,
):
    """
    v3.7.3: Start a methodology review session.

    Initiates a coaching-assisted review of the inferred methodology.
    """
    from ems.review_interface import get_review_session_manager
    from ems.adl_generator import get_adl_generator

    manager = get_review_session_manager()
    adl_generator = get_adl_generator()

    # Get inference result to review
    inference_result_id = request.inference_result_id if request else None

    if inference_result_id:
        result = db.get_latest_inference_result(innovator_id)
        # TODO: Use specific inference_result_id
    else:
        result = db.get_latest_inference_result(innovator_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No inference result found. Run pattern inference first."
        )

    # Get or generate draft archetype
    archetype = db.get_latest_archetype(innovator_id)
    if not archetype:
        # Generate archetype from inference result
        archetype_result = adl_generator.generate_archetype(
            innovator_id=innovator_id,
            inference_result=result
        )
        archetype = archetype_result

    # Start review session
    session_info = manager.start_review_session(
        innovator_id=innovator_id,
        inference_result_id=str(result.get("_id", "")),
        draft_archetype=archetype
    )

    return StartReviewResponse(
        session_id=session_info["session_id"],
        status=session_info["status"],
        review_stage=session_info["review_stage"],
        coaching_message=session_info["coaching_message"],
    )


@router.post("/review/{session_id}/exchange", response_model=CoachingExchangeResponse)
async def coaching_exchange(
    session_id: str,
    request: CoachingExchangeRequest,
):
    """
    v3.7.3: Send a message in the review coaching conversation.
    """
    from ems.review_interface import get_review_session_manager

    manager = get_review_session_manager()

    result = manager.process_innovator_response(
        session_id=session_id,
        innovator_message=request.message,
        current_stage=request.current_stage,
        current_phase_index=request.current_phase_index,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return CoachingExchangeResponse(
        coaching_message=result.get("coaching_message", ""),
        next_stage=result.get("next_stage", request.current_stage),
        current_phase_index=result.get("current_phase_index", 0),
        refinements_applied=result.get("refinements_applied", 0),
    )


@router.get("/review/{session_id}/status", response_model=ReviewStatusResponse)
async def get_review_status(session_id: str):
    """
    v3.7.3: Get current review session status.
    """
    session = db.get_review_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")

    return ReviewStatusResponse(
        session_id=session_id,
        status=session.get("status", "UNKNOWN"),
        review_stage="REVIEWING_PHASES",  # TODO: Track actual stage
        refinement_count=len(session.get("refinements", [])),
        methodology_name=session.get("methodology_name"),
        visibility=session.get("visibility", "PERSONAL"),
    )


@router.post("/review/{session_id}/name")
async def set_methodology_name(
    session_id: str,
    request: NamingRequest,
):
    """
    v3.7.3: Set methodology name, description, and principles.
    """
    success = db.set_methodology_details(
        session_id=session_id,
        name=request.name,
        description=request.description,
        key_principles=request.key_principles,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Could not update naming")

    return {"success": True, "name": request.name}


@router.post("/review/{session_id}/visibility")
async def set_visibility(
    session_id: str,
    request: VisibilityRequest,
):
    """
    v3.7.3: Set visibility level for the methodology.
    """
    valid_levels = ["PERSONAL", "TEAM", "ORGANIZATION", "IKF_SHARED"]
    if request.visibility not in valid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid visibility. Must be one of: {valid_levels}"
        )

    success = db.set_methodology_details(
        session_id=session_id,
        visibility=request.visibility,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Could not update visibility")

    return {"success": True, "visibility": request.visibility}


@router.post("/review/{session_id}/approve", response_model=ApproveResponse)
async def approve_and_publish(session_id: str):
    """
    v3.7.3: Approve and publish the methodology.
    """
    from ems.archetype_publisher import get_archetype_publisher

    session = db.get_review_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")

    # Get innovator info
    innovator_id = session.get("innovator_id", "")
    innovator = {"innovator_id": innovator_id, "display_name": "Innovator"}  # TODO: Fetch actual user

    publisher = get_archetype_publisher()

    try:
        published = publisher.publish(
            review_session=session,
            innovator=innovator,
        )

        arch_content = published.get("archetype", published)

        return ApproveResponse(
            success=True,
            archetype_id=str(published.get("_id", "")),
            archetype_name=arch_content.get("name", ""),
            version_string=published.get("version_string", "1.0"),
            visibility=published.get("visibility", "PERSONAL"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/review/{session_id}/reject")
async def reject_methodology(
    session_id: str,
    reason: str = Query(..., description="Reason for rejection"),
):
    """
    v3.7.3: Reject the inferred methodology.
    """
    session = db.get_review_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")

    # Update status to rejected
    success = db.update_review_session_status(session_id, "REJECTED")

    # Add rejection reason as refinement
    db.add_refinement(
        session_id=session_id,
        action="REJECTION",
        target="methodology",
        before="draft",
        after="rejected",
        innovator_rationale=reason,
    )

    return {"success": success, "status": "REJECTED", "reason": reason}


@router.get("/review/{session_id}/comparison")
async def get_comparison(session_id: str):
    """
    v3.7.3: Get comparison with similar existing archetypes.
    """
    session = db.get_review_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Review session not found")

    draft = session.get("original_draft", {})
    synthesis_metadata = draft.get("synthesis_metadata", {})
    similar_archetypes = synthesis_metadata.get("similar_archetypes", [])

    # Get confidence scores
    confidence = draft.get("source", {}).get("confidence", 0)

    return {
        "similar_archetypes": similar_archetypes,
        "confidence": confidence,
        "phase_count": len(draft.get("archetype", {}).get("phases", [])),
    }


# =============================================================================
# v3.7.3: PUBLISHED ARCHETYPE ENDPOINTS
# =============================================================================

class PublishedArchetypeSummary(BaseModel):
    """Summary of a published archetype."""
    archetype_id: str
    name: str
    display_name: str
    version_string: str
    visibility: str
    phase_count: int
    published_at: str
    usage_count: int = 0


@router.get("/archetypes/mine", response_model=List[PublishedArchetypeSummary])
async def get_my_archetypes(innovator_id: str = Query(...)):
    """
    v3.7.3: List all archetypes published by the innovator.
    """
    from ems.archetype_publisher import get_archetype_publisher

    publisher = get_archetype_publisher()
    archetypes = publisher.get_published_archetypes(innovator_id)

    results = []
    for doc in archetypes:
        arch_result = doc.get("archetype_result", {})
        arch_content = arch_result.get("archetype", arch_result)

        results.append(PublishedArchetypeSummary(
            archetype_id=str(doc.get("_id", "")),
            name=arch_content.get("name", ""),
            display_name=arch_content.get("display_name", arch_content.get("name", "")),
            version_string=arch_result.get("version_string", "1.0"),
            visibility=arch_result.get("visibility", "PERSONAL"),
            phase_count=len(arch_content.get("phases", [])),
            published_at=str(doc.get("created_at", "")),
            usage_count=0,  # TODO: Count pursuits using this archetype
        ))

    return results


@router.put("/archetypes/{archetype_id}/visibility")
async def update_archetype_visibility(
    archetype_id: str,
    request: VisibilityRequest,
    innovator_id: str = Query(...),
):
    """
    v3.7.3: Update visibility of a published archetype.
    """
    from ems.archetype_publisher import get_archetype_publisher

    publisher = get_archetype_publisher()

    try:
        success = publisher.update_visibility(
            archetype_id=archetype_id,
            new_visibility=request.visibility,
            innovator_id=innovator_id,
        )
        return {"success": success, "visibility": request.visibility}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/archetypes/{archetype_id}/evolution-check")
async def check_evolution(
    archetype_id: str,
    innovator_id: str = Query(...),
):
    """
    v3.7.3: Check if methodology should evolve based on new data.
    """
    from ems.archetype_publisher import get_archetype_publisher

    publisher = get_archetype_publisher()
    result = publisher.check_evolution_opportunity(archetype_id, innovator_id)

    return result


@router.post("/archetypes/{archetype_id}/evolve")
async def trigger_evolution(
    archetype_id: str,
    innovator_id: str = Query(...),
):
    """
    v3.7.3: Trigger re-analysis for methodology evolution.
    """
    from ems.pattern_inference import get_pattern_inference_engine

    engine = get_pattern_inference_engine()

    # Run new inference
    result = engine.infer_patterns(innovator_id)

    if result.get("sufficient_data"):
        # Store result
        db.store_inference_result(innovator_id, result)

        return {
            "success": True,
            "inference_id": result.get("inference_timestamp"),
            "message": "New patterns inferred. Start a review session to evolve your methodology.",
        }
    else:
        return {
            "success": False,
            "message": "Not enough new data for evolution analysis.",
        }


# =============================================================================
# ROUTER FACTORY
# =============================================================================

def get_ems_router() -> APIRouter:
    """Get the EMS API router."""
    return router
