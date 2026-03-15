"""
InDE v3.9 - LLM Gateway Provider Tests

Tests for:
- Provider registry
- Claude provider
- Ollama provider
- Failover logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# QUALITY TIER TESTS
# =============================================================================

class TestQualityTier:
    """Tests for quality tier enum."""

    def test_tier_values(self):
        """Test quality tier enum values."""
        from providers.base_provider import QualityTier

        assert QualityTier.PREMIUM.value == "premium"
        assert QualityTier.STANDARD.value == "standard"
        assert QualityTier.BASIC.value == "basic"

    def test_tier_string_conversion(self):
        """Test converting string to QualityTier."""
        from providers.base_provider import QualityTier

        assert QualityTier("premium") == QualityTier.PREMIUM
        assert QualityTier("standard") == QualityTier.STANDARD
        assert QualityTier("basic") == QualityTier.BASIC


# =============================================================================
# PROVIDER STATUS TESTS
# =============================================================================

class TestProviderStatus:
    """Tests for ProviderStatus dataclass."""

    def test_status_creation(self):
        """Test creating provider status."""
        from providers.base_provider import ProviderStatus, QualityTier

        status = ProviderStatus(
            name="test",
            available=True,
            quality_tier=QualityTier.PREMIUM,
            current_model="test-model"
        )

        assert status.name == "test"
        assert status.available is True
        assert status.quality_tier == QualityTier.PREMIUM
        assert status.current_model == "test-model"

    def test_status_dict_conversion(self):
        """Test status dict() method."""
        from providers.base_provider import ProviderStatus, QualityTier

        status = ProviderStatus(
            name="anthropic",
            available=True,
            quality_tier=QualityTier.PREMIUM
        )

        d = status.dict()
        assert d["name"] == "anthropic"
        assert d["available"] is True
        assert d["quality_tier"] == "premium"


# =============================================================================
# CLAUDE PROVIDER TESTS
# =============================================================================

class TestClaudeProvider:
    """Tests for Claude provider adapter."""

    def test_provider_name(self):
        """Test provider name is anthropic."""
        from providers.claude_provider import ClaudeProvider

        provider = ClaudeProvider()
        assert provider.name == "anthropic"

    def test_quality_tier_is_premium(self):
        """Test Claude is always premium tier."""
        from providers.claude_provider import ClaudeProvider
        from providers.base_provider import QualityTier

        provider = ClaudeProvider()
        # Quality tier should always be premium for Claude
        assert provider._quality_tier == QualityTier.PREMIUM

    @pytest.mark.asyncio
    async def test_availability_without_key(self):
        """Test provider unavailable without API key."""
        from providers.claude_provider import ClaudeProvider

        provider = ClaudeProvider(api_key="")
        is_available = await provider.is_available()
        assert is_available is False

    @pytest.mark.asyncio
    async def test_status_without_key(self):
        """Test status shows unavailable without key."""
        from providers.claude_provider import ClaudeProvider

        provider = ClaudeProvider(api_key="")
        status = await provider.get_status()

        assert status.name == "anthropic"
        assert status.available is False
        assert "not configured" in (status.error or "").lower() or status.available is False


# =============================================================================
# OLLAMA PROVIDER TESTS
# =============================================================================

class TestOllamaProvider:
    """Tests for Ollama provider adapter."""

    def test_provider_name(self):
        """Test provider name is ollama."""
        from providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        assert provider.name == "ollama"

    def test_default_tier_is_basic(self):
        """Test default tier before metadata load."""
        from providers.ollama_provider import OllamaProvider
        from providers.base_provider import QualityTier

        provider = OllamaProvider()
        assert provider._quality_tier == QualityTier.BASIC

    def test_param_size_parsing(self):
        """Test parameter size parsing."""
        from providers.ollama_provider import OllamaProvider

        # Various formats
        assert OllamaProvider._parse_param_size("8B") == 8.0
        assert OllamaProvider._parse_param_size("70B") == 70.0
        assert OllamaProvider._parse_param_size("70.6B") == 70.6
        assert OllamaProvider._parse_param_size("7b") == 7.0
        assert OllamaProvider._parse_param_size("13B") == 13.0

        # Invalid formats
        assert OllamaProvider._parse_param_size("invalid") == 0.0
        assert OllamaProvider._parse_param_size("") == 0.0
        assert OllamaProvider._parse_param_size(None) == 0.0

    def test_message_translation_with_system(self):
        """Test message translation with system prompt."""
        from providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"}
        ]

        result = provider._translate_messages(messages, "You are helpful")

        assert len(result) == 3
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are helpful"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"

    def test_message_translation_without_system(self):
        """Test message translation without system prompt."""
        from providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()

        messages = [{"role": "user", "content": "Hi"}]
        result = provider._translate_messages(messages, None)

        assert len(result) == 1
        assert result[0]["role"] == "user"


# =============================================================================
# PROVIDER REGISTRY TESTS
# =============================================================================

class TestProviderRegistry:
    """Tests for provider registry."""

    def test_registry_empty_initially(self):
        """Test registry starts empty."""
        from provider_registry import ProviderRegistry

        registry = ProviderRegistry()
        assert len(registry._providers) == 0

    def test_register_provider(self):
        """Test registering a provider."""
        from provider_registry import ProviderRegistry

        registry = ProviderRegistry()

        mock_provider = MagicMock()
        mock_provider.name = "test"

        registry.register(mock_provider)

        assert len(registry._providers) == 1
        assert registry._providers[0].name == "test"

    def test_get_providers_returns_copy(self):
        """Test get_providers returns a copy."""
        from provider_registry import ProviderRegistry

        registry = ProviderRegistry()

        mock_provider = MagicMock()
        mock_provider.name = "test"
        registry.register(mock_provider)

        providers = registry.get_providers()
        providers.append(MagicMock())  # Modify the copy

        # Original should be unchanged
        assert len(registry._providers) == 1

    @pytest.mark.asyncio
    async def test_get_primary_returns_first_available(self):
        """Test get_primary returns first available provider."""
        from provider_registry import ProviderRegistry

        registry = ProviderRegistry()

        provider1 = AsyncMock()
        provider1.name = "first"
        provider1.is_available = AsyncMock(return_value=True)

        provider2 = AsyncMock()
        provider2.name = "second"
        provider2.is_available = AsyncMock(return_value=True)

        registry._providers = [provider1, provider2]

        primary = await registry.get_primary()
        assert primary.name == "first"

    @pytest.mark.asyncio
    async def test_failover_recorded(self):
        """Test failover is recorded when primary unavailable."""
        from provider_registry import ProviderRegistry

        registry = ProviderRegistry()

        provider1 = AsyncMock()
        provider1.name = "anthropic"
        provider1.is_available = AsyncMock(return_value=False)

        provider2 = AsyncMock()
        provider2.name = "ollama"
        provider2.is_available = AsyncMock(return_value=True)

        registry._providers = [provider1, provider2]

        provider, did_failover = await registry.get_provider_with_failover()

        assert provider.name == "ollama"
        assert did_failover is True
        assert len(registry._failover_log) == 1
        assert registry._failover_log[0]["from_provider"] == "anthropic"
        assert registry._failover_log[0]["to_provider"] == "ollama"

    @pytest.mark.asyncio
    async def test_all_unavailable_raises(self):
        """Test RuntimeError when all providers unavailable."""
        from provider_registry import ProviderRegistry

        registry = ProviderRegistry()

        provider = AsyncMock()
        provider.name = "test"
        provider.is_available = AsyncMock(return_value=False)

        registry._providers = [provider]

        with pytest.raises(RuntimeError, match="No LLM providers available"):
            await registry.get_provider_with_failover()


# =============================================================================
# CHAT REQUEST/RESPONSE TESTS
# =============================================================================

class TestChatMessages:
    """Tests for chat request and response structures."""

    def test_chat_request_creation(self):
        """Test ChatRequest dataclass."""
        from providers.base_provider import ChatRequest

        request = ChatRequest(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="Be helpful",
            max_tokens=1000,
            temperature=0.7
        )

        assert len(request.messages) == 1
        assert request.system_prompt == "Be helpful"
        assert request.max_tokens == 1000
        assert request.temperature == 0.7

    def test_chat_response_creation(self):
        """Test ChatResponse dataclass."""
        from providers.base_provider import ChatResponse, QualityTier

        response = ChatResponse(
            content="Hello there!",
            usage={"input_tokens": 10, "output_tokens": 5},
            provider="anthropic",
            quality_tier=QualityTier.PREMIUM,
            model="claude-sonnet-4"
        )

        assert response.content == "Hello there!"
        assert response.provider == "anthropic"
        assert response.quality_tier == QualityTier.PREMIUM
        assert response.failover is False


# =============================================================================
# INITIALIZE PROVIDERS TESTS
# =============================================================================

class TestInitializeProviders:
    """Tests for provider initialization from environment."""

    def test_default_anthropic_only(self):
        """Test default initialization is anthropic only."""
        from provider_registry import initialize_providers, get_registry

        # Clear any existing registry
        import provider_registry
        provider_registry._registry = None

        with patch.dict(os.environ, {
            "LLM_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": "test-key"
        }, clear=False):
            registry = initialize_providers()
            providers = registry.get_providers()

            assert len(providers) == 1
            assert providers[0].name == "anthropic"

    def test_ollama_only_chain(self):
        """Test ollama-only initialization."""
        from provider_registry import initialize_providers
        import provider_registry
        provider_registry._registry = None

        with patch.dict(os.environ, {
            "LLM_PROVIDER": "ollama",
            "LLM_PROVIDER_CHAIN": "ollama",
            "OLLAMA_MODEL": "llama3"
        }, clear=False):
            registry = initialize_providers()
            providers = registry.get_providers()

            assert len(providers) == 1
            assert providers[0].name == "ollama"

    def test_hybrid_chain(self):
        """Test hybrid provider chain."""
        from provider_registry import initialize_providers
        import provider_registry
        provider_registry._registry = None

        with patch.dict(os.environ, {
            "LLM_PROVIDER_CHAIN": "anthropic,ollama",
            "ANTHROPIC_API_KEY": "test-key",
            "OLLAMA_MODEL": "llama3"
        }, clear=False):
            registry = initialize_providers()
            providers = registry.get_providers()

            assert len(providers) == 2
            assert providers[0].name == "anthropic"
            assert providers[1].name == "ollama"
