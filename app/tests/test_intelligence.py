"""
InDE MVP v3.0.2 - Intelligence Layer Test Suite

Comprehensive tests for:
- HealthMonitor: Health scoring and zone classification
- TemporalPatternIntelligence: Pattern enrichment and anti-pattern detection
- PredictiveGuidanceEngine: Forward-looking predictions
- TemporalRiskDetector: Three-horizon risk detection
- RVE: Full Risk Validation Engine components

Run with: pytest tests/test_intelligence.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import (
    HEALTH_ZONES, HEALTH_SCORE_WEIGHTS, ZONE_COACHING_GUIDELINES,
    PREDICTION_TYPES, TEMPORAL_ANTIPATTERNS, RVE_ZONES, RVE_EXPERIMENT_TEMPLATES
)


class TestHealthMonitor:
    """Test suite for HealthMonitor class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.get_pursuit.return_value = {
            "pursuit_id": "test-pursuit-1",
            "title": "Test Pursuit",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }
        db.get_scaffolding_state.return_value = {
            "completeness": {"vision": 0.6, "fears": 0.4, "hypothesis": 0.3}
        }
        db.save_health_score.return_value = True
        db.get_latest_health_score.return_value = None
        db.get_health_score_history.return_value = []
        return db

    @pytest.fixture
    def mock_velocity_tracker(self):
        """Create mock velocity tracker."""
        tracker = Mock()
        tracker.calculate_velocity.return_value = {
            "elements_per_week": 3.5,
            "status": "on_track",
            "trend": "stable"
        }
        return tracker

    @pytest.fixture
    def mock_phase_manager(self):
        """Create mock phase manager."""
        manager = Mock()
        manager.get_current_phase.return_value = "VISION"
        manager.get_phase_status.return_value = {
            "days_used": 10,
            "days_allocated": 30,
            "percent_used": 33.3
        }
        return manager

    @pytest.fixture
    def health_monitor(self, mock_db, mock_velocity_tracker, mock_phase_manager):
        """Create HealthMonitor instance with mocks."""
        from intelligence.health_monitor import HealthMonitor
        return HealthMonitor(mock_db, mock_velocity_tracker, mock_phase_manager)

    def test_calculate_health_returns_valid_structure(self, health_monitor):
        """Test that calculate_health returns expected structure."""
        result = health_monitor.calculate_health("test-pursuit-1")

        assert "health_score" in result
        assert "zone" in result
        assert "components" in result
        assert "zone_info" in result
        assert "crisis_triggered" in result

    def test_health_score_in_valid_range(self, health_monitor):
        """Test that health score is between 0 and 100."""
        result = health_monitor.calculate_health("test-pursuit-1")

        assert 0 <= result["health_score"] <= 100

    def test_zone_is_valid(self, health_monitor):
        """Test that zone is one of the defined health zones."""
        result = health_monitor.calculate_health("test-pursuit-1")

        assert result["zone"] in HEALTH_ZONES

    def test_components_include_all_weights(self, health_monitor):
        """Test that all weighted components are included."""
        result = health_monitor.calculate_health("test-pursuit-1")
        components = result["components"]

        for component in HEALTH_SCORE_WEIGHTS.keys():
            assert component in components

    def test_healthy_pursuit_is_not_critical(self, health_monitor):
        """Test that a healthy pursuit doesn't trigger crisis."""
        result = health_monitor.calculate_health("test-pursuit-1")

        # With our mock setup, pursuit should be healthy
        assert result["zone"] in ["HEALTHY", "THRIVING", "ATTENTION"]
        assert result["crisis_triggered"] is False

    def test_get_coaching_context_returns_guidelines(self, health_monitor):
        """Test that coaching context includes zone guidelines."""
        result = health_monitor.get_coaching_context("test-pursuit-1")

        assert "zone" in result
        assert "guidelines" in result
        assert "tone" in result["guidelines"]
        assert "intervention_style" in result["guidelines"]

    def test_health_trend_with_no_history(self, health_monitor):
        """Test health trend returns stable with no history."""
        result = health_monitor.get_health_trend("test-pursuit-1")

        assert result["trend"] == "stable"
        assert result["change"] == 0


