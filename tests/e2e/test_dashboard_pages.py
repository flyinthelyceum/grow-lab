"""E2E tests for dashboard page routes."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from pi.dashboard.app import create_app


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_sensor_ids = AsyncMock(return_value=[])
    repo.get_latest = AsyncMock(return_value=None)
    repo.get_db_info = AsyncMock(return_value={})
    return repo


@pytest.fixture
def app(mock_repo):
    return create_app(mock_repo)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestObservatoryPage:
    async def test_root_returns_html(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_contains_observatory_title(self, client):
        response = await client.get("/")
        assert "Living Light Observatory" in response.text

    async def test_contains_subsystem_panels(self, client):
        response = await client.get("/")
        html = response.text
        for panel in ["LIGHT", "WATER", "AIR", "ROOT", "PLANT"]:
            assert panel in html

    async def test_includes_d3_script(self, client):
        response = await client.get("/")
        assert "d3" in response.text.lower() or "d3.min.js" in response.text

    async def test_includes_observatory_js(self, client):
        response = await client.get("/")
        assert "observatory.js" in response.text

    async def test_includes_stylesheet(self, client):
        response = await client.get("/")
        assert "style.css" in response.text


class TestArtModePage:
    async def test_art_returns_html(self, client):
        response = await client.get("/art")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_contains_art_mode_title(self, client):
        response = await client.get("/art")
        assert "Art Mode" in response.text

    async def test_includes_p5_script(self, client):
        response = await client.get("/art")
        assert "p5" in response.text.lower()

    async def test_includes_art_js(self, client):
        response = await client.get("/art")
        assert "art.js" in response.text
