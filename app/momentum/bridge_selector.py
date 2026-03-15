"""
Bridge Selector

Context-aware bridge question selection.

Replaces v4.0's random template selection with momentum-tier-aware,
pursuit-context-parameterized selection.

This is the module that elevates the momentum bridge from a static
pattern to a genuinely responsive coaching move.
"""

import random
import re
import logging
from typing import Optional
from .bridge_library import BRIDGE_LIBRARY

logger = logging.getLogger(__name__)


class BridgeSelector:
    """
    Selects the most appropriate bridge question given:
    - Which artifact was just completed
    - The current momentum tier (from MME)
    - The pursuit context (for placeholder injection)

    Selection rules:
    1. Match to completed_artifact → momentum_tier bucket
    2. Inject pursuit context into placeholders
    3. Prefer templates not recently used in this session (avoid repetition)
    4. Fall back gracefully: unknown artifact → _fallback library
    """

    def __init__(self):
        self._recently_used: list = []  # Track last 3 used to avoid repeats

    def select(
        self,
        completed_artifact: str,
        momentum_tier: str,
        pursuit_context: Optional[dict] = None
    ) -> str:
        """
        Select and return a bridge question.

        Args:
            completed_artifact: Internal artifact key ("vision", "fear", "validation")
            momentum_tier: "HIGH", "MEDIUM", "LOW", or "CRITICAL"
            pursuit_context: Optional dict with idea_domain, idea_summary,
                             user_name, persona for placeholder injection

        Returns:
            A ready-to-deliver bridge question string
        """
        # Get the template pool
        artifact_library = BRIDGE_LIBRARY.get(
            completed_artifact,
            BRIDGE_LIBRARY["_fallback"]
        )
        tier_pool = artifact_library.get(
            momentum_tier,
            artifact_library.get("MEDIUM", BRIDGE_LIBRARY["_fallback"]["MEDIUM"])
        )

        # Filter out recently used templates
        available = [t for t in tier_pool if t not in self._recently_used]
        if not available:
            available = tier_pool  # Reset if all have been used

        # Select
        selected = random.choice(available)

        # Track usage
        self._recently_used.append(selected)
        if len(self._recently_used) > 3:
            self._recently_used.pop(0)

        # Inject context
        result = self._inject_context(selected, pursuit_context or {})

        logger.info(
            f"Bridge selected: artifact={completed_artifact}, "
            f"tier={momentum_tier}, "
            f"bridge_preview='{result[:60]}...'"
        )
        return result

    def _inject_context(self, template: str, context: dict) -> str:
        """
        Replace {placeholder} tokens with pursuit-specific values.
        Falls back gracefully if placeholder values are absent — the
        template is designed to be coherent without them.
        """
        defaults = {
            "idea_domain":   "this space",
            "idea_summary":  "your idea",
            "user_name":     "",
            "persona":       "the people you're trying to help",
        }

        merged = {**defaults, **{k: v for k, v in context.items() if v}}

        try:
            # Replace only placeholders that exist in the template
            result = template
            for key, value in merged.items():
                result = result.replace(f"{{{key}}}", value)
            # Remove any unfilled placeholders gracefully
            result = re.sub(r'\{[a-z_]+\}', defaults.get('idea_domain', 'this area'), result)
            return result
        except Exception:
            return template  # Return raw template if injection fails
