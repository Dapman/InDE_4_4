"""
InDE v3.7.1 - EMS Process Observation Engine Tests

Tests for the EMS module including:
- ProcessObserver functionality
- Observation recording and retrieval
- Synthesis eligibility calculation
- Display Label integration
- Ad-hoc archetype configuration
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch


class TestProcessObserver:
    """Tests for ProcessObserver core functionality."""

    def test_observation_type_enum(self):
        """Test ObservationType enum has all expected values."""
        from ems.process_observer import ObservationType

        expected_types = [
            "ARTIFACT_CREATED",
            "TOOL_INVOKED",
            "DECISION_MADE",
            "TEMPORAL_PATTERN",
            "COACHING_INTERACTION",
            "ELEMENT_CAPTURED",
            "RISK_VALIDATION",
        ]

        for otype in expected_types:
            assert hasattr(ObservationType, otype)
            assert ObservationType[otype].value == otype

    def test_observation_weights_configured(self):
        """Test that observation weights are properly configured."""
        from ems.process_observer import ProcessObserver, ObservationType

        observer = ProcessObserver()

        # Check all types have weights
        for otype in ObservationType:
            assert otype in observer.observation_weights
            weight = observer.observation_weights[otype]
            assert 0.0 <= weight <= 1.0

        # Check specific weights from spec
        assert observer.observation_weights[ObservationType.ARTIFACT_CREATED] == 0.8
        assert observer.observation_weights[ObservationType.DECISION_MADE] == 0.9
        assert observer.observation_weights[ObservationType.COACHING_INTERACTION] == 0.3
        assert observer.observation_weights[ObservationType.TEMPORAL_PATTERN] == 0.5

    def test_process_observation_to_dict(self):
        """Test ProcessObservation serialization."""
        from ems.process_observer import ProcessObservation, ObservationType

        obs = ProcessObservation(
            pursuit_id="test-pursuit-1",
            innovator_id="test-user-1",
            observation_type=ObservationType.ARTIFACT_CREATED,
            timestamp=datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc),
            sequence_number=1,
            details={"artifact_type": "vision", "artifact_id": "v-123"},
            context={"source": "test"},
            signal_weight=0.8,
            is_external_influence=False,
        )

        result = obs.to_dict()

        assert result["pursuit_id"] == "test-pursuit-1"
        assert result["innovator_id"] == "test-user-1"
        assert result["observation_type"] == "ARTIFACT_CREATED"
        assert result["sequence_number"] == 1
        assert result["signal_weight"] == 0.8
        assert result["is_external_influence"] is False
        assert "artifact_type" in result["details"]

    def test_process_observation_from_dict(self):
        """Test ProcessObservation deserialization."""
        from ems.process_observer import ProcessObservation, ObservationType

        data = {
            "pursuit_id": "test-pursuit-2",
            "innovator_id": "test-user-2",
            "observation_type": "TOOL_INVOKED",
            "timestamp": "2026-02-19T14:30:00+00:00",
            "sequence_number": 5,
            "details": {"tool_name": "vision_formulator"},
            "context": {},
            "signal_weight": 0.7,
            "is_external_influence": False,
        }

        obs = ProcessObservation.from_dict(data)

        assert obs.pursuit_id == "test-pursuit-2"
        assert obs.observation_type == ObservationType.TOOL_INVOKED
        assert obs.sequence_number == 5
        assert obs.signal_weight == 0.7


class TestAdhocArchetype:
    """Tests for ad-hoc (Freeform) archetype configuration."""

    def test_adhoc_archetype_exists(self):
        """Test that ad_hoc archetype is defined."""
        from methodology.archetypes import ADHOC_ARCHETYPE

        assert ADHOC_ARCHETYPE is not None
        assert ADHOC_ARCHETYPE["id"] == "ad_hoc"
        assert ADHOC_ARCHETYPE["name"] == "Freeform"

    def test_adhoc_has_no_phases(self):
        """Test that ad_hoc archetype has no predefined phases."""
        from methodology.archetypes import ADHOC_ARCHETYPE

        assert ADHOC_ARCHETYPE["phases"] == []

    def test_adhoc_coaching_is_non_directive(self):
        """Test that ad_hoc coaching config is non-directive."""
        from methodology.archetypes import ADHOC_ARCHETYPE

        coaching_config = ADHOC_ARCHETYPE["coaching_config"]

        assert coaching_config["mode"] == "NON_DIRECTIVE"
        assert coaching_config["proactive_triggers_enabled"] is False
        assert coaching_config["socratic_questioning_enabled"] is False
        assert coaching_config["convergence_detection_enabled"] is False
        assert coaching_config["available_on_request"] is True

    def test_adhoc_ems_config(self):
        """Test that ad_hoc has EMS configuration."""
        from methodology.archetypes import ADHOC_ARCHETYPE

        ems_config = ADHOC_ARCHETYPE["ems_config"]

        assert ems_config["observation_enabled"] is True
        assert ems_config["synthesis_threshold_pursuits"] == 3
        assert ems_config["high_confidence_threshold"] == 5

    def test_is_adhoc_pursuit_function(self):
        """Test is_adhoc_pursuit helper function."""
        from methodology.archetypes import is_adhoc_pursuit

        adhoc = {"archetype": "ad_hoc"}
        lean = {"archetype": "lean_startup"}

        assert is_adhoc_pursuit(adhoc) is True
        assert is_adhoc_pursuit(lean) is False

    def test_nondirective_modifier(self):
        """Test non-directive coaching modifier is defined."""
        from methodology.archetypes import get_nondirective_modifier

        modifier = get_nondirective_modifier()

        assert "RESPONSIVE" in modifier.upper()
        assert "NOT" in modifier.upper()
        assert "PROACTIVE" in modifier.upper()


class TestDisplayLabelsEMS:
    """Tests for EMS-related Display Labels."""

    def test_observation_status_labels(self):
        """Test observation status labels exist."""
        from shared.display_labels import DisplayLabels

        statuses = ["ACTIVE", "PAUSED", "COMPLETED", "ABANDONED"]

        for status in statuses:
            label = DisplayLabels.get("observation_status", status)
            assert label != status  # Should be human-readable

    def test_observation_type_labels(self):
        """Test observation type labels exist."""
        from shared.display_labels import DisplayLabels

        types = [
            "ARTIFACT_CREATED",
            "TOOL_INVOKED",
            "DECISION_MADE",
            "TEMPORAL_PATTERN",
            "COACHING_INTERACTION",
            "ELEMENT_CAPTURED",
            "RISK_VALIDATION",
        ]

        for otype in types:
            label = DisplayLabels.get("observation_type", otype)
            # Should be lowercase, human-readable
            assert label[0].isupper()  # Starts with capital

    def test_synthesis_eligibility_labels(self):
        """Test synthesis eligibility labels exist."""
        from shared.display_labels import DisplayLabels

        levels = ["NOT_ENOUGH_DATA", "ELIGIBLE", "HIGH_CONFIDENCE"]

        for level in levels:
            label = DisplayLabels.get("synthesis_eligibility", level)
            assert label != level

    def test_coaching_mode_labels(self):
        """Test coaching mode labels include NON_DIRECTIVE."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("coaching_mode", "NON_DIRECTIVE")
        assert "Responsive" in label

    def test_freeform_archetype_label(self):
        """Test ad_hoc archetype displays as 'Freeform'."""
        from shared.display_labels import DisplayLabels

        label1 = DisplayLabels.get("methodology_archetype", "ad_hoc")
        label2 = DisplayLabels.get("methodology_archetype", "adhoc")

        assert label1 == "Freeform"
        assert label2 == "Freeform"


