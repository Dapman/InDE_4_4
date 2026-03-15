"""
InDE v3.14 - System API Routes
System information, license status, LLM provider status, diagnostics, and administration endpoints.

v3.14 adds:
- Diagnostics endpoint for system health monitoring (admin-only)

v3.9 adds:
- LLM provider status endpoint for admin panel
- Provider chain visibility
- Failover history
"""

import httpx
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel

from auth.middleware import get_current_user, require_maturity_level
from core.config import VERSION, VERSION_NAME, COLLECTIONS, LLM_GATEWAY_URL
from shared.display_labels import DisplayLabels
from middleware.license import (
    get_license_status,
    is_first_run,
    get_license_info_for_frontend,
    clear_first_run_cache
)
from modules.diagnostics import get_diagnostics

router = APIRouter()


@router.get("/info")
async def get_system_info():
    """
    Get system information (public endpoint).
    """
    return {
        "name": "InDE API",
        "version": VERSION,
        "version_name": VERSION_NAME,
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/stats")
async def get_system_stats(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get system statistics (authenticated).
    """
    db = request.app.state.db

    # User-specific stats
    user_pursuits = db.db.pursuits.count_documents({"user_id": user["user_id"]})
    user_artifacts = db.db.artifacts.count_documents({"user_id": user["user_id"]})

    return {
        "user_stats": {
            "pursuits": user_pursuits,
            "artifacts": user_artifacts
        },
        "collections": len(COLLECTIONS),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/config")
async def get_user_config(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get user-specific configuration.
    """
    db = request.app.state.db

    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user["user_id"],
        "maturity_level": user_doc.get("maturity_level", "NOVICE"),
        "preferences": user_doc.get("preferences", {}),
        "gii_id": user_doc.get("gii_id"),
        "organization_id": user_doc.get("organization_id")
    }


class UpdateConfigRequest(BaseModel):
    """Request body for updating user config."""
    preferences: dict


@router.patch("/config")
async def update_user_config(
    request: Request,
    data: UpdateConfigRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update user preferences.
    """
    db = request.app.state.db

    # Merge with existing preferences instead of overwriting
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    current_prefs = user_doc.get("preferences", {}) if user_doc else {}
    merged_prefs = {**current_prefs, **data.preferences}

    db.db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"preferences": merged_prefs}}
    )

    return {"message": "Preferences updated", "preferences": merged_prefs}


@router.get("/display-labels")
async def get_display_labels():
    """
    Return all Display Labels organized by category.

    This endpoint is used by the React frontend to fetch all labels at startup
    and cache them for the session lifetime. Labels translate internal identifiers
    to human-readable text for innovator-facing display.

    Response format:
    {
        "observation_type": {
            "ARTIFACT_CREATED": {"label": "Created an Artifact", "icon": "📄", "description": "..."},
            ...
        },
        ...
    }
    """
    return DisplayLabels.get_all_categories()


# =============================================================================
# v3.8: License Status Endpoints
# =============================================================================

@router.get("/health")
async def system_health():
    """
    System health check endpoint.

    Returns basic health status including license validation state.
    Used by Docker health checks and monitoring systems.
    """
    license_status = await get_license_status()

    return {
        "status": "healthy",
        "version": VERSION,
        "version_name": VERSION_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "license_valid": license_status.get("valid", False),
        "license_tier": license_status.get("tier"),
        "read_only": license_status.get("read_only", False)
    }


@router.get("/license")
async def get_license_info(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get current license status (authenticated, admin-accessible).

    Returns license tier, seat usage, grace period state, and warnings.
    Only accessible to authenticated users; full details for admins.
    """
    license_info = await get_license_info_for_frontend()

    # Add admin-only fields if user has admin role
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    if user_doc and user_doc.get("role") == "admin":
        full_status = await get_license_status()
        license_info["last_validated"] = full_status.get("last_validated")
        license_info["days_offline"] = full_status.get("days_offline", 0)

    return license_info


@router.get("/first-run")
async def check_first_run(request: Request):
    """
    Check if this is a first-run deployment requiring setup.

    Returns setup_required: true if no organizations or users exist.
    Used by React frontend to decide whether to show setup wizard.
    """
    db = request.app.state.db

    if db is None:
        return {"setup_required": False, "error": "Database not available"}

    first_run = await is_first_run(db)

    return {
        "setup_required": first_run,
        "version": VERSION,
        "version_name": VERSION_NAME
    }


@router.post("/setup-complete")
async def mark_setup_complete(request: Request):
    """
    Mark first-run setup as complete.

    Called by the setup wizard after successful configuration.
    Clears the first-run cache so subsequent requests don't trigger setup.
    """
    clear_first_run_cache()

    return {
        "success": True,
        "message": "Setup marked as complete"
    }


# =============================================================================
# v3.9: LLM Provider Status Endpoints
# =============================================================================

@router.get("/llm/providers")
async def get_llm_providers(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get LLM provider chain status (admin only).

    Returns:
    - Provider chain order
    - Per-provider availability and quality tier
    - Recent failover history

    This proxies to the LLM Gateway's /api/v1/providers endpoint.
    """
    # Check admin role
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required to view provider status"
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{LLM_GATEWAY_URL}/api/v1/providers")
            response.raise_for_status()
            return response.json()

    except httpx.ConnectError:
        return {
            "error": "LLM Gateway not reachable",
            "chain": [],
            "providers": [],
            "failover_history": []
        }
    except Exception as e:
        return {
            "error": str(e),
            "chain": [],
            "providers": [],
            "failover_history": []
        }


@router.get("/llm/quality-tier")
async def get_llm_quality_tier(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get current LLM quality tier.

    Returns the quality tier of the active provider, used for
    adjusting UI indicators about coaching quality.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LLM_GATEWAY_URL}/api/v1/providers/quality-tier")
            response.raise_for_status()
            return response.json()

    except httpx.ConnectError:
        return {
            "tier": "unknown",
            "provider": None,
            "status": "gateway_unreachable"
        }
    except Exception as e:
        return {
            "tier": "unknown",
            "provider": None,
            "status": "error",
            "error": str(e)
        }


@router.get("/llm/user-providers")
async def get_user_llm_providers(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get available LLM providers and user's preference.

    This endpoint is available to all authenticated users (not admin-only)
    to support the Settings page AI Provider selection.

    Returns:
    - providers: Dict of provider options with availability status
    - user_preference: User's saved LLM provider preference
    - active_provider: Which provider will actually be used
    """
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    # Get user's saved preference
    user_preference = "auto"
    if user_doc:
        user_preference = user_doc.get("preferences", {}).get("llm_provider", "auto")

    # Initialize provider status
    providers = {
        "auto": {
            "available": True,
            "name": "Auto (Recommended)",
            "description": "Best available provider with automatic failover",
            "quality_tier": "adaptive",
            "cost": "variable"
        },
        "cloud": {
            "available": False,
            "name": "Cloud (Premium)",
            "description": "Claude API - highest quality coaching",
            "quality_tier": "premium",
            "cost": "API costs apply",
            "reason": "Checking availability..."
        },
        "local": {
            "available": False,
            "name": "Local (Cost-Free)",
            "description": "Local LLM - unlimited free usage",
            "quality_tier": "standard",
            "cost": "No cost",
            "reason": "Checking availability..."
        }
    }

    # Fetch actual availability from gateway
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LLM_GATEWAY_URL}/api/v1/providers")
            if response.status_code == 200:
                gateway_data = response.json()

                for gw_provider in gateway_data.get("providers", []):
                    name = gw_provider.get("name", "").lower()

                    if name == "anthropic":
                        providers["cloud"]["available"] = gw_provider.get("available", False)
                        providers["cloud"]["model"] = gw_provider.get("current_model")
                        if not providers["cloud"]["available"]:
                            providers["cloud"]["reason"] = gw_provider.get("error", "API key not configured")
                        else:
                            providers["cloud"].pop("reason", None)

                    elif name == "ollama":
                        providers["local"]["available"] = gw_provider.get("available", False)
                        providers["local"]["model"] = gw_provider.get("current_model")
                        quality = gw_provider.get("quality_tier", "basic")
                        providers["local"]["quality_tier"] = quality
                        if not providers["local"]["available"]:
                            providers["local"]["reason"] = gw_provider.get("error", "Ollama not configured")
                        else:
                            providers["local"].pop("reason", None)

    except httpx.ConnectError:
        providers["cloud"]["reason"] = "LLM Gateway unreachable"
        providers["local"]["reason"] = "LLM Gateway unreachable"
    except Exception as e:
        providers["cloud"]["reason"] = f"Error: {str(e)}"
        providers["local"]["reason"] = f"Error: {str(e)}"

    # Determine which provider will actually be used
    def determine_active():
        if user_preference == "cloud" and providers["cloud"]["available"]:
            return "cloud"
        elif user_preference == "local" and providers["local"]["available"]:
            return "local"
        elif user_preference == "auto":
            if providers["cloud"]["available"]:
                return "cloud"
            elif providers["local"]["available"]:
                return "local"
        # Fallback for non-auto preference when preferred unavailable
        if providers["cloud"]["available"]:
            return "cloud"
        elif providers["local"]["available"]:
            return "local"
        return "demo"

    active_provider = determine_active()

    return {
        "providers": providers,
        "user_preference": user_preference,
        "active_provider": active_provider,
        "fallback_warning": (
            user_preference != "auto" and
            active_provider != user_preference and
            active_provider != "demo"
        )
    }


# =============================================================================
# v3.14: Diagnostics Endpoints
# =============================================================================

@router.get("/diagnostics")
async def get_system_diagnostics(
    request: Request,
    user: dict = Depends(get_current_user),
    include_errors: bool = Query(True, description="Include recent error entries"),
    error_limit: int = Query(20, ge=1, le=100, description="Max error entries to return"),
    days: Optional[int] = Query(30, ge=1, le=365, description="Days for onboarding stats")
):
    """
    Get comprehensive system diagnostics (admin-only).

    Returns:
    - error_counts: Counts by severity level (ERROR, WARNING, CRITICAL)
    - onboarding_funnel: Onboarding completion metrics
    - system_health: Database, license, and overall health status
    - recent_errors: Most recent error entries (optional)

    This endpoint aggregates metrics from multiple sources for the
    in-app diagnostics panel. Only accessible to admin users.
    """
    # Check admin role
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required to view diagnostics"
        )

    # Collect diagnostics
    diagnostics = get_diagnostics(
        db=db,
        include_errors=include_errors,
        error_limit=error_limit
    )

    return diagnostics


@router.get("/diagnostics/onboarding")
async def get_onboarding_diagnostics(
    request: Request,
    user: dict = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365, description="Days to aggregate")
):
    """
    Get onboarding funnel statistics (admin-only).

    Returns detailed onboarding completion metrics for the specified
    time period. Use this for deeper analysis of onboarding performance.
    """
    # Check admin role
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required to view onboarding diagnostics"
        )

    from modules.diagnostics import OnboardingMetricsService
    metrics_service = OnboardingMetricsService(db)

    return await metrics_service.get_funnel_stats(days=days)


