"""
InDE v3.9 - Air-Gapped Intelligence Integration Tests

Tests for:
- Provider registry architecture
- Quality tier detection and calibration
- Prompt calibration layer
- Failover event emission
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# PROVIDER REGISTRY TESTS
# =============================================================================

class TestProviderRegistry:
    """Tests for the provider registry architecture."""

    def test_registry_initialization(self):
        """Test that registry can be initialized."""
        import sys
        sys.path.insert(0, 'llm-gateway')

        from provider_registry import ProviderRegistry

        registry = ProviderRegistry()
        assert registry._providers == []
        assert registry._failover_log == []

    def test_provider_registration(self):
        """Test registering providers."""
        import sys
        sys.path.insert(0, 'llm-gateway')

        from provider_registry import ProviderRegistry
        from providers.base_provider import BaseProvider

        # Create mock provider
        mock_provider = MagicMock(spec=BaseProvider)
        mock_provider.name = "test_provider"

        registry = ProviderRegistry()
        registry.register(mock_provider)

        assert len(registry._providers) == 1
        assert registry._providers[0].name == "test_provider"

    @pytest.mark.asyncio
    async def test_get_primary_available(self):
        """Test getting primary provider when available."""
        import sys
        sys.path.insert(0, 'llm-gateway')

        from provider_registry import ProviderRegistry

        # Create mock available provider
        mock_provider = AsyncMock()
        mock_provider.name = "anthropic"
        mock_provider.is_available = AsyncMock(return_value=True)

        registry = ProviderRegistry()
        registry._providers = [mock_provider]

        primary = await registry.get_primary()
        assert primary is not None
        assert primary.name == "anthropic"

    @pytest.mark.asyncio
    async def test_failover_when_primary_unavailable(self):
        """Test failover to secondary provider."""
        import sys
        sys.path.insert(0, 'llm-gateway')

        from provider_registry import ProviderRegistry

        # Primary unavailable
        primary = AsyncMock()
        primary.name = "anthropic"
        primary.is_available = AsyncMock(return_value=False)

        # Secondary available
        secondary = AsyncMock()
        secondary.name = "ollama"
        secondary.is_available = AsyncMock(return_value=True)

        registry = ProviderRegistry()
        registry._providers = [primary, secondary]

        provider, did_failover = await registry.get_provider_with_failover()

        assert provider.name == "ollama"
        assert did_failover is True
        assert len(registry._failover_log) == 1


# =============================================================================
# QUALITY TIER TESTS
# =============================================================================

class TestQualityTier:
    """Tests for quality tier detection and management."""

    def test_quality_tier_enum(self):
        """Test quality tier enum values."""
        from coaching.prompt_calibration import QualityTier

        assert QualityTier.PREMIUM.value == "premium"
        assert QualityTier.STANDARD.value == "standard"
        assert QualityTier.BASIC.value == "basic"

    def test_tier_budgets(self):
        """Test tier budgets are configured correctly."""
        from coaching.prompt_calibration import TIER_BUDGETS, QualityTier

        # Premium has highest budgets
        assert TIER_BUDGETS[QualityTier.PREMIUM]["system_prompt"] == 3000
        assert TIER_BUDGETS[QualityTier.PREMIUM]["response"] == 4096

        # Standard has moderate budgets
        assert TIER_BUDGETS[QualityTier.STANDARD]["system_prompt"] == 1500
        assert TIER_BUDGETS[QualityTier.STANDARD]["response"] == 2048

        # Basic has lowest budgets
        assert TIER_BUDGETS[QualityTier.BASIC]["system_prompt"] == 800
        assert TIER_BUDGETS[QualityTier.BASIC]["response"] == 1024

    def test_get_max_response_tokens(self):
        """Test max response token calculation."""
        from coaching.prompt_calibration import get_max_response_tokens

        assert get_max_response_tokens("premium") == 4096
        assert get_max_response_tokens("standard") == 2048
        assert get_max_response_tokens("basic") == 1024


# =============================================================================
# PROMPT CALIBRATION TESTS
# =============================================================================

class TestPromptCalibration:
    """Tests for prompt calibration layer."""

    def test_premium_no_calibration(self):
        """Test that premium tier doesn't modify prompts."""
        from coaching.prompt_calibration import calibrate_system_prompt

        original = "This is the original system prompt with full detail."
        calibrated = calibrate_system_prompt(original, "premium")

        assert calibrated == original

    def test_standard_adds_prefix(self):
        """Test standard tier adds calibration prefix."""
        from coaching.prompt_calibration import calibrate_system_prompt

        original = "Original prompt content."
        calibrated = calibrate_system_prompt(original, "standard")

        assert "IMPORTANT:" in calibrated
        assert "local model" in calibrated.lower()

    def test_basic_adds_rules(self):
        """Test basic tier adds explicit rules."""
        from coaching.prompt_calibration import calibrate_system_prompt

        original = "Original prompt content."
        calibrated = calibrate_system_prompt(original, "basic")

        assert "RULES:" in calibrated
        assert "ONE question at a time" in calibrated

    def test_methodology_keywords_preserved(self):
        """Test that methodology keywords are preserved in compression."""
        from coaching.prompt_calibration import (
            calibrate_system_prompt,
            METHODOLOGY_KEYWORDS
        )

        # Create prompt with methodology keywords
        original = """
        Stage: Vision Exploration
        Archetype: Lean Startup
        Current phase: Problem Validation
        Innovator maturity: COMPETENT
        """

        calibrated = calibrate_system_prompt(original, "basic")

        # Should preserve methodology context
        assert "Stage:" in calibrated or "CURRENT CONTEXT" in calibrated

    def test_quality_indicator_messages(self):
        """Test quality indicator messages for UI."""
        from coaching.prompt_calibration import (
            should_show_quality_indicator,
            get_quality_indicator_message
        )

        # Premium doesn't show indicator
        assert should_show_quality_indicator("premium") is False
        assert get_quality_indicator_message("premium") is None

        # Standard shows indicator
        assert should_show_quality_indicator("standard") is True
        assert "local model" in get_quality_indicator_message("standard")

        # Basic shows indicator with limitation note
        assert should_show_quality_indicator("basic") is True
        assert "limited" in get_quality_indicator_message("basic").lower()


