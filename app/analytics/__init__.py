"""
InDE MVP v3.0.3 - Analytics Module
Portfolio-level analytics and cross-pursuit intelligence.

Components:
- PortfolioIntelligenceEngine: Cross-pursuit analytics with weighted health
- CrossPursuitComparator: Benchmarking with percentile rankings
- InnovationEffectivenessScorecard: 7 organizational metrics
"""

from .portfolio_intelligence import PortfolioIntelligenceEngine
from .cross_pursuit_comparator import CrossPursuitComparator
from .effectiveness_scorecard import InnovationEffectivenessScorecard

__all__ = [
    "PortfolioIntelligenceEngine",
    "CrossPursuitComparator",
    "InnovationEffectivenessScorecard"
]
