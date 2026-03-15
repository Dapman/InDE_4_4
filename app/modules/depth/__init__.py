"""
InDE v4.3 — Depth Dimension System

Provides depth-framed progress measurement for innovators:
- DepthDimension: The five dimensions of idea depth
- DepthCalculator: Maps scaffolding state to depth scores
- PursuitDepthSnapshot: Complete depth profile for a pursuit
"""

from .depth_schemas import (
    DepthDimension,
    DimensionScore,
    PursuitDepthSnapshot,
    DIMENSION_WEIGHTS,
)
from .depth_calculator import DepthCalculator

__all__ = [
    "DepthDimension",
    "DimensionScore",
    "PursuitDepthSnapshot",
    "DIMENSION_WEIGHTS",
    "DepthCalculator",
]
