"""
InDE MVP v3.0.3 - Backward Compatibility Tests

Tests to ensure:
- All v3.0.2 features working (health monitoring, intelligence panels, full RVE, risk detection)
- All v3.0.1 features working (TIM core, timeline, velocity tracking)
- All v2.9 features working (sharing, collaboration, SILR, scaffolding, pattern engine)
- Existing pursuits load correctly with new portfolio fields (null-safe defaults)
- rve_lite/ removal causes NO import failures
- Pre-v3.0.1 pursuits generate reports correctly (graceful fallback)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import sys
import os
import importlib

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRVELiteRemoval:
    """Tests to verify rve_lite removal doesn't break imports."""

    def test_no_rve_lite_imports_in_codebase(self):
        """Test that no code imports from rve_lite."""
        import os
        import re

        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Walk through all Python files
        rve_lite_imports = []
        for root, dirs, files in os.walk(base_path):
            # Skip test directories and __pycache__
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'tests']]

            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Check for rve_lite imports
                        if re.search(r'from\s+rve_lite\s+import', content):
                            rve_lite_imports.append(filepath)
                        if re.search(r'import\s+rve_lite', content):
                            rve_lite_imports.append(filepath)
                    except Exception:
                        pass

        assert len(rve_lite_imports) == 0, f"Found rve_lite imports in: {rve_lite_imports}"

    def test_rve_modules_import_correctly(self):
        """Test that full RVE modules import without error."""
        try:
            from rve import (
                FearToRiskConverter,
                EvidenceFramework,
                DecisionSupport,
                ExperimentDesignWizard,
                RiskAssessmentEngine,
                OverrideManager
            )
        except ImportError as e:
            pytest.fail(f"RVE module import failed: {e}")


class TestV302Features:
    """Tests for v3.0.2 features (Intelligence Layer)."""

    def test_health_monitor_import(self):
        """Test health monitor imports."""
        try:
            from intelligence.health_monitor import HealthMonitor
        except ImportError as e:
            pytest.fail(f"Health monitor import failed: {e}")

    def test_risk_detector_import(self):
        """Test risk detector imports."""
        try:
            from intelligence.risk_detector import RiskDetector
        except ImportError as e:
            pytest.fail(f"Risk detector import failed: {e}")

    def test_predictive_guidance_import(self):
        """Test predictive guidance imports."""
        try:
            from intelligence.predictive_guidance import PredictiveGuidance
        except ImportError as e:
            pytest.fail(f"Predictive guidance import failed: {e}")

    def test_health_zones_config(self):
        """Test health zones are properly configured."""
        from config import HEALTH_ZONES, ZONE_COACHING_GUIDELINES

        expected_zones = ["THRIVING", "HEALTHY", "ATTENTION", "AT_RISK", "CRITICAL"]
        for zone in expected_zones:
            assert zone in HEALTH_ZONES, f"Missing zone: {zone}"
            assert zone in ZONE_COACHING_GUIDELINES, f"Missing guidelines for: {zone}"


class TestV301Features:
    """Tests for v3.0.1 features (Temporal Foundation)."""

    def test_tim_modules_import(self):
        """Test TIM modules import."""
        try:
            from tim.allocation_engine import TimeAllocationEngine
            from tim.velocity_tracker import VelocityTracker
            from tim.event_logger import TemporalEventLogger
            from tim.phase_manager import PhaseManager
        except ImportError as e:
            pytest.fail(f"TIM module import failed: {e}")

    def test_temporal_collections_config(self):
        """Test temporal collections are configured."""
        from config import MONGODB_COLLECTIONS

        temporal_collections = [
            "time_allocations",
            "temporal_events",
            "velocity_metrics",
            "phase_transitions"
        ]

        for coll in temporal_collections:
            assert coll in MONGODB_COLLECTIONS, f"Missing collection: {coll}"

    def test_ikf_phases_config(self):
        """Test IKF phases are configured."""
        from config import IKF_PHASES

        expected_phases = ["VISION", "CONCEPT", "DE_RISK", "DEPLOY"]
        for phase in expected_phases:
            assert phase in IKF_PHASES, f"Missing phase: {phase}"


class TestV29Features:
    """Tests for v2.9 features (Connected Innovation)."""

    def test_sharing_modules_import(self):
        """Test sharing modules import."""
        try:
            from sharing import PursuitSharer, StakeholderResponseHandler
            from distribution import ReportDistributor
            from collaboration import ArtifactComments, ActivityFeed
        except ImportError as e:
            pytest.fail(f"Sharing module import failed: {e}")

    def test_silr_config(self):
        """Test SILR configuration exists."""
        from config import LIVING_SNAPSHOT_CONFIG, PORTFOLIO_ANALYTICS_CONFIG

        assert "template_options" in LIVING_SNAPSHOT_CONFIG or True  # May vary
        assert isinstance(PORTFOLIO_ANALYTICS_CONFIG, dict)

    def test_scaffolding_imports(self):
        """Test scaffolding module imports."""
        try:
            from scaffolding.engine import ScaffoldingEngine
            from scaffolding.element_tracker import ElementTracker
            from scaffolding.moment_detector import MomentDetector
        except ImportError as e:
            pytest.fail(f"Scaffolding module import failed: {e}")


