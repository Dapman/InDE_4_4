"""
InDE MVP v3.4 - Audit Pipeline
Non-blocking audit event capture via Redis Streams with MongoDB persistence.

SOC 2 Ready:
- Immutable audit trail (append-only collection)
- Event correlation for multi-operation tracking
- Configurable retention with TTL indexes
- Sub-50ms async publishing (fire-and-forget)

Architecture:
1. AuditPublisher: Non-blocking publish to Redis Streams (audit stream)
2. AuditConsumer: Consumer group that persists events to MongoDB
3. API endpoints for query and export
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from core.config import AUDIT_CONFIG, REDIS_CONFIG, AUDIT_EVENT_TYPES, AUDIT_OUTCOMES

logger = logging.getLogger("inde.audit")

# Optional Redis imports
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("aioredis not available, audit events will be logged only")


# =============================================================================
# AUDIT EVENT SCHEMA
# =============================================================================

class AuditEvent:
    """
    SOC 2-ready audit event.

    Attributes:
        event_id: Unique event identifier
        timestamp: ISO 8601 timestamp
        event_type: One of AUDIT_EVENT_TYPES
        actor_id: User who performed the action
        actor_role: Role of the actor
        org_id: Organization context (if applicable)
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        action_detail: Additional action metadata
        ip_address: Client IP (if available)
        outcome: SUCCESS | FAILURE | DENIED
        correlation_id: For tracking multi-event operations
    """

    def __init__(
        self,
        event_type: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        actor_role: str = None,
        org_id: str = None,
        action_detail: Dict[str, Any] = None,
        ip_address: str = None,
        outcome: str = "SUCCESS",
        correlation_id: str = None,
        event_id: str = None
    ):
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc)
        self.event_type = event_type
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.org_id = org_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.action_detail = action_detail or {}
        self.ip_address = ip_address
        self.outcome = outcome
        self.correlation_id = correlation_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "org_id": self.org_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action_detail": self.action_detail,
            "ip_address": self.ip_address,
            "outcome": self.outcome,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Create from dictionary."""
        event = cls(
            event_type=data["event_type"],
            actor_id=data["actor_id"],
            resource_type=data["resource_type"],
            resource_id=data["resource_id"],
            actor_role=data.get("actor_role"),
            org_id=data.get("org_id"),
            action_detail=data.get("action_detail", {}),
            ip_address=data.get("ip_address"),
            outcome=data.get("outcome", "SUCCESS"),
            correlation_id=data.get("correlation_id"),
            event_id=data.get("event_id")
        )
        if "timestamp" in data:
            if isinstance(data["timestamp"], str):
                event.timestamp = datetime.fromisoformat(data["timestamp"])
            else:
                event.timestamp = data["timestamp"]
        return event


# =============================================================================
# AUDIT PUBLISHER (Non-blocking)
# =============================================================================

