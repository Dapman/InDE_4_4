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
        from modules.iml.momentum_pattern_engine import MomentumPatternEngine

        mock_db = MagicMock()
        mock_db.momentum_snapshots.find.return_value = []

        engine = MomentumPatternEngine(mock_db)
        result = engine.run_aggregation_cycle()

        assert result["snapshots_processed"] == 0
        assert result["patterns_created"] == 0
        assert result["patterns_updated"] == 0

    def test_pair_snapshots_by_pursuit(self):
        """Snapshots are paired correctly by pursuit."""
        from modules.iml.momentum_pattern_engine import MomentumPatternEngine

        mock_db = MagicMock()
        engine = MomentumPatternEngine(mock_db)

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
        assert pairs[0][0]["session_id"] == "s1"
        assert pairs[0][1]["session_id"] == "s2"

    def test_process_snapshot_pair_bridge_lift(self):
        """Bridge lift pattern is detected when score increases after bridge."""
        from modules.iml.momentum_pattern_engine import MomentumPatternEngine

        mock_db = MagicMock()
        engine = MomentumPatternEngine(mock_db)

        before = {
            "pursuit_id": "p1",
            "composite_score": 0.45,
            "momentum_tier": "MEDIUM",
            "selected_bridge_question_id": "bridge_1",
            "pursuit_stage": "VISION",
        }
        after = {
            "pursuit_id": "p1",
            "composite_score": 0.72,
            "momentum_tier": "HIGH",
            "selected_bridge_question_id": None,
            "pursuit_stage": "VISION",
        }

        pattern = engine._process_snapshot_pair(before, after)

        assert pattern is not None
        assert pattern["pattern_type"] == "BRIDGE_LIFT"
        assert pattern["bridge_id"] == "bridge_1"
        assert pattern["score_delta"] == pytest.approx(0.27, rel=0.01)

    def test_process_snapshot_pair_bridge_stall(self):
        """Bridge stall pattern is detected when score decreases after bridge."""
        from modules.iml.momentum_pattern_engine import MomentumPatternEngine

        mock_db = MagicMock()
        engine = MomentumPatternEngine(mock_db)

        before = {
            "pursuit_id": "p1",
            "composite_score": 0.65,
            "momentum_tier": "MEDIUM",
            "selected_bridge_question_id": "bridge_2",
            "pursuit_stage": "DE_RISK",
        }
        after = {
            "pursuit_id": "p1",
            "composite_score": 0.38,
            "momentum_tier": "LOW",
            "selected_bridge_question_id": None,
            "pursuit_stage": "DE_RISK",
        }

        pattern = engine._process_snapshot_pair(before, after)

        assert pattern is not None
        assert pattern["pattern_type"] == "BRIDGE_STALL"
        assert pattern["bridge_id"] == "bridge_2"


# =============================================================================
# Test: MomentumLiftScorer
# =============================================================================

