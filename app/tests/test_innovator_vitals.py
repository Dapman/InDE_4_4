"""
InDE MVP v4.4.1 - Innovation Vitals Tests

Tests for the InnovatorVitalsService status classification logic
and response envelope structure.

2026 Yul Williams | InDEVerse, Incorporated
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from modules.diagnostics.innovator_vitals import (
    InnovatorVitalsService,
    InnovatorVitalsRecord,
    InnovatorVitalsResponse,
    InnovatorVitalsSummary,
    NEW_USER_WINDOW_HOURS,
    AT_RISK_DAYS,
    DORMANT_DAYS,
    ENGAGED_MIN_COACHING_SESSIONS,
    ENGAGED_MIN_ARTIFACTS,
)


class TestStatusClassification:
    """Tests for engagement status classification logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.now = datetime.now(timezone.utc)

        # Create a mock service for testing _compute_status
        mock_db = MagicMock()
        mock_db.db = MagicMock()
        self.service = InnovatorVitalsService(mock_db)

    def test_status_new_user(self):
        """NEW: User registered within 48 hours should be classified as NEW."""
        registered_at = self.now - timedelta(hours=24)  # 24 hours ago

        status = self.service._compute_status(
            pursuits_created=0,
            artifacts_count=0,
            coaching_sessions=0,
            last_login=self.now,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "NEW"

    def test_status_new_overrides_all(self):
        """NEW status should override even ENGAGED criteria."""
        registered_at = self.now - timedelta(hours=12)  # 12 hours ago

        # Even with ENGAGED-level activity, NEW should win
        status = self.service._compute_status(
            pursuits_created=5,
            artifacts_count=10,
            coaching_sessions=20,
            last_login=self.now,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "NEW"

    def test_status_new_boundary(self):
        """User at exactly 48 hours should still be NEW."""
        registered_at = self.now - timedelta(hours=NEW_USER_WINDOW_HOURS)

        status = self.service._compute_status(
            pursuits_created=0,
            artifacts_count=0,
            coaching_sessions=0,
            last_login=self.now,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "NEW"

    def test_status_new_expired(self):
        """User past 48 hours should not be NEW."""
        registered_at = self.now - timedelta(hours=NEW_USER_WINDOW_HOURS + 1)

        status = self.service._compute_status(
            pursuits_created=0,
            artifacts_count=0,
            coaching_sessions=0,
            last_login=self.now,
            registered_at=registered_at,
            now=self.now
        )

        # Should be DORMANT (no pursuits)
        assert status == "DORMANT"

    def test_status_engaged(self):
        """ENGAGED: pursuits >= 1 AND sessions >= 3 AND artifacts >= 2."""
        registered_at = self.now - timedelta(days=10)  # Not new
        last_login = self.now - timedelta(hours=2)  # Recent

        status = self.service._compute_status(
            pursuits_created=2,
            artifacts_count=5,
            coaching_sessions=10,
            last_login=last_login,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "ENGAGED"

    def test_status_engaged_minimum_thresholds(self):
        """ENGAGED should work at minimum thresholds."""
        registered_at = self.now - timedelta(days=10)
        last_login = self.now - timedelta(days=1)

        status = self.service._compute_status(
            pursuits_created=1,  # Minimum
            artifacts_count=ENGAGED_MIN_ARTIFACTS,  # Minimum
            coaching_sessions=ENGAGED_MIN_COACHING_SESSIONS,  # Minimum
            last_login=last_login,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "ENGAGED"

    def test_status_exploring_low_sessions(self):
        """EXPLORING: Has pursuit but insufficient sessions."""
        registered_at = self.now - timedelta(days=10)
        last_login = self.now - timedelta(hours=2)

        status = self.service._compute_status(
            pursuits_created=1,
            artifacts_count=5,  # Enough artifacts
            coaching_sessions=1,  # Not enough sessions
            last_login=last_login,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "EXPLORING"

    def test_status_exploring_low_artifacts(self):
        """EXPLORING: Has pursuit but insufficient artifacts."""
        registered_at = self.now - timedelta(days=10)
        last_login = self.now - timedelta(hours=2)

        status = self.service._compute_status(
            pursuits_created=1,
            artifacts_count=1,  # Not enough artifacts
            coaching_sessions=10,  # Enough sessions
            last_login=last_login,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "EXPLORING"

    def test_status_at_risk(self):
        """AT RISK: Last login > 7 days AND has pursuits."""
        registered_at = self.now - timedelta(days=30)
        last_login = self.now - timedelta(days=AT_RISK_DAYS + 1)  # 8 days ago

        status = self.service._compute_status(
            pursuits_created=2,
            artifacts_count=3,
            coaching_sessions=5,
            last_login=last_login,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "AT RISK"

    def test_status_at_risk_boundary(self):
        """User at exactly 7 days should NOT be AT RISK."""
        registered_at = self.now - timedelta(days=30)
        last_login = self.now - timedelta(days=AT_RISK_DAYS)  # Exactly 7 days

        status = self.service._compute_status(
            pursuits_created=1,
            artifacts_count=0,
            coaching_sessions=0,
            last_login=last_login,
            registered_at=registered_at,
            now=self.now
        )

        # Should be EXPLORING (has pursuit, recent enough login)
        assert status == "EXPLORING"

    def test_status_dormant_no_pursuits(self):
        """DORMANT: No pursuits created."""
        registered_at = self.now - timedelta(days=10)
        last_login = self.now - timedelta(days=1)  # Recent login

        status = self.service._compute_status(
            pursuits_created=0,  # No pursuits
            artifacts_count=0,
            coaching_sessions=0,
            last_login=last_login,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "DORMANT"

    def test_status_dormant_old_login(self):
        """DORMANT: Last login > 14 days."""
        registered_at = self.now - timedelta(days=60)
        last_login = self.now - timedelta(days=DORMANT_DAYS + 1)  # 15 days ago

        status = self.service._compute_status(
            pursuits_created=1,
            artifacts_count=0,
            coaching_sessions=0,
            last_login=last_login,
            registered_at=registered_at,
            now=self.now
        )

        assert status == "DORMANT"

    def test_status_at_risk_before_dormant(self):
        """AT RISK should be checked before DORMANT for 7-14 day window."""
        registered_at = self.now - timedelta(days=60)
        last_login = self.now - timedelta(days=10)  # Between 7 and 14 days

        status = self.service._compute_status(
            pursuits_created=1,
            artifacts_count=1,
            coaching_sessions=1,
            last_login=last_login,
            registered_at=registered_at,
            now=self.now
        )

        # Should be AT RISK (not DORMANT) because they have a pursuit
        assert status == "AT RISK"

    def test_status_no_login_timestamp(self):
        """Handle missing last_login gracefully."""
        registered_at = self.now - timedelta(days=10)

        status = self.service._compute_status(
            pursuits_created=0,
            artifacts_count=0,
            coaching_sessions=0,
            last_login=None,  # No login timestamp
            registered_at=registered_at,
            now=self.now
        )

        # Should be DORMANT (no pursuits, can't determine login recency)
        assert status == "DORMANT"


class TestResponseEnvelope:
    """Tests for response envelope structure."""

    def test_innovator_vitals_record_model(self):
        """InnovatorVitalsRecord should have all required fields."""
        record = InnovatorVitalsRecord(
            user_id="test-123",
            display_name="Test User",
            email="test@example.com",
            experience_level="INTERMEDIATE",
            pursuits_created=3,
            highest_phase_reached=2,
            artifacts_count=5,
            coaching_sessions=10,
            last_login=datetime.now(timezone.utc),
            session_duration_last=45,
            registered_at=datetime.now(timezone.utc) - timedelta(days=30),
            status="ENGAGED"
        )

        assert record.user_id == "test-123"
        assert record.display_name == "Test User"
        assert record.status == "ENGAGED"

    def test_innovator_vitals_record_optional_fields(self):
        """Optional fields should default to None."""
        record = InnovatorVitalsRecord(
            user_id="test-456",
            display_name="Minimal User",
            email="",
            pursuits_created=0,
            artifacts_count=0,
            coaching_sessions=0,
            status="DORMANT"
        )

        assert record.experience_level is None
        assert record.highest_phase_reached is None
        assert record.last_login is None
        assert record.session_duration_last is None
        assert record.registered_at is None

    def test_innovator_vitals_summary_model(self):
        """InnovatorVitalsSummary should have all status counts."""
        summary = InnovatorVitalsSummary(
            total=50,
            engaged=15,
            exploring=12,
            at_risk=8,
            dormant=10,
            new=5
        )

        assert summary.total == 50
        assert summary.engaged == 15
        assert summary.exploring == 12
        assert summary.at_risk == 8
        assert summary.dormant == 10
        assert summary.new == 5

        # Verify sum of statuses equals total
        assert (summary.engaged + summary.exploring + summary.at_risk +
                summary.dormant + summary.new) == summary.total

    def test_innovator_vitals_response_model(self):
        """InnovatorVitalsResponse should have correct structure."""
        response = InnovatorVitalsResponse(
            users=[
                InnovatorVitalsRecord(
                    user_id="u1",
                    display_name="User One",
                    email="u1@test.com",
                    pursuits_created=1,
                    artifacts_count=2,
                    coaching_sessions=3,
                    status="ENGAGED"
                )
            ],
            summary=InnovatorVitalsSummary(
                total=1,
                engaged=1,
                exploring=0,
                at_risk=0,
                dormant=0,
                new=0
            ),
            generated_at=datetime.now(timezone.utc),
            warnings=[]
        )

        assert len(response.users) == 1
        assert response.summary.total == 1
        assert response.warnings == []

    def test_response_with_warnings(self):
        """Response should include warnings when aggregation fails."""
        response = InnovatorVitalsResponse(
            users=[],
            summary=InnovatorVitalsSummary(
                total=0,
                engaged=0,
                exploring=0,
                at_risk=0,
                dormant=0,
                new=0
            ),
            generated_at=datetime.now(timezone.utc),
            warnings=["Pursuits aggregation failed: timeout"]
        )

        assert len(response.warnings) == 1
        assert "Pursuits aggregation failed" in response.warnings[0]


class TestPhaseConversion:
    """Tests for phase string to number conversion."""

    def setup_method(self):
        """Set up test fixtures."""
        mock_db = MagicMock()
        mock_db.db = MagicMock()
        self.service = InnovatorVitalsService(mock_db)

    def test_phase_string_uppercase(self):
        """Uppercase phase strings should convert correctly."""
        assert self.service._phase_to_number("VISION") == 1
        assert self.service._phase_to_number("PITCH") == 2
        assert self.service._phase_to_number("DE_RISK") == 3
        assert self.service._phase_to_number("BUILD") == 4
        assert self.service._phase_to_number("DEPLOY") == 5

    def test_phase_string_lowercase(self):
        """Lowercase phase strings should convert correctly."""
        assert self.service._phase_to_number("vision") == 1
        assert self.service._phase_to_number("pitch") == 2

    def test_phase_integer(self):
        """Integer phases should pass through."""
        assert self.service._phase_to_number(1) == 1
        assert self.service._phase_to_number(5) == 5

    def test_phase_unknown(self):
        """Unknown phases should return None."""
        assert self.service._phase_to_number("UNKNOWN") is None
        assert self.service._phase_to_number(None) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
