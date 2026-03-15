"""
InDE v3.15 Rate Limiting Middleware
Implements sliding window rate limiting for coaching and auth endpoints.
In-memory implementation — resets on container restart by design.
"""

import time
import logging
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import (
    INDE_COACHING_RATE_LIMIT,
    INDE_AUTH_RATE_LIMIT,
    INDE_AUTH_RATE_LIMIT_WINDOW,
)

logger = logging.getLogger("inde.middleware.rate_limiting")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for InDE.

    Implements sliding window rate limiting:
    - Per-user coaching rate limit (default: 30 requests/minute)
    - Per-IP authentication rate limit (default: 10 attempts/5 minutes)
    """

    def __init__(self, app):
        super().__init__(app)
        # user_id → list of request timestamps (coaching)
        self._coaching_windows: dict[str, list[float]] = defaultdict(list)
        # ip_address → list of attempt timestamps (auth)
        self._auth_windows: dict[str, list[float]] = defaultdict(list)

    def _sliding_window_check(
        self,
        store: dict,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Returns (allowed: bool, retry_after_seconds: int).
        Cleans stale entries from the window on each check.
        """
        now = time.time()
        window_start = now - window_seconds

        # Evict expired entries
        store[key] = [t for t in store.get(key, []) if t > window_start]

        if len(store.get(key, [])) >= limit:
            oldest = min(store[key])
            retry_after = int(window_seconds - (now - oldest)) + 1
            return False, max(1, retry_after)

        store[key].append(now)
        return True, 0

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Per-user coaching rate limit
        if "/coaching/" in path and method == "POST":
            user_id = self._extract_user_id(request)
            if user_id:
                allowed, retry_after = self._sliding_window_check(
                    self._coaching_windows,
                    user_id,
                    INDE_COACHING_RATE_LIMIT,
                    60  # 60-second window
                )
                if not allowed:
                    logger.warning(f"Rate limit exceeded for coaching: user={user_id}")
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": f"You're moving fast! Please wait {retry_after} seconds before sending your next message.",
                            "retry_after_seconds": retry_after
                        },
                        headers={"Retry-After": str(retry_after)}
                    )

        # Per-IP auth rate limit
        if path.endswith(("/auth/login", "/auth/register")) and method == "POST":
            ip = self._get_client_ip(request)
            allowed, retry_after = self._sliding_window_check(
                self._auth_windows,
                ip,
                INDE_AUTH_RATE_LIMIT,
                INDE_AUTH_RATE_LIMIT_WINDOW
            )
            if not allowed:
                logger.warning(f"Auth rate limit exceeded: ip={ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many attempts. Please wait before trying again.",
                        "retry_after_seconds": retry_after
                    },
                    headers={"Retry-After": str(retry_after)}
                )

        return await call_next(request)

    def _extract_user_id(self, request: Request) -> str | None:
        """Extract user_id from JWT token in Authorization header."""
        try:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return None
            token = auth_header.split(" ", 1)[1]
            # Decode without verification - auth middleware handles verification
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("sub") or payload.get("user_id")
        except Exception:
            return None

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP, checking X-Forwarded-For for proxied requests."""
        # Check for forwarded header (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()
        # Fall back to direct client
        return request.client.host if request.client else "unknown"