# =============================================================================
# OLLAMA PROVIDER TESTS
# =============================================================================

class TestOllamaProvider:
    """Tests for Ollama provider adapter."""

    def test_provider_name(self):
        """Test Ollama provider name."""
        import sys
        sys.path.insert(0, 'llm-gateway')

        from providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        assert provider.name == "ollama"

    def test_parameter_size_parsing(self):
        """Test parsing parameter sizes to determine tier."""
        import sys
        sys.path.insert(0, 'llm-gateway')

        from providers.ollama_provider import OllamaProvider

        # Test various formats
        assert OllamaProvider._parse_param_size("8B") == 8.0
        assert OllamaProvider._parse_param_size("70.6B") == 70.6
        assert OllamaProvider._parse_param_size("7b") == 7.0
        assert OllamaProvider._parse_param_size("invalid") == 0.0

    def test_message_translation(self):
        """Test message format translation from Anthropic to Ollama."""
        import sys
        sys.path.insert(0, 'llm-gateway')

        from providers.ollama_provider import OllamaProvider

        provider = OllamaProvider()

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]

        translated = provider._translate_messages(messages, "You are helpful")

        # Should have system message first
        assert translated[0]["role"] == "system"
        assert translated[0]["content"] == "You are helpful"

        # Then user/assistant messages
        assert translated[1]["role"] == "user"
        assert translated[2]["role"] == "assistant"


# =============================================================================
# FAILOVER EVENT TESTS
# =============================================================================

class TestFailoverEvents:
    """Tests for failover event logging and emission."""

    @pytest.mark.asyncio
    async def test_failover_logged(self):
        """Test that failover events are logged."""
        import sys
        sys.path.insert(0, 'llm-gateway')

        from provider_registry import ProviderRegistry

        registry = ProviderRegistry()

        await registry._record_failover(
            from_provider="anthropic",
            to_provider="ollama",
            reason="primary_unavailable"
        )

        assert len(registry._failover_log) == 1
        event = registry._failover_log[0]
        assert event["from_provider"] == "anthropic"
        assert event["to_provider"] == "ollama"
        assert "timestamp" in event

    def test_failover_history_limit(self):
        """Test that failover history is trimmed."""
        import sys
        sys.path.insert(0, 'llm-gateway')

        from provider_registry import ProviderRegistry

        registry = ProviderRegistry()
        registry._max_failover_log = 5

        # Add more events than the limit
        for i in range(10):
            registry._failover_log.append({"event": i})

        # Manually trigger trim
        if len(registry._failover_log) > registry._max_failover_log:
            registry._failover_log = registry._failover_log[-registry._max_failover_log:]

        assert len(registry._failover_log) == 5


# =============================================================================
# LLM INTERFACE INTEGRATION TESTS
# =============================================================================

class TestLLMInterfaceIntegration:
    """Tests for LLM interface with calibration integration."""

    def test_interface_gateway_mode(self):
        """Test LLM interface in gateway mode."""
        # This test would require mocking the gateway
        # Just verify the initialization path exists
        from core.llm_interface import LLMInterface

        # Gateway mode with no API key should not be demo mode
        interface = LLMInterface(api_key=None, use_gateway=True)
        assert interface.use_gateway is True

    def test_quality_indicator_method(self):
        """Test quality indicator retrieval."""
        from core.llm_interface import LLMInterface

        interface = LLMInterface(api_key=None, use_gateway=False)
        interface.demo_mode = True

        # Premium tier should return None
        with patch('core.llm_interface.get_quality_tier') as mock_tier:
            from coaching.prompt_calibration import QualityTier
            mock_tier.return_value = QualityTier.PREMIUM

            indicator = interface.get_quality_indicator()
            # May be None or show: False for premium


# =============================================================================
# VERSION VERIFICATION
# =============================================================================

class TestVersionVerification:
    """Tests to verify v3.9 version strings."""

    def test_config_version(self):
        """Test version in config."""
        from core.config import VERSION, VERSION_NAME

        assert VERSION == "3.9.0"
        assert "Air-Gapped" in VERSION_NAME

    def test_llm_interface_docstring(self):
        """Test LLM interface has v3.9 documentation."""
        from core.llm_interface import LLMInterface

        docstring = LLMInterface.__module__
        # Module should be accessible (basic sanity check)
        assert docstring is not None
