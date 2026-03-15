"""
InDE v3.2 - Domain Event Dispatcher
Redis-backed event dispatcher with in-memory fallback.

PRESERVES the v3.1 interface: dispatcher.emit(event), emit_event(event)
All existing callers continue to work WITHOUT changes.

Internal change: emit() now publishes to Redis via RedisStreamPublisher.
In-memory handler dispatch is replaced by Redis consumer groups (see redis_consumer.py).

BACKWARD COMPAT: If Redis is unavailable, falls back to in-memory dispatch
using the v3.1 handler registry. This ensures coaching never breaks.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timezone
from collections import defaultdict

from events.schemas import DomainEvent
from events.redis_publisher import publisher

logger = logging.getLogger("inde.events")


class EventDispatcher:
    """
    v3.2 EventDispatcher — facade that publishes to Redis Streams.

    PRESERVES the v3.1 interface: dispatcher.emit(event)
    All existing callers continue to work WITHOUT changes.

    Internal change: emit() now publishes to Redis via RedisStreamPublisher.
    In-memory handler dispatch is for fallback only.
    """

    def __init__(self, db=None, persist: bool = True):
        """
        Initialize dispatcher.

        Args:
            db: Database instance for persistence
            persist: Whether to persist events (always True in v3.2)
        """
        self._fallback_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._db = db
        self._persist = persist
        self._event_count = 0

    def register(self, event_type: str, handler: Callable) -> None:
        """
        Register a fallback handler for graceful degradation.

        In normal operation, handlers consume from Redis via RedisStreamConsumer.
        These are only invoked if Redis is unavailable.

        Args:
            event_type: Event type string (e.g., "pursuit.created")
            handler: Callable that receives the event
        """
        self._fallback_handlers[event_type].append(handler)
        logger.debug(f"Registered fallback handler for {event_type}")

    # Alias for backward compatibility
    subscribe = register

    def unregister(self, event_type: str, handler: Callable) -> bool:
        """
        Unregister a handler.

        Args:
            event_type: Event type string
            handler: Handler to remove

        Returns:
            True if handler was found and removed
        """
        if handler in self._fallback_handlers[event_type]:
            self._fallback_handlers[event_type].remove(handler)
            return True
        return False

    def emit(self, event: DomainEvent) -> None:
        """
        Emit an event — same interface as v3.1.

        Publishes to Redis Streams (async) with sync fallback.
        EVERY existing caller continues to work unchanged.

        Args:
            event: DomainEvent to emit
        """
        self._event_count += 1

        # Ensure event has correlation_id
        if not event.correlation_id:
            event.correlation_id = str(uuid.uuid4())

        # Try async Redis publish
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - create task
            asyncio.create_task(publisher.publish(event))
            logger.debug(f"Emitted {event.event_type} via Redis (async)")
        except RuntimeError:
            # No running event loop - use sync fallback
            publisher.publish_sync(event)
            self._fallback_dispatch(event)
            logger.debug(f"Emitted {event.event_type} via sync fallback")

    def emit_sync(
        self,
        event_type: str,
        payload: dict,
        source_module: str = "",
        pursuit_id: str = None,
        user_id: str = None,
        correlation_id: str = None
    ) -> None:
        """
        Convenience method to emit event from parameters.

        This allows existing code that doesn't use DomainEvent subclasses
        to continue working.

        Args:
            event_type: Event type string
            payload: Event payload dict
            source_module: Module that triggered the event
            pursuit_id: Associated pursuit ID
            user_id: Associated user ID
            correlation_id: Correlation ID for tracing
        """
        event = DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            source_module=source_module,
            pursuit_id=pursuit_id,
            user_id=user_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            payload=payload
        )
        self.emit(event)

    def _fallback_dispatch(self, event: DomainEvent) -> None:
        """In-memory dispatch when Redis unavailable — v3.1 behavior."""
        for pattern, handlers in self._fallback_handlers.items():
            if pattern == event.event_type:
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Fallback handler failed for {event.event_type}: {e}")
            elif pattern.endswith(".*") and event.event_type.startswith(pattern[:-2]):
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Fallback handler failed for {event.event_type}: {e}")
            elif pattern == "*":
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Fallback handler failed for {event.event_type}: {e}")

    def replay_events(
        self,
        since: Optional[datetime] = None,
        event_type: Optional[str] = None,
        pursuit_id: Optional[str] = None
    ) -> int:
        """
        Replay persisted events through handlers.

        Args:
            since: Only replay events after this timestamp
            event_type: Only replay specific event type
            pursuit_id: Only replay events for this pursuit

        Returns:
            Number of events replayed
        """
        if not self._db:
            return 0

        query: Dict[str, Any] = {}
        if since:
            query["timestamp"] = {"$gte": since}
        if event_type:
            query["event_type"] = event_type
        if pursuit_id:
            query["pursuit_id"] = pursuit_id

        events = list(self._db.db.domain_events.find(query).sort("timestamp", 1))

        for event_doc in events:
            event = DomainEvent(
                event_id=event_doc.get("event_id"),
                event_type=event_doc.get("event_type"),
                timestamp=event_doc.get("timestamp"),
                source_module=event_doc.get("source_module", ""),
                user_id=event_doc.get("user_id"),
                pursuit_id=event_doc.get("pursuit_id"),
                correlation_id=event_doc.get("correlation_id"),
                payload=event_doc.get("payload", {})
            )

            # Dispatch through fallback handlers only
            self._fallback_dispatch(event)

        return len(events)

    @property
    def event_count(self) -> int:
        """Get total events emitted this session."""
        return self._event_count

    def get_handlers(self, event_type: str) -> List[Callable]:
        """Get registered fallback handlers for an event type."""
        return self._fallback_handlers.get(event_type, [])


# Global dispatcher instance
_dispatcher: Optional[EventDispatcher] = None


def get_dispatcher(db=None) -> EventDispatcher:
    """Get or create global event dispatcher."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = EventDispatcher(db=db)
    elif db is not None and _dispatcher._db is None:
        _dispatcher._db = db
    return _dispatcher


def emit_event(event: DomainEvent) -> None:
    """Convenience function to emit event via global dispatcher."""
    dispatcher = get_dispatcher()
    dispatcher.emit(event)


def on_event(event_type: str):
    """
    Decorator to register a function as an event handler.

    Note: In v3.2, this registers a FALLBACK handler.
    Primary event handling should use Redis consumers.

    Usage:
        @on_event("pursuit.created")
        def handle_pursuit_created(event):
            print(f"Pursuit created: {event.pursuit_id}")
    """
    def decorator(func: Callable) -> Callable:
        get_dispatcher().register(event_type, func)
        return func
    return decorator
