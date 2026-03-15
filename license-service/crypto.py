"""
InDE License Service - Cryptographic Utilities
HMAC-SHA256 for manifest signature generation and verification.

For MVP: Uses a symmetric HMAC secret embedded in the license service.
For production: Migrate to asymmetric RSA/Ed25519 signatures.
"""

import hmac
import hashlib
import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from config import config


def _get_canonical_json(data: Dict[str, Any]) -> str:
    """
    Convert a dictionary to canonical JSON for signing.
    Uses sorted keys and no whitespace for deterministic output.

    Args:
        data: Dictionary to serialize

    Returns:
        Canonical JSON string
    """
    return json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)


def sign_manifest(manifest_data: Dict[str, Any], secret: Optional[str] = None) -> str:
    """
    Sign an entitlement manifest using HMAC-SHA256.

    Args:
        manifest_data: Manifest data without signature
        secret: Optional HMAC secret. Uses config secret if not provided.

    Returns:
        Base64-encoded HMAC-SHA256 signature
    """
    if secret is None:
        secret = config.HMAC_SECRET

    # Remove signature field if present for signing
    data_to_sign = {k: v for k, v in manifest_data.items() if k != 'signature'}
    canonical = _get_canonical_json(data_to_sign)

    signature = hmac.new(
        secret.encode('utf-8'),
        canonical.encode('utf-8'),
        hashlib.sha256
    ).digest()

    return base64.b64encode(signature).decode('utf-8')


def verify_manifest(
    manifest_data: Dict[str, Any],
    signature: str,
    secret: Optional[str] = None
) -> bool:
    """
    Verify an entitlement manifest signature.

    Args:
        manifest_data: Manifest data (may include signature field)
        signature: Base64-encoded signature to verify
        secret: Optional HMAC secret. Uses config secret if not provided.

    Returns:
        True if signature is valid, False otherwise
    """
    if secret is None:
        secret = config.HMAC_SECRET

    try:
        expected_signature = sign_manifest(manifest_data, secret)
        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


def generate_offline_license(
    manifest_data: Dict[str, Any],
    secret: Optional[str] = None,
    ttl_days: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate an offline license file from an entitlement manifest.

    Args:
        manifest_data: Entitlement manifest
        secret: Optional HMAC secret
        ttl_days: Days until expiration. Uses config default if not provided.

    Returns:
        Offline license dictionary with manifest, timestamps, and signature
    """
    if secret is None:
        secret = config.HMAC_SECRET
    if ttl_days is None:
        ttl_days = config.OFFLINE_LICENSE_VALIDITY_DAYS

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=ttl_days)

    offline_license = {
        "manifest": manifest_data,
        "generated_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }

    # Sign the entire offline license (including manifest and timestamps)
    offline_license["signature"] = sign_manifest(offline_license, secret)

    return offline_license


def verify_offline_license(
    license_data: Dict[str, Any],
    secret: Optional[str] = None
) -> bool:
    """
    Verify an offline license file.

    Checks:
    1. Signature is valid
    2. License has not expired

    Args:
        license_data: Offline license dictionary
        secret: Optional HMAC secret

    Returns:
        True if license is valid and not expired, False otherwise
    """
    if secret is None:
        secret = config.HMAC_SECRET

    try:
        # Extract and verify signature
        signature = license_data.get("signature")
        if not signature:
            return False

        # Create data without signature for verification
        data_to_verify = {k: v for k, v in license_data.items() if k != 'signature'}

        if not verify_manifest(data_to_verify, signature, secret):
            return False

        # Check expiration
        expires_at_str = license_data.get("expires_at")
        if not expires_at_str:
            return False

        expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)

        return now < expires_at

    except Exception:
        return False


def is_offline_license_expired(license_data: Dict[str, Any]) -> bool:
    """
    Check if an offline license has expired.

    Args:
        license_data: Offline license dictionary

    Returns:
        True if expired, False if still valid
    """
    try:
        expires_at_str = license_data.get("expires_at")
        if not expires_at_str:
            return True

        expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)

        return now >= expires_at
    except Exception:
        return True
