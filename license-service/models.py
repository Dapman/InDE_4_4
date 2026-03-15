"""
InDE License Service - Pydantic Models
Defines data structures for license management.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LicenseTier(str, Enum):
    """License tier levels."""
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    FEDERATED = "federated"


class GracePeriodState(str, Enum):
    """Grace period states for license validation."""
    ACTIVE = "active"               # License validated, all good
    GRACE_QUIET = "grace_quiet"     # Days 1-7 offline, admin warning only
    GRACE_VISIBLE = "grace_visible" # Days 8-21 offline, admin banner
    GRACE_URGENT = "grace_urgent"   # Days 22-30 offline, all-user banner
    EXPIRED = "expired"             # Day 31+, read-only mode


class EntitlementManifest(BaseModel):
    """
    Signed entitlement manifest returned by the license server.
    Contains everything needed for local entitlement enforcement.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    license_key: str
    customer_id: str
    customer_name: str
    tier: LicenseTier
    seat_limit: int
    modules: List[str]
    federation_enabled: bool = False
    mig_enabled: bool = False
    issued_at: datetime
    expires_at: datetime
    signature: str


class LicenseStatus(BaseModel):
    """Current license status for API responses."""
    model_config = ConfigDict(str_strip_whitespace=True)

    valid: bool
    tier: Optional[LicenseTier] = None
    customer_name: Optional[str] = None
    seat_limit: Optional[int] = None
    seats_used: int = 0
    grace_state: GracePeriodState = GracePeriodState.ACTIVE
    days_until_expiry: Optional[int] = None
    days_offline: int = 0
    expires_at: Optional[datetime] = None
    last_validated: Optional[datetime] = None
    modules: List[str] = Field(default_factory=list)
    federation_enabled: bool = False
    mig_enabled: bool = False
    warning_message: Optional[str] = None
    read_only: bool = False


class SeatCompliance(BaseModel):
    """Seat usage compliance status."""
    model_config = ConfigDict(str_strip_whitespace=True)

    active_seats: int
    seat_limit: int
    compliant: bool
    overage_percentage: float = 0.0
    warning: bool = False
    violation: bool = False


class LicenseActivationRequest(BaseModel):
    """Request to activate a license key."""
    model_config = ConfigDict(str_strip_whitespace=True)

    license_key: str


class LicenseActivationResponse(BaseModel):
    """Response from license activation."""
    model_config = ConfigDict(str_strip_whitespace=True)

    success: bool
    message: str
    manifest: Optional[EntitlementManifest] = None
    error: Optional[str] = None


class GraceState(BaseModel):
    """Persisted grace period state."""
    model_config = ConfigDict(str_strip_whitespace=True)

    last_successful_validation: Optional[datetime] = None
    offline_since: Optional[datetime] = None
    current_state: GracePeriodState = GracePeriodState.ACTIVE


class OfflineLicense(BaseModel):
    """Offline license file structure for air-gapped deployments."""
    model_config = ConfigDict(str_strip_whitespace=True)

    manifest: EntitlementManifest
    generated_at: datetime
    expires_at: datetime
    signature: str


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str = "healthy"
    service: str = "inde-license"
    version: str = "3.8.0"
    license_valid: bool = False
    grace_state: GracePeriodState = GracePeriodState.ACTIVE
