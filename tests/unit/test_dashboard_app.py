"""Tests for the dashboard app factory."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pi.dashboard.app import build_static_asset_url, create_app


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=None)
    repo.get_range = AsyncMock(return_value=[])
    repo.get_events = AsyncMock(return_value=[])
    repo.get_captures = AsyncMock(return_value=[])
    repo.get_sensor_ids = AsyncMock(return_value=[])
    repo.get_db_info = AsyncMock(return_value={})
    return repo


class TestCreateApp:
    def test_returns_fastapi_instance(self, mock_repo):
        app = create_app(mock_repo)
        assert isinstance(app, FastAPI)

    def test_has_api_routes(self, mock_repo):
        # Assert on served behaviour, not on app.routes: Starlette >=1.6 keeps
        # included routers as opaque _IncludedRouter entries instead of
        # flattening their Route objects into app.routes.
        app = create_app(mock_repo)
        api_paths = [p for p in app.openapi()["paths"] if p.startswith("/api/")]
        assert api_paths

    def test_has_page_routes(self, mock_repo):
        app = create_app(mock_repo)
        with TestClient(app) as client:
            assert client.get("/").status_code == 200
            assert client.get("/art").status_code == 200

    def test_has_websocket_route(self, mock_repo):
        # WebSocket routes never appear in the OpenAPI schema, so connect.
        app = create_app(mock_repo)
        with TestClient(app) as client:
            with client.websocket_connect("/ws/updates"):
                pass

    def test_repo_stored_in_state(self, mock_repo):
        app = create_app(mock_repo)
        assert app.state.repo is mock_repo

    def test_registers_static_asset_helper(self, mock_repo):
        app = create_app(mock_repo)
        helper = app.state.templates.env.globals["static_asset"]
        url = helper("art.js")
        assert url.startswith("/static/art.js?v=")


def test_build_static_asset_url_ignores_missing_files():
    assert build_static_asset_url("missing.js") == "/static/missing.js"
