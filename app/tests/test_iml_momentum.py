"""
InDE MVP v4.4.0 - IML Momentum Tests

Unit tests for the IML Momentum Learning features:
- MomentumPatternEngine.run_aggregation_cycle()
- MomentumLiftScorer.score_bridge_question()
- IMLFeedbackReceiver circuit breaker logic
- MomentumTrajectory.generate_for_pursuit()

2026 Yul Williams | InDEVerse, Incorporated
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone


# =============================================================================
# Test: MomentumPatternEngine
# =============================================================================

class TestMomentumPatternEngine:
    """Tests for the IML Momentum Pattern Engine."""

    def test_aggregation_cycle_empty_database(self):
        """Aggregation with no snapshots returns zero counts."""
        with patch('modules.iml.momentum_pattern_engine._get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.momentum_snapshots.find.return_value = []
            mock_get_db.return_value = mock_db

            from modules.iml.momentum_pattern_engine import MomentumPatternEngine

            engine = MomentumPatternEngine()
            result = engine.run_aggregation_cycle()

            assert result["processed"] == 0
            assert result["patterns_created"] == 0
            assert result["patterns_updated"] == 0

    def test_pair_snapshots_by_pursuit(self):
        """Snapshots are paired correctly by pursuit."""
        with patch('modules.iml.momentum_pattern_engine._get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            from modules.iml.momentum_pattern_engine import MomentumPatternEngine

            engine = MomentumPatternEngine()

            # Two snapshots for same pursuit
            snapshots = [
                {
                    "pursuit_id": "p1",
                    "session_id": "s1",
                    "composite_score": 0.5,
                    "momentum_tier": "MEDIUM",
                    "selected_bridge_question_id": "bridge_1",
                    "pursuit_stage": "VISION",
                    "recorded_at": datetime.now(timezone.utc) - timedelta(hours=2)
                },
                {
                    "pursuit_id": "p1",
                    "session_id": "s2",
                    "composite_score": 0.7,
                    "momentum_tier": "HIGH",
                    "selected_bridge_question_id": None,
                    "pursuit_stage": "VISION",
                    "recorded_at": datetime.now(timezone.utc) - timedelta(hours=1)
                },
            ]

            pairs = engine._pair_snapshots_by_pursuit(snapshots)

            assert len(pairs) == 1
            assert pairs[0]["before"]["session_id"] == "s1"
            assert pairs[0]["after"]["session_id"] == "s2"


# =============================================================================
# Test: MomentumLiftScorer
# =============================================================================

class TestMomentumLiftScorer:
    """Tests for the IML Momentum Lift Scorer."""

    def test_neutral_score_no_patterns(self):
        """Returns neutral score when no patterns exist."""
        with patch('modules.iml.momentum_lift_scorer.get_patterns_for_context') as mock_get_patterns:
            mock_get_patterns.return_value = []

            from modules.iml.momentum_lift_scorer import MomentumLiftScorer, NEUTRAL_SCORE

            scorer = MomentumLiftScorer()
            score = scorer.score_bridge_question(
                bridge_question_id="test_bridge",
                pursuit_stage="VISION",
                artifact_type="vision",
                momentum_tier="MEDIUM"
            )

            assert score == NEUTRAL_SCORE

    def test_rank_candidates_returns_list(self):
        """rank_candidates returns a list of candidates."""
        with patch('modules.iml.momentum_lift_scorer.get_patterns_for_context') as mock_get_patterns:
            mock_get_patterns.return_value = []

            from modules.iml.momentum_lift_scorer import MomentumLiftScorer

            scorer = MomentumLiftScorer()

            candidates = [
                {"id": "b1", "base_score": 0.8},
                {"id": "b2", "base_score": 0.6},
            ]

            context = {
                "pursuit_stage": "VISION",
                "artifact_type": "vision",
                "momentum_tier": "MEDIUM",
            }

            ranked = scorer.rank_candidates(candidates, context, candidate_type="bridge")

            assert isinstance(ranked, list)
            assert len(ranked) == 2


# =============================================================================
# Test: IMLFeedbackReceiver
# =============================================================================

class TestIMLFeedbackReceiver:
    """Tests for the IML Feedback Receiver circuit breaker."""

    def test_initial_state_is_closed(self):
        """Circuit breaker starts in CLOSED state."""
        with patch.dict('sys.modules', {'modules.iml.momentum_lift_scorer': MagicMock()}):
            # Need to reimport to get fresh module
            import importlib
            import momentum.iml_feedback_receiver as receiver_module
            importlib.reload(receiver_module)

            from momentum.iml_feedback_receiver import IMLFeedbackReceiver, CircuitState

            receiver = IMLFeedbackReceiver()
            assert receiver._circuit_state == CircuitState.CLOSED

    def test_returns_none_when_iml_unavailable(self):
        """Returns None when IML module is not available."""
        # Simulate IML not being available
        with patch('momentum.iml_feedback_receiver.IML_AVAILABLE', False):
            from momentum.iml_feedback_receiver import IMLFeedbackReceiver

            receiver = IMLFeedbackReceiver()
            receiver._scorer = None  # Simulate no scorer

            result = receiver.get_recommended_bridge(
                available_bridge_ids=["b1", "b2"],
                pursuit_stage="VISION",
                artifact_type="vision",
                momentum_tier="MEDIUM"
            )

            assert result is None


# =============================================================================
# Test: MomentumTrajectory
# =============================================================================

class TestMomentumTrajectory:
    """Tests for the Retrospective Momentum Trajectory dimension."""

    def test_insufficient_data_with_empty_db(self):
        """Returns insufficient_data when no snapshots exist."""
        with patch('modules.retrospective.momentum_trajectory._get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = iter([])
            mock_db.momentum_snapshots.find.return_value = mock_cursor
            mock_get_db.return_value = mock_db

            from modules.retrospective.momentum_trajectory import MomentumTrajectory

            trajectory = MomentumTrajectory()
            result = trajectory.generate_for_pursuit(
                pursuit_id="p1",
                pursuit_context={"idea_summary": "test idea"}
            )

            assert result["trajectory_direction"] == "insufficient_data"
            assert result["snapshot_count"] == 0

    def test_templated_fallback_narrative_rising(self):
        """Templated narrative for rising trajectory includes idea summary."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        narrative = trajectory._templated_narrative("rising", "my test idea")

        assert "my test idea" in narrative
        assert "grew consistently stronger" in narrative

    def test_templated_fallback_narrative_declining(self):
        """Templated narrative for declining trajectory is constructive."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        narrative = trajectory._templated_narrative("declining", "my project")

        assert "my project" in narrative
        assert "started with real momentum" in narrative

    def test_templated_fallback_narrative_stable(self):
        """Templated narrative for stable trajectory emphasizes consistency."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        narrative = trajectory._templated_narrative("stable", "my idea")

        assert "my idea" in narrative
        assert "consistent energy" in narrative

    def test_templated_fallback_narrative_mixed(self):
        """Templated narrative for mixed trajectory highlights peaks."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        narrative = trajectory._templated_narrative("mixed", "my concept")

        assert "my concept" in narrative
        assert "real peaks" in narrative

    def test_minimal_narrative(self):
        """Minimal narrative for new pursuits."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        narrative = trajectory._minimal_narrative({"idea_summary": "new idea"})

        assert "new idea" in narrative
        assert "just getting started" in narrative

    def test_compute_direction_rising(self):
        """Rising direction detected when end > start by > 0.1."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        snapshots = [
            {"composite_score": 0.40},
            {"composite_score": 0.55},
            {"composite_score": 0.65},
        ]

        direction = trajectory._compute_direction(snapshots)
        assert direction == "rising"

    def test_compute_direction_declining(self):
        """Declining direction detected when end < start by > 0.1."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        snapshots = [
            {"composite_score": 0.70},
            {"composite_score": 0.55},
            {"composite_score": 0.45},
        ]

        direction = trajectory._compute_direction(snapshots)
        assert direction == "declining"

    def test_compute_direction_stable(self):
        """Stable direction when change is within threshold."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        snapshots = [
            {"composite_score": 0.50},
            {"composite_score": 0.52},
            {"composite_score": 0.55},
        ]

        direction = trajectory._compute_direction(snapshots)
        assert direction == "stable"

    def test_compute_direction_mixed(self):
        """Mixed direction when variance is high."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        snapshots = [
            {"composite_score": 0.30},
            {"composite_score": 0.80},
            {"composite_score": 0.35},
        ]

        direction = trajectory._compute_direction(snapshots)
        assert direction == "mixed"

    def test_find_turning_point(self):
        """Turning point detected at largest shift."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        # Session index 2 has biggest jump: 0.45 -> 0.72 = +0.27
        snapshots = [
            {"composite_score": 0.40},
            {"composite_score": 0.45},
            {"composite_score": 0.72},  # Turning point (index 2)
            {"composite_score": 0.75},
        ]

        turning_point = trajectory._find_turning_point(snapshots)
        assert turning_point == 2

    def test_find_turning_point_none_when_no_significant_shift(self):
        """No turning point when all shifts are small."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        snapshots = [
            {"composite_score": 0.50},
            {"composite_score": 0.55},
            {"composite_score": 0.58},
            {"composite_score": 0.60},
        ]

        turning_point = trajectory._find_turning_point(snapshots)
        assert turning_point is None


