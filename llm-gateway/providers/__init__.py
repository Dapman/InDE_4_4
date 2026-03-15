"""
InDE v3.9 - LLM Providers
Provider adapters for different LLM backends.

Available Providers:
- anthropic (ClaudeProvider): Anthropic Claude API - Premium tier
- ollama (OllamaProvider): Local Ollama models - Standard/Basic tier
"""

from .base_provider import BaseProvider, QualityTier, ProviderStatus, ChatRequest, ChatResponse
from .claude_provider import ClaudeProvider, generate_claude_response

# Ollama provider is optional - only import if available
try:
    from .ollama_provider import OllamaProvider
    __all__ = ["BaseProvider", "QualityTier", "ProviderStatus", "ChatRequest", "ChatResponse",
               "ClaudeProvider", "OllamaProvider", "generate_claude_response"]
except ImportError:
    __all__ = ["BaseProvider", "QualityTier", "ProviderStatus", "ChatRequest", "ChatResponse",
               "ClaudeProvider", "generate_claude_response"]
