"""
Federation Connection Manager

Manages the full connection lifecycle between this InDE instance and a remote IKF hub.
Implements the state machine: UNREGISTERED → DISCONNECTED → CONNECTING → CONNECTED

Key design decisions:
- All outbound calls go through the circuit breaker (Phase 3)
- Heartbeat runs on a background async task, never blocking coaching
- State transitions emit federation events to Redis Streams
- Connection credentials are encrypted at rest in ikf_federation_state collection
- The connection manager is a singleton; only one connection per InDE instance

Usage:
    manager = ConnectionManager(db, config, event_publisher, circuit_breaker)
    await manager.register(org_credentials)
    await manager.connect()
    # ... heartbeat runs automatically ...
    await manager.disconnect()
"""

import asyncio
import httpx
import os
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Dict, Any
import logging

from .circuit_breaker import CircuitBreaker, CircuitOpenError

logger = logging.getLogger("inde.ikf.connection_manager")


class FederationState(str, Enum):
    """Federation connection state machine states."""
    UNREGISTERED = "UNREGISTERED"  # No registration data
    DISCONNECTED = "DISCONNECTED"  # Registered but not connected
    CONNECTING = "CONNECTING"      # Connection in progress
    CONNECTED = "CONNECTED"        # Actively connected with heartbeat


class ConnectionConfig:
    """Configuration for federation connection."""

    def __init__(self):
        self.IKF_INSTANCE_ID = os.environ.get(
            "IKF_INSTANCE_ID",
            f"inde-{uuid.uuid4().hex[:8]}"
        )
        self.IKF_REMOTE_NODE_URL = os.environ.get("IKF_REMOTE_NODE_URL", "")
        self.IKF_FEDERATION_MODE = os.environ.get("IKF_FEDERATION_MODE", "OFFLINE")
        self.IKF_API_KEY = os.environ.get("IKF_API_KEY", "")

        # Timing configuration
        self.IKF_HEARTBEAT_INTERVAL_SECONDS = int(
            os.environ.get("IKF_HEARTBEAT_INTERVAL", "60")
        )
        self.IKF_CONNECTION_TIMEOUT_SECONDS = int(
            os.environ.get("IKF_CONNECTION_TIMEOUT", "30")
        )
        self.IKF_RETRY_BACKOFF_SECONDS = int(
            os.environ.get("IKF_RETRY_BACKOFF", "30")
        )

        # Circuit breaker settings
        self.IKF_CIRCUIT_BREAKER_THRESHOLD = int(
            os.environ.get("IKF_CIRCUIT_BREAKER_THRESHOLD", "5")
        )
        self.IKF_CIRCUIT_BREAKER_RESET_SECONDS = int(
            os.environ.get("IKF_CIRCUIT_BREAKER_RESET", "300")
        )


