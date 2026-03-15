"""
InDE MVP v3.15 - Client Error Logging API
Receives frontend error boundary reports and logs them to the diagnostics error buffer.

Endpoints:
- POST /api/v1/errors/client - Log a frontend error
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
import logging

from modules.diagnostics.error_buffer import error_buffer

logger = logging.getLogger("inde.api.client_errors")

router = APIRouter(prefix="/api/v1/errors", tags=["errors"])


class ClientErrorReport(BaseModel):
    """Frontend error boundary report."""
    zone: str
    error_message: str
    component_stack: Optional[str] = None


@router.post("/client")
async def log_client_error(error: ClientErrorReport, request: Request):
    """
    Receives frontend error boundary reports and adds them to the error buffer.

    These errors are visible in the admin Diagnostics Panel.
    Fire-and-forget from frontend - always returns success.
    """
    # Get user_id if available
    user = getattr(request.state, "user", None)
    user_id = user.get("user_id") if user else "anonymous"

    # Log to error buffer
    error_buffer.log(
        level="ERROR",
        module=f"frontend.{error.zone}",
        message=f"[Client] {error.error_message}",
        path=f"component:{error.zone}"
    )

    logger.warning(
        f"Client error in {error.zone} (user={user_id}): {error.error_message}"
    )

    return {"status": "logged"}
