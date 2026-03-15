"""
IML Feedback Receiver

InDE MVP v4.4.0 — The Learning Engine

Closes the intelligence feedback loop: IML momentum pattern recommendations
flow into the MME's bridge question selection.

The IMLFeedbackReceiver is called by BridgeSelector BEFORE it consults the
static bridge library. If a momentum-informed recommendation is available
for the current context and exceeds the minimum lift threshold, it is
returned as the selected bridge. If IML is unavailable or no strong
recommendation exists, BridgeSelector falls back to the static library —
identical behavior to v4.3.

Circuit-breaker behavior:
  - If IML query fails 3 consecutive times, the receiver enters OPEN state
  - In OPEN state, all queries return None immediately (no IML call attempted)
  - After RECOVERY_INTERVAL seconds, receiver enters HALF-OPEN state
  - First successful IML call in HALF-OPEN closes the circuit

This ensures that IML availability does not create coaching latency.

© 2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
import time
from enum import Enum
from typing import Optional, List

logger = logging.getLogger("inde.momentum.iml_feedback")

# Import guarded — IML module may not be initialized at startup
try:
    from modules.iml.momentum_lift_scorer import MomentumLiftScorer
    from modules.iml.momentum_pattern_persistence import get_patterns_for_context, MomentumPatternType
    IML_AVAILABLE = True
except ImportError:
    IML_AVAILABLE = False
    logger.warning("IML module not available — IMLFeedbackReceiver in static fallback mode")

MIN_LIFT_THRESHOLD = 0.62    # Minimum momentum_lift_score to prefer IML recommendation
CIRCUIT_OPEN_AFTER = 3       # Consecutive failures before circuit opens
RECOVERY_INTERVAL = 300      # Seconds before half-open retry (5 minutes)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class IMLFeedbackReceiver:
    """
    Queries IML for the best bridge question based on momentum patterns.
    Returns None if no strong recommendation or if circuit is open.
    """

    def __init__(self):
        self._scorer = MomentumLiftScorer() if IML_AVAILABLE else None
        self._failure_count = 0
        self._circuit_state = CircuitState.CLOSED
        self._last_failure_time: Optional[float] = None

    def get_recommended_bridge(
        self,
        available_bridge_ids: List[str],
        pursuit_stage: str,
        artifact_type: str,
        momentum_tier: str,
    ) -> Optional[str]:
        """
        Return the bridge_question_id with the highest predicted momentum lift,
        or None if no recommendation exceeds MIN_LIFT_THRESHOLD.

        available_bridge_ids — the candidate set from bridge_library for this context
        """
        if not IML_AVAILABLE or self._scorer is None:
            return None
        if not self._check_circuit():
            return None
        try:
            context = {
                "pursuit_stage": pursuit_stage,
                "artifact_type": artifact_type,
                "momentum_tier": momentum_tier,
            }
            candidates = [{"id": bid} for bid in available_bridge_ids]
            ranked = self._scorer.rank_candidates(candidates, context, candidate_type="bridge")
            if ranked and ranked[0].get("momentum_lift_score", 0) >= MIN_LIFT_THRESHOLD:
                self._record_success()
                return ranked[0]["id"]
            self._record_success()
            return None
        except Exception as e:
            logger.warning(f"IML bridge recommendation failed: {e}")
            self._record_failure()
            return None

    def _check_circuit(self) -> bool:
        """Return True if the circuit allows a call; False if OPEN."""
        if self._circuit_state == CircuitState.CLOSED:
            return True
        if self._circuit_state == CircuitState.OPEN:
            if (
                self._last_failure_time
                and time.time() - self._last_failure_time >= RECOVERY_INTERVAL
            ):
                self._circuit_state = CircuitState.HALF_OPEN
                logger.info("IMLFeedbackReceiver circuit entering HALF_OPEN state")
                return True
            return False
        return True  # HALF_OPEN — allow one call

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= CIRCUIT_OPEN_AFTER:
            self._circuit_state = CircuitState.OPEN
            logger.warning(
                f"IMLFeedbackReceiver circuit OPEN after {self._failure_count} failures"
            )

    def _record_success(self) -> None:
        self._failure_count = 0
        if self._circuit_state == CircuitState.HALF_OPEN:
            self._circuit_state = CircuitState.CLOSED
            logger.info("IMLFeedbackReceiver circuit CLOSED (recovered)")

    @property
    def circuit_state(self) -> str:
        return self._circuit_state.value
