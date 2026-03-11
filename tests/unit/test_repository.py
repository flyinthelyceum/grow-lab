"""Tests for the SQLite repository."""

from datetime import datetime, timedelta, timezone

import pytest

from pi.data.models import CameraCapture, SensorReading, SystemEvent
from pi.data.repository import SensorRepository


class TestSaveAndRetrieveReadings:
    async def test_save_and_get_latest(self, repo: SensorRepository, sample_reading: SensorReading):
        await repo.save_reading(sample_reading)
        latest = await repo.get_latest("bme280_temperature")
        assert latest is not None
        assert latest.value == 23.5
        assert latest.unit == "°C"
        assert latest.sensor_id == "bme280_temperature"

    async def test_get_latest_returns_none_for_unknown(self, repo: SensorRepository):
        result = await repo.get_latest("nonexistent")
        assert result is None

    async def test_count_readings(self, repo: SensorRepository, sample_reading: SensorReading):
        assert await repo.count_readings() == 0
        await repo.save_reading(sample_reading)
        assert await repo.count_readings() == 1
        assert await repo.count_readings("bme280_temperature") == 1
        assert await repo.count_readings("other") == 0

    async def test_get_range(self, repo: SensorRepository):
        base = datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(5):
            reading = SensorReading(
                timestamp=base + timedelta(minutes=i * 10),
                sensor_id="bme280_temperature",
                value=20.0 + i,
                unit="°C",
            )
            await repo.save_reading(reading)

        start = base + timedelta(minutes=10)
        end = base + timedelta(minutes=30)
        results = await repo.get_range("bme280_temperature", start, end)
        assert len(results) == 3
        assert results[0].value == 21.0
        assert results[-1].value == 23.0

    async def test_get_all_readings_with_limit(self, repo: SensorRepository):
        base = datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(10):
            await repo.save_reading(
                SensorReading(
                    timestamp=base + timedelta(minutes=i),
                    sensor_id="test",
                    value=float(i),
                    unit="x",
                )
            )
        results = await repo.get_all_readings(limit=3)
        assert len(results) == 3
        # Most recent first
        assert results[0].value == 9.0


class TestEvents:
    async def test_save_and_get_events(self, repo: SensorRepository, sample_event: SystemEvent):
        await repo.save_event(sample_event)
        events = await repo.get_events()
        assert len(events) == 1
        assert events[0].event_type == "irrigation"
        assert events[0].description == "Pump pulse 10s"


class TestCaptures:
    async def test_save_and_get_captures(self, repo: SensorRepository):
        capture = CameraCapture(
            timestamp=datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc),
            filepath="/data/images/test.jpg",
            filesize_bytes=500000,
        )
        await repo.save_capture(capture)
        captures = await repo.get_captures()
        assert len(captures) == 1
        assert captures[0].filepath == "/data/images/test.jpg"


class TestDbInfo:
    async def test_db_info_empty(self, repo: SensorRepository):
        info = await repo.get_db_info()
        assert info["sensor_readings"] == 0
        assert info["system_events"] == 0
        assert info["camera_captures"] == 0

    async def test_db_info_with_data(self, repo: SensorRepository, sample_reading, sample_event):
        await repo.save_reading(sample_reading)
        await repo.save_event(sample_event)
        info = await repo.get_db_info()
        assert info["sensor_readings"] == 1
        assert info["system_events"] == 1

    async def test_get_sensor_ids(self, repo: SensorRepository):
        base = datetime(2026, 3, 11, tzinfo=timezone.utc)
        await repo.save_reading(
            SensorReading(timestamp=base, sensor_id="bme280_temperature", value=22.0, unit="°C")
        )
        await repo.save_reading(
            SensorReading(timestamp=base, sensor_id="bme280_humidity", value=55.0, unit="%")
        )
        ids = await repo.get_sensor_ids()
        assert ids == ["bme280_humidity", "bme280_temperature"]


class TestConnectionLifecycle:
    async def test_not_connected_raises(self, test_config):
        repo = SensorRepository(test_config.system.db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await repo.get_db_info()

    async def test_close_and_reopen(self, test_config):
        repo = SensorRepository(test_config.system.db_path)
        await repo.connect()
        await repo.close()
        # Can reconnect
        await repo.connect()
        info = await repo.get_db_info()
        assert info["sensor_readings"] == 0
        await repo.close()
