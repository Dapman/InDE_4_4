"""
Event Bridge - Federation Events to WebSocket

Bridges federation events from the internal event system to WebSocket
clients. Maps event types to channels and handles event transformation.

Event Categories:
- federation.*  -> federation channel
- trust.*       -> trust channel
- benchmark.*   -> benchmark channel
- pattern.*     -> pattern channel
- coaching.*    -> coaching channel (user-specific)
- biomimicry.*  -> biomimicry channel (v3.6.0)

Usage:
    bridge = EventBridge(websocket_manager, event_subscriber)
    bridge.start()
    # Events are automatically bridged to WebSocket clients
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Callable, Optional, Any

logger = logging.getLogger("inde.ikf.realtime.event_bridge")


# Event type to channel mapping
EVENT_CHANNEL_MAP = {
    # Federation events
    "federation.connected": "federation",
    "federation.disconnected": "federation",
    "federation.status_changed": "federation",
    "federation.error": "federation",

    # Trust events
    "trust.requested": "trust",
    "trust.accepted": "trust",
    "trust.rejected": "trust",
    "trust.revoked": "trust",
    "trust.expired": "trust",

    # Benchmark events
    "benchmark.updated": "benchmark",
    "benchmark.ranking_changed": "benchmark",
    "benchmark.industry_updated": "benchmark",

    # Pattern events
    "pattern.discovered": "pattern",
    "pattern.validated": "pattern",
    "pattern.federated": "pattern",
    "pattern.received": "pattern",

    # Reputation events
    "reputation.updated": "reputation",
    "reputation.feedback_received": "reputation",

    # Cross-org discovery events
    "discovery.results_available": "discovery",
    "introduction.requested": "discovery",
    "introduction.accepted": "discovery",
    "introduction.declined": "discovery",

    # Coaching events (user-specific)
    "coaching.insight_available": "coaching",
    "coaching.moment_detected": "coaching",
    "coaching.recommendation": "coaching",

    # v3.6.0: Biomimicry events
    "biomimicry.analysis.triggered": "biomimicry",
    "biomimicry.patterns.matched": "biomimicry",
    "biomimicry.insight.offered": "biomimicry",
    "biomimicry.insight.explored": "biomimicry",
    "biomimicry.insight.accepted": "biomimicry",
    "biomimicry.insight.deferred": "biomimicry",
    "biomimicry.insight.dismissed": "biomimicry",
    "biomimicry.patterns_imported": "biomimicry",
}


class EventBridge:
    """
    Bridges federation events to WebSocket clients.

    Subscribes to internal event stream and forwards relevant events
    to connected WebSocket clients based on channel subscriptions.
    """

    def __init__(self, websocket_manager, event_subscriber=None):
        """
        Initialize the Event Bridge.

        Args:
            websocket_manager: WebSocket connection manager
            event_subscriber: Optional event subscriber for federation events
        """
        self._ws_manager = websocket_manager
        self._subscriber = event_subscriber
        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        # Event transformers
        self._transformers: Dict[str, Callable] = {}
        # Stats
        self._events_bridged = 0
        self._events_dropped = 0

    def start(self):
        """Start the event bridge."""
        if self._processor_task and not self._processor_task.done():
            return
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event bridge started")

    def stop(self):
        """Stop the event bridge."""
        self._running = False
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
        logger.info("Event bridge stopped")

    async def publish_event(self, event_type: str, data: dict,
                            user_id: str = None):
        """
        Publish an event to be bridged to WebSocket clients.

        Args:
            event_type: Type of event (e.g., "federation.connected")
            data: Event data payload
            user_id: Optional user ID for user-specific events
        """
        event = {
            "type": event_type,
            "data": data,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self._event_queue.put(event)

    def register_transformer(self, event_type: str,
                              transformer: Callable[[dict], dict]):
        """
        Register a custom transformer for an event type.

        Transformers can modify event data before it's sent to clients.

        Args:
            event_type: Event type to transform
            transformer: Function that takes event data and returns transformed data
        """
        self._transformers[event_type] = transformer
        logger.debug(f"Registered transformer for {event_type}")

    async def _process_events(self):
        """Process events from the queue and bridge to WebSocket."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._bridge_event(event)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")

    async def _bridge_event(self, event: dict):
        """
        Bridge a single event to WebSocket clients.

        Args:
            event: Event to bridge
        """
        event_type = event.get("type")
        channel = EVENT_CHANNEL_MAP.get(event_type)

        if not channel:
            # Unknown event type, drop it
            self._events_dropped += 1
            logger.debug(f"Dropped unknown event type: {event_type}")
            return

        # Apply transformer if registered
        data = event.get("data", {})
        if event_type in self._transformers:
            try:
                data = self._transformers[event_type](data)
            except Exception as e:
                logger.warning(f"Transformer error for {event_type}: {e}")

        # Build WebSocket message
        ws_message = {
            "type": f"event.{event_type}",
            "channel": channel,
            "data": data,
            "timestamp": event.get("timestamp")
        }

        # Route based on user_id or broadcast to channel
        user_id = event.get("user_id")
        if user_id:
            # User-specific event
            sent = await self._ws_manager.send_to_user(user_id, ws_message)
        else:
            # Broadcast to channel subscribers
            sent = await self._ws_manager.broadcast(ws_message, channel=channel)

        if sent > 0:
            self._events_bridged += 1
            logger.debug(f"Bridged event {event_type} to {sent} clients")
        else:
            self._events_dropped += 1

    def get_stats(self) -> dict:
        """Get event bridge statistics."""
        return {
            "events_bridged": self._events_bridged,
            "events_dropped": self._events_dropped,
            "queue_size": self._event_queue.qsize()
        }

    # =========================================================================
    # Pre-built event publishers for common events
    # =========================================================================

    async def publish_federation_status(self, status: str, details: dict = None):
        """Publish federation status change event."""
        await self.publish_event("federation.status_changed", {
            "status": status,
            "details": details or {}
        })

    async def publish_trust_event(self, event_subtype: str, relationship_id: str,
                                   partner_org: str = None, details: dict = None):
        """Publish trust relationship event."""
        await self.publish_event(f"trust.{event_subtype}", {
            "relationship_id": relationship_id,
            "partner_org": partner_org,
            "details": details or {}
        })

    async def publish_benchmark_update(self, metric_type: str,
                                        percentile: int = None,
                                        trend: str = None):
        """Publish benchmark update event."""
        await self.publish_event("benchmark.updated", {
            "metric_type": metric_type,
            "percentile": percentile,
            "trend": trend
        })

    async def publish_pattern_event(self, event_subtype: str, pattern_id: str,
                                     source: str = None, details: dict = None):
        """Publish pattern event."""
        await self.publish_event(f"pattern.{event_subtype}", {
            "pattern_id": pattern_id,
            "source": source,
            "details": details or {}
        })

    async def publish_coaching_insight(self, user_id: str, insight_type: str,
                                        content: dict):
        """Publish user-specific coaching insight."""
        await self.publish_event(
            "coaching.insight_available",
            {
                "insight_type": insight_type,
                "content": content
            },
            user_id=user_id
        )

    async def publish_discovery_results(self, user_id: str, result_count: int,
                                         search_scope: list):
        """Publish cross-org discovery results event."""
        await self.publish_event(
            "discovery.results_available",
            {
                "result_count": result_count,
                "search_scope": search_scope
            },
            user_id=user_id
        )

    async def publish_introduction_status(self, user_id: str,
                                           introduction_id: str,
                                           status: str):
        """Publish introduction status change."""
        event_type = f"introduction.{status.lower()}"
        await self.publish_event(
            event_type,
            {"introduction_id": introduction_id, "status": status},
            user_id=user_id
        )

    # =========================================================================
    # v3.6.0: Biomimicry Event Publishers
    # =========================================================================

    async def publish_biomimicry_insight(
        self,
        user_id: str,
        event_subtype: str,
        match_id: str,
        pattern_id: str,
        organism: str = None,
        details: dict = None
    ):
        """
        Publish biomimicry insight event to user.

        Args:
            user_id: User to send event to
            event_subtype: offered, explored, accepted, deferred, dismissed
            match_id: The match ID
            pattern_id: The pattern ID
            organism: Optional organism name
            details: Additional details
        """
        await self.publish_event(
            f"biomimicry.insight.{event_subtype}",
            {
                "match_id": match_id,
                "pattern_id": pattern_id,
                "organism": organism,
                "details": details or {}
            },
            user_id=user_id
        )

    async def publish_biomimicry_analysis(
        self,
        pursuit_id: str,
        patterns_matched: int,
        categories: list = None
    ):
        """Publish biomimicry analysis results."""
        await self.publish_event("biomimicry.patterns.matched", {
            "pursuit_id": pursuit_id,
            "patterns_matched": patterns_matched,
            "categories": categories or []
        })