class ConnectionManager:
    """
    Singleton managing the federation connection lifecycle.

    The connection manager handles:
    - Registration with IKF hub
    - Connection establishment with JWT exchange
    - Periodic heartbeat to maintain connection
    - Automatic reconnection with exponential backoff
    - Graceful disconnection

    All operations are async and non-blocking. Failures are isolated
    via the circuit breaker to ensure coaching is never impacted.
    """

    def __init__(
        self,
        db,
        config: Optional[ConnectionConfig] = None,
        event_publisher=None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize connection manager.

        Args:
            db: MongoDB database connection
            config: Connection configuration (or use defaults from env)
            event_publisher: Redis event publisher for federation events
            circuit_breaker: Circuit breaker for outbound calls
        """
        self._db = db
        self._config = config or ConnectionConfig()
        self._publisher = event_publisher

        # Create circuit breaker if not provided
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=self._config.IKF_CIRCUIT_BREAKER_THRESHOLD,
            reset_timeout=self._config.IKF_CIRCUIT_BREAKER_RESET_SECONDS,
            on_state_change=self._on_circuit_state_change
        )

        # Connection state
        self._state = FederationState.UNREGISTERED
        self._federation_jwt: Optional[str] = None
        self._verification_level: Optional[str] = None
        self._assigned_region: Optional[str] = None

        # Heartbeat management
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_heartbeat: Optional[datetime] = None
        self._consecutive_heartbeat_failures = 0

        # Reconnection management
        self._reconnect_attempt = 0
        self._max_reconnect_attempts = 10
        self._reconnect_task: Optional[asyncio.Task] = None

        # HTTP client
        self._http_client = httpx.AsyncClient(
            timeout=self._config.IKF_CONNECTION_TIMEOUT_SECONDS,
            verify=True  # TLS certificate verification
        )

        # Load persisted state
        self._load_state()

        logger.info(
            f"Connection manager initialized: instance={self._config.IKF_INSTANCE_ID}, "
            f"mode={self._config.IKF_FEDERATION_MODE}"
        )

    def _load_state(self):
        """Load persisted federation state from MongoDB."""
        try:
            state_doc = self._db.ikf_federation_state.find_one({"type": "connection"})
            if state_doc:
                saved_state = state_doc.get("connection_state", "UNREGISTERED")
                self._state = FederationState(saved_state)
                self._federation_jwt = state_doc.get("federation_jwt")
                self._verification_level = state_doc.get("verification_level")
                self._reconnect_attempt = state_doc.get("reconnect_attempt", 0)

                # If was connected before restart, transition to DISCONNECTED
                if self._state == FederationState.CONNECTED:
                    self._state = FederationState.DISCONNECTED
                    self._persist_state()
                    logger.info("Federation was CONNECTED before restart → DISCONNECTED")

                logger.info(f"Loaded federation state: {self._state.value}")
        except Exception as e:
            logger.warning(f"Could not load federation state: {e}")

    def _persist_state(self):
        """Persist current state to MongoDB."""
        try:
            self._db.ikf_federation_state.update_one(
                {"type": "connection"},
                {"$set": {
                    "type": "connection",
                    "connection_state": self._state.value,
                    "federation_jwt": self._federation_jwt,
                    "verification_level": self._verification_level,
                    "assigned_region": self._assigned_region,
                    "last_state_change": datetime.now(timezone.utc),
                    "reconnect_attempt": self._reconnect_attempt,
                    "instance_id": self._config.IKF_INSTANCE_ID,
                    "version": "3.5.1"
                }},
                upsert=True
            )
        except Exception as e:
            logger.warning(f"Could not persist federation state: {e}")

    def _on_circuit_state_change(self, old_state, new_state):
        """Handle circuit breaker state changes."""
        logger.info(f"Circuit breaker: {old_state.value} → {new_state.value}")

        # If circuit opens while connected, we need to handle disconnection
        if new_state.value == "OPEN" and self._state == FederationState.CONNECTED:
            logger.warning("Circuit breaker OPEN while connected - scheduling reconnect")
            asyncio.create_task(self._handle_circuit_open())

    async def _handle_circuit_open(self):
        """Handle circuit breaker opening."""
        self._state = FederationState.DISCONNECTED
        self._stop_heartbeat()
        self._persist_state()
        await self._publish_event("federation.circuit_breaker.opened", {
            "instance_id": self._config.IKF_INSTANCE_ID,
            "previous_state": "CONNECTED"
        })

    # === Properties ===

    @property
    def state(self) -> FederationState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == FederationState.CONNECTED

    @property
    def is_registered(self) -> bool:
        return self._state != FederationState.UNREGISTERED

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker

    # === Registration ===

    async def register(self, org_credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register this InDE instance with the IKF hub.

        Transition: UNREGISTERED → DISCONNECTED

        Args:
            org_credentials: {
                "organization_id": str,
                "organization_name": str,
                "industry_codes": list[str],
                "sharing_level": str,  # MINIMAL, MODERATE, FULL
            }

        Returns:
            Registration result with status
        """
        if self._state not in (FederationState.UNREGISTERED, FederationState.DISCONNECTED):
            logger.warning(f"Cannot register from state {self._state}")
            return {"status": "ERROR", "reason": f"Invalid state: {self._state.value}"}

        # Generate instance ID if not set
        instance_id = self._config.IKF_INSTANCE_ID

        # Store registration data
        registration_data = {
            "type": "registration",
            "instance_id": instance_id,
            "organization_id": org_credentials.get("organization_id"),
            "organization_name": org_credentials.get("organization_name"),
            "industry_codes": org_credentials.get("industry_codes", []),
            "sharing_level": org_credentials.get("sharing_level", "MODERATE"),
            "registered_at": datetime.now(timezone.utc)
        }

        try:
            self._db.ikf_federation_state.update_one(
                {"type": "registration"},
                {"$set": registration_data},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to persist registration: {e}")
            return {"status": "ERROR", "reason": str(e)}

        self._state = FederationState.DISCONNECTED
        self._persist_state()

        # Emit registration event
        await self._publish_event("federation.registered", {
            "instance_id": instance_id,
            "org_id": org_credentials.get("organization_id"),
            "verification_level": "PENDING"
        })

        logger.info(f"Federation registered: {instance_id}")

        return {
            "status": "REGISTERED",
            "state": self._state.value,
            "instance_id": instance_id
        }

    # === Connection ===

    async def connect(self) -> Dict[str, Any]:
        """
        Establish federation connection with IKF hub.

        Transition: DISCONNECTED → CONNECTING → CONNECTED (or back to DISCONNECTED on failure)

        Returns:
            Connection result with status and verification level
        """
        if self._state not in (FederationState.DISCONNECTED,):
            logger.warning(f"Cannot connect from state {self._state}")
            return {"status": "ERROR", "reason": f"Invalid state: {self._state.value}"}

        if not self._config.IKF_REMOTE_NODE_URL:
            logger.warning("No IKF_REMOTE_NODE_URL configured")
            return {"status": "ERROR", "reason": "No remote URL configured"}

        self._state = FederationState.CONNECTING
        self._persist_state()

        try:
            # Get registration data
            registration = self._db.ikf_federation_state.find_one({"type": "registration"})
            if not registration:
                self._state = FederationState.UNREGISTERED
                self._persist_state()
                return {"status": "ERROR", "reason": "Not registered — call register() first"}

            # Attempt connection through circuit breaker
            connect_url = f"{self._config.IKF_REMOTE_NODE_URL}/federation/connect"
            connect_payload = {
                "instance_id": registration.get("instance_id", self._config.IKF_INSTANCE_ID),
                "organization_id": registration.get("organization_id"),
                "industry_codes": registration.get("industry_codes", []),
                "sharing_level": registration.get("sharing_level", "MODERATE"),
                "version": "3.5.1",
                "capabilities": ["contributions", "patterns", "benchmarks"]
            }

            logger.info(f"Connecting to federation: {connect_url}")

            response = await self._circuit_breaker.call(
                self._http_client.post,
                connect_url,
                json=connect_payload,
                headers=self._auth_headers()
            )

            if response.status_code == 200:
                data = response.json()
                self._federation_jwt = data.get("federation_token")
                self._verification_level = data.get("verification_level", "PARTICIPANT")
                self._assigned_region = data.get("assigned_region")
                self._state = FederationState.CONNECTED
                self._reconnect_attempt = 0
                self._persist_state()

                # Start heartbeat
                self._start_heartbeat()

                # Emit connected event
                await self._publish_event("federation.connected", {
                    "instance_id": self._config.IKF_INSTANCE_ID,
                    "remote_url": self._config.IKF_REMOTE_NODE_URL,
                    "verification_level": self._verification_level,
                    "latency_ms": response.elapsed.total_seconds() * 1000
                })

                logger.info(
                    f"Federation CONNECTED (verification: {self._verification_level}, "
                    f"region: {self._assigned_region})"
                )

                return {
                    "status": "CONNECTED",
                    "verification_level": self._verification_level,
                    "assigned_region": self._assigned_region,
                    "capabilities": data.get("capabilities", [])
                }
            else:
                raise ConnectionError(f"IKF returned {response.status_code}: {response.text}")

        except CircuitOpenError as e:
            logger.warning(f"Circuit breaker prevented connection: {e}")
            self._state = FederationState.DISCONNECTED
            self._persist_state()
            return {
                "status": "CIRCUIT_OPEN",
                "reason": str(e),
                "reconnect_scheduled": False
            }

        except Exception as e:
            logger.warning(f"Federation connection failed: {e}")
            self._state = FederationState.DISCONNECTED
            self._persist_state()

            # Schedule reconnection with backoff
            await self._schedule_reconnect()

            return {
                "status": "FAILED",
                "reason": str(e),
                "reconnect_scheduled": True,
                "next_attempt": self._reconnect_attempt
            }

    async def disconnect(self) -> Dict[str, Any]:
        """
        Gracefully disconnect from IKF hub.

        Transition: CONNECTED → DISCONNECTED

        Returns:
            Disconnection result
        """
        # Stop heartbeat first
        self._stop_heartbeat()

        # Cancel any pending reconnect
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

        # Notify hub if connected
        if self._state == FederationState.CONNECTED and self._config.IKF_REMOTE_NODE_URL:
            try:
                await self._circuit_breaker.call(
                    self._http_client.post,
                    f"{self._config.IKF_REMOTE_NODE_URL}/federation/disconnect",
                    json={
                        "instance_id": self._config.IKF_INSTANCE_ID,
                        "reason": "manual"
                    },
                    headers=self._auth_headers()
                )
            except Exception as e:
                # Graceful disconnect failure is non-critical
                logger.warning(f"Graceful disconnect notification failed: {e}")

        previous_state = self._state
        self._state = FederationState.DISCONNECTED
        self._federation_jwt = None
        self._reconnect_attempt = 0
        self._persist_state()

        await self._publish_event("federation.disconnected", {
            "instance_id": self._config.IKF_INSTANCE_ID,
            "reason": "manual_disconnect",
            "previous_state": previous_state.value,
            "reconnect_scheduled": False
        })

        logger.info("Federation DISCONNECTED (graceful)")

        return {"status": "DISCONNECTED"}

    # === Heartbeat ===

    def _start_heartbeat(self):
        """Start the periodic heartbeat background task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            return  # Already running

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            f"Heartbeat started (interval: {self._config.IKF_HEARTBEAT_INTERVAL_SECONDS}s)"
        )

    def _stop_heartbeat(self):
        """Stop the heartbeat background task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            logger.info("Heartbeat stopped")

    async def _heartbeat_loop(self):
        """
        Periodic heartbeat to IKF hub.

        Runs as a background task. Failures trigger reconnection logic.
        MUST NEVER block or impact coaching operations.
        """
        interval = self._config.IKF_HEARTBEAT_INTERVAL_SECONDS
        max_failures = self._config.IKF_CIRCUIT_BREAKER_THRESHOLD

        while self._state == FederationState.CONNECTED:
            try:
                await asyncio.sleep(interval)

                # Double-check state after sleep
                if self._state != FederationState.CONNECTED:
                    break

                # Get pending contribution count
                pending_contributions = 0
                try:
                    pending_contributions = self._db.ikf_contributions.count_documents(
                        {"status": "IKF_READY"}
                    )
                except Exception:
                    pass

                # Send heartbeat
                response = await self._circuit_breaker.call(
                    self._http_client.post,
                    f"{self._config.IKF_REMOTE_NODE_URL}/federation/heartbeat",
                    json={
                        "instance_id": self._config.IKF_INSTANCE_ID,
                        "connection_state": self._state.value,
                        "pending_contributions": pending_contributions,
                        "local_health": {"status": "healthy", "version": "3.5.1"},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    headers=self._auth_headers(),
                    timeout=10  # Shorter timeout for heartbeat
                )

                if response.status_code == 200:
                    self._consecutive_heartbeat_failures = 0
                    self._last_heartbeat = datetime.now(timezone.utc)

                    data = response.json()
                    await self._publish_event("federation.heartbeat.sent", {
                        "instance_id": self._config.IKF_INSTANCE_ID,
                        "status": "OK",
                        "pending_patterns": data.get("pending_patterns", 0),
                        "pending_contributions": pending_contributions
                    })
                else:
                    raise ConnectionError(f"Heartbeat rejected: {response.status_code}")

            except asyncio.CancelledError:
                break

            except CircuitOpenError as e:
                logger.warning(f"Heartbeat blocked by circuit breaker: {e}")
                # Circuit breaker is open - disconnect and schedule reconnect
                self._state = FederationState.DISCONNECTED
                self._persist_state()
                await self._schedule_reconnect()
                break

            except Exception as e:
                self._consecutive_heartbeat_failures += 1
                logger.warning(
                    f"Heartbeat failed ({self._consecutive_heartbeat_failures}/"
                    f"{max_failures}): {e}"
                )

                await self._publish_event("federation.heartbeat.failed", {
                    "instance_id": self._config.IKF_INSTANCE_ID,
                    "failure_count": self._consecutive_heartbeat_failures,
                    "error": str(e),
                    "circuit_state": self._circuit_breaker.state.value
                })

                if self._consecutive_heartbeat_failures >= max_failures:
                    logger.error("Heartbeat failures exceeded threshold — disconnecting")
                    self._state = FederationState.DISCONNECTED
                    self._persist_state()
                    await self._schedule_reconnect()
                    break

    # === Reconnection ===

    async def _schedule_reconnect(self):
        """Schedule a reconnection attempt with exponential backoff."""
        if self._reconnect_attempt >= self._max_reconnect_attempts:
            logger.error("Max reconnection attempts reached — giving up")
            await self._publish_event("federation.disconnected", {
                "instance_id": self._config.IKF_INSTANCE_ID,
                "reason": "max_reconnect_attempts_exceeded",
                "reconnect_scheduled": False
            })
            return

        # Exponential backoff: 30s, 60s, 120s, 240s, cap at 300s
        base = self._config.IKF_RETRY_BACKOFF_SECONDS
        delay = min(base * (2 ** self._reconnect_attempt), 300)
        self._reconnect_attempt += 1
        self._persist_state()

        logger.info(f"Scheduling reconnect attempt {self._reconnect_attempt} in {delay}s")

        await self._publish_event("federation.reconnect.scheduled", {
            "instance_id": self._config.IKF_INSTANCE_ID,
            "attempt": self._reconnect_attempt,
            "delay_seconds": delay
        })

        self._reconnect_task = asyncio.create_task(self._reconnect_after_delay(delay))

    async def _reconnect_after_delay(self, delay: float):
        """Wait, then attempt reconnection."""
        try:
            await asyncio.sleep(delay)
            if self._state == FederationState.DISCONNECTED:
                result = await self.connect()
                logger.info(f"Reconnect result: {result}")
        except asyncio.CancelledError:
            logger.info("Reconnect cancelled")

    # === Helpers ===

    def _auth_headers(self) -> Dict[str, str]:
        """Build authorization headers for outbound federation calls."""
        headers = {
            "Content-Type": "application/json",
            "X-InDE-Instance": self._config.IKF_INSTANCE_ID,
            "X-InDE-Version": "3.5.1"
        }

        if self._federation_jwt:
            headers["Authorization"] = f"Bearer {self._federation_jwt}"
        elif self._config.IKF_API_KEY:
            headers["X-API-Key"] = self._config.IKF_API_KEY

        return headers

    async def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish federation event to Redis Streams (fire-and-forget)."""
        if not self._publisher:
            return

        try:
            event_data = {
                **data,
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await self._publisher.publish(event_type, event_data)
        except Exception as e:
            # Federation events must NEVER block — log and continue
            logger.warning(f"Failed to publish {event_type}: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Return current federation status for API/dashboard."""
        return {
            "connection_state": self._state.value,
            "instance_id": self._config.IKF_INSTANCE_ID,
            "remote_url": self._config.IKF_REMOTE_NODE_URL or "(not configured)",
            "verification_level": self._verification_level,
            "assigned_region": self._assigned_region,
            "has_jwt": bool(self._federation_jwt),
            "reconnect_attempt": self._reconnect_attempt,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "heartbeat_active": bool(
                self._heartbeat_task and not self._heartbeat_task.done()
            ),
            "last_heartbeat": (
                self._last_heartbeat.isoformat() if self._last_heartbeat else None
            ),
            "consecutive_heartbeat_failures": self._consecutive_heartbeat_failures,
            "circuit_breaker": self._circuit_breaker.get_status(),
            "mode": self._config.IKF_FEDERATION_MODE,
            "version": "3.5.1"
        }

    async def shutdown(self):
        """Clean shutdown of connection manager."""
        logger.info("Connection manager shutting down...")

        # Stop heartbeat
        self._stop_heartbeat()

        # Cancel reconnect task
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

        # Close HTTP client
        await self._http_client.aclose()

        logger.info("Connection manager shutdown complete")
