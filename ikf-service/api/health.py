"""
InDE IKF Service - Health Check API
Provides health and readiness endpoints.
"""

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/ikf/health")
async def health(request: Request):
    """Health check including Redis and MongoDB connectivity."""
    db_ok = False
    redis_ok = False

    try:
        request.app.state.db.command("ping")
        db_ok = True
    except Exception:
        pass

    try:
        status = await request.app.state.publisher.health_check()
        redis_ok = status.get("connected", False)
    except Exception:
        pass

    status = "healthy" if (db_ok and redis_ok) else "degraded"
    return {
        "status": status,
        "version": "3.5.0",
        "service": "inde-ikf",
        "dependencies": {
            "mongodb": "connected" if db_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected"
        }
    }


@router.get("/ikf/ready")
async def readiness(request: Request):
    """Readiness probe for Kubernetes/orchestrators."""
    try:
        request.app.state.db.command("ping")
        return {"ready": True}
    except Exception:
        return {"ready": False}
