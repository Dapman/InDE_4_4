"""
Depth Dimension System — v4.3

InDE measures pursuit depth across five dimensions:
  Clarity     — How well-defined is the innovator's idea?
  Empathy     — How well does the innovator understand who they're helping?
  Protection  — How many fears and risks have been surfaced and addressed?
  Evidence    — How much the innovator has tested and validated?
  Specificity — How specific and actionable has the idea become?

Each dimension is scored 0.0–1.0 by the depth calculator.
The Display Label Registry provides all innovator-facing language.
Internal dimension names (CLARITY, EMPATHY, etc.) are never surfaced to novice users.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


class DepthDimension(Enum):
    """The five dimensions of idea depth."""
    CLARITY = "clarity"
    EMPATHY = "empathy"
    PROTECTION = "protection"
    EVIDENCE = "evidence"
    SPECIFICITY = "specificity"


@dataclass
class DimensionScore:
    """Score for a single depth dimension."""
    dimension: DepthDimension
    score: float  # 0.0–1.0
    signal_count: int  # scaffolding elements contributing to this score
    strongest_signal: Optional[str]  # the key insight the innovator has produced
    display_label: str  # from Display Label Registry — never computed here
    richness_phrase: str  # e.g., "Your idea is getting sharper"


@dataclass
class PursuitDepthSnapshot:
    """Complete depth profile for a pursuit at a point in time."""
    pursuit_id: str
    overall_depth: float  # weighted composite of 5 dimensions
    dimensions: List[DimensionScore] = field(default_factory=list)
    top_strength: str = ""  # most developed dimension label
    active_frontier: str = ""  # dimension with most recent momentum
    depth_narrative: str = ""  # 1–2 sentence depth summary for innovator
    computed_at: str = ""  # ISO timestamp
    experience_mode: str = "novice"  # novice / intermediate / expert (caller injects)


# Dimension weights for overall_depth composite
DIMENSION_WEIGHTS = {
    DepthDimension.CLARITY: 0.25,
    DepthDimension.EMPATHY: 0.20,
    DepthDimension.PROTECTION: 0.20,
    DepthDimension.EVIDENCE: 0.20,
    DepthDimension.SPECIFICITY: 0.15,
}


# Scaffolding element → Dimension mapping
# Used by DepthCalculator to determine which elements contribute to which dimension
SCAFFOLDING_DIMENSION_MAP = {
    # CLARITY dimension
    "vision_statement": DepthDimension.CLARITY,
    "problem_definition": DepthDimension.CLARITY,
    "impact_statement": DepthDimension.CLARITY,
    "value_proposition": DepthDimension.CLARITY,
    
    # EMPATHY dimension
    "target_persona": DepthDimension.EMPATHY,
    "pain_point": DepthDimension.EMPATHY,
    "user_context": DepthDimension.EMPATHY,
    "stakeholder_map": DepthDimension.EMPATHY,
    
    # PROTECTION dimension
    "fear_register": DepthDimension.PROTECTION,
    "risk_assessment": DepthDimension.PROTECTION,
    "fear_addressed": DepthDimension.PROTECTION,
    "contingency_plan": DepthDimension.PROTECTION,
    
    # EVIDENCE dimension
    "hypothesis": DepthDimension.EVIDENCE,
    "test_plan": DepthDimension.EVIDENCE,
    "experiment_result": DepthDimension.EVIDENCE,
    "validation_insight": DepthDimension.EVIDENCE,
    
    # SPECIFICITY dimension
    "differentiation": DepthDimension.SPECIFICITY,
    "mvp_scope": DepthDimension.SPECIFICITY,
    "success_criteria": DepthDimension.SPECIFICITY,
    "timeline_milestone": DepthDimension.SPECIFICITY,
}


# Score tier thresholds for richness phrases
SCORE_TIERS = {
    (0.0, 0.2): "nascent",
    (0.2, 0.4): "emerging",
    (0.4, 0.6): "developing",
    (0.6, 0.8): "solid",
    (0.8, 1.01): "rich",
}


def get_score_tier(score: float) -> str:
    """Return the richness tier key for a given score."""
    for (low, high), tier in SCORE_TIERS.items():
        if low <= score < high:
            return tier
    return "nascent"
