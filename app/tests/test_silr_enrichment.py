"""
InDE MVP v3.0.3 - SILR Temporal Enrichment Tests

Tests for:
- All 8 visualization types
- Null-safe rendering for pre-v3.0.1 pursuits
- Report type integration (terminal, living snapshot, portfolio)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSILRTemporalEnrichment:
    """Tests for SILRTemporalEnrichment class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.db = Mock()
        return db

    @pytest.fixture
    def enrichment(self, mock_db):
        """Create SILRTemporalEnrichment instance."""
        from reports.silr_temporal_enrichment import SILRTemporalEnrichment
        return SILRTemporalEnrichment(mock_db)

    def test_enrich_terminal_report_with_data(self, enrichment, mock_db):
        """Test terminal report enrichment with full data."""
        mock_db.get_pursuit.return_value = {
            "pursuit_id": "p1",
            "created_at": datetime.now(timezone.utc) - timedelta(days=30)
        }
        mock_db.db.phase_transitions.find.return_value.sort.return_value = [
            {"from_phase": "VISION", "to_phase": "DE_RISK", "transitioned_at": datetime.now(timezone.utc) - timedelta(days=20)}
        ]
        mock_db.get_health_score_history.return_value = [
            {"health_score": 70, "timestamp": datetime.now(timezone.utc)}
        ]
        mock_db.get_latest_risk_detection.return_value = {
            "risks_by_horizon": {"short_term": [], "medium_term": [], "long_term": []}
        }
        mock_db.get_pursuit_experiments.return_value = []
        mock_db.db.velocity_metrics.find.return_value.sort.return_value.limit.return_value = []
        mock_db.db.time_allocations.find_one.return_value = None
        mock_db.db.patterns.find.return_value = []
        mock_db.db.temporal_events.find.return_value.limit.return_value = []

        result = enrichment.enrich_terminal_report("p1")

        # Should return dict of visualizations
        assert isinstance(result, dict)

    def test_enrich_terminal_report_null_safe(self, enrichment, mock_db):
        """Test terminal report enrichment with no temporal data (pre-v3.0.1)."""
        mock_db.get_pursuit.return_value = None
        mock_db.db.phase_transitions.find.return_value.sort.return_value = []
        mock_db.get_health_score_history.return_value = []
        mock_db.get_latest_risk_detection.return_value = None
        mock_db.get_pursuit_experiments.return_value = []

        result = enrichment.enrich_terminal_report("p1")

        # Should return empty dict, not error
        assert isinstance(result, dict)
        # No visualizations should be generated
        assert len(result) == 0 or all(v is None for v in result.values())

    def test_enrich_living_snapshot(self, enrichment, mock_db):
        """Test living snapshot enrichment."""
        mock_db.get_latest_health_score.return_value = {"health_score": 75, "zone": "HEALTHY"}
        mock_db.get_health_score_history.return_value = [
            {"health_score": 70, "timestamp": datetime.now(timezone.utc)},
            {"health_score": 72, "timestamp": datetime.now(timezone.utc) - timedelta(days=1)}
        ]
        mock_db.db.velocity_metrics.find.return_value.sort.return_value.limit.return_value = []
        mock_db.db.time_allocations.find_one.return_value = None

        result = enrichment.enrich_living_snapshot("p1")

        assert isinstance(result, dict)

    def test_enrich_portfolio_report(self, enrichment, mock_db):
        """Test portfolio report enrichment."""
        mock_db.get_user_pursuits.return_value = [
            {"pursuit_id": "p1", "title": "Pursuit 1"},
            {"pursuit_id": "p2", "title": "Pursuit 2"}
        ]
        mock_db.get_health_score_history.return_value = [
            {"health_score": 75}
        ]
        mock_db.db.pursuits.find.return_value.sort.return_value.limit.return_value = []

        result = enrichment.enrich_portfolio_report("user_1")

        assert isinstance(result, dict)

    def test_get_enrichment_summary(self, enrichment, mock_db):
        """Test enrichment summary generation."""
        mock_db.get_pursuit.return_value = {"pursuit_id": "p1"}
        mock_db.db.phase_transitions.find.return_value.sort.return_value = [
            {"from_phase": "VISION", "to_phase": "DE_RISK"}
        ]
        mock_db.db.velocity_metrics.find.return_value.sort.return_value.limit.return_value = [
            {"elements_per_week": 3.0}
        ]
        mock_db.get_health_score_history.return_value = [{"health_score": 70}]
        mock_db.get_latest_risk_detection.return_value = {"risks_by_horizon": {}}
        mock_db.get_pursuit_experiments.return_value = []
        mock_db.db.time_allocations.find_one.return_value = None

        result = enrichment.get_enrichment_summary(pursuit_id="p1", report_type="terminal")

        assert "available_visualizations" in result
        assert "data_completeness" in result
        assert "recommendations" in result


