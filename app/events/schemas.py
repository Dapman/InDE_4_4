"""
InDE v3.4 - Domain Event Schemas
Typed event schemas for the Redis Streams event system.

v3.4 Additions:
- Convergence events (convergence.detected, convergence.explicit_trigger, outcome.captured, handoff.completed)
- Discovery events (discovery.triggered, formation.recommended, formation.completed, invite.sent)
- Audit events (audit.*)
- Methodology events (methodology.changed, transition.completed, transition.overridden)
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid


def _utc_now():
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class DomainEvent(BaseModel):
    """Base class for all domain events."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=_utc_now)
    source_module: str = ""  # v3.2: Module that emitted the event
    user_id: Optional[str] = None
    pursuit_id: Optional[str] = None
    correlation_id: Optional[str] = None  # v3.2: Traces event chains
    payload: Dict[str, Any] = {}

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


# Alias for backward compatibility with IKF service schemas
EventPayload = DomainEvent


# Pursuit Events
class PursuitCreatedEvent(DomainEvent):
    event_type: str = "pursuit.created"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "title": "",
        "storage_election": "FULL_PARTICIPATION"
    })


class PursuitUpdatedEvent(DomainEvent):
    event_type: str = "pursuit.updated"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "fields_changed": [],
        "previous_values": {},
        "new_values": {}
    })


class PursuitTerminatedEvent(DomainEvent):
    event_type: str = "pursuit.terminated"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "terminal_state": "",
        "reason": ""
    })


# Element Events
class ElementCapturedEvent(DomainEvent):
    event_type: str = "element.captured"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "element_type": "",
        "element_name": "",
        "confidence": 0.0
    })


class ElementUpdatedEvent(DomainEvent):
    event_type: str = "element.updated"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "element_type": "",
        "element_name": "",
        "previous_value": "",
        "new_value": "",
        "confidence": 0.0
    })


# Artifact Events
class ArtifactGeneratedEvent(DomainEvent):
    event_type: str = "artifact.generated"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "artifact_id": "",
        "artifact_type": ""
    })


class ArtifactUpdatedEvent(DomainEvent):
    event_type: str = "artifact.updated"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "artifact_id": "",
        "version": 1
    })


# Coaching Events
class CoachingSessionStartedEvent(DomainEvent):
    event_type: str = "coaching.session_started"


class InterventionTriggeredEvent(DomainEvent):
    event_type: str = "coaching.intervention_triggered"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "intervention_type": "",
        "suggestion": ""
    })


# Maturity Events
class MaturityLevelChangedEvent(DomainEvent):
    event_type: str = "maturity.level_changed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "previous_level": "",
        "new_level": "",
        "composite_score": 0.0
    })


class MaturityDimensionUpdatedEvent(DomainEvent):
    event_type: str = "maturity.dimension_updated"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "dimension": "",
        "previous_score": 0.0,
        "new_score": 0.0,
        "trigger": ""
    })


# Crisis Events
class CrisisTriggeredEvent(DomainEvent):
    event_type: str = "crisis.triggered"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "crisis_type": "",
        "urgency": "",
        "trigger_reason": ""
    })


class CrisisPhaseAdvancedEvent(DomainEvent):
    event_type: str = "crisis.phase_advanced"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "session_id": "",
        "previous_phase": "",
        "new_phase": ""
    })


class CrisisResolvedEvent(DomainEvent):
    event_type: str = "crisis.resolved"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "session_id": "",
        "resolution": ""
    })


# Health Events
class HealthZoneChangedEvent(DomainEvent):
    event_type: str = "health.zone_changed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "previous_zone": "",
        "new_zone": "",
        "score": 0.0
    })


# GII Events
class GIIBoundEvent(DomainEvent):
    event_type: str = "gii.bound"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "gii_id": "",
        "region": ""
    })


# v3.2: IKF Events
class IKFPackagePreparedEvent(DomainEvent):
    event_type: str = "ikf.package.prepared"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "package_id": "",
        "package_type": "",
        "title": ""
    })


class IKFPackageReviewedEvent(DomainEvent):
    event_type: str = "ikf.package.reviewed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "package_id": "",
        "status": "",  # APPROVED, REJECTED
        "reviewer_id": ""
    })


