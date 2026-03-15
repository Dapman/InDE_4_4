"""
Blue Ocean Coaching Context Provider

Injects Blue Ocean-specific coaching context. Tier 3 context source -
loaded only when active methodology is "blue_ocean".

Token budget: ~300 tokens when active.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("inde.scaffolding.blue_ocean")


class BlueOceanContextProvider:
    """
    Provides Blue Ocean-specific coaching context for the scaffolding engine.

    Tier 3 context source - only loaded when Blue Ocean methodology is active.
    """

    def __init__(self):
        """Initialize the Blue Ocean context provider."""
        self._token_budget = 300

    async def get_context(
        self,
        pursuit_state: Dict[str, Any],
        active_methodology: str,
        current_phase: str,
    ) -> Optional[Dict]:
        """
        Returns Blue Ocean coaching context if relevant, None otherwise.

        Args:
            pursuit_state: Current pursuit state dict
            active_methodology: The active methodology ID
            current_phase: Current phase name

        Returns:
            Context dict with type, content, token_estimate, and trigger
        """
        if active_methodology != "blue_ocean":
            return None

        context_lines = ["[BLUE_OCEAN_CONTEXT]"]

        blue_ocean_state = pursuit_state.get("blue_ocean_state", {})

        # Include current value curve state if available
        strategy_canvas = blue_ocean_state.get("strategy_canvas")
        if strategy_canvas:
            factors = strategy_canvas.get("competitive_factors", [])
            if factors:
                summary = ", ".join([
                    f"{f['name']}:{f.get('proposed_position', f.get('your_position', '?'))}"
                    for f in factors[:5]
                ])
                context_lines.append(f"Current value curve: {summary}")

            new_factors = strategy_canvas.get("new_factors", [])
            if new_factors:
                created = ", ".join([f["name"] for f in new_factors])
                context_lines.append(f"New factors being created: {created}")

        # Include ERRC actions if available
        four_actions = blue_ocean_state.get("four_actions")
        if four_actions:
            e = [a["factor"] for a in four_actions.get("eliminate", [])]
            r = [a["factor"] for a in four_actions.get("reduce", [])]
            ra = [a["factor"] for a in four_actions.get("raise", [])]
            c = [a["factor"] for a in four_actions.get("create", [])]

            if any([e, r, ra, c]):
                errc_summary = []
                if e:
                    errc_summary.append(f"Eliminate [{', '.join(e)}]")
                if r:
                    errc_summary.append(f"Reduce [{', '.join(r)}]")
                if ra:
                    errc_summary.append(f"Raise [{', '.join(ra)}]")
                if c:
                    errc_summary.append(f"Create [{', '.join(c)}]")
                context_lines.append(f"ERRC: {' '.join(errc_summary)}")

        # Non-customer tier focus
        non_customer_tier = blue_ocean_state.get("non_customer_tier")
        if non_customer_tier:
            tier_descriptions = {
                1: "Soon-to-be (ready to leave)",
                2: "Refusing (consciously reject)",
                3: "Unexplored (never considered)",
            }
            tier_desc = tier_descriptions.get(non_customer_tier, str(non_customer_tier))
            context_lines.append(f"Non-customer focus: Tier {non_customer_tier} - {tier_desc}")

        # Value innovation statement
        value_innovation = blue_ocean_state.get("value_innovation_statement")
        if value_innovation:
            context_lines.append(f"Value innovation: {value_innovation[:100]}")

        # Add coaching rules
        context_lines.append(self._get_coaching_rules(current_phase))

        content = "\n".join(context_lines)

        return {
            "type": "blue_ocean",
            "content": content,
            "token_estimate": len(content.split()) * 1.3,
            "trigger": "blue_ocean_methodology_active",
            "phase": current_phase,
        }

    def _get_coaching_rules(self, current_phase: str) -> str:
        """Get phase-specific coaching rules."""
        base_rules = """
