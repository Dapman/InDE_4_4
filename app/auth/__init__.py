"""
InDE v3.1 - Authentication Module
Provides JWT-based authentication with bcrypt password hashing.
"""

from auth.password import hash_password, verify_password
from auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_access_token,
    verify_refresh_token,
    hash_refresh_token,
    TokenError
)
from auth.middleware import (
    get_current_user,
    get_optional_user,
    require_maturity_level,
    AuthenticatedUser
)

__all__ = [
    # Password utilities
    "hash_password",
    "verify_password",
    # JWT utilities
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_access_token",
    "verify_refresh_token",
    "hash_refresh_token",
    "TokenError",
    # Middleware
    "get_current_user",
    "get_optional_user",
    "require_maturity_level",
    "AuthenticatedUser"
]
