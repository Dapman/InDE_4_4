"""
Channel Manager - WebSocket Channel Subscriptions

Manages channel definitions and subscription policies for real-time
event delivery. Channels provide logical grouping of events.

Available Channels:
- federation: Federation status, connection events
- trust: Trust relationship events
- benchmark: Benchmark updates, ranking changes
- pattern: Pattern discovery, validation, federation
- reputation: Reputation score changes
- discovery: Cross-org discovery results
- coaching: User-specific coaching events (requires user context)

Channel Policies:
- Some channels require specific permissions
- Some channels are user-specific (only receive own events)
- Rate limiting can be applied per channel

Usage:
    manager = ChannelManager()
    if manager.can_subscribe(user_context, "trust"):
        await ws_manager.subscribe(websocket, "trust")
"""

import logging
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("inde.ikf.realtime.channels")


class ChannelType(str, Enum):
    """Types of channels."""
    PUBLIC = "public"           # Anyone can subscribe
    AUTHENTICATED = "authenticated"  # Requires authentication
    PRIVILEGED = "privileged"   # Requires specific role
    USER_SPECIFIC = "user_specific"  # Only receives own events


@dataclass
class ChannelDefinition:
    """Definition of a channel."""
    name: str
    channel_type: ChannelType
    description: str
    required_roles: Set[str] = field(default_factory=set)
    rate_limit_per_minute: int = 60


# Channel definitions
CHANNEL_DEFINITIONS = {
    "federation": ChannelDefinition(
        name="federation",
        channel_type=ChannelType.AUTHENTICATED,
        description="Federation status and connection events",
        rate_limit_per_minute=30
    ),

    "trust": ChannelDefinition(
        name="trust",
        channel_type=ChannelType.PRIVILEGED,
        description="Trust relationship lifecycle events",
        required_roles={"federation_admin", "org_admin"},
        rate_limit_per_minute=20
    ),

    "benchmark": ChannelDefinition(
        name="benchmark",
        channel_type=ChannelType.AUTHENTICATED,
        description="Benchmark updates and ranking changes",
        rate_limit_per_minute=10
    ),

    "pattern": ChannelDefinition(
        name="pattern",
        channel_type=ChannelType.AUTHENTICATED,
        description="Pattern discovery, validation, and federation events",
        rate_limit_per_minute=30
    ),

    "reputation": ChannelDefinition(
        name="reputation",
        channel_type=ChannelType.PRIVILEGED,
        description="Reputation score updates",
        required_roles={"federation_admin", "org_admin"},
        rate_limit_per_minute=10
    ),

    "discovery": ChannelDefinition(
        name="discovery",
        channel_type=ChannelType.USER_SPECIFIC,
        description="Cross-org discovery results (user-specific)",
        rate_limit_per_minute=20
    ),

    "coaching": ChannelDefinition(
        name="coaching",
        channel_type=ChannelType.USER_SPECIFIC,
        description="Coaching insights and recommendations (user-specific)",
        rate_limit_per_minute=60
    )
}


class ChannelManager:
    """
    Manages channel definitions and subscription authorization.

    Provides channel metadata, subscription checks, and policy enforcement.
    """

    def __init__(self):
        """Initialize the Channel Manager."""
        self._channels = CHANNEL_DEFINITIONS.copy()
        # Subscription counts per channel
        self._subscription_counts: Dict[str, int] = {
            name: 0 for name in self._channels
        }

    def get_channel(self, name: str) -> Optional[ChannelDefinition]:
        """
        Get channel definition by name.

        Args:
            name: Channel name

        Returns:
            ChannelDefinition or None if not found
        """
        return self._channels.get(name)

    def list_channels(self) -> List[dict]:
        """
        List all available channels.

        Returns:
            List of channel info dicts
        """
        return [
            {
                "name": ch.name,
                "type": ch.channel_type.value,
                "description": ch.description,
                "requires_roles": list(ch.required_roles) if ch.required_roles else None
            }
            for ch in self._channels.values()
        ]

    def can_subscribe(self, user_context: dict, channel_name: str) -> dict:
        """
        Check if a user can subscribe to a channel.

        Args:
            user_context: User context with roles, permissions
            channel_name: Channel to check

        Returns:
            dict with 'allowed' bool and 'reason' if denied
        """
        channel = self._channels.get(channel_name)
        if not channel:
            return {"allowed": False, "reason": "Channel not found"}

        # Public channels - always allowed
        if channel.channel_type == ChannelType.PUBLIC:
            return {"allowed": True}

        # Check authentication for non-public channels
        if not user_context.get("authenticated"):
            return {"allowed": False, "reason": "Authentication required"}

        # Authenticated channels - just need to be logged in
        if channel.channel_type == ChannelType.AUTHENTICATED:
            return {"allowed": True}

        # Privileged channels - need specific roles
        if channel.channel_type == ChannelType.PRIVILEGED:
            user_roles = set(user_context.get("roles", []))
            if not channel.required_roles.intersection(user_roles):
                return {
                    "allowed": False,
                    "reason": f"Required roles: {', '.join(channel.required_roles)}"
                }
            return {"allowed": True}

        # User-specific channels - always allowed for authenticated users
        # (they'll only receive their own events)
        if channel.channel_type == ChannelType.USER_SPECIFIC:
            return {"allowed": True}

        return {"allowed": False, "reason": "Unknown channel type"}

    def get_user_channels(self, user_context: dict) -> List[str]:
        """
        Get list of channels a user can subscribe to.

        Args:
            user_context: User context with roles, permissions

        Returns:
            List of channel names
        """
        allowed = []
        for name in self._channels:
            if self.can_subscribe(user_context, name).get("allowed"):
                allowed.append(name)
        return allowed

    def register_subscription(self, channel_name: str):
        """Record a new subscription to a channel."""
        if channel_name in self._subscription_counts:
            self._subscription_counts[channel_name] += 1

    def unregister_subscription(self, channel_name: str):
        """Record removal of a subscription."""
        if channel_name in self._subscription_counts:
            self._subscription_counts[channel_name] = max(
                0, self._subscription_counts[channel_name] - 1
            )

    def get_subscription_counts(self) -> Dict[str, int]:
        """Get current subscription counts per channel."""
        return self._subscription_counts.copy()

    def get_stats(self) -> dict:
        """Get channel manager statistics."""
        return {
            "total_channels": len(self._channels),
            "subscription_counts": self._subscription_counts,
            "total_subscriptions": sum(self._subscription_counts.values())
        }
