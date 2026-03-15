"""
InDE v3.2 - Redis Streams Publisher
Publishes events to Redis Streams with automatic stream routing.

Stream routing: event_type "pursuit.created" -> stream "inde:events:pursuit"
The category is the first segment of the dotted event_type.

Fallback: If Redis is unavailable, queues events in-memory for later replay.
All events are ALSO persisted to MongoDB domain_events collection (dual-write).
"""

import redis.asyncio as aioredis
import logging
import os
from datetime import datetime, timezone
from typing import Optional, List
from events.schemas import DomainEvent

logger = logging.getLogger("inde.events.redis")


class RedisStreamPublisher:
    """
    Publishes events to Redis Streams with automatic stream routing.

    Features:
    - Automatic routing based on event category
    - Fallback queue when Redis unavailable
    - Dual-write to MongoDB for audit trail
    - Automatic replay on reconnection
    """

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._prefix = os.environ.get("REDIS_STREAM_PREFIX", "inde:events:")
        self._fallback_queue: List[DomainEvent] = []
        self._connected = False
        self._db = None

    async def connect(self, db=None):
        """
        Connect to Redis. Called at application startup.

        Args:
            db: Optional database instance for MongoDB dual-write
        """
        self._db = db
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

        try:
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            self._connected = True
            logger.info(f"Redis publisher connected to {redis_url}")

            # Replay any queued events from previous disconnection
            await self._replay_queue()

        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), using in-memory fallback")
            self._connected = False

    def _route_to_stream(self, event_type: str) -> str:
        """
        Route event to appropriate Redis Stream by category.

        'pursuit.created' -> 'inde:events:pursuit'
        'coaching.message.exchanged' -> 'inde:events:coaching'
        """
        category = event_type.split(".")[0]
        return f"{self._prefix}{category}"

    async def publish(self, event: DomainEvent) -> str:
        """
        Publish event to Redis Stream.

        Returns: Redis stream entry ID (e.g., "1234567890-0") or "fallback" if queued.

        CRITICAL: Also persists to MongoDB domain_events for audit trail.
        This dual-write ensures no events are lost even if Redis fails.
        """
        # Always persist to MongoDB (audit + replay source)
        self._persist_to_mongo(event)

        if self._connected and self._redis:
            try:
                stream = self._route_to_stream(event.event_type)
                entry_id = await self._redis.xadd(
                    stream,
                    {"data": event.model_dump_json()},
                    maxlen=10000  # Trim streams to prevent unbounded growth
                )
                logger.debug(f"Published {event.event_type} to {stream}: {entry_id}")
                return entry_id
            except Exception as e:
                logger.warning(f"Redis publish failed ({e}), queueing for replay")
                self._connected = False
                self._fallback_queue.append(event)
                return "fallback"
        else:
            self._fallback_queue.append(event)
            return "fallback"

    def publish_sync(self, event: DomainEvent) -> str:
        """
        Synchronous publish for contexts without async loop.

        Returns: "sync_persisted" - event only persisted to MongoDB.
        Redis publish will happen on replay.
        """
        self._persist_to_mongo(event)
        self._fallback_queue.append(event)
        return "sync_persisted"

    def _persist_to_mongo(self, event: DomainEvent):
        """Persist event to domain_events collection for audit trail."""
        if not self._db:
            return

        try:
            doc = event.model_dump()
            doc["persisted_at"] = datetime.now(timezone.utc)
            self._db.db.domain_events.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to persist event to MongoDB: {e}")

    async def _replay_queue(self):
        """Replay queued events to Redis after reconnection."""
        if not self._fallback_queue:
            return

        count = len(self._fallback_queue)
        logger.info(f"Replaying {count} queued events to Redis")

        replayed = 0
        while self._fallback_queue:
            event = self._fallback_queue.pop(0)
            try:
                stream = self._route_to_stream(event.event_type)
                await self._redis.xadd(stream, {"data": event.model_dump_json()})
                replayed += 1
            except Exception:
                self._fallback_queue.insert(0, event)
                break

        logger.info(f"Replayed {replayed}/{count} events")

    async def health_check(self) -> dict:
        """Return Redis connection health status."""
        if self._connected and self._redis:
            try:
                await self._redis.ping()
                return {
                    "status": "connected",
                    "queued_events": len(self._fallback_queue)
                }
            except Exception:
                self._connected = False

        return {
            "status": "disconnected",
            "queued_events": len(self._fallback_queue)
        }

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected

    @property
    def queued_count(self) -> int:
        """Get number of queued events awaiting replay."""
        return len(self._fallback_queue)


# Singleton instance
publisher = RedisStreamPublisher()
