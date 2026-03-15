"""
InDE MVP v3.0.1 - Phase Manager

Manages phase transitions and detects automatic phase changes based on
completeness thresholds. Integrates with allocation engine and event logger.

IKF Phase Taxonomy:
- VISION: Problem definition, target user, solution concept
- DE_RISK: Fear documentation, hypothesis formation, validation
- DEPLOY: Implementation, launch preparation

Transition Triggers:
- automatic: System detects completeness threshold met
- innovator_initiated: User explicitly requests transition
- system_recommendation: System suggests, user confirms
"""

from datetime import datetime
from typing import Dict, List, Optional

from config import IKF_PHASES, PHASE_STATUS, PHASE_TRANSITION_TRIGGERS, READINESS_THRESHOLD


class PhaseManager:
    """
    Manages phase lifecycle and transitions.
    Integrates with TimeAllocationEngine and TemporalEventLogger.
    """

    # Phase transition thresholds (completeness required to auto-transition)
    PHASE_THRESHOLDS = {
        "VISION": 0.75,    # 75% vision complete to transition to DE_RISK
        "DE_RISK": 0.70,   # 70% de-risk complete to transition to DEPLOY
        "DEPLOY": 1.0      # 100% for pursuit completion
    }

    # Element type to phase mapping
    ELEMENT_PHASE_MAP = {
        "vision": "VISION",
        "fears": "DE_RISK",
        "hypothesis": "DE_RISK"
    }

    def __init__(self, database, allocation_engine=None, event_logger=None):
        """
        Initialize PhaseManager.

        Args:
            database: Database instance
            allocation_engine: Optional TimeAllocationEngine
            event_logger: Optional TemporalEventLogger
        """
        self.db = database
        self.allocation_engine = allocation_engine
        self.event_logger = event_logger

    def detect_phase_transition(self, pursuit_id: str,
                                 completeness: Dict[str, float]) -> Optional[Dict]:
        """
        Detects if a phase transition should occur.

        Args:
            pursuit_id: Pursuit ID
            completeness: Dict with vision, fears, hypothesis completeness

        Returns:
            Transition suggestion dict or None if no transition needed
        """
        current_phase = self.get_current_phase(pursuit_id)

        # Check transition from VISION to DE_RISK
        if current_phase == "VISION":
            vision_complete = completeness.get("vision", 0.0)
            if vision_complete >= self.PHASE_THRESHOLDS["VISION"]:
                return {
                    "from_phase": "VISION",
                    "to_phase": "DE_RISK",
                    "trigger": "automatic",
                    "reason": f"Vision completeness ({vision_complete:.0%}) meets threshold",
                    "completeness_at_transition": vision_complete
                }

        # Check transition from DE_RISK to DEPLOY
        elif current_phase == "DE_RISK":
            fears_complete = completeness.get("fears", 0.0)
            hypothesis_complete = completeness.get("hypothesis", 0.0)
            derisk_complete = (fears_complete + hypothesis_complete) / 2

            if derisk_complete >= self.PHASE_THRESHOLDS["DE_RISK"]:
                return {
                    "from_phase": "DE_RISK",
                    "to_phase": "DEPLOY",
                    "trigger": "automatic",
                    "reason": f"De-risk completeness ({derisk_complete:.0%}) meets threshold",
                    "completeness_at_transition": derisk_complete
                }

        return None

    def execute_transition(self, pursuit_id: str, to_phase: str,
                            trigger: str = "automatic", reason: str = None) -> Dict:
        """
        Executes a phase transition.

        Args:
            pursuit_id: Pursuit ID
            to_phase: Target phase
            trigger: Transition trigger type
            reason: Optional reason for transition

        Returns:
            Transition record
        """
        if to_phase not in IKF_PHASES:
            raise ValueError(f"Invalid phase: {to_phase}. Must be one of {IKF_PHASES}")

        if trigger not in PHASE_TRANSITION_TRIGGERS:
            raise ValueError(f"Invalid trigger: {trigger}. Must be one of {PHASE_TRANSITION_TRIGGERS}")

        current_phase = self.get_current_phase(pursuit_id)

        # Record transition
        transition_record = {
            "pursuit_id": pursuit_id,
            "from_phase": current_phase,
            "to_phase": to_phase,
            "trigger": trigger,
            "reason": reason
        }

        self.db.record_phase_transition(transition_record)

        # Update time allocation
        if self.allocation_engine:
            allocation = self.db.get_time_allocation(pursuit_id)
            if allocation:
                # Mark old phase as complete
                for pa in allocation.get("phase_allocations", []):
                    if pa["phase"] == current_phase:
                        pa["status"] = "COMPLETE"
                    elif pa["phase"] == to_phase:
                        pa["status"] = "IN_PROGRESS"

                self.db.update_time_allocation(pursuit_id, {
                    "phase_allocations": allocation["phase_allocations"],
                    "current_phase": to_phase
                })

        # Log event
        if self.event_logger:
            self.event_logger.log_phase_complete(pursuit_id, current_phase)
            self.event_logger.log_phase_start(pursuit_id, to_phase, current_phase)

        return transition_record

    def get_current_phase(self, pursuit_id: str) -> str:
        """
        Returns the current phase for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Phase name (VISION, DE_RISK, or DEPLOY)
        """
        # Check time allocation first
        allocation = self.db.get_time_allocation(pursuit_id)
        if allocation and allocation.get("current_phase"):
            return allocation["current_phase"]

        # Check phase transition history
        current_record = self.db.get_current_phase_record(pursuit_id)
        if current_record:
            return current_record.get("to_phase", "VISION")

        # Default to VISION for new pursuits
        return "VISION"

    def get_phase_status(self, pursuit_id: str, phase: str) -> Dict:
        """
        Returns status details for a specific phase.

        Args:
            pursuit_id: Pursuit ID
            phase: Phase name

        Returns:
            Dict with status, time spent, completeness
        """
        if phase not in IKF_PHASES:
            return {"error": f"Invalid phase: {phase}"}

        # Get time allocation info
        allocation = self.db.get_time_allocation(pursuit_id)
        phase_allocation = None
        if allocation:
            for pa in allocation.get("phase_allocations", []):
                if pa["phase"] == phase:
                    phase_allocation = pa
                    break

        # Get phase duration from transitions
        phase_duration = self.db.get_phase_duration(pursuit_id, phase)

        # Get scaffolding completeness
        state = self.db.get_scaffolding_state(pursuit_id)
        completeness = self._calculate_phase_completeness(state, phase) if state else 0.0

        current_phase = self.get_current_phase(pursuit_id)

        return {
            "phase": phase,
            "status": phase_allocation.get("status", "NOT_STARTED") if phase_allocation else "NOT_STARTED",
            "is_current": current_phase == phase,
            "days_allocated": phase_allocation.get("days_allocated", 0) if phase_allocation else 0,
            "days_used": phase_allocation.get("days_used", 0) if phase_allocation else 0,
            "start_date": phase_allocation.get("start_date") if phase_allocation else None,
            "end_date": phase_allocation.get("end_date") if phase_allocation else None,
            "completeness": completeness,
            "duration": phase_duration
        }

    def _calculate_phase_completeness(self, state: Dict, phase: str) -> float:
        """Calculate completeness for a specific phase."""
        if phase == "VISION":
            elements = state.get("vision_elements", {})
            filled = sum(1 for v in elements.values() if v and v.get("text"))
            total = 8  # 8 vision elements
            return filled / total if total > 0 else 0.0

        elif phase == "DE_RISK":
            fear_elements = state.get("fear_elements", {})
            hypothesis_elements = state.get("hypothesis_elements", {})

            fear_filled = sum(1 for v in fear_elements.values() if v and v.get("text"))
            hyp_filled = sum(1 for v in hypothesis_elements.values() if v and v.get("text"))

            fear_total = 6
            hyp_total = 6

            fear_comp = fear_filled / fear_total if fear_total > 0 else 0.0
            hyp_comp = hyp_filled / hyp_total if hyp_total > 0 else 0.0

            return (fear_comp + hyp_comp) / 2

        elif phase == "DEPLOY":
            # DEPLOY completeness could be based on artifacts or external metrics
            # For now, check if all previous phases are complete
            vision_comp = self._calculate_phase_completeness(state, "VISION")
            derisk_comp = self._calculate_phase_completeness(state, "DE_RISK")

            if vision_comp >= 0.75 and derisk_comp >= 0.70:
                return 0.5  # Started deploy
            return 0.0

        return 0.0

    def get_phase_history(self, pursuit_id: str) -> List[Dict]:
        """Get full phase transition history."""
        return self.db.get_phase_history(pursuit_id)

    def suggest_phase_transition(self, pursuit_id: str,
                                  completeness: Dict[str, float]) -> Optional[Dict]:
        """
        Suggest a phase transition without executing it.

        Returns recommendation that can be shown to user.
        """
        suggestion = self.detect_phase_transition(pursuit_id, completeness)
        if suggestion:
            suggestion["trigger"] = "system_recommendation"
            return suggestion
        return None

    def initiate_transition(self, pursuit_id: str, to_phase: str,
                             reason: str = None) -> Dict:
        """
        Innovator-initiated phase transition.

        Args:
            pursuit_id: Pursuit ID
            to_phase: Target phase
            reason: Optional reason

        Returns:
            Transition record
        """
        return self.execute_transition(
            pursuit_id=pursuit_id,
            to_phase=to_phase,
            trigger="innovator_initiated",
            reason=reason or "User requested transition"
        )

    def get_phase_summary(self, pursuit_id: str) -> Dict:
        """
        Get summary of all phases for display.

        Returns:
            Dict with all phase statuses and current phase
        """
        current = self.get_current_phase(pursuit_id)
        phases = {}

        for phase in IKF_PHASES:
            phases[phase] = self.get_phase_status(pursuit_id, phase)

        return {
            "current_phase": current,
            "phases": phases,
            "phase_order": IKF_PHASES
        }

    def can_transition_to(self, pursuit_id: str, to_phase: str,
                           completeness: Dict[str, float]) -> Dict:
        """
        Check if transition to a phase is allowed.

        Returns:
            Dict with 'allowed', 'reason', 'requirements'
        """
        current = self.get_current_phase(pursuit_id)
        current_idx = IKF_PHASES.index(current) if current in IKF_PHASES else 0
        target_idx = IKF_PHASES.index(to_phase) if to_phase in IKF_PHASES else 0

        # Can't go backwards (for now)
        if target_idx < current_idx:
            return {
                "allowed": False,
                "reason": "Cannot transition to an earlier phase",
                "requirements": []
            }

        # Can't skip phases
        if target_idx > current_idx + 1:
            return {
                "allowed": False,
                "reason": f"Must complete {IKF_PHASES[current_idx + 1]} first",
                "requirements": [f"Complete {IKF_PHASES[current_idx + 1]} phase"]
            }

        # Check completeness requirements
        requirements = []

        if current == "VISION" and to_phase == "DE_RISK":
            threshold = self.PHASE_THRESHOLDS["VISION"]
            vision_complete = completeness.get("vision", 0.0)
            if vision_complete < threshold:
                requirements.append(f"Vision completeness must be at least {threshold:.0%} (currently {vision_complete:.0%})")

        elif current == "DE_RISK" and to_phase == "DEPLOY":
            threshold = self.PHASE_THRESHOLDS["DE_RISK"]
            fears_complete = completeness.get("fears", 0.0)
            hypothesis_complete = completeness.get("hypothesis", 0.0)
            derisk_complete = (fears_complete + hypothesis_complete) / 2
            if derisk_complete < threshold:
                requirements.append(f"De-risk completeness must be at least {threshold:.0%} (currently {derisk_complete:.0%})")

        return {
            "allowed": len(requirements) == 0,
            "reason": requirements[0] if requirements else "Transition allowed",
            "requirements": requirements
        }
