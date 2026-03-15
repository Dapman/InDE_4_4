"""
InDE MVP v3.0.2 - Intelligence Layer Module
Predictive intelligence and health monitoring for innovation pursuits.

Components:
- HealthMonitor: Real-time pursuit health scoring (0-100) with 5 zones
- TemporalPatternIntelligence: Enriched IML pattern matching with temporal signals
- PredictiveGuidanceEngine: Forward-looking predictions based on historical patterns
- RiskDetector: Temporal risk detection across three time horizons

Design Principles:
- All intelligence is ADVISORY - no auto-termination
- GPU acceleration where beneficial (RTX3050 compatible)
- IKF-compatible ISO 8601 timestamps throughout
- Invisible scaffolding - methodology never exposed to innovator
"""

from .health_monitor import HealthMonitor
from .temporal_patterns import TemporalPatternIntelligence
from .predictive_guidance import PredictiveGuidanceEngine
from .risk_detector import TemporalRiskDetector

__all__ = [
    "HealthMonitor",
    "TemporalPatternIntelligence",
    "PredictiveGuidanceEngine",
    "TemporalRiskDetector"
]
