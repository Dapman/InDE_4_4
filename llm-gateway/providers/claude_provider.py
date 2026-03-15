"""
InDE v3.9 - Claude (Anthropic) Provider
Anthropic Claude API integration with BaseProvider interface.

This provider handles all communication with Anthropic's Claude API,
including streaming and non-streaming chat completions.
"""

import os
import json
import logging
from typing import AsyncGenerator, Optional

import anthropic

from .base_provider import (
    BaseProvider, QualityTier, ProviderStatus,
    ChatRequest, ChatResponse
)

logger = logging.getLogger("llm-gateway.claude")


class ClaudeProvider(BaseProvider):
    """
    Anthropic Claude API provider.

    Always reports PREMIUM quality tier as Claude models have
    advanced reasoning capabilities suitable for full ODICM prompts.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model to use (defaults to DEFAULT_MODEL env var)
        """
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._model = model or os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")
        self._client: Optional[anthropic.Anthropic] = None
        self._async_client: Optional[anthropic.AsyncAnthropic] = None

        # Initialize client if API key is available
        if self._api_key:
            self._client = anthropic.Anthropic(api_key=self._api_key)
            self._async_client = anthropic.AsyncAnthropic(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "anthropic"

    def update_api_key(self, api_key: str):
        """Update API key at runtime (for BYOK support)."""
        self._api_key = api_key
        self._client = anthropic.Anthropic(api_key=api_key)
        self._async_client = anthropic.AsyncAnthropic(api_key=api_key)
        logger.info("Claude provider API key updated")

    async def is_available(self) -> bool:
        """Check if Claude API is configured and reachable."""
        if not self._api_key or not self._client:
            return False

        try:
            # Quick validation - check key format
            if not self._api_key.startswith("sk-ant-"):
                return False
            return True
        except Exception as e:
            logger.warning(f"Claude availability check failed: {e}")
            return False

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Non-streaming chat completion via Claude API.

        Args:
            request: Standardized chat request

        Returns:
            ChatResponse with content and usage
        """
        if not self._async_client:
            raise RuntimeError("Claude provider not initialized (no API key)")

        try:
            # Build messages in Claude format
            messages = []
            for msg in request.messages:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # Make API call
            response = await self._async_client.messages.create(
                model=self._model,
                max_tokens=request.max_tokens,
                system=request.system_prompt or "You are a helpful innovation coach.",
                messages=messages,
                temperature=request.temperature
            )

            # Extract response
            content = response.content[0].text if response.content else ""
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }

            logger.info(f"Claude response: {usage['input_tokens']}+{usage['output_tokens']} tokens")

            return ChatResponse(
                content=content,
                usage=usage,
                provider=self.name,
                quality_tier=QualityTier.PREMIUM,
                model=self._model,
                failover=False
            )

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Claude provider error: {e}")
            raise

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Streaming chat completion via Claude API.

        Yields SSE-formatted chunks compatible with frontend expectations.
        """
        if not self._async_client:
            raise RuntimeError("Claude provider not initialized (no API key)")

        try:
            # Build messages
            messages = []
            for msg in request.messages:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # Stream response
            async with self._async_client.messages.stream(
                model=self._model,
                max_tokens=request.max_tokens,
                system=request.system_prompt or "You are a helpful innovation coach.",
                messages=messages,
                temperature=request.temperature
            ) as stream:
                async for text in stream.text_stream:
                    # Emit in SSE format
                    chunk_data = {
                        "type": "content_block_delta",
                        "delta": {"text": text}
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"

        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    async def get_status(self) -> ProviderStatus:
        """Return Claude provider status."""
        available = await self.is_available()

        error = None
        if not self._api_key:
            error = "No API key configured"
        elif not self._api_key.startswith("sk-ant-"):
            error = "Invalid API key format"

        return ProviderStatus(
            name=self.name,
            available=available,
            quality_tier=QualityTier.PREMIUM,
            current_model=self._model,
            context_window=200000,  # Claude has large context
            error=error,
            metadata={
                "api_configured": bool(self._api_key),
                "model": self._model
            }
        )


# Backward compatibility - keep the old function for existing code
async def generate_claude_response(
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 1000,
    model: Optional[str] = None
) -> tuple[str, int]:
    """
    Legacy function for backward compatibility.
    New code should use ClaudeProvider class.
    """
    provider = ClaudeProvider(model=model)
    request = ChatRequest(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=system,
        max_tokens=max_tokens
    )
    response = await provider.chat(request)
    tokens_used = response.usage.get("input_tokens", 0) + response.usage.get("output_tokens", 0)
    return response.content, tokens_used