class AuditPublisher:
    """
    Non-blocking audit event publisher.

    Publishes audit events to Redis Streams with fire-and-forget semantics.
    If Redis is unavailable, events are logged to application log.
    """

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._stream_name = f"{REDIS_CONFIG['stream_prefix']}audit"
        self._connected = False
        self._fallback_queue: List[AuditEvent] = []

    async def connect(self):
        """Establish Redis connection."""
        if not REDIS_AVAILABLE:
            logger.info("Audit publisher running in log-only mode (no Redis)")
            return

        try:
            self._redis = aioredis.from_url(
                REDIS_CONFIG["url"],
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
            self._connected = True
            logger.info(f"Audit publisher connected to Redis: {self._stream_name}")

            # Flush any queued events
            if self._fallback_queue:
                for event in self._fallback_queue:
                    await self._publish_to_redis(event)
                self._fallback_queue.clear()

        except Exception as e:
            logger.warning(f"Failed to connect audit publisher to Redis: {e}")
            self._connected = False

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._connected = False

    async def publish(self, event: AuditEvent) -> bool:
        """
        Publish an audit event (non-blocking).

        Returns True if published successfully, False if fallback was used.
        """
        # Always log the event
        logger.info(f"AUDIT: {event.event_type} | {event.actor_id} | "
                   f"{event.resource_type}:{event.resource_id} | {event.outcome}")

        if not self._connected or not REDIS_AVAILABLE:
            self._fallback_queue.append(event)
            return False

        try:
            # Fire-and-forget with timeout
            await asyncio.wait_for(
                self._publish_to_redis(event),
                timeout=AUDIT_CONFIG.get("async_timeout_ms", 50) / 1000
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Audit publish timeout for event {event.event_id}")
            self._fallback_queue.append(event)
            return False
        except Exception as e:
            logger.error(f"Audit publish error: {e}")
            self._fallback_queue.append(event)
            return False

    async def _publish_to_redis(self, event: AuditEvent):
        """Publish event to Redis Stream."""
        await self._redis.xadd(
            self._stream_name,
            {"data": json.dumps(event.to_dict())},
            maxlen=REDIS_CONFIG.get("stream_maxlen", 10000)
        )

    def publish_sync(self, event: AuditEvent):
        """
        Synchronous publish wrapper for non-async contexts.

        Uses asyncio.create_task to avoid blocking.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.publish(event))
            else:
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # No event loop, just log
            logger.info(f"AUDIT (sync): {event.event_type} | {event.actor_id}")


# Global publisher instance
_publisher: Optional[AuditPublisher] = None


def get_audit_publisher() -> AuditPublisher:
    """Get or create the global audit publisher."""
    global _publisher
    if _publisher is None:
        _publisher = AuditPublisher()
    return _publisher


async def init_audit_publisher():
    """Initialize the audit publisher (call on app startup)."""
    publisher = get_audit_publisher()
    await publisher.connect()
    return publisher


# =============================================================================
# AUDIT CONSUMER (Persistence)
# =============================================================================

class AuditConsumer:
    """
    Consumer that persists audit events from Redis to MongoDB.

    Runs as background task, reading from audit stream consumer group.
    """

    def __init__(self, db):
        self._redis: Optional[aioredis.Redis] = None
        self._db = db
        self._stream_name = f"{REDIS_CONFIG['stream_prefix']}audit"
        self._group_name = "audit-persistence-consumer"
        self._consumer_name = f"consumer-{uuid.uuid4().hex[:8]}"
        self._running = False

    async def start(self):
        """Start the audit consumer."""
        if not REDIS_AVAILABLE:
            logger.info("Audit consumer not started (no Redis)")
            return

        try:
            self._redis = aioredis.from_url(
                REDIS_CONFIG["url"],
                encoding="utf-8",
                decode_responses=True
            )

            # Create consumer group if it doesn't exist
            try:
                await self._redis.xgroup_create(
                    self._stream_name,
                    self._group_name,
                    id="0",
                    mkstream=True
                )
            except Exception:
                pass  # Group already exists

            self._running = True
            logger.info(f"Audit consumer started: {self._consumer_name}")

            # Start consuming
            asyncio.create_task(self._consume_loop())

        except Exception as e:
            logger.error(f"Failed to start audit consumer: {e}")

    async def stop(self):
        """Stop the audit consumer."""
        self._running = False
        if self._redis:
            await self._redis.close()

    async def _consume_loop(self):
        """Main consume loop."""
        while self._running:
            try:
                # Read from stream
                messages = await self._redis.xreadgroup(
                    groupname=self._group_name,
                    consumername=self._consumer_name,
                    streams={self._stream_name: ">"},
                    count=AUDIT_CONFIG.get("stream_batch_size", 100),
                    block=REDIS_CONFIG.get("consumer_block_ms", 5000)
                )

                if messages:
                    for stream_name, stream_messages in messages:
                        for message_id, message_data in stream_messages:
                            await self._process_message(message_id, message_data)

            except Exception as e:
                logger.error(f"Audit consumer error: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, message_id: str, message_data: Dict):
        """Process a single audit event message."""
        try:
            # Parse event
            event_data = json.loads(message_data.get("data", "{}"))
            event = AuditEvent.from_dict(event_data)

            # Persist to MongoDB
            self._db.create_audit_event(event.to_dict())

            # Acknowledge message
            await self._redis.xack(
                self._stream_name,
                self._group_name,
                message_id
            )

        except Exception as e:
            logger.error(f"Failed to process audit event {message_id}: {e}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def audit_login(actor_id: str, success: bool, ip_address: str = None,
                org_id: str = None, details: Dict = None):
    """Audit a login event."""
    event = AuditEvent(
        event_type="AUTH_LOGIN" if success else "AUTH_FAILED",
        actor_id=actor_id,
        resource_type="session",
        resource_id="login",
        org_id=org_id,
        ip_address=ip_address,
        outcome="SUCCESS" if success else "FAILURE",
        action_detail=details or {}
    )
    get_audit_publisher().publish_sync(event)


def audit_logout(actor_id: str, ip_address: str = None, org_id: str = None):
    """Audit a logout event."""
    event = AuditEvent(
        event_type="AUTH_LOGOUT",
        actor_id=actor_id,
        resource_type="session",
        resource_id="logout",
        org_id=org_id,
        ip_address=ip_address,
        outcome="SUCCESS"
    )
    get_audit_publisher().publish_sync(event)


def audit_resource_access(actor_id: str, resource_type: str, resource_id: str,
                          action: str, org_id: str = None,
                          actor_role: str = None, outcome: str = "SUCCESS",
                          correlation_id: str = None, details: Dict = None):
    """Audit a resource access event."""
    event = AuditEvent(
        event_type="RESOURCE_ACCESS",
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type=resource_type,
        resource_id=resource_id,
        org_id=org_id,
        outcome=outcome,
        correlation_id=correlation_id,
        action_detail={"action": action, **(details or {})}
    )
    get_audit_publisher().publish_sync(event)


def audit_resource_change(actor_id: str, resource_type: str, resource_id: str,
                          change_type: str, org_id: str = None,
                          actor_role: str = None, correlation_id: str = None,
                          details: Dict = None):
    """
    Audit a resource creation, update, or deletion.

    change_type: CREATE | UPDATE | DELETE
    """
    event_type_map = {
        "CREATE": "RESOURCE_CREATE",
        "UPDATE": "RESOURCE_UPDATE",
        "DELETE": "RESOURCE_DELETE"
    }
    event = AuditEvent(
        event_type=event_type_map.get(change_type, "RESOURCE_UPDATE"),
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type=resource_type,
        resource_id=resource_id,
        org_id=org_id,
        outcome="SUCCESS",
        correlation_id=correlation_id,
        action_detail=details or {}
    )
    get_audit_publisher().publish_sync(event)


def audit_permission_change(actor_id: str, target_user_id: str,
                            change_description: str, org_id: str,
                            actor_role: str = None, details: Dict = None):
    """Audit a permission or role change."""
    event = AuditEvent(
        event_type="PERMISSION_CHANGE",
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="user",
        resource_id=target_user_id,
        org_id=org_id,
        outcome="SUCCESS",
        action_detail={"change": change_description, **(details or {})}
    )
    get_audit_publisher().publish_sync(event)


def audit_policy_change(actor_id: str, policy_type: str, org_id: str,
                        actor_role: str = None, details: Dict = None):
    """Audit a policy configuration change."""
    event = AuditEvent(
        event_type="POLICY_CHANGE",
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="policy",
        resource_id=policy_type,
        org_id=org_id,
        outcome="SUCCESS",
        action_detail=details or {}
    )
    get_audit_publisher().publish_sync(event)


def audit_data_export(actor_id: str, export_type: str, org_id: str,
                      record_count: int = None, actor_role: str = None):
    """Audit a data export event."""
    event = AuditEvent(
        event_type="DATA_EXPORT",
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="export",
        resource_id=export_type,
        org_id=org_id,
        outcome="SUCCESS",
        action_detail={"record_count": record_count}
    )
    get_audit_publisher().publish_sync(event)


def audit_admin_action(actor_id: str, action: str, target_type: str,
                       target_id: str, org_id: str = None,
                       actor_role: str = None, details: Dict = None):
    """Audit an administrative action."""
    event = AuditEvent(
        event_type="ADMIN_ACTION",
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type=target_type,
        resource_id=target_id,
        org_id=org_id,
        outcome="SUCCESS",
        action_detail={"action": action, **(details or {})}
    )
    get_audit_publisher().publish_sync(event)


@asynccontextmanager
async def audit_correlation(actor_id: str, operation: str):
    """
    Context manager for correlated audit events.

    Usage:
        async with audit_correlation(user_id, "bulk_import") as correlation_id:
            # Multiple operations here will share the correlation_id
            ...
    """
    correlation_id = str(uuid.uuid4())
    logger.debug(f"Starting correlated audit: {operation} ({correlation_id})")
    try:
        yield correlation_id
    finally:
        logger.debug(f"Completed correlated audit: {operation} ({correlation_id})")
