"""FastAPI application factory for the GROWLAB dashboard.

Creates and configures the dashboard application with Jinja2
templates, static file serving, API/WebSocket routes, and the Stage 1
security baseline (sessions, rate limiting, request logging,
response headers).
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from pi.config.schema import FanConfig, SecurityConfig
from pi.dashboard.connections import ConnectionManager
from pi.dashboard.routes.admin import router as admin_router
from pi.dashboard.routes.api import router as api_router
from pi.dashboard.routes.pages import router as pages_router
from pi.dashboard.routes.websocket import router as ws_router
from pi.dashboard.security import (
    RequestLoggerMiddleware,
    SecurityHeadersMiddleware,
)
from pi.data.repository import SensorRepository

DASHBOARD_DIR = Path(__file__).parent
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"

logger = logging.getLogger(__name__)


def build_static_asset_url(path: str) -> str:
    """Return a cache-busted static asset URL for a dashboard file."""
    normalized = path.lstrip("/")
    asset_path = (STATIC_DIR / normalized).resolve()

    try:
        asset_path.relative_to(STATIC_DIR.resolve())
    except ValueError:
        return f"/static/{normalized}"

    if not asset_path.exists():
        return f"/static/{normalized}"

    version = int(asset_path.stat().st_mtime_ns)
    return f"/static/{normalized}?{urlencode({'v': version})}"


def _resolve_session_secret(security_config: SecurityConfig) -> str:
    """Return a session secret, generating an ephemeral one if needed.

    Empty/short configured secrets fall back to an ephemeral 32-byte
    token; sessions will not survive a restart in that mode. A WARN
    is logged so operators notice.
    """
    configured = security_config.session_secret_key
    if configured and len(configured) >= 32:
        return configured
    logger.warning(
        "[security] session_secret_key missing or under 32 chars; generating "
        "ephemeral key. Sessions will NOT survive a restart. Set "
        "GROWLAB_SESSION_SECRET_KEY or [security].session_secret_key to a "
        "stable random 32+ char value."
    )
    return secrets.token_urlsafe(48)


def create_app(
    repo: SensorRepository,
    fan_config: FanConfig | None = None,
    fan_service=None,
    connection_manager: ConnectionManager | None = None,
    security_config: SecurityConfig | None = None,
) -> FastAPI:
    """Build the observatory dashboard application.

    Args:
        repo: Connected SensorRepository for data access.
        fan_config: Optional fan configuration for status endpoint.
        fan_service: Optional FanService instance for duty override control.
        connection_manager: Optional ConnectionManager for WebSocket broadcasts.
        security_config: Stage 1 security baseline config (auth, rate limits,
            request logging). Defaults to SecurityConfig() (auth disabled).

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(title="GROWLAB")
    security = security_config or SecurityConfig()

    if security.enabled and not security.admin_password_sha256:
        logger.warning(
            "[security] admin_password_sha256 is empty; admin endpoints are "
            "UNAUTHENTICATED. Set GROWLAB_ADMIN_PASSWORD_SHA256 or "
            "[security].admin_password_sha256."
        )

    # Shared state
    app.state.repo = repo
    app.state.fan_config = fan_config or FanConfig()
    app.state.fan_service = fan_service
    app.state.connection_manager = connection_manager or ConnectionManager()
    app.state.security_config = security
    app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.templates.env.globals["static_asset"] = build_static_asset_url

    # Rate limiter: keyed by client IP, default limit applied to every route.
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[security.rate_limit_default],
    )
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded, _rate_limit_exceeded_handler
    )

    # Static
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Routers — register before middleware in FastAPI is fine; middleware
    # is applied to the resulting ASGI stack.
    app.include_router(api_router)
    app.include_router(ws_router)
    app.include_router(pages_router)
    app.include_router(admin_router)

    # Middleware. Order: outermost first when using add_middleware.
    # Final request flow (outer -> inner):
    #   SecurityHeaders -> Sessions -> RequestLogger -> SlowAPI -> app
    app.add_middleware(SlowAPIMiddleware)
    if security.log_requests:
        app.add_middleware(
            RequestLoggerMiddleware,
            log_user_agents=security.log_user_agents,
        )
    app.add_middleware(
        SessionMiddleware,
        secret_key=_resolve_session_secret(security),
        max_age=security.session_max_age_seconds,
        same_site="lax",
        https_only=False,
    )
    app.add_middleware(SecurityHeadersMiddleware)

    return app


def _rate_limit_exceeded_handler(request, exc: RateLimitExceeded):
    """Return a plain 429 JSON response when a rate limit is hit."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )
