"""
Tests for InDE License Key Generator.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from key_generator import (
    generate_license_key,
    validate_key_format,
    parse_license_key,
    extract_tier,
    extract_customer_id,
    generate_customer_id,
    TIER_CODES
)


class TestKeyGeneration:
    """Test license key generation."""

    def test_generate_professional_key(self):
        """Test generating a professional tier key."""
        key = generate_license_key("professional")
        assert key.startswith("INDE-PRO-")
        assert len(key) == 26  # INDE-PRO-XXXXXXXXXXXX-XXXX (4+1+3+1+12+1+4)

    def test_generate_enterprise_key(self):
        """Test generating an enterprise tier key."""
        key = generate_license_key("enterprise")
        assert key.startswith("INDE-ENT-")

    def test_generate_federated_key(self):
        """Test generating a federated tier key."""
        key = generate_license_key("federated")
        assert key.startswith("INDE-FED-")

    def test_generate_with_tier_code(self):
        """Test generating with tier code instead of name."""
        key = generate_license_key("PRO")
        assert key.startswith("INDE-PRO-")

    def test_generate_with_custom_customer_id(self):
        """Test generating with custom customer ID."""
        key = generate_license_key("professional", "TESTCUST0001")
        assert "TESTCUST0001" in key

    def test_invalid_tier_raises_error(self):
        """Test that invalid tier raises ValueError."""
        with pytest.raises(ValueError):
            generate_license_key("invalid_tier")

    def test_invalid_customer_id_raises_error(self):
        """Test that invalid customer ID raises ValueError."""
        with pytest.raises(ValueError):
            generate_license_key("professional", "short")

    def test_generate_customer_id(self):
        """Test customer ID generation."""
        cid = generate_customer_id()
        assert len(cid) == 12
        assert cid.isalnum()
        assert cid.isupper()


class TestKeyValidation:
    """Test license key format validation."""

    def test_valid_key_passes(self):
        """Test that a valid key passes validation."""
        key = generate_license_key("professional")
        assert validate_key_format(key) is True

    def test_invalid_format_fails(self):
        """Test that invalid format fails validation."""
        assert validate_key_format("INVALID-KEY") is False
        assert validate_key_format("INDE-XXX-123456789012-ABCD") is False
        assert validate_key_format("") is False
        assert validate_key_format(None) is False

    def test_wrong_checksum_fails(self):
        """Test that wrong checksum fails validation."""
        key = generate_license_key("professional")
        # Tamper with checksum
        tampered = key[:-4] + "0000"
        assert validate_key_format(tampered) is False

    def test_case_insensitive(self):
        """Test that validation is case insensitive."""
        key = generate_license_key("professional")
        assert validate_key_format(key.lower()) is True
        assert validate_key_format(key.upper()) is True


class TestKeyParsing:
    """Test license key parsing."""

    def test_parse_valid_key(self):
        """Test parsing a valid key."""
        key = generate_license_key("professional", "ABCDEF123456")
        result = parse_license_key(key)
        assert result is not None
        tier_code, customer_id, checksum = result
        assert tier_code == "PRO"
        assert customer_id == "ABCDEF123456"
        assert len(checksum) == 4

    def test_parse_invalid_key(self):
        """Test parsing an invalid key returns None."""
        assert parse_license_key("INVALID") is None

    def test_extract_tier(self):
        """Test tier extraction."""
        key = generate_license_key("enterprise")
        assert extract_tier(key) == "enterprise"

    def test_extract_customer_id(self):
        """Test customer ID extraction."""
        key = generate_license_key("professional", "TESTCUST0001")
        assert extract_customer_id(key) == "TESTCUST0001"


class TestAllTiers:
    """Test all tier codes are valid."""

    @pytest.mark.parametrize("tier_code", TIER_CODES.keys())
    def test_tier_code_generates_valid_key(self, tier_code):
        """Test each tier code generates a valid key."""
        key = generate_license_key(tier_code)
        assert validate_key_format(key)
        assert tier_code in key

    @pytest.mark.parametrize("tier_name", TIER_CODES.values())
    def test_tier_name_generates_valid_key(self, tier_name):
        """Test each tier name generates a valid key."""
        key = generate_license_key(tier_name)
        assert validate_key_format(key)