class TestEMSConfig:
    """Tests for EMS configuration in config.py."""

    def test_ems_config_exists(self):
        """Test EMS configuration is defined."""
        from core.config import EMS_CONFIG

        assert EMS_CONFIG is not None
        assert "observation_enabled" in EMS_CONFIG
        assert "significant_gap_hours" in EMS_CONFIG
        assert "synthesis_threshold_pursuits" in EMS_CONFIG

    def test_ems_observation_types_config(self):
        """Test EMS observation types configuration."""
        from core.config import EMS_OBSERVATION_TYPES

        expected_types = [
            "ARTIFACT_CREATED",
            "TOOL_INVOKED",
            "DECISION_MADE",
            "TEMPORAL_PATTERN",
            "COACHING_INTERACTION",
            "ELEMENT_CAPTURED",
            "RISK_VALIDATION",
        ]

        for otype in expected_types:
            assert otype in EMS_OBSERVATION_TYPES
            assert "weight" in EMS_OBSERVATION_TYPES[otype]

    def test_adhoc_coaching_config(self):
        """Test ad-hoc coaching configuration."""
        from core.config import ADHOC_COACHING_CONFIG

        assert ADHOC_COACHING_CONFIG["mode"] == "NON_DIRECTIVE"
        assert ADHOC_COACHING_CONFIG["proactive_triggers_enabled"] is False

    def test_ems_stream_in_redis_streams(self):
        """Test EMS stream is in Redis streams list."""
        from core.config import REDIS_STREAMS

        assert "ems" in REDIS_STREAMS

    def test_methodology_archetypes_includes_adhoc(self):
        """Test METHODOLOGY_ARCHETYPES includes ad_hoc."""
        from core.config import METHODOLOGY_ARCHETYPES

        assert "ad_hoc" in METHODOLOGY_ARCHETYPES