class TestTemporalPatternIntelligence:
    """Test suite for TemporalPatternIntelligence class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.get_pursuit.return_value = {
            "pursuit_id": "test-pursuit-1",
            "created_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }
        db.db.patterns = Mock()
        db.db.patterns.find.return_value.limit.return_value = []
        db.db.temporal_events = Mock()
        db.db.temporal_events.find.return_value.sort.return_value.limit.return_value = []
        return db

    @pytest.fixture
    def mock_velocity_tracker(self):
        """Create mock velocity tracker."""
        tracker = Mock()
        tracker.calculate_velocity.return_value = {
            "elements_per_week": 3.5,
            "status": "on_track"
        }
        tracker.get_velocity_history.return_value = []
        return tracker

    @pytest.fixture
    def mock_phase_manager(self):
        """Create mock phase manager."""
        manager = Mock()
        manager.get_current_phase.return_value = "VISION"
        manager.get_phase_status.return_value = {
            "days_used": 10,
            "days_allocated": 30
        }
        return manager

    @pytest.fixture
    def mock_event_logger(self):
        """Create mock event logger."""
        logger = Mock()
        logger.get_event_stream.return_value = []
        return logger

    @pytest.fixture
    def temporal_patterns(self, mock_db, mock_velocity_tracker, mock_phase_manager, mock_event_logger):
        """Create TemporalPatternIntelligence instance with mocks."""
        from intelligence.temporal_patterns import TemporalPatternIntelligence
        return TemporalPatternIntelligence(
            mock_db, mock_velocity_tracker, mock_phase_manager, mock_event_logger
        )

    def test_detect_antipatterns_returns_list(self, temporal_patterns):
        """Test that detect_antipatterns returns a list."""
        result = temporal_patterns.detect_antipatterns("test-pursuit-1")

        assert isinstance(result, list)

    def test_enrich_pattern_matches_preserves_base_matches(self, temporal_patterns):
        """Test that enrichment preserves original matches."""
        base_matches = [
            {"pattern_id": "p1", "base_relevance": 0.8},
            {"pattern_id": "p2", "base_relevance": 0.6}
        ]

        result = temporal_patterns.enrich_pattern_matches("test-pursuit-1", base_matches)

        assert len(result) == len(base_matches)
        for match in result:
            assert "temporal_relevance" in match

    def test_get_phase_benchmarks_returns_expected_phases(self, temporal_patterns):
        """Test that phase benchmarks cover IKF phases."""
        result = temporal_patterns.get_phase_benchmarks("test-pursuit-1")

        assert "current_phase" in result
        assert "benchmarks" in result


class TestPredictiveGuidanceEngine:
    """Test suite for PredictiveGuidanceEngine class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.get_pursuit.return_value = {
            "pursuit_id": "test-pursuit-1",
            "problem_context": {"domain": "technology"},
            "methodology": "LEAN_STARTUP"
        }
        db.get_scaffolding_state.return_value = {
            "completeness": {"vision": 0.5, "fears": 0.3, "hypothesis": 0.2}
        }
        db.db.patterns = Mock()
        db.db.patterns.find.return_value.limit.return_value = []
        db.get_velocity_history.return_value = []
        return db

    @pytest.fixture
    def mock_velocity_tracker(self):
        """Create mock velocity tracker."""
        tracker = Mock()
        tracker.calculate_velocity.return_value = {
            "elements_per_week": 2.0,
            "status": "on_track",
            "trend": "stable"
        }
        return tracker

    @pytest.fixture
    def mock_phase_manager(self):
        """Create mock phase manager."""
        manager = Mock()
        manager.get_current_phase.return_value = "VISION"
        manager.get_phase_status.return_value = {
            "days_used": 15,
            "days_allocated": 30
        }
        return manager

    @pytest.fixture
    def mock_health_monitor(self):
        """Create mock health monitor."""
        monitor = Mock()
        monitor.calculate_health.return_value = {
            "health_score": 65,
            "zone": "HEALTHY"
        }
        return monitor

    @pytest.fixture
    def predictive_guidance(self, mock_db, mock_velocity_tracker, mock_phase_manager, mock_health_monitor):
        """Create PredictiveGuidanceEngine instance with mocks."""
        from intelligence.predictive_guidance import PredictiveGuidanceEngine
        return PredictiveGuidanceEngine(
            mock_db, mock_velocity_tracker, mock_phase_manager, mock_health_monitor
        )

    def test_generate_predictions_returns_list(self, predictive_guidance):
        """Test that generate_predictions returns a list."""
        result = predictive_guidance.generate_predictions("test-pursuit-1")

        assert isinstance(result, list)

    def test_predictions_have_required_fields(self, predictive_guidance):
        """Test that predictions have required structure."""
        result = predictive_guidance.generate_predictions("test-pursuit-1")

        for prediction in result:
            assert "type" in prediction
            assert "confidence" in prediction
            assert "description" in prediction
            assert prediction["type"] in PREDICTION_TYPES

    def test_predictions_sorted_by_confidence(self, predictive_guidance):
        """Test that predictions are sorted by confidence descending."""
        result = predictive_guidance.generate_predictions("test-pursuit-1")

        if len(result) > 1:
            for i in range(len(result) - 1):
                assert result[i]["confidence"] >= result[i + 1]["confidence"]

    def test_high_confidence_predictions_filter(self, predictive_guidance):
        """Test that high confidence filter works."""
        all_predictions = predictive_guidance.generate_predictions("test-pursuit-1")
        high_conf = predictive_guidance.get_high_confidence_predictions("test-pursuit-1")

        for prediction in high_conf:
            assert prediction["confidence"] >= 0.75

    def test_format_prediction_for_coaching(self, predictive_guidance):
        """Test prediction formatting for coaching integration."""
        prediction = {
            "type": "PHASE_CHALLENGE",
            "title": "Common Challenge",
            "description": "Teams often struggle here",
            "suggestion": "Consider this approach"
        }

        result = predictive_guidance.format_prediction_for_coaching(prediction)

        assert isinstance(result, str)
        assert len(result) > 0


