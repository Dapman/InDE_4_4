"""
IKF Pattern Context Builder - v3.5.2

Retrieves relevant IKF-sourced patterns for coaching context.
When ODICM surfaces an IKF-sourced pattern, the coaching language
makes the source clear with proper attribution.

Attribution templates:
- "Innovators across the InDEVerse have found that..."
- "A pattern from [industry] suggests..."
- "Cross-organizational data indicates that..."

Token Budget:
- IKF_PATTERN_TOKEN_BUDGET = 500 (max tokens for IKF pattern context per turn)
- Total per-turn budget: 12,000 (up from 11,500 in v3.5.1)
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger("inde.scaffolding.ikf_pattern_context")

# Token budget for IKF patterns in coaching context
IKF_PATTERN_TOKEN_BUDGET = 500
MAX_IKF_PATTERNS_PER_TURN = 3

# Attribution templates by pattern type
ATTRIBUTION_TEMPLATES = {
    "success_pattern": "Innovators across the InDEVerse have found that",
    "failure_pattern": "A pattern observed across multiple organizations suggests",
    "predictive_pattern": "Cross-organizational data indicates that",
    "process_pattern": "Teams in similar domains have discovered that",
    "domain_bridge": "An interesting connection from a different industry shows that"
}


def get_ikf_patterns_for_context(db, pursuit_context: dict) -> List[dict]:
    """
    Retrieve relevant IKF-sourced patterns for coaching context.

    Only returns INTEGRATED patterns from ikf_federation_patterns.
    Scored by relevance to current pursuit domain/problem space.

    Args:
        db: MongoDB database instance
        pursuit_context: Current pursuit context dict

    Returns:
        List of formatted IKF patterns (max 3)
    """
    # Check if federation patterns collection exists and has data
    try:
        pattern_count = db.ikf_federation_patterns.count_documents({"status": "INTEGRATED"})
        if pattern_count == 0:
            return []
    except Exception:
        return []  # Collection may not exist

    # Build query for relevant patterns
    query = {"status": "INTEGRATED"}

    # Filter by industry if available
    industry = pursuit_context.get("industry_code")
    if industry:
        query["$or"] = [
            {"applicability.industries": industry},
            {"applicability.industries": "ALL"}
        ]

    # Filter by methodology if available
    methodology = pursuit_context.get("methodology")
    if methodology:
        query["$or"] = query.get("$or", []) + [
            {"applicability.methodologies": methodology}
        ]

    # Query patterns sorted by confidence
    try:
        patterns = list(db.ikf_federation_patterns.find(
            query,
            {"_id": 0, "content_hash": 0}
        ).sort("confidence", -1).limit(MAX_IKF_PATTERNS_PER_TURN))
    except Exception as e:
        logger.warning(f"Failed to query IKF patterns: {e}")
        return []

    return patterns


def format_ikf_pattern_for_coaching(pattern: dict) -> str:
    """
    Format an IKF pattern for inclusion in coaching prompt.

    IMPORTANT: Always includes attribution language.

    Args:
        pattern: The IKF pattern dict

    Returns:
        Formatted string with attribution
    """
    pattern_type = pattern.get("type", "pattern")
    content = pattern.get("content", {})
    confidence = pattern.get("confidence", 0)
    title = pattern.get("title", "")

    # Get appropriate attribution
    attribution = ATTRIBUTION_TEMPLATES.get(
        pattern_type,
        "A global innovation pattern suggests that"
    )

    summary = content.get("summary", "")
    takeaways = content.get("key_takeaways", [])

    formatted = f"[IKF Pattern - Confidence: {confidence:.0%}]\n"
    if title:
        formatted += f"**{title}**\n"
    formatted += f"{attribution} {summary}"

    if takeaways and len(takeaways) > 0:
        formatted += f"\n- Key insight: {takeaways[0]}"

    return formatted


def build_ikf_coaching_context(db, pursuit_context: dict) -> Optional[Dict[str, Any]]:
    """
    Build the IKF pattern context block for coaching.

    Returns None if no relevant patterns are found.

    Args:
        db: MongoDB database instance
        pursuit_context: Current pursuit context

    Returns:
        IKF context dict or None
    """
    patterns = get_ikf_patterns_for_context(db, pursuit_context)

    if not patterns:
        return None

    formatted_patterns = []
    total_tokens_estimate = 0

    for pattern in patterns:
        formatted = format_ikf_pattern_for_coaching(pattern)
        # Rough token estimate: 4 chars per token
        pattern_tokens = len(formatted) // 4

        if total_tokens_estimate + pattern_tokens > IKF_PATTERN_TOKEN_BUDGET:
            break  # Stay within budget

        formatted_patterns.append({
            "pattern_id": pattern.get("pattern_id"),
            "type": pattern.get("type"),
            "formatted": formatted,
            "confidence": pattern.get("confidence")
        })
        total_tokens_estimate += pattern_tokens

    if not formatted_patterns:
        return None

    return {
        "has_ikf_patterns": True,
        "patterns": formatted_patterns,
        "pattern_count": len(formatted_patterns),
        "token_estimate": total_tokens_estimate,
        "attribution_note": (
            "When referencing these patterns, use phrases like "
            "'Innovators across the InDEVerse have found...' or "
            "'Cross-organizational data indicates...'"
        )
    }


async def record_pattern_feedback(
    db,
    pattern_id: str,
    feedback: str,
    pursuit_id: Optional[str] = None
):
    """
    Record innovator feedback on an IKF pattern.

    Called when analysis detects the innovator applied, explored,
    or dismissed a surfaced pattern.

    Args:
        db: MongoDB database instance
        pattern_id: The pattern being rated
        feedback: "applied" | "explored" | "dismissed"
        pursuit_id: Optional pursuit context
    """
    update = {"$push": {"feedback": {
        "type": feedback,
        "pursuit_id": pursuit_id,
        "timestamp": datetime.now(timezone.utc)
    }}}

    if feedback == "applied":
        update["$inc"] = {"application_count": 1}
    elif feedback == "dismissed":
        update["$inc"] = {"dismissal_count": 1}

    db.ikf_federation_patterns.update_one(
        {"pattern_id": pattern_id},
        update
    )

    logger.info(f"Pattern {pattern_id} feedback recorded: {feedback}")


def get_ikf_prompt_section(ikf_context: Optional[Dict]) -> str:
    """
    Generate the IKF section for the coaching prompt.

    Args:
        ikf_context: The IKF context from build_ikf_coaching_context

    Returns:
        Prompt section string or empty string if no patterns
    """
    if not ikf_context or not ikf_context.get("has_ikf_patterns"):
        return ""

    patterns = ikf_context.get("patterns", [])
    if not patterns:
        return ""

    section = "\n\n## Relevant Global Innovation Patterns (from InDEVerse)\n"
    section += "The following patterns from the global innovation network may be relevant:\n\n"

    for p in patterns:
        section += p.get("formatted", "") + "\n\n"

    section += (
        "Note: When referencing these patterns, use attribution language "
        "to indicate they come from the global InDE network.\n"
    )

    return section
