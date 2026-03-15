"""
InDE License Service - Entitlement Manager
Core license validation and entitlement enforcement.

Handles three flows:
1. Startup Validation - Initial license check on service start
2. Periodic Re-validation - 24-hour license refresh
3. Offline License File - Air-gapped deployment support
"""

import json
import os
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List

from models import (
    EntitlementManifest,
    LicenseStatus,
    LicenseTier,
    GracePeriodState,
    LicenseActivationResponse
)
from key_generator import validate_key_format, extract_tier, extract_customer_id
from crypto import sign_manifest, verify_manifest
from grace_period import get_grace_manager
from offline_validator import get_offline_validator
from seat_counter import get_seat_counter
from config import config


# Default modules for Professional tier
PROFESSIONAL_MODULES = [
    "odicm",
    "vision_formulator",
    "fear_extractor",
    "iml",
    "tim",
    "rve",
    "silr",
    "pitch_orchestrator",
    "innovation_validator",
    "ems",
    "biomimicry",
    "team_scaffolding",
    "rbac",
    "gii_foundation",
    "maturity_model",
    "activity_stream"
]


class EntitlementManager:
    """
    Manages license entitlements, validation, and caching.

    This is the heart of the license service, coordinating between:
    - Remote license server validation
    - Local manifest caching
    - Offline license files
    - Grace period management
    """

    def __init__(self):
        """Initialize the entitlement manager."""
        self._cached_manifest: Optional[EntitlementManifest] = None
        self._load_cached_manifest()

    def _load_cached_manifest(self) -> None:
        """Load cached manifest from disk if available."""
        try:
            if os.path.exists(config.CACHE_FILE):
                with open(config.CACHE_FILE, 'r') as f:
                    data = json.load(f)

                # Parse datetime fields
                data['issued_at'] = datetime.fromisoformat(
                    data['issued_at'].replace('Z', '+00:00')
                )
                data['expires_at'] = datetime.fromisoformat(
                    data['expires_at'].replace('Z', '+00:00')
                )
                data['tier'] = LicenseTier(data['tier'])

                self._cached_manifest = EntitlementManifest(**data)
        except Exception:
            self._cached_manifest = None

    def _save_cached_manifest(self, manifest: EntitlementManifest) -> None:
        """Save manifest to disk cache."""
        try:
            os.makedirs(os.path.dirname(config.CACHE_FILE), exist_ok=True)

            data = manifest.model_dump()
            data['issued_at'] = manifest.issued_at.isoformat()
            data['expires_at'] = manifest.expires_at.isoformat()
            data['tier'] = manifest.tier.value

            with open(config.CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            self._cached_manifest = manifest
        except Exception:
            pass

    def _generate_simulation_manifest(self, license_key: str) -> EntitlementManifest:
        """
        Generate a simulated entitlement manifest for testing.

        Args:
            license_key: License key to generate manifest for

        Returns:
            EntitlementManifest for simulation mode
        """
        tier_name = extract_tier(license_key) or "professional"
        customer_id = extract_customer_id(license_key) or "SIMULATION01"

        now = datetime.now(timezone.utc)

        manifest_data = {
            "license_key": license_key,
            "customer_id": customer_id,
            "customer_name": f"Simulation Customer ({customer_id})",
            "tier": LicenseTier(tier_name),
            "seat_limit": 10,
            "modules": PROFESSIONAL_MODULES.copy(),
            "federation_enabled": tier_name in ["enterprise", "federated"],
            "mig_enabled": tier_name == "enterprise",
            "issued_at": now,
            "expires_at": now + timedelta(days=365),
            "signature": ""
        }

        # Sign the manifest
        manifest_data["signature"] = sign_manifest(manifest_data)

        return EntitlementManifest(**manifest_data)

    async def _fetch_remote_manifest(self, license_key: str) -> Tuple[bool, Optional[EntitlementManifest], Optional[str]]:
        """
        Fetch entitlement manifest from remote license server.

        Args:
            license_key: License key to validate

        Returns:
            Tuple of (success, manifest, error_message)
        """
        if config.is_simulation_mode():
            # In simulation mode, generate a local manifest
            manifest = self._generate_simulation_manifest(license_key)
            return (True, manifest, None)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{config.LICENSE_SERVER_URL}/api/v1/validate",
                    json={"license_key": license_key}
                )

                if response.status_code == 200:
                    data = response.json()

                    # Verify signature
                    signature = data.get("signature", "")
                    if not verify_manifest(data, signature):
                        return (False, None, "Invalid manifest signature")

                    # Parse manifest
                    data['issued_at'] = datetime.fromisoformat(
                        data['issued_at'].replace('Z', '+00:00')
                    )
                    data['expires_at'] = datetime.fromisoformat(
                        data['expires_at'].replace('Z', '+00:00')
                    )
                    data['tier'] = LicenseTier(data['tier'])

                    manifest = EntitlementManifest(**data)
                    return (True, manifest, None)

                elif response.status_code == 401:
                    return (False, None, "Invalid license key")
                elif response.status_code == 403:
                    return (False, None, "License expired or revoked")
                else:
                    return (False, None, f"License server error: {response.status_code}")

        except httpx.TimeoutException:
            return (False, None, "License server timeout")
        except httpx.ConnectError:
            return (False, None, "Cannot connect to license server")
        except Exception as e:
            return (False, None, f"License validation error: {str(e)}")

    async def validate_license(self, license_key: Optional[str] = None) -> Tuple[bool, Optional[EntitlementManifest], Optional[str]]:
        """
        Validate a license key and return entitlements.

        Validation flow:
        1. Validate key format locally (checksum)
        2. Try to fetch from remote license server
        3. On network failure, check cached manifest
        4. On cache miss, check offline license file
        5. Apply grace period rules

        Args:
            license_key: License key to validate. Uses config key if not provided.

        Returns:
            Tuple of (is_valid, manifest, error_message)
        """
        grace_manager = get_grace_manager()

        # Use provided key or fall back to environment
        key = license_key or config.LICENSE_KEY

        if not key:
            return (False, None, "No license key configured")

        # Step 1: Validate key format locally
        if not validate_key_format(key):
            return (False, None, "Invalid license key format")

        # Step 2: Try remote validation
        success, manifest, error = await self._fetch_remote_manifest(key)

        if success and manifest:
            # Check if manifest is for the correct key
            if manifest.license_key.upper() != key.upper():
                return (False, None, "License key mismatch")

            # Check expiration
            now = datetime.now(timezone.utc)
            if manifest.expires_at < now:
                return (False, None, "License has expired")

            # Success - cache and record validation
            self._save_cached_manifest(manifest)
            grace_manager.record_successful_validation()
            return (True, manifest, None)

        # Step 3: Network failure - check cached manifest
        if self._cached_manifest and self._cached_manifest.license_key.upper() == key.upper():
            now = datetime.now(timezone.utc)
            if self._cached_manifest.expires_at > now:
                grace_manager.record_failed_validation()
                return (True, self._cached_manifest, "Using cached license (offline)")

        # Step 4: Check offline license file
        offline_validator = get_offline_validator()
        valid, offline_manifest, offline_error = offline_validator.validate()

        if valid and offline_manifest:
            if offline_manifest.license_key.upper() == key.upper():
                self._save_cached_manifest(offline_manifest)
                grace_manager.record_successful_validation()
                return (True, offline_manifest, "Using offline license file")

        # Step 5: No valid license found - check grace period
        if self._cached_manifest:
            grace_manager.record_failed_validation()
            if not grace_manager.is_read_only():
                return (True, self._cached_manifest, grace_manager.get_warning_message())
            else:
                return (False, self._cached_manifest, "Grace period expired - read-only mode")

        return (False, None, error or "License validation failed")

    async def activate_license(self, license_key: str) -> LicenseActivationResponse:
        """
        Activate a license key (first-time setup).

        Args:
            license_key: License key to activate

        Returns:
            LicenseActivationResponse with result
        """
        # Validate format first
        if not validate_key_format(license_key):
            return LicenseActivationResponse(
                success=False,
                message="Invalid license key format",
                error="The license key format is invalid. Please check for typos."
            )

        # Attempt validation
        success, manifest, error = await self.validate_license(license_key)

        if success and manifest:
            return LicenseActivationResponse(
                success=True,
                message=f"License activated successfully for {manifest.customer_name}",
                manifest=manifest
            )
        else:
            return LicenseActivationResponse(
                success=False,
                message="License activation failed",
                error=error
            )

    async def get_status(self) -> LicenseStatus:
        """
        Get current license status.

        Returns:
            LicenseStatus with current state
        """
        grace_manager = get_grace_manager()
        seat_counter = get_seat_counter()

        manifest = self._cached_manifest
        grace_state = grace_manager.get_current_state()
        days_offline = grace_manager.get_days_offline()

        if not manifest:
            return LicenseStatus(
                valid=False,
                grace_state=grace_state,
                days_offline=days_offline,
                warning_message="No license configured",
                read_only=grace_manager.is_read_only()
            )

        # Check expiration
        now = datetime.now(timezone.utc)
        days_until_expiry = (manifest.expires_at - now).days if manifest.expires_at > now else 0

        # Get seat count
        seats_used = await seat_counter.count_active_seats()

        return LicenseStatus(
            valid=True,
            tier=manifest.tier,
            customer_name=manifest.customer_name,
            seat_limit=manifest.seat_limit,
            seats_used=seats_used,
            grace_state=grace_state,
            days_until_expiry=days_until_expiry,
            days_offline=days_offline,
            expires_at=manifest.expires_at,
            last_validated=grace_manager.get_last_validation(),
            modules=manifest.modules,
            federation_enabled=manifest.federation_enabled,
            mig_enabled=manifest.mig_enabled,
            warning_message=grace_manager.get_warning_message(),
            read_only=grace_manager.is_read_only()
        )

    def get_cached_manifest(self) -> Optional[EntitlementManifest]:
        """Get the cached entitlement manifest."""
        return self._cached_manifest

    def is_module_enabled(self, module_name: str) -> bool:
        """
        Check if a module is enabled in the current license.

        Args:
            module_name: Name of the module to check

        Returns:
            True if module is enabled, False otherwise
        """
        if not self._cached_manifest:
            return False
        return module_name in self._cached_manifest.modules

    def get_enabled_modules(self) -> List[str]:
        """
        Get list of enabled modules.

        Returns:
            List of enabled module names
        """
        if not self._cached_manifest:
            return []
        return self._cached_manifest.modules.copy()


# Singleton instance
_entitlement_manager: Optional[EntitlementManager] = None


def get_entitlement_manager() -> EntitlementManager:
    """Get the singleton entitlement manager instance."""
    global _entitlement_manager
    if _entitlement_manager is None:
        _entitlement_manager = EntitlementManager()
    return _entitlement_manager
