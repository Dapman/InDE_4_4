"""
TRIZ Coaching Context Provider

Injects TRIZ-specific coaching context when the active pursuit uses
the TRIZ archetype. Provides:
1. Current contradiction state (if formulated)
2. Recommended inventive principles (from contradiction matrix)
3. Biological analogs for active principles (from TRIZ-Biomimicry bridge)
4. Ideal Final Result reference

This is a Tier 3 context source - loaded ONLY when:
- Active methodology is "triz"
- Current phase involves contradiction or principle work

Token budget: ~300 tokens when active. May push per-turn to 12,800.
If total exceeds 13,000, Tier 2 context (biomimicry/IKF) is reduced.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("inde.scaffolding.triz")


class TrizContextProvider:
    """
    Provides TRIZ-specific coaching context for the scaffolding engine.

    Tier 3 context source - only loaded when TRIZ methodology is active.
    """

    def __init__(self, principles, matrix, bridge):
        """
        Initialize the TRIZ context provider.

        Args:
            principles: INVENTIVE_PRINCIPLES list
            matrix: CONTRADICTION_MATRIX dict and lookup_principles function
            bridge: TrizBiomimicryBridge instance
        """
        self._principles = principles
        self._matrix = matrix
        self._bridge = bridge
        self._token_budget = 300

    async def get_context(
        self,
        pursuit_state: Dict[str, Any],
        active_methodology: str,
        current_phase: str,
    ) -> Optional[Dict]:
        """
        Returns TRIZ coaching context if relevant, None otherwise.

        Args:
            pursuit_state: Current pursuit state dict
            active_methodology: The active methodology ID
            current_phase: Current phase name

        Returns:
            Context dict with type, content, token_estimate, and trigger
        """
        if active_methodology != "triz":
            return None

        context_lines = ["[TRIZ_CONTEXT]"]

        # Include IFR if defined
        triz_state = pursuit_state.get("triz_state", {})
        ifr = triz_state.get("ideal_final_result")
        if ifr:
            context_lines.append(f"Ideal Final Result: {ifr[:100]}")

        # Include active contradiction if formulated
        contradiction = triz_state.get("active_contradiction")
        if contradiction:
            improving = contradiction.get("improving_parameter")
            worsening = contradiction.get("worsening_parameter")
            context_lines.append(
                f"Active contradiction: improving {improving} worsens {worsening}"
            )

            # Look up recommended principles
            from methodology.triz import lookup_principles
            principle_nums = lookup_principles(improving, worsening)

            if principle_nums:
                principle_names = self._format_principle_names(principle_nums)
                context_lines.append(f"Recommended principles: {principle_names}")

                # TRIZ-Biomimicry bridge: biological analogs
                if current_phase in ("Principle Application", "Solution Development"):
                    for num in principle_nums[:2]:  # Max 2 biological analogs
                        analogs = self._bridge.get_biological_analogs(num)
                        if analogs:
                            analog = analogs[0]  # Best match
                            principle_name = self._get_principle_name(num)
                            context_lines.append(
                                f"Nature's example of Principle {num} ({principle_name}): "
                                f"{analog['organism']} - {analog['mechanism_summary']}"
                            )

            elif not principle_nums:
                context_lines.append(
                    "No matrix entry for this parameter pair - use LLM reasoning"
                )

        # Include principles already applied
        principles_applied = triz_state.get("principles_applied", [])
        if principles_applied:
            context_lines.append(
                f"Principles already explored: {', '.join(str(p) for p in principles_applied)}"
            )

        # Add coaching rules
        context_lines.append(self._get_coaching_rules(current_phase))

        content = "\n".join(context_lines)

        return {
            "type": "triz",
            "content": content,
            "token_estimate": len(content.split()) * 1.3,
            "trigger": "triz_methodology_active",
            "phase": current_phase,
        }

    def _format_principle_names(self, numbers: List[int]) -> str:
        """Format principle numbers with names."""
        names = []
        for n in numbers:
            if 1 <= n <= 40:
                principle = self._principles[n - 1]
                names.append(f"Principle {n}: {principle['name']}")
        return ", ".join(names)

    def _get_principle_name(self, number: int) -> str:
        """Get principle name by number."""
        if 1 <= number <= 40:
            return self._principles[number - 1]["name"]
        return f"Principle {number}"

    def _get_coaching_rules(self, current_phase: str) -> str:
        """Get phase-specific coaching rules."""
        base_rules = """
