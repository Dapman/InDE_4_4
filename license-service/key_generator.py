"""
InDE License Service - Key Generator
License key generation and validation.

Key format: INDE-{TIER}-{CUSTOMER_ID}-{CHECKSUM}
- TIER: PRO | ENT | FED
- CUSTOMER_ID: 12 alphanumeric characters (uppercase + digits)
- CHECKSUM: 4 character CRC32 suffix of the key body
"""

import re
import zlib
import secrets
import string
from typing import Optional, Tuple


# Valid tier codes
TIER_CODES = {
    "PRO": "professional",
    "ENT": "enterprise",
    "FED": "federated"
}

# Reverse mapping for tier to code
TIER_TO_CODE = {v: k for k, v in TIER_CODES.items()}

# Key format pattern
KEY_PATTERN = re.compile(r'^INDE-(PRO|ENT|FED)-([A-Z0-9]{12})-([A-F0-9]{4})$')

# Customer ID characters (uppercase alphanumeric)
CUSTOMER_ID_CHARS = string.ascii_uppercase + string.digits


def _calculate_checksum(key_body: str) -> str:
    """
    Calculate 4-character CRC32 checksum of the key body.

    Args:
        key_body: The key without checksum (e.g., "INDE-PRO-A7X9K2M4P1B3")

    Returns:
        4-character uppercase hex checksum
    """
    crc = zlib.crc32(key_body.encode('utf-8')) & 0xFFFFFFFF
    return format(crc % 0xFFFF, '04X')


def generate_customer_id() -> str:
    """
    Generate a random 12-character customer ID.

    Returns:
        12-character uppercase alphanumeric string
    """
    return ''.join(secrets.choice(CUSTOMER_ID_CHARS) for _ in range(12))


def generate_license_key(tier: str, customer_id: Optional[str] = None) -> str:
    """
    Generate a new license key.

    Args:
        tier: License tier ("professional", "enterprise", "federated") or
              tier code ("PRO", "ENT", "FED")
        customer_id: Optional 12-character customer ID. Generated if not provided.

    Returns:
        Complete license key in format INDE-{TIER}-{CUSTOMER_ID}-{CHECKSUM}

    Raises:
        ValueError: If tier is invalid or customer_id has wrong format
    """
    # Normalize tier to code
    tier_upper = tier.upper()
    if tier_upper in TIER_CODES:
        tier_code = tier_upper
    elif tier.lower() in TIER_TO_CODE:
        tier_code = TIER_TO_CODE[tier.lower()]
    else:
        raise ValueError(f"Invalid tier: {tier}. Must be one of {list(TIER_CODES.keys())}")

    # Generate or validate customer ID
    if customer_id is None:
        customer_id = generate_customer_id()
    else:
        customer_id = customer_id.upper()
        if len(customer_id) != 12 or not all(c in CUSTOMER_ID_CHARS for c in customer_id):
            raise ValueError(
                f"Invalid customer_id: must be 12 uppercase alphanumeric characters"
            )

    # Build key body and checksum
    key_body = f"INDE-{tier_code}-{customer_id}"
    checksum = _calculate_checksum(key_body)

    return f"{key_body}-{checksum}"


def validate_key_format(key: str) -> bool:
    """
    Validate license key format and checksum.
    This is a structural validation only - does not verify with license server.

    Args:
        key: License key to validate

    Returns:
        True if key has valid format and checksum, False otherwise
    """
    if not key:
        return False

    # Check pattern match
    match = KEY_PATTERN.match(key.upper())
    if not match:
        return False

    # Extract components
    tier_code, customer_id, provided_checksum = match.groups()

    # Verify checksum
    key_body = f"INDE-{tier_code}-{customer_id}"
    expected_checksum = _calculate_checksum(key_body)

    return provided_checksum == expected_checksum


def parse_license_key(key: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a license key into its components.

    Args:
        key: License key to parse

    Returns:
        Tuple of (tier_code, customer_id, checksum) if valid, None otherwise
    """
    if not validate_key_format(key):
        return None

    match = KEY_PATTERN.match(key.upper())
    if not match:
        return None

    return match.groups()


def extract_tier(key: str) -> Optional[str]:
    """
    Extract the tier name from a license key.

    Args:
        key: License key

    Returns:
        Tier name (e.g., "professional") or None if invalid
    """
    parsed = parse_license_key(key)
    if not parsed:
        return None

    tier_code, _, _ = parsed
    return TIER_CODES.get(tier_code)


def extract_customer_id(key: str) -> Optional[str]:
    """
    Extract the customer ID from a license key.

    Args:
        key: License key

    Returns:
        Customer ID or None if invalid
    """
    parsed = parse_license_key(key)
    if not parsed:
        return None

    _, customer_id, _ = parsed
    return customer_id
