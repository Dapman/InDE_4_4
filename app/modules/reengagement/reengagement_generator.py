"""
Re-Engagement Message Generator

Generates pursuit-specific, coach-voiced re-engagement messages for
async delivery. These are single coaching questions about the
innovator's specific idea — not platform reminders.

Message structure:
  Subject (email): A thought I had about [idea_summary]
  Body: A single question about their specific idea, framed as
        something the coach has been thinking about since the last
        session.

All messages MUST:
  - Be pursuit-specific (reference the actual idea)
  - End with a single question
  - Sound like the coach, not the platform
  - Contain no methodology terminology
  - Not mention InDE by name in the body (it's from the coach,
    not a system notification)
  - Not explain why the message is being sent
    ("we noticed you haven't logged in" is explicitly FORBIDDEN)
"""

import random
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Re-engagement message templates organized by:
# momentum tier at exit × attempt number (1 or 2)
# Attempt 1: gentle curiosity — opens a new angle on the idea
# Attempt 2 (if attempt 1 unanswered): reconnects with core motivation

REENGAGEMENT_TEMPLATES = {

    "HIGH": {
        1: [
            {
                "subject": "A thought about {idea_summary}",
                "body": (
                    "Something from our last conversation has been sitting with me. "
                    "You were making real progress on {idea_summary}. "
                    "Here's a question I've been wondering about: "
                    "{bridge_question}"
                )
            },
            {
                "subject": "Still thinking about {idea_domain}",
                "body": (
                    "I've been thinking about {idea_summary} since we last talked. "
                    "One question that keeps coming up: "
                    "{bridge_question}"
                )
            },
        ],
        2: [
            {
                "subject": "One more thought on {idea_summary}",
                "body": (
                    "I don't want to crowd your inbox, but I wanted to leave you "
                    "with one thought about {idea_summary} in case it's useful: "
                    "{bridge_question}"
                )
            },
        ],
    },

    "MEDIUM": {
        1: [
            {
                "subject": "A question about {idea_summary}",
                "body": (
                    "I've been thinking about where we left things with "
                    "{idea_summary}. One question came to mind: "
                    "{bridge_question}"
                )
            },
            {
                "subject": "Something I've been wondering about {idea_domain}",
                "body": (
                    "A thought about {idea_summary} that I wanted to share: "
                    "{bridge_question}"
                )
            },
        ],
        2: [
            {
                "subject": "Last thought on {idea_summary} for now",
                "body": (
                    "One last thought about {idea_summary} before I give you "
                    "some space: "
                    "{bridge_question}"
                )
            },
        ],
    },

    "LOW": {
        1: [
            {
                "subject": "A simple question about {idea_summary}",
                "body": (
                    "I've been thinking about {idea_summary}. "
                    "Just one question — no pressure: "
                    "{bridge_question}"
                )
            },
            {
                "subject": "Something that might be worth sitting with",
                "body": (
                    "One thought about {idea_summary} that I wanted to pass along: "
                    "{bridge_question}"
                )
            },
        ],
        2: [
            {
                "subject": "One last thought on {idea_summary}",
                "body": (
                    "I'll keep this short. One question about {idea_summary} "
                    "that I think is worth sitting with: "
                    "{bridge_question}"
                )
            },
        ],
    },

    "CRITICAL": {
        1: [
            {
                "subject": "Something about {idea_summary}",
                "body": (
                    "Just one question. No agenda: "
                    "{bridge_question}"
                )
            },
        ],
        2: [
            {
                "subject": "One thought, then I'll give you space",
                "body": (
                    "One question about {idea_summary}, then I'll leave "
                    "you alone for a while: "
                    "{bridge_question}"
                )
            },
        ],
    },

    "_no_snapshot": {
        1: [
            {
                "subject": "A thought about {idea_summary}",
                "body": (
                    "One question about {idea_summary} that came to mind: "
                    "{bridge_question}"
                )
            },
        ],
        2: [
            {
                "subject": "Last thought on {idea_summary} for now",
                "body": (
                    "One last thought about {idea_summary}: "
                    "{bridge_question}"
                )
            },
        ],
    },
}

