"""
Momentum Signal Collectors

Four specialized extractors that observe conversational turns and
return normalized signal scores (0.0–1.0) for each momentum dimension.

All scoring is conservative — it is better to underestimate momentum
and select a re-grounding bridge than to overestimate and miss a
flagging innovator.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MomentumSignals:
    """
    The four observable momentum dimensions extracted from a conversation turn.

    Each score is 0.0 (low momentum signal) to 1.0 (high momentum signal).
    Composite score is computed by MomentumManagementEngine, not here.
    """
    response_specificity: float    # How detailed and precise is the response?
    conversational_lean: float     # Is the innovator leaning toward the pursuit?
    temporal_commitment: float     # Are they referencing future action?
    idea_ownership: float          # Are they claiming the idea as theirs?

    def __post_init__(self):
        for field in ['response_specificity', 'conversational_lean',
                      'temporal_commitment', 'idea_ownership']:
            val = getattr(self, field)
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{field} must be 0.0–1.0, got {val}")


class ResponseSpecificityCollector:
    """
    Measures how detailed and precise the innovator's response is.

    High specificity: Names, numbers, specific people, concrete examples,
    domain-specific language, detailed scenarios.

    Low specificity: Vague generalities, one-word answers, restating
    the coach's question, hedging without substance.

    Weight in composite: 0.30
    """

    # Specificity indicators
    SPECIFICITY_PATTERNS = [
        r'\b\d+\b',                          # Numbers (counts, metrics, dates)
        r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b',    # Proper nouns (names, places)
        r'\b(because|specifically|exactly|'
        r'particularly|especially|namely)\b',# Precision language
        r'\b(percent|%|million|thousand|'
        r'hundred)\b',                        # Quantification
        r'"[^"]{5,}"',                        # Quoted specific terms
        r"'[^']{5,}'",
    ]

    # Low specificity patterns
    VAGUENESS_PATTERNS = [
        r'^(yes|no|yeah|okay|ok|sure|maybe|'
        r'i guess|perhaps|possibly)\.?\s*$',  # One-word non-answers
        r'\b(something|somehow|some kind of|'
        r'sort of|kind of|stuff|things)\b',   # Vague nouns
        r'\b(whatever|whoever|whenever|'
        r'wherever)\b',                        # Vague reference
    ]

    def score(self, message: str, word_count: int) -> float:
        if not message or word_count == 0:
            return 0.0

        text = message.lower()

        # Base score from word count — longer responses are more specific
        # Threshold: <10 words = low, 10-30 = medium, 30+ = high
        length_score = min(1.0, word_count / 50.0)

        # Specificity bonus
        specificity_hits = sum(
            1 for pattern in self.SPECIFICITY_PATTERNS
            if re.search(pattern, message)
        )
        specificity_bonus = min(0.4, specificity_hits * 0.1)

        # Vagueness penalty
        vagueness_hits = sum(
            1 for pattern in self.VAGUENESS_PATTERNS
            if re.search(pattern, text)
        )
        vagueness_penalty = min(0.4, vagueness_hits * 0.15)

        raw = length_score + specificity_bonus - vagueness_penalty
        return max(0.0, min(1.0, raw))


class ConversationalLeanCollector:
    """
    Measures whether the innovator's last message ends with forward
    energy — a question, a new idea, an expressed desire to continue —
    rather than a statement that closes a thought.

    High lean: Message ends with a question. Message introduces a new
    angle. Message expresses curiosity or anticipation about the idea.

    Low lean: Message is purely reactive/responsive. Message uses
    closure language. Message expresses doubt or withdrawal.

    Weight in composite: 0.25
    """

    FORWARD_PATTERNS = [
        r'\?$',                               # Ends with question
        r'\bwhat if\b',                       # Hypothetical exploration
        r'\bi wonder\b',                      # Expressed curiosity
        r'\bwhat about\b',                    # Opening new angle
        r'\bcould (we|i|this)\b',             # Possibility language
        r'\bthat makes me think\b',           # Active thinking
        r'\band also\b',                      # Additive energy
        r'\banother thing\b',                 # Continuing momentum
        r'\bi\'d like to\b',                  # Expressed desire
        r'\bcan\'t wait\b',                   # Anticipation
    ]

    CLOSURE_PATTERNS = [
        r'\bthat\'s (all|it|everything)\b',   # Closure
        r'\bi think (that\'s|we\'re) done\b', # Explicit close
        r'\bi have to go\b',                  # Exit signal
        r'\bwe can stop\b',                   # Stop signal
        r'\bnot sure (this|i) (works|can)\b', # Withdrawal signal
        r'\bmaybe another time\b',            # Deferral
        r'\bforget it\b',                     # Abandonment
    ]

    def score(self, message: str) -> float:
        if not message:
            return 0.3  # Neutral — no message means no signal

        text = message.lower().strip()

        forward_hits = sum(
            1 for pattern in self.FORWARD_PATTERNS
            if re.search(pattern, text)
        )
        closure_hits = sum(
            1 for pattern in self.CLOSURE_PATTERNS
            if re.search(pattern, text)
        )

        # Base: neutral (0.5)
        base = 0.5
        forward_bonus = min(0.5, forward_hits * 0.15)
        closure_penalty = min(0.5, closure_hits * 0.25)

        return max(0.0, min(1.0, base + forward_bonus - closure_penalty))


class TemporalCommitmentCollector:
    """
    Measures whether the innovator is referencing future action in
    their own words — indicating they are mentally committed to
    continuing work on the idea after this session.

    High commitment: References to what they will do, plan to do,
    want to try, will ask, will build, will test.

    Low commitment: Only present or past tense. No future reference.
    Passive framing ("it would be nice if").

    Weight in composite: 0.25
    """

    COMMITMENT_PATTERNS = [
        r'\b(i will|i\'ll|we will|we\'ll)\b',         # Direct future
        r'\b(i\'m going to|i am going to)\b',          # Planned future
        r'\b(i want to|i\'d like to)\s+\w+\s+(it|this|that|them)\b',
        r'\b(next (week|month|day)|tomorrow)\b',        # Near-term time ref
        r'\b(plan to|planning to|intend to)\b',         # Intentional future
        r'\b(will (try|test|ask|build|check|talk|reach))\b',
        r'\b(going to (try|test|ask|build|check|talk|reach))\b',
        r'\b(by (monday|friday|next week|the end of))\b',  # Deadline ref
    ]

    PASSIVE_PATTERNS = [
        r'\b(it would be nice if|someday|eventually|at some point)\b',
        r'\b(if things work out|if i get a chance)\b',
        r'\b(someone should|someone could)\b',           # Diffusing ownership
    ]

    def score(self, message: str) -> float:
        if not message:
            return 0.2  # Low default — no commitment signal

        text = message.lower()

        commitment_hits = sum(
            1 for pattern in self.COMMITMENT_PATTERNS
            if re.search(pattern, text)
        )
        passive_hits = sum(
            1 for pattern in self.PASSIVE_PATTERNS
            if re.search(pattern, text)
        )

        if commitment_hits == 0 and passive_hits == 0:
            return 0.3  # Neutral — no temporal signal either way

        base = min(1.0, commitment_hits * 0.35)
        passive_penalty = min(0.3, passive_hits * 0.15)

        return max(0.0, min(1.0, base - passive_penalty))


class IdeaOwnershipCollector:
    """
    Measures whether the innovator is claiming the idea as their own
    in their language — using possessive and active framing rather
    than distancing or spectator language.

    High ownership: "My idea", "what I'm building", "the problem I've
    seen", "my users", "the people I talked to". Active first-person
    engagement with the pursuit's specifics.

    Low ownership: Passive third-person framing. Generic "one could"
    or "people might" language. Hedged "if this were real" framing.

    Weight in composite: 0.20
    """

    OWNERSHIP_PATTERNS = [
        r'\b(my (idea|solution|approach|users|customers|problem|design|product|service))\b',
        r'\b(i\'ve (built|created|designed|seen|noticed|found|learned))\b',
        r'\b(i (built|created|designed|noticed|discovered|validated))\b',
        r'\b(what i\'m (building|creating|designing|working on))\b',
        r'\b(the people i (talked|spoke|work) with)\b',
        r'\b(my (target|intended|actual) (users|customers|audience))\b',
        r'\b(in my (experience|field|industry|work))\b',
    ]

    DISTANCING_PATTERNS = [
        r'\b(hypothetically|theoretically|in theory|if this were real)\b',
        r'\b(one could|one might|a person might|people might)\b',
        r'\b(it\'s (just|only) an idea)\b',                  # Self-minimizing
        r'\b(probably (won\'t|doesn\'t|can\'t) work)\b',    # Pre-abandoned
        r'\b(someone else (probably|already|could))\b',      # Diffusion
    ]

    def score(self, message: str) -> float:
        if not message:
            return 0.3

        text = message.lower()

        ownership_hits = sum(
            1 for pattern in self.OWNERSHIP_PATTERNS
            if re.search(pattern, text)
        )
        distancing_hits = sum(
            1 for pattern in self.DISTANCING_PATTERNS
            if re.search(pattern, text)
        )

        base = 0.4  # Neutral default
        ownership_bonus = min(0.6, ownership_hits * 0.2)
        distancing_penalty = min(0.4, distancing_hits * 0.2)

        return max(0.0, min(1.0, base + ownership_bonus - distancing_penalty))


def collect_signals(message: str) -> MomentumSignals:
    """
    Entry point: extract all four momentum signals from a single
    conversational message. Called by MomentumManagementEngine
    after every innovator turn.

    Args:
        message: The innovator's raw message text

    Returns:
        MomentumSignals with scores for all four dimensions
    """
    word_count = len(message.split()) if message else 0

    return MomentumSignals(
        response_specificity=ResponseSpecificityCollector().score(message, word_count),
        conversational_lean=ConversationalLeanCollector().score(message),
        temporal_commitment=TemporalCommitmentCollector().score(message),
        idea_ownership=IdeaOwnershipCollector().score(message),
    )
