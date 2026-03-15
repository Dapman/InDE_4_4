"""
InDE v3.16 - Authentication API Routes
Handles user registration, login, and token management.

v3.16: GII auto-assignment at registration, welcome email with GII.
v3.15: Include role in /me response for admin panel access.
v3.14: Auto-assign admin role from INDE_ADMIN_EMAIL on registration.
"""

from datetime import datetime, timezone
from typing import Optional
import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from auth.password import hash_password, verify_password
from auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    hash_refresh_token,
    TokenError
)
from auth.middleware import get_current_user
from core.config import INDE_ADMIN_EMAIL, DEMO_MODE_ACTIVE
from gii.manager import GIIManager
from services.email_service import send_welcome_email
from services.telemetry import track

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=100)
    experience_level: Optional[str] = "NOVICE"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    experience_level: str
    maturity_level: str
    created_at: datetime
    role: Optional[str] = None  # v3.15: Include role for admin detection
    gii_id: Optional[str] = None  # v3.16: Global Innovator Identifier
    gii_state: Optional[str] = None  # v3.16: GII state (PROVISIONAL, ACTIVE, etc.)


@router.post("/register", response_model=TokenResponse)
async def register(request: Request, data: RegisterRequest):
    """
    Register a new user account.

    Creates a new user, hashes their password, and returns access tokens.
    """
    db = request.app.state.db

    # Check if email already exists
    existing = db.db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered. Please use login."
        )

    # Create user
    user_id = str(uuid.uuid4())

    # v3.14: Auto-assign admin role if email matches INDE_ADMIN_EMAIL
    is_admin = (
        INDE_ADMIN_EMAIL and
        data.email.lower() == INDE_ADMIN_EMAIL.lower()
    )
    if is_admin:
        logger.info(f"Auto-assigning admin role to {data.email}")

    # v3.16: Issue PROVISIONAL GII at registration
    gii_manager = GIIManager(db)
    gii_id = gii_manager.generate_gii(region="US", user_id=user_id)

    user = {
        "user_id": user_id,
        "email": data.email,
        "name": data.name,
        "display_name": data.name,
        "password_hash": hash_password(data.password),
        "experience_level": data.experience_level,
        "maturity_level": "NOVICE",
        "maturity_scores": {
            "discovery_competence": 0.0,
            "validation_rigor": 0.0,
            "reflective_practice": 0.0,
            "velocity_management": 0.0,
            "risk_awareness": 0.0,
            "knowledge_contribution": 0.0,
            "composite": 0.0
        },
        "gii_id": gii_id,  # v3.16: Auto-assigned at registration
        "gii_state": "PROVISIONAL",  # v3.16: Initial state
        "organization_id": None,
        "preferences": {},
        "is_legacy": False,
        "created_at": datetime.now(timezone.utc),
        "last_active": datetime.now(timezone.utc),
        "pursuit_count": 0,
        "completed_pursuits": 0,
        "role": "admin" if is_admin else "user",  # v3.14: Admin auto-assignment
    }

    db.db.users.insert_one(user)

    # v3.16: Create GII profile record
    gii_profile = {
        "gii_id": gii_id,
        "user_id": user_id,
        "state": "PROVISIONAL",
        "region": "US",
        "storage_election": "FULL_PARTICIPATION",
        "organization_id": None,
        "verification_level": "UNVERIFIED",
        "issued_at": datetime.now(timezone.utc),
        "last_updated": datetime.now(timezone.utc),
        "privacy_settings": {
            "allow_public_profile": False,
            "allow_ikf_contribution": True,
            "allow_anonymized_patterns": True
        }
    }
    db.db.gii_profiles.insert_one(gii_profile)
    logger.info(f"PROVISIONAL GII issued: {gii_id} for user {user_id}")

    # v3.16: Send welcome email with GII (non-blocking)
    try:
        send_welcome_email(data.email, data.name, gii_id)
    except Exception as e:
        logger.warning(f"Failed to send welcome email: {e}")

    # v3.16: Track GII issuance event
    track("gii.issued", gii_id=gii_id, properties={"method": "registration"})

    # Create tokens
    access_token = create_access_token(
        user_id=user_id,
        email=data.email,
        maturity_level="NOVICE"
    )
    refresh_token = create_refresh_token(user_id)

    # Store refresh token hash
    db.db.sessions.insert_one({
        "user_id": user_id,
        "refresh_token_hash": hash_refresh_token(refresh_token),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc)  # Will be set by TTL index
    })

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, data: LoginRequest):
    """
    Authenticate user and return access tokens.
    """
    db = request.app.state.db

    # Find user by email
    user = db.db.users.find_one({"email": data.email})
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(data.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Update last active
    db.db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"last_active": datetime.now(timezone.utc)}}
    )

    # Create tokens
    access_token = create_access_token(
        user_id=user["user_id"],
        email=user["email"],
        maturity_level=user.get("maturity_level", "NOVICE")
    )
    refresh_token = create_refresh_token(user["user_id"])

    # Store refresh token hash
    db.db.sessions.insert_one({
        "user_id": user["user_id"],
        "refresh_token_hash": hash_refresh_token(refresh_token),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc)
    })

    # v3.16: Track session start
    track("session.started", gii_id=user.get("gii_id"),
          properties={"returning_user": user.get("pursuit_count", 0) > 0})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, data: RefreshRequest):
    """
    Refresh an access token using a refresh token.
    """
    db = request.app.state.db

    try:
        user_id = verify_refresh_token(data.refresh_token)
    except TokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid refresh token: {str(e)}"
        )

    # Verify refresh token exists in database
    token_hash = hash_refresh_token(data.refresh_token)
    session = db.db.sessions.find_one({
        "user_id": user_id,
        "refresh_token_hash": token_hash
    })

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Refresh token not found or revoked"
        )

    # Get user for new token
    user = db.db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    # Revoke old refresh token
    db.db.sessions.delete_one({"_id": session["_id"]})

    # Create new tokens
    access_token = create_access_token(
        user_id=user_id,
        email=user["email"],
        maturity_level=user.get("maturity_level", "NOVICE")
    )
    new_refresh_token = create_refresh_token(user_id)

    # Store new refresh token
    db.db.sessions.insert_one({
        "user_id": user_id,
        "refresh_token_hash": hash_refresh_token(new_refresh_token),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc)
    })

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.post("/logout")
async def logout(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Logout current user by revoking all refresh tokens.
    """
    db = request.app.state.db

    # Delete all sessions for user
    result = db.db.sessions.delete_many({"user_id": user["user_id"]})

    return {
        "message": "Logged out successfully",
        "sessions_revoked": result.deleted_count
    }


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(request: Request):
    """
    Login with a demo account.
    Creates the demo user if it doesn't exist.

    v4.2: Respects DEMO_MODE setting. When INACTIVE, returns 403 with
    a message directing users to register or sign in.
    """
    # v4.2: Check if demo mode is active
    if not DEMO_MODE_ACTIVE:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "DEMO_MODE_INACTIVE",
                "message": "The Demo User account is currently not available. Please register for a new account or sign in with your existing credentials to explore InDE."
            }
        )

    db = request.app.state.db

    demo_email = "demo@inde.dev"
    demo_password = "demo123!"
    demo_name = "Demo User"

    # Check if demo user exists
    user = db.db.users.find_one({"email": demo_email})

    if not user:
        # Create demo user
        user_id = str(uuid.uuid4())
        user = {
            "user_id": user_id,
            "email": demo_email,
            "name": demo_name,
            "display_name": demo_name,
            "password_hash": hash_password(demo_password),
            "experience_level": "INTERMEDIATE",
            "maturity_level": "PRACTITIONER",
            "maturity_scores": {
                "discovery_competence": 0.5,
                "validation_rigor": 0.5,
                "reflective_practice": 0.5,
                "velocity_management": 0.5,
                "risk_awareness": 0.5,
                "knowledge_contribution": 0.5,
                "composite": 0.5
            },
            "gii_id": None,
            "organization_id": None,
            "preferences": {},
            "is_legacy": False,
            "is_demo": True,
            "created_at": datetime.now(timezone.utc),
            "last_active": datetime.now(timezone.utc),
            "pursuit_count": 0,
            "completed_pursuits": 0
        }
        db.db.users.insert_one(user)
    else:
        user_id = user["user_id"]
        # Update last active
        db.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"last_active": datetime.now(timezone.utc)}}
        )

    # Create tokens
    access_token = create_access_token(
        user_id=user_id,
        email=demo_email,
        maturity_level=user.get("maturity_level", "PRACTITIONER")
    )
    refresh_token = create_refresh_token(user_id)

    # Store refresh token hash
    db.db.sessions.insert_one({
        "user_id": user_id,
        "refresh_token_hash": hash_refresh_token(refresh_token),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc)
    })

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Get current user's profile information.
    """
    db = request.app.state.db

    user_doc = db.db.users.find_one({"user_id": user["user_id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        user_id=user_doc["user_id"],
        email=user_doc["email"],
        name=user_doc.get("name", user_doc.get("display_name", "")),
        experience_level=user_doc.get("experience_level", "NOVICE"),
        maturity_level=user_doc.get("maturity_level", "NOVICE"),
        created_at=user_doc.get("created_at", datetime.now(timezone.utc)),
        role=user_doc.get("role", "user"),  # v3.15: Include role for admin detection
        gii_id=user_doc.get("gii_id"),  # v3.16: Global Innovator Identifier
        gii_state=user_doc.get("gii_state")  # v3.16: GII state
    )


# ═══════════════════════════════════════════════════════════════════════════════
# v4.2: SESSION STATE AND PREFERENCES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/session-state")
async def get_session_state(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    v4.2: Get last session state for context detection.

    Returns the user's last active pursuit and timestamp for routing
    decisions on login.
    """
    db = request.app.state.db

    # Find last conversation turn across all pursuits
    last_turn = db.db.conversation_history.find_one(
        {"user_id": user["user_id"]},
        sort=[("timestamp", -1)]
    )

    # Find last momentum snapshot for momentum context
    last_snapshot = None
    if last_turn and last_turn.get("pursuit_id"):
        last_snapshot = db.db.momentum_snapshots.find_one(
            {"pursuit_id": last_turn["pursuit_id"]},
            sort=[("recorded_at", -1)]
        )

    return {
        "last_active_pursuit": last_turn.get("pursuit_id") if last_turn else None,
        "last_active_timestamp": last_turn.get("timestamp").isoformat() if last_turn and last_turn.get("timestamp") else None,
        "momentum_at_exit": {
            "tier": last_snapshot.get("momentum_tier") if last_snapshot else None,
            "composite_score": last_snapshot.get("composite_score") if last_snapshot else None,
            "artifact_at_exit": last_snapshot.get("artifact_at_exit") if last_snapshot else None,
            "bridge_delivered": last_snapshot.get("bridge_delivered", False) if last_snapshot else False,
        } if last_snapshot else None
    }


class PreferencesUpdate(BaseModel):
    skip_context_routing: Optional[bool] = None
    llm_provider: Optional[str] = None
    coaching_cadence: Optional[str] = None  # v4.2: "off", "gentle", "active"
    experience_mode: Optional[str] = None  # v4.3: "novice", "intermediate", "expert"


@router.patch("/preferences")
async def update_preferences(
    request: Request,
    data: PreferencesUpdate,
    user: dict = Depends(get_current_user)
):
    """
    v4.3: Update user preferences.

    Supports:
    - skip_context_routing: Skip context detection and go directly to dashboard
    - llm_provider: Preferred LLM provider (auto, anthropic, openai)
    - coaching_cadence: Re-engagement preference (off, gentle, active)
    - experience_mode: Progress display mode (novice, intermediate, expert) [v4.3]
    """
    db = request.app.state.db

    # Build update dict from non-None values
    updates = {}
    if data.skip_context_routing is not None:
        updates["preferences.skip_context_routing"] = data.skip_context_routing
    if data.llm_provider is not None:
        updates["preferences.llm_provider"] = data.llm_provider
    if data.coaching_cadence is not None:
        if data.coaching_cadence not in ("off", "gentle", "active"):
            raise HTTPException(status_code=400, detail="coaching_cadence must be 'off', 'gentle', or 'active'")
        updates["preferences.coaching_cadence"] = data.coaching_cadence
    # v4.3: Experience mode preference
    if data.experience_mode is not None:
        if data.experience_mode not in ("novice", "intermediate", "expert"):
            raise HTTPException(status_code=400, detail="experience_mode must be 'novice', 'intermediate', or 'expert'")
        updates["preferences.experience_mode"] = data.experience_mode

    if not updates:
        raise HTTPException(status_code=400, detail="No preferences to update")

    result = db.db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": updates}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": "updated", "fields": list(updates.keys())}
