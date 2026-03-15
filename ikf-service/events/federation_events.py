"""
Federation Event Schemas

Defines event types for the federation lifecycle. Published to the
'federation' Redis Stream with consumer group support.

These events are for observability and audit — they must NEVER block
user-facing operations. Publishing is always fire-and-forget.

Event Types:
1. federation.registered - Instance registered with IKF
2. federation.connected - Connection established
3. federation.disconnected - Connection terminated
4. federation.heartbeat.sent - Heartbeat successfully sent
5. federation.heartbeat.failed - Heartbeat failed
6. federation.circuit.opened - Circuit breaker opened
7. federation.circuit.closed - Circuit breaker recovered

v3.5.2 additions:
8. contribution.submitted - Outbox successfully submitted contribution
9. contribution.accepted - IKF accepted the contribution
10. contribution.failed - Contribution submission failed permanently
11. pattern.batch_imported - Batch of patterns received from IKF
12. pattern.integrated - Single pattern integrated into local cache
13. pattern.sync_completed - Incremental sync completed
14. cross_pollination.detected - Cross-domain pattern application detected
15. cross_pollination.confirmed - Cross-domain success confirmed

v3.6.0 additions (Biomimicry):
16. biomimicry.analysis.triggered - When biomimicry analysis is invoked
17. biomimicry.patterns.matched - When patterns are matched to challenge
18. biomimicry.insight.offered - When an insight is offered via coaching
19. biomimicry.insight.explored - When an innovator explores further
20. biomimicry.insight.accepted - When an innovator accepts the insight
21. biomimicry.insight.deferred - When an innovator defers for later
22. biomimicry.insight.dismissed - When an innovator dismisses the insight
23. biomimicry.patterns_imported - When patterns imported from federation

v3.6.1 additions (TRIZ, Blue Ocean, Scenario):
24. triz.contradiction_formulated - Technical contradiction identified
25. triz.principles_recommended - Inventive principles recommended from matrix
26. triz.biomimicry_bridge_activated - Biological analog surfaced for principle
27. triz.solution_concept_generated - Solution concept from inventive principle
28. triz.secondary_contradiction - Secondary contradiction detected in solution
29. blue_ocean.strategy_canvas_created - Industry strategy canvas documented
30. blue_ocean.four_actions_completed - ERRC grid completed
31. blue_ocean.value_curve_diverged - Value curve diverges from industry
32. blue_ocean.non_customers_identified - Non-customer tier explored
33. scenario.detection_triggered - Decision fork detected in conversation
34. scenario.exploration_started - Scenario exploration coaching began
35. scenario.future_explored - Individual scenario explored
36. scenario.decision_captured - Innovator's scenario decision recorded
37. scenario.artifact_generated - Scenario artifact created
38. scenario.revisit_triggered - Revisit condition met

All events include:
- event_type: Qualified event name
- instance_id: InDE instance identifier
- timestamp: ISO 8601 timestamp
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class VerificationLevel(str, Enum):
    """IKF verification levels."""
    PENDING = "PENDING"
    OBSERVER = "OBSERVER"
    PARTICIPANT = "PARTICIPANT"
    CONTRIBUTOR = "CONTRIBUTOR"
    STEWARD = "STEWARD"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class DisconnectReason(str, Enum):
    """Reasons for federation disconnection."""
    MANUAL_DISCONNECT = "manual_disconnect"
    CONNECTION_LOST = "connection_lost"
    MAX_RECONNECT_EXCEEDED = "max_reconnect_exceeded"
    CIRCUIT_BROKEN = "circuit_broken"
    TOKEN_EXPIRED = "token_expired"
    AUTHENTICATION_FAILED = "authentication_failed"
    SERVER_ERROR = "server_error"


# ==============================================================================
# EVENT SCHEMAS
# ==============================================================================

class BaseFederationEvent(BaseModel):
    """Base class for all federation events."""
    event_type: str
    instance_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FederationRegisteredEvent(BaseFederationEvent):
    """Emitted when an InDE instance registers with the IKF."""
    event_type: str = "federation.registered"
    org_id: str
    organization_name: Optional[str] = None
    verification_level: str = "PENDING"
    industry_codes: List[str] = []


class FederationConnectedEvent(BaseFederationEvent):
    """Emitted when federation connection is established."""
    event_type: str = "federation.connected"
    remote_url: str
    verification_level: str
    assigned_region: Optional[str] = None
    latency_ms: float
    capabilities: List[str] = []


class FederationDisconnectedEvent(BaseFederationEvent):
    """Emitted when federation connection is terminated."""
    event_type: str = "federation.disconnected"
    reason: str  # manual_disconnect, connection_lost, max_reconnect_exceeded, etc.
    previous_state: Optional[str] = None
    reconnect_scheduled: bool = False
    reconnect_attempt: Optional[int] = None
    next_reconnect_seconds: Optional[float] = None


class FederationHeartbeatSentEvent(BaseFederationEvent):
    """Emitted when a heartbeat is successfully sent to the hub."""
    event_type: str = "federation.heartbeat.sent"
    status: str = "OK"  # OK, DEGRADED
    pending_patterns: int = 0
    pending_contributions: int = 0
    local_health: Dict[str, Any] = {}


class FederationHeartbeatFailedEvent(BaseFederationEvent):
    """Emitted when a heartbeat fails."""
    event_type: str = "federation.heartbeat.failed"
    failure_count: int
    max_failures: int = 5
    circuit_state: str  # CLOSED, OPEN, HALF_OPEN
    error_message: Optional[str] = None
    will_reconnect: bool = False


class FederationCircuitOpenedEvent(BaseFederationEvent):
    """Emitted when the circuit breaker opens due to failures."""
    event_type: str = "federation.circuit.opened"
    failure_count: int
    failure_threshold: int
    reset_time_seconds: int
    last_error: Optional[str] = None


class FederationCircuitClosedEvent(BaseFederationEvent):
    """Emitted when the circuit breaker recovers and closes."""
    event_type: str = "federation.circuit.closed"
    recovery_time_seconds: float
    probe_success: bool = True
    total_failures_during_open: int = 0


class FederationReconnectScheduledEvent(BaseFederationEvent):
    """Emitted when a reconnection attempt is scheduled."""
    event_type: str = "federation.reconnect.scheduled"
    attempt: int
    max_attempts: int = 10
    delay_seconds: float
    backoff_type: str = "exponential"


class FederationSyncCompletedEvent(BaseFederationEvent):
    """Emitted when pattern sync completes."""
    event_type: str = "federation.sync.completed"
    patterns_received: int
    patterns_acknowledged: int
    sync_duration_ms: float


class FederationContributionSubmittedEvent(BaseFederationEvent):
    """Emitted when a contribution is submitted to the hub."""
    event_type: str = "federation.contribution.submitted"
    contribution_id: str
    contribution_type: str  # pattern, effectiveness, benchmark
    status: str  # submitted, accepted, rejected


# ==============================================================================
# v3.5.2 EVENT SCHEMAS - Bidirectional Knowledge Flow
# ==============================================================================

class ContributionSubmittedEvent(BaseFederationEvent):
    """Emitted when a contribution is submitted via the outbox."""
    event_type: str = "contribution.submitted"
    contribution_id: str
    package_type: str
    receipt_id: Optional[str] = None


class ContributionAcceptedEvent(BaseFederationEvent):
    """Emitted when IKF accepts a contribution."""
    event_type: str = "contribution.accepted"
    contribution_id: str
    receipt_id: str


class ContributionFailedEvent(BaseFederationEvent):
    """Emitted when a contribution permanently fails after max retries."""
    event_type: str = "contribution.failed"
    contribution_id: str
    reason: str
    attempts: int


class PatternBatchImportedEvent(BaseFederationEvent):
    """Emitted after importing a batch of patterns from IKF."""
    event_type: str = "pattern.batch_imported"
    source: str  # IKF_PUSH or IKF_PULL
    accepted: int
    rejected: int
    deduplicated: int


class PatternIntegratedEvent(BaseFederationEvent):
    """Emitted when a single pattern is integrated into the local cache."""
    event_type: str = "pattern.integrated"
    pattern_id: str
    pattern_type: str
    confidence: float
    source: str


class PatternSyncCompletedEvent(BaseFederationEvent):
    """Emitted when incremental pattern sync completes."""
    event_type: str = "pattern.sync_completed"
    patterns_received: int
    accepted: int
    rejected: int
    deduplicated: int
    differential: bool  # True if since-timestamp was used


class CrossPollinationDetectedEvent(BaseFederationEvent):
    """Emitted when cross-domain pattern application is detected."""
    event_type: str = "cross_pollination.detected"
    pattern_id: str
    source_industries: List[str]
    target_industry: str
    pursuit_id: str


class CrossPollinationConfirmedEvent(BaseFederationEvent):
    """Emitted when cross-pollination success is confirmed."""
    event_type: str = "cross_pollination.confirmed"
    pattern_id: str
    source_industries: List[str]
    target_industry: str
    success_indicator: str
    proposal_id: Optional[str] = None


# ==============================================================================
# v3.6.0 EVENT SCHEMAS - Biomimicry & Nature-Inspired Innovation
# ==============================================================================

class BiomimicryAnalysisTriggeredEvent(BaseFederationEvent):
    """Emitted when biomimicry analysis is invoked for a challenge."""
    event_type: str = "biomimicry.analysis.triggered"
    pursuit_id: str
    trigger_reason: str  # explicit_query, challenge_available, fear_context, phase_transition
    challenge_text_length: int
    methodology: Optional[str] = None


class BiomimicryPatternsMatchedEvent(BaseFederationEvent):
    """Emitted when biomimicry patterns are matched to a challenge."""
    event_type: str = "biomimicry.patterns.matched"
    pursuit_id: str
    patterns_matched: int
    top_pattern_id: Optional[str] = None
    top_pattern_score: Optional[float] = None
    categories_matched: List[str] = []
    functions_extracted: List[str] = []


class BiomimicryInsightOfferedEvent(BaseFederationEvent):
    """Emitted when a biomimicry insight is offered via coaching."""
    event_type: str = "biomimicry.insight.offered"
    pursuit_id: str
    match_id: str
    pattern_id: str
    organism: str
    category: str
    match_score: float
    methodology: Optional[str] = None


class BiomimicryInsightExploredEvent(BaseFederationEvent):
    """Emitted when an innovator explores a biomimicry insight further."""
    event_type: str = "biomimicry.insight.explored"
    pursuit_id: str
    match_id: str
    pattern_id: str
    response: str = "explored"
    methodology: Optional[str] = None


class BiomimicryInsightAcceptedEvent(BaseFederationEvent):
    """Emitted when an innovator accepts/applies a biomimicry insight."""
    event_type: str = "biomimicry.insight.accepted"
    pursuit_id: str
    match_id: str
    pattern_id: str
    response: str = "accepted"
    feedback_rating: Optional[int] = None
    methodology: Optional[str] = None


class BiomimicryInsightDeferredEvent(BaseFederationEvent):
    """Emitted when an innovator defers a biomimicry insight for later."""
    event_type: str = "biomimicry.insight.deferred"
    pursuit_id: str
    match_id: str
    pattern_id: str
    response: str = "deferred"
    stored_in_intelligence_panel: bool = True


class BiomimicryInsightDismissedEvent(BaseFederationEvent):
    """Emitted when an innovator dismisses a biomimicry insight."""
    event_type: str = "biomimicry.insight.dismissed"
    pursuit_id: str
    match_id: str
    pattern_id: str
    response: str = "dismissed"


class BiomimicryPatternsImportedEvent(BaseFederationEvent):
    """Emitted when biomimicry patterns are imported from the federation."""
    event_type: str = "biomimicry.patterns_imported"
    source: str  # ikf_federation, org_contributed
    accepted: int
    enriched: int
    deduplicated: int


# ==============================================================================
# v3.6.1 EVENT SCHEMAS - TRIZ, Blue Ocean, Scenario
# ==============================================================================

# TRIZ Events (5)
class TrizContradictionFormulatedEvent(BaseFederationEvent):
    """Emitted when a technical contradiction is formulated."""
    event_type: str = "triz.contradiction_formulated"
    pursuit_id: str
    improving_parameter: str
    worsening_parameter: str
    contradiction_type: str = "technical"  # technical or physical
    methodology: str = "triz"


class TrizPrinciplesRecommendedEvent(BaseFederationEvent):
    """Emitted when inventive principles are recommended from the matrix."""
    event_type: str = "triz.principles_recommended"
    pursuit_id: str
    principle_numbers: List[int]
    parameter_pair: str  # "strength:weight"
    from_matrix: bool = True


class TrizBiomimicryBridgeActivatedEvent(BaseFederationEvent):
    """Emitted when the TRIZ-Biomimicry bridge surfaces a biological analog."""
    event_type: str = "triz.biomimicry_bridge_activated"
    pursuit_id: str
    principle_number: int
    principle_name: str
    organism: str
    pattern_id: str


class TrizSolutionConceptGeneratedEvent(BaseFederationEvent):
    """Emitted when a solution concept is generated from an inventive principle."""
    event_type: str = "triz.solution_concept_generated"
    pursuit_id: str
    principle_numbers: List[int]
    concept_name: str
    approaches_ifr: bool = False  # Approaches Ideal Final Result


class TrizSecondaryContradictionEvent(BaseFederationEvent):
    """Emitted when a secondary contradiction is detected in a proposed solution."""
    event_type: str = "triz.secondary_contradiction"
    pursuit_id: str
    primary_contradiction_resolved: bool
    secondary_improving: str
    secondary_worsening: str


# Blue Ocean Events (4)
class BlueOceanStrategyCanvasCreatedEvent(BaseFederationEvent):
    """Emitted when an industry strategy canvas is documented."""
    event_type: str = "blue_ocean.strategy_canvas_created"
    pursuit_id: str
    industry: str
    competitive_factors_count: int
    new_factors_count: int = 0


class BlueOceanFourActionsCompletedEvent(BaseFederationEvent):
    """Emitted when the ERRC grid is completed."""
    event_type: str = "blue_ocean.four_actions_completed"
    pursuit_id: str
    eliminate_count: int
    reduce_count: int
    raise_count: int
    create_count: int


class BlueOceanValueCurveDivergedEvent(BaseFederationEvent):
    """Emitted when the value curve diverges meaningfully from industry norms."""
    event_type: str = "blue_ocean.value_curve_diverged"
    pursuit_id: str
    divergence_score: float  # 0-10 scale
    significant_changes: int
    is_divergent: bool


class BlueOceanNonCustomersIdentifiedEvent(BaseFederationEvent):
    """Emitted when a non-customer tier is explored."""
    event_type: str = "blue_ocean.non_customers_identified"
    pursuit_id: str
    tier: int  # 1, 2, or 3
    tier_description: str
    insights_captured: int = 0


# Scenario Events (6)
class ScenarioDetectionTriggeredEvent(BaseFederationEvent):
    """Emitted when a decision fork is detected in conversation."""
    event_type: str = "scenario.detection_triggered"
    pursuit_id: str
    trigger_reason: str  # explicit_fork_language, phase_transition_with_fears, etc.
    methodology: Optional[str] = None


class ScenarioExplorationStartedEvent(BaseFederationEvent):
    """Emitted when scenario exploration coaching begins."""
    event_type: str = "scenario.exploration_started"
    pursuit_id: str
    session_id: str
    trigger_reason: str
    methodology: Optional[str] = None


class ScenarioFutureExploredEvent(BaseFederationEvent):
    """Emitted when an individual scenario is explored."""
    event_type: str = "scenario.future_explored"
    pursuit_id: str
    scenario_name: str
    scenario_index: int  # 1, 2, or 3
    has_assumptions: bool = False
    has_risks: bool = False


class ScenarioDecisionCapturedEvent(BaseFederationEvent):
    """Emitted when the innovator's scenario decision is recorded."""
    event_type: str = "scenario.decision_captured"
    pursuit_id: str
    chosen_scenario: str  # name or "deferred"
    has_rationale: bool = False
    has_revisit_trigger: bool = False


