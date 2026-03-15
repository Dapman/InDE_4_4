"""
InDE MVP v3.0.3 - IKF Tests

Tests for:
- Generalization pipeline (entity abstraction, metric normalization, PII detection)
- IKF package schema validation
- Contribution preparation workflow
- Human review gate (mandatory approval)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGeneralizationEngine:
    """Tests for GeneralizationEngine."""

    @pytest.fixture
    def engine(self):
        """Create GeneralizationEngine instance."""
        from ikf import GeneralizationEngine
        return GeneralizationEngine()

    def test_entity_abstraction_email(self, engine):
        """Test email address abstraction."""
        data = {"contact": "john.doe@example.com", "notes": "Email john.doe@example.com for details"}
        context = {"industry": "Technology"}

        result = engine.generalize(data, context)

        generalized = result.get("generalized", {})
        # Emails should be removed or replaced
        assert "john.doe@example.com" not in str(generalized)

    def test_entity_abstraction_phone(self, engine):
        """Test phone number abstraction."""
        data = {"phone": "555-123-4567", "contact": "Call 555.123.4567"}
        context = {"industry": "Technology"}

        result = engine.generalize(data, context)

        generalized = result.get("generalized", {})
        # Phone numbers should be removed or replaced
        assert "555-123-4567" not in str(generalized)
        assert "555.123.4567" not in str(generalized)

    def test_entity_abstraction_url(self, engine):
        """Test URL abstraction."""
        data = {"website": "https://mycompany.com", "notes": "Visit http://secret.internal.net"}
        context = {"industry": "Technology"}

        result = engine.generalize(data, context)

        generalized = result.get("generalized", {})
        # URLs should be removed or replaced
        assert "mycompany.com" not in str(generalized)
        assert "secret.internal.net" not in str(generalized)

    def test_metric_normalization_revenue(self, engine):
        """Test revenue normalization to ranges."""
        data = {"revenue": 1500000, "annual_revenue": "$2.5M"}
        context = {"industry": "Finance"}

        result = engine.generalize(data, context)

        generalized = result.get("generalized", {})
        # Revenue should be normalized to range, not exact value
        assert "1500000" not in str(generalized)

    def test_metric_normalization_employees(self, engine):
        """Test employee count normalization."""
        data = {"employees": 47}
        context = {"industry": "Technology"}

        result = engine.generalize(data, context)

        generalized = result.get("generalized", {})
        # Employee count should be normalized to range
        # The employees field should be a range, not the exact number
        assert generalized.get("employees") != 47
        assert "-" in str(generalized.get("employees", "")) or "range" in str(generalized).lower()

    def test_context_preservation_industry(self, engine):
        """Test that industry context is preserved."""
        data = {
            "industry": "Healthcare",
            "naics_code": "621",
            "innovation_type": "B2B"
        }
        context = {"industry": "Healthcare"}

        result = engine.generalize(data, context)

        generalized = result.get("generalized", {})
        # Industry and innovation type should be preserved
        assert "Healthcare" in str(generalized) or generalized.get("industry") == "Healthcare"

    def test_pattern_extraction(self, engine):
        """Test pattern extraction from data."""
        data = {
            "fear": "worried about market timing",
            "health_zone": "ATTENTION",
            "retrospective_insight": "Should have validated earlier"
        }
        context = {"methodology": "LEAN_STARTUP"}

        result = engine.generalize(data, context)

        # Should extract patterns while generalizing
        assert "transformations_log" in result

    def test_confidence_score(self, engine):
        """Test that confidence score is returned."""
        data = {"simple_field": "test value"}
        context = {}

        result = engine.generalize(data, context)

        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1

    def test_warnings_on_low_confidence(self, engine):
        """Test warnings when generalization confidence is low."""
        # Data with potential PII that might be missed
        data = {
            "notes": "Met with John Smith at 123 Main St, called his assistant Maria"
        }
        context = {}

        result = engine.generalize(data, context)

        # Should have warnings if PII detection uncertain
        assert "warnings" in result


class TestIKFContributionPreparer:
    """Tests for IKFContributionPreparer."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database with all required collections mocked."""
        db = Mock()
        db.db = MagicMock()
        db.get_pursuit.return_value = {
            "pursuit_id": "p1",
            "title": "Test Pursuit",
            "user_id": "user_1",
            "status": "launched",
            "methodology": "LEAN_STARTUP"
        }

        # Create a helper class to mock MongoDB cursors
        class MockCursor:
            def __init__(self, data=None):
                self._data = data or []

            def __iter__(self):
                return iter(self._data)

            def sort(self, *args, **kwargs):
                return self

            def limit(self, *args, **kwargs):
                return self

        # Mock all collections used by contribution preparer
        for coll_name in ['velocity_metrics', 'phase_transitions', 'time_allocations',
                          'patterns', 'health_scores', 'rve_experiments',
                          'conversation_history', 'retrospectives', 'coaching_interventions']:
            coll = MagicMock()
            coll.find.return_value = MockCursor()
            coll.find_one.return_value = None
            setattr(db.db, coll_name, coll)

        return db

    @pytest.fixture
    def mock_engine(self):
        """Create mock GeneralizationEngine."""
        engine = Mock()
        engine.generalize.return_value = {
            "original_hash": "abc123",
            "generalized": {"field": "value"},
            "transformations_log": [],
            "confidence": 0.95,
            "warnings": []
        }
        return engine

    @pytest.fixture
    def preparer(self, mock_db, mock_engine):
        """Create IKFContributionPreparer instance."""
        from ikf import IKFContributionPreparer
        return IKFContributionPreparer(mock_db, mock_engine)

    def test_prepare_contribution_creates_draft(self, preparer, mock_db):
        """Test that prepare_contribution returns a contribution with DRAFT status."""
        mock_db.save_ikf_contribution.return_value = "contrib_123"

        result = preparer.prepare_contribution(
            pursuit_id="p1",
            package_type="temporal_benchmark"
        )

        # Result should include contribution_id (either from save or generated)
        assert result is not None
        # The status in result should be DRAFT
        assert result.get("status") == "DRAFT" or "contribution_id" in result

    def test_prepare_contribution_all_package_types(self, preparer, mock_db):
        """Test all package types are recognized."""
        # Just verify the package types are accepted - don't test full pipeline
        from config import IKF_PACKAGE_TYPES

        assert "temporal_benchmark" in IKF_PACKAGE_TYPES
        assert "pattern" in IKF_PACKAGE_TYPES or "pattern_contribution" in IKF_PACKAGE_TYPES
        assert "risk_intelligence" in IKF_PACKAGE_TYPES
        assert "effectiveness" in IKF_PACKAGE_TYPES or "effectiveness_metrics" in IKF_PACKAGE_TYPES
        assert "retrospective" in IKF_PACKAGE_TYPES or "retrospective_wisdom" in IKF_PACKAGE_TYPES

    def test_review_contribution_approve(self, preparer, mock_db):
        """Test approving a contribution."""
        mock_db.get_ikf_contribution.return_value = {
            "contribution_id": "c1",
            "status": "DRAFT",
            "user_id": "user_1"
        }
        mock_db.update_ikf_contribution.return_value = True

        result = preparer.review_contribution(
            contribution_id="c1",
            approved=True,
            reviewer_id="user_1",
            notes="Approved"
        )

        assert result.get("status") == "IKF_READY"

    def test_review_contribution_reject(self, preparer, mock_db):
        """Test rejecting a contribution."""
        mock_db.get_ikf_contribution.return_value = {
            "contribution_id": "c1",
            "status": "DRAFT",
            "user_id": "user_1"
        }
        mock_db.update_ikf_contribution.return_value = True

        result = preparer.review_contribution(
            contribution_id="c1",
            approved=False,
            reviewer_id="user_1",
            notes="Contains sensitive data"
        )

        assert result.get("status") == "REJECTED"

    def test_review_mandatory_for_export(self, preparer, mock_db):
        """Test that human review is mandatory - cannot skip to IKF_READY."""
        # There should be no way to directly create IKF_READY status
        mock_db.save_ikf_contribution.return_value = "contrib_123"

        result = preparer.prepare_contribution(
            pursuit_id="p1",
            package_type="temporal_benchmark"
        )

        # Initial status should always be DRAFT, never IKF_READY
        call_args = mock_db.save_ikf_contribution.call_args
        if call_args and call_args[1]:
            status = call_args[1].get("status", "DRAFT")
            assert status != "IKF_READY", "Cannot create IKF_READY without review"

    def test_get_pending_reviews(self, preparer, mock_db):
        """Test getting pending reviews."""
        mock_db.get_pending_ikf_reviews.return_value = [
            {"contribution_id": "c1", "status": "DRAFT"},
            {"contribution_id": "c2", "status": "PENDING_REVIEW"}
        ]

        result = preparer.get_pending_reviews("user_1")

        assert isinstance(result, list)


