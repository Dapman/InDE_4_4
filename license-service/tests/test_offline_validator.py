"""
Tests for InDE License Offline Validator.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json
import tempfile
from datetime import datetime, timezone, timedelta

from offline_validator import OfflineLicenseValidator
from crypto import generate_offline_license, sign_manifest


class TestOfflineValidatorBasics:
    """Test basic offline validator functionality."""

    def test_no_license_file(self):
        """Test behavior when no license file exists."""
        validator = OfflineLicenseValidator("/nonexistent/path.json")
        assert validator.has_offline_license() is False

    def test_has_license_file(self):
        """Test detecting existing license file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "data"}, f)
            temp_file = f.name

        try:
            validator = OfflineLicenseValidator(temp_file)
            assert validator.has_offline_license() is True
        finally:
            os.unlink(temp_file)


class TestOfflineValidation:
    """Test offline license validation."""

    @pytest.fixture
    def valid_manifest(self):
        """Create a valid manifest."""
        now = datetime.now(timezone.utc)
        return {
            "license_key": "INDE-PRO-TESTCUST0001-ABCD",
            "customer_id": "TESTCUST0001",
            "customer_name": "Test Customer",
            "tier": "professional",
            "seat_limit": 10,
            "modules": ["odicm", "tim", "rve"],
            "federation_enabled": False,
            "mig_enabled": False,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=365)).isoformat(),
            "signature": ""
        }

    def test_validate_valid_license(self, valid_manifest):
        """Test validating a valid offline license."""
        # Generate offline license
        offline = generate_offline_license(valid_manifest, ttl_days=30)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(offline, f)
            temp_file = f.name

        try:
            validator = OfflineLicenseValidator(temp_file)
            is_valid, manifest, error = validator.validate()

            assert is_valid is True
            assert manifest is not None
            assert error is None
            assert manifest.customer_name == "Test Customer"
        finally:
            os.unlink(temp_file)

    def test_validate_expired_license(self, valid_manifest):
        """Test validating an expired offline license."""
        now = datetime.now(timezone.utc)

        # Create expired license
        expired = {
            "manifest": valid_manifest,
            "generated_at": (now - timedelta(days=100)).isoformat(),
            "expires_at": (now - timedelta(days=10)).isoformat()
        }
        expired["signature"] = sign_manifest(expired)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(expired, f)
            temp_file = f.name

        try:
            validator = OfflineLicenseValidator(temp_file)
            is_valid, manifest, error = validator.validate()

            assert is_valid is False
            assert manifest is None
            # Either "expired" or "signature" error since signature check comes first
            assert "expired" in error.lower() or "signature" in error.lower()
        finally:
            os.unlink(temp_file)

    def test_validate_tampered_license(self, valid_manifest):
        """Test validating a tampered offline license."""
        offline = generate_offline_license(valid_manifest, ttl_days=30)

        # Tamper with the manifest
        offline["manifest"]["seat_limit"] = 999

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(offline, f)
            temp_file = f.name

        try:
            validator = OfflineLicenseValidator(temp_file)
            is_valid, manifest, error = validator.validate()

            assert is_valid is False
            assert "signature" in error.lower()
        finally:
            os.unlink(temp_file)

    def test_validate_missing_file(self):
        """Test validation when file doesn't exist."""
        validator = OfflineLicenseValidator("/nonexistent/license.json")
        is_valid, manifest, error = validator.validate()

        assert is_valid is False
        assert manifest is None
        assert "no" in error.lower() or "not found" in error.lower()


class TestExpirationInfo:
    """Test expiration information retrieval."""

    @pytest.fixture
    def valid_manifest(self):
        """Create a valid manifest."""
        now = datetime.now(timezone.utc)
        return {
            "license_key": "INDE-PRO-TESTCUST0001-ABCD",
            "customer_id": "TESTCUST0001",
            "customer_name": "Test Customer",
            "tier": "professional",
            "seat_limit": 10,
            "modules": ["odicm"],
            "federation_enabled": False,
            "mig_enabled": False,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=365)).isoformat(),
            "signature": ""
        }

    def test_get_expiration(self, valid_manifest):
        """Test getting expiration date."""
        offline = generate_offline_license(valid_manifest, ttl_days=30)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(offline, f)
            temp_file = f.name

        try:
            validator = OfflineLicenseValidator(temp_file)
            expiration = validator.get_expiration()

            assert expiration is not None
            assert expiration > datetime.now(timezone.utc)
        finally:
            os.unlink(temp_file)

    def test_get_days_until_expiration(self, valid_manifest):
        """Test getting days until expiration."""
        offline = generate_offline_license(valid_manifest, ttl_days=15)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(offline, f)
            temp_file = f.name

        try:
            validator = OfflineLicenseValidator(temp_file)
            days = validator.get_days_until_expiration()

            # Should be approximately 15 days (might be 14 due to timing)
            assert days is not None
            assert 13 <= days <= 15
        finally:
            os.unlink(temp_file)
