"""Rate limiting middleware (ARCH-06).

Uses slowapi to apply per-endpoint rate limits. Key function uses
user_id from JWT if authenticated, otherwise falls back to client IP.

Set RATE_LIMIT_ENABLED=false in env to disable (useful for testing).
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _get_rate_limit_key(request: Request) -> str:
    """Extract a rate-limit key: JWT user_id if present, else client IP."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        try:
            from ..services.auth_service import decode_token
            payload = decode_token(token)
            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return get_remote_address(request)


_enabled = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() != "false"
limiter = Limiter(key_func=_get_rate_limit_key, enabled=_enabled)
