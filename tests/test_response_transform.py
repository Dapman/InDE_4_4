"""
Tests for the API Response Transform Middleware.
InDE MVP v3.7.0 - IKF UI Remediation & Display Label Registry

Core assertion: NO internal identifier survives the transform.
"""

import pytest
import sys
import os
from datetime import datetime, timezone, timedelta

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.middleware.response_transform import ResponseTransformMiddleware
from app.shared.display_labels import DisplayLabels


class TestResponseTransformStripping:
    """Test that internal fields are properly stripped."""

    def test_strip_fields_removed(self):
        """All STRIP_FIELDS are removed from transformed output."""
        raw = {
            "contribution_id": "550e8400-e29b-41d4-a716-446655440000",
            "contributor_org_hash": "abc123def456",
            "instance_id": "node-001",
            "pattern_id": "pat-789",
            "package_type": "temporal_benchmark",
            "pursuit_name": "My SaaS Onboarding"
        }
        result = ResponseTransformMiddleware.transform(raw)

        assert "contribution_id" not in result
        assert "contributor_org_hash" not in result
        assert "instance_id" not in result
        assert "pattern_id" not in result
        assert "pursuit_name" in result  # Non-stripped fields preserved

    def test_mongodb_id_stripped(self):
        """MongoDB _id field is stripped."""
        raw = {"_id": "507f1f77bcf86cd799439011", "name": "Test"}
        result = ResponseTransformMiddleware.transform(raw)
        assert "_id" not in result
        assert "name" in result


class TestResponseTransformTranslation:
    """Test that enum fields are properly translated."""

    def test_translate_fields_converted(self):
        """All TRANSLATE_FIELDS are converted to human-readable labels."""
        raw = {"package_type": "temporal_benchmark"}
        result = ResponseTransformMiddleware.transform(raw)

        assert result["package_type"] == "Timing & Velocity Benchmark"
        assert result["package_type_raw"] == "temporal_benchmark"
        assert result["package_type_icon"] == "⏱️"

    def test_translate_contribution_status(self):
        """Contribution status is translated."""
        raw = {"status": "IKF_READY"}
        result = ResponseTransformMiddleware.transform(raw)

        assert result["status"] == "Ready to Share"
        assert result["status_raw"] == "IKF_READY"

    def test_translate_methodology_archetype(self):
        """Methodology archetype is translated."""
        raw = {"methodology_archetype": "lean_startup"}
        result = ResponseTransformMiddleware.transform(raw)

        assert result["methodology_archetype"] == "Lean Startup"
        assert "_" not in result["methodology_archetype"]


class TestContributionDisplayIdentifier:
    """Test contribution display identifier generation."""

    def test_contribution_display_identifier(self):
        """Contribution gets human-readable primary identifier."""
        raw = {
            "contribution_id": "550e8400-...",
            "package_type": "risk_intelligence",
            "pursuit_name": "My Health Device",
            "created_at": "2026-02-14T10:30:00Z"
        }
        result = ResponseTransformMiddleware.transform_contribution_for_display(raw)

        assert "display_identifier" in result
        assert "My Health Device" in result["display_identifier"]
        assert "Risk Methodology Insight" in result["display_identifier"]
        assert "contribution_id" not in result

    def test_contribution_display_identifier_from_metadata(self):
        """Pursuit name can come from metadata."""
        raw = {
            "contribution_id": "uuid",
            "package_type": "effectiveness",
            "metadata": {"pursuit_name": "Nested Pursuit Name"},
            "created_at": "2026-01-01T00:00:00Z"
        }
        result = ResponseTransformMiddleware.transform_contribution_for_display(raw)

        assert "Nested Pursuit Name" in result["display_identifier"]