[TRIZ_COACHING_RULES]
- Guide contradiction formulation before principle application
- When presenting biological analogs, explain WHY the organism's
  strategy embodies the inventive principle
- Always check for secondary contradictions after proposing solutions
- The Ideal Final Result is the north star - solutions should approach it
- The innovator may find non-TRIZ solutions - celebrate those too"""

        if current_phase == "Problem Analysis":
            return base_rules + """
- Push for specificity in the Ideal Final Result
- Don't accept vague problem statements"""

        elif current_phase == "Contradiction Formulation":
            return base_rules + """
- Find the REAL conflict, not symptoms
- Map parameters to the contradiction matrix"""

        elif current_phase == "Principle Application":
            return base_rules + """
- Present principles as thinking tools, not answers
- Surface biomimicry analogs when available"""

        elif current_phase == "Solution Development":
            return base_rules + """
- Test contradiction resolution rigorously
- Watch for secondary contradictions"""

        elif current_phase == "Implementation":
            return base_rules + """
- Capture which principles worked for IKF
- Document unexpected insights"""

        return base_rules

    async def get_principle_coaching_hints(
        self,
        principle_number: int
    ) -> List[str]:
        """
        Get coaching hints for a specific inventive principle.

        Args:
            principle_number: TRIZ principle number (1-40)

        Returns:
            List of coaching hint strings
        """
        if 1 <= principle_number <= 40:
            principle = self._principles[principle_number - 1]
            return principle.get("coaching_hints", [])
        return []

    async def format_contradiction_context(
        self,
        improving: str,
        worsening: str
    ) -> str:
        """
        Format full contradiction context for coaching.

        Args:
            improving: The parameter being improved
            worsening: The parameter getting worse

        Returns:
            Formatted context string
        """
        from methodology.triz import lookup_principles, TRIZ_PARAMETERS

        lines = []

        # Parameter descriptions
        improving_info = TRIZ_PARAMETERS.get(improving, {})
        worsening_info = TRIZ_PARAMETERS.get(worsening, {})

        lines.append(f"Improving: {improving}")
        if improving_info:
            lines.append(f"  Definition: {improving_info.get('description', '')}")

        lines.append(f"Worsening: {worsening}")
        if worsening_info:
            lines.append(f"  Definition: {worsening_info.get('description', '')}")

        # Recommended principles
        principle_nums = lookup_principles(improving, worsening)
        if principle_nums:
            lines.append("\nRecommended inventive principles:")
            for num in principle_nums:
                name = self._get_principle_name(num)
                principle = self._principles[num - 1] if 1 <= num <= 40 else {}
                description = principle.get("description", "")[:100]
                lines.append(f"  {num}. {name}: {description}")

                # Add biological analog if available
                analogs = self._bridge.get_biological_analogs(num)
                if analogs:
                    organism = analogs[0].get("organism", "")
                    lines.append(f"      Nature's example: {organism}")
        else:
            lines.append("\nNo matrix entry - use inventive thinking to resolve")

        return "\n".join(lines)


async def create_triz_context_provider(db) -> TrizContextProvider:
    """
    Factory function to create a fully initialized TrizContextProvider.

    Args:
        db: MongoDB database connection

    Returns:
        Initialized TrizContextProvider instance
    """
    from methodology.triz import INVENTIVE_PRINCIPLES, CONTRADICTION_MATRIX
    from methodology.triz.biomimicry_bridge import TrizBiomimicryBridge

    bridge = TrizBiomimicryBridge(db)
    await bridge.build_index()

    # Create a matrix module-like object for the provider
    class MatrixModule:
        pass
    matrix = MatrixModule()
    matrix.CONTRADICTION_MATRIX = CONTRADICTION_MATRIX

    return TrizContextProvider(INVENTIVE_PRINCIPLES, matrix, bridge)
