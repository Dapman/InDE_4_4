"""
InDE v3.9 - Provider Registry
Configuration-driven provider chain with automatic failover.

The registry maintains an ordered list of LLM providers and handles:
- Provider priority ordering
- Health monitoring
- Automatic failover when primary is unavailable
- Failover event logging
- Redis Streams event emission for observability
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import redis.asyncio as redis

from providers.base_provider import BaseProvider, ProviderStatus, QualityTier

logger = logging.getLogger("llm-gateway.registry")

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://inde-events:6379")
REDIS_STREAM_PREFIX = os.getenv("REDIS_STREAM_PREFIX", "inde:events:")
FAILOVER_STREAM = f"{REDIS_STREAM_PREFIX}llm-failover"


class ProviderRegistry:
    """
    Configuration-driven provider chain.

    Maintains ordered list of providers with health status and automatic failover.
    Providers are tried in priority order until one is available.
    Emits failover events to Redis Streams for observability.
    """

    def __init__(self):
        self._providers: List[BaseProvider] = []
        self._failover_log: List[dict] = []
        self._max_failover_log = 100  # Keep last N failover events
        self._redis_client: Optional[redis.Redis] = None
        self._redis_connected = False

    def register(self, provider: BaseProvider):
        """
        Add a provider to the chain in priority order.

        First registered provider is highest priority (primary).
        """
        self._providers.append(provider)
        logger.info(f"Registered LLM provider: {provider.name} (priority {len(self._providers)})")

    def get_providers(self) -> List[BaseProvider]:
        """Return all registered providers."""
        return self._providers.copy()

    async def get_primary(self) -> Optional[BaseProvider]:
        """
        Return the highest-priority available provider.

        Returns:
            First available provider, or None if all unavailable
        """
        for provider in self._providers:
            if await provider.is_available():
                return provider
        return None

    async def get_provider_with_failover(self) -> Tuple[BaseProvider, bool]:
        """
        Get available provider, recording failover if needed.

        Returns:
            Tuple of (provider, did_failover)
            - provider: First available provider in chain
            - did_failover: True if returned provider is not the primary

        Raises:
            RuntimeError: If no providers are available
        """
        if not self._providers:
            raise RuntimeError("No LLM providers registered")

        for i, provider in enumerate(self._providers):
            try:
                if await provider.is_available():
                    did_failover = i > 0

                    if did_failover:
                        primary_name = self._providers[0].name
                        await self._record_failover(
                            from_provider=primary_name,
                            to_provider=provider.name,
                            reason="primary_unavailable"
                        )

                    return provider, did_failover

            except Exception as e:
                logger.warning(f"Provider {provider.name} check failed: {e}")
                continue

        # All providers failed
        raise RuntimeError("No LLM providers available")

    def _get_provider_by_name(self, name: str) -> Optional[BaseProvider]:
        """
        Get a specific provider by name.

        Args:
            name: Provider name (e.g., 'anthropic', 'ollama')

        Returns:
            The provider if found, None otherwise
        """
        name_lower = name.lower()
        for provider in self._providers:
            if provider.name.lower() == name_lower:
                return provider
        return None

    async def get_provider_by_preference(
        self, preference: str
    ) -> Tuple[BaseProvider, bool]:
        """
        Get provider based on user preference with automatic fallback.

        This allows users to express a preference for cloud (premium quality)
        or local (cost-free) providers. If the preferred provider is unavailable,
        the system falls back to the normal failover chain.

        Args:
            preference: User preference - 'auto', 'cloud', or 'local'

        Returns:
            Tuple of (provider, did_fallback)
            - provider: Selected provider based on preference
            - did_fallback: True if preferred provider was unavailable

        Raises:
            RuntimeError: If no providers are available
        """
        if not self._providers:
            raise RuntimeError("No LLM providers registered")

        if preference == "cloud":
            # User prefers cloud/premium provider (Claude)
            claude = self._get_provider_by_name("anthropic")
            if claude:
                try:
                    if await claude.is_available():
                        return claude, False
                except Exception as e:
                    logger.warning(f"Cloud provider check failed: {e}")

            # Claude unavailable, fall back to chain
            logger.info("Cloud provider unavailable, falling back to chain")
            provider, _ = await self.get_provider_with_failover()
            return provider, True

        elif preference == "local":
            # User prefers local/cost-free provider (Ollama)
            ollama = self._get_provider_by_name("ollama")
            if ollama:
                try:
                    if await ollama.is_available():
                        return ollama, False
                except Exception as e:
                    logger.warning(f"Local provider check failed: {e}")

            # Ollama unavailable, fall back to chain
            logger.info("Local provider unavailable, falling back to chain")
            provider, _ = await self.get_provider_with_failover()
            return provider, True

        # Default: 'auto' - use normal failover chain
        return await self.get_provider_with_failover()

    async def get_all_status(self) -> List[ProviderStatus]:
        """Return status of all registered providers."""
        statuses = []
        for provider in self._providers:
            try:
                status = await provider.get_status()
                statuses.append(status)
            except Exception as e:
                # Return error status if status check fails
                statuses.append(ProviderStatus(
                    name=provider.name,
                    available=False,
                    quality_tier=QualityTier.BASIC,
                    error=str(e)
                ))
        return statuses

    def get_failover_history(self, limit: int = 50) -> List[dict]:
        """Return recent failover events."""
        return self._failover_log[-limit:]

    async def _record_failover(self, from_provider: str, to_provider: str, reason: str):
        """Record a failover event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_provider": from_provider,
            "to_provider": to_provider,
            "reason": reason
        }

        self._failover_log.append(event)

        # Trim log if needed
        if len(self._failover_log) > self._max_failover_log:
            self._failover_log = self._failover_log[-self._max_failover_log:]

        logger.warning(
            f"LLM provider failover: {from_provider} → {to_provider} ({reason})"
        )

        # Emit to Redis if available (Phase 6 will implement this)
        await self._emit_failover_event(event)

    async def _ensure_redis_connected(self):
        """Ensure Redis client is connected."""
        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(
                    REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._redis_client.ping()
                self._redis_connected = True
                logger.info(f"Connected to Redis at {REDIS_URL}")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._redis_connected = False

    async def _emit_failover_event(self, event: dict):
        """
        Emit failover event to Redis Streams.

        Event is published to the inde:events:llm-failover stream
        for consumption by the admin dashboard and monitoring systems.
        """
        try:
            await self._ensure_redis_connected()

            if not self._redis_connected or self._redis_client is None:
                logger.debug("Redis not available, skipping event emission")
                return

            # Prepare event payload
            payload = {
                "event_type": "llm_provider_failover",
                "timestamp": event["timestamp"],
                "from_provider": event["from_provider"],
                "to_provider": event["to_provider"],
                "reason": event["reason"],
                "severity": "warning"
            }

            # Emit to Redis Stream
            await self._redis_client.xadd(
                FAILOVER_STREAM,
                payload,
                maxlen=1000  # Keep last 1000 events
            )

            logger.info(f"Emitted failover event to Redis: {FAILOVER_STREAM}")

        except Exception as e:
            logger.warning(f"Failed to emit failover event to Redis: {e}")
            # Don't fail the request if Redis emission fails

    async def health_check(self) -> dict:
        """
        Comprehensive health check of the provider registry.

        Returns dict with overall status and per-provider details.
        """
        statuses = await self.get_all_status()
        primary = await self.get_primary()

        available_count = sum(1 for s in statuses if s.available)
        total_count = len(statuses)

        return {
            "status": "healthy" if primary else "degraded",
            "active_provider": primary.name if primary else None,
            "active_quality_tier": (await primary.get_status()).quality_tier if primary else None,
            "providers_available": available_count,
            "providers_total": total_count,
            "providers": [s.dict() for s in statuses],
            "recent_failovers": self.get_failover_history(limit=10)
        }


# Global registry instance
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Get or create the global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def initialize_providers():
    """
    Initialize providers from environment configuration.

    Reads LLM_PROVIDER or LLM_PROVIDER_CHAIN to determine which
    providers to register and in what order.

    Configuration:
        LLM_PROVIDER=anthropic           # Single provider (default)
        LLM_PROVIDER=ollama              # Ollama only (air-gapped)
        LLM_PROVIDER_CHAIN=anthropic,ollama  # Failover chain
    """
    from providers.claude_provider import ClaudeProvider

    registry = get_registry()

    # Clear existing providers (for re-initialization)
    registry._providers = []

    # Determine provider chain
    provider_config = os.getenv("LLM_PROVIDER", "anthropic")
    chain_config = os.getenv("LLM_PROVIDER_CHAIN", provider_config)
    chain = [p.strip() for p in chain_config.split(",") if p.strip()]

    logger.info(f"Initializing LLM provider chain: {chain}")

    # Provider factory
    provider_factories = {
        "anthropic": lambda: ClaudeProvider(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model=os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")
        ),
        # Ollama provider will be added in Phase 3
    }

    # Try to import Ollama provider if available
    try:
        from providers.ollama_provider import OllamaProvider
        provider_factories["ollama"] = lambda: OllamaProvider(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3")
        )
    except ImportError:
        logger.debug("Ollama provider not yet available")

    # Register providers in chain order
    for name in chain:
        if name in provider_factories:
            try:
                provider = provider_factories[name]()
                registry.register(provider)
            except Exception as e:
                logger.error(f"Failed to create provider {name}: {e}")
        else:
            logger.warning(f"Unknown LLM provider: {name} (skipped)")

    if not registry._providers:
        logger.error("No LLM providers were registered!")
    else:
        logger.info(f"Registered {len(registry._providers)} LLM provider(s)")

    return registry
