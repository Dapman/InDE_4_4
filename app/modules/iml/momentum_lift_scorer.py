"""
Momentum Lift Scorer

InDE MVP v4.4.0 — The Learning Engine

Scores IML insight and bridge question candidates by their estimated
momentum-lifting potential, derived from the momentum_patterns collection.

Used by:
  1. AdaptiveKnowledgeSurfacingEngine — ranks insights partly by lift score
  2. MME BridgeSelector (via IMLFeedbackReceiver) — selects bridge by lift score

Scoring is additive to existing relevance/novelty criteria — it does not
replace them. If no momentum pattern data exists for a context, the scorer
returns a neutral score (0.5) and the existing selection logic is unchanged.

The scorer is intentionally stateless — it reads from MongoDB on each call.
Caching can be added in a future build if latency becomes a concern.

© 2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from typing import List, Dict, Any

from .momentum_pattern_persistence import (
    MomentumPatternType,
    make_context_hash,
    get_patterns_for_context,
)

logger = logging.getLogger("inde.iml.momentum_lift_scorer")

NEUTRAL_SCORE = 0.5          # Returned when no pattern data is available
LIFT_SCALE_FACTOR = 2.0      # Amplifies delta for scoring (delta range ≈ -0.5 to +0.5)
MAX_SCORE = 1.0
MIN_SCORE = 0.0


class MomentumLiftScorer:
    """
    Scores bridge questions and insights by momentum-lifting potential.
    Returns a float in [0.0, 1.0]. Higher = more likely to lift momentum.
    """

    def score_bridge_question(
        self,
        bridge_question_id: str,
        pursuit_stage: str,
        artifact_type: str,
        momentum_tier: str,
    ) -> float:
        """
        Score a bridge question by historical momentum-lift for this context.
        Returns NEUTRAL_SCORE if insufficient pattern data exists.
        """
        try:
            ctx_hash = make_context_hash(pursuit_stage, artifact_type, momentum_tier)
            patterns = get_patterns_for_context(
                ctx_hash,
                pattern_types=[
                    MomentumPatternType.BRIDGE_LIFT.value,
                    MomentumPatternType.BRIDGE_STALL.value,
                ],
            )
            matching = [
                p for p in patterns
                if p.get("bridge_question_id") == bridge_question_id
            ]
            if not matching:
                return NEUTRAL_SCORE
            best = max(matching, key=lambda p: p.get("confidence_score", 0))
            raw = NEUTRAL_SCORE + (best.get("momentum_lift_delta", 0) * LIFT_SCALE_FACTOR)
            return round(max(MIN_SCORE, min(MAX_SCORE, raw)), 4)
        except Exception as e:
            logger.warning(f"Bridge lift score failed for {bridge_question_id}: {e}")
            return NEUTRAL_SCORE

    def score_insight(
        self,
        insight_category: str,
        pursuit_stage: str,
        artifact_type: str,
        momentum_tier: str,
    ) -> float:
        """
        Score an IML insight category by historical momentum-lift for this context.
        Returns NEUTRAL_SCORE if insufficient pattern data exists.
        """
        try:
            ctx_hash = make_context_hash(pursuit_stage, artifact_type, momentum_tier)
            patterns = get_patterns_for_context(
                ctx_hash,
                pattern_types=[
                    MomentumPatternType.INSIGHT_LIFT.value,
                    MomentumPatternType.INSIGHT_STALL.value,
                ],
            )
            matching = [
                p for p in patterns
                if p.get("insight_category") == insight_category
            ]
            if not matching:
                return NEUTRAL_SCORE
            best = max(matching, key=lambda p: p.get("confidence_score", 0))
            raw = NEUTRAL_SCORE + (best.get("momentum_lift_delta", 0) * LIFT_SCALE_FACTOR)
            return round(max(MIN_SCORE, min(MAX_SCORE, raw)), 4)
        except Exception as e:
            logger.warning(f"Insight lift score failed for {insight_category}: {e}")
            return NEUTRAL_SCORE

    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        context: dict,
        candidate_type: str = "bridge",
    ) -> List[Dict[str, Any]]:
        """
        Rank a list of candidates by momentum-lift score.
        Each candidate must have: 'id' (bridge_question_id or insight_category).
        Returns the same list, sorted descending by momentum_lift_score.
        Adds 'momentum_lift_score' field to each candidate.

        candidate_type: "bridge" | "insight"
        context keys: pursuit_stage, artifact_type, momentum_tier
        """
        pursuit_stage = context.get("pursuit_stage", "unknown")
        artifact_type = context.get("artifact_type", "unknown")
        momentum_tier = context.get("momentum_tier", "MEDIUM")

        for c in candidates:
            cid = c.get("id", "")
            if candidate_type == "bridge":
                c["momentum_lift_score"] = self.score_bridge_question(
                    cid, pursuit_stage, artifact_type, momentum_tier
                )
            else:
                c["momentum_lift_score"] = self.score_insight(
                    cid, pursuit_stage, artifact_type, momentum_tier
                )
        return sorted(candidates, key=lambda x: x.get("momentum_lift_score", 0), reverse=True)