class TestEMSEvents:
    """Tests for EMS event definitions."""

    def test_ems_event_type_enum(self):
        """Test EMSEventType enum has expected values."""
        from ems.events import EMSEventType

        expected = [
            "OBSERVATION_RECORDED",
            "SYNTHESIS_ELIGIBLE",
            "SYNTHESIS_REQUESTED",
            "OBSERVATION_STARTED",
            "OBSERVATION_COMPLETED",
        ]

        for event in expected:
            assert hasattr(EMSEventType, event)

    def test_ems_event_handler_exists(self):
        """Test EMSEventHandler class exists."""
        from ems.events import EMSEventHandler

        handler = EMSEventHandler()
        assert handler is not None

    def test_ems_handler_has_required_methods(self):
        """Test EMSEventHandler has all required handler methods."""
        from ems.events import EMSEventHandler

        handler = EMSEventHandler()

        required_methods = [
            "handle_pursuit_created",
            "handle_artifact_created",
            "handle_element_captured",
            "handle_coaching_message",
            "handle_rve_experiment",
            "handle_pursuit_completed",
        ]

        for method in required_methods:
            assert hasattr(handler, method)
            assert callable(getattr(handler, method))


class TestODICMNonDirective:
    """Tests for ODICM non-directive mode."""

    def test_coaching_mode_includes_non_directive(self):
        """Test CoachingMode enum includes NON_DIRECTIVE."""
        from coaching.odicm_extensions import CoachingMode

        assert hasattr(CoachingMode, "NON_DIRECTIVE")
        assert CoachingMode.NON_DIRECTIVE.value == "non_directive"


class TestCollectionsAdded:
    """Tests for database collection additions."""

    def test_process_observations_in_collections(self):
        """Test process_observations collection is defined."""
        from core.config import COLLECTIONS

        assert "process_observations" in COLLECTIONS


class TestVersionUpdate:
    """Tests for version string updates."""

    def test_version_is_3_7_1(self):
        """Test VERSION is 3.7.1."""
        from core.config import VERSION

        assert VERSION == "3.7.1"

    def test_version_name_mentions_ems(self):
        """Test VERSION_NAME mentions EMS."""
        from core.config import VERSION_NAME

        assert "EMS" in VERSION_NAME or "Process Observation" in VERSION_NAME


# =============================================================================
# INTEGRATION TESTS (with mocked database)
# =============================================================================

