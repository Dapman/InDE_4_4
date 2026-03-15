"""
Scenario Exploration Coaching Context

Injected into the coaching prompt when scenario detection triggers.
Instructs the LLM to guide the innovator through structured
future-thinking WITHOUT generating pre-computed scenarios.

CRITICAL: The innovator creates the scenarios. The coach helps them
think rigorously about each future. The coach NEVER presents a list
of pre-built scenarios and asks the innovator to choose.

This follows the same conversational-not-wizard principle as biomimicry.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("inde.scaffolding.scenario")


class ScenarioContextProvider:
    """
    Provides scenario exploration coaching context.

    Injected when scenario detection triggers a decision fork.
    """

    def __init__(self):
        """Initialize the scenario context provider."""
        self._token_budget = 400
        self._max_scenarios = 3

    async def get_context(
        self,
        trigger_reason: str,
        pursuit_state: Dict[str, Any],
        active_methodology: str,
    ) -> Dict:
        """
        Build scenario exploration coaching context.

        Args:
            trigger_reason: What triggered scenario exploration
            pursuit_state: Current pursuit state
            active_methodology: The active methodology ID

        Returns:
            Context dict with coaching instructions
        """
        context_lines = ["[SCENARIO_EXPLORATION_MODE]"]
        context_lines.append(f"Trigger: {trigger_reason}")
        context_lines.append(f"Methodology: {active_methodology}")

        # Add the core coaching protocol
        context_lines.append(self._get_coaching_protocol())

        # Add scenario rules
        context_lines.append(self._get_scenario_rules())

        # Add methodology-specific framing
        methodology_framing = self._get_methodology_framing(active_methodology)
        if methodology_framing:
            context_lines.append(methodology_framing)

        # Add context from pursuit state if available
        pursuit_context = self._extract_pursuit_context(pursuit_state)
        if pursuit_context:
            context_lines.append(pursuit_context)

        content = "\n".join(context_lines)

        return {
            "type": "scenario",
            "content": content,
            "token_estimate": len(content.split()) * 1.3,
            "trigger": trigger_reason,
            "max_scenarios": self._max_scenarios,
        }

    def _get_coaching_protocol(self) -> str:
        """Get the core scenario coaching protocol."""
        return """
[SCENARIO_COACHING_PROTOCOL]
The innovator is at a decision fork. Guide them through
structured scenario thinking:

1. INVITATION: Acknowledge the fork naturally.
   'You're weighing two fundamentally different paths here...'
   'Let's think through what each future looks like.'

2. EXPLORATION: For each scenario (max 3), help the innovator think through:
   - What happens in the next 3-12 months?
   - What assumptions must be true for this path to work?
   - What's the biggest risk in this scenario?
   - What resources does this path require?
   - What's the reversibility - can you change course later?

3. COMPARISON: Synthesize what you've heard.
   'Here's what I'm hearing - Path A gives you X but costs Y...'
   Connect to existing pursuit artifacts (fears, vision, validation data).

4. COMMITMENT: Ask for the innovator's decision.
   'Based on this exploration, which direction feels right?'
   Capture the REASONING, not just the choice.
   Ask: 'What would make you reconsider this decision?'"""

    def _get_scenario_rules(self) -> str:
        """Get the scenario exploration rules."""
        return """
