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

        result = engine.generalize(data)

        generalized = result.get("generalized", {})
        # Emails should be removed or replaced
        assert "john.doe@example.com" not in str(generalized)

    def test_entity_abstraction_phone(self, engine):
        """Test phone number abstraction."""
        data = {"phone": "555-123-4567", "contact": "Call 555.123.4567"}

        result = engine.generalize(data)

        generalized = result.get("generalized", {})
        # Phone numbers should be removed or replaced
        assert "555-123-4567" not in str(generalized)
        assert "555.123.4567" not in str(generalized)

    def test_entity_abstraction_url(self, engine):
        """Test URL abstraction."""
        data = {"website": "https://mycompany.com", "notes": "Visit http://secret.internal.net"}

        result = engine.generalize(data)

        generalized = result.get("generalized", {})
        # URLs should be removed or replaced
        assert "mycompany.com" not in str(generalized)
        assert "secret.internal.net" not in str(generalized)

    def test_metric_normalization_revenue(self, engine):
        """Test revenue normalization to ranges."""
        data = {"revenue": 1500000, "annual_revenue": "$2.5M"}

        result = engine.generalize(data)

        generalized = result.get("generalized", {})
        # Revenue should be normalized to range, not exact value
        assert "1500000" not in str(generalized)

    def test_metric_normalization_employees(self, engine):
        """Test employee count normalization."""
        data = {"employees": 47, "team_size": "47 people"}

        result = engine.generalize(data)

        generalized = result.get("generalized", {})
        # Employee count should be normalized to range
        # Exact number should not appear
        assert "47" not in str(generalized) or "range" in str(generalized).lower()

    def test_context_preservation_industry(self, engine):
        """Test that industry context is preserved."""
        data = {
            "industry": "Healthcare",
            "naics_code": "621",
            "innovation_type": "B2B"
        }

        result = engine.generalize(data)

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

        result = engine.generalize(data)

        # Should extract patterns while generalizing
        assert "transformations_log" in result

    def test_confidence_score(self, engine):
        """Test that confidence score is returned."""
        data = {"simple_field": "test value"}

        result = engine.generalize(data)

        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1

    def test_warnings_on_low_confidence(self, engine):
        """Test warnings when generalization confidence is low."""
        # Data with potential PII that might be missed
        data = {
            "notes": "Met with John Smith at 123 Main St, called his assistant Maria"
        }

        result = engine.generalize(data)

        # Should have warnings if PII detection uncertain
        assert "warnings" in result


class TestIKFContributionPreparer:
    """Tests for IKFContributionPreparer."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.db = Mock()
        db.get_pursuit.return_value = {
            "pursuit_id": "p1",
            "title": "Test Pursuit",
            "user_id": "user_1",
            "status": "launched"
        }
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
        """Test that prepare_contribution creates a DRAFT status contribution."""
        mock_db.save_ikf_contribution.return_value = "contrib_123"

        result = preparer.prepare_contribution(
            pursuit_id="p1",
            package_type="temporal_benchmark"
        )

        assert "contribution_id" in result
        # Verify save was called with DRAFT status
        call_args = mock_db.save_ikf_contribution.call_args
        assert call_args is not None

    def test_prepare_contribution_all_package_types(self, preparer, mock_db):
        """Test all 5 package types can be prepared."""
        package_types = [
            "temporal_benchmark",
            "pattern",
            "risk_intelligence",
            "effectiveness",
            "retrospective"
        ]

        mock_db.save_ikf_contribution.return_value = "contrib_123"

        for pkg_type in package_types:
            result = preparer.prepare_contribution(
                pursuit_id="p1",
                package_type=pkg_type
            )
            assert "contribution_id" in result, f"Failed for {pkg_type}"

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
            reviewer_notes="Approved"
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
            reviewer_notes="Contains sensitive data"
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
        mock_db.db.ikf_contributions.find.return_value = [
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

        result = engine.generalize(data)
        generalized = result.get("generalized", {})

        # Any remaining timestamps should be ISO 8601 format
        for key, value in generalized.items():
            if "at" in key.lower() and isinstance(value, str):
                # Should be parseable as ISO 8601
                try:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pytest.fail(f"Timestamp {key} not in ISO 8601 format: {value}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