class TestTemporalRiskDetector:
    """Test suite for TemporalRiskDetector class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.get_pursuit.return_value = {
            "pursuit_id": "test-pursuit-1",
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat() + 'Z'
        }
        db.get_scaffolding_state.return_value = {
            "completeness": {"vision": 0.4, "fears": 0.2, "hypothesis": 0.1}
        }
        db.save_risk_detection.return_value = True
        db.get_latest_risk_detection.return_value = None
        return db

    @pytest.fixture
    def mock_velocity_tracker(self):
        """Create mock velocity tracker."""
        tracker = Mock()
        tracker.calculate_velocity.return_value = {
            "elements_per_week": 1.5,
            "status": "behind"
        }
        return tracker

    @pytest.fixture
    def mock_phase_manager(self):
        """Create mock phase manager."""
        manager = Mock()
        manager.get_current_phase.return_value = "VISION"
        manager.get_phase_status.return_value = {
            "days_used": 25,
            "days_allocated": 30
        }
        return manager

    @pytest.fixture
    def mock_health_monitor(self):
        """Create mock health monitor."""
        monitor = Mock()
        monitor.calculate_health.return_value = {
            "health_score": 45,
            "zone": "ATTENTION"
        }
        return monitor

    @pytest.fixture
    def risk_detector(self, mock_db, mock_velocity_tracker, mock_phase_manager, mock_health_monitor):
        """Create TemporalRiskDetector instance with mocks."""
        from intelligence.risk_detector import TemporalRiskDetector
        return TemporalRiskDetector(
            mock_db, mock_velocity_tracker, mock_phase_manager, mock_health_monitor
        )

    def test_detect_risks_returns_valid_structure(self, risk_detector):
        """Test that detect_risks returns expected structure."""
        result = risk_detector.detect_risks("test-pursuit-1")

        assert "overall_risk_level" in result
        assert "risk_count" in result
        assert "risks_by_horizon" in result
        assert "recommendations" in result

    def test_risk_horizons_are_present(self, risk_detector):
        """Test that all three risk horizons are included."""
        result = risk_detector.detect_risks("test-pursuit-1")
        horizons = result["risks_by_horizon"]

        assert "short_term" in horizons
        assert "medium_term" in horizons
        assert "long_term" in horizons

    def test_overall_risk_level_is_valid(self, risk_detector):
        """Test that overall risk level is a valid value."""
        result = risk_detector.detect_risks("test-pursuit-1")

        valid_levels = ["LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"]
        assert result["overall_risk_level"] in valid_levels

    def test_get_risk_summary_returns_string(self, risk_detector):
        """Test that risk summary returns readable string."""
        result = risk_detector.get_risk_summary("test-pursuit-1")

        assert isinstance(result, str)
        assert len(result) > 0


class TestRVEComponents:
    """Test suite for Risk Validation Engine components."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database for RVE."""
        db = Mock()
        db.get_pursuit.return_value = {
            "pursuit_id": "test-pursuit-1",
            "methodology": "LEAN_STARTUP"
        }
        db.get_pursuit_fears.return_value = [
            {"fear_id": "f1", "description": "Market too small"},
            {"fear_id": "f2", "description": "Technical feasibility"}
        ]
        db.get_pursuit_experiments.return_value = []
        db.create_validation_experiment.return_value = {"experiment_id": "exp-1"}
        db.update_pursuit_rve_status.return_value = True
        db.get_pursuit_rve_status.return_value = {
            "green_count": 0, "yellow_count": 0, "red_count": 2
        }
        return db

    def test_fear_to_risk_converter(self, mock_db):
        """Test FearToRiskConverter transforms fears to risks."""
        from rve.fear_to_risk import FearToRiskConverter
        converter = FearToRiskConverter(mock_db)

        result = converter.convert_fear_to_risk("test-pursuit-1", "f1", "Market too small")

        assert "risk_id" in result
        assert "risk_statement" in result
        assert "suggested_experiments" in result

    def test_experiment_wizard_templates(self, mock_db):
        """Test ExperimentDesignWizard has templates for methodologies."""
        from rve.experiment_wizard import ExperimentDesignWizard
        wizard = ExperimentDesignWizard(mock_db)

        templates = wizard.get_available_templates("LEAN_STARTUP")

        assert isinstance(templates, list)
        assert len(templates) > 0
        for template in templates:
            assert "name" in template
            assert "description" in template

    def test_risk_assessment_zones(self, mock_db):
        """Test RiskAssessmentEngine uses three-zone model."""
        from rve.risk_assessment import RiskAssessmentEngine
        engine = RiskAssessmentEngine(mock_db)

        zones = engine.get_zone_definitions()

        assert "GREEN" in zones
        assert "YELLOW" in zones
        assert "RED" in zones

    def test_evidence_framework_verdict_options(self, mock_db):
        """Test EvidenceFramework supports verdict options."""
        from rve.evidence_framework import EvidenceFramework
        framework = EvidenceFramework(mock_db)

        verdicts = framework.get_verdict_options()

        assert "SUPPORTS" in verdicts or "supports" in str(verdicts).lower()
        assert "CONTRADICTS" in verdicts or "contradicts" in str(verdicts).lower()

    def test_override_manager_captures_decision(self, mock_db):
        """Test OverrideManager captures innovator decisions."""
        from rve.override_manager import OverrideManager
        manager = OverrideManager(mock_db)

        result = manager.record_override(
            pursuit_id="test-pursuit-1",
            risk_id="r1",
            decision="PROCEED_DESPITE_RED",
            rationale="Acceptable risk for strategic reasons"
        )

        assert result is not None
        assert "override_id" in result