class TestPIITransform:
    """Test PII scan result transformation."""

    def test_pii_traffic_light_red(self):
        """High confidence PII shows red traffic light."""
        result = ResponseTransformMiddleware.transform_pii_results(
            {"confidence": 0.92, "field_detections": [{"field": "name"}]}
        )
        assert result["pii_level"] == "red"
        assert "review required" in result["pii_status"].lower()
        assert len(result["details"]) > 0  # Details available for red

    def test_pii_traffic_light_yellow(self):
        """Medium confidence PII shows yellow traffic light."""
        result = ResponseTransformMiddleware.transform_pii_results(
            {"confidence": 0.65, "field_detections": [{"field": "email"}]}
        )
        assert result["pii_level"] == "yellow"
        assert result["detail_available"] is True

    def test_pii_traffic_light_green(self):
        """Low confidence PII shows green traffic light."""
        green = ResponseTransformMiddleware.transform_pii_results(
            {"confidence": 0.15}
        )
        assert green["pii_level"] == "green"
        assert len(green["details"]) == 0  # No details for green

    def test_pii_empty_data(self):
        """Empty PII data returns safe defaults."""
        result = ResponseTransformMiddleware.transform_pii_results({})
        assert result["pii_level"] == "green"

        result2 = ResponseTransformMiddleware.transform_pii_results(None)
        assert result2["pii_level"] == "green"


