"""Page routes serving Jinja2 templates.

Serves the observatory dashboard HTML pages.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def observatory(request: Request) -> HTMLResponse:
    """Serve the main GROWLAB dashboard."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "observatory.html")


@router.get("/art", response_class=HTMLResponse)
async def art_mode(request: Request) -> HTMLResponse:
    """Serve the Art Mode generative visualization page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "art.html")


@router.get("/dream", response_class=HTMLResponse)
async def dream_mode(request: Request) -> HTMLResponse:
    """Serve the Dream Mode ML-driven particle visualization."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "dream.html")
