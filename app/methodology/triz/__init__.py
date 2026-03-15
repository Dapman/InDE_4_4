"""
TRIZ (Theory of Inventive Problem Solving) Reference Data

This module provides:
- 40 Inventive Principles with coaching hints and examples
- Simplified Contradiction Matrix for coaching guidance
- TRIZ-Biomimicry Bridge for biological analog discovery
"""

from .inventive_principles import INVENTIVE_PRINCIPLES, get_principle
from .contradiction_matrix import TRIZ_PARAMETERS, CONTRADICTION_MATRIX, lookup_principles
from .biomimicry_bridge import TrizBiomimicryBridge

__all__ = [
    "INVENTIVE_PRINCIPLES",
    "get_principle",
    "TRIZ_PARAMETERS",
    "CONTRADICTION_MATRIX",
    "lookup_principles",
    "TrizBiomimicryBridge",
]