class IKFPackageReadyEvent(DomainEvent):
    event_type: str = "ikf.package.ready"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "package_id": "",
        "package_type": ""
    })


class IKFFederationStatusEvent(DomainEvent):
    event_type: str = "ikf.federation.status"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "node_status": "",
        "patterns_synced": 0
    })


# v3.2: Retrospective Event
class RetrospectiveCompletedEvent(DomainEvent):
    event_type: str = "retrospective.completed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "completion_percentage": 0.0,
        "learnings_captured": 0
    })


# All event types for registration (v3.4 extended)
EVENT_TYPES = [
    # Pursuit events
    "pursuit.created",
    "pursuit.updated",
    "pursuit.terminated",
    "pursuit.completed",
    "pursuit.state.transitioned",
    # Element events
    "element.captured",
    "element.updated",
    "element.milestone.reached",
    # Artifact events
    "artifact.generated",
    "artifact.updated",
    # Coaching events
    "coaching.session_started",
    "coaching.intervention_triggered",
    "coaching.message.exchanged",
    "coaching.crisis.activated",
    "coaching.crisis.resolved",
    "coaching.convergence.triggered",
    # Maturity events
    "maturity.level_changed",
    "maturity.dimension_updated",
    "maturity.score.recalculated",
    "maturity.level.advanced",
    # Crisis events
    "crisis.triggered",
    "crisis.phase_advanced",
    "crisis.resolved",
    "crisis.activated",
    "crisis.option.selected",
    # Health events
    "health.zone_changed",
    "health.score.updated",
    "health.crisis.detected",
    # GII events
    "gii.bound",
    # RVE events
    "rve.experiment.designed",
    "rve.experiment.completed",
    "rve.validation.failed",
    # v3.2: IKF events
    "ikf.package.prepared",
    "ikf.package.reviewed",
    "ikf.package.ready",
    "ikf.federation.status",
    # v3.2: Retrospective events
    "retrospective.completed",
    # v3.4: Convergence events (NEW)
    "convergence.detected",
    "convergence.explicit_trigger",
    "convergence.outcome.captured",
    "convergence.handoff.completed",
    # v3.4: Discovery events (NEW)
    "discovery.triggered",
    "discovery.formation.recommended",
    "discovery.formation.completed",
    "discovery.invite.sent",
    # v3.4: Audit events (NEW)
    "audit.event",
    # v3.4: Methodology events (NEW)
    "pursuit.methodology.changed",
    "pursuit.transition.completed",
    "pursuit.transition.overridden",
]