class ScenarioArtifactGeneratedEvent(BaseFederationEvent):
    """Emitted when a scenario artifact is created."""
    event_type: str = "scenario.artifact_generated"
    pursuit_id: str
    artifact_id: str
    scenarios_count: int
    decision_made: bool


class ScenarioRevisitTriggeredEvent(BaseFederationEvent):
    """Emitted when a revisit condition is met for a previous scenario decision."""
    event_type: str = "scenario.revisit_triggered"
    pursuit_id: str
    original_artifact_id: str
    original_decision: str
    trigger_condition: str


# ==============================================================================
# EVENT TYPE REGISTRY
# ==============================================================================

FEDERATION_EVENT_TYPES = {
    # v3.5.1 events
    "federation.registered": FederationRegisteredEvent,
    "federation.connected": FederationConnectedEvent,
    "federation.disconnected": FederationDisconnectedEvent,
    "federation.heartbeat.sent": FederationHeartbeatSentEvent,
    "federation.heartbeat.failed": FederationHeartbeatFailedEvent,
    "federation.circuit.opened": FederationCircuitOpenedEvent,
    "federation.circuit.closed": FederationCircuitClosedEvent,
    "federation.reconnect.scheduled": FederationReconnectScheduledEvent,
    "federation.sync.completed": FederationSyncCompletedEvent,
    "federation.contribution.submitted": FederationContributionSubmittedEvent,
    # v3.5.2 events
    "contribution.submitted": ContributionSubmittedEvent,
    "contribution.accepted": ContributionAcceptedEvent,
    "contribution.failed": ContributionFailedEvent,
    "pattern.batch_imported": PatternBatchImportedEvent,
    "pattern.integrated": PatternIntegratedEvent,
    "pattern.sync_completed": PatternSyncCompletedEvent,
    "cross_pollination.detected": CrossPollinationDetectedEvent,
    "cross_pollination.confirmed": CrossPollinationConfirmedEvent,
    # v3.6.0 events - Biomimicry
    "biomimicry.analysis.triggered": BiomimicryAnalysisTriggeredEvent,
    "biomimicry.patterns.matched": BiomimicryPatternsMatchedEvent,
    "biomimicry.insight.offered": BiomimicryInsightOfferedEvent,
    "biomimicry.insight.explored": BiomimicryInsightExploredEvent,
    "biomimicry.insight.accepted": BiomimicryInsightAcceptedEvent,
    "biomimicry.insight.deferred": BiomimicryInsightDeferredEvent,
    "biomimicry.insight.dismissed": BiomimicryInsightDismissedEvent,
    "biomimicry.patterns_imported": BiomimicryPatternsImportedEvent,
    # v3.6.1 events - TRIZ
    "triz.contradiction_formulated": TrizContradictionFormulatedEvent,
    "triz.principles_recommended": TrizPrinciplesRecommendedEvent,
    "triz.biomimicry_bridge_activated": TrizBiomimicryBridgeActivatedEvent,
    "triz.solution_concept_generated": TrizSolutionConceptGeneratedEvent,
    "triz.secondary_contradiction": TrizSecondaryContradictionEvent,
    # v3.6.1 events - Blue Ocean
    "blue_ocean.strategy_canvas_created": BlueOceanStrategyCanvasCreatedEvent,
    "blue_ocean.four_actions_completed": BlueOceanFourActionsCompletedEvent,
    "blue_ocean.value_curve_diverged": BlueOceanValueCurveDivergedEvent,
    "blue_ocean.non_customers_identified": BlueOceanNonCustomersIdentifiedEvent,
    # v3.6.1 events - Scenario
    "scenario.detection_triggered": ScenarioDetectionTriggeredEvent,
    "scenario.exploration_started": ScenarioExplorationStartedEvent,
    "scenario.future_explored": ScenarioFutureExploredEvent,
    "scenario.decision_captured": ScenarioDecisionCapturedEvent,
    "scenario.artifact_generated": ScenarioArtifactGeneratedEvent,
    "scenario.revisit_triggered": ScenarioRevisitTriggeredEvent,
}


def get_event_schema(event_type: str):
    """Get the schema class for an event type."""
    return FEDERATION_EVENT_TYPES.get(event_type)


def validate_event(event_type: str, data: dict) -> BaseFederationEvent:
    """Validate event data against its schema."""
    schema_class = get_event_schema(event_type)
    if not schema_class:
        raise ValueError(f"Unknown federation event type: {event_type}")
    return schema_class(**data)


def list_event_types() -> List[str]:
    """List all registered federation event types."""
    return list(FEDERATION_EVENT_TYPES.keys())