class TestFederationStatusTransform:
    """Test federation status transformation."""

    def test_federation_status_strips_internals(self):
        """Federation status shows human-friendly label, not state machine."""
        raw = {
            "connection_state": "HALF_OPEN",
            "instance_id": "node-abc-123",
            "last_sync_at": (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat(),
            "pending_count": 3
        }
        result = ResponseTransformMiddleware.transform_federation_status(raw)

        assert "instance_id" not in str(result)
        assert "HALF_OPEN" not in str(result)
        assert "Reconnecting" in result["status_label"]
        assert result["pending_contributions"] == 3

    def test_federation_status_connected(self):
        """Connected state shows appropriate label."""
        raw = {"connection_state": "CONNECTED"}
        result = ResponseTransformMiddleware.transform_federation_status(raw)

        assert "Connected" in result["status_label"]
        assert result["is_connected"] is True

    def test_federation_status_offline(self):
        """Offline state shows appropriate label."""
        raw = {"state": "OFFLINE"}
        result = ResponseTransformMiddleware.transform_federation_status(raw)

        assert "Local" in result["status_label"]
        assert result["is_connected"] is False


class TestNestedTransform:
    """Test recursive transformation of nested structures."""

    def test_nested_transform(self):
        """Nested dicts and lists are recursively transformed."""
        raw = {
            "items": [
                {"contribution_id": "uuid-1", "package_type": "effectiveness"},
                {"contribution_id": "uuid-2", "package_type": "pattern_contribution"}
            ]
        }
        result = ResponseTransformMiddleware.transform(raw)

        for item in result["items"]:
            assert "contribution_id" not in item
            assert "_" not in item["package_type"]  # Translated

    def test_deeply_nested_transform(self):
        """Deeply nested structures are handled."""
        raw = {
            "level1": {
                "level2": {
                    "contribution_id": "should-be-stripped",
                    "status": "IKF_READY"
                }
            }
        }
        result = ResponseTransformMiddleware.transform(raw)

        assert "contribution_id" not in result["level1"]["level2"]
        assert result["level1"]["level2"]["status"] == "Ready to Share"


class TestActivityLogTransform:
    """Test activity log event transformation."""

    def test_activity_log_event_descriptions(self):
        """Activity log events get natural language descriptions."""
        events = [
            {"event_type": "ikf.package.prepared"},
            {"event_type": "ikf.package.reviewed"},
            {"event_type": "pursuit.completed"}
        ]

        for event in events:
            result = ResponseTransformMiddleware.transform_activity_log_event(event)
            assert "description" in result
            assert "." not in result["description"].split()[0]  # No dotted codes

    def test_unknown_event_type_handled(self):
        """Unknown event types get reasonable description."""
        result = ResponseTransformMiddleware.transform_activity_log_event(
            {"event_type": "custom.unknown.event"}
        )
        assert "description" in result
        assert "Custom" in result["description"] or "Unknown" in result["description"].lower()


class TestPatternTransform:
    """Test pattern intelligence transformation."""

    def test_pattern_strips_ids(self):
        """Pattern transform strips pattern IDs."""
        raw = {
            "pattern_id": "pat-123",
            "ikf_pattern_id": "ikf-456",
            "name": "Regulatory Timing Pattern",
            "source": "IKF_GLOBAL"
        }
        result = ResponseTransformMiddleware.transform_pattern_for_display(raw)

        assert "pattern_id" not in result
        assert "ikf_pattern_id" not in result
        assert "name" in result

    def test_pattern_source_badge_ikf(self):
        """IKF patterns get network badge."""
        raw = {"source": "IKF_GLOBAL", "name": "Test"}
        result = ResponseTransformMiddleware.transform_pattern_for_display(raw)

        assert "Innovation Network" in result["source_badge"]

    def test_pattern_source_badge_local(self):
        """Local patterns get experience badge."""
        raw = {"source": "LOCAL", "name": "Test"}
        result = ResponseTransformMiddleware.transform_pattern_for_display(raw)

        assert "Your Experience" in result["source_badge"]


class TestBiomimicryTransform:
    """Test biomimicry feedback transformation."""

    def test_biomimicry_feedback_uses_names(self):
        """Biomimicry feedback uses organism + strategy names, not IDs."""
        raw = {
            "pattern_id": "bio-pat-123",
            "organism_name": "Namibian Desert Beetle",
            "strategy_name": "Fog Harvesting"
        }
        result = ResponseTransformMiddleware.transform_biomimicry_feedback(raw)

        assert "pattern_id" not in result
        assert "Namibian Desert Beetle" in result["confirmation_message"]
        assert "Fog Harvesting" in result["confirmation_message"]


class TestScenarioTransform:
    """Test scenario artifact transformation."""

    def test_scenario_trigger_translation(self):
        """Scenario triggers get natural language descriptions."""
        raw = {"trigger": "fork_language"}
        result = ResponseTransformMiddleware.transform_scenario_artifact(raw)

        assert "trigger_description" in result
        assert "decision point" in result["trigger_description"]


class TestDateFormatting:
    """Test date and time formatting utilities."""

    def test_format_date(self):
        """ISO date formats to human-readable."""
        result = ResponseTransformMiddleware._format_date("2026-02-14T10:30:00Z")
        assert "Feb" in result
        assert "14" in result
        assert "2026" in result

    def test_format_date_empty(self):
        """Empty date returns empty string."""
        assert ResponseTransformMiddleware._format_date("") == ""
        assert ResponseTransformMiddleware._format_date(None) == ""

    def test_format_relative_time_just_now(self):
        """Recent timestamp shows 'Just now'."""
        now = datetime.now(timezone.utc).isoformat()
        result = ResponseTransformMiddleware._format_relative_time(now)
        assert "Just now" in result

    def test_format_relative_time_minutes(self):
        """Minutes-old timestamp shows minutes."""
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        result = ResponseTransformMiddleware._format_relative_time(past)
        assert "minute" in result

    def test_format_relative_time_hours(self):
        """Hours-old timestamp shows hours."""
        past = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        result = ResponseTransformMiddleware._format_relative_time(past)
        assert "hour" in result

    def test_format_relative_time_days(self):
        """Days-old timestamp shows days."""
        past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        result = ResponseTransformMiddleware._format_relative_time(past)
        assert "day" in result

    def test_format_relative_time_never(self):
        """Empty timestamp shows 'Never'."""
        assert ResponseTransformMiddleware._format_relative_time(None) == "Never"
        assert ResponseTransformMiddleware._format_relative_time("") == "Never"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_input(self):
        """None input returns None."""
        assert ResponseTransformMiddleware.transform(None) is None

    def test_list_input(self):
        """List input transforms each item."""
        raw = [
            {"contribution_id": "1", "status": "DRAFT"},
            {"contribution_id": "2", "status": "REVIEWED"}
        ]
        result = ResponseTransformMiddleware.transform(raw)

        assert len(result) == 2
        assert "contribution_id" not in result[0]
        assert result[0]["status"] == "Needs Your Review"

    def test_primitive_input(self):
        """Primitive input passes through unchanged."""
        assert ResponseTransformMiddleware.transform("string") == "string"
        assert ResponseTransformMiddleware.transform(123) == 123
        assert ResponseTransformMiddleware.transform(True) is True

    def test_empty_dict(self):
        """Empty dict returns empty dict."""
        assert ResponseTransformMiddleware.transform({}) == {}

    def test_empty_list(self):
        """Empty list returns empty list."""
        assert ResponseTransformMiddleware.transform([]) == []
