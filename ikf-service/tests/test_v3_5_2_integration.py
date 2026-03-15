"""
InDE IKF Service v3.5.2 Integration Tests

Tests the bidirectional pattern exchange components:
- Contribution Outbox
- Pattern Importer
- Pattern Sync
- Publication Boundary
- Cross-Pollination Detection
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestContributionOutbox:
    """Tests for the Contribution Outbox (Phase 1)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.ikf_contribution_outbox.update_one = MagicMock()
        db.ikf_contribution_outbox.find_one = MagicMock(return_value=None)
        db.ikf_contribution_outbox.find.return_value.sort.return_value.limit.return_value = []
        db.ikf_contributions.find_one = MagicMock(return_value={
            "contribution_id": "test-contrib-001",
            "package_type": "pattern_contribution",
            "status": "IKF_READY",
            "generalized_data": {"test": "data"},
            "generalization_level": 2
        })
        db.ikf_contributions.update_one = MagicMock()
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
            json=Mock(return_value={"receipt_id": "test-receipt-001", "status": "ACCEPTED"})
        ))
        return breaker

    @pytest.fixture
    def mock_publisher(self):
        publisher = MagicMock()
        publisher.publish_ikf_event = AsyncMock()
        return publisher

    @pytest.mark.asyncio
    async def test_outbox_enqueue(self, mock_db, mock_conn_manager, mock_circuit_breaker, mock_publisher):
        """Test enqueueing a contribution for federation submission."""
        from contribution.outbox import ContributionOutbox

        outbox = ContributionOutbox(
            db=mock_db,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_circuit_breaker,
            event_publisher=mock_publisher,
            http_client=MagicMock(),
            config=None
        )

        await outbox.enqueue("test-contrib-001")

        mock_db.ikf_contribution_outbox.update_one.assert_called_once()
        call_args = mock_db.ikf_contribution_outbox.update_one.call_args
        assert call_args[0][0] == {"contribution_id": "test-contrib-001"}

    def test_outbox_queue_status(self, mock_db, mock_conn_manager, mock_circuit_breaker, mock_publisher):
        """Test outbox queue status reporting."""
        from contribution.outbox import ContributionOutbox

        mock_db.ikf_contribution_outbox.count_documents.side_effect = [5, 2, 10, 1]

        outbox = ContributionOutbox(
            db=mock_db,
            connection_manager=mock_conn_manager,
            circuit_breaker=mock_circuit_breaker,
            event_publisher=mock_publisher,
            http_client=MagicMock(),
            config=None
        )

        status = outbox.get_queue_status()

        assert status["pending"] == 5
        assert status["retry"] == 2
        assert status["delivered"] == 10
        assert status["failed"] == 1


