"""
InDE MVP v3.0.1 - Temporal Intelligence Module (TIM)

The TIM provides time-based tracking, velocity monitoring, and timeline
visualization for innovation pursuits. All temporal data uses IKF-compatible
standards (ISO 8601 timestamps, universal phase taxonomy).

Components:
- TimeAllocationEngine: Phase-based timeline distribution
- VelocityTracker: Progress pace monitoring (elements/week)
- TemporalEventLogger: IKF-compatible event stream
- PhaseManager: Phase transition management

IKF Standards Enforced:
- All timestamps: ISO 8601 format ('2026-02-13T14:30:00Z')
- Phase taxonomy: VISION, DE_RISK, DEPLOY (universal)
- Velocity units: elements/week (standardized)
"""

from tim.allocation_engine import TimeAllocationEngine
from tim.velocity_tracker import VelocityTracker
from tim.event_logger import TemporalEventLogger
from tim.phase_manager import PhaseManager

__all__ = [
    'TimeAllocationEngine',
    'VelocityTracker',
    'TemporalEventLogger',
    'PhaseManager'
]
