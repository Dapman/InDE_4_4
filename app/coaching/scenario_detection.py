"""
Scenario Detection

Detects decision points in coaching conversations where multiple
plausible futures exist. Triggers the scenario exploration coaching
mode within ODICM.

DESIGN PRINCIPLE: Detection is heuristic and fast (no LLM calls).
The LLM is involved in the COACHING of scenarios, not the DETECTION.

Triggers:
1. Phase transition decision - innovator weighing proceed/pivot/iterate
2. Pivot consideration - RVE experiment results are ambiguous
3. Technology bet - multiple solution approaches with different risk profiles
4. Market timing - external factor sensitivity
5. Fear resolution fork - fear exploration reveals branching outcomes

Anti-triggers:
- Already exploring scenarios this session
- Pursuit in PREPARATION state (decision already made)
- Administrative or retrospective conversations
"""

import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger("inde.coaching.scenario")


class ScenarioDetector:
    """
    Detects decision forks in coaching conversations.

    Fast heuristic-based detection - no LLM calls.
    """

    def __init__(self):
        """Initialize the scenario detector."""
        self._session_cooldown = True  # Only 1 scenario exploration per session
        self._max_scenarios_per_decision = 3
        self._min_message_length = 20  # Skip very short messages

        # Fork language patterns
        self._fork_patterns = [
            # Explicit choice language
            "should we", "or should we", "on the other hand",
            "what if we", "alternatively", "two options",
            "path a", "path b", "fork in the road",
            "not sure which direction", "weighing between",
            "torn between", "choosing between",

            # Strategic decisions
            "enterprise or consumer", "build or buy",
            "pivot", "double down", "change direction",
            "stay the course", "cut losses",

            # External dependencies
            "if the regulation", "depends on whether",
            "what happens if", "plan b",
            "if the market", "if competitors",

            # Timing considerations
            "now or later", "wait and see",
            "first mover", "fast follower",
        ]

        # Anti-trigger patterns
        self._anti_patterns = [
            # Administrative
            "schedule", "meeting", "calendar",
            "deadline", "status update",

            # Retrospective
            "looking back", "in hindsight",
            "what we learned", "retrospective",

            # Simple acknowledgments (will also check message length)
            "yes", "no", "ok", "okay", "thanks",
            "got it", "sure", "right",
        ]

    async def should_explore_scenarios(
        self,
        conversation_context: Dict[str, Any],
        pursuit_state: Dict[str, Any],
        session_state: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Determine if scenario exploration should be triggered.

        Args:
            conversation_context: Recent conversation context
            pursuit_state: Current pursuit state
            session_state: Current session state

        Returns:
            Tuple of (should_explore: bool, trigger_reason: str)
        """
        # Anti-trigger: Already exploring scenarios this session
        if session_state.get("scenario_exploration_active", False):
            return False, "already_exploring"

        # Anti-trigger: Pursuit in PREPARATION state (too late)
        universal_state = pursuit_state.get("universal_state", "")
        if universal_state == "PREPARATION":
            return False, "pursuit_in_preparation"

        # Get last user message
        last_message = conversation_context.get("last_user_message", "").lower()

        # Anti-trigger: Very short messages
        if len(last_message) < self._min_message_length:
            return False, "message_too_short"

        # Anti-trigger: Administrative patterns
        if any(pattern in last_message for pattern in self._anti_patterns):
            # But only if it's a short message (administrative acknowledgment)
            if len(last_message) < 50:
                return False, "administrative_context"

        # Trigger: Explicit fork language
        if any(pattern in last_message for pattern in self._fork_patterns):
            return True, "explicit_fork_language"

        # Trigger: Phase transition with ambiguity
        if pursuit_state.get("phase_transition_pending", False):
            # Phase transition + recent fear context = scenario opportunity
            if pursuit_state.get("active_fears"):
                return True, "phase_transition_with_fears"

            # Phase transition + validation ambiguity
            last_validation = pursuit_state.get("last_validation_result", {})
            if last_validation.get("verdict") == "needs_more_data":
                return True, "phase_transition_ambiguous"

        # Trigger: RVE experiment with inconclusive results
        rve_status = pursuit_state.get("rve_last_result")
        if rve_status:
            if rve_status.get("verdict") == "inconclusive":
                return True, "rve_inconclusive"
            if rve_status.get("confidence", 1.0) < 0.5:
                return True, "rve_low_confidence"

        # Trigger: Multiple solution concepts under consideration
        solution_concepts = pursuit_state.get("triz_state", {}).get("solution_concepts", [])
        if len(solution_concepts) >= 2:
            # If there are multiple concepts and user mentions choosing
            choice_language = ["which one", "which option", "best approach", "compare"]
            if any(cl in last_message for cl in choice_language):
                return True, "multiple_solution_concepts"

        # Trigger: Blue Ocean with market entry decision
        if pursuit_state.get("blue_ocean_state", {}).get("four_actions"):
            if "market" in last_message and ("enter" in last_message or "launch" in last_message):
                return True, "market_entry_decision"

        return False, "no_trigger"

    def get_trigger_description(self, trigger_reason: str) -> str:
        """
        Get a human-readable description of a trigger reason.

        Args:
            trigger_reason: The trigger reason code

        Returns:
            Human-readable description
        """
        descriptions = {
            "explicit_fork_language": "Decision fork detected in conversation",
            "phase_transition_with_fears": "Phase transition with active concerns",
            "phase_transition_ambiguous": "Phase transition with unclear validation",
            "rve_inconclusive": "Experiment results are inconclusive",
            "rve_low_confidence": "Experiment results have low confidence",
            "multiple_solution_concepts": "Multiple solution paths under consideration",
            "market_entry_decision": "Market entry strategy decision point",
            "already_exploring": "Scenario exploration already active",
            "pursuit_in_preparation": "Pursuit has reached preparation phase",
            "message_too_short": "Message too brief for analysis",
            "administrative_context": "Administrative conversation context",
            "no_trigger": "No scenario trigger detected",
        }
        return descriptions.get(trigger_reason, trigger_reason)

    def get_max_scenarios(self) -> int:
        """Return maximum scenarios per decision point."""
        return self._max_scenarios_per_decision

    def add_custom_fork_pattern(self, pattern: str) -> None:
        """
        Add a custom fork detection pattern.

        Args:
            pattern: Pattern string to add
        """
        if pattern.lower() not in self._fork_patterns:
            self._fork_patterns.append(pattern.lower())

    def add_custom_anti_pattern(self, pattern: str) -> None:
        """
        Add a custom anti-trigger pattern.

        Args:
            pattern: Pattern string to add
        """
        if pattern.lower() not in self._anti_patterns:
            self._anti_patterns.append(pattern.lower())


class ScenarioExplorationState:
    """
    Tracks the state of an active scenario exploration.
    """

    def __init__(
        self,
        trigger_reason: str,
        pursuit_id: str,
        session_id: str,
    ):
        """
        Initialize scenario exploration state.

        Args:
            trigger_reason: What triggered the exploration
            pursuit_id: The pursuit being explored
            session_id: The coaching session
        """
        self.trigger_reason = trigger_reason
        self.pursuit_id = pursuit_id
        self.session_id = session_id
        self.scenarios: List[Dict] = []
        self.current_scenario_index = 0
        self.decision_made = False
        self.chosen_scenario: str = None
        self.rationale: str = None
        self.revisit_trigger: str = None

    def add_scenario(
        self,
        name: str,
        description: str = "",
        assumptions: List[str] = None,
        risks: List[str] = None,
        opportunities: List[str] = None,
        timeframe: str = "",
        resources: str = "",
        reversibility: str = "",
    ) -> bool:
        """
        Add a scenario to the exploration.

        Args:
            name: Scenario name
            description: Brief description
            assumptions: What must be true
            risks: Key risks
            opportunities: Opportunities opened
            timeframe: Time estimate
            resources: Resource requirements
            reversibility: Can they change course?

        Returns:
            True if added, False if max reached
        """
        if len(self.scenarios) >= 3:
            return False

        self.scenarios.append({
            "name": name,
            "description": description,
            "assumptions": assumptions or [],
            "risks": risks or [],
            "opportunities": opportunities or [],
            "timeframe": timeframe,
            "resource_requirements": resources,
            "reversibility": reversibility,
        })
        return True

    def record_decision(
        self,
        chosen: str,
        rationale: str,
        key_factors: List[str] = None,
        revisit_trigger: str = "",
    ) -> None:
        """
        Record the innovator's decision.

        Args:
            chosen: Name of chosen scenario (or "deferred")
            rationale: Why this was chosen
            key_factors: Key decision factors
            revisit_trigger: Under what conditions to reconsider
        """
        self.decision_made = True
        self.chosen_scenario = chosen
        self.rationale = rationale
        self.key_factors = key_factors or []
        self.revisit_trigger = revisit_trigger

    def to_artifact_data(self, title: str) -> Dict:
        """
        Convert exploration state to .scenario artifact data.

        Args:
            title: Title for the scenario artifact

        Returns:
            Dict matching SCENARIO_SCHEMA
        """
        return {
            "title": title,
            "trigger": self.trigger_reason,
            "scenarios_explored": self.scenarios,
            "decision": {
                "chosen_scenario": self.chosen_scenario or "deferred",
                "rationale": self.rationale or "",
                "key_factors": getattr(self, "key_factors", []),
                "revisit_trigger": self.revisit_trigger or "",
            } if self.decision_made else None,
            "coaching_session_id": self.session_id,
            "pursuit_id": self.pursuit_id,
        }