class TestPatternImporter:
    """Tests for the Pattern Importer (Phase 2)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.ikf_federation_patterns.count_documents.return_value = 0
        db.ikf_federation_patterns.find_one.return_value = None
        db.ikf_federation_patterns.insert_one = MagicMock()
        db.ikf_federation_patterns.update_one = MagicMock()
        db.ikf_pattern_rejections.insert_one = MagicMock()
        return db

    @pytest.fixture
    def mock_publisher(self):
        publisher = MagicMock()
        publisher.publish_ikf_event = AsyncMock()
        return publisher

    @pytest.mark.asyncio
    async def test_import_valid_pattern(self, mock_db, mock_publisher):
        """Test importing a valid pattern."""
        from federation.pattern_importer import PatternImporter

        importer = PatternImporter(mock_db, None, mock_publisher)

        patterns = [{
            "pattern_id": "test-pattern-001",
            "type": "success_pattern",
            "content": {"summary": "Test pattern content"},
            "confidence": 0.8
        }]

        result = await importer.import_patterns(patterns, "IKF_PULL")

        assert result["accepted"] == 1
        assert result["rejected"] == 0
        mock_db.ikf_federation_patterns.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_invalid_pattern_type(self, mock_db, mock_publisher):
        """Test rejecting patterns with invalid type."""
        from federation.pattern_importer import PatternImporter

        importer = PatternImporter(mock_db, None, mock_publisher)

        patterns = [{
            "pattern_id": "test-pattern-001",
            "type": "invalid_type",
            "content": {"summary": "Test"},
            "confidence": 0.8
        }]

        result = await importer.import_patterns(patterns, "IKF_PULL")

        assert result["rejected"] == 1
        mock_db.ikf_pattern_rejections.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_deduplicate_pattern(self, mock_db, mock_publisher):
        """Test deduplicating patterns by content hash."""
        from federation.pattern_importer import PatternImporter

        # Simulate existing pattern with same hash
        mock_db.ikf_federation_patterns.find_one.return_value = {
            "pattern_id": "existing-001",
            "version": 1
        }

        importer = PatternImporter(mock_db, None, mock_publisher)

        patterns = [{
            "pattern_id": "test-pattern-001",
            "type": "success_pattern",
            "content": {"summary": "Test pattern content"},
            "confidence": 0.8,
            "version": 1
        }]

        result = await importer.import_patterns(patterns, "IKF_PULL")

        assert result["deduplicated"] == 1
        assert result["accepted"] == 0


class TestPublicationBoundary:
    """Tests for the Publication Boundary (Phase 5)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.pursuits.find_one.return_value = {"storage_election": "ORG"}
        db.users.find_one.return_value = {
            "federation_availability": "AVAILABLE",
            "default_storage_election": "ORG"  # Required for valid contribution
        }
        db.audit_events.insert_one = MagicMock()
        return db

    def test_pass_valid_contribution(self, mock_db):
        """Test passing a valid contribution through boundary."""
        from contribution.publication_boundary import PublicationBoundary

        boundary = PublicationBoundary(mock_db)

        contribution = {
            "contribution_id": "test-contrib-001",
            "pursuit_id": "pursuit-001",
            "generalized_content": {"summary": "Test content"},
            "generalization_level": 2,
            "pii_scan": {"passed": True, "high_confidence_flags": []}
        }

        result = boundary.enforce(contribution, "user-001")

        assert result["passed"] is True
        assert result["violations"] == []

    def test_block_personal_storage(self, mock_db):
        """Test blocking PERSONAL storage contributions."""
        from contribution.publication_boundary import PublicationBoundary, PublicationBoundaryError

        mock_db.pursuits.find_one.return_value = {"storage_election": "PERSONAL"}

        boundary = PublicationBoundary(mock_db)

        contribution = {
            "contribution_id": "test-contrib-001",
            "pursuit_id": "pursuit-001",
            "generalized_content": {"summary": "Test"},
            "generalization_level": 2
        }

        with pytest.raises(PublicationBoundaryError) as exc_info:
            boundary.enforce(contribution, "user-001")

        assert "STORAGE_ELECTION" in str(exc_info.value)

    def test_block_pii_detected(self, mock_db):
        """Test blocking contributions with detected PII."""
        from contribution.publication_boundary import PublicationBoundary, PublicationBoundaryError

        boundary = PublicationBoundary(mock_db)

        contribution = {
            "contribution_id": "test-contrib-001",
            "pursuit_id": "pursuit-001",
            "generalized_content": {"summary": "Test"},
            "generalization_level": 2,
            "pii_scan": {
                "passed": False,
                "high_confidence_flags": ["SSN detected", "Email detected"]
            }
        }

        with pytest.raises(PublicationBoundaryError) as exc_info:
            boundary.enforce(contribution, "user-001")

        assert "PII_REMAINING" in str(exc_info.value)


