"""
Depth Calculator — v4.3

Reads scaffolding_elements from the database for a given pursuit and maps
element completion to five depth dimension scores.

Scaffolding -> Depth Dimension mapping:
  CLARITY:     vision elements (vision_statement, problem_definition, impact_statement)
  EMPATHY:     persona elements (target_persona, pain_point, user_context)
  PROTECTION:  fear/risk elements (fear_register, risk_assessment, fear_addressed_count)
  EVIDENCE:    validation elements (hypothesis, test_plan, experiment_result, validation_count)
  SPECIFICITY: refinement elements (value_proposition, differentiation, mvp_scope)
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging

from .depth_schemas import (
    DepthDimension,
    DimensionScore,
    PursuitDepthSnapshot,
    DIMENSION_WEIGHTS,
    SCAFFOLDING_DIMENSION_MAP,
    get_score_tier,
)

logger = logging.getLogger(__name__)


class DepthCalculator:
    """
    Computes depth snapshots from scaffolding state.

    Does not re-run scaffolding - it consumes the scaffolding state as its input.
    """

    def __init__(self, db=None):
        """
        Initialize with optional database connection.

        Args:
            db: Database connection with db.db.scaffolding_elements collection
        """
        self.db = db
        self._display_labels = None

    def _get_display_labels(self):
        """Lazy-load display labels."""
        if self._display_labels is None:
            from shared.display_labels import DisplayLabels
            self._display_labels = DisplayLabels
        return self._display_labels

    def compute_depth_snapshot(
        self,
        pursuit_id: str,
        experience_mode: str = "novice",
        scaffolding_elements: Optional[List[Dict[str, Any]]] = None
    ) -> PursuitDepthSnapshot:
        """
        Main entry point. Reads scaffolding state from DB (or uses provided elements),
        computes depth. Returns a PursuitDepthSnapshot ready for API response.

        Args:
            pursuit_id: The pursuit to compute depth for
            experience_mode: 'novice', 'intermediate', or 'expert'
            scaffolding_elements: Optional pre-fetched elements (for testing)

        Returns:
            PursuitDepthSnapshot with all dimension scores and narrative
        """
        # Get scaffolding elements
        if scaffolding_elements is None and self.db is not None:
            elements = list(self.db.db.scaffolding_elements.find({
                "pursuit_id": pursuit_id
            }))
        else:
            elements = scaffolding_elements or []

        # Compute each dimension score
        dimension_scores = []
        for dimension in DepthDimension:
            score = self._compute_dimension_score(dimension, elements, experience_mode)
            dimension_scores.append(score)

        # Compute overall depth (weighted average)
        overall_depth = sum(
            score.score * DIMENSION_WEIGHTS.get(score.dimension, 0.2)
            for score in dimension_scores
        )

        # Identify top strength and active frontier
        top_strength = self._identify_top_strength(dimension_scores)
        active_frontier = self._identify_active_frontier(elements, dimension_scores)

        # Generate narrative
        depth_narrative = self._compute_depth_narrative(
            dimension_scores, experience_mode, top_strength, active_frontier
        )

        return PursuitDepthSnapshot(
            pursuit_id=pursuit_id,
            overall_depth=round(overall_depth, 3),
            dimensions=dimension_scores,
            top_strength=top_strength,
            active_frontier=active_frontier,
            depth_narrative=depth_narrative,
            computed_at=datetime.now(timezone.utc).isoformat(),
            experience_mode=experience_mode,
        )

    def _compute_dimension_score(
        self,
        dimension: DepthDimension,
        elements: List[Dict[str, Any]],
        experience_mode: str
    ) -> DimensionScore:
        """
        Scores a single depth dimension from relevant scaffolding elements.

        Args:
            dimension: The dimension to score
            elements: All scaffolding elements for the pursuit
            experience_mode: For selecting appropriate display labels

        Returns:
            DimensionScore with display_label from the Display Label Registry
        """
        # Find elements that contribute to this dimension
        contributing_elements = []
        for element in elements:
            element_type = element.get("element_type", "")
            if SCAFFOLDING_DIMENSION_MAP.get(element_type) == dimension:
                contributing_elements.append(element)

        # Calculate score based on element count and quality
        signal_count = len(contributing_elements)

        if signal_count == 0:
            score = 0.0
        else:
            # Base score from element count (max 4 elements = 0.8)
            count_score = min(signal_count / 4.0, 0.8)

            # Quality bonus from filled vs. empty elements
            filled_count = sum(
                1 for e in contributing_elements
                if e.get("content") or e.get("value") or e.get("filled")
            )
            quality_score = (filled_count / max(signal_count, 1)) * 0.2

            score = min(count_score + quality_score, 1.0)

        # Get strongest signal (most recent or most filled element)
        strongest_signal = None
        if contributing_elements:
            # Sort by updated_at or content length
            sorted_elements = sorted(
                contributing_elements,
                key=lambda e: (
                    len(str(e.get("content", ""))),
                    e.get("updated_at", datetime.min)
                ),
                reverse=True
            )
            if sorted_elements:
                strongest = sorted_elements[0]
                strongest_signal = strongest.get("label") or strongest.get("element_type")

        # Get display labels
        labels = self._get_display_labels()
        display_label = labels.get("depth_dimensions", dimension.value, experience_mode)
        if isinstance(display_label, dict):
            display_label = display_label.get("label", dimension.value)

        # Get richness phrase
        tier = get_score_tier(score)
        richness_phrase = labels.get("depth_richness_signals", tier, experience_mode)
        if isinstance(richness_phrase, dict):
            richness_phrase = richness_phrase.get("label", tier)

        return DimensionScore(
            dimension=dimension,
            score=round(score, 3),
            signal_count=signal_count,
            strongest_signal=strongest_signal,
            display_label=display_label or dimension.value,
            richness_phrase=richness_phrase or tier,
        )

    def _identify_top_strength(self, dimensions: List[DimensionScore]) -> str:
        """
        Returns the Display Label for the most developed dimension.
        """
        if not dimensions:
            return ""
        top = max(dimensions, key=lambda d: d.score)
        return top.display_label

    def _identify_active_frontier(
        self,
        elements: List[Dict[str, Any]],
        dimensions: List[DimensionScore]
    ) -> str:
        """
        Returns the Display Label for the dimension with the most recent
        scaffolding activity - this is where the innovator's energy is currently
        flowing and where the bridge questions are focused.
        """
        if not elements:
            # Default to lowest-scoring dimension
            if dimensions:
                lowest = min(dimensions, key=lambda d: d.score)
                return lowest.display_label
            return ""

        # Find most recently updated element
        recent_element = max(
            elements,
            key=lambda e: e.get("updated_at", datetime.min) if isinstance(e.get("updated_at"), datetime) else datetime.min,
            default=None
        )

        if recent_element:
            element_type = recent_element.get("element_type", "")
            dimension = SCAFFOLDING_DIMENSION_MAP.get(element_type)
            if dimension:
                for d in dimensions:
                    if d.dimension == dimension:
                        return d.display_label

        # Fallback to lowest-scoring dimension
        if dimensions:
            lowest = min(dimensions, key=lambda d: d.score)
            return lowest.display_label
        return ""

    def _compute_depth_narrative(
        self,
        dimensions: List[DimensionScore],
        experience_mode: str,
        top_strength: str,
        active_frontier: str
    ) -> str:
        """
        Generates a 1-2 sentence depth narrative for the innovator.

        novice mode: pure goal vocabulary
        expert mode: may reference methodology dimensions

        Example (novice): "You have a clear picture of who you are helping and
        what their problem is. Your next depth opportunity is testing your assumptions."
        """
        if not dimensions:
            return "Start capturing your idea to see your depth grow."

        # Calculate average score
        avg_score = sum(d.score for d in dimensions) / len(dimensions)

        # Find strongest and weakest dimensions
        strongest = max(dimensions, key=lambda d: d.score)
        weakest = min(dimensions, key=lambda d: d.score)

        # Build narrative based on overall depth
        if avg_score < 0.2:
            # Just starting
            narrative = "Your idea is just beginning to take shape. "
            narrative += f"Start with {weakest.display_label.lower()} to build your foundation."
        elif avg_score < 0.4:
            # Emerging
            narrative = f"Your idea is gaining form. {strongest.display_label} is where you are strongest. "
            if weakest.score < 0.2:
                narrative += f"Consider developing {weakest.display_label.lower()}."
        elif avg_score < 0.6:
            # Developing
            narrative = f"Your idea is developing well. You have a solid handle on {strongest.display_label.lower()}. "
            if weakest.score < 0.4:
                narrative += f"The next frontier is {weakest.display_label.lower()}."
        elif avg_score < 0.8:
            # Solid
            narrative = f"Your idea has real depth. {strongest.display_label} is particularly strong. "
            if weakest.score < 0.6:
                narrative += f"Deepening {weakest.display_label.lower()} will make it even more robust."
        else:
            # Rich
            narrative = "Your idea is deeply developed across all dimensions. "
            narrative += "You are ready to move forward with confidence."

        # Expert mode: add dimension specifics
        if experience_mode == "expert":
            scores_str = ", ".join(
                f"{d.dimension.value}: {d.score:.0%}"
                for d in sorted(dimensions, key=lambda x: x.score, reverse=True)
            )
            narrative += f" [{scores_str}]"

        return narrative
