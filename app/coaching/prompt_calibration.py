"""
InDE v3.9 - ODICM Prompt Calibration Layer
Adapts coaching prompts based on LLM provider quality tier.

The calibration layer ensures effective coaching across different model capabilities:
- PREMIUM (Claude): Full ODICM prompts, complex reasoning, large context
- STANDARD (70B+): Moderate compression, simplified chains, good reasoning
- BASIC (7B-13B): Aggressive compression, numbered steps, explicit structure

This is NOT a dumbed-down version — it's an adapted version that preserves
innovation methodology integrity while working within model constraints.
"""

from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger("inde.coaching.calibration")


class QualityTier(str, Enum):
    """Quality tier classification matching LLM Gateway tiers."""
    PREMIUM = "premium"     # Claude-class models
    STANDARD = "standard"   # 70B+ local models
    BASIC = "basic"         # 7B-13B local models


# Token budgets per quality tier
TIER_BUDGETS = {
    QualityTier.PREMIUM: {
        "system_prompt": 3000,   # Full ODICM prompts
        "context": 8000,         # Rich conversation history
        "response": 4096         # Detailed coaching responses
    },
    QualityTier.STANDARD: {
        "system_prompt": 1500,   # Compressed prompts
        "context": 4000,         # Recent history only
        "response": 2048         # Moderate responses
    },
    QualityTier.BASIC: {
        "system_prompt": 800,    # Minimal essential prompts
        "context": 2000,         # Limited history
        "response": 1024         # Concise responses
    },
}

# Keywords to preserve in compressed prompts (methodology-critical)
METHODOLOGY_KEYWORDS = [
    "stage:", "archetype:", "scaffolding:", "current phase:",
    "innovator:", "pursuit:", "maturity:", "pattern:",
    "fear:", "vision:", "risk:", "team:", "hypothesis:",
    "experiment:", "milestone:", "convergence:", "health:"
]


def calibrate_system_prompt(
    original_prompt: str,
    quality_tier: str,
    pursuit_context: Optional[dict] = None
) -> str:
    """
    Adapt an ODICM system prompt for the given quality tier.

    Args:
        original_prompt: Full ODICM system prompt
        quality_tier: Provider quality tier (premium/standard/basic)
        pursuit_context: Optional pursuit-specific context

    Returns:
        Calibrated prompt appropriate for the model capability
    """
    tier = QualityTier(quality_tier) if isinstance(quality_tier, str) else quality_tier

    if tier == QualityTier.PREMIUM:
        # Claude - use original prompt unchanged
        return original_prompt

    if tier == QualityTier.STANDARD:
        return _compress_standard(original_prompt, pursuit_context)

    return _compress_basic(original_prompt, pursuit_context)


def _compress_standard(prompt: str, context: Optional[dict] = None) -> str:
    """
    Standard tier compression for 70B+ local models.

    Strategy:
    - Remove meta-commentary about model capabilities
    - Simplify nested conditional instructions
    - Preserve methodology terminology and stage structure
    - Reduce examples
    - Add explicit instruction about response format
    """
    calibration_prefix = """IMPORTANT: You are an innovation coach running on a local model.
Keep your responses focused and well-structured.
Use numbered lists for multi-step guidance.
Aim for 300-500 words unless more detail is requested.
Ask one clarifying question at a time.

"""

    # Truncate if needed
    budget = TIER_BUDGETS[QualityTier.STANDARD]["system_prompt"]
    max_chars = budget * 4  # ~4 chars per token estimate

    # Extract key sections from the prompt
    compressed = _extract_essential_sections(prompt, max_chars - len(calibration_prefix) * 4)

    return calibration_prefix + compressed


