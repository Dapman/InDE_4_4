"""
InDE IKF Service - Event Schemas
Shared event payload schema - must be kept in sync with app/events/event_schemas.py

v3.5.3 additions:
- Benchmark events (benchmark.*)
- Trust relationship events (trust.*)
- Reputation events (reputation.*)
- Cross-org discovery events (discovery.*, introduction.*)
- Coaching events (coaching.*)
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List


class EventPayload(BaseModel):
    """Base event schema — mirrors app/events/event_schemas.py."""
    event_id: str = ""
    event_type: str
    timestamp: datetime
    source_module: str
    pursuit_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None  # v3.2 — traces event chains
    payload: dict = {}


class EventTypes:
    """Event type constants — mirrors app/events/event_schemas.py."""
    # IKF-relevant events
    PURSUIT_COMPLETED = "pursuit.completed"
    PURSUIT_TERMINATED = "pursuit.terminated"
    RETROSPECTIVE_COMPLETED = "retrospective.completed"
    RVE_EXPERIMENT_COMPLETED = "rve.experiment.completed"
    MATURITY_LEVEL_ADVANCED = "maturity.level.advanced"

    # IKF-originated events
    IKF_PACKAGE_PREPARED = "ikf.package.prepared"
    IKF_PACKAGE_REVIEWED = "ikf.package.reviewed"
    IKF_PACKAGE_READY = "ikf.package.ready"
    IKF_FEDERATION_STATUS = "ikf.federation.status"

    # v3.5.3 - Federation status events
    FEDERATION_CONNECTED = "federation.connected"
    FEDERATION_DISCONNECTED = "federation.disconnected"
    FEDERATION_STATUS_CHANGED = "federation.status_changed"
    FEDERATION_ERROR = "federation.error"

    # v3.5.3 - Benchmark events
    BENCHMARK_UPDATED = "benchmark.updated"
    BENCHMARK_RANKING_CHANGED = "benchmark.ranking_changed"
    BENCHMARK_INDUSTRY_UPDATED = "benchmark.industry_updated"
    BENCHMARK_SYNC_COMPLETED = "benchmark.sync_completed"

    # v3.5.3 - Trust relationship events
    TRUST_REQUESTED = "trust.requested"
    TRUST_ACCEPTED = "trust.accepted"
    TRUST_REJECTED = "trust.rejected"
    TRUST_REVOKED = "trust.revoked"
    TRUST_EXPIRED = "trust.expired"
    TRUST_TERMS_UPDATED = "trust.terms_updated"

    # v3.5.3 - Reputation events
    REPUTATION_UPDATED = "reputation.updated"
    REPUTATION_FEEDBACK_RECEIVED = "reputation.feedback_received"
    REPUTATION_MILESTONE_REACHED = "reputation.milestone_reached"

    # v3.5.3 - Pattern federation events (extends existing)
    PATTERN_DISCOVERED = "pattern.discovered"
    PATTERN_VALIDATED = "pattern.validated"
    PATTERN_FEDERATED = "pattern.federated"
    PATTERN_RECEIVED = "pattern.received"
    PATTERN_APPLIED = "pattern.applied"

    # v3.5.3 - Cross-org discovery events
    DISCOVERY_SEARCH_COMPLETED = "discovery.search_completed"
    DISCOVERY_RESULTS_AVAILABLE = "discovery.results_available"
    INTRODUCTION_REQUESTED = "introduction.requested"
    INTRODUCTION_ACCEPTED = "introduction.accepted"
    INTRODUCTION_DECLINED = "introduction.declined"
    INTRODUCTION_EXPIRED = "introduction.expired"

    # v3.5.3 - Coaching events (user-specific)
    COACHING_INSIGHT_AVAILABLE = "coaching.insight_available"
    COACHING_MOMENT_DETECTED = "coaching.moment_detected"
    COACHING_RECOMMENDATION = "coaching.recommendation"
    COACHING_BENCHMARK_CONTEXT = "coaching.benchmark_context"


# =========================================================================
# v3.5.3 Event Payload Models
# =========================================================================

class BenchmarkEventPayload(BaseModel):
    """Payload for benchmark events."""
    metric_type: str
    percentile: Optional[int] = None
    previous_percentile: Optional[int] = None
    trend: Optional[str] = None  # "improving", "declining", "stable"
    comparison_scope: Optional[str] = None  # "industry", "methodology", "size"


class TrustEventPayload(BaseModel):
    """Payload for trust relationship events."""
    relationship_id: str
    partner_org_id: Optional[str] = None
    partner_org_name: Optional[str] = None
    relationship_type: Optional[str] = None  # "BILATERAL", "CONSORTIUM", "RESEARCH"
    sharing_level: Optional[str] = None  # "INDUSTRY", "PARTNER"
    status: Optional[str] = None
    reason: Optional[str] = None


class ReputationEventPayload(BaseModel):
    """Payload for reputation events."""
    entity_type: str  # "organization", "innovator"
    entity_id: str
    overall_score: Optional[int] = None
    previous_score: Optional[int] = None
    changed_components: Optional[Dict[str, float]] = None
    milestone: Optional[str] = None


class DiscoveryEventPayload(BaseModel):
    """Payload for cross-org discovery events."""
    search_id: Optional[str] = None
    result_count: int = 0
    search_scope: List[str] = []
    gap_context: Optional[Dict[str, Any]] = None


class IntroductionEventPayload(BaseModel):
    """Payload for introduction events."""
    introduction_id: str
    target_gii: Optional[str] = None
    target_org_id: Optional[str] = None
    status: str
    context: Optional[str] = None
    response_message: Optional[str] = None


class CoachingEventPayload(BaseModel):
    """Payload for coaching events."""
    insight_type: str
    content: Dict[str, Any]
    benchmark_context: Optional[Dict[str, Any]] = None
    priority: Optional[str] = None  # "high", "medium", "low"
    actionable: bool = True
