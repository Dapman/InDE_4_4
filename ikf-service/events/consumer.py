"""
InDE IKF Service - Redis Streams Consumer
Consumes events relevant to IKF processing from Redis Streams.
"""

import redis.asyncio as aioredis
import asyncio
import logging
import os
from typing import Dict, List, Callable
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger("inde.ikf.consumer")


class EventPayload(BaseModel):
    """Event schema - mirrors app schema."""
    event_id: str = ""
    event_type: str
    timestamp: datetime
    source_module: str
    pursuit_id: str = None
    user_id: str = None
    correlation_id: str = None
    payload: dict = {}


class IKFEventConsumer:
    """Redis Streams consumer for IKF-relevant events."""

    def __init__(self, db=None, publisher=None):
        self._redis = None
        self._db = db
        self._publisher = publisher
        self._group = os.environ.get("IKF_CONSUMER_GROUP", "ikf-pipeline")
        self._consumer = f"ikf-worker-{os.getpid()}"
        self._prefix = os.environ.get("REDIS_STREAM_PREFIX", "inde:events:")
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._preparer = None

        # Register IKF-specific handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register all IKF event handlers."""
        # Pursuit completion triggers contribution preparation
        self.register_handler("pursuit.completed", self._on_pursuit_completed)
        self.register_handler("pursuit.terminated", self._on_pursuit_completed)

        # Retrospective completion triggers wisdom package
        self.register_handler("retrospective.completed", self._on_retrospective_completed)

        # RVE experiments can contribute to risk intelligence
        self.register_handler("rve.experiment.completed", self._on_rve_experiment_completed)

        # Maturity advancement triggers effectiveness metrics
        self.register_handler("maturity.level.advanced", self._on_maturity_advanced)

    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def connect(self):
        """Connect to Redis and ensure consumer groups exist."""
        url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        try:
            self._redis = aioredis.from_url(url, decode_responses=True)
            await self._redis.ping()

            # Create consumer group on relevant streams
            for stream in self._get_streams():
                try:
                    await self._redis.xgroup_create(stream, self._group, id="0", mkstream=True)
                    logger.info(f"Created consumer group '{self._group}' on '{stream}'")
                except aioredis.ResponseError as e:
                    if "BUSYGROUP" not in str(e):
                        raise

            logger.info(f"IKF consumer connected, group='{self._group}'")
        except Exception as e:
            logger.error(f"Failed to connect IKF consumer: {e}")
            raise

    def _get_streams(self) -> List[str]:
        """Derive stream names from registered handler event types."""
        categories = set()
        for event_type in self._handlers:
            category = event_type.split(".")[0]
            categories.add(category)
        return [f"{self._prefix}{cat}" for cat in categories]

    async def start(self):
        """Main consumption loop."""
        self._running = True
        streams = {s: ">" for s in self._get_streams()}

        if not streams:
            logger.warning("IKF consumer has no streams to consume")
            return

        logger.info(f"IKF consumer starting on streams: {list(streams.keys())}")

        while self._running:
            try:
                results = await self._redis.xreadgroup(
                    self._group, self._consumer, streams,
                    count=5, block=5000
                )
                for stream, messages in results:
                    for msg_id, data in messages:
                        await self._process(stream, msg_id, data)
            except asyncio.CancelledError:
                logger.info("IKF consumer shutting down")
                break
            except Exception as e:
                logger.error(f"IKF consumer error: {e}")
                await asyncio.sleep(2)

    async def _process(self, stream: str, msg_id: str, data: dict):
        """Process a single message."""
        try:
            event = EventPayload.model_validate_json(data.get("data", "{}"))

            # Find matching handlers
            for pattern, handlers in self._handlers.items():
                if pattern == event.event_type or \
                   (pattern.endswith(".*") and event.event_type.startswith(pattern[:-2])):
                    for handler in handlers:
                        try:
                            result = handler(event)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.error(f"Handler failed for {event.event_type}: {e}")

            # Acknowledge message
            await self._redis.xack(stream, self._group, msg_id)

        except Exception as e:
            logger.error(f"IKF processing failed for {msg_id}: {e}")

    async def stop(self):
        """Gracefully stop the consumer."""
        self._running = False
        if self._redis:
            await self._redis.close()

    def _get_preparer(self):
        """Lazy-load the contribution preparer."""
        if self._preparer is None and self._db:
            from contribution.preparer import IKFContributionPreparer
            self._preparer = IKFContributionPreparer(self._db, self._publisher)
        return self._preparer

    # === Event Handlers ===

    async def _on_pursuit_completed(self, event: EventPayload):
        """Auto-prepare IKF contribution packages when pursuit completes."""
        logger.info(f"IKF: Pursuit completed/terminated {event.pursuit_id}, preparing contributions")

        preparer = self._get_preparer()
        if not preparer:
            logger.warning("No preparer available, skipping auto-preparation")
            return

        # Prepare multiple package types for completed pursuits
        # v3.6.0: Added biomimicry_application to capture biological insights applied during pursuit
        package_types = ["pattern_contribution", "temporal_benchmark", "risk_intelligence", "biomimicry_application"]

        for pkg_type in package_types:
            try:
                result = await preparer.prepare(
                    pursuit_id=event.pursuit_id,
                    package_type=pkg_type,
                    auto_triggered=True,
                    trigger_priority="high"  # pursuit.completed has high priority
                )
                if result.get("success"):
                    logger.info(f"Auto-prepared {pkg_type} package: {result.get('contribution_id')}")
                elif result.get("rate_limited"):
                    logger.debug(f"Rate limited for {pkg_type}: {result.get('error')}")
                else:
                    logger.warning(f"Failed to prepare {pkg_type}: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error preparing {pkg_type}: {e}")

    async def _on_retrospective_completed(self, event: EventPayload):
        """Auto-prepare retrospective wisdom package."""
        logger.info(f"IKF: Retrospective completed for {event.pursuit_id}")

        preparer = self._get_preparer()
        if not preparer:
            return

        try:
            result = await preparer.prepare(
                pursuit_id=event.pursuit_id,
                package_type="retrospective_wisdom",
                auto_triggered=True,
                trigger_priority="high"
            )
            if result.get("success"):
                logger.info(f"Auto-prepared retrospective wisdom: {result.get('contribution_id')}")
        except Exception as e:
            logger.error(f"Error preparing retrospective wisdom: {e}")

    async def _on_rve_experiment_completed(self, event: EventPayload):
        """Queue risk intelligence package after sufficient experiments."""
        logger.info(f"IKF: RVE experiment completed in {event.pursuit_id}")

        # Check if we have enough experiments to warrant a package
        if self._db:
            experiment_count = self._db.rve_experiments.count_documents({
                "pursuit_id": event.pursuit_id,
                "status": "COMPLETED"
            })

            # Only trigger after 3+ experiments
            if experiment_count >= 3 and experiment_count % 3 == 0:
                preparer = self._get_preparer()
                if preparer:
                    try:
                        result = await preparer.prepare(
                            pursuit_id=event.pursuit_id,
                            package_type="risk_intelligence",
                            auto_triggered=True,
                            trigger_priority="normal"
                        )
                        if result.get("success"):
                            logger.info(f"Auto-prepared risk intelligence: {result.get('contribution_id')}")
                    except Exception as e:
                        logger.error(f"Error preparing risk intelligence: {e}")

    async def _on_maturity_advanced(self, event: EventPayload):
        """Prepare effectiveness metrics on maturity level advancement."""
        logger.info(f"IKF: Maturity advanced for user {event.user_id}")

        # Only prepare after advancing to ADVANCED or MASTER level
        payload = event.payload or {}
        new_level = payload.get("new_level", "")

        if new_level in ("ADVANCED", "MASTER"):
            # Get any recent pursuit for this user
            if self._db:
                recent_pursuit = self._db.pursuits.find_one(
                    {"user_id": event.user_id},
                    sort=[("updated_at", -1)]
                )
                if recent_pursuit:
                    preparer = self._get_preparer()
                    if preparer:
                        try:
                            result = await preparer.prepare(
                                pursuit_id=recent_pursuit.get("pursuit_id"),
                                package_type="effectiveness_metrics",
                                auto_triggered=True,
                                trigger_priority="normal"
                            )
                            if result.get("success"):
                                logger.info(f"Auto-prepared effectiveness metrics: {result.get('contribution_id')}")
                        except Exception as e:
                            logger.error(f"Error preparing effectiveness metrics: {e}")
