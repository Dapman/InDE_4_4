"""
InDE v3.2 - Event System Integration Tests
Tests Redis Streams publisher, consumer, and graceful degradation.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# Add app directory to path for imports
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

os.chdir(app_dir)


class TestRedisPublisherImports:
    """Test that v3.2 Redis publisher modules can be imported."""

    def test_redis_publisher_import(self):
        from events.redis_publisher import RedisStreamPublisher, publisher
        assert RedisStreamPublisher is not None
        assert publisher is not None

    def test_redis_consumer_import(self):
        from events.redis_consumer import RedisStreamConsumer
        assert RedisStreamConsumer is not None

    def test_consumer_registry_import(self):
        from events.consumer_registry import create_app_consumers, register_fallback_handlers
        assert create_app_consumers is not None
        assert register_fallback_handlers is not None

    def test_dead_letter_import(self):
        from events.dead_letter import DeadLetterQueue
        assert DeadLetterQueue is not None


class TestEventSchemas:
    """Test v3.2 event schema enhancements."""

    def test_domain_event_has_correlation_id(self):
        from events.schemas import DomainEvent

        event = DomainEvent(
            event_type="test.event",
            user_id="user1",
            pursuit_id="pursuit1",
            payload={"test": "data"}
        )

        # correlation_id should be optional
        assert hasattr(event, 'correlation_id')

    def test_domain_event_has_source_module(self):
        from events.schemas import DomainEvent

        event = DomainEvent(
            event_type="test.event",
            user_id="user1",
            pursuit_id="pursuit1",
            payload={},
            source_module="test-module"
        )

        assert event.source_module == "test-module"

    def test_ikf_event_types_exist(self):
        from events.schemas import (
            IKFPackagePreparedEvent,
            IKFPackageReviewedEvent,
            IKFPackageReadyEvent,
            IKFFederationStatusEvent
        )

        assert IKFPackagePreparedEvent is not None
        assert IKFPackageReviewedEvent is not None
        assert IKFPackageReadyEvent is not None
        assert IKFFederationStatusEvent is not None

    def test_event_types_constants(self):
        from events.schemas import EventTypes

        assert EventTypes.PURSUIT_CREATED == "pursuit.created"
        assert EventTypes.IKF_PACKAGE_PREPARED == "ikf.package.prepared"
        assert EventTypes.RETROSPECTIVE_COMPLETED == "retrospective.completed"


class TestRedisPublisher:
    """Test RedisStreamPublisher functionality."""

    def test_publisher_initialization(self):
        from events.redis_publisher import RedisStreamPublisher

        pub = RedisStreamPublisher()
        assert pub._connected is False
        assert pub._redis is None

    def test_stream_routing(self):
        from events.redis_publisher import RedisStreamPublisher

        pub = RedisStreamPublisher()

        # Test routing logic
        assert "pursuit" in pub._route_to_stream("pursuit.created")
        assert "coaching" in pub._route_to_stream("coaching.message.exchanged")
        assert "element" in pub._route_to_stream("element.captured")
        assert "maturity" in pub._route_to_stream("maturity.level.changed")
        assert "health" in pub._route_to_stream("health.score.updated")
        assert "ikf" in pub._route_to_stream("ikf.package.prepared")

    @pytest.mark.asyncio
    async def test_publish_persists_to_mongo(self):
        from events.redis_publisher import RedisStreamPublisher
        from events.schemas import PursuitCreatedEvent

        # Mock database
        mock_db = MagicMock()
        mock_db.db.domain_events.insert_one = MagicMock()

        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value="1234567890-0")

        pub = RedisStreamPublisher()
        pub._db = mock_db
        pub._redis = mock_redis
        pub._connected = True

        event = PursuitCreatedEvent(
            user_id="user1",
            pursuit_id="pursuit1",
            payload={"title": "Test"}
        )

        entry_id = await pub.publish(event)

        # Verify MongoDB persistence (dual-write) to domain_events collection
        assert mock_db.db.domain_events.insert_one.called

        # Verify Redis publish
        assert mock_redis.xadd.called
        assert entry_id == "1234567890-0"


class TestRedisConsumer:
    """Test RedisStreamConsumer functionality."""

    def test_consumer_initialization(self):
        from events.redis_consumer import RedisStreamConsumer

        consumer = RedisStreamConsumer(group_name="test-group")
        assert consumer._group == "test-group"
        assert consumer._running is False
        assert len(consumer._handlers) == 0

    def test_handler_registration(self):
        from events.redis_consumer import RedisStreamConsumer

        consumer = RedisStreamConsumer(group_name="test-group")

        def test_handler(event):
            pass

        consumer.register_handler("test.event", test_handler)

        assert "test.event" in consumer._handlers
        assert test_handler in consumer._handlers["test.event"]

    def test_wildcard_handler_matching(self):
        from events.redis_consumer import RedisStreamConsumer

        consumer = RedisStreamConsumer(group_name="test-group")

        def handler1(event):
            pass

        def handler2(event):
            pass

        def handler_all(event):
            pass

        consumer.register_handler("coaching.message.exchanged", handler1)
        consumer.register_handler("coaching.*", handler2)
        consumer.register_handler("*", handler_all)

        # Exact match
        matched = consumer._match_handlers("coaching.message.exchanged")
        assert handler1 in matched

        # Wildcard category match
        matched = consumer._match_handlers("coaching.session.started")
        assert handler2 in matched

        # Global wildcard
        matched = consumer._match_handlers("any.event.type")
        assert handler_all in matched

    def test_stream_derivation_from_handlers(self):
        from events.redis_consumer import RedisStreamConsumer

        consumer = RedisStreamConsumer(group_name="test-group")
        consumer.register_handler("pursuit.created", lambda e: None)
        consumer.register_handler("coaching.message", lambda e: None)

        streams = consumer._get_subscribed_streams()

        assert any("pursuit" in s for s in streams)
        assert any("coaching" in s for s in streams)


class TestConsumerRegistry:
    """Test consumer registry functionality."""

    def test_creates_multiple_consumer_groups(self):
        from events.consumer_registry import create_app_consumers

        consumers = create_app_consumers(db=None)

        # Should create at least 5 consumer groups
        assert len(consumers) >= 5

        # Verify expected consumer groups exist
        group_names = [c.group_name for c in consumers]
        assert "maturity-engine" in group_names
        assert "health-monitor" in group_names
        assert "crisis-monitor" in group_names
        assert "temporal-logger" in group_names
        assert "portfolio-intel" in group_names

    def test_fallback_handlers_registered(self):
        from events.consumer_registry import register_fallback_handlers
        from events.dispatcher import EventDispatcher

        dispatcher = EventDispatcher(db=None, persist=False)

        # Should not raise
        register_fallback_handlers(dispatcher, db=None)

        # Verify critical event types have fallback handlers
        assert "pursuit.created" in dispatcher._fallback_handlers
        assert "pursuit.completed" in dispatcher._fallback_handlers
        assert "element.captured" in dispatcher._fallback_handlers
        assert "crisis.triggered" in dispatcher._fallback_handlers


class TestDeadLetterQueue:
    """Test dead letter queue functionality."""

    def test_dead_letter_initialization(self):
        from events.dead_letter import DeadLetterQueue

        mock_db = MagicMock()
        dlq = DeadLetterQueue(db=mock_db)

        assert dlq._db == mock_db

    def test_get_dead_letters_query(self):
        from events.dead_letter import DeadLetterQueue

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = []
        mock_db.db.event_dead_letters.find.return_value = mock_cursor

        dlq = DeadLetterQueue(db=mock_db)
        result = dlq.get_dead_letters(limit=10, consumer_group="test-group")

        # Verify query was made
        assert mock_db.db.event_dead_letters.find.called

    def test_get_stats_aggregation(self):
        from events.dead_letter import DeadLetterQueue

        mock_db = MagicMock()
        mock_db.db.event_dead_letters.aggregate.return_value = [
            {"_id": "group1", "count": 5, "oldest": datetime.now(timezone.utc), "newest": datetime.now(timezone.utc)},
            {"_id": "group2", "count": 3, "oldest": datetime.now(timezone.utc), "newest": datetime.now(timezone.utc)}
        ]

        dlq = DeadLetterQueue(db=mock_db)
        stats = dlq.get_stats()

        assert stats["total"] == 8
        assert "group1" in stats["by_group"]
        assert "group2" in stats["by_group"]


class TestGracefulDegradation:
    """Test graceful degradation when Redis unavailable."""

    def test_fallback_dispatch_without_redis(self):
        from events.dispatcher import EventDispatcher
        from events.schemas import PursuitCreatedEvent

        # Create dispatcher without Redis connection
        dispatcher = EventDispatcher(db=None, persist=False)

        # Track handler calls
        handled_events = []

        def fallback_handler(event):
            handled_events.append(event)

        dispatcher.register("pursuit.created", fallback_handler)

        # Emit event (should use fallback since no Redis)
        event = PursuitCreatedEvent(
            user_id="test_user",
            pursuit_id="test_pursuit",
            payload={"title": "Test"}
        )
        dispatcher.emit(event)

        # Verify fallback handler was called
        assert len(handled_events) == 1
        assert handled_events[0].pursuit_id == "test_pursuit"

    def test_correlation_id_assigned(self):
        from events.dispatcher import EventDispatcher
        from events.schemas import PursuitCreatedEvent

        dispatcher = EventDispatcher(db=None, persist=False)

        captured_event = None

        def capture_handler(event):
            nonlocal captured_event
            captured_event = event

        dispatcher.register("pursuit.created", capture_handler)

        event = PursuitCreatedEvent(
            user_id="test_user",
            pursuit_id="test_pursuit",
            payload={}
        )

        # Event should not have correlation_id initially
        assert not event.correlation_id

        dispatcher.emit(event)

        # After emit, correlation_id should be assigned
        assert captured_event is not None
        assert captured_event.correlation_id is not None


class TestEventRoundtrip:
    """Test full event roundtrip (publish → consume)."""

    @pytest.mark.asyncio
    async def test_message_processing(self):
        from events.redis_consumer import RedisStreamConsumer
        from events.schemas import DomainEvent

        consumer = RedisStreamConsumer(group_name="test-group")

        processed_events = []

        def handler(event):
            processed_events.append(event)

        consumer.register_handler("test.event", handler)

        # Simulate message processing
        mock_data = {
            "data": DomainEvent(
                event_type="test.event",
                user_id="user1",
                pursuit_id="pursuit1",
                payload={"test": "data"}
            ).model_dump_json()
        }

        # Mock Redis for ack
        consumer._redis = AsyncMock()
        consumer._redis.xack = AsyncMock()

        await consumer._process_message("inde:events:test", "msg-123", mock_data)

        # Verify handler was called
        assert len(processed_events) == 1
        assert processed_events[0].event_type == "test.event"
        assert processed_events[0].user_id == "user1"


class TestVersionUpdate:
    """Test v3.2 version configuration."""

    def test_version_is_3_2(self):
        # Import from sys.path already set at module level
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "config",
            os.path.join(app_dir, "core", "config.py")
        )
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)

        assert config.VERSION == "3.5.1"
        assert "Federation Protocol" in config.VERSION_NAME

    def test_redis_config_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "config",
            os.path.join(app_dir, "core", "config.py")
        )
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)

        assert "url" in config.REDIS_CONFIG
        assert "stream_prefix" in config.REDIS_CONFIG


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
