"""
WebSocket API Endpoint

Provides WebSocket endpoint for real-time event delivery.

Endpoint: /api/v1/ws
Query params:
- token: Authentication token (required)
- session_id: Optional session identifier

Client Messages:
- {type: "heartbeat"} - Keep connection alive
- {type: "subscribe", channel: "..."} - Subscribe to channel
- {type: "unsubscribe", channel: "..."} - Unsubscribe from channel

Server Messages:
- {type: "connection.established"} - Connection confirmed
- {type: "heartbeat"} - Server heartbeat
- {type: "channel.subscribed"} - Subscription confirmed
- {type: "event.*"} - Bridged event from federation
- {type: "server.shutdown"} - Server shutting down
"""

import uuid
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

logger = logging.getLogger("inde.ikf.api.websocket")

router = APIRouter(tags=["websocket"])


async def authenticate_websocket(token: str) -> Optional[dict]:
    """
    Authenticate WebSocket connection token.

    In production, this would validate JWT or session token.
    For now, returns a mock user context.

    Args:
        token: Authentication token

    Returns:
        User context dict or None if invalid
    """
    if not token:
        return None

    # Mock authentication - in production, validate token
    # and extract user info from JWT claims or session
    return {
        "user_id": f"user_{token[:8]}",
        "authenticated": True,
        "roles": ["user"],  # Would be extracted from token
        "permissions": []
    }


@router.websocket("/api/v1/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
    session_id: str = Query(None)
):
    """
    WebSocket endpoint for real-time event delivery.

    Requires authentication token in query params.
    Supports channel subscriptions for targeted event delivery.
    """
    # Get managers from app state
    ws_manager = getattr(websocket.app.state, "websocket_manager", None)
    channel_manager = getattr(websocket.app.state, "channel_manager", None)

    if not ws_manager:
        await websocket.close(code=1011, reason="WebSocket service unavailable")
        return

    # Authenticate
    user_context = await authenticate_websocket(token)
    if not user_context:
        await websocket.close(code=4001, reason="Authentication required")
        return

    user_id = user_context["user_id"]
    session_id = session_id or str(uuid.uuid4())

    # Connect
    connected = await ws_manager.connect(websocket, user_id, session_id)
    if not connected:
        return

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle subscription requests
            if data.get("type") == "subscribe":
                channel = data.get("channel")
                if channel and channel_manager:
                    auth_check = channel_manager.can_subscribe(user_context, channel)
                    if auth_check.get("allowed"):
                        await ws_manager.subscribe(websocket, channel)
                        channel_manager.register_subscription(channel)
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Cannot subscribe to {channel}: {auth_check.get('reason')}"
                        })

            elif data.get("type") == "unsubscribe":
                channel = data.get("channel")
                if channel:
                    await ws_manager.unsubscribe(websocket, channel)
                    if channel_manager:
                        channel_manager.unregister_subscription(channel)

            else:
                # Handle other messages (heartbeat, etc)
                await ws_manager.handle_client_message(websocket, data)

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


@router.get("/api/v1/ws/channels")
async def list_channels(websocket: WebSocket = None):
    """
    List available WebSocket channels.

    Returns channel names, descriptions, and requirements.
    """
    from fastapi import Request

    # This would need the request context - simplified for now
    from ..realtime.channels import CHANNEL_DEFINITIONS

    return {
        "channels": [
            {
                "name": ch.name,
                "type": ch.channel_type.value,
                "description": ch.description,
                "requires_roles": list(ch.required_roles) if ch.required_roles else None
            }
            for ch in CHANNEL_DEFINITIONS.values()
        ]
    }


@router.get("/api/v1/ws/stats")
async def get_websocket_stats(websocket: WebSocket = None):
    """
    Get WebSocket connection statistics.

    Requires admin role in production.
    """
    # Would get from app state in production
    return {
        "message": "Stats endpoint - requires app context",
        "available": False
    }
