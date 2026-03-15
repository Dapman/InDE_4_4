"""
InDE v3.9 - Ollama Provider
Local LLM support via Ollama REST API for air-gapped deployments.

Ollama API reference:
- POST /api/chat       — Chat completion (streaming by default)
- POST /api/generate   — Text generation
- GET  /api/tags       — List available models
- POST /api/show       — Model metadata (parameter count, context length)
- GET  /api/ps         — Running models

Ollama listens on http://localhost:11434 by default.
"""

import os
import json
import logging
from typing import AsyncGenerator, Optional

import httpx

from .base_provider import (
    BaseProvider, QualityTier, ProviderStatus,
    ChatRequest, ChatResponse
)

logger = logging.getLogger("llm-gateway.ollama")


class OllamaProvider(BaseProvider):
    """
    Ollama REST API provider for local LLM inference.

    Supports any model installed via `ollama pull <model>`.
    Quality tier is automatically determined based on model parameter count:
    - 65B+ parameters: STANDARD tier
    - <65B parameters: BASIC tier

    Ollama models include: llama3, llama3:70b, mistral, mixtral, phi3, etc.
    """

    def __init__(
        self,
        base_url: str = "http://host.docker.internal:11434",
        model: str = "llama3",
        timeout: float = 120.0
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama server URL (default: Docker-accessible localhost)
            model: Model name (must be pulled via `ollama pull <model>`)
            timeout: Request timeout in seconds
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._model_metadata: Optional[dict] = None
        self._quality_tier: QualityTier = QualityTier.BASIC
        self._context_window: int = 8192  # Conservative default
        self._parameter_size: str = "unknown"

    @property
    def name(self) -> str:
        return "ollama"

    async def is_available(self) -> bool:
        """Check if Ollama is reachable and the configured model is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check if Ollama is running
                resp = await client.get(f"{self._base_url}/api/tags")
                if resp.status_code != 200:
                    return False

                # Check if configured model exists
                data = resp.json()
                models = data.get("models", [])

                # Model names can be "llama3" or "llama3:latest" or "llama3:70b"
                model_base = self._model.split(":")[0]
                for m in models:
                    m_name = m.get("name", "").split(":")[0]
                    if m_name == model_base:
                        return True

                    # Also check the full name
                    if m.get("name", "") == self._model:
                        return True

                logger.warning(f"Model {self._model} not found in Ollama. Available: {[m.get('name') for m in models]}")
                return False

        except httpx.ConnectError:
            logger.debug(f"Ollama not reachable at {self._base_url}")
            return False
        except Exception as e:
            logger.warning(f"Ollama availability check failed: {e}")
            return False

    async def _load_model_metadata(self):
        """Fetch model metadata from Ollama to determine quality tier."""
        if self._model_metadata:
            return  # Already loaded

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self._base_url}/api/show",
                    json={"model": self._model}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    self._model_metadata = data

                    # Extract parameter size (e.g., "8B", "70.6B")
                    details = data.get("details", {})
                    self._parameter_size = details.get("parameter_size", "unknown")

                    # Determine quality tier from parameter count
                    param_billions = self._parse_param_size(self._parameter_size)

                    if param_billions >= 65:
                        self._quality_tier = QualityTier.STANDARD
                        logger.info(f"Ollama model {self._model} classified as STANDARD tier ({self._parameter_size})")
                    else:
                        self._quality_tier = QualityTier.BASIC
                        logger.info(f"Ollama model {self._model} classified as BASIC tier ({self._parameter_size})")

                    # Extract context window from model info
                    model_info = data.get("model_info", {})
                    for key, value in model_info.items():
                        if "context_length" in key.lower() or "context_window" in key.lower():
                            try:
                                self._context_window = int(value)
                            except (ValueError, TypeError):
                                pass
                            break

                    logger.info(
                        f"Ollama model metadata: {self._model}, "
                        f"params={self._parameter_size}, "
                        f"tier={self._quality_tier.value}, "
                        f"context={self._context_window}"
                    )
                else:
                    logger.warning(f"Failed to load Ollama model metadata: {resp.status_code}")

        except Exception as e:
            logger.warning(f"Failed to load Ollama model metadata: {e}")

    @staticmethod
    def _parse_param_size(param_str: str) -> float:
        """Parse '70.6B' or '8B' into a float of billions."""
        try:
            cleaned = param_str.upper().replace("B", "").strip()
            return float(cleaned)
        except (ValueError, AttributeError, TypeError):
            return 0.0

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Non-streaming chat completion via Ollama /api/chat endpoint.
        """
        await self._load_model_metadata()

        # Translate messages to Ollama format
        ollama_messages = self._translate_messages(request.messages, request.system_prompt)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": ollama_messages,
                        "stream": False,
                        "options": {
                            "temperature": request.temperature,
                            "num_predict": request.max_tokens,
                            "num_ctx": min(self._context_window, 32768),
                        }
                    }
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract response content
                content = data.get("message", {}).get("content", "")

                # Token usage (Ollama provides eval_count and prompt_eval_count)
                usage = {
                    "input_tokens": data.get("prompt_eval_count", 0),
                    "output_tokens": data.get("eval_count", 0)
                }

                logger.info(f"Ollama response: {usage['input_tokens']}+{usage['output_tokens']} tokens")

                return ChatResponse(
                    content=content,
                    usage=usage,
                    provider=self.name,
                    quality_tier=self._quality_tier,
                    model=self._model,
                    failover=False
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Streaming chat completion via Ollama /api/chat endpoint.

        Yields SSE-formatted chunks compatible with frontend expectations.
        """
        await self._load_model_metadata()

        ollama_messages = self._translate_messages(request.messages, request.system_prompt)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": ollama_messages,
                        "stream": True,
                        "options": {
                            "temperature": request.temperature,
                            "num_predict": request.max_tokens,
                            "num_ctx": min(self._context_window, 32768),
                        }
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")

                                if content:
                                    # Emit in SSE format matching Claude streaming convention
                                    chunk_data = {
                                        "type": "content_block_delta",
                                        "delta": {"text": content}
                                    }
                                    yield f"data: {json.dumps(chunk_data)}\n\n"

                                if chunk.get("done", False):
                                    # Signal completion
                                    yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"

                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    async def get_status(self) -> ProviderStatus:
        """Return Ollama provider status."""
        await self._load_model_metadata()
        available = await self.is_available()

        error = None
        if not available:
            error = f"Ollama not reachable at {self._base_url} or model '{self._model}' not found"

        return ProviderStatus(
            name=self.name,
            available=available,
            quality_tier=self._quality_tier,
            current_model=self._model,
            context_window=self._context_window,
            error=error,
            metadata={
                "base_url": self._base_url,
                "parameter_size": self._parameter_size,
                "quantization": self._model_metadata.get("details", {}).get("quantization_level", "unknown") if self._model_metadata else "unknown"
            }
        )

    def _translate_messages(self, messages: list, system_prompt: Optional[str] = None) -> list:
        """
        Translate from Anthropic/internal message format to Ollama chat format.

        Anthropic: [{"role": "user", "content": "..."}] + system_prompt as separate param
        Ollama:    [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

        Ollama uses the same message format as OpenAI — system message is
        a regular message with role="system" at the start.
        """
        ollama_msgs = []

        # Add system prompt as first message
        if system_prompt:
            ollama_msgs.append({"role": "system", "content": system_prompt})

        # Translate remaining messages
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Ollama supports: system, user, assistant
            if role in ["system", "user", "assistant"]:
                ollama_msgs.append({"role": role, "content": content})
            else:
                # Default unknown roles to user
                ollama_msgs.append({"role": "user", "content": content})

        return ollama_msgs
