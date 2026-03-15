"""
InDE v3.2 - Redis Streams Consumer
Async Redis Streams consumer with consumer group support.

Each consumer group independently tracks its read position.
Multiple consumer groups can read the same stream independently.
Unacknowledged events are reclaimed via XCLAIM after timeout.
"""

import redis.asyncio as aioredis
import asyncio
import logging
import os
from typing import Callable, Dict, List
from events.schemas import DomainEvent

logger = logging.getLogger("inde.events.consumer")


class RedisStreamConsumer:
    """
    Async Redis Streams consumer with consumer group support.

    Features:
    - Consumer group-based consumption
    - Automatic consumer group creation
    - XACK for processed messages
    - XCLAIM for reclaiming unacknowledged messages
    - Dead letter queue for failed messages
    """

    def __init__(self, group_name: str, consumer_name: str = None):
        """
        Initialize consumer.

        Args:
            group_name: Consumer group name (e.g., "maturity-engine")
            consumer_name: Consumer instance name (auto-generated if not provided)
        """
        self._redis: aioredis.Redis = None
        self._group = group_name
        self._consumer = consumer_name or f"{group_name}-{os.getpid()}"
        self._prefix = os.environ.get("REDIS_STREAM_PREFIX", "inde:events:")
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._reclaim_timeout_ms = 30000  # 30 seconds
        self._db = None

    async def connect(self, redis_url: str = None, db=None):
        """
        Connect to Redis and ensure consumer groups exist.

        Args:
            redis_url: Redis connection URL
            db: Database instance for dead letter persistence
        """
        self._db = db
        url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")
        self._redis = aioredis.from_url(url, decode_responses=True)
        await self._redis.ping()

        # Create consumer groups for each stream we'll consume
        for stream in self._get_subscribed_streams():
            try:
                await self._redis.xgroup_create(stream, self._group, id="0", mkstream=True)
                logger.info(f"Created consumer group '{self._group}' on '{stream}'")
            except aioredis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    pass  # Group already exists
                else:
                    raise

        logger.info(f"Consumer '{self._consumer}' connected to Redis")

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type.

        Supports exact match and wildcard: 'coaching.*' matches all coaching events.

        Args:
            event_type: Event type pattern
            handler: Async or sync callable
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type} on {self._group}")

    def _get_subscribed_streams(self) -> List[str]:
        """Derive stream names from registered handler event types."""
        categories = set()
        for event_type in self._handlers:
            category = event_type.split(".")[0]
            if category == "*":
                # Wildcard-all — subscribe to known categories
                categories.update([
                    "coaching", "pursuit", "element", "health",
                    "rve", "maturity", "crisis", "ikf", "retrospective",
                    "artifact", "gii"
                ])
            else:
                categories.add(category)
        return [f"{self._prefix}{cat}" for cat in categories]

    async def start(self):
        """Start consuming events in an async loop."""
        self._running = True
        streams = self._get_subscribed_streams()

        if not streams:
            logger.warning(f"Consumer '{self._group}' has no streams to consume")
            return

        logger.info(f"Consumer '{self._group}' starting on streams: {streams}")

        # Process pending (unacknowledged) events first
        await self._process_pending()

        # Main consumption loop
        stream_dict = {s: ">" for s in streams}  # ">" = new messages only

        while self._running:
            try:
                results = await self._redis.xreadgroup(
                    self._group, self._consumer,
                    stream_dict,
                    count=10,       # Process 10 events per batch
                    block=5000      # Block for 5 seconds if no events
                )
                for stream_name, messages in results:
                    for msg_id, msg_data in messages:
                        await self._process_message(stream_name, msg_id, msg_data)

            except asyncio.CancelledError:
                logger.info(f"Consumer '{self._group}' shutting down")
                break
            except Exception as e:
                logger.error(f"Consumer '{self._group}' error: {e}")
                await asyncio.sleep(1)  # Backoff on error

    async def _process_message(self, stream: str, msg_id: str, data: dict):
        """Process a single message and acknowledge it."""
        try:
            event = DomainEvent.model_validate_json(data.get("data", "{}"))
            matched = self._match_handlers(event.event_type)

            for handler in matched:
                try:
                    result = handler(event)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Handler failed for {event.event_type}: {e}")
                    # Don't ACK — let XCLAIM reclaim after timeout
                    return

            # All handlers succeeded — acknowledge
            await self._redis.xack(stream, self._group, msg_id)
            logger.debug(f"Processed and ACKed {event.event_type} ({msg_id})")

        except Exception as e:
            logger.error(f"Failed to process message {msg_id}: {e}")
            await self._handle_dead_letter(stream, msg_id, data, str(e))

    def _match_handlers(self, event_type: str) -> List[Callable]:
        """Find all handlers matching the event type (exact + wildcard)."""
        matched = []
        for pattern, handlers in self._handlers.items():
            if pattern == event_type:
                matched.extend(handlers)
            elif pattern.endswith(".*") and event_type.startswith(pattern[:-2]):
                matched.extend(handlers)
            elif pattern == "*":
                matched.extend(handlers)
        return matched

    async def _process_pending(self):
        """Process any pending (unacknowledged) events on startup."""
        for stream in self._get_subscribed_streams():
            try:
                pending = await self._redis.xpending_range(
                    stream, self._group, min="-", max="+", count=100
                )
                if pending:
                    logger.info(f"Processing {len(pending)} pending events from '{stream}'")
                    for item in pending:
                        msg_id = item["message_id"]
                        idle_time = item.get("time_since_delivered", 0)
                        if idle_time > self._reclaim_timeout_ms:
                            # Reclaim from dead consumer
                            claimed = await self._redis.xclaim(
                                stream, self._group, self._consumer,
                                min_idle_time=self._reclaim_timeout_ms,
                                message_ids=[msg_id]
                            )
                            for claim_id, claim_data in claimed:
                                await self._process_message(stream, claim_id, claim_data)
            except Exception as e:
                logger.warning(f"Pending processing failed for '{stream}': {e}")

    async def _handle_dead_letter(self, stream: str, msg_id: str, data: dict, error: str):
        """Move permanently failed events to dead letter collection."""
        try:
            if self._db:
                from datetime import datetime, timezone
                self._db.db.event_dead_letters.insert_one({
                    "event_id": msg_id,
                    "stream": stream,
                    "data": data,
                    "failure_reason": error,
                    "consumer_group": self._group,
                    "failed_at": datetime.now(timezone.utc)
                })
            # Acknowledge to prevent re-processing
            await self._redis.xack(stream, self._group, msg_id)
            logger.warning(f"Event {msg_id} moved to dead letter queue: {error}")
        except Exception as e:
            logger.error(f"Dead letter handling failed: {e}")

    async def stop(self):
        """Gracefully stop the consumer."""
        self._running = False
        if self._redis:
            await self._redis.close()
        logger.info(f"Consumer '{self._group}' stopped")

    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running

    @property
    def group_name(self) -> str:
        """Get consumer group name."""
        return self._group
