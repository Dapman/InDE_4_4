"""
InDE v3.1 - Claude API Provider
Anthropic Claude API integration for the LLM Gateway.
"""

import os
import logging
from typing import Optional, Tuple

import anthropic

logger = logging.getLogger("llm-gateway.claude")

# API configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")

# Initialize client
_client = None


def get_client() -> anthropic.Anthropic:
    """Get or create Anthropic client."""
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


async def generate_claude_response(
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 1000,
    model: Optional[str] = None
) -> Tuple[str, int]:
    """
    Generate response using Claude API.

    Args:
        prompt: User prompt/message
        system: Optional system prompt
        max_tokens: Maximum tokens to generate
        model: Model to use (defaults to DEFAULT_MODEL)

    Returns:
        Tuple of (response_text, tokens_used)
    """
    client = get_client()
    model = model or DEFAULT_MODEL

    try:
        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Make API call
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system or "You are a helpful innovation coach.",
            messages=messages
        )

        # Extract response
        content = response.content[0].text if response.content else ""

        # Calculate tokens used
        tokens_used = (
            response.usage.input_tokens +
            response.usage.output_tokens
        )

        logger.info(f"Claude response generated: {tokens_used} tokens used")

        return content, tokens_used

    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Claude provider: {e}")
        raise
