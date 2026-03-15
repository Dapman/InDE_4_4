"""
InDE MVP v3.4 - Session 1 Integration Tests
Tests for Phase 1-6 components: Database, RBAC, Audit, Convergence, Methodology.

Run with: pytest tests/test_v34_session1.py -v
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock
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
    db.get_custom_role.return_value = None
    db.get_access_policy.return_value = None
    db.get_convergence_session.return_value = None
    return db


@pytest.fixture
def test_user():
    """Create test user."""
    return {
        "user_id": "user-1",
        "email": "test@example.com",
        "role": "admin"
    }


# =============================================================================
# DATABASE SCHEMA TESTS
# =============================================================================

class TestDatabaseSchema:
    """Test v3.4 database schema additions."""

    def test_v34_collections_defined(self):
        """Verify 8 new v3.4 collections are defined."""
        from core.config import COLLECTIONS

        v34_collections = [
            "audit_events",
            "convergence_sessions",
            "innovator_profiles",
            "vouching_records",
            "formation_recommendations",
            "composition_patterns",
            "custom_roles",
            "access_policies"
        ]

        for collection in v34_collections:
            assert collection in COLLECTIONS, f"Missing collection: {collection}"

    def test_collection_count(self):
        """Verify total collection count is at least 49 (v3.4 base + any legacy)."""
        from core.config import COLLECTIONS
        assert len(COLLECTIONS) >= 49, f"Expected at least 49 collections, got {len(COLLECTIONS)}"


# =============================================================================
# RBAC TESTS
# =============================================================================

class TestRBAC:
    """Test advanced RBAC functionality."""

    def test_builtin_roles_defined(self):
        """Verify built-in roles are defined."""
        from core.config import BUILTIN_ROLE_PERMISSIONS

        assert "admin" in BUILTIN_ROLE_PERMISSIONS
        assert "member" in BUILTIN_ROLE_PERMISSIONS
        assert "viewer" in BUILTIN_ROLE_PERMISSIONS

    def test_defined_permissions(self):
        """Verify all defined permissions exist."""
        from core.config import DEFINED_PERMISSIONS

        expected_permissions = [
            "can_create_pursuits",
            "can_invite_members",
            "can_manage_org_settings",
            "can_review_ikf_contributions",
            "can_view_portfolio_dashboard",
            "can_manage_audit_logs",
            "can_manage_roles",
            "can_manage_retention_policies",
            "can_discover_members"
        ]

        for perm in expected_permissions:
            assert perm in DEFINED_PERMISSIONS, f"Missing permission: {perm}"

    def test_admin_has_all_permissions(self):
        """Verify admin role has all permissions."""
        from core.config import BUILTIN_ROLE_PERMISSIONS, DEFINED_PERMISSIONS

        admin_perms = BUILTIN_ROLE_PERMISSIONS["admin"]
        for perm in DEFINED_PERMISSIONS:
            assert perm in admin_perms, f"Admin missing permission: {perm}"

    def test_role_permission_resolution(self, mock_db):
        """Test get_role_permissions resolves correctly."""
        from middleware.rbac import get_role_permissions

        with patch('middleware.rbac.db', mock_db):  # Uses app/middleware/rbac.py
            # Built-in role
            perms = get_role_permissions("org-1", "admin")
            assert "can_manage_roles" in perms

            # Non-existent custom role
            perms = get_role_permissions("org-1", "custom_role")
            assert perms == []


# =============================================================================
# AUDIT PIPELINE TESTS
# =============================================================================

class TestAuditPipeline:
    """Test audit event functionality."""

    def test_audit_event_types_defined(self):
        """Verify audit event types are defined."""
        from core.config import AUDIT_EVENT_TYPES

        expected_types = [
            "AUTH_LOGIN",
            "AUTH_LOGOUT",
            "AUTH_FAILED",
            "RESOURCE_ACCESS",
            "RESOURCE_CREATE",
            "RESOURCE_UPDATE",
            "RESOURCE_DELETE",
            "PERMISSION_CHANGE",
            "POLICY_CHANGE",
            "CONFIG_CHANGE",
            "DATA_EXPORT",
            "ADMIN_ACTION"
        ]

        for event_type in expected_types:
            assert event_type in AUDIT_EVENT_TYPES, f"Missing event type: {event_type}"

    def test_audit_event_creation(self):
        """Test AuditEvent creation."""
        from events.audit import AuditEvent

        event = AuditEvent(
            event_type="AUTH_LOGIN",
            actor_id="user-1",
            resource_type="session",
            resource_id="login",
            outcome="SUCCESS"
        )

        assert event.event_id is not None
        assert event.event_type == "AUTH_LOGIN"
        assert event.actor_id == "user-1"
        assert event.outcome == "SUCCESS"

    def test_audit_event_to_dict(self):
        """Test AuditEvent serialization."""
        from events.audit import AuditEvent

        event = AuditEvent(
            event_type="RESOURCE_ACCESS",
            actor_id="user-1",
            resource_type="pursuit",
            resource_id="pursuit-1"
        )

        event_dict = event.to_dict()

        assert "event_id" in event_dict
        assert "timestamp" in event_dict
        assert event_dict["event_type"] == "RESOURCE_ACCESS"

    def test_audit_event_from_dict(self):
        """Test AuditEvent deserialization."""
        from events.audit import AuditEvent

        event_dict = {
            "event_id": "test-id",
            "event_type": "AUTH_LOGIN",
            "actor_id": "user-1",
            "resource_type": "session",
            "resource_id": "login",
            "outcome": "SUCCESS",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        event = AuditEvent.from_dict(event_dict)

        assert event.event_id == "test-id"
        assert event.event_type == "AUTH_LOGIN"


# =============================================================================
# CONVERGENCE PROTOCOL TESTS
# =============================================================================

class TestConvergenceProtocol:
    """Test coaching convergence protocol."""

    def test_convergence_phases_defined(self):
        """Verify convergence phases are defined."""
        from core.config import CONVERGENCE_PHASES

        expected_phases = ["EXPLORING", "CONSOLIDATING", "COMMITTED", "HANDED_OFF"]
        for phase in expected_phases:
            assert phase in CONVERGENCE_PHASES, f"Missing phase: {phase}"

    def test_outcome_types_defined(self):
        """Verify convergence outcome types are defined."""
        from core.config import CONVERGENCE_OUTCOME_TYPES

        expected_types = ["DECISION", "INSIGHT", "HYPOTHESIS", "COMMITMENT", "REFINEMENT"]
        for otype in expected_types:
            assert otype in CONVERGENCE_OUTCOME_TYPES, f"Missing outcome type: {otype}"

    def test_signal_detector_initialization(self):
        """Test ConvergenceSignalDetector initialization."""
        from coaching.convergence import ConvergenceSignalDetector

        detector = ConvergenceSignalDetector()

        assert "repetition" in detector.weights
        assert "decision_language" in detector.weights
        assert sum(detector.weights.values()) == pytest.approx(1.0, rel=0.01)

    def test_signal_detection_decision_language(self):
        """Test detection of decision language."""
        from coaching.convergence import ConvergenceSignalDetector

        detector = ConvergenceSignalDetector()
        message = "I've decided to focus on the mobile app first"

        signals = detector.detect_signals(
            message=message,
            conversation_history=[],
            session_start_time=datetime.now(timezone.utc) - timedelta(minutes=30)
        )

        decision_signals = [s for s in signals if s.signal_type == "decision_language"]
        assert len(decision_signals) > 0
        assert decision_signals[0].score > 0.5

    def test_signal_detection_summary_request(self):
        """Test detection of summary requests."""
        from coaching.convergence import ConvergenceSignalDetector

        detector = ConvergenceSignalDetector()
        message = "Can you summarize what we've covered so far?"

        signals = detector.detect_signals(
            message=message,
            conversation_history=[],
            session_start_time=datetime.now(timezone.utc) - timedelta(minutes=30)
        )

        summary_signals = [s for s in signals if s.signal_type == "summary_requests"]
        assert len(summary_signals) > 0

    def test_composite_score_calculation(self):
        """Test composite score calculation."""
        from coaching.convergence import ConvergenceSignalDetector, ConvergenceSignal

        detector = ConvergenceSignalDetector()
        signals = [
            ConvergenceSignal(signal_type="decision_language", score=0.8),
            ConvergenceSignal(signal_type="satisfaction", score=0.7)
        ]

        score = detector.calculate_composite_score(signals)
        assert 0.0 <= score <= 1.0

    def test_state_machine_transitions(self):
        """Test convergence state machine transitions."""
        from coaching.convergence import ConvergenceStateMachine, ConvergencePhase

        machine = ConvergenceStateMachine(
            session_id="test-session",
            pursuit_id="test-pursuit",
            user_id="user-1"
        )

        # Initial state
        assert machine.current_phase == ConvergencePhase.EXPLORING

        # Valid transition
        assert machine.can_transition_to(ConvergencePhase.CONSOLIDATING)
        result = machine.transition_to(ConvergencePhase.CONSOLIDATING, "test")
        assert result is True
        assert machine.current_phase == ConvergencePhase.CONSOLIDATING

        # Invalid transition (skipping phases)
        assert not machine.can_transition_to(ConvergencePhase.HANDED_OFF)


# =============================================================================
# METHODOLOGY ARCHETYPES TESTS
# =============================================================================

class TestMethodologyArchetypes:
    """Test methodology archetype definitions."""

    def test_archetypes_defined(self):
        """Verify all archetypes are defined."""
        from core.config import METHODOLOGY_ARCHETYPES

        expected = ["lean_startup", "design_thinking", "stage_gate", "adhoc", "emergent"]
        for arch in expected:
            assert arch in METHODOLOGY_ARCHETYPES, f"Missing archetype: {arch}"

    def test_get_archetype(self):
        """Test archetype retrieval."""
        from coaching.methodology_archetypes import get_archetype

        lean = get_archetype("lean_startup")
        assert lean is not None
        assert lean.name == "lean_startup"

        design = get_archetype("design_thinking")
        assert design is not None
        assert design.name == "design_thinking"

        stage = get_archetype("stage_gate")
        assert stage is not None
        assert stage.enforcement == "strict"

    def test_design_thinking_phases(self):
        """Test Design Thinking archetype has correct phases."""
        from coaching.methodology_archetypes import get_archetype, get_archetype_phases

        design = get_archetype("design_thinking")
        phases = get_archetype_phases("design_thinking")

        assert "EMPATHIZE" in phases
        assert "DEFINE" in phases
        assert "IDEATE" in phases
        assert "PROTOTYPE" in phases
        assert "TEST" in phases

    def test_stage_gate_enforcement(self):
        """Test Stage-Gate has strict enforcement."""
        from coaching.methodology_archetypes import get_enforcement_mode

        enforcement = get_enforcement_mode("stage_gate")
        assert enforcement == "strict"

    def test_coaching_language_adapter(self):
        """Test coaching language adapter."""
        from coaching.methodology_archetypes import CoachingLanguageAdapter

        # Lean Startup adapter
        lean_adapter = CoachingLanguageAdapter("lean_startup")
        message = lean_adapter.adapt_transition_prompt("test hypotheses")
        assert "hypothesis" in message.lower()

        # Design Thinking adapter
        design_adapter = CoachingLanguageAdapter("design_thinking")
        message = design_adapter.adapt_encouragement("user needs")
        assert "user" in message.lower()

        # Stage-Gate adapter
        stage_adapter = CoachingLanguageAdapter("stage_gate")
        message = stage_adapter.adapt_transition_prompt("proceed to development")
        assert "gate" in message.lower().replace("criteria", "gate")

    def test_transition_criteria(self):
        """Test transition criteria retrieval."""
        from coaching.methodology_archetypes import get_transition_criteria

        # Lean Startup VISION→DE_RISK
        criteria = get_transition_criteria("lean_startup", "VISION", "DE_RISK")
        assert len(criteria) > 0
        assert any(c.criterion_type == "ARTIFACT_EXISTS" for c in criteria)

        # Stage-Gate has COACH_CHECKPOINT requirements
        criteria = get_transition_criteria("stage_gate", "DISCOVERY", "SCOPING")
        assert any(c.criterion_type == "COACH_CHECKPOINT" for c in criteria)


# =============================================================================
# CONFIG VERIFICATION TESTS
# =============================================================================

class TestV34Config:
    """Test v3.4 configuration values."""

    def test_version_info(self):
        """Verify version information is correct."""
        from core.config import VERSION, VERSION_NAME

        assert VERSION == "3.5.1"
        assert "Federation Protocol" in VERSION_NAME

    def test_convergence_config(self):
        """Verify convergence configuration."""
        from core.config import CONVERGENCE_CONFIG

        assert "threshold" in CONVERGENCE_CONFIG
        assert "signal_weights" in CONVERGENCE_CONFIG
        assert 0.0 < CONVERGENCE_CONFIG["threshold"] <= 1.0

    def test_audit_config(self):
        """Verify audit configuration."""
        from core.config import AUDIT_CONFIG

        assert "retention_days" in AUDIT_CONFIG
        assert AUDIT_CONFIG["retention_days"] >= 365  # SOC 2 compliance

    def test_idtfs_config(self):
        """Verify IDTFS configuration."""
        from core.config import IDTFS_CONFIG

        assert "max_candidates" in IDTFS_CONFIG
        assert "pillar_weights" in IDTFS_CONFIG
        assert IDTFS_CONFIG["max_candidates"] >= 10


# =============================================================================
# EVENT SCHEMA TESTS
# =============================================================================

class TestEventSchemas:
    """Test v3.4 event schemas."""

    def test_v34_event_types(self):
        """Verify v3.4 event types are defined."""
        from events.schemas import EVENT_TYPES, EventTypes

        # Convergence events
        assert "convergence.detected" in EVENT_TYPES
        assert "convergence.outcome.captured" in EVENT_TYPES
        assert "convergence.handoff.completed" in EVENT_TYPES

        # Discovery events
        assert "discovery.triggered" in EVENT_TYPES
        assert "discovery.formation.recommended" in EVENT_TYPES

        # Audit events
        assert "audit.event" in EVENT_TYPES

        # Methodology events
        assert "pursuit.methodology.changed" in EVENT_TYPES

    def test_event_type_constants(self):
        """Verify EventTypes constants."""
        from events.schemas import EventTypes

        assert EventTypes.CONVERGENCE_DETECTED == "convergence.detected"
        assert EventTypes.AUDIT_EVENT == "audit.event"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
