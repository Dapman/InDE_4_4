"""
InDE MVP v3.4 - Coaching Convergence Protocol
Four-phase convergence model with signal detection, criteria evaluation, and outcome capture.

v4.1 Enhancement: Momentum-aware convergence threshold adjustment.
High momentum → slightly easier to converge (innovator is engaged)
Low momentum → harder to converge (re-ground first, don't close flagging session)

Convergence Phases:
1. EXPLORING - Open-ended discovery, no convergence signals
2. CONSOLIDATING - Convergence detected, awaiting criteria
3. COMMITTED - Criteria met, capturing outcomes
4. HANDED_OFF - Session complete, ready for next activity

Signal Types:
- repetition: Semantic similarity between recent messages
- decision_language: "I think we should...", "My decision is..."
- summary_requests: Innovator asks coach to summarize, recap
- satisfaction: Positive affirmation, closure language
- time_investment: Session duration relative to expected
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from core.config import (
    CONVERGENCE_CONFIG, CONVERGENCE_PHASES, CONVERGENCE_OUTCOME_TYPES,
    CONVERGENCE_CRITERIA_TYPES, CRITERIA_ENFORCEMENT
)
from core.database import db

logger = logging.getLogger("inde.coaching.convergence")


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class ConvergencePhase(str, Enum):
    EXPLORING = "EXPLORING"
    CONSOLIDATING = "CONSOLIDATING"
    COMMITTED = "COMMITTED"
    HANDED_OFF = "HANDED_OFF"


class OutcomeType(str, Enum):
    DECISION = "DECISION"
    INSIGHT = "INSIGHT"
    HYPOTHESIS = "HYPOTHESIS"
    COMMITMENT = "COMMITMENT"
    REFINEMENT = "REFINEMENT"


@dataclass
class ConvergenceSignal:
    """A single convergence signal reading."""
    signal_type: str
    score: float
    evidence: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "signal_type": self.signal_type,
            "score": self.score,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ConvergenceOutcome:
    """A captured convergence outcome."""
    outcome_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    outcome_type: str = "DECISION"
    summary: str = ""
    artifact_ref: Optional[str] = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    captured_by: str = ""  # user_id or "coach"

    def to_dict(self) -> Dict:
        return {
            "outcome_id": self.outcome_id,
            "outcome_type": self.outcome_type,
            "summary": self.summary,
            "artifact_ref": self.artifact_ref,
            "captured_at": self.captured_at.isoformat(),
            "captured_by": self.captured_by
        }


@dataclass
class TransitionCriterion:
    """A criterion for phase transition."""
    criterion_type: str
    description: str
    is_satisfied: bool = False
    satisfied_at: Optional[datetime] = None
    evidence: str = ""

    def to_dict(self) -> Dict:
        return {
            "criterion_type": self.criterion_type,
            "description": self.description,
            "is_satisfied": self.is_satisfied,
            "satisfied_at": self.satisfied_at.isoformat() if self.satisfied_at else None,
            "evidence": self.evidence
        }


# =============================================================================
# SIGNAL DETECTOR
# =============================================================================

class ConvergenceSignalDetector:
    """
    Detects convergence signals in coaching conversation.

    Analyzes messages for:
    - Semantic repetition (similar content appearing)
    - Decision language ("I've decided...", "My choice is...")
    - Summary requests ("Can you recap...", "What have we covered...")
    - Satisfaction signals ("That makes sense", "I'm good with that")
    - Time investment (session duration vs expected)
    """

    # Decision language patterns
    DECISION_PATTERNS = [
        "i've decided", "i have decided", "my decision is",
        "i think we should", "i'm going to", "i will",
        "let's go with", "i choose", "my choice is",
        "that's what i'll do", "i'm committed to"
    ]

    # Summary request patterns
    SUMMARY_PATTERNS = [
        "can you summarize", "can you recap", "what have we covered",
        "let me make sure i understand", "so to summarize",
        "in summary", "to wrap up", "before we finish"
    ]

    # Satisfaction patterns
    SATISFACTION_PATTERNS = [
        "that makes sense", "i'm good with that", "sounds good",
        "i understand now", "that's helpful", "perfect",
        "i feel ready", "i'm confident", "i'm satisfied"
    ]

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or CONVERGENCE_CONFIG.get("signal_weights", {
            "repetition": 0.25,
            "decision_language": 0.30,
            "summary_requests": 0.15,
            "satisfaction": 0.15,
            "time_investment": 0.15
        })

    def detect_signals(
        self,
        message: str,
        conversation_history: List[Dict],
        session_start_time: datetime,
        expected_duration_minutes: int = 30
    ) -> List[ConvergenceSignal]:
        """
        Detect convergence signals in a message.

        Args:
            message: Current user message
            conversation_history: Recent conversation turns
            session_start_time: When the session started
            expected_duration_minutes: Expected session duration

        Returns:
            List of detected signals with scores
        """
        signals = []
        message_lower = message.lower()

        # 1. Decision language detection
        decision_score, decision_evidence = self._detect_decision_language(message_lower)
        if decision_score > 0:
            signals.append(ConvergenceSignal(
                signal_type="decision_language",
                score=decision_score,
                evidence=decision_evidence
            ))

        # 2. Summary request detection
        summary_score, summary_evidence = self._detect_summary_request(message_lower)
        if summary_score > 0:
            signals.append(ConvergenceSignal(
                signal_type="summary_requests",
                score=summary_score,
                evidence=summary_evidence
            ))

        # 3. Satisfaction detection
        satisfaction_score, satisfaction_evidence = self._detect_satisfaction(message_lower)
        if satisfaction_score > 0:
            signals.append(ConvergenceSignal(
                signal_type="satisfaction",
                score=satisfaction_score,
                evidence=satisfaction_evidence
            ))

        # 4. Repetition detection (semantic similarity)
        if len(conversation_history) >= 3:
            repetition_score = self._detect_repetition(message, conversation_history)
            if repetition_score > 0.3:  # Only report meaningful repetition
                signals.append(ConvergenceSignal(
                    signal_type="repetition",
                    score=repetition_score,
                    evidence="Content repeating from earlier in conversation"
                ))

        # 5. Time investment
        elapsed_minutes = (datetime.now(timezone.utc) - session_start_time).total_seconds() / 60
        time_ratio = min(elapsed_minutes / expected_duration_minutes, 1.5)
        if time_ratio >= 0.7:  # At least 70% of expected time
            signals.append(ConvergenceSignal(
                signal_type="time_investment",
                score=min(time_ratio, 1.0),
                evidence=f"Session has been active for {elapsed_minutes:.0f} minutes"
            ))

        return signals

    def _detect_decision_language(self, message: str) -> tuple:
        """Detect decision-making language."""
        for pattern in self.DECISION_PATTERNS:
            if pattern in message:
                return (0.8, pattern)
        return (0.0, "")

    def _detect_summary_request(self, message: str) -> tuple:
        """Detect summary/recap requests."""
        for pattern in self.SUMMARY_PATTERNS:
            if pattern in message:
                return (0.9, pattern)
        return (0.0, "")

    def _detect_satisfaction(self, message: str) -> tuple:
        """Detect satisfaction/closure signals."""
        for pattern in self.SATISFACTION_PATTERNS:
            if pattern in message:
                return (0.7, pattern)
        return (0.0, "")

    def _detect_repetition(self, message: str, history: List[Dict]) -> float:
        """
        Detect semantic repetition in conversation.

        Simple approach: word overlap between current message and recent history.
        In production, would use embeddings for semantic similarity.
        """
        message_words = set(message.lower().split())
        if len(message_words) < 5:
            return 0.0

        # Look at last 5 user messages
        recent_user_messages = [
            turn.get("user_message", "")
            for turn in history[-10:]
            if turn.get("role") == "user" or turn.get("user_message")
        ][-5:]

        if not recent_user_messages:
            return 0.0

        # Calculate overlap with each recent message
        max_overlap = 0.0
        for prev_message in recent_user_messages:
            prev_words = set(prev_message.lower().split())
            if len(prev_words) >= 5:
                overlap = len(message_words & prev_words) / len(message_words | prev_words)
                max_overlap = max(max_overlap, overlap)

        return max_overlap

    def calculate_composite_score(self, signals: List[ConvergenceSignal]) -> float:
        """
        Calculate weighted composite convergence score.

        Returns:
            Score between 0.0 and 1.0
        """
        if not signals:
            return 0.0

        # Map signals to their weighted scores
        signal_scores = {s.signal_type: s.score for s in signals}

        composite = 0.0
        for signal_type, weight in self.weights.items():
            score = signal_scores.get(signal_type, 0.0)
            composite += score * weight

        return min(composite, 1.0)


# =============================================================================
# STATE MACHINE
# =============================================================================

class ConvergenceStateMachine:
    """
    Manages convergence phase transitions.

    State Transitions:
    - EXPLORING → CONSOLIDATING: When composite signal score exceeds threshold
    - CONSOLIDATING → COMMITTED: When required criteria are satisfied
    - COMMITTED → HANDED_OFF: When outcomes are captured and handoff initiated
    """

    def __init__(
        self,
        session_id: str,
        pursuit_id: str,
        user_id: str,
        methodology_archetype: str = "lean_startup",
        enforcement: str = "advisory"
    ):
        self.session_id = session_id
        self.pursuit_id = pursuit_id
        self.user_id = user_id
        self.methodology_archetype = methodology_archetype
        self.enforcement = enforcement

        self._current_phase = ConvergencePhase.EXPLORING
        self._signal_history: List[ConvergenceSignal] = []
        self._criteria: List[TransitionCriterion] = []
        self._outcomes: List[ConvergenceOutcome] = []
        self._initiated_at = datetime.now(timezone.utc)
        self._phase_history: List[Dict] = []

    @property
    def current_phase(self) -> ConvergencePhase:
        return self._current_phase

    @property
    def signal_history(self) -> List[ConvergenceSignal]:
        return self._signal_history

    @property
    def outcomes(self) -> List[ConvergenceOutcome]:
        return self._outcomes

    def record_signals(self, signals: List[ConvergenceSignal]):
        """Record detected signals."""
        self._signal_history.extend(signals)

    def can_transition_to(self, target_phase: ConvergencePhase) -> bool:
        """Check if transition to target phase is allowed."""
        valid_transitions = {
            ConvergencePhase.EXPLORING: [ConvergencePhase.CONSOLIDATING],
            ConvergencePhase.CONSOLIDATING: [ConvergencePhase.COMMITTED, ConvergencePhase.EXPLORING],
            ConvergencePhase.COMMITTED: [ConvergencePhase.HANDED_OFF, ConvergencePhase.CONSOLIDATING],
            ConvergencePhase.HANDED_OFF: []  # Terminal state
        }
        return target_phase in valid_transitions.get(self._current_phase, [])

    def transition_to(self, target_phase: ConvergencePhase, reason: str = "") -> bool:
        """
        Transition to a new phase.

        Args:
            target_phase: The phase to transition to
            reason: Reason for the transition

        Returns:
            True if transition succeeded
        """
        if not self.can_transition_to(target_phase):
            logger.warning(
                f"Invalid transition: {self._current_phase} → {target_phase} "
                f"for session {self.session_id}"
            )
            return False

        # Record the transition
        self._phase_history.append({
            "from_phase": self._current_phase.value,
            "to_phase": target_phase.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        old_phase = self._current_phase
        self._current_phase = target_phase

        logger.info(
            f"Convergence transition: {old_phase.value} → {target_phase.value} "
            f"for session {self.session_id}"
        )

        return True

    def check_convergence(
        self,
        composite_score: float,
        momentum_context: Optional[Dict] = None
    ) -> bool:
        """
        Check if convergence threshold is met.

        v4.1 Enhancement: Momentum-aware threshold adjustment.
        High momentum (HIGH tier) → slightly lower convergence threshold
        (the innovator is engaged and ready to move — don't hold them back).
        Low momentum (LOW/CRITICAL tier) → higher convergence threshold
        (don't converge a flagging session — re-ground first).

        Args:
            composite_score: The weighted signal score
            momentum_context: v4.1 - Optional momentum context from MME

        Returns:
            True if convergence should be triggered
        """
        base_threshold = CONVERGENCE_CONFIG.get("threshold", 0.7)

        # v4.1: Momentum-based threshold adjustment
        threshold_adjustment = 0.0
        if momentum_context:
            tier = momentum_context.get("momentum_tier", "MEDIUM")
            TIER_THRESHOLD_ADJUSTMENTS = {
                "HIGH":     -0.05,   # Slightly easier to converge
                "MEDIUM":    0.00,   # No adjustment
                "LOW":      +0.08,   # Harder to converge — re-ground first
                "CRITICAL": +0.15,   # Much harder — this session needs care
            }
            threshold_adjustment = TIER_THRESHOLD_ADJUSTMENTS.get(tier, 0.0)

        effective_threshold = base_threshold + threshold_adjustment
        return composite_score >= effective_threshold

    def add_criterion(self, criterion: TransitionCriterion):
        """Add a transition criterion."""
        self._criteria.append(criterion)

    def satisfy_criterion(self, criterion_type: str, evidence: str = "") -> bool:
        """Mark a criterion as satisfied."""
        for criterion in self._criteria:
            if criterion.criterion_type == criterion_type and not criterion.is_satisfied:
                criterion.is_satisfied = True
                criterion.satisfied_at = datetime.now(timezone.utc)
                criterion.evidence = evidence
                return True
        return False

    def are_criteria_met(self) -> bool:
        """Check if all required criteria are satisfied."""
        if not self._criteria:
            return True  # No criteria = automatically met

        if self.enforcement == "strict":
            return all(c.is_satisfied for c in self._criteria)
        else:
            # Advisory/suggestive: Just need coach checkpoint
            return any(
                c.is_satisfied
                for c in self._criteria
                if c.criterion_type == "COACH_CHECKPOINT"
            ) if any(c.criterion_type == "COACH_CHECKPOINT" for c in self._criteria) else True

    def capture_outcome(self, outcome: ConvergenceOutcome):
        """Capture a convergence outcome."""
        self._outcomes.append(outcome)

    def get_state(self) -> Dict:
        """Get the full state for persistence."""
        return {
            "session_id": self.session_id,
            "pursuit_id": self.pursuit_id,
            "user_id": self.user_id,
            "current_phase": self._current_phase.value,
            "methodology_archetype": self.methodology_archetype,
            "enforcement": self.enforcement,
            "signal_history": [s.to_dict() for s in self._signal_history],
            "criteria": [c.to_dict() for c in self._criteria],
            "outcomes_captured": [o.to_dict() for o in self._outcomes],
            "phase_history": self._phase_history,
            "initiated_at": self._initiated_at.isoformat()
        }


# =============================================================================
# ORCHESTRATOR
# =============================================================================

class ConvergenceOrchestrator:
    """
    Coordinates the convergence workflow.

    Responsibilities:
    - Process messages through signal detection
    - Manage state machine transitions
    - Generate convergence-aware coaching prompts
    - Capture and persist outcomes
    """

    def __init__(self, db_instance=None):
        self._db = db_instance or db
        self._detector = ConvergenceSignalDetector()
        self._sessions: Dict[str, ConvergenceStateMachine] = {}

    def get_or_create_session(
        self,
        session_id: str,
        pursuit_id: str,
        user_id: str,
        methodology_archetype: str = "lean_startup"
    ) -> ConvergenceStateMachine:
        """Get existing or create new convergence session."""
        if session_id not in self._sessions:
            # Check database for existing session
            existing = self._db.get_convergence_session(session_id)
            if existing:
                # Restore from database
                machine = ConvergenceStateMachine(
                    session_id=session_id,
                    pursuit_id=pursuit_id,
                    user_id=user_id,
                    methodology_archetype=existing.get("methodology_archetype", methodology_archetype)
                )
                machine._current_phase = ConvergencePhase(existing.get("current_phase", "EXPLORING"))
                self._sessions[session_id] = machine
            else:
                # Create new session
                machine = ConvergenceStateMachine(
                    session_id=session_id,
                    pursuit_id=pursuit_id,
                    user_id=user_id,
                    methodology_archetype=methodology_archetype
                )
                self._sessions[session_id] = machine

                # Persist to database
                self._db.create_convergence_session(
                    session_id=session_id,
                    pursuit_id=pursuit_id,
                    user_id=user_id,
                    methodology_archetype=methodology_archetype
                )

        return self._sessions[session_id]

    def process_message(
        self,
        session_id: str,
        message: str,
        conversation_history: List[Dict],
        session_start_time: datetime,
        momentum_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process a message through convergence detection.

        Args:
            session_id: The coaching session ID
            message: The user's message
            conversation_history: Recent conversation turns
            session_start_time: When the session started
            momentum_context: v4.1 - Optional momentum context from MME

        Returns:
            Dict with convergence state and any recommended actions
        """
        if session_id not in self._sessions:
            return {"convergence_active": False}

        machine = self._sessions[session_id]

        # Detect signals
        signals = self._detector.detect_signals(
            message=message,
            conversation_history=conversation_history,
            session_start_time=session_start_time
        )

        # Record signals
        machine.record_signals(signals)

        # Calculate composite score
        composite_score = self._detector.calculate_composite_score(signals)

        # Check for phase transitions
        result = {
            "convergence_active": True,
            "current_phase": machine.current_phase.value,
            "composite_score": composite_score,
            "signals_detected": [s.to_dict() for s in signals],
            "recommended_action": None,
            "transition_occurred": False
        }

        # Handle transitions based on current phase
        if machine.current_phase == ConvergencePhase.EXPLORING:
            # v4.1: Pass momentum_context for momentum-aware threshold
            if machine.check_convergence(composite_score, momentum_context):
                if machine.transition_to(ConvergencePhase.CONSOLIDATING, "Signal threshold exceeded"):
                    result["transition_occurred"] = True
                    result["recommended_action"] = "confirm_convergence"
                    result["current_phase"] = ConvergencePhase.CONSOLIDATING.value

        elif machine.current_phase == ConvergencePhase.CONSOLIDATING:
            if machine.are_criteria_met():
                result["recommended_action"] = "capture_outcomes"
            else:
                result["recommended_action"] = "check_criteria"

        # Persist state
        self._db.update_convergence_session(session_id, machine.get_state())

        return result

    def explicit_convergence_trigger(
        self,
        session_id: str,
        source: str = "ui_button"
    ) -> Dict[str, Any]:
        """
        Handle explicit convergence trigger from UI or message.

        Args:
            session_id: The coaching session ID
            source: Source of trigger ("ui_button" or "message")

        Returns:
            Dict with transition result
        """
        if session_id not in self._sessions:
            return {"success": False, "error": "Session not found"}

        machine = self._sessions[session_id]

        if machine.current_phase == ConvergencePhase.EXPLORING:
            if machine.transition_to(ConvergencePhase.CONSOLIDATING, f"Explicit trigger: {source}"):
                self._db.update_convergence_session(session_id, machine.get_state())
                return {
                    "success": True,
                    "new_phase": ConvergencePhase.CONSOLIDATING.value
                }

        return {"success": False, "error": "Cannot trigger convergence from current phase"}

    def capture_outcome(
        self,
        session_id: str,
        outcome_type: str,
        summary: str,
        artifact_ref: str = None,
        captured_by: str = "user"
    ) -> Dict[str, Any]:
        """
        Capture a convergence outcome.

        Args:
            session_id: The coaching session ID
            outcome_type: Type of outcome (DECISION, INSIGHT, etc.)
            summary: Summary of the outcome
            artifact_ref: Reference to related artifact
            captured_by: Who captured the outcome

        Returns:
            Dict with captured outcome
        """
        if session_id not in self._sessions:
            return {"success": False, "error": "Session not found"}

        machine = self._sessions[session_id]

        outcome = ConvergenceOutcome(
            outcome_type=outcome_type,
            summary=summary,
            artifact_ref=artifact_ref,
            captured_by=captured_by
        )

        machine.capture_outcome(outcome)
        self._db.add_convergence_outcome(session_id, outcome.to_dict())

        # If in CONSOLIDATING and criteria met, can move to COMMITTED
        if machine.current_phase == ConvergencePhase.CONSOLIDATING and machine.are_criteria_met():
            machine.transition_to(ConvergencePhase.COMMITTED, "Outcome captured, criteria met")
            self._db.update_convergence_session(session_id, machine.get_state())

        return {
            "success": True,
            "outcome_id": outcome.outcome_id,
            "current_phase": machine.current_phase.value
        }

    def complete_handoff(
        self,
        session_id: str,
        next_activity: str = None
    ) -> Dict[str, Any]:
        """
        Complete the convergence handoff.

        Args:
            session_id: The coaching session ID
            next_activity: What activity follows (optional)

        Returns:
            Dict with handoff result
        """
        if session_id not in self._sessions:
            return {"success": False, "error": "Session not found"}

        machine = self._sessions[session_id]

        if machine.current_phase == ConvergencePhase.COMMITTED:
            if machine.transition_to(ConvergencePhase.HANDED_OFF, f"Handoff to: {next_activity or 'next session'}"):
                self._db.update_convergence_session(session_id, {
                    **machine.get_state(),
                    "completed_at": datetime.now(timezone.utc)
                })
                return {
                    "success": True,
                    "outcomes_count": len(machine.outcomes),
                    "next_activity": next_activity
                }

        return {"success": False, "error": "Not ready for handoff"}

    def get_convergence_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get convergence context for coaching prompt injection.

        Returns context suitable for including in ODICM prompts.
        """
        if session_id not in self._sessions:
            return {}

        machine = self._sessions[session_id]

        context = {
            "phase": machine.current_phase.value,
            "outcomes_captured": len(machine.outcomes),
            "recent_signals": [s.to_dict() for s in machine.signal_history[-5:]],
        }

        # Add phase-specific guidance
        phase_guidance = {
            ConvergencePhase.EXPLORING: "Focus on discovery and exploration. No convergence pressure.",
            ConvergencePhase.CONSOLIDATING: "Convergence detected. Help consolidate insights and check criteria.",
            ConvergencePhase.COMMITTED: "Commitment made. Help capture outcomes clearly.",
            ConvergencePhase.HANDED_OFF: "Session complete. Prepare for handoff."
        }

        context["coaching_guidance"] = phase_guidance.get(machine.current_phase, "")

        return context


# Global orchestrator instance
_orchestrator: Optional[ConvergenceOrchestrator] = None


def get_convergence_orchestrator() -> ConvergenceOrchestrator:
    """Get or create the global convergence orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ConvergenceOrchestrator()
    return _orchestrator