class TestMomentumLiftScorer:
    """Tests for the IML Momentum Lift Scorer."""

    def test_neutral_score_no_patterns(self):
        """Returns neutral score when no patterns exist."""
        from modules.iml.momentum_lift_scorer import MomentumLiftScorer, NEUTRAL_SCORE

        mock_db = MagicMock()
        mock_db.momentum_patterns.find.return_value = []

        scorer = MomentumLiftScorer(mock_db)
        score = scorer.score_bridge_question(
            bridge_id="test_bridge",
            pursuit_stage="VISION",
            artifact_type="vision",
            momentum_tier="MEDIUM"
        )

        assert score == NEUTRAL_SCORE

    def test_high_lift_pattern_returns_high_score(self):
        """Bridge with lift pattern returns score above neutral."""
        from modules.iml.momentum_lift_scorer import MomentumLiftScorer, NEUTRAL_SCORE

        mock_db = MagicMock()
        # Return a BRIDGE_LIFT pattern with high confidence
        mock_db.momentum_patterns.find.return_value = [
            {
                "pattern_type": "BRIDGE_LIFT",
                "bridge_id": "test_bridge",
                "confidence": 0.85,
                "avg_delta": 0.25,
                "sample_size": 10
            }
        ]

        scorer = MomentumLiftScorer(mock_db)
        score = scorer.score_bridge_question(
            bridge_id="test_bridge",
            pursuit_stage="VISION",
            artifact_type="vision",
            momentum_tier="MEDIUM"
        )

        assert score > NEUTRAL_SCORE
        assert score <= 1.0

    def test_stall_pattern_returns_low_score(self):
        """Bridge with stall pattern returns score below neutral."""
        from modules.iml.momentum_lift_scorer import MomentumLiftScorer, NEUTRAL_SCORE

        mock_db = MagicMock()
        # Return a BRIDGE_STALL pattern
        mock_db.momentum_patterns.find.return_value = [
            {
                "pattern_type": "BRIDGE_STALL",
                "bridge_id": "test_bridge",
                "confidence": 0.75,
                "avg_delta": -0.20,
                "sample_size": 8
            }
        ]

        scorer = MomentumLiftScorer(mock_db)
        score = scorer.score_bridge_question(
            bridge_id="test_bridge",
            pursuit_stage="VISION",
            artifact_type="vision",
            momentum_tier="MEDIUM"
        )

        assert score < NEUTRAL_SCORE
        assert score >= 0.0

    def test_rank_candidates_adds_lift_score(self):
        """rank_candidates adds momentum_lift_score to each candidate."""
        from modules.iml.momentum_lift_scorer import MomentumLiftScorer

        mock_db = MagicMock()
        mock_db.momentum_patterns.find.return_value = []

        scorer = MomentumLiftScorer(mock_db)

        candidates = [
            {"bridge_id": "b1", "base_score": 0.8},
            {"bridge_id": "b2", "base_score": 0.6},
        ]

        ranked = scorer.rank_candidates(
            candidates=candidates,
            pursuit_stage="VISION",
            artifact_type="vision",
            momentum_tier="MEDIUM"
        )

        assert all("momentum_lift_score" in c for c in ranked)


# =============================================================================
# Test: IMLFeedbackReceiver
# =============================================================================

