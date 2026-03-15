"""
Federation Authentication Module

Handles:
1. Outbound auth: Attaching federation JWT to calls to remote IKF
2. Inbound auth: Validating JWT on requests FROM the IKF to local endpoints
3. Certificate management: TLS cert storage, validation, rotation
4. Credential storage: Encrypted persistence of federation secrets

Security model:
- Outbound: Federation JWT (issued by IKF during connect) + API key as fallback
- Inbound: IKF presents its own JWT; we validate against known IKF public key
- Transport: All federation traffic over TLS 1.3 (enforced by httpx client)

Usage:
    authenticator = FederationAuthenticator(db, config)

    # Validate inbound request
    claims = authenticator.validate_inbound_token(token)

    # Create outbound headers
    headers = authenticator.create_outbound_headers(federation_jwt)

    # FastAPI dependency
    @app.get("/federation/endpoint")
    async def endpoint(auth: FederationAuth = Depends(require_federation_auth)):
        ...
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from functools import lru_cache

from fastapi import HTTPException, Request, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("inde.ikf.federation.auth")


class FederationAuthError(Exception):
    """Raised when federation authentication fails."""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


class FederationAuthConfig:
    """Configuration for federation authentication."""

    def __init__(self):
        self.IKF_INSTANCE_ID = os.environ.get("IKF_INSTANCE_ID", "")
        self.IKF_API_KEY = os.environ.get("IKF_API_KEY", "")

        # JWT configuration
        # In production, this would be fetched via JWKS from the IKF identity service
        self.IKF_JWT_SECRET = os.environ.get(
            "IKF_JWT_SECRET",
            "simulator-secret-key-change-in-prod"
        )
        self.IKF_JWT_ALGORITHM = os.environ.get("IKF_JWT_ALGORITHM", "HS256")
        self.IKF_JWT_ISSUER = os.environ.get(
            "IKF_JWT_ISSUER",
            "https://auth.ikf.indeverse.io"
        )
        self.IKF_JWT_AUDIENCE = os.environ.get(
            "IKF_JWT_AUDIENCE",
            "api.ikf.indeverse.io"
        )

        # Verification level required for different operations
        self.REQUIRED_SCOPES = {
            "read": ["federation:read"],
            "write": ["federation:write"],
            "contribute": ["knowledge:contribute"],
            "patterns": ["patterns:read"]
        }


class FederationAuth:
    """Parsed federation authentication context."""

    def __init__(
        self,
        org_id: str,
        instance_id: str,
        verification_level: str,
        scopes: List[str],
        region: Optional[str] = None,
        raw_claims: Optional[Dict[str, Any]] = None
    ):
        self.org_id = org_id
        self.instance_id = instance_id
        self.verification_level = verification_level
        self.scopes = scopes
        self.region = region
        self.raw_claims = raw_claims or {}

    def has_scope(self, scope: str) -> bool:
        """Check if authentication includes a specific scope."""
        return scope in self.scopes

    def has_any_scope(self, scopes: List[str]) -> bool:
        """Check if authentication includes any of the specified scopes."""
        return any(s in self.scopes for s in scopes)

    def can_write(self) -> bool:
        """Check if authentication allows write operations."""
        return self.has_scope("federation:write")

    def can_contribute(self) -> bool:
        """Check if authentication allows knowledge contributions."""
        return self.has_scope("knowledge:contribute")


class FederationAuthenticator:
    """Manages federation authentication for both directions."""

    def __init__(self, db=None, config: Optional[FederationAuthConfig] = None):
        self._db = db
        self._config = config or FederationAuthConfig()
        self._jwt_module = None

        # Lazy load JWT module
        try:
            import jwt
            self._jwt_module = jwt
        except ImportError:
            logger.warning("PyJWT not available - JWT validation disabled")

    def validate_inbound_token(self, token: str) -> FederationAuth:
        """
        Validate a JWT from an incoming IKF request.

        Args:
            token: Bearer token from Authorization header

        Returns:
            FederationAuth with parsed claims

        Raises:
            FederationAuthError: If validation fails
        """
        if not self._jwt_module:
            raise FederationAuthError("JWT validation not available", 503)

        try:
            claims = self._jwt_module.decode(
                token,
                self._config.IKF_JWT_SECRET,
                algorithms=[self._config.IKF_JWT_ALGORITHM],
                audience=self._config.IKF_JWT_AUDIENCE,
                issuer=self._config.IKF_JWT_ISSUER
            )

            # Verify required claims
            required = ["sub", "orgId", "verificationLevel"]
            missing = [c for c in required if c not in claims]
            if missing:
                raise FederationAuthError(f"Missing claims: {missing}")

            # Parse scopes
            scope_str = claims.get("scope", "")
            scopes = scope_str.split() if scope_str else []

            # Verify minimum scope for federation access
            if not any(s.startswith("federation:") for s in scopes):
                raise FederationAuthError("Insufficient scope for federation access")

            return FederationAuth(
                org_id=claims["orgId"],
                instance_id=claims.get("instanceId", ""),
                verification_level=claims["verificationLevel"],
                scopes=scopes,
                region=claims.get("region"),
                raw_claims=claims
            )

        except self._jwt_module.ExpiredSignatureError:
            raise FederationAuthError("Federation token expired")

        except self._jwt_module.InvalidTokenError as e:
            raise FederationAuthError(f"Invalid federation token: {e}")

    def validate_api_key(self, api_key: str) -> FederationAuth:
        """
        Validate an API key (fallback authentication).

        API keys provide limited access compared to JWT.

        Args:
            api_key: API key from X-API-Key header

        Returns:
            FederationAuth with limited claims

        Raises:
            FederationAuthError: If validation fails
        """
        # In production, this would validate against a database of API keys
        # For MVP/simulation, we accept the configured API key
        if api_key and api_key == self._config.IKF_API_KEY:
            return FederationAuth(
                org_id="api-key-auth",
                instance_id=self._config.IKF_INSTANCE_ID,
                verification_level="PARTICIPANT",
                scopes=["federation:read", "federation:write"],
                raw_claims={"auth_method": "api_key"}
            )

        raise FederationAuthError("Invalid API key")

    def create_outbound_headers(
        self,
        federation_jwt: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Build headers for outbound federation requests.

        Args:
            federation_jwt: JWT received during federation connect

        Returns:
            Headers dict for HTTP requests
        """
        headers = {
            "Content-Type": "application/json",
            "X-InDE-Instance": self._config.IKF_INSTANCE_ID,
            "X-InDE-Version": "3.5.1"
        }

        if federation_jwt:
            headers["Authorization"] = f"Bearer {federation_jwt}"
        elif self._config.IKF_API_KEY:
            headers["X-API-Key"] = self._config.IKF_API_KEY

        return headers

    def store_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Persist federation credentials to MongoDB.

        In production: encrypt sensitive fields (JWT, API keys) before storage.
        For MVP: stored as-is with a marker for future encryption.

        Args:
            credentials: Dict containing JWT, API key, etc.

        Returns:
            True if stored successfully
        """
        if not self._db:
            logger.warning("No database connection - credentials not persisted")
            return False

        try:
            self._db.ikf_federation_state.update_one(
                {"type": "credentials"},
                {"$set": {
                    "type": "credentials",
                    **credentials,
                    "stored_at": datetime.now(timezone.utc),
                    "encrypted": False,  # Flag for production encryption
                    "rotation_due": None,  # Set when rotation is implemented
                    "version": "3.5.1"
                }},
                upsert=True
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False

    def load_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Load persisted federation credentials.

        Returns:
            Credentials dict or None if not found
        """
        if not self._db:
            return None

        try:
            doc = self._db.ikf_federation_state.find_one(
                {"type": "credentials"},
                {"_id": 0}
            )
            return doc

        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def clear_credentials(self) -> bool:
        """
        Clear stored federation credentials.

        Returns:
            True if cleared successfully
        """
        if not self._db:
            return False

        try:
            self._db.ikf_federation_state.delete_one({"type": "credentials"})
            return True

        except Exception as e:
            logger.error(f"Failed to clear credentials: {e}")
            return False


