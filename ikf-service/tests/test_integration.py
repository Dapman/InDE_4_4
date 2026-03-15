"""
InDE IKF Service v3.2 - Integration Tests

Tests for:
- Generalization pipeline
- Contribution workflows
- Federation operations
- Event consumer triggers
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGeneralizationPipeline:
    """Tests for the 4-stage generalization pipeline."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock()
        client.post = AsyncMock(return_value=Mock(
            status_code=200,
            json=Mock(return_value={
                "choices": [{"message": {"content": "{}"}}]
            })
        ))
        return client

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        return db

    @pytest.fixture
    def engine(self, mock_llm_client, mock_db):
        """Create GeneralizationEngine instance."""
        from generalization.engine import GeneralizationEngine
        return GeneralizationEngine(llm_client=mock_llm_client, db=mock_db)

    def test_engine_initialization(self, engine):
        """Test engine initializes with all stages."""
        assert engine._entity_detector is not None
        assert engine._normalizer is not None
        assert engine._preserver is not None
        assert engine._extractor is not None
        assert engine._pii_scanner is not None

    @pytest.mark.asyncio
    async def test_generalize_basic(self, engine):
        """Test basic generalization."""
        raw_data = {
            "title": "Test Pursuit",
            "description": "A simple test"
        }
        context = {
            "industry": "Technology",
            "methodology": "LEAN_STARTUP"
        }

        result = await engine.generalize(raw_data, context)

        assert "generalized" in result
        assert "confidence" in result
        assert "pii_scan" in result
        assert "transformations_log" in result

    def test_generalize_sync(self, engine):
        """Test synchronous generalization."""
        raw_data = {"field": "value"}
        context = {"industry": "Healthcare"}

        result = engine.generalize_sync(raw_data, context)

        assert "generalized" in result
        assert "original_hash" in result


class TestEntityDetector:
    """Tests for LLMEntityDetector."""

    @pytest.fixture
    def detector(self):
        """Create entity detector."""
        from generalization.entity_detector import LLMEntityDetector
        return LLMEntityDetector(llm_client=None)

    def test_email_detection(self, detector):
        """Test email detection regex."""
        import re
        text = "Contact john@example.com for details"
        pattern = re.compile(detector.PATTERNS["email"])

        matches = list(pattern.finditer(text))
        assert len(matches) == 1
        assert matches[0].group() == "john@example.com"

    def test_phone_detection(self, detector):
        """Test phone detection regex."""
        import re
        test_cases = [
            "555-123-4567",
            "5551234567",
        ]

        pattern = re.compile(detector.PATTERNS["phone_us"])

        for phone in test_cases:
            matches = list(pattern.finditer(phone))
            assert len(matches) >= 1, f"Failed to detect: {phone}"

    def test_url_detection(self, detector):
        """Test URL detection regex."""
        import re
        text = "Visit https://example.com or http://test.org/path"
        pattern = re.compile(detector.PATTERNS["url"])

        matches = list(pattern.finditer(text))
        assert len(matches) == 2

    def test_money_detection(self, detector):
        """Test money detection regex."""
        import re
        test_cases = ["$100", "$1,000"]
        pattern = re.compile(detector.PATTERNS["money"])

        for money in test_cases:
            matches = list(pattern.finditer(money))
            assert len(matches) >= 1, f"Failed to detect: {money}"


class TestMetricNormalizer:
    """Tests for MetricNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Create metric normalizer."""
        from generalization.metric_normalizer import MetricNormalizer
        return MetricNormalizer()

    def test_revenue_normalization(self, normalizer):
        """Test revenue value normalization."""
        data = {"revenue": 1500000}
        context = {}

        result, log = normalizer.normalize(data, context)

        assert "revenue" in result
        # Should be a range, not exact value
        assert "range" in str(result["revenue"]).lower() or "-" in str(result["revenue"])

    def test_employee_count_normalization(self, normalizer):
        """Test employee count normalization."""
        data = {"employees": 47}
        context = {}

        result, log = normalizer.normalize(data, context)

        assert "employees" in result
        # Should be a range
        assert result["employees"] != 47 or "range" in str(result).lower()

    def test_percentage_preservation(self, normalizer):
        """Test that percentages are preserved."""
        data = {"growth_rate": 0.15}
        context = {}

        result, log = normalizer.normalize(data, context)

        # Percentages should be kept
        assert "growth_rate" in result


