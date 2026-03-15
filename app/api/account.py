"""
InDE v3.13 - Account Management API Routes
Handles account deletion, session management, password changes, and preferences.

v3.12: Account Trust & Completeness
v3.13: Added notification preferences endpoints
"""

from datetime import datetime, timezone
from typing import Optional
import os

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from auth.middleware import get_current_user
from auth.password import hash_password, verify_password
from modules.account.deletion import AccountDeletionService
from modules.account.password_reset import PasswordResetService
from services.email_service import (
    send_password_reset_email,
    send_deletion_confirmation_email,
    is_email_configured
)

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ══════════════════════════════════════════════════════════════════════════════

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class ValidateTokenRequest(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class NotificationPreferencesUpdate(BaseModel):
    """Partial update for notification preferences."""
    activity_feed: Optional[str] = None       # "all" | "significant" | "off"
    mentions: Optional[str] = None            # "always" | "muted"
    state_changes: Optional[bool] = None
    new_members: Optional[bool] = None
    contributions: Optional[str] = None       # "all" | "direct_team" | "off"
    polling_interval_seconds: Optional[int] = None  # 15 | 30 | 60 | 120


class AccountDeletionRequest(BaseModel):
    confirm_email: EmailStr


class SessionResponse(BaseModel):
    session_id: str
    device_info: str
    ip_address: str
    created_at: Optional[str] = None
    last_active: Optional[str] = None
    expires_at: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# Password Reset Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/forgot-password")
async def forgot_password(request: Request, data: ForgotPasswordRequest):
    """
    Request a password reset email.
    ALWAYS returns 200 — never reveals whether email exists (prevents enumeration).
    """
    db = request.app.state.db
    service = PasswordResetService(db)

    result = await service.create_reset_token(
        email=data.email,
        requesting_ip=request.client.host if request.client else ""
    )

    if result and is_email_configured():
        send_password_reset_email(
            to_address=data.email,
            display_name=result["user"].get("display_name", result["user"].get("name", "Innovator")),
            reset_token=result["token"]
        )

    # Always return 200 regardless of whether email was found or sent
    return {"message": "If that email address is registered, you'll receive a reset link shortly."}


@router.post("/reset-password")
async def reset_password(request: Request, data: ResetPasswordRequest):
    """
    Complete password reset using token from email.
    """
    db = request.app.state.db
    service = PasswordResetService(db)

    result = await service.validate_and_consume_token(data.token, data.new_password)

    if not result["success"]:
        raise HTTPException(400, result["reason"])

    return {"message": "Password updated successfully. Please log in with your new password."}


@router.post("/validate-reset-token")
async def validate_reset_token(request: Request, data: ValidateTokenRequest):
    """
    Validate a password reset token without consuming it.
    Used by frontend to check token validity before showing reset form.
    """
    db = request.app.state.db
    service = PasswordResetService(db)

    result = await service.validate_token_only(data.token)
    return result


@router.get("/password-reset-status")
async def password_reset_status():
    """Let the UI know whether email-based password reset is available."""
    return {"email_configured": is_email_configured()}


# ══════════════════════════════════════════════════════════════════════════════
# Session Management Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/sessions")
async def get_sessions(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Return all active sessions for the current user.
    Includes device info, last active time, IP address.
    """
    db = request.app.state.db

    sessions = list(db.db.sessions.find({
        "user_id": user["user_id"],
        "revoked": {"$ne": True}
    }).limit(50))

    # Don't return raw token hashes — return safe session metadata only
    return [
        {
            "session_id": str(s["_id"]),
            "device_info": s.get("user_agent", s.get("device_info", "Unknown device")),
            "ip_address": s.get("ip_address", "Unknown"),
            "created_at": s.get("created_at").isoformat() if isinstance(s.get("created_at"), datetime) else s.get("created_at"),
            "last_active": s.get("last_active").isoformat() if isinstance(s.get("last_active"), datetime) else s.get("last_active"),
            "expires_at": s.get("expires_at").isoformat() if isinstance(s.get("expires_at"), datetime) else s.get("expires_at"),
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
async def terminate_session(
    session_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Terminate a specific session. User can only terminate their own sessions."""
    db = request.app.state.db
    from bson import ObjectId

    try:
        result = db.db.sessions.update_one(
            {"_id": ObjectId(session_id), "user_id": user["user_id"]},
            {"$set": {"revoked": True}}
        )
    except Exception:
        raise HTTPException(400, "Invalid session ID")

    if result.modified_count == 0:
        raise HTTPException(404, "Session not found")

    return {"message": "Session terminated. Active access tokens will expire within 30 minutes."}


@router.delete("/sessions")
async def terminate_all_other_sessions(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Terminate all sessions except the current one."""
    db = request.app.state.db

    # Note: We don't track current session ID in JWT, so this terminates ALL sessions
    # The user will need to log in again
    result = db.db.sessions.update_many(
        {"user_id": user["user_id"], "revoked": {"$ne": True}},
        {"$set": {"revoked": True}}
    )

    return {"message": f"Terminated {result.modified_count} session(s). Please log in again."}


# ══════════════════════════════════════════════════════════════════════════════
# Account Deletion Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/request-deletion")
async def request_account_deletion(
    data: AccountDeletionRequest,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Initiate account deletion.
    Requires confirmation: request.confirm_email must match the user's email.
    """
    db = request.app.state.db

    # Email confirmation gate
    if data.confirm_email.lower().strip() != user["email"].lower().strip():
        raise HTTPException(400, "Email confirmation does not match your account email.")

    service = AccountDeletionService(db)
    result = await service.request_deletion(
        user_id=user["user_id"],
        requesting_ip=request.client.host if request.client else ""
    )

    # Send confirmation email if configured
    if is_email_configured() and not result.get("already_requested"):
        send_deletion_confirmation_email(
            to_address=user["email"],
            display_name=user.get("display_name", user.get("name", "Innovator")),
            cancellation_token=result["cancellation_token"],
            scheduled_for=result["scheduled_for"]
        )

    return {
        "message": f"Account deletion scheduled for {result['scheduled_for']}.",
        "scheduled_for": result["scheduled_for"],
        "can_cancel_until": result["scheduled_for"],
        "email_sent": is_email_configured() and not result.get("already_requested"),
        "already_requested": result.get("already_requested", False),
        "cancellation_note": "To cancel, use the link in the confirmation email or contact your administrator."
    }


@router.get("/cancel-deletion")
async def cancel_account_deletion(token: str, request: Request):
    """
    Cancel a pending account deletion using the cancellation token from email.
    This endpoint requires NO authentication — the cancellation token IS the auth.
    Returns a redirect-friendly response for browser use.
    """
    db = request.app.state.db
    service = AccountDeletionService(db)
    result = await service.cancel_deletion(token)

    if not result["success"]:
        raise HTTPException(400, result.get("reason", "Cancellation failed"))

    return {
        "message": f"Account deletion cancelled. Welcome back, {result['display_name']}!",
        "success": True
    }


@router.get("/deletion-status")
async def get_deletion_status(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Return current deletion status for the authenticated user."""
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    if not user_doc:
        raise HTTPException(404, "User not found")

    return {
        "status": user_doc.get("status", "active"),
        "deletion_scheduled_for": user_doc.get("deletion_scheduled_for"),
        "deletion_requested_at": user_doc.get("deletion_requested_at")
    }


# ══════════════════════════════════════════════════════════════════════════════
# Change Password (Authenticated)
# ══════════════════════════════════════════════════════════════════════════════

@router.put("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Change password for authenticated user. Requires current password verification."""
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    if not user_doc:
        raise HTTPException(404, "User not found")

    if not verify_password(data.current_password, user_doc.get("password_hash", "")):
        raise HTTPException(400, "Current password is incorrect")

    db.db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "password_hash": hash_password(data.new_password),
            "last_active": datetime.now(timezone.utc)
        }}
    )

    return {"message": "Password updated successfully."}


# ══════════════════════════════════════════════════════════════════════════════
# Admin Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/admin/users/{user_id}/reset-link")
async def admin_generate_reset_link(
    user_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Admin endpoint: generate a password reset link without email.
    For self-hosted environments without SMTP configured.
    Returns the direct reset URL for the administrator to share securely.

    Note: In production, this should check for admin role.
    """
    db = request.app.state.db

    # TODO: Add admin role check when RBAC is fully implemented
    # if user.get("role") not in ["admin", "super_admin"]:
    #     raise HTTPException(403, "Admin access required")

    service = PasswordResetService(db)
    link = await service.admin_generate_reset_link(user_id)

    if not link:
        raise HTTPException(404, "User not found or not eligible for reset")

    expiry_minutes = int(os.environ.get("PASSWORD_RESET_TOKEN_EXPIRY_MINUTES", "60"))

    return {
        "reset_link": link,
        "expires_in_minutes": expiry_minutes,
        "warning": "Share this link securely — it grants immediate account access."
    }


# ══════════════════════════════════════════════════════════════════════════════
# v3.13: Notification Preferences
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_NOTIFICATION_PREFS = {
    "activity_feed": "all",        # "all" | "significant" | "off"
    "mentions": "always",          # "always" | "muted"
    "state_changes": True,
    "new_members": True,
    "contributions": "direct_team", # "all" | "direct_team" | "off"
    "polling_interval_seconds": 30
}


@router.get("/notification-preferences")
async def get_notification_preferences(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Return current notification preferences, with defaults for unset values.
    """
    db = request.app.state.db
    user_doc = db.db.users.find_one({"user_id": user["user_id"]})

    if not user_doc:
        raise HTTPException(404, "User not found")

    user_prefs = user_doc.get("preferences", {})
    saved_notifications = user_prefs.get("notifications", {})

    # Merge saved with defaults — saved values take precedence
    merged = {**DEFAULT_NOTIFICATION_PREFS, **saved_notifications}
    return merged


@router.put("/notification-preferences")
async def update_notification_preferences(
    prefs: NotificationPreferencesUpdate,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Update notification preferences.
    Partial updates supported — only provided fields are changed.
    All values validated against allowed options before saving.
    """
    db = request.app.state.db

    # Validate values
    allowed = {
        "activity_feed": ["all", "significant", "off"],
        "mentions": ["always", "muted"],
        "contributions": ["all", "direct_team", "off"],
        "polling_interval_seconds": [15, 30, 60, 120]
    }

    updates = prefs.model_dump(exclude_none=True)

    for field, value in updates.items():
        if field in allowed and value not in allowed[field]:
            raise HTTPException(
                400,
                f"Invalid value '{value}' for {field}. Allowed: {allowed[field]}"
            )

    # Save as nested update within preferences.notifications
    mongo_updates = {
        f"preferences.notifications.{k}": v
        for k, v in updates.items()
    }
    mongo_updates["updated_at"] = datetime.now(timezone.utc)

    db.db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": mongo_updates}
    )

    # Return the full merged preferences after save
    return await get_notification_preferences(request=request, user=user)
