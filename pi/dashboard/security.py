"""Security primitives for the GROWLAB dashboard.

Stage 1 baseline: stdlib-only password hashing, session-backed admin auth,
privacy-preserving access logging, and conservative response headers.

No external auth dependencies. Password verification uses
secrets.compare_digest for constant-time comparison. IPs and user-agents
are hashed (sha256, truncated 16 hex chars) before persisting to avoid
storing PII in the access log.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import sys
import time
from typing import Awaitable, Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Paths excluded from access logging (high-volume, low-signal).
_LOG_SKIP_PREFIXES: tuple[str, ...] = ("/static/", "/ws/", "/ws")

# CSP allows inline styles to keep the existing dashboard functioning;
# revisit once style.css is fully externalised.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://static.cloudflareinsights.com; "
    "script-src-elem 'self' https://static.cloudflareinsights.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: blob:; "
    "connect-src 'self' ws: wss: https://cloudflareinsights.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

_PERMISSIONS_POLICY = (
    "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
)


def _hash_password(plain: str) -> str:
    """Return the lowercase hex sha256 of a plaintext password."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def verify_password(plain: str, expected_hash: str) -> bool:
    """Constant-time check of plaintext against stored hex sha256.

    Returns False if expected_hash is empty (auth disabled state should
    be handled by the caller before reaching here).
    """
    if not expected_hash:
        return False
    candidate = _hash_password(plain)
    return secrets.compare_digest(candidate, expected_hash.lower())


def _hash_token(value: str) -> str:
    """Return the first 16 hex chars of sha256(value). Privacy-preserving id."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def is_admin(request: Request) -> bool:
    """Return True if the current session is authenticated as admin."""
    try:
        session = request.session
    except AssertionError:
        # SessionMiddleware not installed — treat as unauthenticated.
        return False
    return bool(session.get("admin", False))


async def require_admin(request: Request) -> None:
    """FastAPI dependency: raise 401 if the request is not admin-authenticated.

    Use as `Depends(require_admin)` on protected routes.
    """
    if not is_admin(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Persist a privacy-preserving record of each request to access_log.

    Skips /static/* and /ws/* to avoid flooding the table. Hashes client
    IP and user-agent to 16 hex chars before storing. Logs only the path
    (not the query string) to avoid leaking tokens. Falls back to stderr
    if the SQLite repository is unavailable so a logging error never
    breaks the request.
    """

    def __init__(self, app: ASGIApp, log_user_agents: bool = True) -> None:
        super().__init__(app)
        self._log_user_agents = log_user_agents

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if any(path.startswith(prefix) for prefix in _LOG_SKIP_PREFIXES):
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            try:
                await self._record(request, path, status_code, duration_ms)
            except Exception as exc:  # pragma: no cover - defensive
                print(
                    f"[access-log] failed to persist: {exc!r}",
                    file=sys.stderr,
                )

    async def _record(
        self,
        request: Request,
        path: str,
        status_code: int,
        duration_ms: int,
    ) -> None:
        repo = getattr(request.app.state, "repo", None)
        if repo is None or not hasattr(repo, "log_access"):
            return

        client_host = request.client.host if request.client else ""
        ip_hash = _hash_token(client_host) if client_host else ""

        ua = request.headers.get("user-agent", "") if self._log_user_agents else ""
        ua_hash = _hash_token(ua) if ua else ""

        referrer = request.headers.get("referer", "")[:256]

        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).isoformat()

        await repo.log_access(
            timestamp=timestamp,
            method=request.method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            referrer=referrer,
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply conservative response headers to every response.

    CSP allows 'self' for default and inline styles for compatibility
    with the existing dashboard. WebSocket schemes (ws:, wss:) are
    permitted in connect-src for the live telemetry feed.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("Content-Security-Policy", _CSP)
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        headers.setdefault("Permissions-Policy", _PERMISSIONS_POLICY)
        return response