class TestPIIScanner:
    """Tests for PIIScanner."""

    @pytest.fixture
    def scanner(self):
        """Create PII scanner."""
        from generalization.pii_scanner import PIIScanner
        return PIIScanner()

    def test_clean_data_passes(self, scanner):
        """Test clean data passes scan."""
        data = {
            "description": "A generic product description",
            "category": "Technology"
        }

        result = scanner.scan(data)

        assert result["passed"] is True
        assert len(result["high_confidence_flags"]) == 0

    def test_email_detection(self, scanner):
        """Test email is flagged."""
        data = {"contact": "john@example.com"}

        result = scanner.scan(data)

        assert result["passed"] is False or len(result["high_confidence_flags"]) > 0

    def test_ssn_detection(self, scanner):
        """Test SSN pattern is flagged."""
        data = {"notes": "SSN: 123-45-6789"}

        result = scanner.scan(data)

        # SSN should be high confidence flag
        assert len(result["high_confidence_flags"]) > 0


class TestContributionPreparer:
    """Tests for IKFContributionPreparer."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.pursuit_cache = Mock()
        db.ikf_contributions = Mock()
        db.users = Mock()
        return db

    @pytest.fixture
    def mock_publisher(self):
        """Create mock event publisher."""
        publisher = AsyncMock()
        publisher.publish_ikf_event = AsyncMock()
        return publisher

    @pytest.fixture
    def preparer(self, mock_db, mock_publisher):
        """Create preparer instance."""
        from contribution.preparer import IKFContributionPreparer
        return IKFContributionPreparer(mock_db, mock_publisher)

    def test_package_types_defined(self, preparer):
        """Test all package types are defined."""
        from contribution.preparer import PACKAGE_TYPES

        expected = [
            "temporal_benchmark",
            "pattern_contribution",
            "risk_intelligence",
            "effectiveness_metrics",
            "retrospective_wisdom"
        ]

        for pkg_type in expected:
            assert pkg_type in PACKAGE_TYPES

    def test_summary_generation(self, preparer):
        """Test summary generation."""
        data = {
            "title": "Test Pursuit Title",
            "current_phase": "VALIDATION",
            "fears": ["fear1", "fear2", "fear3"]
        }

        summary = preparer._generate_summary(data)

        assert "Test Pursuit" in summary
        assert "VALIDATION" in summary
        assert "3" in summary  # 3 fears


class TestRateLimiter:
    """Tests for ContributionRateLimiter."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.users = Mock()
        db.ikf_contributions = Mock()
        return db

    @pytest.fixture
    def limiter(self, mock_db):
        """Create rate limiter instance."""
        from contribution.rate_limiter import ContributionRateLimiter
        return ContributionRateLimiter(mock_db)

    def test_user_disabled_contributions(self, limiter, mock_db):
        """Test user with NONE sharing level."""
        mock_db.users.find_one.return_value = {
            "_id": "user1",
            "ikf_preferences": {"sharing_level": "NONE"}
        }
        mock_db.ikf_contributions.count_documents.return_value = 0

        allowed, reason = limiter.can_auto_prepare("user1", "pattern_contribution")

        assert allowed is False
        assert "disabled" in reason.lower()

    def test_max_pending_reached(self, limiter, mock_db):
        """Test max pending limit."""
        mock_db.users.find_one.return_value = {
            "_id": "user1",
            "ikf_preferences": {"sharing_level": "MODERATE"}
        }
        mock_db.ikf_contributions.count_documents.return_value = 5  # Over limit

        allowed, reason = limiter.can_auto_prepare("user1", "pattern_contribution")

        assert allowed is False
        assert "max" in reason.lower()

    def test_high_priority_bypasses_cooldown(self, limiter, mock_db):
        """Test high priority triggers bypass cooldown."""
        mock_db.users.find_one.return_value = {
            "_id": "user1",
            "ikf_preferences": {"sharing_level": "MODERATE"}
        }
        mock_db.ikf_contributions.count_documents.return_value = 0
        mock_db.ikf_contributions.find_one.return_value = {
            "created_at": datetime.now(timezone.utc) - timedelta(hours=1)  # Recent
        }

        # Normal priority should be blocked
        allowed, _ = limiter.can_auto_prepare("user1", "pattern_contribution", "normal")
        assert allowed is False

        # High priority should pass
        allowed, _ = limiter.can_auto_prepare("user1", "pattern_contribution", "high")
        assert allowed is True