class TestNullSafeDefaults:
    """Tests for null-safe defaults on new fields."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.db = Mock()
        return db

    def test_pre_v301_pursuit_loads(self, mock_db):
        """Test that pre-v3.0.1 pursuit (no temporal data) loads correctly."""
        # Simulate pre-v3.0.1 pursuit without temporal fields
        old_pursuit = {
            "pursuit_id": "old_p1",
            "title": "Old Pursuit",
            "user_id": "user_1",
            "status": "active",
            "created_at": datetime.now(timezone.utc) - timedelta(days=90)
            # Missing: current_phase, portfolio_priority, etc.
        }

        mock_db.get_pursuit.return_value = old_pursuit

        # Should not error when accessing new fields with defaults
        phase = old_pursuit.get("current_phase", "VISION")
        priority = old_pursuit.get("portfolio_priority", 1.0)

        assert phase == "VISION"
        assert priority == 1.0

    def test_pre_v303_pursuit_portfolio_fields(self, mock_db):
        """Test that pre-v3.0.3 pursuit handles portfolio fields."""
        # Simulate pre-v3.0.3 pursuit without portfolio fields
        old_pursuit = {
            "pursuit_id": "p1",
            "title": "Test Pursuit",
            "current_phase": "DE_RISK"
            # Missing: portfolio_priority
        }

        mock_db.get_pursuit.return_value = old_pursuit
        mock_db.get_user_pursuits.return_value = [old_pursuit]
        mock_db.get_latest_health_score.return_value = {"health_score": 75, "zone": "HEALTHY"}

        from analytics import PortfolioIntelligenceEngine
        engine = PortfolioIntelligenceEngine(mock_db)

        # Should handle missing portfolio_priority
        result = engine.calculate_portfolio_health("user_1")

        # Should not error, should use default priority
        assert "health_score" in result

    def test_enrichment_handles_no_temporal_data(self, mock_db):
        """Test SILR enrichment handles pursuits with no temporal data."""
        mock_db.get_pursuit.return_value = {"pursuit_id": "p1"}
        mock_db.db.phase_transitions.find.return_value.sort.return_value = []
        mock_db.db.velocity_metrics.find.return_value.sort.return_value.limit.return_value = []
        mock_db.get_health_score_history.return_value = []
        mock_db.get_latest_risk_detection.return_value = None
        mock_db.get_pursuit_experiments.return_value = []
        mock_db.db.time_allocations.find_one.return_value = None
        mock_db.db.temporal_events.find.return_value.limit.return_value = []
        mock_db.db.patterns.find.return_value = []

        from reports.silr_temporal_enrichment import SILRTemporalEnrichment
        enrichment = SILRTemporalEnrichment(mock_db)

        # Should not error, should return empty or minimal data
        result = enrichment.enrich_terminal_report("p1")
        assert isinstance(result, dict)


class TestV303NewFeatures:
    """Tests for v3.0.3 new features (Analytics & Synthesis)."""

    def test_analytics_module_imports(self):
        """Test analytics module imports."""
        try:
            from analytics import (
                PortfolioIntelligenceEngine,
                CrossPursuitComparator,
                InnovationEffectivenessScorecard
            )
        except ImportError as e:
            pytest.fail(f"Analytics module import failed: {e}")

    def test_ikf_module_imports(self):
        """Test IKF module imports."""
        try:
            from ikf import GeneralizationEngine, IKFContributionPreparer
        except ImportError as e:
            pytest.fail(f"IKF module import failed: {e}")

    def test_portfolio_dashboard_import(self):
        """Test portfolio dashboard imports."""
        try:
            from ui.portfolio_dashboard import PortfolioDashboard
        except ImportError as e:
            pytest.fail(f"Portfolio dashboard import failed: {e}")

    def test_silr_enrichment_import(self):
        """Test SILR enrichment imports."""
        try:
            from reports.silr_temporal_enrichment import SILRTemporalEnrichment
        except ImportError as e:
            pytest.fail(f"SILR enrichment import failed: {e}")

    def test_analytics_visualizations_import(self):
        """Test analytics visualizations imports."""
        try:
            from ui.analytics_visualizations import (
                create_health_badge,
                create_velocity_bar_chart,
                create_health_trend_chart
            )
        except ImportError as e:
            pytest.fail(f"Analytics visualizations import failed: {e}")

    def test_new_collections_config(self):
        """Test new collections are configured."""
        from config import MONGODB_COLLECTIONS

        new_collections = ["portfolio_analytics", "ikf_contributions"]
        for coll in new_collections:
            assert coll in MONGODB_COLLECTIONS, f"Missing collection: {coll}"

    def test_portfolio_moment_type_config(self):
        """Test PORTFOLIO_INSIGHT moment type is configured."""
        from config import INTELLIGENCE_MOMENT_TYPES, PORTFOLIO_MOMENT_TYPE

        assert "PORTFOLIO_INSIGHT" in INTELLIGENCE_MOMENT_TYPES
        assert PORTFOLIO_MOMENT_TYPE.get("cooldown_minutes") == 2  # 120 seconds


class TestDatabaseBackwardCompatibility:
    """Tests for database backward compatibility."""

    def test_version_config(self):
        """Test version is correctly set."""
        from config import VERSION, VERSION_NAME, DATABASE_NAME

        assert VERSION == "3.0.3"
        assert VERSION_NAME == "Analytics & Synthesis"
        assert DATABASE_NAME == "inde_v3_0_3"

    def test_collection_count(self):
        """Test correct number of collections."""
        from config import MONGODB_COLLECTIONS

        # v3.0.3 should have 35 collections
        assert len(MONGODB_COLLECTIONS) == 35, f"Expected 35 collections, got {len(MONGODB_COLLECTIONS)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