def _compress_basic(prompt: str, context: Optional[dict] = None) -> str:
    """
    Basic tier compression for 7B-13B local models.

    Strategy:
    - Extract only: role, current stage, key constraints
    - Replace natural language with numbered directives
    - Remove all examples and extended explanations
    - Maximum ~800 tokens
    """
    calibration_prefix = """INSTRUCTIONS: You are an innovation coach.

RULES:
1. Ask ONE question at a time
2. Guide the user through their innovation stage
3. Be encouraging but honest about challenges
4. Keep responses under 250 words
5. Use simple, clear language
6. If unsure, ask for clarification

"""

    # Extract only methodology-critical lines
    key_lines = []
    for line in prompt.split("\n"):
        line_lower = line.lower().strip()
        if any(kw in line_lower for kw in METHODOLOGY_KEYWORDS):
            key_lines.append(line.strip())

    # Build context section
    context_section = "CURRENT CONTEXT:\n"
    if key_lines:
        context_section += "\n".join(key_lines[:15])  # Limit lines
    else:
        context_section += "- Innovation coaching session in progress\n"

    # Add pursuit-specific context if available
    if context:
        title = context.get("title", "")
        stage = context.get("current_stage", "")
        if title:
            context_section += f"\n- Pursuit: {title}"
        if stage:
            context_section += f"\n- Stage: {stage}"

    # Ensure we stay within budget
    budget = TIER_BUDGETS[QualityTier.BASIC]["system_prompt"]
    max_chars = budget * 4

    full_prompt = calibration_prefix + context_section
    if len(full_prompt) > max_chars:
        full_prompt = full_prompt[:max_chars - 50] + "\n...[truncated]"

    return full_prompt


def _extract_essential_sections(prompt: str, max_chars: int) -> str:
    """
    Extract essential sections from a full ODICM prompt.

    ODICM prompts typically follow this structure:
    1. Role definition
    2. Methodology context (archetype, stage, scaffolding)
    3. Coaching philosophy
    4. Innovator context (patterns, maturity, history)
    5. Response instructions

    For standard tier, we keep 1, 2, 4, and a simplified 5.
    """
    sections = []
    current_section = []

    for line in prompt.split("\n"):
        # Detect section headers (usually all caps or markdown headers)
        if line.isupper() or line.startswith("#") or line.startswith("=="):
            if current_section:
                sections.append("\n".join(current_section))
            current_section = [line]
        else:
            current_section.append(line)

    if current_section:
        sections.append("\n".join(current_section))

    # Prioritize sections
    result_lines = []
    char_count = 0

    for section in sections:
        section_lower = section.lower()

        # High priority: role, methodology, context
        is_high_priority = any(kw in section_lower for kw in [
            "role", "methodology", "stage", "pursuit", "innovator",
            "scaffolding", "archetype", "context", "current"
        ])

        # Skip philosophy sections for compression
        is_philosophy = any(kw in section_lower for kw in [
            "philosophy", "principles", "approach", "guidelines"
        ])

        if is_high_priority and not is_philosophy:
            if char_count + len(section) < max_chars:
                result_lines.append(section)
                char_count += len(section)

    return "\n\n".join(result_lines)


def get_max_response_tokens(quality_tier: str) -> int:
    """Return the maximum response tokens for the given tier."""
    tier = QualityTier(quality_tier) if isinstance(quality_tier, str) else quality_tier
    return TIER_BUDGETS[tier]["response"]


def get_context_budget(quality_tier: str) -> int:
    """Return the context token budget for the given tier."""
    tier = QualityTier(quality_tier) if isinstance(quality_tier, str) else quality_tier
    return TIER_BUDGETS[tier]["context"]


def should_show_quality_indicator(quality_tier: str) -> bool:
    """
    Determine if the UI should show a quality indicator.

    Returns True for non-premium tiers where users should be aware
    of potential capability limitations.
    """
    tier = QualityTier(quality_tier) if isinstance(quality_tier, str) else quality_tier
    return tier != QualityTier.PREMIUM


def get_quality_indicator_message(quality_tier: str) -> Optional[str]:
    """
    Get the message to display in the UI quality indicator.

    Returns None for premium tier (no indicator needed).
    """
    tier = QualityTier(quality_tier) if isinstance(quality_tier, str) else quality_tier

    if tier == QualityTier.PREMIUM:
        return None
    elif tier == QualityTier.STANDARD:
        return "Running on local model — coaching quality may vary slightly"
    else:
        return "Running on local model — some advanced reasoning may be limited"


# Cached quality tier for the session
_current_quality_tier: Optional[QualityTier] = None


def set_quality_tier(tier: str):
    """Set the current quality tier (called when gateway reports tier)."""
    global _current_quality_tier
    _current_quality_tier = QualityTier(tier)
    logger.info(f"Quality tier set to: {tier}")


def get_quality_tier() -> QualityTier:
    """Get the current quality tier, defaulting to PREMIUM if not set."""
    global _current_quality_tier
    return _current_quality_tier or QualityTier.PREMIUM
