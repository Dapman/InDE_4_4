"""
InDE v3.7.2 - EMS Pattern Inference Engine Tests

Tests the pattern inference engine, ADL generator, and related components.
Verifies the 4 inference algorithms, confidence scoring, and ADL generation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from typing import Dict, List


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_observations():
    """Create mock observation data for testing."""
    base_time = datetime.now(timezone.utc)

    return [
        {
            "pursuit_id": "pursuit_1",
            "innovator_id": "innovator_test",
            "observation_type": "ARTIFACT_CREATED",
            "timestamp": base_time - timedelta(days=5, hours=3),
            "sequence_number": 1,
            "details": {"artifact_type": "vision"},
            "context": {"pursuit_phase": "IDEATION"},
            "signal_weight": 0.8,
            "is_external_influence": False,
        },
        {
            "pursuit_id": "pursuit_1",
            "innovator_id": "innovator_test",
            "observation_type": "TOOL_INVOKED",
            "timestamp": base_time - timedelta(days=5, hours=2),
            "sequence_number": 2,
            "details": {"tool_name": "risk_detector"},
            "context": {"pursuit_phase": "IDEATION"},
            "signal_weight": 0.7,
            "is_external_influence": False,
        },
        {
            "pursuit_id": "pursuit_1",
            "innovator_id": "innovator_test",
            "observation_type": "DECISION_MADE",
            "timestamp": base_time - timedelta(days=5, hours=1),
            "sequence_number": 3,
            "details": {"decision_type": "pivot"},
            "context": {"pursuit_phase": "VALIDATION"},
            "signal_weight": 0.9,
            "is_external_influence": False,
        },
        {
            "pursuit_id": "pursuit_1",
            "innovator_id": "innovator_test",
            "observation_type": "ARTIFACT_CREATED",
            "timestamp": base_time - timedelta(days=4),
            "sequence_number": 4,
            "details": {"artifact_type": "hypothesis"},
            "context": {"pursuit_phase": "VALIDATION"},
            "signal_weight": 0.8,
            "is_external_influence": False,
        },
    ]


@pytest.fixture
def mock_pursuits():
    """Create mock pursuit data for testing."""
    return [
        {
            "pursuit_id": "pursuit_1",
            "user_id": "innovator_test",
            "name": "Test Pursuit 1",
            "archetype": "ad_hoc",
            "status": "COMPLETED.SUCCESSFUL",
            "created_at": datetime.now(timezone.utc) - timedelta(days=10),
            "adhoc_metadata": {
                "observation_status": "COMPLETED",
                "observation_count": 4,
            },
        },
        {
            "pursuit_id": "pursuit_2",
            "user_id": "innovator_test",
            "name": "Test Pursuit 2",
            "archetype": "ad_hoc",
            "status": "COMPLETED.SUCCESSFUL",
            "created_at": datetime.now(timezone.utc) - timedelta(days=5),
            "adhoc_metadata": {
                "observation_status": "COMPLETED",
                "observation_count": 5,
            },
        },
        {
            "pursuit_id": "pursuit_3",
            "user_id": "innovator_test",
            "name": "Test Pursuit 3",
            "archetype": "ad_hoc",
            "status": "COMPLETED.SUCCESSFUL",
            "created_at": datetime.now(timezone.utc) - timedelta(days=2),
            "adhoc_metadata": {
                "observation_status": "COMPLETED",
                "observation_count": 6,
            },
        },
    ]


# =============================================================================
# INFERENCE DATA PREP TESTS
# =============================================================================

class TestInferenceDataPrep:
    """Tests for InferenceDataPrep class."""

    def test_build_activity_sequence_basic(self):
        """Test basic activity sequence building."""
        from ems.inference_data_prep import InferenceDataPrep

        prep = InferenceDataPrep()

        observations = [
            {"observation_type": "ARTIFACT_CREATED", "details": {}},
            {"observation_type": "TOOL_INVOKED", "details": {}},
            {"observation_type": "DECISION_MADE", "details": {}},
        ]

        sequence = prep.build_activity_sequence(observations, enrich=False)

        assert len(sequence) == 3
        assert sequence[0] == "ARTIFACT_CREATED"
        assert sequence[1] == "TOOL_INVOKED"
        assert sequence[2] == "DECISION_MADE"

    def test_build_activity_sequence_enriched(self):
        """Test enriched activity sequence building."""
        from ems.inference_data_prep import InferenceDataPrep

        prep = InferenceDataPrep()

        observations = [
            {"observation_type": "ARTIFACT_CREATED", "details": {"artifact_type": "vision"}},
            {"observation_type": "TOOL_INVOKED", "details": {"tool_name": "risk_detector"}},
        ]

        sequence = prep.build_activity_sequence(observations, enrich=True)

        assert len(sequence) == 2
        assert sequence[0] == "ARTIFACT_CREATED:vision"
        assert sequence[1] == "TOOL_INVOKED:risk_detector"

    def test_calculate_temporal_features_empty(self):
        """Test temporal features with empty observations."""
        from ems.inference_data_prep import InferenceDataPrep

        prep = InferenceDataPrep()
        features = prep.calculate_temporal_features([])

        assert features["total_duration_days"] == 0
        assert features["avg_gap_hours"] == 0
        assert features["activity_bursts"] == []
        assert features["dormant_periods"] == []

    def test_calculate_temporal_features_with_data(self, mock_observations):
        """Test temporal features calculation with data."""
        from ems.inference_data_prep import InferenceDataPrep

        prep = InferenceDataPrep()
        features = prep.calculate_temporal_features(mock_observations)

        assert features["total_duration_days"] > 0
        assert "phase_durations" in features
        assert isinstance(features["inter_event_gaps"], list)


# =============================================================================
# PATTERN INFERENCE ENGINE TESTS
# =============================================================================

class TestPatternInferenceEngine:
    """Tests for PatternInferenceEngine class."""

    def test_insufficient_data_detection(self):
        """Test that insufficient data is properly detected."""
        from ems.pattern_inference import PatternInferenceEngine

        engine = PatternInferenceEngine()

        with patch.object(
            engine.data_prep,
            'prepare_innovator_data',
            return_value={"pursuit_count": 1, "pursuits": []}
        ):
            result = engine.infer_patterns("test_innovator")

        assert result["sufficient_data"] is False
        assert result["synthesis_ready"] is False
        assert result["pursuit_count"] == 1

    def test_sequence_mining_basic(self):
        """Test basic sequence mining."""
        from ems.pattern_inference import PatternInferenceEngine

        engine = PatternInferenceEngine()

        prepared_data = {
            "pursuit_count": 3,
            "pursuits": [
                {
                    "pursuit_id": "p1",
                    "sequence": ["A", "B", "C", "D"],
                    "outcome": "COMPLETED.SUCCESSFUL",
                },
                {
                    "pursuit_id": "p2",
                    "sequence": ["A", "B", "C", "E"],
                    "outcome": "COMPLETED.SUCCESSFUL",
                },
                {
                    "pursuit_id": "p3",
                    "sequence": ["A", "B", "C", "F"],
                    "outcome": "COMPLETED.SUCCESSFUL",
                },
            ],
        }

        sequences = engine._mine_sequences(prepared_data)

        # Should find A->B->C as a common sequence
        assert len(sequences) > 0

        # Check that at least one sequence has high frequency
        has_frequent = any(s["frequency"] >= 0.4 for s in sequences)
        assert has_frequent

    def test_phase_clustering_basic(self):
        """Test basic phase clustering."""
        from ems.pattern_inference import PatternInferenceEngine

        engine = PatternInferenceEngine()

        prepared_data = {
            "pursuit_count": 2,
            "pursuits": [
                {
                    "pursuit_id": "p1",
                    "detailed_sequence": [
                        {"observation_type": "A", "context": {"pursuit_phase": "IDEATION"}},
                        {"observation_type": "B", "context": {"pursuit_phase": "IDEATION"}},
                        {"observation_type": "C", "context": {"pursuit_phase": "VALIDATION"}},
                        {"observation_type": "D", "context": {"pursuit_phase": "VALIDATION"}},
                    ],
                    "temporal_features": {},
                },
                {
                    "pursuit_id": "p2",
                    "detailed_sequence": [
                        {"observation_type": "A", "context": {"pursuit_phase": "IDEATION"}},
                        {"observation_type": "B", "context": {"pursuit_phase": "IDEATION"}},
                        {"observation_type": "E", "context": {"pursuit_phase": "VALIDATION"}},
                    ],
                    "temporal_features": {},
                },
            ],
        }

        phases = engine._cluster_into_phases(prepared_data)

        # Should identify IDEATION and VALIDATION phases
        phase_names = [p["name"] for p in phases]
        assert "IDEATION" in phase_names or "VALIDATION" in phase_names

    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        from ems.pattern_inference import PatternInferenceEngine

        engine = PatternInferenceEngine()

        prepared_data = {
            "pursuit_count": 5,
            "pursuits": [{"pursuit_id": f"p{i}"} for i in range(5)],
        }

        sequences = [
            {"frequency": 0.8, "outcome_correlation": 0.7, "sequence": ["A", "B", "C"]},
            {"frequency": 0.6, "outcome_correlation": 0.6, "sequence": ["X", "Y"]},
        ]
        phases = [{"frequency": 0.9}]
        transitions = [{"frequency": 0.7}]
        dependencies = []

        confidence = engine._calculate_confidence(
            prepared_data, sequences, phases, transitions, dependencies
        )

        assert "overall" in confidence
        assert "sample_size_score" in confidence
        assert "consistency_score" in confidence
        assert "outcome_association_score" in confidence
        assert "distinctiveness_score" in confidence

        # With 5 pursuits, sample score should be 0.5
        assert confidence["sample_size_score"] == 0.5

        # Overall should be between 0 and 1
        assert 0 <= confidence["overall"] <= 1


# =============================================================================
# ADL GENERATOR TESTS
# =============================================================================

class TestADLGenerator:
    """Tests for ADLGenerator class."""

    def test_insufficient_data_response(self):
        """Test ADL generation with insufficient data."""
        from ems.adl_generator import ADLGenerator

        generator = ADLGenerator()

        inference_result = {
            "sufficient_data": False,
            "synthesis_ready": False,
            "pursuit_count": 2,
            "confidence": {"overall": 0.2},
            "patterns": {
                "sequences": [],
                "phases": [],
                "transitions": [],
                "dependencies": [],
            },
        }

        result = generator.generate_archetype(
            "test_innovator",
            inference_result=inference_result
        )

        assert result["archetype_id"] is None
        assert result["archetype"] is None
        assert "insufficient_data" in result.get("synthesis_metadata", {}).get("status", "")

    def test_archetype_generation_with_valid_data(self):
        """Test ADL generation with valid inference data."""
        from ems.adl_generator import ADLGenerator

        generator = ADLGenerator()

        inference_result = {
            "sufficient_data": True,
            "synthesis_ready": True,
            "pursuit_count": 5,
            "confidence": {"overall": 0.7},
            "patterns": {
                "sequences": [
                    {
                        "sequence": ["ARTIFACT_CREATED:vision", "TOOL_INVOKED:risk"],
                        "frequency": 0.8,
                        "outcome_correlation": 0.9,
                        "avg_position": 0.2,
                    }
                ],
                "phases": [
                    {
                        "phase_id": "phase_ideation",
                        "name": "IDEATION",
                        "typical_activities": ["ARTIFACT_CREATED"],
                        "position": "early",
                        "frequency": 0.9,
                    },
                    {
                        "phase_id": "phase_validation",
                        "name": "VALIDATION",
                        "typical_activities": ["RISK_VALIDATION"],
                        "position": "late",
                        "frequency": 0.85,
                    },
                ],
                "transitions": [
                    {
                        "from_phase": "IDEATION",
                        "to_phase": "VALIDATION",
                        "trigger_activities": ["ARTIFACT_CREATED"],
                        "trigger_artifacts": ["ARTIFACT_CREATED:vision"],
                        "avg_activities_before_transition": 3,
                        "frequency": 0.7,
                    }
                ],
                "dependencies": [
                    {
                        "source": "TOOL_INVOKED:risk",
                        "target": "ARTIFACT_CREATED:hypothesis",
                        "dependency_type": "enables",
                        "strength": 0.6,
                        "lag": 1.5,
                    }
                ],
            },
        }

        result = generator.generate_archetype(
            "test_innovator",
            inference_result=inference_result
        )

        assert result["archetype_id"] is not None
        assert result["archetype"] is not None
        assert result["adl_version"] == "1.0"
        assert "generated_at" in result
        assert len(result["archetype"]["phases"]) == 2
        # Check origin contains EMS reference
        assert "EMS" in result["archetype"]["origin"]
        # Check new required fields for hand-authored compatibility
        assert result["archetype"]["transition_philosophy"] == "fluid"
        assert result["archetype"]["criteria_enforcement"] == "advisory"
        assert result["archetype"]["backward_iteration"] == "revisit_as_needed"
        assert result["archetype"]["draft"] is True
        # Check coaching_config structure
        assert "coaching_config" in result["archetype"]
        assert "language_style" in result["archetype"]["coaching_config"]
        assert "framing" in result["archetype"]["coaching_config"]
        assert "backward_iteration" in result["archetype"]["coaching_config"]
        # Check phase structure
        for phase in result["archetype"]["phases"]:
            assert "name" in phase
            assert "universal_state" in phase
            assert "activities" in phase
            assert "transition_criteria" in phase
        # Check provenance
        assert "provenance" in result["archetype"]
        assert result["archetype"]["provenance"]["source"] == "EMS"
        # Check validation result
        assert "validation" in result
        assert result["validation"]["valid"] is True

    def test_archetype_id_generation(self):
        """Test that archetype IDs are properly generated."""
        from ems.adl_generator import ADLGenerator

        generator = ADLGenerator()
        archetype_id = generator._generate_archetype_id("test_innovator")

        assert archetype_id.startswith("emergent_")
        assert len(archetype_id) > 10  # emergent_ + hash

    def test_phase_description_generation(self):
        """Test that phase descriptions are generated."""
        from ems.adl_generator import ADLGenerator

        generator = ADLGenerator()

        phase = {
            "typical_activities": ["ARTIFACT_CREATED", "TOOL_INVOKED"],
            "position": "early",
        }

        description = generator._generate_phase_description(phase)

        assert "early" in description
        assert len(description) > 10


# =============================================================================
# DISPLAY LABEL TESTS
# =============================================================================

class TestDisplayLabelsInference:
    """Tests for v3.7.2 inference-related display labels."""

    def test_inference_algorithm_labels(self):
        """Test that inference algorithm labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("inference_algorithm", "sequence_mining")
        assert "Pattern" in label or "Activity" in label

        label = DisplayLabels.get("inference_algorithm", "phase_clustering")
        assert "Phase" in label

    def test_pattern_type_labels(self):
        """Test that pattern type labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("pattern_type", "sequence")
        assert "Sequence" in label or "Activity" in label

        label = DisplayLabels.get("pattern_type", "phase")
        assert "Phase" in label

    def test_confidence_dimension_labels(self):
        """Test that confidence dimension labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("confidence_dimension", "sample_size")
        assert len(label) > 0

        label = DisplayLabels.get("confidence_dimension", "consistency")
        assert len(label) > 0

    def test_adl_status_labels(self):
        """Test that ADL status labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("adl_status", "insufficient_data")
        assert len(label) > 0

        label = DisplayLabels.get("adl_status", "complete")
        assert len(label) > 0

    def test_archetype_origin_labels(self):
        """Test that archetype origin labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("archetype_origin", "synthesized")
        assert "Emergent" in label or "Your" in label

        label = DisplayLabels.get("archetype_origin", "prescribed")
        assert "Established" in label

    def test_confidence_level_labels(self):
        """Test that confidence level labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("confidence_level", "high")
        assert "Strong" in label

        label = DisplayLabels.get("confidence_level", "low")
        assert "Emerging" in label


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestSynthesisTriggerIntegration:
    """Tests for synthesis trigger integration."""

    def test_synthesis_trigger_method_exists(self):
        """Test that synthesis trigger method exists on ProcessObserver."""
        from ems.process_observer import ProcessObserver

        observer = ProcessObserver()

        # Verify the method exists
        assert hasattr(observer, '_trigger_synthesis_check_if_eligible')
        assert callable(observer._trigger_synthesis_check_if_eligible)

    def test_complete_observation_returns_success(self):
        """Test that complete_observation properly returns success status."""
        from ems.process_observer import ProcessObserver

        observer = ProcessObserver()

        with patch('ems.process_observer.db') as mock_db:
            mock_db.update_observation_status.return_value = True
            mock_db.get_pursuit.return_value = None  # No pursuit found, skip trigger

            result = observer.complete_observation("test_pursuit")
            assert result is True


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_pursuit_list_handling(self):
        """Test handling of empty pursuit list."""
        from ems.pattern_inference import PatternInferenceEngine

        engine = PatternInferenceEngine()

        result = engine._mine_sequences({"pursuits": [], "pursuit_count": 0})
        assert result == []

        result = engine._cluster_into_phases({"pursuits": [], "pursuit_count": 0})
        assert result == []

    def test_single_pursuit_patterns(self):
        """Test that single pursuit still yields patterns (frequency = 1.0)."""
        from ems.pattern_inference import PatternInferenceEngine

        engine = PatternInferenceEngine()

        prepared_data = {
            "pursuit_count": 1,
            "pursuits": [
                {
                    "pursuit_id": "p1",
                    "sequence": ["A", "B", "C"],
                    "outcome": "COMPLETED",
                }
            ],
        }

        # With only 1 pursuit, patterns have frequency 1.0 (100%)
        # But the engine requires MIN_PURSUITS_FOR_INFERENCE = 3
        # The sequence mining still works, but full inference should fail
        sequences = engine._mine_sequences(prepared_data)
        # A-B-C is found with frequency 1.0 (1/1 pursuits)
        assert len(sequences) >= 1

        # However, full inference should report insufficient data
        with patch.object(
            engine.data_prep,
            'prepare_innovator_data',
            return_value=prepared_data
        ):
            result = engine.infer_patterns("test_innovator")
            assert result["sufficient_data"] is False

    def test_missing_observation_fields(self):
        """Test handling of observations with missing fields."""
        from ems.inference_data_prep import InferenceDataPrep

        prep = InferenceDataPrep()

        # Observations with missing fields
        observations = [
            {"observation_type": "UNKNOWN"},  # No details
            {},  # Empty
        ]

        sequence = prep.build_activity_sequence(observations, enrich=True)
        assert len(sequence) == 2
        assert sequence[0] == "UNKNOWN"
        assert sequence[1] == "UNKNOWN"


# =============================================================================
# v3.7.3: ARCHETYPE SIMILARITY TESTS
# =============================================================================

class TestArchetypeSimilarity:
    """Tests for v3.7.3 archetype-to-archetype similarity comparison."""

    def test_compute_archetype_similarity_lean_startup_like(self):
        """Test that Lean Startup-like behavior produces high similarity."""
        from ems.pattern_inference import PatternInferenceEngine
        from coaching.methodology_archetypes import LEAN_STARTUP_ARCHETYPE

        engine = PatternInferenceEngine()

        # Inferred data that resembles Lean Startup
        inferred_phases = [
            {"phase_id": "phase_vision", "name": "VISION", "position": "early",
             "typical_activities": ["vision_creation", "problem_definition"]},
            {"phase_id": "phase_derisk", "name": "DE_RISK", "position": "middle",
             "typical_activities": ["hypothesis_testing", "experiment_design"]},
            {"phase_id": "phase_deploy", "name": "DEPLOY", "position": "late",
             "typical_activities": ["mvp_development", "launch"]},
        ]
        inferred_transitions = [
            {"from_phase": "VISION", "to_phase": "DE_RISK"},
            {"from_phase": "DE_RISK", "to_phase": "DEPLOY"},
        ]
        inferred_activities = {
            "vision", "hypothesis", "experiment", "validate", "mvp", "test"
        }
        inferred_tools = {"TOOL_experiment", "TOOL_survey"}

        similarity = engine._compute_archetype_similarity(
            inferred_phases=inferred_phases,
            inferred_transitions=inferred_transitions,
            inferred_activities=inferred_activities,
            inferred_tools=inferred_tools,
            existing_archetype=LEAN_STARTUP_ARCHETYPE
        )

        # Should have high similarity (> 0.5) with Lean Startup
        assert similarity > 0.5, f"Expected high similarity, got {similarity}"

    def test_compute_archetype_similarity_novel_behavior(self):
        """Test that novel behavior produces low similarity."""
        from ems.pattern_inference import PatternInferenceEngine
        from coaching.methodology_archetypes import LEAN_STARTUP_ARCHETYPE

        engine = PatternInferenceEngine()

        # Inferred data that is completely different
        inferred_phases = [
            {"phase_id": "phase_custom", "name": "CUSTOM_PHASE", "position": "early",
             "typical_activities": ["unique_activity_xyz"]},
        ]
        inferred_transitions = []
        inferred_activities = {"unique_activity_xyz", "novel_approach"}
        inferred_tools = set()

        similarity = engine._compute_archetype_similarity(
            inferred_phases=inferred_phases,
            inferred_transitions=inferred_transitions,
            inferred_activities=inferred_activities,
            inferred_tools=inferred_tools,
            existing_archetype=LEAN_STARTUP_ARCHETYPE
        )

        # Should have low similarity (< 0.4) with Lean Startup
        assert similarity < 0.4, f"Expected low similarity, got {similarity}"

    def test_compare_to_existing_archetypes(self):
        """Test the full comparison across all archetypes."""
        from ems.pattern_inference import PatternInferenceEngine

        engine = PatternInferenceEngine()

        # Lean Startup-like behavior
        inferred_phases = [
            {"phase_id": "phase_1", "name": "INITIAL", "position": "early",
             "typical_activities": ["vision", "fears"]},
            {"phase_id": "phase_2", "name": "TEST", "position": "middle",
             "typical_activities": ["hypothesis", "experiment"]},
        ]
        inferred_transitions = [{"from_phase": "INITIAL", "to_phase": "TEST"}]
        inferred_activities = {"vision", "hypothesis", "experiment", "validate"}
        inferred_tools = {"TOOL_test"}

        similar = engine._compare_to_existing_archetypes(
            inferred_phases=inferred_phases,
            inferred_transitions=inferred_transitions,
            inferred_activities=inferred_activities,
            inferred_tools=inferred_tools
        )

        # Should return a list
        assert isinstance(similar, list)
        # If there are results, they should have required fields
        for item in similar:
            assert "name" in item
            assert "display_name" in item
            assert "similarity" in item
            assert item["similarity"] > 0.3  # Only > 0.3 included (exclusive)

    def test_confidence_includes_similar_archetypes(self):
        """Test that confidence result includes similar_archetypes field."""
        from ems.pattern_inference import PatternInferenceEngine

        engine = PatternInferenceEngine()

        prepared_data = {"pursuit_count": 5}
        sequences = [{"sequence": ["A", "B"], "frequency": 0.6, "outcome_correlation": 0.7}]
        phases = [{"position": "early", "frequency": 0.8, "typical_activities": ["vision"]}]
        transitions = [{"from_phase": "A", "to_phase": "B", "frequency": 0.5}]
        dependencies = []

        confidence = engine._calculate_confidence(
            prepared_data, sequences, phases, transitions, dependencies
        )

        assert "similar_archetypes" in confidence
        assert isinstance(confidence["similar_archetypes"], list)

    def test_longest_common_subsequence(self):
        """Test LCS helper function."""
        from ems.pattern_inference import PatternInferenceEngine

        engine = PatternInferenceEngine()

        # Test cases
        assert engine._longest_common_subsequence([], []) == 0
        assert engine._longest_common_subsequence(["A"], ["A"]) == 1
        assert engine._longest_common_subsequence(["A", "B", "C"], ["A", "C"]) == 2
        assert engine._longest_common_subsequence(["A", "B", "C"], ["X", "Y", "Z"]) == 0
        assert engine._longest_common_subsequence(
            ["DISCOVERY", "VALIDATION", "IMPLEMENTATION"],
            ["DISCOVERY", "IMPLEMENTATION"]
        ) == 2


# =============================================================================
# v3.7.3: EMS EVENT EMISSION TESTS (Phase 7 will add actual event types)
# =============================================================================

class TestEMSEventEmission:
    """Tests for EMS event infrastructure (Phase 7 adds full event types)."""

    def test_event_types_class_exists(self):
        """Test that EventTypes class exists and has basic structure."""
        from events.schemas import EventTypes

        # Verify the base EventTypes class is available
        assert hasattr(EventTypes, 'PURSUIT_CREATED')
        assert hasattr(EventTypes, 'ELEMENT_CAPTURED')

    def test_redis_stream_publisher_exists(self):
        """Test that Redis stream publisher class exists."""
        from events.redis_publisher import RedisStreamPublisher

        # Just verify the class is importable
        assert RedisStreamPublisher is not None

    def test_process_observer_complete_observation(self):
        """Test that ProcessObserver.complete_observation works."""
        from ems.process_observer import ProcessObserver

        observer = ProcessObserver()

        with patch('ems.process_observer.db') as mock_db:
            mock_db.update_observation_status.return_value = True
            mock_db.get_pursuit.return_value = None  # Skip further processing

            result = observer.complete_observation("test_pursuit")
            assert result is True


# =============================================================================
# v3.7.3: REVIEW INTERFACE TESTS
# =============================================================================

class TestReviewInterface:
    """Tests for v3.7.3 innovator review interface."""

    def test_review_session_manager_exists(self):
        """Test that ReviewSessionManager class exists."""
        from ems.review_interface import ReviewSessionManager

        assert ReviewSessionManager is not None

    def test_review_stages_defined(self):
        """Test that review stages are properly defined."""
        from ems.review_interface import ReviewSessionManager

        assert len(ReviewSessionManager.REVIEW_STAGES) == 7
        assert "INITIATED" in ReviewSessionManager.REVIEW_STAGES
        assert "REVIEWING_PHASES" in ReviewSessionManager.REVIEW_STAGES
        assert "NAMING" in ReviewSessionManager.REVIEW_STAGES
        assert "FINALIZING" in ReviewSessionManager.REVIEW_STAGES

    def test_slugify_function(self):
        """Test the slugify helper function."""
        from ems.review_interface import slugify

        assert slugify("My Innovation Process") == "my_innovation_process"
        assert slugify("Test@#$Name") == "testname"
        assert slugify("  Leading  Trailing  ") == "leading_trailing"

    def test_apply_refinements_rename_phase(self):
        """Test that apply_refinements handles phase renaming."""
        from ems.review_interface import apply_refinements

        draft = {
            "archetype": {
                "name": "test",
                "description": "test desc",
                "phases": [
                    {"name": "Original Phase", "activities": ["a1"]}
                ]
            }
        }

        refinements = [
            {
                "action": "RENAMED_PHASE",
                "target": "phase_0",
                "before": "Original Phase",
                "after": "New Phase Name"
            }
        ]

        naming = {
            "methodology_name": "Test Methodology",
            "methodology_description": "A test methodology",
            "key_principles": ["Be thorough"]
        }

        with patch('ems.adl_generator.validate_adl_compatibility') as mock_validate:
            mock_validate.return_value = {"valid": True, "errors": []}
            result = apply_refinements(draft, refinements, naming)

        assert result["archetype"]["phases"][0]["name"] == "New Phase Name"
        assert result["archetype"]["name"] == "Test Methodology"


# =============================================================================
# v3.7.3: ARCHETYPE PUBLISHER TESTS
# =============================================================================

class TestArchetypePublisher:
    """Tests for v3.7.3 archetype publisher."""

    def test_archetype_publisher_exists(self):
        """Test that ArchetypePublisher class exists."""
        from ems.archetype_publisher import ArchetypePublisher

        assert ArchetypePublisher is not None

    def test_visibility_levels_defined(self):
        """Test that visibility levels are properly defined."""
        from ems.archetype_publisher import ArchetypePublisher

        assert len(ArchetypePublisher.VISIBILITY_LEVELS) == 4
        assert "PERSONAL" in ArchetypePublisher.VISIBILITY_LEVELS
        assert "TEAM" in ArchetypePublisher.VISIBILITY_LEVELS
        assert "ORGANIZATION" in ArchetypePublisher.VISIBILITY_LEVELS
        assert "IKF_SHARED" in ArchetypePublisher.VISIBILITY_LEVELS

    def test_generate_attribution(self):
        """Test attribution generation."""
        from ems.archetype_publisher import ArchetypePublisher

        publisher = ArchetypePublisher(db=MagicMock())

        innovator = {
            "_id": "innovator_123",
            "display_name": "Test Innovator"
        }

        review_session = {
            "created_at": datetime.now(timezone.utc),
            "original_draft": {
                "provenance": {
                    "source_pursuit_count": 5
                }
            }
        }

        attribution = publisher._generate_attribution(innovator, review_session)

        assert attribution["innovator_id"] == "innovator_123"
        assert attribution["innovator_display_name"] == "Test Innovator"
        assert attribution["source_pursuit_count"] == 5
        assert attribution["methodology_origin"] == "emergent"


# =============================================================================
# v3.7.3: DISPLAY LABELS TESTS
# =============================================================================

class TestDisplayLabelsReview:
    """Tests for v3.7.3 review-related display labels."""

    def test_review_status_labels(self):
        """Test that review status labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("review_status", "INITIATED")
        assert len(label) > 0

        label = DisplayLabels.get("review_status", "APPROVED")
        assert len(label) > 0

    def test_refinement_action_labels(self):
        """Test that refinement action labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("refinement_action", "RENAMED_PHASE")
        assert len(label) > 0

        label = DisplayLabels.get("refinement_action", "REORDERED")
        assert len(label) > 0

    def test_methodology_visibility_labels(self):
        """Test that visibility labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("methodology_visibility", "PERSONAL")
        assert len(label) > 0  # "Just for Me"

        label = DisplayLabels.get("methodology_visibility", "IKF_SHARED")
        assert len(label) > 0

    def test_archetype_version_labels(self):
        """Test that archetype version labels are registered."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("archetype_version", "CURRENT")
        assert len(label) > 0

        label = DisplayLabels.get("archetype_version", "SUPERSEDED")
        assert len(label) > 0