# Bridge questions for async re-engagement
# These are lower-intensity than in-session bridges — designed to be
# easy to think about without requiring the platform to be open
ASYNC_BRIDGE_QUESTIONS = {
    "vision": [
        "Who is the single person who would benefit most from {idea_summary} — and do you know someone like that you could talk to this week?",
        "What's the part of {idea_summary} that you're most confident about right now?",
        "If {idea_summary} worked exactly as you imagine it, what would be different for {persona}?",
    ],
    "fear": [
        "Of all the things that could go wrong with {idea_summary}, which one are you most confident you could handle?",
        "What's one small step you could take this week that would make {idea_summary} feel a little more real?",
        "What would you need to learn to feel more confident about {idea_summary}?",
    ],
    "validation": [
        "What has the evidence you've gathered told you about {idea_summary} that you didn't know before?",
        "What would the next test of {idea_summary} look like?",
        "Based on what you know now, what's the part of {idea_summary} you feel best about?",
    ],
    "_default": [
        "What's the most interesting question you have about {idea_summary} right now?",
        "What part of {idea_summary} have you been thinking about most?",
        "If you had one hour to work on {idea_summary} today, what would you do?",
    ],
}


class ReengagementGenerator:
    """
    Generates async re-engagement messages for inactive innovators.
    """

    def generate(
        self,
        pursuit_context: dict,
        momentum_tier: Optional[str],
        artifact_at_exit: Optional[str],
        attempt_number: int = 1
    ) -> dict:
        """
        Generate a re-engagement message.

        Args:
            pursuit_context: dict with idea_summary, idea_domain, persona
            momentum_tier:   Exit momentum tier from last snapshot (or None)
            artifact_at_exit: Last active artifact key (or None)
            attempt_number:  1 or 2 (max 2 attempts per gap)

        Returns:
            dict with 'subject' and 'body' keys
        """
        tier_key = momentum_tier if momentum_tier else "_no_snapshot"
        attempt_key = min(attempt_number, 2)

        # Get message templates
        tier_templates = REENGAGEMENT_TEMPLATES.get(
            tier_key, REENGAGEMENT_TEMPLATES["_no_snapshot"]
        )
        templates = tier_templates.get(attempt_key, tier_templates.get(1, []))
        if not templates:
            templates = REENGAGEMENT_TEMPLATES["_no_snapshot"][1]

        template = random.choice(templates)

        # Get bridge question
        bridge_pool = ASYNC_BRIDGE_QUESTIONS.get(
            artifact_at_exit or "_default",
            ASYNC_BRIDGE_QUESTIONS["_default"]
        )
        bridge_question = random.choice(bridge_pool)

        # Inject context into bridge question
        bridge_question = self._inject(bridge_question, pursuit_context)

        # Inject into message template
        full_context = {**pursuit_context, "bridge_question": bridge_question}
        subject = self._inject(template["subject"], full_context)
        body = self._inject(template["body"], full_context)

        logger.info(
            f"Re-engagement generated: tier={tier_key}, "
            f"attempt={attempt_number}, "
            f"subject='{subject}'"
        )
        return {"subject": subject, "body": body}

    def _inject(self, text: str, context: dict) -> str:
        defaults = {
            "idea_summary":     "your idea",
            "idea_domain":      "this space",
            "persona":          "the people you're helping",
            "bridge_question":  "What's on your mind about this?",
        }
        merged = {**defaults, **{k: v for k, v in context.items() if v}}
        try:
            result = text
            for key, value in merged.items():
                result = result.replace(f"{{{key}}}", str(value))
            result = re.sub(r'\{[a-z_]+\}', "your idea", result)
            result = re.sub(r'  +', ' ', result).strip()
            return result
        except Exception:
            return text
