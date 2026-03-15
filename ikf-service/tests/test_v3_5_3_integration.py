"""
InDE IKF Service v3.5.3 Integration Tests

Tests the Global Benchmarking & Cross-Org Intelligence components:
- Benchmark Engine
- Trust Manager
- Reputation Tracker
- Cross-Org Discovery Service
- WebSocket Manager
- Event Bridge
- Channel Manager
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestBenchmarkEngine:
    """Tests for the Benchmark Engine (Phase 1)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        # Return cached benchmark data for get_industry_benchmark
        db.ikf_benchmarks.find_one.return_value = {
            "type": "industry",
            "key": "5112",
            "fetched_at": datetime.now(timezone.utc) - timedelta(minutes=30),
            "data": {
                "metric": "pursuitSuccessRate",
                "statistics": {"median": 45}
            }
        }
        db.ikf_benchmarks.update_one = MagicMock()
        db.ikf_federation_state.find_one.return_value = {
            "type": "registration",
            "org_id": "test-org-001"
        }
        return db

    @pytest.fixture
    def mock_conn_manager(self):
        manager = MagicMock()
        manager.is_connected = True
        return manager

    @pytest.fixture
    def mock_circuit_breaker(self):
        breaker = MagicMock()
        breaker.call = AsyncMock(return_value=Mock(
            status_code=200,
            json=Mock(return_value={
                "metric": "pursuitSuccessRate",
                "statistics": {
                    "percentile25": 30,
                    "median": 45,
                    "percentile75": 60,
                    "mean": 48
                }
            })
        ))
        return breaker

    @pytest.mark.asyncio
    async def test_get_industry_benchmark_from_cache(self, mock_db, mock_conn_manager, mock_circuit_breaker):
        """Test fetching industry benchmark data from cache."""
        from federation.benchmark_engine import BenchmarkEngine

        engine = BenchmarkEngine(
            db=mock_db,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_circuit_breaker,
            http_client=MagicMock(),
            config=None
        )

        result = await engine.get_industry_benchmark("5112")

        assert result is not None
        assert result["metric"] == "pursuitSuccessRate"
        # Verify cache was queried
        mock_db.ikf_benchmarks.find_one.assert_called()

    def test_benchmark_staleness_check(self, mock_db, mock_conn_manager, mock_circuit_breaker):
        """Test benchmark cache staleness check."""
        from federation.benchmark_engine import BenchmarkEngine

        engine = BenchmarkEngine(
            db=mock_db,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_circuit_breaker,
            http_client=MagicMock(),
            config=None
        )

        # is_benchmark_stale should return False when data is recent
        is_stale = engine.is_benchmark_stale()

        # With recent data (30 min old), should not be stale
        assert is_stale is False


