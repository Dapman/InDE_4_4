"""
Re-Entry Generator

Selects and renders a personalized coach opening turn for a returning
user session. Uses the assembled re-entry context to choose the
appropriate template from the opening library and inject pursuit-
specific details.

This is the function that replaces the generic "welcome back" with
a coaching moment.
"""

import random
import re
import logging
from typing import Optional
from .reentry_opening_library import REENTRY_OPENINGS

logger = logging.getLogger(__name__)


class ReentryGenerator:
    """
    Generates personalized coach opening turns for returning users.

    Usage:
        generator = ReentryGenerator()
        opening = generator.generate(reentry_context)
        # Returns a ready-to-deliver coaching turn string
    """

    def __init__(self):
        # Track recently used openings to avoid repetition
        self._recent_openings = []
        self._max_recent = 5

    def generate(self, context: dict) -> str:
        """
        Generate a personalized opening turn.

        Args:
            context: The assembled re-entry context dict from
                     ReentryContextAssembler.assemble()

        Returns:
            A personalized opening turn string, ready for delivery.
            Always ends with '?'. Never contains methodology terminology.
        """
        momentum_tier = context.get("momentum_tier")
        gap_tier = context.get("gap_tier", "MEDIUM")

        # Select library bucket
        if momentum_tier is None:
            tier_library = REENTRY_OPENINGS.get("_no_snapshot", {})
        else:
            tier_library = REENTRY_OPENINGS.get(momentum_tier, REENTRY_OPENINGS["MEDIUM"])

        # Get templates for this gap duration
        templates = tier_library.get(gap_tier, tier_library.get("MEDIUM", []))
        if not templates:
            templates = REENTRY_OPENINGS["_no_snapshot"].get("MEDIUM", [
                "Welcome back. What's on your mind about {idea_summary}?"
            ])

        # Select template (avoid recent repetitions)
        template = self._select_avoiding_recent(templates)

        # Inject context
        result = self._inject(template, context)

        logger.info(
            f"Re-entry opening generated: "
            f"tier={momentum_tier}, gap={gap_tier}, "
            f"pursuit={context.get('pursuit_id', 'unknown')}, "
            f"preview='{result[:60]}...'"
        )
        return result

    def _select_avoiding_recent(self, templates: list) -> str:
        """Select a template, avoiding recently used ones if possible."""
        # Filter out recently used
        available = [t for t in templates if t not in self._recent_openings]
        if not available:
            available = templates  # If all are recent, reset

        selected = random.choice(available)

        # Track recent
        self._recent_openings.append(selected)
        if len(self._recent_openings) > self._max_recent:
            self._recent_openings.pop(0)

        return selected

    def _inject(self, template: str, context: dict) -> str:
        """
        Inject pursuit-context values into template placeholders.
        Falls back gracefully for missing values.
        """
        defaults = {
            "idea_summary":  "your idea",
            "idea_domain":   "this space",
            "persona":       "the people you're helping",
            "last_artifact": "your last conversation",
            "user_name":     "",
            "gap_natural":   "a little while",
        }
        merged = {**defaults, **{k: v for k, v in context.items() if v}}

        try:
            result = template
            for key, value in merged.items():
                result = result.replace(f"{{{key}}}", str(value))
            # Remove any unfilled placeholders gracefully
            result = re.sub(r'\{[a-z_]+\}', "your idea", result)
            # Clean up double spaces that can appear after empty user_name injection
            result = re.sub(r'  +', ' ', result).strip()
            return result
        except Exception:
            return template
