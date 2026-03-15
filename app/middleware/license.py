"""
InDE v3.8 - License Validation Middleware
Validates license status and enforces entitlements.

This middleware:
1. Checks license status on startup and caches it
2. Re-validates every 24 hours via background task
3. Enforces read-only mode when grace period expires
4. Detects first-run state for setup wizard redirection
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from functools import wraps

import httpx
from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("inde.license")

# =============================================================================
# Configuration
# =============================================================================

LICENSE_SERVICE_URL = os.getenv("LICENSE_SERVICE_URL", "http://inde-license:8100")
LICENSE_MODE = os.getenv("INDE_LICENSE_MODE", "simulation")
CACHE_TTL_SECONDS = 300  # Cache status for 5 minutes

# =============================================================================
# License Status Cache
# =============================================================================

_license_cache: Dict[str, Any] = {
    "status": None,
    "last_check": None,
    "first_run": None
}


async def _fetch_license_status() -> Dict[str, Any]:
    """Fetch license status from the license service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{LICENSE_SERVICE_URL}/api/v1/status")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"License service returned {response.status_code}")
                return {"valid": False, "error": f"Status {response.status_code}"}
    except httpx.ConnectError:
        logger.warning("Cannot connect to license service")
        return {"valid": False, "error": "Connection failed", "offline": True}
    except Exception as e:
        logger.error(f"License status fetch error: {e}")
        return {"valid": False, "error": str(e)}


async def get_license_status(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get current license status (cached).

    Args:
        force_refresh: If True, bypass cache and fetch fresh status

    Returns:
        License status dictionary
    """
    global _license_cache

    now = datetime.now(timezone.utc)

    # Check cache validity
    if not force_refresh and _license_cache["status"] is not None:
        last_check = _license_cache.get("last_check")
        if last_check and (now - last_check).total_seconds() < CACHE_TTL_SECONDS:
            return _license_cache["status"]

    # Fetch fresh status
    status = await _fetch_license_status()
    _license_cache["status"] = status
    _license_cache["last_check"] = now

    return status


async def is_first_run(db) -> bool:
    """
    Detect if this is a first-run deployment.

    Returns True if:
    - No organizations exist in the database
    - No users exist in the database
    """
    global _license_cache

    # Check cache
    if _license_cache.get("first_run") is not None:
        return _license_cache["first_run"]

    try:
        org_count = db.db.organizations.count_documents({})
        user_count = db.db.users.count_documents({})

        is_first = org_count == 0 and user_count == 0
        _license_cache["first_run"] = is_first

        if is_first:
            logger.info("First-run deployment detected")

        return is_first
    except Exception as e:
        logger.error(f"First-run detection error: {e}")
        return False


def clear_first_run_cache():
    """Clear the first-run cache after setup completes."""
    global _license_cache
    _license_cache["first_run"] = None


async def is_read_only_mode() -> bool:
    """
    Check if the system is in read-only mode due to license expiration.

    Returns:
        True if grace period has expired and system is read-only
    """
    status = await get_license_status()
    return status.get("read_only", False)


def require_write_access(func):
    """
    Decorator to enforce write access (blocks when in read-only mode).

    Use on routes that modify data (POST, PUT, DELETE).
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if await is_read_only_mode():
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "read_only_mode",
                    "message": (
                        "InDE is in read-only mode due to license grace period expiration. "
                        "Please renew your license to restore full functionality."
                    )
                }
            )
        return await func(*args, **kwargs)
    return wrapper


# =============================================================================
# License Middleware
# =============================================================================

class LicenseMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for license validation.

    On every request:
    1. If first-run and not accessing setup routes, indicate setup needed
    2. If read-only mode, block write operations
    3. Otherwise, pass through normally
    """

    # Routes that are always accessible (even without license)
    ALWAYS_ALLOWED = [
        "/health",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/system/info",
        "/api/system/license",
        "/api/system/first-run",
        "/api/auth/login",
        "/api/auth/register",
        "/setup",
        "/assets",
    ]

    # Routes accessible during first-run setup
    SETUP_ROUTES = [
        "/api/setup",
        "/api/license/activate",
        "/api/organizations",
        "/api/auth/register",
    ]

    # Write methods that require license
    WRITE_METHODS = ["POST", "PUT", "PATCH", "DELETE"]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Always allow certain routes
        if any(path.startswith(allowed) for allowed in self.ALWAYS_ALLOWED):
            return await call_next(request)

        # Check if disabled mode (development)
        if LICENSE_MODE.lower() == "disabled":
            return await call_next(request)

        # Get database from app state
        db = getattr(request.app.state, "db", None)

        # Check first-run status
        if db and await is_first_run(db):
            # Allow setup-related routes
            if any(path.startswith(route) for route in self.SETUP_ROUTES):
                return await call_next(request)

            # For all other routes during first-run, indicate setup needed
            # (React frontend will redirect to /setup)
            request.state.first_run = True

        # Check read-only mode for write operations
        if request.method in self.WRITE_METHODS:
            if await is_read_only_mode():
                # Allow read-only exceptions
                if self._is_read_only_exception(path):
                    return await call_next(request)

                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "read_only_mode",
                        "message": (
                            "InDE is in read-only mode. "
                            "Please renew your license to restore write access."
                        ),
                        "renewal_url": "https://indeverse.com/renew"
                    }
                )

        return await call_next(request)

    def _is_read_only_exception(self, path: str) -> bool:
        """
        Check if a path is exempt from read-only mode restrictions.

        Allowed in read-only:
        - Export endpoints (innovators can always export their data)
        - Admin panel access
        - License renewal endpoints
        """
        readonly_exceptions = [
            "/api/exports",
            "/api/reports/export",
            "/api/artifacts/export",
            "/api/license",
            "/api/system",
        ]
        return any(path.startswith(exc) for exc in readonly_exceptions)


# =============================================================================
# License Status API Functions
# =============================================================================

async def validate_license_on_startup(db) -> Dict[str, Any]:
    """
    Validate license on application startup.

    Called from main.py lifespan handler.
    """
    logger.info("Validating license on startup...")

    # Check first-run
    first_run = await is_first_run(db)
    if first_run:
        logger.info("First-run deployment - awaiting setup")
        return {"status": "first_run", "setup_required": True}

    # Get license status
    status = await get_license_status(force_refresh=True)

    if status.get("valid"):
        tier = status.get("tier", "unknown")
        logger.info(f"License valid: {tier} tier")
    elif status.get("offline"):
        logger.warning("License service offline - operating in cached mode")
    else:
        error = status.get("error", "Unknown error")
        logger.warning(f"License validation issue: {error}")

    return status


async def get_license_info_for_frontend() -> Dict[str, Any]:
    """
    Get license information formatted for the React frontend.

    Returns a sanitized subset of license status safe for client display.
    """
    status = await get_license_status()

    return {
        "valid": status.get("valid", False),
        "tier": status.get("tier"),
        "seats_used": status.get("seats_used", 0),
        "seat_limit": status.get("seat_limit", 0),
        "expires_at": status.get("expires_at"),
        "days_until_expiry": status.get("days_until_expiry"),
        "grace_state": status.get("grace_state"),
        "read_only": status.get("read_only", False),
        "warning_message": status.get("warning_message"),
        "modules": status.get("modules", []),
        "federation_enabled": status.get("federation_enabled", False)
    }