# =============================================================================
# Test: Context Hash Generation
# =============================================================================

class TestContextHash:
    """Tests for context fingerprint generation."""

    def test_deterministic_hash(self):
        """Same inputs produce same hash."""
        from modules.iml.momentum_pattern_persistence import make_context_hash

        hash1 = make_context_hash("VISION", "vision", "MEDIUM")
        hash2 = make_context_hash("VISION", "vision", "MEDIUM")

        assert hash1 == hash2
        assert len(hash1) > 0  # Hash has some length

    def test_different_inputs_different_hash(self):
        """Different inputs produce different hashes."""
        from modules.iml.momentum_pattern_persistence import make_context_hash

        hash1 = make_context_hash("VISION", "vision", "MEDIUM")
        hash2 = make_context_hash("DE_RISK", "fear", "HIGH")

        assert hash1 != hash2


# =============================================================================
# Test: MomentumPatternType Enum
# =============================================================================

class TestMomentumPatternType:
    """Tests for the MomentumPatternType enum."""

    def test_pattern_types_exist(self):
        """All expected pattern types exist."""
        from modules.iml.momentum_pattern_persistence import MomentumPatternType

        assert hasattr(MomentumPatternType, 'BRIDGE_LIFT')
        assert hasattr(MomentumPatternType, 'BRIDGE_STALL')
        assert hasattr(MomentumPatternType, 'INSIGHT_LIFT')
        assert hasattr(MomentumPatternType, 'INSIGHT_STALL')


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
