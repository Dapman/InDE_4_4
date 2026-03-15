"""
Biomimicry Detection: Determines WHEN to invoke the Challenge Analyzer.

Not every coaching turn should trigger biomimicry analysis. Detection
evaluates whether the current coaching context warrants checking for
biological parallels.

Triggers:
1. Pursuit creation / vision formulation - challenge description available
2. Fear exploration - risk/barrier may have biological solution analog
3. Phase transition - moving to VALIDATION or REFINEMENT
4. Explicit query - innovator asks about nature-inspired approaches
5. Cross-pollination - IKF pattern with biological domain detected

Anti-triggers (do NOT invoke biomimicry):
- Routine progress updates
- Administrative conversations
- Retrospective sessions
- Already offered biomimicry this session (cooldown)
"""

import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger("inde.ikf.biomimicry.detection")

# Keywords that indicate explicit interest in nature-inspired solutions
EXPLICIT_QUERY_KEYWORDS = [
    "nature", "biological", "biomimicry", "natural solution",
    "how does nature", "natural world", "organism", "evolution",
    "animal", "plant", "insect", "creature", "species",
    "evolved", "adaptation", "ecosystem", "bioinspired",
    "bio-inspired", "biomimetic", "living system"
]

# Keywords that indicate the conversation is administrative (skip analysis)
ADMINISTRATIVE_KEYWORDS = [
    "meeting", "schedule", "calendar", "team member",
    "budget", "deadline", "status update", "progress report",
    "retrospective", "sprint planning", "standup"
]


class BiomimicryDetector:
    """
    Determines when biomimicry analysis should be invoked.

    The detector uses lightweight heuristics (no LLM calls) to decide
    whether the current conversation context warrants checking for
    biological parallels. This keeps detection fast and inexpensive.

    Key design principles:
    - Never force biomimicry on unsuitable contexts
    - Cooldown prevents overwhelming the innovator
    - Explicit queries always trigger analysis
    - Phase transitions are prime opportunities
    """

    def __init__(self, db, config=None):
        """
        Initialize the Biomimicry Detector.

        Args:
            db: MongoDB database instance
            config: Optional configuration object
        """
        self._db = db
        self._config = config
        self._session_cooldown_turns = 5  # Don't re-offer for 5 turns after last offer

    async def should_analyze(
        self,
        conversation_context: Dict[str, Any],
        pursuit_state: Dict[str, Any],
        recent_biomimicry_offer_turn: Optional[int] = None,
        current_turn: int = 0
    ) -> Tuple[bool, str]:
        """
        Determines whether to invoke biomimicry analysis.

        This is the main entry point called by the coaching context assembly
        pipeline. It returns quickly without any LLM calls.

        Args:
            conversation_context: Current conversation context
                - last_user_message: Most recent user input
                - conversation_history: Optional list of recent messages
            pursuit_state: Current pursuit state
                - universal_state: Current phase (DISCOVERY, DEFINITION, etc.)
                - challenge_text: The innovation challenge description
                - domain: Optional domain context
                - active_fears: List of active fears
                - phase_transition_pending: Whether a transition is imminent
            recent_biomimicry_offer_turn: Turn number of last biomimicry offer
            current_turn: Current turn number

        Returns:
            Tuple of (should_analyze: bool, trigger_reason: str)
        """
        # Check cooldown first (most common rejection)
        if recent_biomimicry_offer_turn is not None:
            turns_since_offer = current_turn - recent_biomimicry_offer_turn
            if turns_since_offer < self._session_cooldown_turns:
                return False, "cooldown_active"

        last_message = conversation_context.get("last_user_message", "")
        last_message_lower = last_message.lower()

        # Check for administrative context (skip analysis)
        if self._is_administrative(last_message_lower):
            return False, "administrative_context"

        # Check explicit query (always trigger)
        if self._is_explicit_query(last_message_lower):
            return True, "explicit_query"

        # Check pursuit state triggers
        universal_state = pursuit_state.get("universal_state", "")

        # Vision formulation and problem definition - prime for biomimicry
        if universal_state in ("DISCOVERY", "DEFINITION"):
            challenge_text = pursuit_state.get("challenge_text", "")
            if len(challenge_text) > 50:  # Enough context to analyze
                return True, "challenge_available"

        # Fear/risk exploration context
        active_fears = pursuit_state.get("active_fears", [])
        if active_fears and universal_state in ("DISCOVERY", "DEFINITION", "VALIDATION"):
            return True, "fear_context"

        # Phase transition
        if pursuit_state.get("phase_transition_pending", False):
            return True, "phase_transition"

        # Validation phase with technical focus
        if universal_state == "VALIDATION":
            # Check if the message mentions technical challenges
            tech_keywords = ["build", "implement", "design", "engineer", "prototype",
                           "test", "develop", "create", "make", "construct"]
            if any(kw in last_message_lower for kw in tech_keywords):
                return True, "validation_technical"

        # Check message length and content density
        # Longer, substantive messages are more likely to benefit from analysis
        if len(last_message) > 200 and not self._is_short_response(last_message_lower):
            # Check for problem-oriented language
            problem_keywords = ["challenge", "problem", "issue", "difficulty",
                              "struggle", "need to", "want to", "how can",
                              "trying to", "looking for", "solution"]
            if any(kw in last_message_lower for kw in problem_keywords):
                return True, "substantive_challenge"

        return False, "no_trigger"

    def _is_explicit_query(self, message: str) -> bool:
        """Check if the message explicitly asks about nature-inspired solutions."""
        return any(keyword in message for keyword in EXPLICIT_QUERY_KEYWORDS)

    def _is_administrative(self, message: str) -> bool:
        """Check if the message is administrative in nature."""
        return any(keyword in message for keyword in ADMINISTRATIVE_KEYWORDS)

    def _is_short_response(self, message: str) -> bool:
        """Check if the message is a short response that doesn't warrant analysis."""
        short_responses = [
            "yes", "no", "ok", "okay", "sure", "thanks", "thank you",
            "got it", "understood", "makes sense", "i see", "right",
            "let me think", "good point", "interesting"
        ]
        stripped = message.strip().lower().rstrip(".")
        return stripped in short_responses or len(stripped) < 10

    def get_cooldown_remaining(
        self,
        recent_biomimicry_offer_turn: Optional[int],
        current_turn: int
    ) -> int:
        """Get number of turns remaining in cooldown period."""
        if recent_biomimicry_offer_turn is None:
            return 0
        turns_since = current_turn - recent_biomimicry_offer_turn
        remaining = self._session_cooldown_turns - turns_since
        return max(0, remaining)

    async def get_dismissed_patterns(self, pursuit_id: str) -> set:
        """Get pattern IDs that have been dismissed for this pursuit."""
        matches = self._db.biomimicry_matches.find({
            "pursuit_id": pursuit_id,
            "innovator_response": "dismissed"
        })
        return {m["pattern_id"] for m in matches}

    async def filter_dismissed(
        self,
        pattern_ids: list,
        pursuit_id: str
    ) -> list:
        """Filter out patterns that have been dismissed for this pursuit."""
        dismissed = await self.get_dismissed_patterns(pursuit_id)
        return [pid for pid in pattern_ids if pid not in dismissed]