class TestCrossPollinationDetector:
    """Tests for Cross-Pollination Detection (Phase 7)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.ikf_federation_patterns.find_one.return_value = {
            "pattern_id": "finance-pattern-001",
            "applicability": {"industries": ["FINANCE", "BANKING"]}
        }
        db.pursuits.find_one.return_value = {
            "pursuit_id": "pursuit-001",
            "industry_code": "HEALTHCARE"  # Different from pattern
        }
        db.ikf_cross_pollination_events.insert_one = MagicMock()
        db.ikf_cross_pollination_events.find.return_value = []
        return db

    @pytest.fixture
    def mock_publisher(self):
        publisher = MagicMock()
        publisher.publish_ikf_event = AsyncMock()
        return publisher

    @pytest.mark.asyncio
    async def test_detect_cross_pollination(self, mock_db, mock_publisher):
        """Test detecting cross-domain pattern application."""
        from federation.cross_pollination import CrossPollinationDetector

        detector = CrossPollinationDetector(mock_db, mock_publisher, None)

        result = await detector.on_pattern_applied(
            pattern_id="finance-pattern-001",
            pursuit_id="pursuit-001",
            user_id="user-001"
        )

        assert result is not None
        assert result["type"] == "cross_pollination"
        assert result["target_industry"] == "HEALTHCARE"
        assert "FINANCE" in result["pattern_source_industries"]
        mock_db.ikf_cross_pollination_events.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_detection_same_industry(self, mock_db, mock_publisher):
        """Test no detection when pattern matches pursuit industry."""
        from federation.cross_pollination import CrossPollinationDetector

        # Pattern applies to same industry
        mock_db.ikf_federation_patterns.find_one.return_value = {
            "pattern_id": "health-pattern-001",
            "applicability": {"industries": ["HEALTHCARE"]}
        }

        detector = CrossPollinationDetector(mock_db, mock_publisher, None)

        result = await detector.on_pattern_applied(
            pattern_id="health-pattern-001",
            pursuit_id="pursuit-001",
            user_id="user-001"
        )

        assert result is None
        mock_db.ikf_cross_pollination_events.insert_one.assert_not_called()


class TestPatternSync:
    """Tests for Pattern Sync Service (Phase 4)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.ikf_federation_state.find_one.return_value = {"type": "sync", "last_sync_timestamp": None}
        db.ikf_federation_state.update_one = MagicMock()
        return db

    @pytest.fixture
    def mock_conn_manager(self):
        manager = MagicMock()
        manager.is_connected = True
        return manager

    def test_sync_status(self, mock_db, mock_conn_manager):
        """Test sync status reporting."""
        from federation.pattern_sync import PatternSyncService

        sync = PatternSyncService(
            db=mock_db,
            connection_manager=mock_conn_manager,
            circuit_breaker=MagicMock(),
            pattern_importer=MagicMock(),
            http_client=MagicMock(),
            config=None,
            event_publisher=MagicMock()
        )

        status = sync.get_sync_status()

        assert "last_sync" in status
        assert "sync_running" in status
        assert status["connected"] is True

    @pytest.mark.asyncio
    async def test_sync_skipped_when_disconnected(self, mock_db):
        """Test sync is skipped when not connected."""
        from federation.pattern_sync import PatternSyncService

        mock_conn = MagicMock()
        mock_conn.is_connected = False

        sync = PatternSyncService(
            db=mock_db,
            connection_manager=mock_conn,
            circuit_breaker=MagicMock(),
            pattern_importer=MagicMock(),
            http_client=MagicMock(),
            config=None,
            event_publisher=MagicMock()
        )

        result = await sync.sync_now()

        assert result["status"] == "SKIPPED"
        assert result["reason"] == "Not connected"


class TestIKFPatternContext:
    """Tests for ODICM Integration (Phase 6)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.ikf_federation_patterns.count_documents.return_value = 5
        db.ikf_federation_patterns.find.return_value.sort.return_value.limit.return_value = [
            {
                "pattern_id": "test-001",
                "type": "success_pattern",
                "title": "Test Pattern",
                "content": {"summary": "Test summary"},
                "confidence": 0.85
            }
        ]
        return db

    def test_build_coaching_context(self, mock_db):
        """Test building IKF pattern coaching context."""
        from scaffolding.ikf_pattern_context import build_ikf_coaching_context

        pursuit_context = {
            "industry_code": "TECHNOLOGY",
            "methodology": "LEAN_STARTUP"
        }

        result = build_ikf_coaching_context(mock_db, pursuit_context)

        assert result is not None
        assert result["has_ikf_patterns"] is True
        assert result["pattern_count"] == 1

    def test_format_pattern_attribution(self, mock_db):
        """Test pattern formatting includes attribution."""
        from scaffolding.ikf_pattern_context import format_ikf_pattern_for_coaching

        pattern = {
            "type": "success_pattern",
            "title": "Test Pattern",
            "content": {"summary": "Test summary", "key_takeaways": ["Insight 1"]},
            "confidence": 0.85
        }

        result = format_ikf_pattern_for_coaching(pattern)

        assert "Innovators across the InDEVerse" in result
        assert "85%" in result
        assert "Test Pattern" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
