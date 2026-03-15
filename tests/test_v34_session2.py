"""
InDE MVP v3.4 - Session 2 Integration Tests
Tests for Phase 8-12 components: IDTFS, Formation, Portfolio Dashboard, ODICM.

Run with: pytest tests/test_v34_session2.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import uuid


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    """Create mock database instance."""
    db = MagicMock()
    db.get_user_membership_in_org.return_value = {
        "user_id": "user-1",
        "org_id": "org-1",
        "role": "admin",
        "status": "active",
        "permissions": {}
    }
    db.get_org_innovator_profiles.return_value = []
    db.get_org_vouching_records.return_value = []
    db.get_org_formation_recommendations.return_value = []
    db.get_pursuits_by_org.return_value = []
    db.get_pursuit.return_value = None
    db.get_user.return_value = {"user_id": "user-1", "display_name": "Test User"}
    return db


@pytest.fixture
def test_user():
    """Create test user."""
    return {
        "user_id": "user-1",
        "email": "test@example.com",
        "role": "admin"
    }


@pytest.fixture
def test_org():
    """Create test organization."""
    return {
        "org_id": "org-1",
        "name": "Test Organization"
    }


@pytest.fixture
def test_pursuit():
    """Create test pursuit."""
    return {
        "pursuit_id": "pursuit-1",
        "name": "Test Innovation",
        "org_id": "org-1",
        "user_id": "user-1",
        "methodology_archetype": "lean_startup",
        "current_stage": "VISION",
        "health_score": 0.75,
        "status": "active",
        "sharing": {"team_members": []}
    }


# =============================================================================
# IDTFS CORE TESTS (Phase 8)
# =============================================================================

class TestIDTFSCore:
    """Test IDTFS core components (Pillars 1-4, 6)."""

    def test_profile_manager_initialization(self):
        """Test InnovatorProfileManager initialization."""
        from discovery.idtfs import InnovatorProfileManager

        manager = InnovatorProfileManager()
        assert manager is not None

    def test_availability_status_enum(self):
        """Test AvailabilityStatus enum values."""
        from discovery.idtfs import AvailabilityStatus

        assert AvailabilityStatus.FULL_TIME.value == "FULL_TIME"
        assert AvailabilityStatus.PART_TIME.value == "PART_TIME"
        assert AvailabilityStatus.LIMITED.value == "LIMITED"
        assert AvailabilityStatus.UNAVAILABLE.value == "UNAVAILABLE"

    def test_vouching_type_enum(self):
        """Test VouchingType enum values."""
        from discovery.idtfs import VouchingType

        assert VouchingType.EXPERTISE.value == "EXPERTISE"
        assert VouchingType.CHARACTER.value == "CHARACTER"
        assert VouchingType.COLLABORATION.value == "COLLABORATION"
        assert VouchingType.DELIVERY.value == "DELIVERY"

    def test_expertise_type_enum(self):
        """Test ExpertiseType enum values."""
        from discovery.idtfs import ExpertiseType

        expected_types = ["DOMAIN", "TECHNICAL", "CREATIVE", "ANALYTICAL",
                         "CONNECTOR", "EXECUTOR", "MENTOR", "VISIONARY"]
        for etype in expected_types:
            assert hasattr(ExpertiseType, etype)

    def test_expertise_calculator_initialization(self):
        """Test BehavioralExpertiseCalculator initialization."""
        from discovery.idtfs import BehavioralExpertiseCalculator

        calculator = BehavioralExpertiseCalculator()
        assert calculator is not None
        assert hasattr(calculator, "evidence_weights")

    def test_expertise_matcher_initialization(self):
        """Test ExpertiseTypeMatcher initialization."""
        from discovery.idtfs import ExpertiseTypeMatcher

        matcher = ExpertiseTypeMatcher()
        assert matcher is not None

    def test_discovery_query_initialization(self):
        """Test DiscoveryQuery initialization."""
        from discovery.idtfs import DiscoveryQuery

        query = DiscoveryQuery()
        assert query is not None

    def test_singleton_accessors(self):
        """Test IDTFS singleton accessors."""
        from discovery.idtfs import (
            get_profile_manager, get_vouching_service,
            get_expertise_calculator, get_expertise_matcher, get_discovery_query
        )

        assert get_profile_manager() is not None
        assert get_vouching_service() is not None
        assert get_expertise_calculator() is not None
        assert get_expertise_matcher() is not None
        assert get_discovery_query() is not None


# =============================================================================
# IDTFS INTELLIGENCE TESTS (Phase 9)
# =============================================================================

class TestIDTFSIntelligence:
    """Test IDTFS intelligence components (Pillar 5 + Formation)."""

    def test_pattern_type_enum(self):
        """Test PatternType enum values."""
        from discovery.formation import PatternType

        expected_types = ["EXPERTISE_MIX", "ROLE_BALANCE", "COGNITIVE_DIVERSITY",
                         "EXPERIENCE_BLEND", "COLLABORATION_HISTORY"]
        for ptype in expected_types:
            assert hasattr(PatternType, ptype)

    def test_formation_status_enum(self):
        """Test FormationStatus enum values."""
        from discovery.formation import FormationStatus

        expected_statuses = ["DRAFT", "PROPOSED", "ACCEPTED", "REJECTED",
                            "IN_PROGRESS", "COMPLETED"]
        for status in expected_statuses:
            assert hasattr(FormationStatus, status)

    def test_gap_severity_enum(self):
        """Test GapSeverity enum values."""
        from discovery.formation import GapSeverity

        assert GapSeverity.CRITICAL.value == "CRITICAL"
        assert GapSeverity.SIGNIFICANT.value == "SIGNIFICANT"
        assert GapSeverity.MODERATE.value == "MODERATE"
        assert GapSeverity.MINOR.value == "MINOR"

    def test_pattern_analyzer_initialization(self):
        """Test CompositionPatternAnalyzer initialization."""
        from discovery.formation import CompositionPatternAnalyzer

        analyzer = CompositionPatternAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, "pattern_weights")

    def test_gap_analyzer_initialization(self):
        """Test GapAnalyzer initialization."""
        from discovery.formation import GapAnalyzer

        analyzer = GapAnalyzer()
        assert analyzer is not None

    def test_formation_orchestrator_initialization(self):
        """Test FormationFlowOrchestrator initialization."""
        from discovery.formation import FormationFlowOrchestrator

        orchestrator = FormationFlowOrchestrator()
        assert orchestrator is not None
        assert hasattr(orchestrator, "pattern_analyzer")
        assert hasattr(orchestrator, "gap_analyzer")

    def test_composition_pattern_to_dict(self):
        """Test CompositionPattern serialization."""
        from discovery.formation import CompositionPattern, PatternType

        pattern = CompositionPattern(
            pattern_id="test-pattern",
            pattern_type=PatternType.EXPERTISE_MIX,
            org_id="org-1",
            pattern_data={"recommended_tags": ["python", "ml"]},
            effectiveness_score=0.8,
            sample_size=10,
            confidence=0.9
        )

        pattern_dict = pattern.to_dict()

        assert pattern_dict["pattern_id"] == "test-pattern"
        assert pattern_dict["pattern_type"] == "EXPERTISE_MIX"
        assert pattern_dict["effectiveness_score"] == 0.8

    def test_formation_recommendation_to_dict(self):
        """Test FormationRecommendation serialization."""
        from discovery.formation import FormationRecommendation, FormationStatus

        rec = FormationRecommendation(
            recommendation_id="rec-1",
            pursuit_id="pursuit-1",
            org_id="org-1",
            gap_id="gap-1",
            recommended_members=[{"user_id": "user-2"}],
            rationale="Test rationale",
            composition_score=0.75,
            pattern_matches=["EXPERTISE_MIX"],
            status=FormationStatus.PROPOSED,
            created_by="user-1"
        )

        rec_dict = rec.to_dict()

        assert rec_dict["recommendation_id"] == "rec-1"
        assert rec_dict["status"] == "PROPOSED"
        assert len(rec_dict["recommended_members"]) == 1


# =============================================================================
# PORTFOLIO DASHBOARD TESTS (Phase 10)
# =============================================================================

class TestPortfolioDashboard:
    """Test org-level portfolio dashboard."""

    def test_panel_type_enum(self):
        """Test PanelType enum values."""
        from portfolio.dashboard import PanelType

        expected_panels = [
            "portfolio_health", "stage_distribution", "resource_allocation",
            "innovation_pipeline", "risk_radar", "convergence_insights", "talent_formation"
        ]

        for panel in expected_panels:
            assert hasattr(PanelType, panel.upper().replace("_", "_"))

    def test_health_level_enum(self):
        """Test HealthLevel enum values."""
        from portfolio.dashboard import HealthLevel

        assert HealthLevel.EXCELLENT.value == "excellent"
        assert HealthLevel.GOOD.value == "good"
        assert HealthLevel.AT_RISK.value == "at_risk"
        assert HealthLevel.CRITICAL.value == "critical"

    def test_dashboard_initialization(self):
        """Test PortfolioDashboard initialization."""
        from portfolio.dashboard import PortfolioDashboard

        dashboard = PortfolioDashboard()
        assert dashboard is not None
        assert hasattr(dashboard, "_cache")

    def test_dashboard_panel_dataclass(self):
        """Test DashboardPanel dataclass."""
        from portfolio.dashboard import DashboardPanel, PanelType

        panel = DashboardPanel(
            panel_type=PanelType.PORTFOLIO_HEALTH,
            title="Test Panel",
            data={"test": "data"}
        )

        assert panel.panel_type == PanelType.PORTFOLIO_HEALTH
        assert panel.title == "Test Panel"
        assert panel.cache_duration_seconds == 300

    def test_dashboard_panel_to_dict(self):
        """Test DashboardPanel serialization."""
        from portfolio.dashboard import DashboardPanel, PanelType

        panel = DashboardPanel(
            panel_type=PanelType.RISK_RADAR,
            title="Risk Radar",
            data={"risk_score": 0.85}
        )

        panel_dict = panel.to_dict()

        assert panel_dict["panel_type"] == "risk_radar"
        assert panel_dict["title"] == "Risk Radar"
        assert "updated_at" in panel_dict

    def test_portfolio_health_metrics_to_dict(self):
        """Test PortfolioHealthMetrics serialization."""
        from portfolio.dashboard import PortfolioHealthMetrics

        metrics = PortfolioHealthMetrics(
            total_pursuits=10,
            active_pursuits=7,
            average_health_score=0.72,
            health_distribution={"excellent": 3, "good": 4, "at_risk": 2, "critical": 1},
            trending_up=4,
            trending_down=2,
            stalled_pursuits=1
        )

        metrics_dict = metrics.to_dict()

        assert metrics_dict["total_pursuits"] == 10
        assert metrics_dict["average_health_score"] == 0.72
        assert metrics_dict["health_distribution"]["excellent"] == 3


# =============================================================================
# ODICM EXTENSIONS TESTS (Phase 11)
# =============================================================================

class TestODICMExtensions:
    """Test ODICM extensions."""

    def test_coaching_mode_enum(self):
        """Test CoachingMode enum values."""
        from coaching.odicm_extensions import CoachingMode

        assert CoachingMode.EXPLORATORY.value == "exploratory"
        assert CoachingMode.CONVERGENT.value == "convergent"
        assert CoachingMode.DIRECTIVE.value == "directive"
        assert CoachingMode.REFLECTIVE.value == "reflective"

    def test_context_source_enum(self):
        """Test ContextSource enum values."""
        from coaching.odicm_extensions import ContextSource

        expected_sources = ["PURSUIT", "CONVERSATION", "PORTFOLIO",
                           "ORGANIZATION", "METHODOLOGY"]
        for source in expected_sources:
            assert hasattr(ContextSource, source)

    def test_convergence_coach_initialization(self):
        """Test ConvergenceAwareCoach initialization."""
        from coaching.odicm_extensions import ConvergenceAwareCoach

        coach = ConvergenceAwareCoach()
        assert coach is not None
        assert hasattr(coach, "signal_detector")
        assert hasattr(coach, "convergence_threshold")

    def test_org_intelligence_initialization(self):
        """Test OrgIntelligenceProvider initialization."""
        from coaching.odicm_extensions import OrgIntelligenceProvider

        provider = OrgIntelligenceProvider()
        assert provider is not None
        assert hasattr(provider, "_cache")

    def test_coaching_context_to_dict(self):
        """Test CoachingContext serialization."""
        from coaching.odicm_extensions import CoachingContext, CoachingMode
        from coaching.convergence import ConvergencePhase

        context = CoachingContext(
            pursuit_id="pursuit-1",
            user_id="user-1",
            org_id="org-1",
            methodology_archetype="lean_startup",
            current_phase=ConvergencePhase.EXPLORING,
            coaching_mode=CoachingMode.EXPLORATORY,
            convergence_signals=[],
            portfolio_context={},
            methodology_guidance={},
            recent_outcomes=[]
        )

        context_dict = context.to_dict()

        assert context_dict["pursuit_id"] == "pursuit-1"
        assert context_dict["current_phase"] == "EXPLORING"
        assert context_dict["coaching_mode"] == "exploratory"

    def test_enhanced_response_to_dict(self):
        """Test EnhancedCoachingResponse serialization."""
        from coaching.odicm_extensions import EnhancedCoachingResponse, CoachingMode
        from coaching.convergence import ConvergencePhase

        response = EnhancedCoachingResponse(
            message="Test response",
            coaching_mode=CoachingMode.CONVERGENT,
            convergence_phase=ConvergencePhase.CONSOLIDATING,
            suggested_actions=["Action 1", "Action 2"],
            methodology_hints=["Hint 1"],
            convergence_prompt="Ready to converge?",
            portfolio_insights=None
        )

        response_dict = response.to_dict()

        assert response_dict["message"] == "Test response"
        assert response_dict["coaching_mode"] == "convergent"
        assert len(response_dict["suggested_actions"]) == 2


# =============================================================================
# UI EXTENSIONS TESTS (Phase 12)
# =============================================================================

class TestUIExtensions:
    """Test UI extensions."""

    def test_convergence_panel_initialization(self, mock_db):
        """Test ConvergencePanel initialization."""
        from ui.v34_extensions import ConvergencePanel

        panel = ConvergencePanel(db=mock_db)
        assert panel is not None

    def test_discovery_panel_initialization(self, mock_db):
        """Test DiscoveryPanel initialization."""
        from ui.v34_extensions import DiscoveryPanel

        panel = DiscoveryPanel(db=mock_db)
        assert panel is not None

    def test_org_dashboard_panel_initialization(self, mock_db):
        """Test OrgDashboardPanel initialization."""
        from ui.v34_extensions import OrgDashboardPanel

        panel = OrgDashboardPanel(db=mock_db)
        assert panel is not None

    def test_methodology_panel_initialization(self, mock_db):
        """Test MethodologyPanel initialization."""
        from ui.v34_extensions import MethodologyPanel

        panel = MethodologyPanel(db=mock_db)
        assert panel is not None

    def test_create_v34_ui_components(self, mock_db):
        """Test create_v34_ui_components factory function."""
        from ui.v34_extensions import create_v34_ui_components

        components = create_v34_ui_components(db=mock_db)

        assert "convergence" in components
        assert "discovery" in components
        assert "org_dashboard" in components
        assert "methodology" in components

    def test_convergence_panel_no_session(self, mock_db):
        """Test ConvergencePanel with no session."""
        from ui.v34_extensions import ConvergencePanel

        panel = ConvergencePanel(db=mock_db)
        status = panel.get_convergence_status("")

        assert "No active coaching session" in status

    def test_discovery_panel_no_org(self, mock_db):
        """Test DiscoveryPanel with no org."""
        from ui.v34_extensions import DiscoveryPanel

        panel = DiscoveryPanel(db=mock_db)
        overview = panel.get_discovery_overview("")

        assert "Organization context required" in overview

    def test_methodology_panel_no_pursuit(self, mock_db):
        """Test MethodologyPanel with no pursuit."""
        from ui.v34_extensions import MethodologyPanel

        panel = MethodologyPanel(db=mock_db)
        status = panel.get_methodology_status("")

        assert "Pursuit context required" in status


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestV34Integration:
    """Integration tests for v3.4 components working together."""

    def test_idtfs_to_formation_flow(self, mock_db):
        """Test IDTFS discovery leading to formation recommendation."""
        from discovery.idtfs import get_discovery_query
        from discovery.formation import get_formation_orchestrator

        # Both should be accessible
        query = get_discovery_query()
        orchestrator = get_formation_orchestrator()

        assert query is not None
        assert orchestrator is not None
        # Orchestrator should have access to pattern analyzer
        assert hasattr(orchestrator, "pattern_analyzer")

    def test_convergence_to_odicm_flow(self):
        """Test convergence integration with ODICM."""
        from coaching.convergence import get_convergence_orchestrator
        from coaching.odicm_extensions import get_convergence_coach

        orchestrator = get_convergence_orchestrator()
        coach = get_convergence_coach()

        assert orchestrator is not None
        assert coach is not None
        # Coach should use signal detector
        assert hasattr(coach, "signal_detector")

    def test_portfolio_dashboard_panels(self):
        """Test all 7 portfolio dashboard panels exist."""
        from portfolio.dashboard import PanelType

        expected_panels = [
            PanelType.PORTFOLIO_HEALTH,
            PanelType.STAGE_DISTRIBUTION,
            PanelType.RESOURCE_ALLOCATION,
            PanelType.INNOVATION_PIPELINE,
            PanelType.RISK_RADAR,
            PanelType.CONVERGENCE_INSIGHTS,
            PanelType.TALENT_FORMATION
        ]

        assert len(expected_panels) == 7

    def test_methodology_archetype_integration(self):
        """Test methodology archetypes work with ODICM."""
        from coaching.methodology_archetypes import (
            get_archetype, CoachingLanguageAdapter
        )
        from coaching.odicm_extensions import ConvergenceAwareCoach

        # Get archetype
        lean = get_archetype("lean_startup")
        assert lean is not None

        # Create adapter
        adapter = CoachingLanguageAdapter("lean_startup")
        assert adapter is not None

        # Coach should be able to use methodology
        coach = ConvergenceAwareCoach()
        assert coach is not None


# =============================================================================
# CONFIG VERIFICATION TESTS
# =============================================================================

class TestV34ConfigComplete:
    """Verify all v3.4 configuration is complete."""

    def test_idtfs_config(self):
        """Verify IDTFS configuration."""
        from core.config import IDTFS_CONFIG

        assert "max_candidates" in IDTFS_CONFIG
        assert "pillar_weights" in IDTFS_CONFIG
        assert IDTFS_CONFIG["max_candidates"] >= 10

    def test_convergence_config(self):
        """Verify convergence configuration."""
        from core.config import CONVERGENCE_CONFIG

        assert "threshold" in CONVERGENCE_CONFIG
        assert "signal_weights" in CONVERGENCE_CONFIG

    def test_methodology_archetypes_config(self):
        """Verify methodology archetypes configuration."""
        from core.config import METHODOLOGY_ARCHETYPES

        expected = ["lean_startup", "design_thinking", "stage_gate", "adhoc", "emergent"]
        for arch in expected:
            assert arch in METHODOLOGY_ARCHETYPES

    def test_audit_config(self):
        """Verify audit configuration."""
        from core.config import AUDIT_CONFIG

        assert "retention_days" in AUDIT_CONFIG
        assert AUDIT_CONFIG["retention_days"] >= 365

    def test_rbac_config(self):
        """Verify RBAC configuration."""
        from core.config import BUILTIN_ROLE_PERMISSIONS, DEFINED_PERMISSIONS

        assert "admin" in BUILTIN_ROLE_PERMISSIONS
        assert "member" in BUILTIN_ROLE_PERMISSIONS
        assert "viewer" in BUILTIN_ROLE_PERMISSIONS
        assert len(DEFINED_PERMISSIONS) >= 9


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
