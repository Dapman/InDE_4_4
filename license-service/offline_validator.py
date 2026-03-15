"""
InDE License Service - Offline License Validator
Validates offline license files for air-gapped deployments.

Offline license files contain a signed entitlement manifest with a
time-bound expiration. This allows Professional tier customers
operating in air-gapped environments to validate licenses locally.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

from models import EntitlementManifest, OfflineLicense, LicenseTier
from crypto import verify_offline_license, is_offline_license_expired
from config import config


class OfflineLicenseValidator:
    """Validates and manages offline license files."""

    def __init__(self, license_file: Optional[str] = None):
        """
        Initialize the offline license validator.

        Args:
            license_file: Path to offline license file. Uses config default if not provided.
        """
        self.license_file = license_file or config.OFFLINE_LICENSE_FILE

    def has_offline_license(self) -> bool:
        """
        Check if an offline license file exists.

        Returns:
            True if file exists, False otherwise
        """
        return os.path.exists(self.license_file)

    def load_offline_license(self) -> Optional[dict]:
        """
        Load the offline license file.

        Returns:
            License data dictionary, or None if file doesn't exist or is invalid
        """
        if not self.has_offline_license():
            return None

        try:
            with open(self.license_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def validate(self) -> Tuple[bool, Optional[EntitlementManifest], Optional[str]]:
        """
        Validate the offline license file.

        Returns:
            Tuple of (is_valid, manifest, error_message)
            - is_valid: True if license is valid and not expired
            - manifest: EntitlementManifest if valid, None otherwise
            - error_message: Error description if invalid, None if valid
        """
        # Check if file exists
        if not self.has_offline_license():
            return (False, None, "No offline license file found")

        # Load license data
        license_data = self.load_offline_license()
        if not license_data:
            return (False, None, "Failed to read offline license file")

        # Verify signature
        if not verify_offline_license(license_data):
            return (False, None, "Offline license signature verification failed")

        # Check expiration
        if is_offline_license_expired(license_data):
            return (False, None, "Offline license has expired")

        # Extract and validate manifest
        manifest_data = license_data.get("manifest")
        if not manifest_data:
            return (False, None, "Offline license missing manifest")

        try:
            # Handle nested manifest if present
            if isinstance(manifest_data.get("manifest"), dict):
                manifest_data = manifest_data["manifest"]

            # Parse datetime fields
            issued_at = manifest_data.get("issued_at")
            expires_at = manifest_data.get("expires_at")

            if isinstance(issued_at, str):
                manifest_data["issued_at"] = datetime.fromisoformat(
                    issued_at.replace('Z', '+00:00')
                )
            if isinstance(expires_at, str):
                manifest_data["expires_at"] = datetime.fromisoformat(
                    expires_at.replace('Z', '+00:00')
                )

            # Parse tier
            tier_value = manifest_data.get("tier", "professional")
            if isinstance(tier_value, str):
                manifest_data["tier"] = LicenseTier(tier_value.lower())

            manifest = EntitlementManifest(**manifest_data)
            return (True, manifest, None)

        except Exception as e:
            return (False, None, f"Invalid manifest format: {str(e)}")

    def get_expiration(self) -> Optional[datetime]:
        """
        Get the expiration date of the offline license.

        Returns:
            Expiration datetime, or None if no license or invalid
        """
        license_data = self.load_offline_license()
        if not license_data:
            return None

        try:
            expires_at_str = license_data.get("expires_at")
            if expires_at_str:
                return datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        except Exception:
            pass

        return None

    def get_days_until_expiration(self) -> Optional[int]:
        """
        Get the number of days until the offline license expires.

        Returns:
            Days until expiration, or None if no license or invalid
        """
        expiration = self.get_expiration()
        if not expiration:
            return None

        now = datetime.now(timezone.utc)
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)

        delta = expiration - now
        return max(0, delta.days)


# Singleton instance
_offline_validator: Optional[OfflineLicenseValidator] = None


def get_offline_validator() -> OfflineLicenseValidator:
    """Get the singleton offline license validator instance."""
    global _offline_validator
    if _offline_validator is None:
        _offline_validator = OfflineLicenseValidator()
    return _offline_validator
