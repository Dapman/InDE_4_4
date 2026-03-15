"""
WebSocket Connection Manager

Manages WebSocket connections for real-time event delivery.
Supports multiple concurrent connections per user/session.

Features:
- Connection lifecycle management (connect, disconnect, heartbeat)
- Connection registry by user and session
- Graceful shutdown with connection draining
- Connection health monitoring

Usage:
    manager = WebSocketManager()
    await manager.connect(websocket, user_id, session_id)
    await manager.send_to_user(user_id, event_data)
    await manager.disconnect(websocket)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("inde.ikf.realtime.websocket")

HEARTBEAT_INTERVAL = 30  # seconds
CONNECTION_TIMEOUT = 120  # seconds


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    session_id: str
    connected_at: datetime
    last_heartbeat: datetime
    channels: Set[str] = field(default_factory=set)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time event delivery.

    Supports:
    - Multiple connections per user
    - Channel-based subscriptions
    - Heartbeat monitoring
    - Graceful shutdown
    """

    def __init__(self):
        """Initialize the WebSocket Manager."""
        # Connection registry: websocket -> ConnectionInfo
        self._connections: Dict[WebSocket, ConnectionInfo] = {}
        # User index: user_id -> set of websockets
        self._user_connections: Dict[str, Set[WebSocket]] = {}
        # Session index: session_id -> websocket
        self._session_connections: Dict[str, WebSocket] = {}
        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        # Stats
        self._total_connections = 0
        self._total_messages_sent = 0

    def start(self):
        """Start the WebSocket manager and heartbeat monitoring."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            return
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket manager started")

    def stop(self):
        """Stop the WebSocket manager."""
        self._running = False
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        logger.info("WebSocket manager stopped")

    async def connect(self, websocket: WebSocket, user_id: str,
                      session_id: str) -> bool:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: User identifier
            session_id: Session identifier

        Returns:
            True if connection registered successfully
        """
        try:
            await websocket.accept()

            now = datetime.now(timezone.utc)
            info = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                session_id=session_id,
                connected_at=now,
                last_heartbeat=now
            )

            # Register in all indexes
            self._connections[websocket] = info

            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(websocket)

            self._session_connections[session_id] = websocket

            self._total_connections += 1
            logger.info(f"WebSocket connected: user={user_id}, session={session_id}")

            # Send connection confirmation
            await self._send(websocket, {
                "type": "connection.established",
                "timestamp": now.isoformat(),
                "session_id": session_id
            })

            return True

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False

    async def disconnect(self, websocket: WebSocket):
        """
        Unregister a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
        """
        info = self._connections.pop(websocket, None)
        if not info:
            return

        # Remove from user index
        if info.user_id in self._user_connections:
            self._user_connections[info.user_id].discard(websocket)
            if not self._user_connections[info.user_id]:
                del self._user_connections[info.user_id]

        # Remove from session index
        self._session_connections.pop(info.session_id, None)

        logger.info(f"WebSocket disconnected: user={info.user_id}, session={info.session_id}")

        try:
            await websocket.close()
        except Exception:
            pass  # Already closed

    async def send_to_user(self, user_id: str, data: dict) -> int:
        """
        Send data to all connections for a user.

        Args:
            user_id: Target user ID
            data: Data to send

        Returns:
            Number of connections that received the message
        """
        websockets = self._user_connections.get(user_id, set())
        sent = 0

        for ws in list(websockets):
            if await self._send(ws, data):
                sent += 1

        return sent

    async def send_to_session(self, session_id: str, data: dict) -> bool:
        """
        Send data to a specific session.

        Args:
            session_id: Target session ID
            data: Data to send

        Returns:
            True if message sent successfully
        """
        websocket = self._session_connections.get(session_id)
        if websocket:
            return await self._send(websocket, data)
        return False

    async def broadcast(self, data: dict, channel: str = None) -> int:
        """
        Broadcast data to all connections or a specific channel.

        Args:
            data: Data to send
            channel: Optional channel filter

        Returns:
            Number of connections that received the message
        """
        sent = 0

        for ws, info in list(self._connections.items()):
            if channel and channel not in info.channels:
                continue
            if await self._send(ws, data):
                sent += 1

        return sent

    async def subscribe(self, websocket: WebSocket, channel: str) -> bool:
        """
        Subscribe a connection to a channel.

        Args:
            websocket: The WebSocket connection
            channel: Channel to subscribe to

        Returns:
            True if subscription successful
        """
        info = self._connections.get(websocket)
        if not info:
            return False

        info.channels.add(channel)
        logger.debug(f"Subscribed {info.session_id} to channel {channel}")

        await self._send(websocket, {
            "type": "channel.subscribed",
            "channel": channel,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return True

    async def unsubscribe(self, websocket: WebSocket, channel: str) -> bool:
        """
        Unsubscribe a connection from a channel.

        Args:
            websocket: The WebSocket connection
            channel: Channel to unsubscribe from

        Returns:
            True if unsubscription successful
        """
        info = self._connections.get(websocket)
        if not info:
            return False

        info.channels.discard(channel)
        logger.debug(f"Unsubscribed {info.session_id} from channel {channel}")

        return True

    def get_connection_count(self) -> int:
        """Get current number of active connections."""
        return len(self._connections)

    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for a specific user."""
        return len(self._user_connections.get(user_id, set()))

    def get_stats(self) -> dict:
        """Get WebSocket manager statistics."""
        return {
            "active_connections": len(self._connections),
            "unique_users": len(self._user_connections),
            "total_connections": self._total_connections,
            "total_messages_sent": self._total_messages_sent
        }

    async def _send(self, websocket: WebSocket, data: dict) -> bool:
        """
        Send data to a WebSocket connection.

        Args:
            websocket: Target WebSocket
            data: Data to send

        Returns:
            True if sent successfully
        """
        try:
            await websocket.send_json(data)
            self._total_messages_sent += 1
            return True
        except Exception as e:
            logger.warning(f"WebSocket send failed: {e}")
            # Connection may be dead, clean up
            await self.disconnect(websocket)
            return False

    async def _heartbeat_loop(self):
        """Periodic heartbeat check for all connections."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)

                for ws, info in list(self._connections.items()):
                    # Check for timeout
                    elapsed = (now - info.last_heartbeat).total_seconds()
                    if elapsed > CONNECTION_TIMEOUT:
                        logger.warning(f"Connection timeout: {info.session_id}")
                        await self.disconnect(ws)
                        continue

                    # Send heartbeat
                    await self._send(ws, {
                        "type": "heartbeat",
                        "timestamp": now.isoformat()
                    })

                await asyncio.sleep(HEARTBEAT_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def handle_client_message(self, websocket: WebSocket, message: dict):
        """
        Handle incoming message from a WebSocket client.

        Args:
            websocket: Source WebSocket
            message: Received message
        """
        info = self._connections.get(websocket)
        if not info:
            return

        msg_type = message.get("type")

        if msg_type == "heartbeat":
            info.last_heartbeat = datetime.now(timezone.utc)

        elif msg_type == "subscribe":
            channel = message.get("channel")
            if channel:
                await self.subscribe(websocket, channel)

        elif msg_type == "unsubscribe":
            channel = message.get("channel")
            if channel:
                await self.unsubscribe(websocket, channel)

        else:
            logger.debug(f"Unknown message type: {msg_type}")

    async def shutdown(self):
        """Graceful shutdown - close all connections."""
        self.stop()

        # Notify all clients
        await self.broadcast({
            "type": "server.shutdown",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Close all connections
        for ws in list(self._connections.keys()):
            await self.disconnect(ws)

        logger.info("WebSocket manager shutdown complete")