[SCENARIO_RULES]
- The innovator creates scenarios - NEVER present pre-computed futures
- Maximum 3 scenarios per decision point (prevent scope creep)
- Each scenario needs: assumptions, risks, opportunities, timeframe
- Capture a 'revisit trigger' - under what conditions should they reconsider?
- Weave into natural conversation - no structured scenario forms
- This conversation will produce a .scenario artifact automatically"""

    def _get_methodology_framing(self, methodology: str) -> Optional[str]:
        """Get methodology-specific scenario framing."""
        framings = {
            "lean_startup": (
                "\nLean Startup framing: Which path generates the fastest learning? "
                "What's the minimum viable experiment for each scenario?"
            ),
            "design_thinking": (
                "\nDesign Thinking framing: Which path keeps the user at the center? "
                "How would each scenario affect the people you're designing for?"
            ),
            "stage_gate": (
                "\nStage-Gate framing: Which path has the clearest gate criteria? "
                "What evidence would you need to proceed with each option?"
            ),
            "triz": (
                "\nTRIZ framing: Do these paths resolve the same contradiction differently? "
                "Which inventive principles might apply to each scenario?"
            ),
            "blue_ocean": (
                "\nBlue Ocean framing: Which path leads to more uncontested space? "
                "How does each scenario affect your value curve?"
            ),
        }
        return framings.get(methodology)

    def _extract_pursuit_context(self, pursuit_state: Dict[str, Any]) -> Optional[str]:
        """Extract relevant context from pursuit state."""
        lines = []

        # Active fears
        fears = pursuit_state.get("active_fears", [])
        if fears:
            fear_names = [f.get("fear_type", f.get("name", "")) for f in fears[:3]]
            if fear_names:
                lines.append(f"Active concerns: {', '.join(fear_names)}")

        # Vision statement
        vision = pursuit_state.get("vision_statement")
        if vision:
            lines.append(f"Pursuit vision: {vision[:100]}")

        # Recent validation
        validation = pursuit_state.get("last_validation_result", {})
        if validation.get("verdict"):
            lines.append(f"Recent validation: {validation['verdict']}")

        if lines:
            return "\n[PURSUIT_CONTEXT]\n" + "\n".join(lines)
        return None

    def get_completion_prompt(self) -> str:
        """Get prompt for completing scenario exploration."""
        return """
[SCENARIO_COMPLETION]
The scenario exploration is complete. The innovator has made their decision.

Summarize:
1. The scenarios explored and their key characteristics
2. The chosen path and the reasoning behind it
3. The revisit trigger - when should they reconsider?

Close with encouragement for the path chosen, while acknowledging
the value of having thought through alternatives."""


class ScenarioIntegrationHelper:
    """
    Helper for integrating scenarios with other InDE components.
    """

    @staticmethod
    def format_for_tim(scenario_artifact: Dict) -> Dict:
        """
        Format scenario for Time Intelligence Module.

        The chosen path's timeframe and resources inform TIM recommendations.
        """
        decision = scenario_artifact.get("decision", {})
        scenarios = scenario_artifact.get("scenarios_explored", [])

        chosen_name = decision.get("chosen_scenario")
        chosen_scenario = next(
            (s for s in scenarios if s.get("name") == chosen_name),
            {}
        )

        return {
            "scenario_title": scenario_artifact.get("title"),
            "chosen_path": chosen_name,
            "timeframe": chosen_scenario.get("timeframe", ""),
            "resource_requirements": chosen_scenario.get("resource_requirements", ""),
            "revisit_trigger": decision.get("revisit_trigger", ""),
            "decision_date": scenario_artifact.get("created_at"),
        }

    @staticmethod
    def format_for_retrospective(scenario_artifact: Dict) -> str:
        """
        Format scenario for retrospective reflection.

        Returns a reflection prompt about the scenario decision.
        """
        decision = scenario_artifact.get("decision", {})
        revisit = decision.get("revisit_trigger", "")

        return (
            f"You chose the '{decision.get('chosen_scenario')}' path "
            f"because: {decision.get('rationale', 'reason not captured')}. "
            f"Your revisit trigger was: '{revisit}'. "
            f"Looking back, was this the right call? Has the revisit trigger "
            f"condition been met?"
        )

    @staticmethod
    def format_for_ikf(scenario_artifact: Dict, industry: str = "") -> Dict:
        """
        Format scenario for IKF contribution.

        Generalize the pattern for cross-org learning.
        """
        decision = scenario_artifact.get("decision", {})

        # Anonymize and generalize
        return {
            "pattern_type": "scenario_decision",
            "fork_type": scenario_artifact.get("trigger", "decision_fork"),
            "industry": industry,
            "scenarios_count": len(scenario_artifact.get("scenarios_explored", [])),
            "chosen_path_characteristics": {
                "was_deferred": decision.get("chosen_scenario") == "deferred",
                "had_revisit_trigger": bool(decision.get("revisit_trigger")),
                "key_factors_count": len(decision.get("key_factors", [])),
            },
            # No specific content - just structural patterns
        }


async def create_scenario_context_provider() -> ScenarioContextProvider:
    """
    Factory function to create a ScenarioContextProvider.

    Returns:
        Initialized ScenarioContextProvider instance
    """
    return ScenarioContextProvider()