[BLUE_OCEAN_COACHING_RULES]
- Challenge industry assumptions - ask 'why does everyone compete on this?'
- Push toward non-customers, not existing customer satisfaction
- The value curve must DIVERGE from industry norms, not just shift
- Value innovation = differentiation AND low cost simultaneously
- If the innovator's curve looks like the industry, push harder
- Incremental improvement is a valid conclusion but challenge it first"""

        if current_phase == "As-Is Analysis":
            return base_rules + """
- Map ALL factors the industry competes on
- Ask why these factors exist - are they actually valued?"""

        elif current_phase == "Strategic Reconstruction":
            return base_rules + """
- Every factor must be questioned for elimination or reduction
- Created factors must be truly NEW, not industry upgrades"""

        elif current_phase == "Value Innovation":
            return base_rules + """
- Test: Is this BOTH differentiation AND lower cost?
- Where do eliminated/reduced factors fund the created factors?"""

        elif current_phase == "Fair Process Execution":
            return base_rules + """
- Test with non-customers first, not existing customers
- Ensure stakeholders understand the WHY of the shift"""

        elif current_phase == "Launch Preparation":
            return base_rules + """
- Blue oceans eventually turn red - plan for renewal
- Document imitation barriers clearly"""

        return base_rules

    async def get_six_paths_prompts(self, industry: str = "") -> List[Dict]:
        """
        Get coaching prompts for the Six Paths Framework.

        Args:
            industry: Optional industry context

        Returns:
            List of path dicts with coaching prompts
        """
        from methodology.archetypes.blue_ocean import SIX_PATHS_FRAMEWORK
        return list(SIX_PATHS_FRAMEWORK.values())

    async def get_non_customer_prompts(self, current_tier: int = None) -> List[Dict]:
        """
        Get coaching prompts for non-customer exploration.

        Args:
            current_tier: Currently explored tier (1, 2, or 3)

        Returns:
            List of tier dicts with coaching prompts
        """
        from methodology.archetypes.blue_ocean import NON_CUSTOMER_TIERS
        return list(NON_CUSTOMER_TIERS.values())

    async def evaluate_value_curve_divergence(
        self,
        strategy_canvas: Dict
    ) -> Dict:
        """
        Evaluate how divergent a value curve is from industry norms.

        Args:
            strategy_canvas: The strategy canvas data

        Returns:
            Dict with divergence score and feedback
        """
        factors = strategy_canvas.get("competitive_factors", [])
        new_factors = strategy_canvas.get("new_factors", [])

        if not factors:
            return {
                "divergence_score": 0,
                "feedback": "Strategy canvas has no competitive factors mapped",
                "is_divergent": False,
            }

        # Calculate divergence
        total_diff = 0
        significant_changes = 0

        for f in factors:
            industry_avg = f.get("industry_average", 5)
            proposed = f.get("proposed_position", f.get("your_position", 5))
            diff = abs(proposed - industry_avg)
            total_diff += diff
            if diff >= 3:  # Significant if 3+ points different
                significant_changes += 1

        avg_divergence = total_diff / len(factors) if factors else 0
        new_factor_bonus = len(new_factors) * 2  # Bonus for created factors

        divergence_score = min(10, avg_divergence + new_factor_bonus)

        is_divergent = divergence_score >= 4 and (significant_changes >= 2 or len(new_factors) >= 1)

        if is_divergent:
            feedback = "Value curve shows meaningful divergence from industry norms"
        elif divergence_score >= 2:
            feedback = "Value curve shows some divergence but may need bolder moves"
        else:
            feedback = "Value curve looks too similar to industry - push for elimination/creation"

        return {
            "divergence_score": round(divergence_score, 1),
            "significant_changes": significant_changes,
            "new_factors_count": len(new_factors),
            "is_divergent": is_divergent,
            "feedback": feedback,
        }


async def create_blue_ocean_context_provider() -> BlueOceanContextProvider:
    """
    Factory function to create a BlueOceanContextProvider.

    Returns:
        Initialized BlueOceanContextProvider instance
    """
    return BlueOceanContextProvider()
