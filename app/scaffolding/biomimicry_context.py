"""
Biomimicry Coaching Context Provider

Integrates with the existing scaffolding context assembly pipeline to
inject biomimicry pattern data when relevant. This is a Tier 2
(on-demand) context source - loaded only when the BiomimicryDetector
signals that analysis is warranted.

Token budget: ~1,000 tokens borrowed from IKF pattern budget when active.
Total per-turn budget unchanged at 12,500.

Design principles:
- Natural conversational delivery (NEVER wizard-like)
- Methodology-adaptive guidance
- Respect innovator sovereignty (accept/explore/defer/dismiss)
- Maximum 1 biological insight per coaching message
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("inde.scaffolding.biomimicry_context")

# Token budget borrowed from IKF pattern context when biomimicry is active
BIOMIMICRY_TOKEN_BUDGET = 1000


class BiomimicryContextProvider:
    """
    Provides biomimicry coaching context when biological parallels
    are relevant to the innovator's challenge.

    This provider integrates with the ODICM scaffolding context assembly
    pipeline as a Tier 2 (on-demand) context source. When biomimicry
    detection triggers, this provider:

    1. Analyzes the challenge for biological parallels
    2. Formats matched patterns into coaching-ready context
    3. Includes methodology-specific guidance
    4. Returns context block for LLM injection

    The context explicitly instructs conversational delivery (not wizard-like)
    and respects Abstract Sovereignty by presenting insights as suggestions.
    """

    def __init__(self, analyzer, detector, config=None):
        """
        Initialize the Biomimicry Context Provider.

        Args:
            analyzer: BiomimicryAnalyzer instance for challenge analysis
            detector: BiomimicryDetector instance for trigger detection
            config: Optional configuration object
        """
        self._analyzer = analyzer
        self._detector = detector
        self._config = config
        self._token_budget = BIOMIMICRY_TOKEN_BUDGET

    async def get_context(
        self,
        conversation_context: Dict[str, Any],
        pursuit_state: Dict[str, Any],
        active_methodology: str,
        pursuit_id: str,
        current_turn: int,
        recent_biomimicry_offer_turn: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get biomimicry coaching context if relevant.

        This is the main entry point called by the context assembler.
        Returns a context block if biomimicry coaching is appropriate,
        or None if not.

        When this returns a context block, the IKF pattern context budget
        should be reduced by self._token_budget to maintain the 12,500 total.

        Args:
            conversation_context: Current conversation context
            pursuit_state: Current pursuit state
            active_methodology: Active innovation methodology
            pursuit_id: The pursuit ID
            current_turn: Current turn number
            recent_biomimicry_offer_turn: Turn of last biomimicry offer

        Returns:
            Context dict if biomimicry is relevant, None otherwise
        """
        # Check if we should analyze
        should_analyze, trigger = await self._detector.should_analyze(
            conversation_context,
            pursuit_state,
            recent_biomimicry_offer_turn,
            current_turn
        )

        if not should_analyze:
            logger.debug(f"Biomimicry analysis skipped: {trigger}")
            return None

        # Extract challenge text
        challenge_text = self._extract_challenge_text(
            conversation_context, pursuit_state
        )

        if len(challenge_text) < 30:
            logger.debug("Challenge text too short for analysis")
            return None

        # Analyze challenge for biomimicry opportunities
        matches = await self._analyzer.analyze_challenge(
            challenge_context=challenge_text,
            pursuit_domain=pursuit_state.get("domain"),
            active_methodology=active_methodology,
            pursuit_id=pursuit_id
        )

        if not matches:
            logger.debug("No biomimicry matches found")
            return None

        # Format matches into coaching context
        context_block = self._format_coaching_context(matches, active_methodology)

        logger.info(
            f"Biomimicry context generated: {len(matches)} patterns, "
            f"trigger={trigger}, methodology={active_methodology}"
        )

        return context_block

    def _extract_challenge_text(
        self,
        conversation_context: Dict[str, Any],
        pursuit_state: Dict[str, Any]
    ) -> str:
        """
        Extract the challenge text from context for analysis.

        Combines pursuit challenge description with recent conversation
        context to provide full challenge picture.
        """
        parts = []

        # Primary challenge text from pursuit
        if pursuit_state.get("challenge_text"):
            parts.append(pursuit_state["challenge_text"])

        # Recent user message (may contain additional context)
        if conversation_context.get("last_user_message"):
            parts.append(conversation_context["last_user_message"])

        # Active fears (potential problem areas)
        if pursuit_state.get("active_fears"):
            fears = pursuit_state["active_fears"]
            if isinstance(fears, list) and fears:
                fear_text = "; ".join(str(f) for f in fears[:3])
                parts.append(f"Concerns: {fear_text}")

        return " ".join(parts)

    def _format_coaching_context(
        self,
        matches: List[Any],
        methodology: str
    ) -> Dict[str, Any]:
        """
        Format matched patterns into coaching context block.

        CRITICAL: This is injected into the LLM prompt. It tells the
        coaching engine WHAT biological insights are available and
        HOW to present them conversationally.

        The context does NOT tell the LLM to use wizard formatting.
        It instructs natural, conversational delivery.

        Args:
            matches: List of BiomimicryMatchResult objects
            methodology: Active innovation methodology

        Returns:
            Context dict with type, content, and metadata
        """
        context_lines = ["[BIOMIMICRY_CONTEXT]"]
        context_lines.append(
            "Biological strategies relevant to the innovator's current challenge:"
        )

        for match in matches:
            context_lines.append(f"\n--- {match.organism}: {match.strategy_name} ---")
            context_lines.append(f"Mechanism: {match.mechanism[:250]}")
            context_lines.append(f"Principle: {'; '.join(match.innovation_principles)}")

            if match.known_applications:
                app = match.known_applications[0]
                if isinstance(app, dict):
                    app_name = app.get("name", "")
                    app_impact = app.get("impact", "")
                else:
                    app_name = str(app)
                    app_impact = ""
                if app_name:
                    context_lines.append(f"Known application: {app_name} - {app_impact}")

            context_lines.append(f"Relevance: {match.reason}")

        # Methodology-specific coaching guidance
        context_lines.append(f"\n[BIOMIMICRY_COACHING_STYLE: {methodology}]")
        context_lines.append(self._get_methodology_guidance(methodology))

        # Delivery rules (CRITICAL for non-wizard presentation)
        context_lines.append(self._get_delivery_rules())

        content = "\n".join(context_lines)

        return {
            "type": "biomimicry",
            "content": content,
            "token_estimate": int(len(content.split()) * 1.3),
            "pattern_ids": [m.pattern_id for m in matches],
            "trigger": "biomimicry_detected",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def _get_methodology_guidance(self, methodology: str) -> str:
        """Get methodology-specific biomimicry coaching guidance."""
        guidance = {
            "lean_startup": (
                "Frame biological insight as testable hypothesis. "
                "Ask: 'Could we validate whether this principle works in our context?' "
                "Connect to Build-Measure-Learn cycle."
            ),
            "design_thinking": (
                "Connect to empathy and prototyping. "
                "Ask: 'How might users experience this principle? Could we prototype it?' "
                "Encourage sketching or modeling the biological mechanism."
            ),
            "stage_gate": (
                "Frame as technical feasibility evidence. "
                "Suggest documenting in feasibility assessment. "
                "Connect to innovation readiness criteria."
            ),
            "jobs_to_be_done": (
                "Connect biological mechanism to the job being done. "
                "Ask: 'How does this pattern address the underlying job?' "
                "Explore progress-making forces."
            ),
            "agile": (
                "Frame as increment opportunity. "
                "Ask: 'Could we test this principle in a single sprint?' "
                "Identify smallest viable experiment."
            ),
            # v3.6.1: TRIZ and Blue Ocean methodology guidance
            "triz": (
                "This biological strategy embodies a TRIZ inventive principle. "
                "Connect the organism's solution to the active contradiction. "
                "Ask: 'This organism resolved the same type of conflict - "
                "what principle is at work here?'"
            ),
            "blue_ocean": (
                "Connect the biological strategy to value innovation thinking. "
                "Ask: 'Nature found an uncontested niche using this approach - "
                "could your value curve incorporate this principle?'"
            ),
        }

        return guidance.get(
            methodology,
            (
                "Present the biological insight naturally. "
                "Explain the biology accessibly, then abstract the principle. "
                "Ask how it might apply to their challenge."
            )
        )

    def _get_delivery_rules(self) -> str:
        """Get biomimicry delivery rules for coaching."""
        return """
[BIOMIMICRY_DELIVERY_RULES]
- Weave insight into natural conversation - NEVER use structured cards or scores
- Explain the biology accessibly, then abstract the principle
- Ask the innovator how it might apply to their challenge
- Respect accept/explore/defer/dismiss response without judgment
- Maximum 1 biological insight per coaching message
- If innovator wants to explore further, use your full training knowledge about the organism
- Do NOT repeat the pattern_id or score - these are for internal tracking only
- Frame as "nature has an interesting approach" or "the natural world offers inspiration"
- If dismissed, move on gracefully without insisting or explaining why it's relevant"""

    def get_token_budget(self) -> int:
        """Get the token budget this provider uses."""
        return self._token_budget

    async def record_biomimicry_response(
        self,
        pursuit_id: str,
        pattern_id: str,
        response: str,
        feedback_service
    ):
        """
        Helper to record innovator response to biomimicry insight.

        This is called by the coaching engine when it detects an
        accept/explore/defer/dismiss response to a biomimicry offer.

        Args:
            pursuit_id: The pursuit ID
            pattern_id: The pattern that was offered
            response: One of: explored, accepted, deferred, dismissed
            feedback_service: BiomimicryFeedback instance
        """
        # Find the most recent match for this pattern in this pursuit
        match = self._analyzer._db.biomimicry_matches.find_one(
            {
                "pursuit_id": pursuit_id,
                "pattern_id": pattern_id,
                "innovator_response": "pending"
            },
            sort=[("created_at", -1)]
        )

        if match:
            await feedback_service.record_response(
                match_id=match["match_id"],
                pattern_id=pattern_id,
                pursuit_id=pursuit_id,
                response=response
            )


def create_biomimicry_context_provider(
    db,
    llm_gateway,
    event_publisher=None,
    config=None
):
    """
    Factory function to create a fully configured BiomimicryContextProvider.

    This is the recommended way to instantiate the provider, ensuring
    all dependencies are properly wired.

    Args:
        db: MongoDB database instance
        llm_gateway: LLM gateway for analysis
        event_publisher: Optional event publisher
        config: Optional configuration

    Returns:
        Tuple of (BiomimicryContextProvider, BiomimicryAnalyzer, BiomimicryDetector, BiomimicryFeedback)
    """
    # Import here to avoid circular imports
    import sys
    import os

    # Add ikf-service to path if needed
    ikf_path = os.path.join(os.path.dirname(__file__), "..", "..", "ikf-service")
    if ikf_path not in sys.path:
        sys.path.insert(0, ikf_path)

    from biomimicry.challenge_analyzer import BiomimicryAnalyzer
    from biomimicry.detection import BiomimicryDetector
    from biomimicry.feedback import BiomimicryFeedback

    analyzer = BiomimicryAnalyzer(db, llm_gateway, config)
    detector = BiomimicryDetector(db, config)
    feedback = BiomimicryFeedback(db, event_publisher)
    provider = BiomimicryContextProvider(analyzer, detector, config)

    return provider, analyzer, detector, feedback
