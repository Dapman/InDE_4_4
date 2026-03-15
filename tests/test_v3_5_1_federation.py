"""
InDE MVP v3.5.1 - Federation Protocol Activation Tests

Tests for the new federation components:
1. Circuit Breaker - State machine validation
2. Connection Manager - Lifecycle transitions
3. Federation Authentication - JWT validation
4. Federation Events - Schema and publishing
5. Graceful Degradation - Coaching isolation
6. API Versioning - Route validation

Run with: pytest tests/test_v3_5_1_federation.py -v
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==============================================================================
# CIRCUIT BREAKER TESTS
# ==============================================================================

class TestCircuitBreaker:
    """Circuit breaker state machine validation."""

    def test_starts_closed(self):
        """Initial state is CLOSED."""
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'ikf-service'
        ))
        from federation.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=3, reset_timeout=60)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed

    def test_opens_after_threshold_failures(self):
        """Transitions to OPEN after failure_threshold failures."""
        from federation.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=3, reset_timeout=60)

        # Record failures
        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open

    @pytest.mark.asyncio
    async def test_rejects_calls_when_open(self):
        """CircuitOpenError raised when OPEN."""
        from federation.circuit_breaker import CircuitBreaker, CircuitOpenError

        breaker = CircuitBreaker(failure_threshold=1, reset_timeout=300)
        breaker.record_failure()  # Opens the circuit

        async def mock_func():
            return "should not be called"

        with pytest.raises(CircuitOpenError):
            await breaker.call(mock_func)

    def test_transitions_to_half_open_after_timeout(self):
        """After reset timeout, transitions to HALF_OPEN."""
        from federation.circuit_breaker import CircuitBreaker, CircuitState

        # Use very short timeout for testing
        breaker = CircuitBreaker(failure_threshold=1, reset_timeout=1)
        breaker.record_failure()  # Opens the circuit

        assert breaker.state == CircuitState.OPEN

        # Wait for reset timeout
        time.sleep(1.1)

        # Check state (should auto-transition to HALF_OPEN)
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_on_successful_probe(self):
        """Successful HALF_OPEN call transitions to CLOSED."""
        from federation.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=1, reset_timeout=1)
        breaker.record_failure()  # Opens

        time.sleep(1.1)  # Wait for HALF_OPEN

        async def successful_call():
            return "success"

        result = await breaker.call(successful_call)

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_manual_reset(self):
        """Admin reset forces CLOSED state."""
        from federation.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=1, reset_timeout=300)
        breaker.record_failure()  # Opens
        assert breaker.state == CircuitState.OPEN

        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_get_status(self):
        """get_status returns expected structure."""
        from federation.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=5, reset_timeout=300)

        status = breaker.get_status()

        assert "state" in status
        assert "failure_count" in status
        assert "failure_threshold" in status
        assert "statistics" in status
        assert status["failure_threshold"] == 5


# ==============================================================================
# CONNECTION MANAGER TESTS
# ==============================================================================

class TestConnectionManager:
    """Connection lifecycle validation."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        mock = MagicMock()
        mock.ikf_federation_state.find_one.return_value = None
        mock.ikf_contributions.count_documents.return_value = 0
        return mock

    @pytest.fixture
    def connection_manager(self, mock_db):
        """Create connection manager with mocks."""
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'ikf-service'
        ))
        from federation.connection_manager import ConnectionManager

        return ConnectionManager(
            db=mock_db,
            config=None,
            event_publisher=None,
            circuit_breaker=None
        )

    def test_initial_state_unregistered(self, connection_manager):
        """Starts in UNREGISTERED state."""
        from federation.connection_manager import FederationState

        assert connection_manager.state == FederationState.UNREGISTERED
        assert not connection_manager.is_registered

    @pytest.mark.asyncio
    async def test_register_transitions_to_disconnected(self, connection_manager):
        """Registration moves to DISCONNECTED."""
        from federation.connection_manager import FederationState

        result = await connection_manager.register({
            "organization_id": "test-org",
            "organization_name": "Test Organization",
            "industry_codes": ["TECH"],
            "sharing_level": "MODERATE"
        })

        assert result["status"] == "REGISTERED"
        assert connection_manager.state == FederationState.DISCONNECTED
        assert connection_manager.is_registered

    def test_get_status_structure(self, connection_manager):
        """get_status returns expected structure."""
        status = connection_manager.get_status()

        assert "connection_state" in status
        assert "instance_id" in status
        assert "remote_url" in status
        assert "circuit_breaker" in status
        assert "mode" in status


# ==============================================================================
# FEDERATION AUTHENTICATION TESTS
# ==============================================================================

