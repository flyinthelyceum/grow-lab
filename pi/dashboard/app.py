"""FastAPI application factory for the Living Light Observatory.

Creates and configures the dashboard application with Jinja2
templates, static file serving, and API/WebSocket routes.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pi.dashboard.routes.api import router as api_router
from pi.dashboard.routes.pages import router as pages_router
from pi.dashboard.routes.websocket import router as ws_router
from pi.data.repository import SensorRepository

DASHBOARD_DIR = Path(__file__).parent
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"


def create_app(repo: SensorRepository) -> FastAPI:
    """Build the observatory dashboard application.

    Args:
        repo: Connected SensorRepository for data access.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(title="GROWLAB")

    # Store repo in app state for access from routes
    app.state.repo = repo
    app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Include routers
    app.include_router(api_router)
    app.include_router(ws_router)
    app.include_router(pages_router)

    return app