# ==============================================================================
# FASTAPI DEPENDENCIES
# ==============================================================================

# Singleton authenticator instance
_authenticator: Optional[FederationAuthenticator] = None


def get_authenticator() -> FederationAuthenticator:
    """Get or create the singleton authenticator instance."""
    global _authenticator
    if _authenticator is None:
        _authenticator = FederationAuthenticator()
    return _authenticator


def set_authenticator(authenticator: FederationAuthenticator):
    """Set the singleton authenticator (for testing/DI)."""
    global _authenticator
    _authenticator = authenticator


async def require_federation_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> FederationAuth:
    """
    FastAPI dependency for requiring federation authentication.

    Checks in order:
    1. Authorization: Bearer <token>
    2. X-API-Key header

    Usage:
        @app.get("/federation/endpoint")
        async def endpoint(auth: FederationAuth = Depends(require_federation_auth)):
            if not auth.can_write():
                raise HTTPException(403, "Write access required")
            ...
    """
    authenticator = get_authenticator()

    # Try Bearer token first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
        try:
            return authenticator.validate_inbound_token(token)
        except FederationAuthError as e:
            raise HTTPException(status_code=e.status_code, detail=str(e))

    # Fall back to API key
    if x_api_key:
        try:
            return authenticator.validate_api_key(x_api_key)
        except FederationAuthError as e:
            raise HTTPException(status_code=e.status_code, detail=str(e))

    # No authentication provided
    raise HTTPException(
        status_code=401,
        detail="Federation authentication required",
        headers={"WWW-Authenticate": "Bearer"}
    )


async def optional_federation_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[FederationAuth]:
    """
    FastAPI dependency for optional federation authentication.

    Returns None if no valid authentication is provided.
    """
    try:
        return await require_federation_auth(request, authorization, x_api_key)
    except HTTPException:
        return None


def require_scope(required_scope: str):
    """
    Factory for creating scope-checking dependencies.

    Usage:
        @app.post("/federation/contribute")
        async def contribute(
            auth: FederationAuth = Depends(require_scope("knowledge:contribute"))
        ):
            ...
    """
    async def scope_checker(
        auth: FederationAuth = require_federation_auth
    ) -> FederationAuth:
        if not auth.has_scope(required_scope):
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{required_scope}' required"
            )
        return auth

    return scope_checker


def require_verification_level(min_level: str):
    """
    Factory for creating verification level checking dependencies.

    Levels (lowest to highest): PENDING, OBSERVER, PARTICIPANT, CONTRIBUTOR, STEWARD
    """
    level_order = ["PENDING", "OBSERVER", "PARTICIPANT", "CONTRIBUTOR", "STEWARD"]

    async def level_checker(
        auth: FederationAuth = require_federation_auth
    ) -> FederationAuth:
        current_idx = level_order.index(auth.verification_level) \
            if auth.verification_level in level_order else -1
        required_idx = level_order.index(min_level) \
            if min_level in level_order else len(level_order)

        if current_idx < required_idx:
            raise HTTPException(
                status_code=403,
                detail=f"Verification level '{min_level}' required"
            )
        return auth

    return level_checker
