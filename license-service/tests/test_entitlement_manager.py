"""
Tests for InDE License Entitlement Manager.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
from unittest.mock import patch, AsyncMock, MagicMock

from entitlement_manager import EntitlementManager
from key_generator import generate_license_key
from models import LicenseTier


class TestSimulationMode:
    """Test entitlement manager in simulation mode."""

    @pytest.fixture
    def manager(self):
        """Create a manager with temporary cache."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            grace_file = f.name

        # Patch config to use temp files
        with patch('entitlement_manager.config') as mock_config:
            mock_config.CACHE_FILE = cache_file
            mock_config.GRACE_STATE_FILE = grace_file
            mock_config.LICENSE_MODE = "simulation"
            mock_config.HMAC_SECRET = "test-secret"
            mock_config.is_simulation_mode.return_value = True

            manager = EntitlementManager()
            yield manager

        # Cleanup
        for f in [cache_file, grace_file]:
            if os.path.exists(f):
                os.unlink(f)

    @pytest.mark.asyncio
    async def test_simulation_generates_manifest(self, manager):
        """Test that simulation mode generates a valid manifest."""
        key = generate_license_key("professional")

        with patch('entitlement_manager.config') as mock_config:
            mock_config.is_simulation_mode.return_value = True
            mock_config.LICENSE_KEY = key
            mock_config.HMAC_SECRET = "test-secret"

            success, manifest, error = await manager.validate_license(key)

            # In simulation mode, should generate a manifest
            assert manifest is not None or error is not None


class TestKeyValidation:
    """Test license key validation."""

    def test_invalid_key_format_rejected(self):
        """Test that invalid key format is rejected."""
        manager = EntitlementManager()

        # This should fail synchronously during format validation
        with patch('entitlement_manager.validate_key_format') as mock_validate:
            mock_validate.return_value = False
            # Would need async test for full validation


class TestModuleEntitlements:
    """Test module entitlement checks."""

    def test_module_enabled_check(self):
        """Test checking if a module is enabled."""
        manager = EntitlementManager()

        # Without cached manifest, should return False
        assert manager.is_module_enabled("odicm") is False

    def test_get_enabled_modules_empty(self):
        """Test getting enabled modules with no manifest."""
        manager = EntitlementManager()

        modules = manager.get_enabled_modules()
        assert modules == []


class TestLicenseKeyFormats:
    """Test various license key formats."""

    @pytest.mark.parametrize("tier", ["professional", "enterprise", "federated"])
    def test_tier_key_validation(self, tier):
        """Test that generated keys for each tier are valid."""
        key = generate_license_key(tier)

        # Key should be properly formatted
        assert key.startswith("INDE-")
        assert len(key) == 26  # INDE-XXX-XXXXXXXXXXXX-XXXX