class TestProcessObserverIntegration:
    """Integration tests with mocked database."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return Mock()

    def test_synthesis_eligibility_not_enough(self, mock_db):
        """Test synthesis eligibility with insufficient pursuits."""
        from ems.process_observer import ProcessObserver

        with patch("ems.process_observer.db") as db_mock:
            db_mock.get_adhoc_pursuit_count.return_value = 1

            observer = ProcessObserver()
            result = observer.get_synthesis_eligibility("test-user")

            assert result["eligibility"] == "NOT_ENOUGH_DATA"
            assert result["pursuits_until_eligible"] == 2

    def test_synthesis_eligibility_eligible(self, mock_db):
        """Test synthesis eligibility with sufficient pursuits."""
        from ems.process_observer import ProcessObserver

        with patch("ems.process_observer.db") as db_mock:
            db_mock.get_adhoc_pursuit_count.return_value = 3

            observer = ProcessObserver()
            result = observer.get_synthesis_eligibility("test-user")

            assert result["eligibility"] == "ELIGIBLE"
            assert result["pursuits_until_eligible"] == 0

    def test_synthesis_eligibility_high_confidence(self, mock_db):
        """Test synthesis eligibility with high confidence."""
        from ems.process_observer import ProcessObserver

        with patch("ems.process_observer.db") as db_mock:
            db_mock.get_adhoc_pursuit_count.return_value = 7

            observer = ProcessObserver()
            result = observer.get_synthesis_eligibility("test-user")

            assert result["eligibility"] == "HIGH_CONFIDENCE"


# =============================================================================
# v3.7.1 ARTIFACT DETECTION TESTS
# =============================================================================

class TestArtifactDetectionPatterns:
    """Tests for v3.7.1 artifact detection pattern fixes."""

    def test_data_collection_sheet_detected(self):
        """Test that 'data collection sheet' is detected as experiment artifact."""
        import sys
        sys.path.insert(0, "app")
        from scaffolding.engine import ScaffoldingEngine

        # Create minimal engine for testing pattern detection
        engine = ScaffoldingEngine.__new__(ScaffoldingEngine)

        # Test the detection method
        msg = "Create a data collection sheet consistent with the experiment"
        result = engine._detect_explicit_artifact_request(msg)
        assert result == "experiment"

    def test_produce_that_detected(self):
        """Test that 'produce that' is detected as artifact request."""
        import sys
        sys.path.insert(0, "app")
        from scaffolding.engine import ScaffoldingEngine

        engine = ScaffoldingEngine.__new__(ScaffoldingEngine)

        msg = "That is great. Can you produce that?"
        result = engine._detect_explicit_artifact_request(msg)
        assert result == "experiment"  # Generic defaults to experiment

    def test_produce_as_artifact_detected(self):
        """Test that 'produce that as an artifact' is detected."""
        import sys
        sys.path.insert(0, "app")
        from scaffolding.engine import ScaffoldingEngine

        engine = ScaffoldingEngine.__new__(ScaffoldingEngine)

        msg = "That looks great. Can you produce that as an artifact?"
        result = engine._detect_explicit_artifact_request(msg)
        assert result == "experiment"

    def test_tracking_sheet_detected(self):
        """Test that 'tracking sheet' is detected as experiment artifact."""
        import sys
        sys.path.insert(0, "app")
        from scaffolding.engine import ScaffoldingEngine

        engine = ScaffoldingEngine.__new__(ScaffoldingEngine)

        msg = "Create a tracking sheet for the experiment results"
        result = engine._detect_explicit_artifact_request(msg)
        assert result == "experiment"

    def test_vision_still_works(self):
        """Test that vision artifact detection still works."""
        import sys
        sys.path.insert(0, "app")
        from scaffolding.engine import ScaffoldingEngine

        engine = ScaffoldingEngine.__new__(ScaffoldingEngine)

        msg = "Can you generate a vision statement?"
        result = engine._detect_explicit_artifact_request(msg)
        assert result == "vision"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
