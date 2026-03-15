"""
InDE v3.2 - Domain Events Module
Redis Streams event bus with typed event schemas.
"""

from events.dispatcher import (
    EventDispatcher,
    get_dispatcher,
    emit_event,
    on_event
)
from events.redis_publisher import (
    RedisStreamPublisher,
    publisher
)
from events.schemas import (
    DomainEvent,
    EventPayload,  # Alias for DomainEvent
    PursuitCreatedEvent,
    PursuitUpdatedEvent,
    PursuitTerminatedEvent,
    ElementCapturedEvent,
    ElementUpdatedEvent,
    ArtifactGeneratedEvent,
    ArtifactUpdatedEvent,
    CoachingSessionStartedEvent,
    InterventionTriggeredEvent,
    MaturityLevelChangedEvent,
    MaturityDimensionUpdatedEvent,
    CrisisTriggeredEvent,
    CrisisPhaseAdvancedEvent,
    CrisisResolvedEvent,
    HealthZoneChangedEvent,
    GIIBoundEvent,
    # v3.2: IKF events
    IKFPackagePreparedEvent,
    IKFPackageReviewedEvent,
    IKFPackageReadyEvent,
    IKFFederationStatusEvent,
    RetrospectiveCompletedEvent,
    EVENT_TYPES,
    EventTypes
)

__all__ = [
    # Dispatcher
    "EventDispatcher",
    "get_dispatcher",
    "emit_event",
    "on_event",
    # v3.2: Redis publisher
    "RedisStreamPublisher",
    "publisher",
    # Events
    "DomainEvent",
    "EventPayload",
    "PursuitCreatedEvent",
    "PursuitUpdatedEvent",
    "PursuitTerminatedEvent",
    "ElementCapturedEvent",
    "ElementUpdatedEvent",
    "ArtifactGeneratedEvent",
    "ArtifactUpdatedEvent",
    "CoachingSessionStartedEvent",
    "InterventionTriggeredEvent",
    "MaturityLevelChangedEvent",
    "MaturityDimensionUpdatedEvent",
    "CrisisTriggeredEvent",
    "CrisisPhaseAdvancedEvent",
    "CrisisResolvedEvent",
    "HealthZoneChangedEvent",
    "GIIBoundEvent",
    # v3.2: IKF events
    "IKFPackagePreparedEvent",
    "IKFPackageReviewedEvent",
    "IKFPackageReadyEvent",
    "IKFFederationStatusEvent",
    "RetrospectiveCompletedEvent",
    "EVENT_TYPES",
    "EventTypes"
]
