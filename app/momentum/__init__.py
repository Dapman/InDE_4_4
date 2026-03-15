"""
Momentum Management Engine (MME)

InDE MVP v4.1.0 — The Momentum Engine

The MME is an invisible intelligence layer that runs alongside the ODICM,
continuously observing conversational signals to assess the innovator's
forward energy state. It uses this assessment to:

  1. Select the bridge question most likely to sustain momentum at
     each artifact completion event (replacing v4.0's random selection)

  2. Inject momentum context into ODICM turn generation, allowing the
     coach to be subtly responsive to the innovator's energy state

  3. Capture momentum trajectories for IML pattern learning and
     retrospective insight

Design principles:
  - The MME is NEVER visible to the innovator
  - Momentum score is internal state — it never surfaces as a metric
  - The right technique is pursuit-specific and innovator-specific
  - Every session must end with more forward energy than it started with

© 2026 Yul Williams | InDEVerse, Incorporated
"""

from .momentum_engine import MomentumManagementEngine
from .bridge_selector import BridgeSelector
from .bridge_library import BRIDGE_LIBRARY

__all__ = ["MomentumManagementEngine", "BridgeSelector", "BRIDGE_LIBRARY"]
