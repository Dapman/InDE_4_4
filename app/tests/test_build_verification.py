"""
InDE v3.2 - Build Verification Tests
Verify that all modules can be imported and basic functionality works.
"""

import pytest
import sys
import os

# conftest.py handles path setup - no need to duplicate here


class TestCoreImports:
    """Test that core modules can be imported."""

    def test_config_import(self):
        from core.config import VERSION, VERSION_NAME
        assert VERSION == "3.5.1"
        assert "Federation Protocol" in VERSION_NAME

    def test_database_import(self):
        from core.database import Database
        assert Database is not None

    def test_llm_interface_import(self):
        from core.llm_interface import LLMInterface
        assert LLMInterface is not None


class TestAuthImports:
    """Test that auth modules can be imported."""

    def test_password_import(self):
        from auth.password import hash_password, verify_password
        assert hash_password is not None
        assert verify_password is not None

    def test_jwt_handler_import(self):
        from auth.jwt_handler import create_access_token, verify_access_token
        assert create_access_token is not None
        assert verify_access_token is not None

    def test_middleware_import(self):
        from auth.middleware import get_current_user
        assert get_current_user is not None


class TestEventsImports:
    """Test that events module can be imported."""

    def test_dispatcher_import(self):
        from events.dispatcher import EventDispatcher, emit_event
        assert EventDispatcher is not None
        assert emit_event is not None

    def test_schemas_import(self):
        from events.schemas import DomainEvent, PursuitCreatedEvent
        assert DomainEvent is not None
        assert PursuitCreatedEvent is not None

    def test_redis_publisher_import(self):
        """v3.2: Test Redis publisher imports."""
        from events.redis_publisher import RedisStreamPublisher, publisher
        assert RedisStreamPublisher is not None
        assert publisher is not None

    def test_redis_consumer_import(self):
        """v3.2: Test Redis consumer imports."""
        from events.redis_consumer import RedisStreamConsumer
        assert RedisStreamConsumer is not None

    def test_ikf_events_import(self):
        """v3.2: Test IKF event schemas."""
        from events.schemas import IKFPackagePreparedEvent, IKFPackageReadyEvent
        assert IKFPackagePreparedEvent is not None
        assert IKFPackageReadyEvent is not None


class TestMaturityImports:
    """Test that maturity module can be imported."""

    def test_model_import(self):
        from maturity.model import MaturityCalculator, update_user_maturity
        assert MaturityCalculator is not None
        assert update_user_maturity is not None


class TestCrisisImports:
    """Test that crisis module can be imported."""

    def test_manager_import(self):
        from crisis.manager import CrisisManager
        assert CrisisManager is not None


class TestGIIImports:
    """Test that GII module can be imported."""

    def test_manager_import(self):
        from gii.manager import GIIManager
        assert GIIManager is not None


class TestAPIImports:
    """Test that API modules can be imported."""

    def test_auth_routes(self):
        from api.auth import router
        assert router is not None

    def test_pursuits_routes(self):
        from api.pursuits import router
        assert router is not None

    def test_coaching_routes(self):
        from api.coaching import router
        assert router is not None

    def test_maturity_routes(self):
        from api.maturity import router
        assert router is not None

    def test_crisis_routes(self):
        from api.crisis import router
        assert router is not None


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_and_verify(self):
        from auth.password import hash_password, verify_password

        password = "test_password_123"
        hashed = hash_password(password)

        # Verify the hash is different from original
        assert hashed != password

        # Verify correct password
        assert verify_password(password, hashed) is True

        # Verify wrong password
        assert verify_password("wrong_password", hashed) is False


class TestJWTTokens:
    """Test JWT token functionality."""

    def test_access_token_creation(self):
        from auth.jwt_handler import create_access_token, verify_access_token

        token = create_access_token(
            user_id="test_user",
            email="test@example.com",
            maturity_level="NOVICE"
        )

        assert token is not None
        assert len(token) > 0

        # Verify the token
        claims = verify_access_token(token)
        assert claims["user_id"] == "test_user"
        assert claims["email"] == "test@example.com"
        assert claims["maturity_level"] == "NOVICE"

    def test_refresh_token_creation(self):
        from auth.jwt_handler import create_refresh_token, verify_refresh_token

        token = create_refresh_token("test_user")
        assert token is not None

        user_id = verify_refresh_token(token)
        assert user_id == "test_user"


class TestEventDispatcher:
    """Test event dispatcher functionality."""

    def test_emit_and_handle(self):
        from events.dispatcher import EventDispatcher
        from events.schemas import PursuitCreatedEvent

        dispatcher = EventDispatcher(db=None, persist=False)

        # Track handler calls
        handled_events = []

        def handler(event):
            handled_events.append(event)

        dispatcher.register("pursuit.created", handler)

        # Emit event
        event = PursuitCreatedEvent(
            user_id="test_user",
            pursuit_id="test_pursuit",
            payload={"title": "Test Pursuit"}
        )
        dispatcher.emit(event)

        # Verify handler was called
        assert len(handled_events) == 1
        assert handled_events[0].pursuit_id == "test_pursuit"


class TestGIIGeneration:
    """Test GII generation."""

    def test_gii_format(self):
        # Import directly to test generation
        import secrets

        region = "NA"
        random_id = secrets.token_hex(6).upper()
        gii = f"GII-{region}-{random_id}"

        assert gii.startswith("GII-")
        parts = gii.split("-")
        assert len(parts) == 3
        assert parts[0] == "GII"
        assert parts[1] == "NA"
        assert len(parts[2]) == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