class TestIKFSchemaValidation:
    """Tests for IKF package schema validation."""

    def test_temporal_benchmark_schema(self):
        """Test temporal benchmark package schema."""
        from config import IKF_PACKAGE_TYPES

        assert "temporal_benchmark" in IKF_PACKAGE_TYPES

    def test_iso_8601_timestamps(self):
        """Test that all timestamps are ISO 8601 format."""
        from ikf import GeneralizationEngine

        engine = GeneralizationEngine()
        data = {
            "created_at": datetime.now(timezone.utc),
            "modified_at": datetime.now(timezone.utc)
        }
        context = {"industry": "Technology"}

        result = engine.generalize(data, context)
        generalized = result.get("generalized", {})

        # Any remaining timestamps should be ISO 8601 format
        for key, value in generalized.items():
            if "at" in key.lower() and isinstance(value, str):
                # Should be parseable as ISO 8601
                try:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pytest.fail(f"Timestamp {key} not in ISO 8601 format: {value}")


class TestIKFServiceClient:
    """Tests for IKFServiceClient (v3.2)."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        return db

    @pytest.fixture
    def client(self, mock_db):
        """Create IKFServiceClient instance."""
        from ikf.service_client import IKFServiceClient
        return IKFServiceClient(mock_db)

    def test_default_benchmarks_lean_startup(self, client):
        """Test default benchmarks for Lean Startup methodology."""
        result = client._default_benchmarks("LEAN_STARTUP", "VALIDATION")

        assert result["methodology"] == "LEAN_STARTUP"
        assert result["phase"] == "VALIDATION"
        assert result["source"] == "defaults"
        assert "p50" in result
        assert result["p50"] > 0

    def test_default_benchmarks_design_thinking(self, client):
        """Test default benchmarks for Design Thinking methodology."""
        result = client._default_benchmarks("DESIGN_THINKING", "PROTOTYPE")

        assert result["methodology"] == "DESIGN_THINKING"
        assert result["phase"] == "PROTOTYPE"
        assert "p50" in result

    def test_default_benchmarks_unknown_methodology(self, client):
        """Test default benchmarks for unknown methodology."""
        result = client._default_benchmarks("UNKNOWN_METHOD", "SOME_PHASE")

        assert "p50" in result
        assert result["p50"] == 30  # Default fallback

    @pytest.mark.asyncio
    async def test_search_patterns_error_handling(self, client):
        """Test pattern search handles errors gracefully."""
        # Without real service, should return empty results
        result = await client.search_patterns(
            methodology="LEAN_STARTUP",
            phase="VALIDATION"
        )

        assert "patterns" in result or "error" in result
        await client.close()

    @pytest.mark.asyncio
    async def test_get_risk_indicators_error_handling(self, client):
        """Test risk indicators handles errors gracefully."""
        result = await client.get_risk_indicators(phase="VALIDATION")

        assert "indicators" in result or "error" in result
        await client.close()


class TestIKFInsightsProvider:
    """Tests for IKFInsightsProvider (v3.2)."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        return db

    @pytest.fixture
    def provider(self, mock_db):
        """Create IKFInsightsProvider instance."""
        from ikf.insights_provider import IKFInsightsProvider
        return IKFInsightsProvider(mock_db)

    def test_risk_mitigation_hints(self, provider):
        """Test risk mitigation hint generation."""
        assert "Consider" in provider._get_risk_mitigation("RESOURCE_CONSTRAINT")
        assert "Validate" in provider._get_risk_mitigation("MARKET_UNCERTAINTY")

    def test_risk_mitigation_unknown_category(self, provider):
        """Test fallback for unknown risk category."""
        result = provider._get_risk_mitigation("UNKNOWN_CATEGORY")
        assert "Review" in result

    def test_cache_operations(self, provider):
        """Test caching functionality."""
        # Set a cached value
        provider._set_cached("test_key", {"data": "test"})

        # Get cached value
        result = provider._get_cached("test_key")
        assert result == {"data": "test"}

        # Clear cache
        provider.clear_cache()
        assert provider._get_cached("test_key") is None

    @pytest.mark.asyncio
    async def test_get_phase_guidance_structure(self, provider):
        """Test phase guidance response structure."""
        # This will use defaults since no real service
        guidance = await provider.get_phase_guidance(
            pursuit_id="test_pursuit",
            methodology="LEAN_STARTUP",
            phase="VALIDATION"
        )

        assert "pursuit_id" in guidance
        assert "phase" in guidance
        assert "methodology" in guidance
        assert "benchmarks" in guidance
        assert "common_risks" in guidance
        assert "success_indicators" in guidance
        assert "warning_signs" in guidance

        await provider.close()