class EventTypes:
    """Event type constants for type-safe event emission."""
    # Coaching events
    COACHING_MESSAGE_EXCHANGED = "coaching.message.exchanged"
    COACHING_CRISIS_ACTIVATED = "coaching.crisis.activated"
    COACHING_CRISIS_RESOLVED = "coaching.crisis.resolved"
    COACHING_CONVERGENCE_TRIGGERED = "coaching.convergence.triggered"

    # Pursuit events
    PURSUIT_CREATED = "pursuit.created"
    PURSUIT_STATE_TRANSITIONED = "pursuit.state.transitioned"
    PURSUIT_COMPLETED = "pursuit.completed"
    PURSUIT_TERMINATED = "pursuit.terminated"

    # Element events
    ELEMENT_CAPTURED = "element.captured"
    ELEMENT_UPDATED = "element.updated"
    ELEMENT_MILESTONE_REACHED = "element.milestone.reached"

    # Health events
    HEALTH_SCORE_UPDATED = "health.score.updated"
    HEALTH_ZONE_CHANGED = "health.zone.changed"
    HEALTH_CRISIS_DETECTED = "health.crisis.detected"

    # RVE events
    RVE_EXPERIMENT_DESIGNED = "rve.experiment.designed"
    RVE_EXPERIMENT_COMPLETED = "rve.experiment.completed"
    RVE_VALIDATION_FAILED = "rve.validation.failed"

    # Maturity events
    MATURITY_SCORE_RECALCULATED = "maturity.score.recalculated"
    MATURITY_LEVEL_ADVANCED = "maturity.level.advanced"

    # Crisis events
    CRISIS_ACTIVATED = "crisis.activated"
    CRISIS_OPTION_SELECTED = "crisis.option.selected"
    CRISIS_RESOLVED = "crisis.resolved"

    # v3.2: IKF events
    IKF_PACKAGE_PREPARED = "ikf.package.prepared"
    IKF_PACKAGE_REVIEWED = "ikf.package.reviewed"
    IKF_PACKAGE_READY = "ikf.package.ready"
    IKF_FEDERATION_STATUS = "ikf.federation.status"

    # v3.2: Retrospective event
    RETROSPECTIVE_COMPLETED = "retrospective.completed"

    # v3.4: Convergence events (NEW)
    CONVERGENCE_DETECTED = "convergence.detected"
    CONVERGENCE_EXPLICIT_TRIGGER = "convergence.explicit_trigger"
    OUTCOME_CAPTURED = "convergence.outcome.captured"
    HANDOFF_COMPLETED = "convergence.handoff.completed"

    # v3.4: Discovery events (NEW)
    DISCOVERY_TRIGGERED = "discovery.triggered"
    FORMATION_RECOMMENDED = "discovery.formation.recommended"
    FORMATION_COMPLETED = "discovery.formation.completed"
    INVITE_SENT = "discovery.invite.sent"

    # v3.4: Audit events (NEW)
    AUDIT_EVENT = "audit.event"

    # v3.4: Methodology events (NEW)
    METHODOLOGY_CHANGED = "pursuit.methodology.changed"
    TRANSITION_COMPLETED = "pursuit.transition.completed"
    TRANSITION_OVERRIDDEN = "pursuit.transition.overridden"

    # v3.7.3: EMS Review & Publication events (NEW)
    EMS_REVIEW_STARTED = "ems.review.started"
    EMS_REVIEW_REFINEMENT_APPLIED = "ems.review.refinement_applied"
    EMS_REVIEW_COMPLETED = "ems.review.completed"
    EMS_ARCHETYPE_PUBLISHED = "ems.archetype.published"
    EMS_ARCHETYPE_VISIBILITY_CHANGED = "ems.archetype.visibility_changed"
    EMS_ARCHETYPE_IKF_SHARED = "ems.archetype.ikf_shared"
    EMS_ARCHETYPE_EVOLUTION_TRIGGERED = "ems.archetype.evolution_triggered"


# =============================================================================
# v3.7.3: EMS REVIEW & PUBLICATION EVENT SCHEMAS
# =============================================================================

class EMSReviewStartedEvent(DomainEvent):
    """Emitted when a methodology review session is initiated."""
    event_type: str = "ems.review.started"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "innovator_id": "",
        "session_id": "",
        "phase_count": 0,
        "confidence_tier": "",
    })


class EMSReviewRefinementAppliedEvent(DomainEvent):
    """Emitted when the innovator modifies the draft methodology."""
    event_type: str = "ems.review.refinement_applied"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "session_id": "",
        "action": "",
        "target": "",
        "refinement_count": 0,
    })


class EMSReviewCompletedEvent(DomainEvent):
    """Emitted when a review session concludes (approve or reject)."""
    event_type: str = "ems.review.completed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "session_id": "",
        "outcome": "",  # APPROVED, REJECTED, ABANDONED
        "refinement_count": 0,
        "methodology_name": "",
    })


class EMSArchetypePublishedEvent(DomainEvent):
    """Emitted when an archetype is committed to the repository."""
    event_type: str = "ems.archetype.published"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "archetype_name": "",
        "version": "",
        "visibility": "",
        "innovator_id": "",
        "phase_count": 0,
    })


class EMSArchetypeVisibilityChangedEvent(DomainEvent):
    """Emitted when archetype visibility is updated."""
    event_type: str = "ems.archetype.visibility_changed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "archetype_id": "",
        "old_visibility": "",
        "new_visibility": "",
        "innovator_id": "",
    })


class EMSArchetypeIKFSharedEvent(DomainEvent):
    """Emitted when an archetype is shared through IKF."""
    event_type: str = "ems.archetype.ikf_shared"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "archetype_name": "",
        "confidence": 0.0,
        "phase_count": 0,
    })


class EMSArchetypeEvolutionTriggeredEvent(DomainEvent):
    """Emitted when re-analysis is started for methodology update."""
    event_type: str = "ems.archetype.evolution_triggered"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "archetype_id": "",
        "current_version": "",
        "pursuits_since_publication": 0,
    })


# =============================================================================
# v3.4: CONVERGENCE EVENT SCHEMAS
# =============================================================================

class ConvergenceDetectedEvent(DomainEvent):
    """Emitted when convergence is detected via signal threshold."""
    event_type: str = "convergence.detected"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "session_id": "",
        "signal_scores": {},
        "composite_score": 0.0,
        "threshold": 0.7,
    })


class ConvergenceExplicitTriggerEvent(DomainEvent):
    """Emitted when innovator explicitly triggers convergence."""
    event_type: str = "convergence.explicit_trigger"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "session_id": "",
        "trigger_source": "ui_button",  # ui_button | message
    })


class OutcomeCapturedEvent(DomainEvent):
    """Emitted when a convergence outcome is captured."""
    event_type: str = "convergence.outcome.captured"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "session_id": "",
        "outcome_id": "",
        "outcome_type": "",  # DECISION | INSIGHT | HYPOTHESIS | COMMITMENT | REFINEMENT
        "artifact_ref": None,
    })


class HandoffCompletedEvent(DomainEvent):
    """Emitted when convergence handoff to next activity completes."""
    event_type: str = "convergence.handoff.completed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "session_id": "",
        "from_phase": "",
        "to_phase": "",
        "criteria_satisfied": [],
    })


# =============================================================================
# v3.4: DISCOVERY EVENT SCHEMAS
# =============================================================================

class DiscoveryTriggeredEvent(DomainEvent):
    """Emitted when IDTFS discovery is triggered."""
    event_type: str = "discovery.triggered"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "gap_description": "",
        "gap_source": "",  # SCAFFOLDING | COACHING | MANUAL
        "org_id": "",
    })


class FormationRecommendedEvent(DomainEvent):
    """Emitted when formation candidates are recommended."""
    event_type: str = "discovery.formation.recommended"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "recommendation_id": "",
        "candidate_count": 0,
        "top_candidate_score": 0.0,
    })


class FormationCompletedEvent(DomainEvent):
    """Emitted when team formation is completed."""
    event_type: str = "discovery.formation.completed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "recommendation_id": "",
        "outcome_user_id": "",
        "accepted": True,
    })


class InviteSentEvent(DomainEvent):
    """Emitted when outreach invite is sent."""
    event_type: str = "discovery.invite.sent"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "invite_user_id": "",
        "invited_by": "",
        "gap_summary": "",
    })


# =============================================================================
# v3.4: AUDIT EVENT SCHEMA
# =============================================================================

class AuditEvent(DomainEvent):
    """
    SOC 2-ready audit event.

    Event types: AUTH_LOGIN, AUTH_LOGOUT, AUTH_FAILED, RESOURCE_ACCESS,
    RESOURCE_CREATE, RESOURCE_UPDATE, RESOURCE_DELETE, PERMISSION_CHANGE,
    POLICY_CHANGE, CONFIG_CHANGE, DATA_EXPORT, ADMIN_ACTION
    """
    event_type: str = "audit.event"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "audit_event_type": "",  # AUTH_LOGIN | RESOURCE_ACCESS | etc.
        "actor_id": "",
        "actor_role": "",
        "org_id": None,
        "resource_type": "",
        "resource_id": "",
        "action_detail": {},
        "ip_address": None,
        "outcome": "SUCCESS",  # SUCCESS | FAILURE | DENIED
    })


# =============================================================================
# v3.4: METHODOLOGY EVENT SCHEMAS
# =============================================================================

class MethodologyChangedEvent(DomainEvent):
    """Emitted when pursuit methodology archetype changes."""
    event_type: str = "pursuit.methodology.changed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "previous_archetype": "",
        "new_archetype": "",
        "changed_by": "",
    })


class TransitionCompletedEvent(DomainEvent):
    """Emitted when phase transition is completed."""
    event_type: str = "pursuit.transition.completed"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "from_phase": "",
        "to_phase": "",
        "criteria_snapshot": [],
        "methodology_archetype": "",
    })


class TransitionOverriddenEvent(DomainEvent):
    """Emitted when transition criteria are overridden."""
    event_type: str = "pursuit.transition.overridden"
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "from_phase": "",
        "to_phase": "",
        "override_rationale": "",
        "unsatisfied_criteria": [],
    })
