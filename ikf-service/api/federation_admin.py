"""
InDE IKF Service v3.5.1 - Federation Administration API

Provides administrative control over federation lifecycle.
All endpoints require admin role (enforced by RBAC middleware in production).

These endpoints are called by the admin dashboard, not by innovators.

Endpoints:
- POST /register - Register this InDE instance with IKF
- POST /connect - Initiate federation connection
- POST /disconnect - Gracefully disconnect
- GET /status - Full federation status
- POST /circuit-breaker/reset - Manual circuit breaker reset
- POST /circuit-breaker/force-open - Force circuit breaker open (maintenance)
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger("inde.ikf.federation.admin")

router = APIRouter(prefix="/v1/federation/admin", tags=["federation-admin"])


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class OrgCredentials(BaseModel):
    """Organization credentials for federation registration."""
    organization_id: str
    organization_name: str
    industry_codes: List[str] = []
    sharing_level: str = "MODERATE"  # MINIMAL, MODERATE, FULL


class AdminStatusResponse(BaseModel):
    """Full federation status for admin dashboard."""
    connection: Dict[str, Any]
    circuit_breaker: Dict[str, Any]
    mode: str
    node_id: Optional[str] = None
    version: str = "3.5.1"


class CircuitBreakerAction(BaseModel):
    """Circuit breaker admin action."""
    action: str  # "reset" or "force_open"
    reason: Optional[str] = None


# ==============================================================================
# ADMIN ENDPOINTS
# ==============================================================================

@router.post("/register")
async def admin_register(credentials: OrgCredentials, request: Request):
    """
    Register this InDE instance with IKF (admin only).

    This is the first step in federation setup. After registration,
    use /connect to establish the connection.

    Returns:
        Registration status and instance ID
    """
    connection_manager = getattr(request.app.state, "connection_manager", None)

    if not connection_manager:
        raise HTTPException(
            status_code=503,
            detail="Connection manager not initialized - check federation mode"
        )

    try:
        result = await connection_manager.register(credentials.dict())
        logger.info(f"Admin registered federation: {credentials.organization_id}")
        return result

    except Exception as e:
        logger.error(f"Admin registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect")
async def admin_connect(request: Request):
    """
    Initiate federation connection (admin only).

    Must be registered first via /register.

    Returns:
        Connection status, verification level, and capabilities
    """
    connection_manager = getattr(request.app.state, "connection_manager", None)

    if not connection_manager:
        raise HTTPException(
            status_code=503,
            detail="Connection manager not initialized - check federation mode"
        )

    try:
        result = await connection_manager.connect()
        logger.info(f"Admin initiated connection: {result}")
        return result

    except Exception as e:
        logger.error(f"Admin connection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def admin_disconnect(request: Request):
    """
    Gracefully disconnect from IKF (admin only).

    Stops heartbeat, notifies hub, and clears connection state.

    Returns:
        Disconnection confirmation
    """
    connection_manager = getattr(request.app.state, "connection_manager", None)

    if not connection_manager:
        raise HTTPException(
            status_code=503,
            detail="Connection manager not initialized"
        )

    try:
        result = await connection_manager.disconnect()
        logger.info("Admin initiated disconnect")
        return result

    except Exception as e:
        logger.error(f"Admin disconnect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def admin_status(request: Request) -> Dict[str, Any]:
    """
    Full federation status including circuit breaker and heartbeat state.

    Returns:
        Comprehensive status for admin dashboard
    """
    connection_manager = getattr(request.app.state, "connection_manager", None)
    circuit_breaker = getattr(request.app.state, "circuit_breaker", None)
    federation_node = getattr(request.app.state, "federation_node", None)

    import os
    federation_mode = os.environ.get("IKF_FEDERATION_MODE", "OFFLINE")

    status = {
        "mode": federation_mode,
        "version": "3.5.1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if connection_manager:
        status["connection"] = connection_manager.get_status()
    else:
        status["connection"] = {
            "connection_state": "NOT_INITIALIZED",
            "message": "Connection manager not available"
        }

    if circuit_breaker:
        status["circuit_breaker"] = circuit_breaker.get_status()
    else:
        status["circuit_breaker"] = {
            "state": "NOT_INITIALIZED",
            "message": "Circuit breaker not available"
        }

    if federation_node:
        status["local_node"] = federation_node.get_status()

    return status


@router.post("/circuit-breaker/reset")
async def admin_reset_circuit_breaker(request: Request):
    """
    Manually reset circuit breaker to CLOSED (admin only).

    Use this to recover from an OPEN circuit after the underlying
    issue has been resolved.

    Returns:
        New circuit breaker state
    """
    circuit_breaker = getattr(request.app.state, "circuit_breaker", None)

    if not circuit_breaker:
        raise HTTPException(
            status_code=503,
            detail="Circuit breaker not initialized"
        )

    previous_state = circuit_breaker.state.value
    circuit_breaker.reset()

    logger.info(f"Admin reset circuit breaker: {previous_state} -> CLOSED")

    return {
        "status": "CLOSED",
        "previous_state": previous_state,
        "message": "Circuit breaker manually reset",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/circuit-breaker/force-open")
async def admin_force_open_circuit_breaker(request: Request, reason: Optional[str] = None):
    """
    Force circuit breaker to OPEN state (admin only).

    Use this for maintenance or when federation issues are known
    but not yet triggering automatic circuit opening.

    Returns:
        New circuit breaker state
    """
    circuit_breaker = getattr(request.app.state, "circuit_breaker", None)

    if not circuit_breaker:
        raise HTTPException(
            status_code=503,
            detail="Circuit breaker not initialized"
        )

    previous_state = circuit_breaker.state.value
    circuit_breaker.force_open()

    logger.info(f"Admin forced circuit breaker OPEN: {reason or 'No reason provided'}")

    return {
        "status": "OPEN",
        "previous_state": previous_state,
        "reason": reason or "Admin manual action",
        "message": "Circuit breaker forced open",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/events/recent")
async def admin_recent_events(
    request: Request,
    limit: int = 20,
    event_type: Optional[str] = None
):
    """
    Get recent federation events from audit log.

    Returns:
        List of recent federation events
    """
    db = getattr(request.app.state, "db", None)

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    query = {"source": "federation"}
    if event_type:
        query["event_type"] = {"$regex": f"^{event_type}"}

    events = list(
        db.audit_events.find(query, {"_id": 0})
        .sort("recorded_at", -1)
        .limit(limit)
    )

    return {
        "events": events,
        "count": len(events),
        "limit": limit
    }


@router.delete("/credentials")
async def admin_clear_credentials(request: Request):
    """
    Clear stored federation credentials (admin only).

    Use this before re-registering with different organization.

    Returns:
        Confirmation of credential removal
    """
    connection_manager = getattr(request.app.state, "connection_manager", None)

    if not connection_manager:
        raise HTTPException(
            status_code=503,
            detail="Connection manager not initialized"
        )

    # First disconnect if connected
    if connection_manager.is_connected:
        await connection_manager.disconnect()

    # Clear stored credentials
    db = getattr(request.app.state, "db", None)
    if db:
        db.ikf_federation_state.delete_many({
            "type": {"$in": ["credentials", "registration", "connection"]}
        })

    logger.info("Admin cleared federation credentials")

    return {
        "status": "cleared",
        "message": "Federation credentials and registration cleared",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/config/environment")
async def admin_get_config(request: Request):
    """
    Get current federation configuration from environment.

    Returns:
        All federation-related configuration values
    """
    import os

    config = {
        "IKF_FEDERATION_MODE": os.environ.get("IKF_FEDERATION_MODE", "OFFLINE"),
        "IKF_REMOTE_NODE_URL": os.environ.get("IKF_REMOTE_NODE_URL", "(not set)"),
        "IKF_INSTANCE_ID": os.environ.get("IKF_INSTANCE_ID", "(auto-generated)"),
        "IKF_HEARTBEAT_INTERVAL": os.environ.get("IKF_HEARTBEAT_INTERVAL", "60"),
        "IKF_CONNECTION_TIMEOUT": os.environ.get("IKF_CONNECTION_TIMEOUT", "30"),
        "IKF_CIRCUIT_BREAKER_THRESHOLD": os.environ.get("IKF_CIRCUIT_BREAKER_THRESHOLD", "5"),
        "IKF_CIRCUIT_BREAKER_RESET": os.environ.get("IKF_CIRCUIT_BREAKER_RESET", "300"),
        "IKF_RETRY_BACKOFF": os.environ.get("IKF_RETRY_BACKOFF", "30"),
        # Don't expose secrets
        "IKF_API_KEY": "(set)" if os.environ.get("IKF_API_KEY") else "(not set)",
        "IKF_JWT_SECRET": "(set)" if os.environ.get("IKF_JWT_SECRET") else "(using default)",
    }

    return {
        "config": config,
        "version": "3.5.1"
    }
