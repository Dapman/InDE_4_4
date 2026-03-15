"""
InDE IKF Service v3.5.1 - Redis Streams Publisher
Publishes IKF-related events to Redis Streams.

Supports multiple streams:
- inde:events:ikf - Core IKF events (contributions, patterns)
- inde:events:federation - Federation lifecycle events (connect, heartbeat, etc.)
"""

import redis.asyncio as aioredis
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger("inde.ikf.publisher")


class EventPayload(BaseModel):
    """Event schema - mirrors app schema."""
    event_id: str = ""
    event_type: str
    timestamp: datetime
    source_module: str
    pursuit_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    payload: dict = {}


class IKFEventPublisher:
    """Publishes IKF events to Redis Streams."""

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._prefix = os.environ.get("REDIS_STREAM_PREFIX", "inde:events:")
        self._connected = False

    async def connect(self):
        """Connect to Redis."""
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        try:
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            self._connected = True
            logger.info(f"IKF publisher connected to Redis: {redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), IKF events will not be published")
            self._connected = False

    async def publish(self, event: EventPayload) -> str:
        """Publish event to Redis Stream."""
        if not self._connected or not self._redis:
            logger.warning("Redis not connected, event not published")
            return "not_connected"

        try:
            stream = f"{self._prefix}ikf"
            entry_id = await self._redis.xadd(
                stream,
                {"data": event.model_dump_json()},
                maxlen=10000
            )
            logger.debug(f"Published IKF event: {event.event_type}")
            return entry_id
        except Exception as e:
            logger.error(f"Failed to publish IKF event: {e}")
            return "error"

    async def health_check(self) -> dict:
        """Return Redis connection health status."""
        if self._connected and self._redis:
            try:
                await self._redis.ping()
                return {"connected": True, "status": "healthy"}
            except Exception:
                self._connected = False
        return {"connected": False, "status": "disconnected"}

    async def publish_federation_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Publish to the federation stream (fire-and-forget).

        Federation events are for observability and audit.
        They must NEVER block user-facing operations.

        Args:
            event_type: Qualified event name (e.g., "federation.connected")
            data: Event payload data

        Returns:
            Entry ID or error indicator
        """
        if not self._connected or not self._redis:
            logger.debug("Redis not connected, federation event not published")
            return "not_connected"

        try:
            stream = f"{self._prefix}federation"

            # Ensure timestamp is present
            if "timestamp" not in data:
                data["timestamp"] = datetime.now(timezone.utc).isoformat()

            # Always include event_type in payload
            data["event_type"] = event_type

            entry_id = await self._redis.xadd(
                stream,
                {
                    "event_type": event_type,
                    "data": json.dumps(data, default=str)
                },
                maxlen=10000
            )
            logger.debug(f"Published federation event: {event_type}")
            return entry_id

        except Exception as e:
            # Federation events must NEVER block - log and continue
            logger.warning(f"Federation event publish failed (non-blocking): {e}")
            return "error"

    async def close(self):
        """Disconnect from Redis (alias for disconnect)."""
        await self.disconnect()

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._connected = False