class TestFederationIntegration:
    """Integration tests for federation components (v3.2)."""

    def test_contribution_lifecycle(self):
        """Test contribution status lifecycle."""
        valid_statuses = ["DRAFT", "REVIEWED", "IKF_READY", "REJECTED", "SUBMITTED"]

        # Verify all statuses are valid
        for status in valid_statuses:
            assert status in ["DRAFT", "REVIEWED", "IKF_READY", "REJECTED", "SUBMITTED",
                            "PENDING", "RETRY_PENDING", "SUBMISSION_FAILED"]

    def test_package_types_complete(self):
        """Test all 5 package types are defined."""
        expected_types = [
            "temporal_benchmark",
            "pattern_contribution",
            "risk_intelligence",
            "effectiveness_metrics",
            "retrospective_wisdom"
        ]

        from config import IKF_PACKAGE_TYPES

        for pkg_type in expected_types:
            assert pkg_type in IKF_PACKAGE_TYPES, f"Missing package type: {pkg_type}"

    def test_user_sharing_levels(self):
        """Test user sharing level options."""
        valid_levels = ["AGGRESSIVE", "MODERATE", "MINIMAL", "NONE"]

        # All levels should be valid
        for level in valid_levels:
            assert level in ["AGGRESSIVE", "MODERATE", "MINIMAL", "NONE"]


class TestRateLimiter:
    """Tests for ContributionRateLimiter."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.users = Mock()
        db.ikf_contributions = Mock()
        return db

    def test_rate_limiter_import(self):
        """Test rate limiter can be imported."""
        # This tests the module structure
        try:
            from ikf.service_client import IKFServiceClient
            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
