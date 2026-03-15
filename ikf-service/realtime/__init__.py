"""
Real-time Event Delivery Module

WebSocket-based real-time event delivery for federation events.
Supports channel-based subscriptions for targeted event delivery.

Components:
- WebSocketManager: Connection lifecycle management
- EventBridge: Bridge federation events to WebSocket clients
- ChannelManager: Channel subscription management
"""

from .websocket_manager import WebSocketManager
from .event_bridge import EventBridge
from .channels import ChannelManager

__all__ = ["WebSocketManager", "EventBridge", "ChannelManager"]
