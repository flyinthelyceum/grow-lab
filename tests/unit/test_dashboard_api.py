"""Tests for the dashboard REST API endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from pi.dashboard.app import create_app
from pi.data.models import CameraCapture, SensorReading, SystemEvent


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=None)
    repo.get_range = AsyncMock(return_value=[])
    repo.get_all_readings = AsyncMock(return_value=[])
    repo.get_events = AsyncMock(return_value=[])
    repo.get_captures = AsyncMock(return_value=[])
    repo.get_sensor_ids = AsyncMock(return_value=[])
    repo.get_db_info = AsyncMock(return_value={
        "sensor_readings": 0,
        "system_events": 0,
        "camera_captures": 0,
    })
    repo.count_readings = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def app(mock_repo):
    return create_app(mock_repo)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _reading(sensor_id: str, value: float, unit: str, minutes_ago: int = 0):
    return SensorReading(
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        sensor_id=sensor_id,
        value=value,
        unit=unit,
    )


class TestReadingsEndpoint:
    async def test_get_readings_empty(self, client, mock_repo):
        response = await client.get("/api/readings/bme280_temperature")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_get_readings_with_data(self, client, mock_repo):
        readings = [
            _reading("bme280_temperature", 23.5, "°C", minutes_ago=5),
            _reading("bme280_temperature", 23.8, "°C", minutes_ago=0),
        ]
        mock_repo.get_range.return_value = readings

        response = await client.get("/api/readings/bme280_temperature?window=1h")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["value"] == 23.5
        assert data[1]["value"] == 23.8
        assert "timestamp" in data[0]
        assert "unit" in data[0]

    async def test_get_readings_default_window_24h(self, client, mock_repo):
        await client.get("/api/readings/bme280_temperature")
        # Should call get_range with ~24h window
        call_args = mock_repo.get_range.call_args
        assert call_args is not None
        start, end = call_args[1].get("start") or call_args[0][1], call_args[1].get("end") or call_args[0][2]
        delta = end - start
        assert 23 <= delta.total_seconds() / 3600 <= 25

    async def test_get_readings_1h_window(self, client, mock_repo):
        await client.get("/api/readings/bme280_humidity?window=1h")
        call_args = mock_repo.get_range.call_args
        assert call_args is not None

    async def test_get_readings_7d_window(self, client, mock_repo):
        await client.get("/api/readings/bme280_pressure?window=7d")
        call_args = mock_repo.get_range.call_args
        assert call_args is not None


class TestLatestReadingsEndpoint:
    async def test_latest_empty(self, client, mock_repo):
        mock_repo.get_sensor_ids.return_value = []
        response = await client.get("/api/readings/latest")
        assert response.status_code == 200
        assert response.json() == {}

    async def test_latest_with_data(self, client, mock_repo):
        mock_repo.get_sensor_ids.return_value = ["bme280_temperature", "bme280_humidity"]
        mock_repo.get_latest.side_effect = [
            _reading("bme280_temperature", 23.5, "°C"),
            _reading("bme280_humidity", 55.0, "%"),
        ]

        response = await client.get("/api/readings/latest")
        assert response.status_code == 200
        data = response.json()
        assert "bme280_temperature" in data
        assert data["bme280_temperature"]["value"] == 23.5
        assert "bme280_humidity" in data


class TestEventsEndpoint:
    async def test_events_empty(self, client, mock_repo):
        response = await client.get("/api/events")
        assert response.status_code == 200
        assert response.json() == []

    async def test_events_with_data(self, client, mock_repo):
        events = [
            SystemEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="irrigation",
                description="Pump pulse 10s",
            ),
        ]
        mock_repo.get_events.return_value = events

        response = await client.get("/api/events?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_type"] == "irrigation"


class TestImagesEndpoint:
    async def test_latest_image_none(self, client, mock_repo):
        mock_repo.get_captures.return_value = []
        response = await client.get("/api/images/latest")
        assert response.status_code == 200
        assert response.json() is None

    async def test_latest_image(self, client, mock_repo):
        capture = CameraCapture(
            timestamp=datetime.now(timezone.utc),
            filepath="/data/captures/img_001.jpg",
            filesize_bytes=54321,
        )
        mock_repo.get_captures.return_value = [capture]

        response = await client.get("/api/images/latest")
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "img_001.jpg"
        assert data["available"] is False
        assert data["url"] == "/api/images/img_001.jpg/file"

    async def test_image_file(self, client, mock_repo, tmp_path):
        capture_path = tmp_path / "img_001.jpg"
        capture_path.write_bytes(b"test-image")
        capture = CameraCapture(
            timestamp=datetime.now(timezone.utc),
            filepath=str(capture_path),
            filesize_bytes=10,
        )
        mock_repo.get_captures.return_value = [capture]

        response = await client.get("/api/images/img_001.jpg/file")
        assert response.status_code == 200
        assert response.content == b"test-image"

    async def test_image_file_missing(self, client, mock_repo):
        capture = CameraCapture(
            timestamp=datetime.now(timezone.utc),
            filepath=str(Path("/tmp/missing-image.jpg")),
            filesize_bytes=10,
        )
        mock_repo.get_captures.return_value = [capture]

        response = await client.get("/api/images/missing-image.jpg/file")
        assert response.status_code == 404

    async def test_images_list(self, client, mock_repo):
        captures = [
            CameraCapture(
                timestamp=datetime.now(timezone.utc),
                filepath=f"/data/captures/img_{i:03d}.jpg",
                filesize_bytes=10000 + i,
            )
            for i in range(3)
        ]
        mock_repo.get_captures.return_value = captures

        response = await client.get("/api/images?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestAlertsEndpoint:
    async def test_alerts_empty(self, client, mock_repo):
        mock_repo.get_events.return_value = []
        response = await client.get("/api/alerts")
        assert response.status_code == 200
        assert response.json() == []

    async def test_alerts_filters_by_type(self, client, mock_repo):
        events = [
            SystemEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="alert_warning",
                description="Humidity warning: 28.0%",
            ),
            SystemEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="irrigation",
                description="Pump pulse 10s",
            ),
            SystemEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="alert_critical",
                description="Humidity critical: 26.1%",
            ),
        ]
        mock_repo.get_events.return_value = events
        response = await client.get("/api/alerts")
        data = response.json()
        assert len(data) == 2
        assert all(d["event_type"].startswith("alert_") for d in data)


class TestAlertRulesEndpoint:
    async def test_rules_returns_defaults(self, client):
        response = await client.get("/api/alerts/rules")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        assert data[0]["sensor_id"] == "bme280_temperature"
        assert "warning_low" in data[0]
        assert "critical_high" in data[0]
        assert data[0]["label"] == "Air"


class TestFanStatusEndpoint:
    async def test_fan_status_no_temp(self, client, mock_repo):
        mock_repo.get_latest.return_value = None
        response = await client.get("/api/fan/status")
        assert response.status_code == 200
        data = response.json()
        assert data["temp_f"] is None
        assert data["duty_percent"] is None

    async def test_fan_status_with_temp(self, client, mock_repo):
        mock_repo.get_latest.return_value = _reading("bme280_temperature", 23.8, "°C")
        response = await client.get("/api/fan/status")
        assert response.status_code == 200
        data = response.json()
        # 23.8°C = 74.84°F — in ramp range
        assert data["temp_f"] is not None
        assert data["duty_percent"] is not None
        assert 0 <= data["duty_percent"] <= 100


class TestFanOverrideEndpoint:
    async def test_set_manual_duty(self, mock_repo):
        from unittest.mock import MagicMock

        fan_svc = MagicMock()
        fan_svc.override_duty = None
        app = create_app(mock_repo, fan_service=fan_svc)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/fan/override", json={"duty": 60})
        assert response.status_code == 200
        fan_svc.set_override.assert_called_once_with(60)

    async def test_set_auto_mode(self, mock_repo):
        from unittest.mock import MagicMock

        fan_svc = MagicMock()
        fan_svc.override_duty = 60
        app = create_app(mock_repo, fan_service=fan_svc)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/fan/override", json={"mode": "auto"})
        assert response.status_code == 200
        fan_svc.clear_override.assert_called_once()

    async def test_invalid_duty_rejected(self, client):
        response = await client.post("/api/fan/override", json={"duty": 150})
        assert response.status_code == 422

    async def test_no_fan_service_returns_503(self, client):
        response = await client.post("/api/fan/override", json={"duty": 50})
        assert response.status_code == 503


class TestSystemStatus:
    async def test_status(self, client, mock_repo):
        mock_repo.get_db_info.return_value = {
            "sensor_readings": 150,
            "system_events": 10,
            "camera_captures": 5,
        }
        mock_repo.get_sensor_ids.return_value = ["bme280_temperature", "bme280_humidity"]

        response = await client.get("/api/system/status")
        assert response.status_code == 200
        data = response.json()
        assert "db" in data
        assert "sensors" in data
        assert data["db"]["sensor_readings"] == 150
