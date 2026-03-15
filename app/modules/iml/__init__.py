"""
IML Momentum Pattern Module

InDE MVP v4.4.0 — The Learning Engine

This module extends the existing IML (Innovation Machine Learning) layer
with momentum pattern learning capabilities. It closes the intelligence
loop: momentum signals accumulated across pursuits become cross-innovator
patterns that inform coaching decisions.

Components:
  - MomentumPatternPersistence: MongoDB read/write for momentum_patterns
  - MomentumPatternEngine: Background aggregation of momentum snapshots
  - MomentumLiftScorer: Scores bridges/insights by momentum-lift potential

Design Principles:
  - Patterns are ALWAYS anonymized — no PII or pursuit-specific identifiers
  - Pattern aggregation runs in the background — never on coaching path
  - All scoring has graceful fallback to neutral when data is insufficient
  - The static bridge library is NEVER replaced — only augmented

© 2026 Yul Williams | InDEVerse, Incorporated
"""

from .momentum_pattern_persistence import (
    MomentumPatternType,
    make_context_hash,
    upsert_pattern,
    get_patterns_for_context,
    get_contribution_eligible_patterns,
    MIN_SAMPLE_FOR_CONFIDENCE,
    IKF_CONTRIBUTION_CONFIDENCE_THRESHOLD,
    SCHEMA_VERSION,
)

from .momentum_pattern_engine import MomentumPatternEngine

from .momentum_lift_scorer import (
    MomentumLiftScorer,
    NEUTRAL_SCORE,
)

__all__ = [
    # Persistence
    "MomentumPatternType",
    "make_context_hash",
    "upsert_pattern",
    "get_patterns_for_context",
    "get_contribution_eligible_patterns",
    "MIN_SAMPLE_FOR_CONFIDENCE",
    "IKF_CONTRIBUTION_CONFIDENCE_THRESHOLD",
    "SCHEMA_VERSION",
    # Engine
    "MomentumPatternEngine",
    # Scorer
    "MomentumLiftScorer",
    "NEUTRAL_SCORE",
]
