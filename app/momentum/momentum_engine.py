"""
Momentum Management Engine — Core

Maintains running momentum state for each active coaching session,
calculates composite momentum scores, and provides context to the
ODICM for bridge selection and coaching tone adaptation.

The MME is a stateful, per-session service. One MME instance per
active coaching session. State is persisted to MongoDB at session
end via MomentumPersistence.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from .signal_collectors import MomentumSignals, collect_signals

logger = logging.getLogger(__name__)


# Signal weights — must sum to 1.0
SIGNAL_WEIGHTS = {
    "response_specificity": 0.30,
    "conversational_lean":  0.25,
    "temporal_commitment":  0.25,
    "idea_ownership":       0.20,
}

# Momentum tier thresholds (for bridge selection)
# These are internal labels only — never surfaced to innovator
MOMENTUM_TIERS = {
    "HIGH":    0.70,   # Strong forward energy — advance bridge
    "MEDIUM":  0.45,   # Moderate engagement — sustaining bridge
    "LOW":     0.25,   # Flagging energy — re-grounding bridge
    "CRITICAL": 0.0,   # Very low energy — reconnection bridge
}

# Rolling window: score is averaged over last N turns
ROLLING_WINDOW = 5


@dataclass
class MomentumSnapshot:
    """
    Point-in-time momentum state. Persisted at session end.
    Never exposed to the innovator — internal telemetry only.

    v4.4: Added selected_bridge_question_id and last_surfaced_insight_category
          for IML momentum pattern aggregation.
    """
    session_id: str
    pursuit_id: str
    gii_id: str                          # Hashed — never plain text
    recorded_at: datetime
    turn_count: int
    composite_score: float               # 0.0–1.0
    momentum_tier: str                   # HIGH/MEDIUM/LOW/CRITICAL
    signal_history: List[dict]           # Last ROLLING_WINDOW turns
    artifact_at_exit: Optional[str]      # Which artifact was active at exit
    bridge_delivered: bool               # Was a bridge fired in this session?
    bridge_responded: bool               # Did the innovator respond to it?
    exit_reason: str                     # "natural", "timeout", "bridge_exit"
    # v4.4: Fields for IML momentum pattern aggregation
    selected_bridge_question_id: Optional[str] = None   # Bridge ID selected by BridgeSelector
    last_surfaced_insight_category: Optional[str] = None  # IML insight category surfaced
    pursuit_stage: Optional[str] = None                 # Stage at snapshot time (VISION, etc.)


@dataclass
class SessionMomentumState:
    """
    Live momentum state for an active session.
    Maintained in memory; snapshotted to MongoDB at session end.
    """
    session_id: str
    pursuit_id: str
    gii_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    turn_count: int = 0
    signal_history: List[MomentumSignals] = field(default_factory=list)
    composite_score: float = 0.5         # Neutral starting point
    momentum_tier: str = "MEDIUM"
    last_artifact_active: Optional[str] = None
    bridge_delivered: bool = False
    bridge_responded: bool = False
    bridge_delivered_at_turn: Optional[int] = None


class MomentumManagementEngine:
    """
    Core MME — manages momentum state for a single coaching session.

    Usage:
        mme = MomentumManagementEngine(session_id, pursuit_id, gii_id)

        # After each innovator turn:
        context = mme.process_turn(message, artifact_active)

        # Inject context into ODICM:
        odicm_prompt = build_prompt(..., momentum_context=context)

        # At artifact completion:
        bridge = mme.select_bridge(completed_artifact, pursuit_summary)

        # At session end:
        snapshot = mme.snapshot(exit_reason)
    """

    def __init__(self, session_id: str, pursuit_id: str, gii_id: str):
        self.state = SessionMomentumState(
            session_id=session_id,
            pursuit_id=pursuit_id,
            gii_id=gii_id,
        )
        logger.debug(f"MME initialized: session={session_id}, pursuit={pursuit_id}")

    def process_turn(
        self,
        message: str,
        artifact_active: Optional[str] = None
    ) -> dict:
        """
        Process a single innovator turn. Extracts signals, updates
        composite score, returns momentum context for ODICM injection.

        Args:
            message: The innovator's message text
            artifact_active: Which artifact module is currently active
                             (internal key, e.g. "vision", "fear") — optional

        Returns:
            momentum_context dict for ODICM prompt injection
        """
        # Collect signals
        signals = collect_signals(message)

        # Update state
        self.state.turn_count += 1
        self.state.signal_history.append(signals)
        if artifact_active:
            self.state.last_artifact_active = artifact_active

        # Mark bridge responded if this is the turn after delivery
        if (self.state.bridge_delivered and
            not self.state.bridge_responded and
            self.state.bridge_delivered_at_turn is not None and
            self.state.turn_count == self.state.bridge_delivered_at_turn + 1):
            self.state.bridge_responded = True
            logger.debug(f"Bridge response received at turn {self.state.turn_count}")

        # Calculate composite score over rolling window
        self.state.composite_score = self._calculate_composite()
        self.state.momentum_tier = self._determine_tier(self.state.composite_score)

        context = self._build_context()
        logger.debug(
            f"Turn {self.state.turn_count}: score={self.state.composite_score:.2f} "
            f"tier={self.state.momentum_tier}"
        )
        return context

    def _calculate_composite(self) -> float:
        """
        Weighted composite of the most recent ROLLING_WINDOW signals.
        Earlier turns in window are slightly discounted (recency bias).
        """
        window = self.state.signal_history[-ROLLING_WINDOW:]
        if not window:
            return 0.5

        # Recency weights: most recent turn gets full weight,
        # earlier turns discounted by 10% per position back
        total_weighted = 0.0
        total_weight = 0.0

        for i, signals in enumerate(reversed(window)):
            recency_factor = 1.0 - (i * 0.10)
            turn_score = (
                signals.response_specificity * SIGNAL_WEIGHTS["response_specificity"] +
                signals.conversational_lean   * SIGNAL_WEIGHTS["conversational_lean"] +
                signals.temporal_commitment   * SIGNAL_WEIGHTS["temporal_commitment"] +
                signals.idea_ownership        * SIGNAL_WEIGHTS["idea_ownership"]
            )
            total_weighted += turn_score * recency_factor
            total_weight += recency_factor

        return round(total_weighted / total_weight, 3) if total_weight > 0 else 0.5

    def _determine_tier(self, score: float) -> str:
        if score >= MOMENTUM_TIERS["HIGH"]:    return "HIGH"
        if score >= MOMENTUM_TIERS["MEDIUM"]:  return "MEDIUM"
        if score >= MOMENTUM_TIERS["LOW"]:     return "LOW"
        return "CRITICAL"

    def _build_context(self) -> dict:
        """
        Builds the momentum context dict injected into ODICM prompts.
        Uses plain-English coaching guidance — never exposes scores.

        The ODICM receives this as coaching tone guidance, not metrics.
        It must never include score numbers or tier labels in coach output.
        """
        tier = self.state.momentum_tier

        COACHING_GUIDANCE = {
            "HIGH": (
                "The innovator is highly engaged — responding with detail and forward "
                "energy. The coach can move quickly, ask deeper questions, and challenge "
                "assumptions confidently. Trust that the innovator is with you."
            ),
            "MEDIUM": (
                "The innovator is engaged but not at full energy. Maintain warmth and "
                "curiosity. Keep questions open and generative. Avoid process-oriented "
                "language — stay in the idea space."
            ),
            "LOW": (
                "The innovator's energy is flagging. Prioritize reconnecting them with "
                "what's interesting about their idea. Ask a question that surfaces the "
                "most compelling aspect of what they've described. Do not advance the "
                "substance — re-ground first."
            ),
            "CRITICAL": (
                "The innovator may be disengaging. Do not push forward on any agenda. "
                "Ask a simple, genuine question about the idea itself — something that "
                "would be easy and satisfying to answer. The goal of the next turn is "
                "only to re-establish connection with the idea."
            ),
        }

        return {
            "momentum_tier": tier,              # Internal — for bridge selection
            "turn_count": self.state.turn_count,
            "composite_score": self.state.composite_score,
            "coaching_guidance": COACHING_GUIDANCE[tier],
            "bridge_delivered": self.state.bridge_delivered,
            "bridge_responded": self.state.bridge_responded,
            # Signal breakdown for admin telemetry (not in coach prompt)
            "_signals_latest": vars(self.state.signal_history[-1])
                                if self.state.signal_history else {},
        }

    def record_bridge_delivered(self) -> None:
        """Called by BridgeSelector when a bridge question is sent."""
        self.state.bridge_delivered = True
        self.state.bridge_delivered_at_turn = self.state.turn_count

    def snapshot(self, exit_reason: str = "natural") -> MomentumSnapshot:
        """
        Captures final momentum state for persistence at session end.
        """
        return MomentumSnapshot(
            session_id=self.state.session_id,
            pursuit_id=self.state.pursuit_id,
            gii_id=self.state.gii_id,
            recorded_at=datetime.utcnow(),
            turn_count=self.state.turn_count,
            composite_score=self.state.composite_score,
            momentum_tier=self.state.momentum_tier,
            signal_history=[vars(s) for s in self.state.signal_history[-ROLLING_WINDOW:]],
            artifact_at_exit=self.state.last_artifact_active,
            bridge_delivered=self.state.bridge_delivered,
            bridge_responded=self.state.bridge_responded,
            exit_reason=exit_reason,
        )
