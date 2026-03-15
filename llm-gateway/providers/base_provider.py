"""
InDE v3.9 - Base Provider Interface
Abstract base class for all LLM providers.

The gateway interacts with providers exclusively through this interface,
enabling provider-agnostic routing and automatic failover.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncGenerator, Optional, List
from pydantic import BaseModel


class QualityTier(str, Enum):
    """
    Quality tier classification for LLM providers.
    Used by ODICM for prompt calibration.
    """
    PREMIUM = "premium"     # Claude-class models (100B+ parameters, advanced reasoning)
    STANDARD = "standard"   # 70B+ local models (good reasoning, reliable instruction following)
    BASIC = "basic"         # 7B-13B local models (acceptable coaching, simpler reasoning)


class ProviderStatus(BaseModel):
    """Status information for a provider."""
    name: str
    available: bool
    quality_tier: QualityTier
    current_model: Optional[str] = None
    context_window: int = 200000  # tokens
    error: Optional[str] = None
    metadata: dict = {}

    class Config:
        use_enum_values = True


class ChatRequest(BaseModel):
    """Standardized chat request format."""
    messages: List[dict]
    system_prompt: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    stream: bool = False
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Standardized chat response format."""
    content: str
    usage: dict  # {"input_tokens": int, "output_tokens": int}
    provider: str
    quality_tier: QualityTier
    model: str
    failover: bool = False

    class Config:
        use_enum_values = True


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    Every provider must implement these methods. The gateway interacts
    with providers exclusively through this interface, enabling:
    - Provider-agnostic routing
    - Automatic failover
    - Quality tier awareness
    - Unified health monitoring
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g., 'anthropic', 'ollama')."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the provider is currently reachable and operational.

        Returns:
            True if provider can handle requests, False otherwise
        """
        pass

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Non-streaming chat completion.

        Args:
            request: Standardized chat request

        Returns:
            ChatResponse with content and usage info
        """
        pass

    @abstractmethod
    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Streaming chat completion via Server-Sent Events.

        Args:
            request: Standardized chat request

        Yields:
            SSE-formatted chunks
        """
        pass

    @abstractmethod
    async def get_status(self) -> ProviderStatus:
        """
        Return current provider status with quality tier and model info.

        Returns:
            ProviderStatus with availability, tier, and metadata
        """
        pass

    async def health_check(self) -> dict:
        """
        Perform a health check and return status.
        Default implementation uses is_available().
        """
        try:
            available = await self.is_available()
            status = await self.get_status()
            return {
                "provider": self.name,
                "healthy": available,
                "quality_tier": status.quality_tier,
                "model": status.current_model,
                "error": status.error
            }
        except Exception as e:
            return {
                "provider": self.name,
                "healthy": False,
                "error": str(e)
            }
