"""
Bridge Selector

Context-aware bridge question selection.

Replaces v4.0's random template selection with momentum-tier-aware,
pursuit-context-parameterized selection.

This is the module that elevates the momentum bridge from a static
pattern to a genuinely responsive coaching move.

v4.4: Extended with IML-first selection. Queries IMLFeedbackReceiver
before consulting the static bridge library. If a high-confidence
momentum-informed recommendation is available, it is used. Otherwise,
falls back to static library — identical behavior to v4.3.
"""

import random
import re
import logging
from typing import Optional, Dict, Any
from .bridge_library import BRIDGE_LIBRARY

logger = logging.getLogger(__name__)

# v4.4: IML feedback integration (guarded import)
try:
    from .iml_feedback_receiver import IMLFeedbackReceiver
    _iml_feedback = IMLFeedbackReceiver()
    IML_FEEDBACK_ENABLED = True
except Exception:
    IML_FEEDBACK_ENABLED = False
    _iml_feedback = None


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

        v4.4: Queries IML for momentum-informed recommendation first.
              Falls back to static library if no strong recommendation.

        Args:
            completed_artifact: Internal artifact key ("vision", "fear", "validation")
            momentum_tier: "HIGH", "MEDIUM", "LOW", or "CRITICAL"
            pursuit_context: Optional dict with idea_domain, idea_summary,
                             user_name, persona for placeholder injection

        Returns:
            A ready-to-deliver bridge question string
        """
        context = pursuit_context or {}
        selection_source = "static"

        # --- v4.4 addition: IML-informed selection ---
        if IML_FEEDBACK_ENABLED and _iml_feedback:
            available_ids = self._get_candidate_bridge_ids(completed_artifact, momentum_tier)
            iml_recommendation = _iml_feedback.get_recommended_bridge(
                available_bridge_ids=available_ids,
                pursuit_stage=context.get("pursuit_stage", "unknown"),
                artifact_type=completed_artifact,
                momentum_tier=momentum_tier,
            )
            if iml_recommendation:
                selection_source = "iml"
                # IML recommended a bridge ID — look it up in the library
                selected = self._lookup_bridge_by_id(iml_recommendation, completed_artifact, momentum_tier)
                if selected:
                    result = self._inject_context(selected, context)
                    logger.info(
                        f"Bridge selected (IML): artifact={completed_artifact}, "
                        f"tier={momentum_tier}, "
                        f"bridge_preview='{result[:60]}...'"
                    )
                    # Tag for telemetry
                    context["_bridge_selected_by"] = selection_source
                    return result
        # --- end v4.4 addition ---

        # Fall back to static library selection
        selected = self._select_from_static_library(completed_artifact, momentum_tier)

        # Track usage
        self._recently_used.append(selected)
        if len(self._recently_used) > 3:
            self._recently_used.pop(0)

        # Inject context
        result = self._inject_context(selected, context)

        # Tag for telemetry
        context["_bridge_selected_by"] = selection_source

        logger.info(
            f"Bridge selected (static): artifact={completed_artifact}, "
            f"tier={momentum_tier}, "
            f"bridge_preview='{result[:60]}...'"
        )
        return result

    def _get_candidate_bridge_ids(self, completed_artifact: str, momentum_tier: str) -> list:
        """
        v4.4: Get list of bridge template IDs for IML scoring.
        Returns a list of string IDs (using index as ID for now).
        """
        artifact_library = BRIDGE_LIBRARY.get(
            completed_artifact,
            BRIDGE_LIBRARY["_fallback"]
        )
        tier_pool = artifact_library.get(
            momentum_tier,
            artifact_library.get("MEDIUM", BRIDGE_LIBRARY["_fallback"]["MEDIUM"])
        )
        # Use template hash as ID for now
        return [f"{completed_artifact}_{momentum_tier}_{i}" for i in range(len(tier_pool))]

    def _lookup_bridge_by_id(self, bridge_id: str, completed_artifact: str, momentum_tier: str) -> Optional[str]:
        """
        v4.4: Look up a bridge template by its ID.
        """
        try:
            parts = bridge_id.rsplit("_", 1)
            if len(parts) == 2:
                idx = int(parts[1])
                artifact_library = BRIDGE_LIBRARY.get(
                    completed_artifact,
                    BRIDGE_LIBRARY["_fallback"]
                )
                tier_pool = artifact_library.get(
                    momentum_tier,
                    artifact_library.get("MEDIUM", BRIDGE_LIBRARY["_fallback"]["MEDIUM"])
                )
                if 0 <= idx < len(tier_pool):
                    return tier_pool[idx]
        except Exception:
            pass
        return None

    def _select_from_static_library(self, completed_artifact: str, momentum_tier: str) -> str:
        """
        v4.4: Original static library selection logic extracted into method.
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
        return random.choice(available)

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