class TestZoneCoachingGuidelines:
    """Test suite for zone-specific coaching guidelines."""

    def test_all_zones_have_guidelines(self):
        """Test that all health zones have coaching guidelines."""
        for zone in HEALTH_ZONES.keys():
            assert zone in ZONE_COACHING_GUIDELINES
            assert "tone" in ZONE_COACHING_GUIDELINES[zone]
            assert "intervention_style" in ZONE_COACHING_GUIDELINES[zone]

    def test_critical_zone_is_urgent(self):
        """Test that CRITICAL zone guidance is appropriately urgent."""
        critical_guidelines = ZONE_COACHING_GUIDELINES["CRITICAL"]

        assert "urgent" in critical_guidelines["tone"].lower() or "honest" in critical_guidelines["tone"].lower()

    def test_thriving_zone_is_celebratory(self):
        """Test that THRIVING zone guidance is celebratory."""
        thriving_guidelines = ZONE_COACHING_GUIDELINES["THRIVING"]

        assert "celebrat" in thriving_guidelines["tone"].lower() or "forward" in thriving_guidelines["tone"].lower()


class TestIntegration:
    """Integration tests for intelligence layer components working together."""

    @pytest.fixture
    def full_mock_db(self):
        """Create comprehensive mock database."""
        db = Mock()
        db.get_pursuit.return_value = {
            "pursuit_id": "test-pursuit-1",
            "title": "Integration Test Pursuit",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat() + 'Z',
            "methodology": "LEAN_STARTUP",
            "problem_context": {"domain": "technology"}
        }
        db.get_scaffolding_state.return_value = {
            "completeness": {"vision": 0.7, "fears": 0.5, "hypothesis": 0.4}
        }
        db.save_health_score.return_value = True
        db.get_latest_health_score.return_value = None
        db.get_health_score_history.return_value = []
        db.save_risk_detection.return_value = True
        db.get_latest_risk_detection.return_value = None
        db.get_velocity_history.return_value = []
        db.db = Mock()
        db.db.patterns = Mock()
        db.db.patterns.find.return_value.limit.return_value = []
        db.db.temporal_events = Mock()
        db.db.temporal_events.find.return_value.sort.return_value.limit.return_value = []
        return db

    @pytest.fixture
    def full_mock_velocity_tracker(self):
        """Create velocity tracker for integration."""
        tracker = Mock()
        tracker.calculate_velocity.return_value = {
            "elements_per_week": 4.0,
            "status": "on_track",
            "trend": "improving"
        }
        tracker.get_velocity_history.return_value = []
        return tracker

    @pytest.fixture
    def full_mock_phase_manager(self):
        """Create phase manager for integration."""
        manager = Mock()
        manager.get_current_phase.return_value = "DE_RISK"
        manager.get_phase_status.return_value = {
            "days_used": 20,
            "days_allocated": 45
        }
        return manager

    @pytest.fixture
    def full_mock_event_logger(self):
        """Create event logger for integration."""
        logger = Mock()
        logger.get_event_stream.return_value = []
        return logger

    def test_intelligence_summary_integration(
        self, full_mock_db, full_mock_velocity_tracker,
        full_mock_phase_manager, full_mock_event_logger
    ):
        """Test that all intelligence components work together."""
        from intelligence.health_monitor import HealthMonitor
        from intelligence.temporal_patterns import TemporalPatternIntelligence
        from intelligence.predictive_guidance import PredictiveGuidanceEngine
        from intelligence.risk_detector import TemporalRiskDetector

        # Initialize components
        health_monitor = HealthMonitor(
            full_mock_db, full_mock_velocity_tracker, full_mock_phase_manager
        )
        temporal_patterns = TemporalPatternIntelligence(
            full_mock_db, full_mock_velocity_tracker,
            full_mock_phase_manager, full_mock_event_logger
        )
        predictive_guidance = PredictiveGuidanceEngine(
            full_mock_db, full_mock_velocity_tracker,
            full_mock_phase_manager, health_monitor
        )
        risk_detector = TemporalRiskDetector(
            full_mock_db, full_mock_velocity_tracker,
            full_mock_phase_manager, health_monitor
        )

        # Get results from all components
        pursuit_id = "test-pursuit-1"

        health = health_monitor.calculate_health(pursuit_id)
        antipatterns = temporal_patterns.detect_antipatterns(pursuit_id)
        predictions = predictive_guidance.generate_predictions(pursuit_id)
        risks = risk_detector.detect_risks(pursuit_id)

        # Verify all components return valid data
        assert health["health_score"] >= 0
        assert health["zone"] in HEALTH_ZONES
        assert isinstance(antipatterns, list)
        assert isinstance(predictions, list)
        assert "overall_risk_level" in risks

        # Verify coaching context uses health
        coaching_context = health_monitor.get_coaching_context(pursuit_id)
        assert coaching_context["zone"] == health["zone"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
