"""
InDE v3.1 - JWT Token Handler
Provides JWT token creation, validation, and refresh functionality.

Token Claims (OIDC-compatible):
- sub: user_id
- email: user email
- maturity: current maturity level
- exp: expiration timestamp
- iat: issued at
- type: "access" or "refresh"
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import JWTError, jwt
import hashlib

from core.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)


class TokenError(Exception):
    """Exception raised for token-related errors."""
    pass


def create_access_token(
    user_id: str,
    email: str,
    maturity_level: str = "NOVICE",
    additional_claims: Optional[Dict] = None
) -> str:
    """
    Create JWT access token.

    Args:
        user_id: User's unique identifier
        email: User's email address
        maturity_level: Current maturity level (NOVICE, COMPETENT, PROFICIENT, EXPERT)
        additional_claims: Optional additional JWT claims

    Returns:
        Encoded JWT access token string
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    claims = {
        "sub": user_id,
        "email": email,
        "maturity": maturity_level,
        "exp": expire,
        "iat": now,
        "type": "access"
    }

    if additional_claims:
        claims.update(additional_claims)

    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    Create longer-lived refresh token for silent renewal.

    Args:
        user_id: User's unique identifier

    Returns:
        Encoded JWT refresh token string
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    claims = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "refresh"
    }

    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict:
    """
    Decode and validate JWT.

    Args:
        token: JWT token string

    Returns:
        Decoded token claims

    Raises:
        TokenError: If token is invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise TokenError(f"Invalid token: {str(e)}")


def verify_access_token(token: str) -> Dict:
    """
    Verify an access token and return its claims.

    Args:
        token: Access token string

    Returns:
        Token claims dict with user_id, email, maturity

    Raises:
        TokenError: If token is invalid or not an access token
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise TokenError("Invalid token type: expected access token")

    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "maturity_level": payload.get("maturity", "NOVICE")
    }


def verify_refresh_token(token: str) -> str:
    """
    Verify a refresh token and return the user_id.

    Args:
        token: Refresh token string

    Returns:
        User ID from the token

    Raises:
        TokenError: If token is invalid or not a refresh token
    """
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise TokenError("Invalid token type: expected refresh token")

    return payload.get("sub")


def hash_refresh_token(token: str) -> str:
    """
    Create a hash of a refresh token for secure storage.

    Args:
        token: Refresh token string

    Returns:
        SHA-256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()
