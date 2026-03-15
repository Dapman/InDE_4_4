"""
InDE License Service - Configuration
Environment-based configuration for license validation.
"""

import os
from typing import Optional


class LicenseConfig:
    """Configuration for the license service."""

    # Service version
    VERSION = "3.9.0"
    SERVICE_NAME = "inde-license"

    # License mode: "simulation" for local testing, "live" for production
    LICENSE_MODE: str = os.getenv("INDE_LICENSE_MODE", "simulation")

    # License server URL (only used in live mode)
    LICENSE_SERVER_URL: str = os.getenv(
        "INDE_LICENSE_SERVER_URL",
        "https://license.indeverse.com"
    )

    # License key from environment
    LICENSE_KEY: Optional[str] = os.getenv("INDEVERSE_LICENSE_KEY")

    # MongoDB connection for seat counting
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://inde-db:27017/inde")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "inde")

    # Data directory for caching
    DATA_DIR: str = os.getenv("INDE_LICENSE_DATA_DIR", "/data")

    # Cached manifest file path
    @property
    def CACHE_FILE(self) -> str:
        return os.path.join(self.DATA_DIR, "license_cache.json")

    # Grace state file path
    @property
    def GRACE_STATE_FILE(self) -> str:
        return os.path.join(self.DATA_DIR, "grace_state.json")

    # Offline license file path
    @property
    def OFFLINE_LICENSE_FILE(self) -> str:
        return os.path.join(self.DATA_DIR, "inde_license.json")

    # Re-validation interval (24 hours in seconds)
    REVALIDATION_INTERVAL_SECONDS: int = 86400

    # Grace period thresholds (in days)
    GRACE_QUIET_DAYS: int = 7
    GRACE_VISIBLE_DAYS: int = 21
    GRACE_URGENT_DAYS: int = 30

    # Seat counting settings
    SEAT_WINDOW_DAYS: int = 30  # Trailing window for active seat counting
    SEAT_OVERAGE_TOLERANCE: float = 0.10  # 10% overage tolerance

    # HMAC secret for signature verification
    # In production, this would be an asymmetric key pair
    HMAC_SECRET: str = os.getenv(
        "INDE_LICENSE_HMAC_SECRET",
        "inde-license-signing-secret-v3.9.0"  # Default for simulation mode
    )

    # Offline license validity period (days)
    OFFLINE_LICENSE_VALIDITY_DAYS: int = 90

    # API settings
    API_HOST: str = os.getenv("INDE_LICENSE_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("INDE_LICENSE_PORT", "8100"))

    # Logging
    LOG_LEVEL: str = os.getenv("INDE_LOG_LEVEL", "INFO")

    @classmethod
    def is_simulation_mode(cls) -> bool:
        """Check if running in simulation mode."""
        return cls.LICENSE_MODE.lower() == "simulation"

    @classmethod
    def is_disabled_mode(cls) -> bool:
        """Check if license validation is disabled (dev mode)."""
        return cls.LICENSE_MODE.lower() == "disabled"


# Singleton configuration instance
config = LicenseConfig()