class TestFederationLocalNode:
    """Tests for LocalFederationNode."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.ikf_node_config = Mock()
        db.ikf_contributions = Mock()
        db.ikf_node_config.find_one.return_value = None
        db.ikf_node_config.insert_one.return_value = Mock()
        return db

    @pytest.fixture
    def node(self, mock_db):
        """Create federation node."""
        from federation.local_node import LocalFederationNode
        return LocalFederationNode(mock_db)

    def test_node_id_generation(self, node):
        """Test node ID is generated."""
        assert node.node_id is not None
        assert node.node_id.startswith("node-")

    def test_capabilities(self, node):
        """Test capability advertisement."""
        caps = node._get_capabilities()

        assert "package_types" in caps
        assert "methodologies" in caps
        assert "supports_query" in caps
        assert "supports_contribute" in caps

    def test_status(self, node):
        """Test status reporting."""
        status = node.get_status()

        assert "node_id" in status
        assert "mode" in status
        assert "capabilities" in status


class TestFederationQueryClient:
    """Tests for FederationQueryClient."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.ikf_contributions = Mock()
        db.ikf_query_cache = Mock()
        return db

    @pytest.fixture
    def mock_node(self):
        """Create mock federation node."""
        node = Mock()
        node.is_connected = False
        node._http_client = None
        return node

    @pytest.fixture
    def client(self, mock_db, mock_node):
        """Create query client."""
        from federation.query_client import FederationQueryClient
        return FederationQueryClient(mock_db, mock_node)

    def test_cache_key_generation(self, client):
        """Test cache key generation."""
        key1 = client._build_cache_key("patterns", {"phase": "A"})
        key2 = client._build_cache_key("patterns", {"phase": "B"})
        key3 = client._build_cache_key("patterns", {"phase": "A"})

        assert key1 != key2
        assert key1 == key3

    @pytest.mark.asyncio
    async def test_local_pattern_search(self, client, mock_db):
        """Test local pattern search when offline."""
        mock_db.ikf_contributions.find.return_value.sort.return_value.limit.return_value = []

        result = await client._search_local_patterns(
            {"methodology": "LEAN_STARTUP"},
            "pattern_contribution",
            10
        )

        assert "patterns" in result
        assert result["source"] == "local"


class TestEventConsumer:
    """Tests for IKFEventConsumer."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        return Mock()

    @pytest.fixture
    def mock_publisher(self):
        """Create mock publisher."""
        return AsyncMock()

    @pytest.fixture
    def consumer(self, mock_db, mock_publisher):
        """Create event consumer."""
        from events.consumer import IKFEventConsumer
        return IKFEventConsumer(mock_db, mock_publisher)

    def test_handler_registration(self, consumer):
        """Test event handlers are registered."""
        # Should have handlers for key events
        assert "pursuit.completed" in consumer._handlers
        assert "pursuit.terminated" in consumer._handlers
        assert "retrospective.completed" in consumer._handlers

    def test_stream_derivation(self, consumer):
        """Test stream names are derived from handlers."""
        streams = consumer._get_streams()

        # Should have pursuit stream
        assert any("pursuit" in s for s in streams)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
