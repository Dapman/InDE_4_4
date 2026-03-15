"""
InDE v3.1 - Authentication Middleware
FastAPI dependencies for JWT authentication.
"""

from typing import Optional, Dict
from datetime import datetime, timezone
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.jwt_handler import verify_access_token, TokenError
from core.database import db

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


def _update_last_active(user_id: str):
    """Update user's last_active timestamp (non-blocking, fire-and-forget)."""
    try:
        db.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"last_active": datetime.now(timezone.utc)}}
        )
    except Exception:
        # Silently ignore - activity tracking should never block requests
        pass


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """
    FastAPI dependency that extracts and validates JWT from Authorization header.

    Usage:
        @router.get("/protected")
        async def protected_route(user = Depends(get_current_user)):
            # user contains: user_id, email, maturity_level
            pass

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User dict with user_id, email, maturity_level

    Raises:
        HTTPException(401): If token is missing, invalid, or expired
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid access token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user = verify_access_token(credentials.credentials)

        # v3.16: Update last_active on every authenticated request
        if user.get("user_id"):
            _update_last_active(user["user_id"])

        return user
    except TokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict]:
    """
    Same as get_current_user but returns None instead of raising.
    Used for endpoints that work both authenticated and anonymous.

    Usage:
        @router.get("/public-or-private")
        async def flexible_route(user = Depends(get_optional_user)):
            if user:
                # Authenticated user
                pass
            else:
                # Anonymous access
                pass

    Args:
        credentials: HTTP Bearer token credentials (optional)

    Returns:
        User dict if authenticated, None if not
    """
    if not credentials:
        return None

    try:
        return verify_access_token(credentials.credentials)
    except TokenError:
        return None


def require_maturity_level(min_level: str):
    """
    Factory for creating maturity-level-checking dependencies.

    Usage:
        @router.get("/expert-only")
        async def expert_route(
            user = Depends(require_maturity_level("PROFICIENT"))
        ):
            # Only PROFICIENT and EXPERT users can access
            pass

    Args:
        min_level: Minimum required maturity level

    Returns:
        FastAPI dependency function
    """
    level_order = ["NOVICE", "COMPETENT", "PROFICIENT", "EXPERT"]

    async def check_maturity(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict:
        user = await get_current_user(credentials)

        user_level = user.get("maturity_level", "NOVICE")
        user_level_idx = level_order.index(user_level) if user_level in level_order else 0
        required_idx = level_order.index(min_level) if min_level in level_order else 0

        if user_level_idx < required_idx:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires {min_level} maturity level or higher."
            )

        return user

    return check_maturity


class AuthenticatedUser:
    """
    Helper class to access current user info throughout the request.
    Useful for logging and event emission.
    """

    def __init__(self, user_data: Dict):
        self.user_id = user_data.get("user_id")
        self.email = user_data.get("email")
        self.maturity_level = user_data.get("maturity_level", "NOVICE")

    @property
    def is_legacy(self) -> bool:
        """Check if this is the legacy system user."""
        return self.email == "legacy@inde.local"

    def __repr__(self):
        return f"AuthenticatedUser(user_id={self.user_id}, email={self.email})"
