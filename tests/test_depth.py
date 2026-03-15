"""
InDE v4.3 — Depth Dimension System Tests

Tests:
- DepthDimension enum
- DIMENSION_WEIGHTS sum to 1.0
- SCAFFOLDING_DIMENSION_MAP coverage
- DepthCalculator.compute_depth_snapshot()
- Display Label Registry v4.3 categories
"""

import pytest
import sys
sys.path.insert(0, 'app')

from modules.depth.depth_schemas import (
    DepthDimension,
    DimensionScore,
    PursuitDepthSnapshot,
    DIMENSION_WEIGHTS,
    SCAFFOLDING_DIMENSION_MAP,
    get_score_tier,
)
from modules.depth.depth_calculator import DepthCalculator
from shared.display_labels import DisplayLabels


class TestDepthDimension:
    """Tests for DepthDimension enum."""

    def test_dimension_count(self):
        """Five dimensions defined."""
        assert len(DepthDimension) == 5

    def test_dimension_values(self):
        """Dimension values are lowercase strings."""
        expected = {"clarity", "empathy", "protection", "evidence", "specificity"}
        actual = {d.value for d in DepthDimension}
        assert actual == expected


class TestDimensionWeights:
    """Tests for DIMENSION_WEIGHTS."""

    def test_weights_sum_to_one(self):
        """Weights sum to exactly 1.0."""
        total = sum(DIMENSION_WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_all_dimensions_have_weights(self):
        """Every dimension has a weight defined."""
        for dim in DepthDimension:
            assert dim in DIMENSION_WEIGHTS


class TestScaffoldingDimensionMap:
    """Tests for SCAFFOLDING_DIMENSION_MAP."""

    def test_all_map_to_valid_dimensions(self):
        """Every mapped element points to a valid dimension."""
        for element_type, dimension in SCAFFOLDING_DIMENSION_MAP.items():
            assert isinstance(dimension, DepthDimension)

    def test_minimum_coverage(self):
        """At least 3 elements per dimension."""
        counts = {d: 0 for d in DepthDimension}
        for dimension in SCAFFOLDING_DIMENSION_MAP.values():
            counts[dimension] += 1
        for dim, count in counts.items():
            assert count >= 3, f"{dim.value} has only {count} elements"


class TestScoreTier:
    """Tests for get_score_tier function."""

    def test_tier_boundaries(self):
        """Score tiers have correct boundaries."""
        assert get_score_tier(0.0) == "nascent"
        assert get_score_tier(0.19) == "nascent"
        assert get_score_tier(0.2) == "emerging"
        assert get_score_tier(0.39) == "emerging"
        assert get_score_tier(0.4) == "developing"
        assert get_score_tier(0.59) == "developing"
        assert get_score_tier(0.6) == "solid"
        assert get_score_tier(0.79) == "solid"
        assert get_score_tier(0.8) == "rich"
        assert get_score_tier(1.0) == "rich"


class TestDepthCalculator:
    """Tests for DepthCalculator."""

    def test_empty_elements_returns_zero_depth(self):
        """No scaffolding elements yields zero overall depth."""
        calculator = DepthCalculator()
        snapshot = calculator.compute_depth_snapshot(
            pursuit_id="test-pursuit",
            scaffolding_elements=[]
        )
        assert snapshot.overall_depth == 0.0
        assert len(snapshot.dimensions) == 5

    def test_all_dimensions_scored(self):
        """Snapshot includes scores for all 5 dimensions."""
        calculator = DepthCalculator()
        snapshot = calculator.compute_depth_snapshot(
            pursuit_id="test-pursuit",
            scaffolding_elements=[]
        )
        dimension_names = {d.dimension.value for d in snapshot.dimensions}
        expected = {"clarity", "empathy", "protection", "evidence", "specificity"}
        assert dimension_names == expected

    def test_depth_with_scaffolding_elements(self):
        """Elements increase dimension scores."""
        calculator = DepthCalculator()
        elements = [
            {"element_type": "vision_statement", "content": "My idea"},
            {"element_type": "problem_definition", "content": "The problem"},
            {"element_type": "target_persona", "content": "Users"},
        ]
        snapshot = calculator.compute_depth_snapshot(
            pursuit_id="test-pursuit",
            scaffolding_elements=elements
        )
        # Should have non-zero depth
        assert snapshot.overall_depth > 0.0
        # Clarity should be highest (2 elements)
        clarity_score = next(
            d.score for d in snapshot.dimensions
            if d.dimension == DepthDimension.CLARITY
        )
        assert clarity_score > 0.0

    def test_depth_narrative_generated(self):
        """Depth narrative is non-empty string."""
        calculator = DepthCalculator()
        snapshot = calculator.compute_depth_snapshot(
            pursuit_id="test-pursuit",
            scaffolding_elements=[]
        )
        assert isinstance(snapshot.depth_narrative, str)
        assert len(snapshot.depth_narrative) > 0

    def test_experience_mode_preserved(self):
        """Experience mode is stored in snapshot."""
        calculator = DepthCalculator()
        snapshot = calculator.compute_depth_snapshot(
            pursuit_id="test-pursuit",
            experience_mode="expert",
            scaffolding_elements=[]
        )
        assert snapshot.experience_mode == "expert"


class TestDisplayLabelsV43:
    """Tests for v4.3 Display Label Registry categories."""

    V43_CATEGORIES = [
        "depth_dimensions",
        "depth_richness_signals",
        "navigation_sections",
        "artifact_richness_signals",
        "tim_depth_labels",
        "onboarding_depth_framing",
        "experience_mode_labels",
    ]

    def test_v43_categories_exist(self):
        """All v4.3 categories are registered."""
        for category in self.V43_CATEGORIES:
            assert category in DisplayLabels._REGISTRY, f"Missing: {category}"

    def test_depth_dimensions_count(self):
        """5 depth dimension labels."""
        assert len(DisplayLabels._REGISTRY["depth_dimensions"]) == 5

    def test_depth_richness_signals_count(self):
        """5 richness signal tiers."""
        assert len(DisplayLabels._REGISTRY["depth_richness_signals"]) == 5

    def test_navigation_sections_count(self):
        """7 navigation sections."""
        assert len(DisplayLabels._REGISTRY["navigation_sections"]) == 7

    def test_tim_depth_labels_count(self):
        """7 TIM depth labels."""
        assert len(DisplayLabels._REGISTRY["tim_depth_labels"]) == 7

    def test_all_entries_have_labels(self):
        """Every entry has a 'label' field."""
        for category in self.V43_CATEGORIES:
            for key, entry in DisplayLabels._REGISTRY[category].items():
                assert "label" in entry, f"{category}.{key} missing 'label'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
