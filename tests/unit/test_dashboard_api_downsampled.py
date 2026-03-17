"""Tests for the downsampled readings API endpoint.

The /api/readings/{sensor_id}/downsampled endpoint performs SQL-level
bucketing and averaging. These tests use a real in-memory SQLite DB
(not mocks) to verify the SQL bucketing logic produces correct results.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from pi.dashboard.app import create_app
from pi.data.models import SensorReading
from pi.data.repository import SensorRepository


@pytest.fixture
async def repo(tmp_path):
    """Real repository with in-memory-like temp DB."""
    db_path = tmp_path / "test_downsample.db"
    repository = SensorRepository(db_path)
    await repository.connect()
    yield repository
    await repository.close()


@pytest.fixture
def app(repo):
    return create_app(repo)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _insert_readings(repo, sensor_id, unit, values_with_minutes_ago):
    """Helper: insert readings at specific times.

    values_with_minutes_ago: list of (value, minutes_ago) tuples.
    """
    readings = []
    for value, minutes_ago in values_with_minutes_ago:
        readings.append(SensorReading(
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
            sensor_id=sensor_id,
            value=value,
            unit=unit,
        ))
    return readings


class TestDownsampledEndpoint:
    """Tests for GET /api/readings/{sensor_id}/downsampled."""

    async def test_empty_returns_empty_list(self, client):
        """No data → empty array, not an error."""
        response = await client.get(
            "/api/readings/bme280_temperature/downsampled?window=24h"
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_bucketed_averages(self, client, repo):
        """Multiple readings in the same 5-min bucket get averaged."""
        now = datetime.now(timezone.utc)
        # Insert 3 readings within the same 5-min bucket (~2 min ago)
        for val in [20.0, 22.0, 24.0]:
            await repo.save_reading(SensorReading(
                timestamp=now - timedelta(minutes=2, seconds=val),
                sensor_id="bme280_temperature",
                value=val,
                unit="°C",
            ))

        response = await client.get(
            "/api/readings/bme280_temperature/downsampled?window=1h"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # Average of 20, 22, 24 = 22.0
        assert abs(data[0]["value"] - 22.0) < 0.01
        assert data[0]["unit"] == "°C"
        assert data[0]["sensor_id"] == "bme280_temperature"
        assert "timestamp" in data[0]

    async def test_separate_buckets_stay_separate(self, client, repo):
        """Readings far apart should land in different buckets (24h/5min)."""
        now = datetime.now(timezone.utc)
        await repo.save_reading(SensorReading(
            timestamp=now - timedelta(minutes=10),
            sensor_id="bme280_temperature",
            value=20.0,
            unit="°C",
        ))
        await repo.save_reading(SensorReading(
            timestamp=now - timedelta(hours=6),
            sensor_id="bme280_temperature",
            value=30.0,
            unit="°C",
        ))

        response = await client.get(
            "/api/readings/bme280_temperature/downsampled?window=24h"
        )
        assert response.status_code == 200
        data = response.json()
        # 24h window uses 300s buckets, 6h apart → definitely separate
        assert len(data) == 2
        values = sorted([d["value"] for d in data])
        assert abs(values[0] - 20.0) < 0.01
        assert abs(values[1] - 30.0) < 0.01

    async def test_window_filters_old_data(self, client, repo):
        """Data outside the time window should be excluded."""
        now = datetime.now(timezone.utc)
        # One reading within 1h window
        await repo.save_reading(SensorReading(
            timestamp=now - timedelta(minutes=30),
            sensor_id="bme280_temperature",
            value=22.0,
            unit="°C",
        ))
        # One reading outside 1h window (2 hours ago)
        await repo.save_reading(SensorReading(
            timestamp=now - timedelta(hours=2),
            sensor_id="bme280_temperature",
            value=18.0,
            unit="°C",
        ))

        response = await client.get(
            "/api/readings/bme280_temperature/downsampled?window=1h"
        )
        data = response.json()
        assert len(data) == 1
        assert abs(data[0]["value"] - 22.0) < 0.01

    async def test_different_sensors_isolated(self, client, repo):
        """Downsampled endpoint only returns data for the requested sensor."""
        now = datetime.now(timezone.utc)
        await repo.save_reading(SensorReading(
            timestamp=now - timedelta(minutes=5),
            sensor_id="bme280_temperature",
            value=22.0,
            unit="°C",
        ))
        await repo.save_reading(SensorReading(
            timestamp=now - timedelta(minutes=5),
            sensor_id="bme280_humidity",
            value=55.0,
            unit="%",
        ))

        response = await client.get(
            "/api/readings/bme280_temperature/downsampled?window=1h"
        )
        data = response.json()
        assert len(data) == 1
        assert data[0]["sensor_id"] == "bme280_temperature"

    async def test_24h_window_uses_5min_buckets(self, client, repo):
        """24h window should use 300s buckets — readings 30s apart merge."""
        now = datetime.now(timezone.utc)
        # Place both readings at exactly the same minute to guarantee same bucket
        base = now - timedelta(minutes=10)
        await repo.save_reading(SensorReading(
            timestamp=base,
            sensor_id="bme280_temperature",
            value=21.0,
            unit="°C",
        ))
        await repo.save_reading(SensorReading(
            timestamp=base + timedelta(seconds=30),
            sensor_id="bme280_temperature",
            value=23.0,
            unit="°C",
        ))

        response = await client.get(
            "/api/readings/bme280_temperature/downsampled?window=24h"
        )
        data = response.json()
        # 30s apart with 5-min buckets → same bucket, averaged
        assert len(data) == 1
        assert abs(data[0]["value"] - 22.0) < 0.01

    async def test_results_ordered_by_time(self, client, repo):
        """Results should be in ascending time order."""
        now = datetime.now(timezone.utc)
        for i in range(5):
            await repo.save_reading(SensorReading(
                timestamp=now - timedelta(minutes=50 - i * 10),
                sensor_id="bme280_temperature",
                value=20.0 + i,
                unit="°C",
            ))

        response = await client.get(
            "/api/readings/bme280_temperature/downsampled?window=1h"
        )
        data = response.json()
        timestamps = [d["timestamp"] for d in data]
        assert timestamps == sorted(timestamps)

    async def test_response_has_iso_timestamps(self, client, repo):
        """Timestamps in response should be valid ISO format."""
        now = datetime.now(timezone.utc)
        await repo.save_reading(SensorReading(
            timestamp=now - timedelta(minutes=5),
            sensor_id="bme280_temperature",
            value=22.0,
            unit="°C",
        ))

        response = await client.get(
            "/api/readings/bme280_temperature/downsampled?window=1h"
        )
        data = response.json()
        assert len(data) == 1
        # Should parse without error
        parsed = datetime.fromisoformat(data[0]["timestamp"])
        assert parsed.tzinfo is not None  # Should be timezone-aware

    async def test_invalid_sensor_id_rejected(self, client):
        """Sensor IDs with invalid characters should be rejected (404 or 422)."""
        response = await client.get(
            "/api/readings/../../etc/passwd/downsampled?window=1h"
        )
        # Path traversal gets caught by router as 404 (no matching route)
        assert response.status_code in (404, 422)

    async def test_default_window_is_24h(self, client, repo):
        """No window param should default to 24h."""
        now = datetime.now(timezone.utc)
        # Reading within 24h
        await repo.save_reading(SensorReading(
            timestamp=now - timedelta(hours=12),
            sensor_id="bme280_temperature",
            value=22.0,
            unit="°C",
        ))
        # Reading outside 24h
        await repo.save_reading(SensorReading(
            timestamp=now - timedelta(hours=36),
            sensor_id="bme280_temperature",
            value=18.0,
            unit="°C",
        ))

        response = await client.get(
            "/api/readings/bme280_temperature/downsampled"
        )
        data = response.json()
        assert len(data) == 1