@router.get("/diagnostics/errors")
async def get_error_diagnostics(
    request: Request,
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100, description="Max entries to return"),
    level: Optional[str] = Query(None, description="Filter by level (ERROR, WARNING, CRITICAL)")
):
    """
    Get recent error entries (admin-only).

    Returns error entries from the in-memory error buffer.
    Useful for debugging recent issues without checking logs.
    """
    # Check admin role
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required to view error diagnostics"
        )

    from modules.diagnostics import error_buffer

    return {
        "errors": error_buffer.get_recent(limit=limit, level_filter=level),
        "counts": error_buffer.get_counts()
    }


@router.get("/diagnostics/users")
async def get_user_diagnostics(
    request: Request,
    user: dict = Depends(get_current_user),
    online_threshold_minutes: int = Query(15, ge=1, le=60, description="Minutes to consider user online")
):
    """
    Get all registered users with their online status (admin-only).

    Returns:
    - users: List of users with name, email, last_active, and online status
    - online_count: Number of currently online users
    - total_count: Total registered users

    Users are considered "online" if their last_active timestamp is within
    the specified threshold (default 15 minutes).
    """
    from datetime import timedelta

    # Check admin role
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required to view user diagnostics"
        )

    # Calculate online threshold
    online_cutoff = datetime.now(timezone.utc) - timedelta(minutes=online_threshold_minutes)

    # Fetch all users (exclude system/legacy users)
    users_cursor = db.db.users.find(
        {"is_legacy": {"$ne": True}},
        {
            "user_id": 1,
            "name": 1,
            "display_name": 1,
            "email": 1,
            "last_active": 1,
            "created_at": 1,
            "role": 1
        }
    ).sort("last_active", -1)  # Most recently active first

    users_list = []
    online_count = 0

    for u in users_cursor:
        last_active = u.get("last_active")
        is_online = False

        if last_active:
            # Handle both datetime objects and strings
            if isinstance(last_active, str):
                try:
                    last_active = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
                except:
                    last_active = None

            if last_active and last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)

            if last_active and last_active > online_cutoff:
                is_online = True
                online_count += 1

        users_list.append({
            "user_id": u.get("user_id"),
            "name": u.get("display_name") or u.get("name") or "Unknown",
            "email": u.get("email"),
            "last_active": last_active.isoformat() if last_active else None,
            "created_at": u.get("created_at").isoformat() if u.get("created_at") else None,
            "is_online": is_online,
            "role": u.get("role", "user")
        })

    return {
        "users": users_list,
        "online_count": online_count,
        "total_count": len(users_list),
        "online_threshold_minutes": online_threshold_minutes,
        "collected_at": datetime.now(timezone.utc).isoformat()
    }
