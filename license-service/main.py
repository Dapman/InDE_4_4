"""
InDE License Service - FastAPI Application
Provides license validation, entitlement management, and seat counting.

Endpoints:
- GET  /health              - Health check for Docker
- POST /api/v1/validate     - Validate license key, return entitlements
- GET  /api/v1/status       - Current license status
- POST /api/v1/activate     - First-time license activation
- GET  /api/v1/seats        - Current seat count and compliance
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from models import (
    HealthResponse,
    LicenseStatus,
    LicenseActivationRequest,
    LicenseActivationResponse,
    SeatCompliance,
    GracePeriodState
)
from config import config
from entitlement_manager import get_entitlement_manager, EntitlementManager
from grace_period import get_grace_manager, GracePeriodManager
from seat_counter import get_seat_counter, SeatCounter


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    logger.info(f"Starting InDE License Service v{config.VERSION}")
    logger.info(f"License mode: {config.LICENSE_MODE}")

    # Perform initial license validation if key is configured
    if config.LICENSE_KEY:
        manager = get_entitlement_manager()
        success, manifest, error = await manager.validate_license()
        if success:
            logger.info(f"License validated: {manifest.customer_name} ({manifest.tier.value})")
        else:
            logger.warning(f"License validation failed: {error}")
    else:
        logger.warning("No license key configured")

    yield

    # Cleanup
    seat_counter = get_seat_counter()
    await seat_counter.close()
    logger.info("License service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="InDE License Service",
    description="License validation and entitlement management for InDE",
    version=config.VERSION,
    lifespan=lifespan
)

# Add CORS middleware for internal communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Internal service, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
def get_manager() -> EntitlementManager:
    """Dependency to get entitlement manager."""
    return get_entitlement_manager()


def get_grace() -> GracePeriodManager:
    """Dependency to get grace period manager."""
    return get_grace_manager()


def get_seats() -> SeatCounter:
    """Dependency to get seat counter."""
    return get_seat_counter()


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    manager: EntitlementManager = Depends(get_manager),
    grace: GracePeriodManager = Depends(get_grace)
) -> HealthResponse:
    """
    Health check endpoint for Docker health monitoring.

    Returns service health status including license validation state.
    """
    manifest = manager.get_cached_manifest()
    grace_state = grace.get_current_state()

    return HealthResponse(
        status="healthy",
        service=config.SERVICE_NAME,
        version=config.VERSION,
        license_valid=manifest is not None,
        grace_state=grace_state
    )


# =============================================================================
# License Validation
# =============================================================================

@app.post("/api/v1/validate", response_model=LicenseStatus, tags=["License"])
async def validate_license(
    request: Optional[LicenseActivationRequest] = None,
    manager: EntitlementManager = Depends(get_manager)
) -> LicenseStatus:
    """
    Validate a license key and return current entitlements.

    If no license key is provided in the request, uses the configured
    environment variable.

    Called by inde-app on startup for license verification.
    """
    license_key = request.license_key if request else None

    success, manifest, error = await manager.validate_license(license_key)

    if not success:
        # Return status with error info rather than raising exception
        return await manager.get_status()

    return await manager.get_status()


@app.post("/api/v1/activate", response_model=LicenseActivationResponse, tags=["License"])
async def activate_license(
    request: LicenseActivationRequest,
    manager: EntitlementManager = Depends(get_manager)
) -> LicenseActivationResponse:
    """
    Activate a license key for first-time setup.

    This endpoint is called by the React setup wizard during initial
    deployment configuration.
    """
    return await manager.activate_license(request.license_key)


@app.get("/api/v1/status", response_model=LicenseStatus, tags=["License"])
async def get_license_status(
    manager: EntitlementManager = Depends(get_manager)
) -> LicenseStatus:
    """
    Get current license status.

    Returns tier, seat usage, grace period state, expiration date,
    and warning messages. Called periodically by inde-app and the
    React admin panel.
    """
    return await manager.get_status()


# =============================================================================
# Seat Management
# =============================================================================

@app.get("/api/v1/seats", response_model=SeatCompliance, tags=["Seats"])
async def get_seat_status(
    manager: EntitlementManager = Depends(get_manager),
    seats: SeatCounter = Depends(get_seats)
) -> SeatCompliance:
    """
    Get current seat usage and compliance status.

    Returns active seat count, limit, and whether usage is within
    the licensed limit (with 10% tolerance).
    """
    manifest = manager.get_cached_manifest()

    if not manifest:
        raise HTTPException(
            status_code=503,
            detail="No license configured"
        )

    return await seats.check_seat_compliance(manifest.seat_limit)


@app.get("/api/v1/seats/details", tags=["Seats"])
async def get_seat_details(
    manager: EntitlementManager = Depends(get_manager),
    seats: SeatCounter = Depends(get_seats)
) -> dict:
    """
    Get detailed seat usage information.

    Includes usage percentage, available seats, compliance status,
    and window configuration.
    """
    manifest = manager.get_cached_manifest()

    if not manifest:
        raise HTTPException(
            status_code=503,
            detail="No license configured"
        )

    return await seats.get_seat_details(manifest.seat_limit)


# =============================================================================
# Module Entitlements
# =============================================================================

@app.get("/api/v1/modules", tags=["Entitlements"])
async def get_enabled_modules(
    manager: EntitlementManager = Depends(get_manager)
) -> dict:
    """
    Get list of modules enabled by the current license.

    Used by inde-app to determine feature availability.
    """
    manifest = manager.get_cached_manifest()

    if not manifest:
        return {
            "modules": [],
            "federation_enabled": False,
            "mig_enabled": False
        }

    return {
        "modules": manifest.modules,
        "federation_enabled": manifest.federation_enabled,
        "mig_enabled": manifest.mig_enabled
    }


@app.get("/api/v1/modules/{module_name}", tags=["Entitlements"])
async def check_module_enabled(
    module_name: str,
    manager: EntitlementManager = Depends(get_manager)
) -> dict:
    """
    Check if a specific module is enabled.

    Args:
        module_name: Name of the module to check

    Returns:
        Dictionary with enabled status
    """
    return {
        "module": module_name,
        "enabled": manager.is_module_enabled(module_name)
    }


# =============================================================================
# Grace Period Information
# =============================================================================

@app.get("/api/v1/grace", tags=["Grace Period"])
async def get_grace_status(
    grace: GracePeriodManager = Depends(get_grace)
) -> dict:
    """
    Get current grace period status.

    Returns state, days offline, and any warning messages.
    """
    return {
        "state": grace.get_current_state().value,
        "days_offline": grace.get_days_offline(),
        "is_read_only": grace.is_read_only(),
        "warning_message": grace.get_warning_message(),
        "last_validation": grace.get_last_validation().isoformat() if grace.get_last_validation() else None
    }


# =============================================================================
# Development/Testing Endpoints (only in simulation mode)
# =============================================================================

if config.is_simulation_mode():
    from key_generator import generate_license_key

    @app.post("/api/v1/dev/generate-key", tags=["Development"])
    async def dev_generate_key(tier: str = "professional") -> dict:
        """
        Generate a test license key (simulation mode only).

        Args:
            tier: License tier (professional, enterprise, federated)
        """
        key = generate_license_key(tier)
        return {
            "license_key": key,
            "tier": tier,
            "note": "This is a simulation key for testing"
        }

    @app.post("/api/v1/dev/reset-grace", tags=["Development"])
    async def dev_reset_grace(
        grace: GracePeriodManager = Depends(get_grace)
    ) -> dict:
        """Reset grace period state (simulation mode only)."""
        grace.reset()
        return {"message": "Grace period reset"}


# =============================================================================
# Run server (for local development)
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )
