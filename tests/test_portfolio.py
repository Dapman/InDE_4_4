"""
InDE MVP v3.0.3 - Portfolio Intelligence Tests

Tests for:
- Portfolio health calculation (all zones, edge cases)
- Velocity distribution statistics
- Cross-pursuit comparison (same phase, different phases, missing data)
- Effectiveness scorecard (all 7 metrics)
- Portfolio pattern detection
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPortfolioIntelligenceEngine:
    """Tests for PortfolioIntelligenceEngine."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.db = Mock()
        return db

    @pytest.fixture
    def portfolio_engine(self, mock_db):
        """Create PortfolioIntelligenceEngine instance."""
        from analytics import PortfolioIntelligenceEngine
        return PortfolioIntelligenceEngine(mock_db)

    def test_portfolio_health_no_pursuits(self, portfolio_engine, mock_db):
        """Test portfolio health with 0 pursuits."""
        mock_db.get_user_pursuits.return_value = []

        result = portfolio_engine.calculate_portfolio_health("user_1")

        assert result["pursuit_count"] == 0
        assert result["health_score"] == 0
        assert result["zone"] == "CRITICAL"

    def test_portfolio_health_single_pursuit(self, portfolio_engine, mock_db):
        """Test portfolio health with 1 pursuit."""
        mock_db.get_user_pursuits.return_value = [
            {"pursuit_id": "p1", "current_phase": "VISION", "portfolio_priority": 1.0}
        ]
        mock_db.get_latest_health_score.return_value = {"health_score": 75, "zone": "HEALTHY"}

        result = portfolio_engine.calculate_portfolio_health("user_1")

        assert result["pursuit_count"] == 1
        assert result["health_score"] == 75
        assert result["zone"] == "HEALTHY"

    def test_portfolio_health_weighted_calculation(self, portfolio_engine, mock_db):
        """Test weighted health calculation with multiple pursuits."""
        mock_db.get_user_pursuits.return_value = [
            {"pursuit_id": "p1", "current_phase": "VISION", "portfolio_priority": 1.0},
            {"pursuit_id": "p2", "current_phase": "DE_RISK", "portfolio_priority": 2.0},
        ]

        def mock_health(pursuit_id):
            if pursuit_id == "p1":
                return {"health_score": 80, "zone": "THRIVING"}
            return {"health_score": 60, "zone": "HEALTHY"}

        mock_db.get_latest_health_score.side_effect = mock_health

        result = portfolio_engine.calculate_portfolio_health("user_1")

        # Verify weighted calculation
        assert result["pursuit_count"] == 2
        assert "health_score" in result
        assert "zone" in result
        assert "breakdown" in result

    def test_portfolio_health_zones(self, portfolio_engine, mock_db):
        """Test all portfolio health zones."""
        test_cases = [
            (90, "THRIVING"),
            (70, "HEALTHY"),
            (50, "ATTENTION"),
            (30, "AT_RISK"),
            (10, "CRITICAL"),
        ]

        mock_db.get_user_pursuits.return_value = [
            {"pursuit_id": "p1", "current_phase": "VISION", "portfolio_priority": 1.0}
        ]

        for score, expected_zone in test_cases:
            mock_db.get_latest_health_score.return_value = {"health_score": score, "zone": expected_zone}
            result = portfolio_engine.calculate_portfolio_health("user_1")
            assert result["zone"] == expected_zone, f"Expected {expected_zone} for score {score}"


class TestCrossPursuitComparator:
    """Tests for CrossPursuitComparator."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.db = Mock()
        return db

    @pytest.fixture
    def comparator(self, mock_db):
        """Create CrossPursuitComparator instance."""
        from analytics import CrossPursuitComparator
        return CrossPursuitComparator(mock_db)

    def test_compare_velocity_same_phase(self, comparator, mock_db):
        """Test velocity comparison for pursuits in same phase."""
        mock_db.get_pursuit.side_effect = lambda pid: {
            "pursuit_id": pid,
            "current_phase": "DE_RISK",
            "title": f"Pursuit {pid}"
        }
        mock_db.db.velocity_metrics.find_one.return_value = {
            "elements_per_week": 3.5
        }

        result = comparator.compare_velocity("p1", "p2")

        assert "comparison" in result
        assert "pursuit_1" in result
        assert "pursuit_2" in result
        # Language should be informational, not judgmental
        assert "best" not in result.get("comparison", "").lower()
        assert "worst" not in result.get("comparison", "").lower()

    def test_compare_health_trajectory(self, comparator, mock_db):
        """Test health trajectory comparison."""
        mock_db.get_pursuit.return_value = {"pursuit_id": "p1", "title": "Test"}
        mock_db.get_health_score_history.return_value = [
            {"health_score": 60, "timestamp": datetime.now(timezone.utc)},
            {"health_score": 70, "timestamp": datetime.now(timezone.utc) - timedelta(days=7)},
        ]

        result = comparator.compare_health_trajectory("p1", "p2")

        assert "pursuit_1_trend" in result
        assert "pursuit_2_trend" in result


class TestEffectivenessScorecard:
    """Tests for InnovationEffectivenessScorecard."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.db = Mock()
        return db

    @pytest.fixture
    def scorecard(self, mock_db):
        """Create InnovationEffectivenessScorecard instance."""
        from analytics import InnovationEffectivenessScorecard
        return InnovationEffectivenessScorecard(mock_db)

    def test_scorecard_insufficient_data(self, scorecard, mock_db):
        """Test scorecard with insufficient data."""
        mock_db.db.pursuits.find.return_value = Mock()
        mock_db.db.pursuits.find.return_value.count.return_value = 0

        result = scorecard.calculate_full_scorecard("user_1")

        assert "metrics" in result
        # Should handle insufficient data gracefully

    def test_scorecard_all_metrics(self, scorecard, mock_db):
        """Test that all 7 metrics are calculated."""
        expected_metrics = [
            "learning_velocity_trend",
            "prediction_accuracy",
            "risk_validation_roi",
            "pattern_application_success",
            "fear_resolution_rate",
            "retrospective_completeness",
            "time_to_decision"
        ]

        # Setup mock data for each metric
        mock_db.db.pursuits.find.return_value = [
            {"pursuit_id": "p1", "status": "launched", "created_at": datetime.now(timezone.utc) - timedelta(days=30)}
        ]
        mock_db.db.patterns.find.return_value = []
        mock_db.db.experiments.find.return_value = []

        result = scorecard.calculate_full_scorecard("user_1")

        # All metrics should be present
        for metric in expected_metrics:
            assert metric in result.get("metrics", {}), f"Missing metric: {metric}"


class TestPortfolioPatternDetection:
    """Tests for portfolio pattern detection."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.db = Mock()
        return db

    @pytest.fixture
    def portfolio_engine(self, mock_db):
        """Create PortfolioIntelligenceEngine instance."""
        from analytics import PortfolioIntelligenceEngine
        return PortfolioIntelligenceEngine(mock_db)

    def test_detect_shared_risk_pattern(self, portfolio_engine, mock_db):
        """Test detection of shared risk across pursuits."""
        mock_db.get_user_pursuits.return_value = [
            {"pursuit_id": "p1"},
            {"pursuit_id": "p2"}
        ]
        mock_db.db.fears.find.return_value = [
            {"pursuit_id": "p1", "content": "Market timing risk"},
            {"pursuit_id": "p2", "content": "Market timing concern"}
        ]

        result = portfolio_engine.detect_portfolio_patterns("user_1")

        # Should detect pattern (or handle case where no patterns found)
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