class TestIMLFeedbackReceiver:
    """Tests for the IML Feedback Receiver circuit breaker."""

    def test_initial_state_is_closed(self):
        """Circuit breaker starts in CLOSED state."""
        with patch('momentum.iml_feedback_receiver._get_db', return_value=MagicMock()):
            from momentum.iml_feedback_receiver import IMLFeedbackReceiver, CircuitState

            receiver = IMLFeedbackReceiver()
            assert receiver._circuit_state == CircuitState.CLOSED

    def test_circuit_opens_after_threshold_failures(self):
        """Circuit opens after FAILURE_THRESHOLD consecutive failures."""
        with patch('momentum.iml_feedback_receiver._get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.momentum_patterns.find.side_effect = Exception("DB Error")
            mock_get_db.return_value = mock_db

            from momentum.iml_feedback_receiver import IMLFeedbackReceiver, CircuitState

            receiver = IMLFeedbackReceiver()

            # Call enough times to trip the breaker
            for _ in range(3):  # FAILURE_THRESHOLD = 3
                receiver.get_recommended_bridge(
                    available_bridge_ids=["b1", "b2"],
                    pursuit_stage="VISION",
                    artifact_type="vision",
                    momentum_tier="MEDIUM"
                )

            assert receiver._circuit_state == CircuitState.OPEN

    def test_open_circuit_returns_none(self):
        """Open circuit returns None (fallback to static library)."""
        with patch('momentum.iml_feedback_receiver._get_db', return_value=MagicMock()):
            from momentum.iml_feedback_receiver import IMLFeedbackReceiver, CircuitState

            receiver = IMLFeedbackReceiver()
            receiver._circuit_state = CircuitState.OPEN
            receiver._circuit_opened_at = datetime.now(timezone.utc)

            result = receiver.get_recommended_bridge(
                available_bridge_ids=["b1", "b2"],
                pursuit_stage="VISION",
                artifact_type="vision",
                momentum_tier="MEDIUM"
            )

            assert result is None

    def test_half_open_allows_probe(self):
        """Half-open circuit allows one probe request."""
        with patch('momentum.iml_feedback_receiver._get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.momentum_patterns.find.return_value = []
            mock_get_db.return_value = mock_db

            from momentum.iml_feedback_receiver import IMLFeedbackReceiver, CircuitState

            receiver = IMLFeedbackReceiver()
            receiver._circuit_state = CircuitState.HALF_OPEN

            # Successful probe should close the circuit
            receiver.get_recommended_bridge(
                available_bridge_ids=["b1", "b2"],
                pursuit_stage="VISION",
                artifact_type="vision",
                momentum_tier="MEDIUM"
            )

            assert receiver._circuit_state == CircuitState.CLOSED


# =============================================================================
# Test: MomentumTrajectory
# =============================================================================

class TestMomentumTrajectory:
    """Tests for the Retrospective Momentum Trajectory dimension."""

    def test_insufficient_data_narrative(self):
        """Returns insufficient_data when fewer than 3 snapshots."""
        with patch('modules.retrospective.momentum_trajectory._get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.momentum_snapshots.find.return_value.sort.return_value = [
                {"composite_score": 0.5},
                {"composite_score": 0.6},
            ]
            mock_get_db.return_value = mock_db

            from modules.retrospective.momentum_trajectory import MomentumTrajectory

            trajectory = MomentumTrajectory()
            result = trajectory.generate_for_pursuit(
                pursuit_id="p1",
                pursuit_context={"idea_summary": "test idea"}
            )

            assert result["trajectory_direction"] == "insufficient_data"
            assert result["snapshot_count"] == 2

    def test_rising_trajectory_detection(self):
        """Rising trajectory detected when end score > start score by > 0.1."""
        with patch('modules.retrospective.momentum_trajectory._get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = iter([
                {"composite_score": 0.40},
                {"composite_score": 0.50},
                {"composite_score": 0.55},
                {"composite_score": 0.65},
            ])
            mock_db.momentum_snapshots.find.return_value = mock_cursor
            mock_get_db.return_value = mock_db

            from modules.retrospective.momentum_trajectory import MomentumTrajectory

            trajectory = MomentumTrajectory()
            result = trajectory.generate_for_pursuit(
                pursuit_id="p1",
                pursuit_context={"idea_summary": "test idea"}
            )

            assert result["trajectory_direction"] == "rising"

    def test_declining_trajectory_detection(self):
        """Declining trajectory detected when end score < start score by > 0.1."""
        with patch('modules.retrospective.momentum_trajectory._get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = iter([
                {"composite_score": 0.70},
                {"composite_score": 0.60},
                {"composite_score": 0.55},
                {"composite_score": 0.45},
            ])
            mock_db.momentum_snapshots.find.return_value = mock_cursor
            mock_get_db.return_value = mock_db

            from modules.retrospective.momentum_trajectory import MomentumTrajectory

            trajectory = MomentumTrajectory()
            result = trajectory.generate_for_pursuit(
                pursuit_id="p1",
                pursuit_context={"idea_summary": "test idea"}
            )

            assert result["trajectory_direction"] == "declining"

    def test_turning_point_detection(self):
        """Turning point detected at largest momentum shift."""
        with patch('modules.retrospective.momentum_trajectory._get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = MagicMock()
            # Session 3 (index 2) has the biggest jump: 0.45 -> 0.72 = +0.27
            mock_cursor.sort.return_value = iter([
                {"composite_score": 0.40},
                {"composite_score": 0.45},
                {"composite_score": 0.72},  # Turning point
                {"composite_score": 0.75},
            ])
            mock_db.momentum_snapshots.find.return_value = mock_cursor
            mock_get_db.return_value = mock_db

            from modules.retrospective.momentum_trajectory import MomentumTrajectory

            trajectory = MomentumTrajectory()
            result = trajectory.generate_for_pursuit(
                pursuit_id="p1",
                pursuit_context={"idea_summary": "test idea"}
            )

            assert result["turning_point_session"] == 2  # 0-indexed, shift happens at index 2

    def test_templated_fallback_narrative(self):
        """Templated narrative used when LLM fails."""
        from modules.retrospective.momentum_trajectory import MomentumTrajectory

        trajectory = MomentumTrajectory()
        narrative = trajectory._templated_narrative("rising", "my test idea")

        assert "my test idea" in narrative
        assert "grew consistently stronger" in narrative


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
        assert len(hash1) == 64  # SHA-256 hex

    def test_different_inputs_different_hash(self):
        """Different inputs produce different hashes."""
        from modules.iml.momentum_pattern_persistence import make_context_hash

        hash1 = make_context_hash("VISION", "vision", "MEDIUM")
        hash2 = make_context_hash("DE_RISK", "fear", "HIGH")

        assert hash1 != hash2


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