class TestAnalyticsVisualizations:
    """Tests for analytics visualization functions."""

    def test_create_health_badge(self):
        """Test health badge creation."""
        from ui.analytics_visualizations import create_health_badge

        result = create_health_badge(75, "HEALTHY")

        # Should return bytes (PNG image)
        assert isinstance(result, bytes)
        # Should have PNG header
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

    def test_create_velocity_bar_chart(self):
        """Test velocity bar chart creation."""
        from ui.analytics_visualizations import create_velocity_bar_chart

        per_pursuit = {"p1": 3.5, "p2": 2.8, "p3": 4.2}
        mean = 3.5

        result = create_velocity_bar_chart(per_pursuit, mean)

        assert isinstance(result, bytes)
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

    def test_create_health_trend_chart(self):
        """Test health trend chart creation."""
        from ui.analytics_visualizations import create_health_trend_chart

        history = [
            {"health_score": 60, "timestamp": datetime.now(timezone.utc) - timedelta(days=7)},
            {"health_score": 65, "timestamp": datetime.now(timezone.utc) - timedelta(days=5)},
            {"health_score": 70, "timestamp": datetime.now(timezone.utc) - timedelta(days=3)},
            {"health_score": 75, "timestamp": datetime.now(timezone.utc)}
        ]

        result = create_health_trend_chart(history)

        assert isinstance(result, bytes)
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

    def test_create_risk_horizon_map(self):
        """Test risk horizon map creation."""
        from ui.analytics_visualizations import create_risk_horizon_map

        by_horizon = {"short": 2, "medium": 5, "long": 3}

        result = create_risk_horizon_map(by_horizon)

        assert isinstance(result, bytes)
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

    def test_create_rve_status_chart(self):
        """Test RVE status donut chart creation."""
        from ui.analytics_visualizations import create_rve_status_chart

        by_zone = {"PASS": 5, "GREY": 3, "FAIL": 2}

        result = create_rve_status_chart(by_zone)

        assert isinstance(result, bytes)
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

    def test_create_prediction_gauge(self):
        """Test prediction gauge creation."""
        from ui.analytics_visualizations import create_prediction_gauge

        result = create_prediction_gauge(75.5)

        assert isinstance(result, bytes)
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

    def test_create_learning_sparkline(self):
        """Test learning sparkline creation."""
        from ui.analytics_visualizations import create_learning_sparkline

        values = [3.2, 3.5, 3.1, 4.0, 3.8, 4.2, 4.5]

        result = create_learning_sparkline(values)

        assert isinstance(result, bytes)
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

    def test_create_portfolio_heatmap(self):
        """Test portfolio heatmap creation."""
        from ui.analytics_visualizations import create_portfolio_heatmap

        pursuit_data = [
            {"name": "Pursuit 1", "health_history": [60, 65, 70, 75]},
            {"name": "Pursuit 2", "health_history": [50, 55, 60, 65]},
            {"name": "Pursuit 3", "health_history": [70, 72, 75, 80]}
        ]

        result = create_portfolio_heatmap(pursuit_data)

        assert isinstance(result, bytes)
        assert result[:8] == b'\x89PNG\r\n\x1a\n'

    def test_visualization_empty_data(self):
        """Test visualizations handle empty data gracefully."""
        from ui.analytics_visualizations import (
            create_health_trend_chart,
            create_risk_horizon_map,
            create_rve_status_chart
        )

        # Empty health history
        result = create_health_trend_chart([])
        assert result is None or isinstance(result, bytes)

        # Empty risk data
        result = create_risk_horizon_map({})
        assert result is None or isinstance(result, bytes)

        # Empty RVE data
        result = create_rve_status_chart({})
        assert result is None or isinstance(result, bytes)


class TestInDEColorTheme:
    """Tests for InDE color theme consistency."""

    def test_zone_colors_defined(self):
        """Test that all zone colors are defined."""
        from config import INDE_COLORS

        expected_zones = ["THRIVING", "HEALTHY", "ATTENTION", "AT_RISK", "CRITICAL"]
        for zone in expected_zones:
            assert zone in INDE_COLORS, f"Missing color for zone: {zone}"

    def test_color_format(self):
        """Test that colors are in valid format."""
        from config import INDE_COLORS

        for zone, color in INDE_COLORS.items():
            # Should be hex color format
            assert color.startswith("#"), f"Color for {zone} should be hex format"
            assert len(color) == 7, f"Color for {zone} should be #RRGGBB format"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