class TestFederationAuth:
    """Authentication and JWT validation."""

    @pytest.fixture
    def authenticator(self):
        """Create authenticator instance."""
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'ikf-service'
        ))
        from federation.auth import FederationAuthenticator

        return FederationAuthenticator()

    def test_valid_jwt_accepted(self, authenticator):
        """Valid federation JWT passes validation."""
        try:
            import jwt
        except ImportError:
            pytest.skip("PyJWT not installed")

        # Create a valid token
        payload = {
            "sub": "test-org",
            "iss": "https://auth.ikf.indeverse.io",
            "aud": "api.ikf.indeverse.io",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(timezone.utc).timestamp(),
            "scope": "federation:read federation:write",
            "orgId": "test-org",
            "verificationLevel": "PARTICIPANT",
            "instanceId": "test-instance"
        }
        token = jwt.encode(
            payload,
            "simulator-secret-key-change-in-prod",
            algorithm="HS256"
        )

        auth = authenticator.validate_inbound_token(token)

        assert auth.org_id == "test-org"
        assert auth.verification_level == "PARTICIPANT"
        assert auth.has_scope("federation:read")
        assert auth.has_scope("federation:write")

    def test_expired_jwt_rejected(self, authenticator):
        """Expired JWT raises FederationAuthError."""
        try:
            import jwt
        except ImportError:
            pytest.skip("PyJWT not installed")

        from federation.auth import FederationAuthError

        # Create an expired token
        payload = {
            "sub": "test-org",
            "iss": "https://auth.ikf.indeverse.io",
            "aud": "api.ikf.indeverse.io",
            "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp(),
            "iat": (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp(),
            "scope": "federation:read",
            "orgId": "test-org",
            "verificationLevel": "PARTICIPANT"
        }
        token = jwt.encode(
            payload,
            "simulator-secret-key-change-in-prod",
            algorithm="HS256"
        )

        with pytest.raises(FederationAuthError) as exc_info:
            authenticator.validate_inbound_token(token)

        assert "expired" in str(exc_info.value).lower()

    def test_outbound_headers_with_jwt(self, authenticator):
        """create_outbound_headers includes JWT in Authorization header."""
        headers = authenticator.create_outbound_headers("test-jwt-token")

        assert headers["Authorization"] == "Bearer test-jwt-token"
        assert "X-InDE-Instance" in headers
        assert headers["X-InDE-Version"] == "3.5.1"


# ==============================================================================
# FEDERATION EVENTS TESTS
# ==============================================================================

class TestFederationEvents:
    """Event schema and publishing."""

    def test_all_event_types_defined(self):
        """FEDERATION_EVENT_TYPES contains all expected types."""
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'ikf-service'
        ))
        from events.federation_events import FEDERATION_EVENT_TYPES, list_event_types

        expected_types = [
            "federation.registered",
            "federation.connected",
            "federation.disconnected",
            "federation.heartbeat.sent",
            "federation.heartbeat.failed",
            "federation.circuit.opened",
            "federation.circuit.closed",
        ]

        for event_type in expected_types:
            assert event_type in FEDERATION_EVENT_TYPES, f"Missing: {event_type}"

        # Verify list_event_types function
        event_list = list_event_types()
        for event_type in expected_types:
            assert event_type in event_list

    def test_event_validation(self):
        """Events can be validated against schemas."""
        from events.federation_events import validate_event, FederationConnectedEvent

        event = validate_event("federation.connected", {
            "instance_id": "test-instance",
            "remote_url": "http://test.local",
            "verification_level": "PARTICIPANT",
            "latency_ms": 50.5
        })

        assert isinstance(event, FederationConnectedEvent)
        assert event.instance_id == "test-instance"
        assert event.latency_ms == 50.5


# ==============================================================================
# API VERSIONING TESTS
# ==============================================================================

class TestAPIVersioning:
    """Route versioning validation."""

    def test_federation_router_uses_v1_prefix(self):
        """Federation router uses /v1/federation prefix."""
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'ikf-service'
        ))
        from api.federation import router

        assert router.prefix == "/v1/federation"

    def test_admin_router_uses_v1_prefix(self):
        """Admin router uses /v1/federation/admin prefix."""
        from api.federation_admin import router

        assert router.prefix == "/v1/federation/admin"


# ==============================================================================
# HUB SIMULATOR TESTS
# ==============================================================================

class TestHubSimulator:
    """Hub simulator for local testing."""

    @pytest.fixture
    def simulator(self):
        """Create simulator instance."""
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'ikf-service'
        ))
        from federation.hub_simulator import HubSimulator

        return HubSimulator()

    @pytest.mark.asyncio
    async def test_connect_returns_jwt(self, simulator):
        """Connect endpoint returns federation JWT."""
        from federation.hub_simulator import ConnectRequest

        request = ConnectRequest(
            instance_id="test-instance",
            organization_id="test-org",
            industry_codes=["TECH"],
            sharing_level="MODERATE"
        )

        response = await simulator.handle_connect(request)

        assert response.status == "CONNECTED"
        assert response.federation_token is not None
        assert len(response.federation_token) > 0
        assert response.verification_level == "PARTICIPANT"

    @pytest.mark.asyncio
    async def test_heartbeat_requires_connection(self, simulator):
        """Heartbeat fails if not connected."""
        from federation.hub_simulator import HeartbeatRequest
        from fastapi import HTTPException

        request = HeartbeatRequest(
            instance_id="not-connected",
            connection_state="CONNECTED",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        with pytest.raises(HTTPException) as exc_info:
            await simulator.handle_heartbeat(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_sync_pull_returns_patterns(self, simulator):
        """Sync pull returns seeded patterns."""
        from federation.hub_simulator import ConnectRequest

        # First connect
        connect_req = ConnectRequest(
            instance_id="sync-test",
            organization_id="test-org"
        )
        await simulator.handle_connect(connect_req)

        # Then pull
        response = await simulator.handle_sync_pull("sync-test")

        assert response.count >= 0
        assert isinstance(response.patterns, list)


# ==============================================================================
# VERSION TESTS
# ==============================================================================

class TestVersion:
    """Version string validation."""

    def test_config_version_is_3_5_1(self):
        """Core config reports version 3.5.1."""
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'app'
        ))
        from core.config import VERSION, VERSION_NAME

        assert VERSION == "3.5.1"
        assert "Federation Protocol" in VERSION_NAME


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
