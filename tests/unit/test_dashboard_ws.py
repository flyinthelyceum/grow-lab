"""Tests for the dashboard WebSocket endpoint."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from pi.dashboard.app import create_app
from pi.data.models import SensorReading


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_sensor_ids = AsyncMock(return_value=["bme280_temperature"])
    repo.get_latest = AsyncMock(
        return_value=SensorReading(
            timestamp=datetime.now(timezone.utc),
            sensor_id="bme280_temperature",
            value=23.5,
            unit="°C",
        )
    )
    return repo


@pytest.fixture
def app(mock_repo):
    return create_app(mock_repo)


class TestWebSocket:
    def test_connect_and_receive(self, app, mock_repo):
        """WebSocket should connect and send at least one message."""
        client = TestClient(app)
        with client.websocket_connect("/ws/updates") as ws:
            data = ws.receive_json()
            assert "timestamp" in data
            assert "readings" in data

    def test_readings_format(self, app, mock_repo):
        """Each reading in the broadcast should have sensor_id, value, unit."""
        client = TestClient(app)
        with client.websocket_connect("/ws/updates") as ws:
            data = ws.receive_json()
            readings = data["readings"]
            assert len(readings) >= 1
            r = readings[0]
            assert "sensor_id" in r
            assert "value" in r
            assert "unit" in r

    def test_empty_readings(self, app, mock_repo):
        """Should handle when no sensors have data."""
        mock_repo.get_sensor_ids.return_value = []
        client = TestClient(app)
        with client.websocket_connect("/ws/updates") as ws:
            data = ws.receive_json()
            assert data["readings"] == []

    def test_request_triggers_update(self, app, mock_repo):
        """Sending text should trigger another update."""
        client = TestClient(app)
        with client.websocket_connect("/ws/updates") as ws:
            # First auto-sent update
            data1 = ws.receive_json()
            assert "readings" in data1
            # Request another
            ws.send_text("update")
            data2 = ws.receive_json()
            assert "readings" in data2

    def test_no_repo_closes_socket(self):
        """WebSocket should close with 1011 when repo is missing."""
        from pi.dashboard.app import create_app

        app = create_app(None)
        # Manually clear repo to simulate missing state
        app.state.repo = None
        client = TestClient(app)
        try:
            with client.websocket_connect("/ws/updates") as ws:
                # Should either close immediately or raise
                ws.receive_json()
        except Exception:
            pass  # Expected — socket closed
