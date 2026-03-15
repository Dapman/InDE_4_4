"""
Tests for InDE License Cryptographic Utilities.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone, timedelta

from crypto import (
    sign_manifest,
    verify_manifest,
    generate_offline_license,
    verify_offline_license,
    is_offline_license_expired
)


class TestManifestSigning:
    """Test manifest signing and verification."""

    @pytest.fixture
    def sample_manifest(self):
        """Create a sample manifest for testing."""
        return {
            "license_key": "INDE-PRO-TESTCUST0001-ABCD",
            "customer_id": "TESTCUST0001",
            "customer_name": "Test Customer",
            "tier": "professional",
            "seat_limit": 10,
            "modules": ["odicm", "tim", "rve"],
            "federation_enabled": False,
            "mig_enabled": False,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        }

    def test_sign_manifest_returns_string(self, sample_manifest):
        """Test that signing returns a base64 string."""
        signature = sign_manifest(sample_manifest)
        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_verify_valid_signature(self, sample_manifest):
        """Test verifying a valid signature."""
        signature = sign_manifest(sample_manifest)
        assert verify_manifest(sample_manifest, signature) is True

    def test_reject_invalid_signature(self, sample_manifest):
        """Test rejecting an invalid signature."""
        assert verify_manifest(sample_manifest, "invalid_signature") is False

    def test_reject_tampered_manifest(self, sample_manifest):
        """Test rejecting a tampered manifest."""
        signature = sign_manifest(sample_manifest)
        sample_manifest["seat_limit"] = 999  # Tamper
        assert verify_manifest(sample_manifest, signature) is False

    def test_signing_is_deterministic(self, sample_manifest):
        """Test that signing the same data produces the same signature."""
        sig1 = sign_manifest(sample_manifest)
        sig2 = sign_manifest(sample_manifest)
        assert sig1 == sig2

    def test_different_secrets_produce_different_signatures(self, sample_manifest):
        """Test that different secrets produce different signatures."""
        sig1 = sign_manifest(sample_manifest, "secret1")
        sig2 = sign_manifest(sample_manifest, "secret2")
        assert sig1 != sig2


class TestOfflineLicense:
    """Test offline license generation and validation."""

    @pytest.fixture
    def sample_manifest(self):
        """Create a sample manifest for testing."""
        return {
            "license_key": "INDE-PRO-TESTCUST0001-ABCD",
            "customer_id": "TESTCUST0001",
            "customer_name": "Test Customer",
            "tier": "professional",
            "seat_limit": 10,
            "modules": ["odicm", "tim", "rve"],
            "federation_enabled": False,
            "mig_enabled": False,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "signature": "original_sig"
        }

    def test_generate_offline_license(self, sample_manifest):
        """Test generating an offline license."""
        offline = generate_offline_license(sample_manifest)
        assert "manifest" in offline
        assert "generated_at" in offline
        assert "expires_at" in offline
        assert "signature" in offline

    def test_verify_valid_offline_license(self, sample_manifest):
        """Test verifying a valid offline license."""
        offline = generate_offline_license(sample_manifest, ttl_days=30)
        assert verify_offline_license(offline) is True

    def test_reject_tampered_offline_license(self, sample_manifest):
        """Test rejecting a tampered offline license."""
        offline = generate_offline_license(sample_manifest)
        offline["manifest"]["seat_limit"] = 999  # Tamper
        assert verify_offline_license(offline) is False

    def test_reject_expired_offline_license(self, sample_manifest):
        """Test rejecting an expired offline license."""
        # Generate with negative TTL to create expired license
        now = datetime.now(timezone.utc)
        offline = {
            "manifest": sample_manifest,
            "generated_at": (now - timedelta(days=100)).isoformat(),
            "expires_at": (now - timedelta(days=10)).isoformat()
        }
        offline["signature"] = sign_manifest(offline)
        assert is_offline_license_expired(offline) is True

    def test_not_expired_offline_license(self, sample_manifest):
        """Test that valid offline license is not expired."""
        offline = generate_offline_license(sample_manifest, ttl_days=30)
        assert is_offline_license_expired(offline) is False

    def test_custom_ttl(self, sample_manifest):
        """Test offline license with custom TTL."""
        offline = generate_offline_license(sample_manifest, ttl_days=7)

        generated = datetime.fromisoformat(offline["generated_at"].replace('Z', '+00:00'))
        expires = datetime.fromisoformat(offline["expires_at"].replace('Z', '+00:00'))

        delta = expires - generated
        assert delta.days == 7