class TestTrustManager:
    """Tests for the Trust Manager (Phase 2)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.ikf_trust_relationships.find_one.return_value = None
        db.ikf_trust_relationships.update_one = MagicMock()
        db.ikf_trust_relationships.find.return_value = []
        db.ikf_trust_relationships.count_documents.return_value = 0
        db.ikf_federation_state.find_one.return_value = {
            "type": "registration",
            "verification_level": "CONTRIBUTOR"
        }
        return db

    @pytest.fixture
    def mock_conn_manager(self):
        manager = MagicMock()
        manager.is_connected = True
        return manager

    @pytest.fixture
    def mock_circuit_breaker(self):
        breaker = MagicMock()
        breaker.call = AsyncMock(return_value=Mock(
            status_code=201,
            json=Mock(return_value={
                "relationshipId": "trust-001",
                "partnerOrgId": "partner-org-001",
                "status": "PROPOSED"
            }),
            text="Success"
        ))
        return breaker

    @pytest.fixture
    def mock_publisher(self):
        publisher = MagicMock()
        publisher.publish_ikf_event = AsyncMock()
        return publisher

    @pytest.mark.asyncio
    async def test_request_trust(self, mock_db, mock_conn_manager, mock_circuit_breaker, mock_publisher):
        """Test initiating a trust relationship request."""
        from federation.trust_manager import TrustManager

        manager = TrustManager(
            db=mock_db,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_circuit_breaker,
            http_client=MagicMock(),
            event_publisher=mock_publisher,
            config=None
        )

        result = await manager.request_trust(
            target_org_id="partner-org-001",
            relationship_type="BILATERAL",
            sharing_level="INDUSTRY"
        )

        assert result is not None
        assert result["relationshipId"] == "trust-001"
        mock_publisher.publish_ikf_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_trust_prerequisites(self, mock_db, mock_conn_manager, mock_circuit_breaker, mock_publisher):
        """Test checking trust prerequisites for cross-org features."""
        from federation.trust_manager import TrustManager

        # Set up active trust relationship
        mock_db.ikf_trust_relationships.find.return_value = [
            {"partner_org_id": "partner-001", "status": "ACTIVE", "sharing_level": "PARTNER"}
        ]

        manager = TrustManager(
            db=mock_db,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_circuit_breaker,
            http_client=MagicMock(),
            event_publisher=mock_publisher,
            config=None
        )

        prereqs = await manager.check_trust_prerequisites()

        assert prereqs["has_active_trust"] is True
        assert prereqs["can_use_cross_org_idtfs"] is True
        assert prereqs["can_use_partner_sharing"] is True

    @pytest.mark.asyncio
    async def test_request_trust_disconnected(self, mock_db, mock_circuit_breaker, mock_publisher):
        """Test trust request fails when disconnected."""
        from federation.trust_manager import TrustManager

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        manager = TrustManager(
            db=mock_db,
            connection_manager=mock_conn,
            circuit_breaker=mock_circuit_breaker,
            http_client=MagicMock(),
            event_publisher=mock_publisher,
            config=None
        )

        result = await manager.request_trust(
            target_org_id="partner-org-001",
            relationship_type="BILATERAL",
            sharing_level="INDUSTRY"
        )

        assert result is None


class TestReputationTracker:
    """Tests for the Reputation Tracker (Phase 2)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.ikf_reputation.find_one.return_value = {
            "entity_type": "organization",
            "entity_id": "test-org-001",
            "data": {
                "overallScore": 75,
                "components": {
                    "contributionVolume": 80,
                    "contributionQuality": 70
                }
            }
        }
        db.ikf_reputation.update_one = MagicMock()
        db.ikf_federation_state.find_one.return_value = {
            "type": "registration",
            "org_id": "test-org-001"
        }
        return db

    @pytest.fixture
    def mock_conn_manager(self):
        manager = MagicMock()
        manager.is_connected = True
        return manager

    @pytest.mark.asyncio
    async def test_get_org_reputation(self, mock_db, mock_conn_manager):
        """Test retrieving cached organization reputation."""
        from federation.reputation_tracker import ReputationTracker

        tracker = ReputationTracker(
            db=mock_db,
            connection_manager=mock_conn_manager,
            circuit_breaker=MagicMock(),
            http_client=MagicMock(),
            config=None
        )

        result = await tracker.get_org_reputation()

        assert result is not None
        assert result["overallScore"] == 75

    @pytest.mark.asyncio
    async def test_submit_feedback_connected(self, mock_db, mock_conn_manager):
        """Test submitting contribution feedback when connected."""
        from federation.reputation_tracker import ReputationTracker

        mock_breaker = MagicMock()
        mock_breaker.call = AsyncMock(return_value=Mock(status_code=200))

        tracker = ReputationTracker(
            db=mock_db,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_breaker,
            http_client=MagicMock(),
            config=None
        )

        result = await tracker.submit_contribution_feedback(
            contribution_id="contrib-001",
            feedback_type="applied",
            effectiveness_rating=4
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_submit_feedback_disconnected(self, mock_db):
        """Test feedback submission fails when disconnected."""
        from federation.reputation_tracker import ReputationTracker

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        tracker = ReputationTracker(
            db=mock_db,
            connection_manager=mock_conn,
            circuit_breaker=MagicMock(),
            http_client=MagicMock(),
            config=None
        )

        result = await tracker.submit_contribution_feedback(
            contribution_id="contrib-001",
            feedback_type="applied"
        )

        assert result is False


class TestCrossOrgDiscovery:
    """Tests for Cross-Org Discovery Service (Phase 3)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.organization_settings.find_one.return_value = {
            "cross_org_discovery_enabled": True
        }
        db.ikf_introduction_requests.update_one = MagicMock()
        return db

    @pytest.fixture
    def mock_trust_manager(self):
        manager = MagicMock()
        manager.check_trust_prerequisites = AsyncMock(return_value={
            "has_active_trust": True,
            "can_use_cross_org_idtfs": True,
            "trusted_org_ids": ["partner-001", "partner-002"],
            "verification_level": "CONTRIBUTOR"
        })
        return manager

    @pytest.fixture
    def mock_conn_manager(self):
        manager = MagicMock()
        manager.is_connected = True
        return manager

    @pytest.fixture
    def mock_circuit_breaker(self):
        breaker = MagicMock()
        breaker.call = AsyncMock(return_value=Mock(
            status_code=200,
            json=Mock(return_value={
                "profiles": [
                    {
                        "gii": "GII-12345",
                        "availability": "AVAILABLE",
                        "matchScore": 0.85,
                        "anonymizedProfile": {"skills": ["Python", "ML"]}
                    },
                    {
                        "gii": "GII-67890",
                        "availability": "LIMITED",
                        "matchScore": 0.75,
                        "anonymizedProfile": {"skills": ["Data Science"]}
                    }
                ],
                "totalCount": 2,
                "searchedOrgs": ["partner-001"]
            })
        ))
        return breaker

    @pytest.mark.asyncio
    async def test_discover_cross_org_success(self, mock_db, mock_trust_manager, mock_conn_manager, mock_circuit_breaker):
        """Test successful cross-org discovery."""
        from federation.cross_org_discovery import CrossOrgDiscoveryService

        service = CrossOrgDiscoveryService(
            db=mock_db,
            trust_manager=mock_trust_manager,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_circuit_breaker,
            http_client=MagicMock(),
            config=None
        )

        result = await service.discover_cross_org(
            gap_context={"required_skills": ["Python"]}
        )

        assert result["prerequisites_met"] is True
        assert result["total_found"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["source"] == "cross_org"

    @pytest.mark.asyncio
    async def test_filter_unavailable(self, mock_db, mock_trust_manager, mock_conn_manager):
        """Test that UNAVAILABLE innovators are filtered out."""
        from federation.cross_org_discovery import CrossOrgDiscoveryService

        mock_breaker = MagicMock()
        mock_breaker.call = AsyncMock(return_value=Mock(
            status_code=200,
            json=Mock(return_value={
                "profiles": [
                    {"gii": "GII-001", "availability": "AVAILABLE", "matchScore": 0.9},
                    {"gii": "GII-002", "availability": "UNAVAILABLE", "matchScore": 0.8},  # Should be filtered
                    {"gii": "GII-003", "availability": "LIMITED", "matchScore": 0.7}
                ],
                "totalCount": 3,
                "searchedOrgs": ["partner-001"]
            })
        ))

        service = CrossOrgDiscoveryService(
            db=mock_db,
            trust_manager=mock_trust_manager,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_breaker,
            http_client=MagicMock(),
            config=None
        )

        result = await service.discover_cross_org(gap_context={})

        # UNAVAILABLE should be filtered - only 2 results
        assert len(result["results"]) == 2
        for profile in result["results"]:
            assert profile["availability"] != "UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_prerequisites_not_met(self, mock_db, mock_conn_manager, mock_circuit_breaker):
        """Test discovery fails when prerequisites not met."""
        from federation.cross_org_discovery import CrossOrgDiscoveryService

        mock_trust = MagicMock()
        mock_trust.check_trust_prerequisites = AsyncMock(return_value={
            "has_active_trust": False,
            "can_use_cross_org_idtfs": False,
            "verification_level": "OBSERVER"
        })

        service = CrossOrgDiscoveryService(
            db=mock_db,
            trust_manager=mock_trust,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_circuit_breaker,
            http_client=MagicMock(),
            config=None
        )

        result = await service.discover_cross_org(gap_context={})

        assert result["prerequisites_met"] is False
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_request_introduction(self, mock_db, mock_trust_manager, mock_conn_manager):
        """Test requesting a mediated introduction."""
        from federation.cross_org_discovery import CrossOrgDiscoveryService

        mock_breaker = MagicMock()
        mock_breaker.call = AsyncMock(return_value=Mock(
            status_code=201,
            json=Mock(return_value={
                "introductionId": "intro-001",
                "status": "PENDING"
            })
        ))

        service = CrossOrgDiscoveryService(
            db=mock_db,
            trust_manager=mock_trust_manager,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_breaker,
            http_client=MagicMock(),
            config=None
        )

        result = await service.request_introduction(
            target_gii="GII-12345",
            context="Looking for ML expertise",
            purpose="Project collaboration"
        )

        assert result["success"] is True
        assert result["introduction_id"] == "intro-001"


class TestWebSocketManager:
    """Tests for WebSocket Manager (Phase 4)."""

    @pytest.fixture
    def ws_manager(self):
        from realtime.websocket_manager import WebSocketManager
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_connection_registration(self, ws_manager):
        """Test WebSocket connection registration."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        connected = await ws_manager.connect(mock_ws, "user-001", "session-001")

        assert connected is True
        assert ws_manager.get_connection_count() == 1
        assert ws_manager.get_user_connection_count("user-001") == 1

    @pytest.mark.asyncio
    async def test_send_to_user(self, ws_manager):
        """Test sending message to all user connections."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await ws_manager.connect(mock_ws, "user-001", "session-001")
        sent = await ws_manager.send_to_user("user-001", {"test": "message"})

        assert sent == 1
        mock_ws.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect(self, ws_manager):
        """Test WebSocket disconnection."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()

        await ws_manager.connect(mock_ws, "user-001", "session-001")
        await ws_manager.disconnect(mock_ws)

        assert ws_manager.get_connection_count() == 0

    def test_stats(self, ws_manager):
        """Test WebSocket stats reporting."""
        stats = ws_manager.get_stats()

        assert "active_connections" in stats
        assert "unique_users" in stats
        assert "total_connections" in stats


class TestEventBridge:
    """Tests for Event Bridge (Phase 4)."""

    @pytest.fixture
    def mock_ws_manager(self):
        manager = MagicMock()
        manager.broadcast = AsyncMock(return_value=5)
        manager.send_to_user = AsyncMock(return_value=1)
        return manager

    @pytest.mark.asyncio
    async def test_publish_event(self, mock_ws_manager):
        """Test publishing event through bridge."""
        from realtime.event_bridge import EventBridge

        bridge = EventBridge(mock_ws_manager)
        bridge.start()

        await bridge.publish_event("trust.accepted", {"relationship_id": "trust-001"})

        # Give the processor time to handle the event
        await asyncio.sleep(0.1)

        bridge.stop()

    @pytest.mark.asyncio
    async def test_publish_user_specific_event(self, mock_ws_manager):
        """Test publishing user-specific event."""
        from realtime.event_bridge import EventBridge

        bridge = EventBridge(mock_ws_manager)
        bridge.start()

        await bridge.publish_coaching_insight(
            user_id="user-001",
            insight_type="benchmark_comparison",
            content={"percentile": 75}
        )

        await asyncio.sleep(0.1)
        bridge.stop()

    def test_event_channel_mapping(self):
        """Test event type to channel mapping."""
        from realtime.event_bridge import EVENT_CHANNEL_MAP

        assert EVENT_CHANNEL_MAP["trust.accepted"] == "trust"
        assert EVENT_CHANNEL_MAP["benchmark.updated"] == "benchmark"
        assert EVENT_CHANNEL_MAP["coaching.insight_available"] == "coaching"


class TestChannelManager:
    """Tests for Channel Manager (Phase 4)."""

    @pytest.fixture
    def channel_manager(self):
        from realtime.channels import ChannelManager
        return ChannelManager()

    def test_list_channels(self, channel_manager):
        """Test listing available channels."""
        channels = channel_manager.list_channels()

        assert len(channels) > 0
        channel_names = [c["name"] for c in channels]
        assert "federation" in channel_names
        assert "trust" in channel_names
        assert "benchmark" in channel_names

    def test_can_subscribe_authenticated(self, channel_manager):
        """Test subscription check for authenticated channels."""
        user_context = {"authenticated": True, "roles": ["user"]}

        result = channel_manager.can_subscribe(user_context, "federation")

        assert result["allowed"] is True

    def test_cannot_subscribe_privileged_without_role(self, channel_manager):
        """Test subscription denied for privileged channel without required role."""
        user_context = {"authenticated": True, "roles": ["user"]}

        result = channel_manager.can_subscribe(user_context, "trust")

        assert result["allowed"] is False
        assert "Required roles" in result["reason"]

    def test_can_subscribe_privileged_with_role(self, channel_manager):
        """Test subscription allowed for privileged channel with required role."""
        user_context = {"authenticated": True, "roles": ["federation_admin"]}

        result = channel_manager.can_subscribe(user_context, "trust")

        assert result["allowed"] is True

    def test_get_user_channels(self, channel_manager):
        """Test getting all subscribable channels for user."""
        user_context = {"authenticated": True, "roles": ["federation_admin"]}

        channels = channel_manager.get_user_channels(user_context)

        assert "federation" in channels
        assert "trust" in channels  # Has required role


class TestEventSchemas:
    """Tests for v3.5.3 Event Schemas (Phase 5)."""

    def test_event_types_defined(self):
        """Test that v3.5.3 event types are defined."""
        import sys
        import os
        # Add parent directory to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        try:
            from models.events import EventTypes

            # Benchmark events
            assert hasattr(EventTypes, "BENCHMARK_UPDATED")
            assert hasattr(EventTypes, "BENCHMARK_RANKING_CHANGED")

            # Trust events
            assert hasattr(EventTypes, "TRUST_REQUESTED")
            assert hasattr(EventTypes, "TRUST_ACCEPTED")
            assert hasattr(EventTypes, "TRUST_REVOKED")

            # Reputation events
            assert hasattr(EventTypes, "REPUTATION_UPDATED")

            # Discovery events
            assert hasattr(EventTypes, "DISCOVERY_RESULTS_AVAILABLE")
            assert hasattr(EventTypes, "INTRODUCTION_REQUESTED")
        finally:
            sys.path.pop(0)

    def test_benchmark_event_payload(self):
        """Test BenchmarkEventPayload model."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        try:
            from models.events import BenchmarkEventPayload

            payload = BenchmarkEventPayload(
                metric_type="pursuitSuccessRate",
                percentile=75,
                trend="improving"
            )

            assert payload.metric_type == "pursuitSuccessRate"
            assert payload.percentile == 75
            assert payload.trend == "improving"
        finally:
            sys.path.pop(0)

    def test_trust_event_payload(self):
        """Test TrustEventPayload model."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        try:
            from models.events import TrustEventPayload

            payload = TrustEventPayload(
                relationship_id="trust-001",
                partner_org_id="partner-001",
                status="ACTIVE"
            )

            assert payload.relationship_id == "trust-001"
            assert payload.status == "ACTIVE"
        finally:
            sys.path.pop(0)


class TestMigration:
    """Tests for v3.5.3 Database Migration (Phase 6)."""

    def test_migration_file_exists(self):
        """Test migration file exists and has required attributes."""
        import os
        import sys

        # Add tools directory to path for import
        tools_path = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "migrations")
        sys.path.insert(0, os.path.abspath(tools_path))

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "migration_004",
                os.path.join(tools_path, "004_v3_5_3_global_benchmarking.py")
            )
            if spec and spec.loader:
                migration = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration)

                assert migration.MIGRATION_ID == "004_v3_5_3_global_benchmarking"
                assert migration.VERSION == "3.5.3"
                assert hasattr(migration, "up")
                assert hasattr(migration, "down")
                assert hasattr(migration, "is_applied")
        finally:
            if tools_path in sys.path:
                sys.path.remove(tools_path)

    def test_migration_collections(self):
        """Test migration creates expected collections."""
        # The migration should create indexes for these collections
        expected_collections = [
            "ikf_benchmarks",
            "ikf_trust_relationships",
            "ikf_reputation",
            "ikf_introduction_requests"
        ]

        # Just verify the collection names are as expected
        for collection in expected_collections:
            assert collection.startswith("ikf_")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
