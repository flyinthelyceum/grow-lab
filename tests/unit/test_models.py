"""Tests for frozen data models."""

from datetime import datetime, timezone

import pytest

from pi.data.models import CameraCapture, SensorReading, SystemEvent


class TestSensorReading:
    def test_creation(self):
        r = SensorReading(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            sensor_id="bme280_temperature",
            value=22.5,
            unit="°C",
        )
        assert r.sensor_id == "bme280_temperature"
        assert r.value == 22.5
        assert r.unit == "°C"
        assert r.metadata is None

    def test_frozen(self):
        r = SensorReading(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            sensor_id="test",
            value=1.0,
            unit="x",
        )
        with pytest.raises(AttributeError):
            r.value = 2.0  # type: ignore[misc]

    def test_iso_timestamp(self):
        dt = datetime(2026, 3, 11, 14, 30, 0, tzinfo=timezone.utc)
        r = SensorReading(timestamp=dt, sensor_id="test", value=1.0, unit="x")
        assert r.iso_timestamp == "2026-03-11T14:30:00+00:00"

    def test_with_metadata(self):
        r = SensorReading(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            sensor_id="test",
            value=1.0,
            unit="x",
            metadata='{"key": "val"}',
        )
        assert r.metadata == '{"key": "val"}'


class TestSystemEvent:
    def test_creation(self):
        e = SystemEvent(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            event_type="irrigation",
            description="Pump pulse",
        )
        assert e.event_type == "irrigation"
        assert e.description == "Pump pulse"

    def test_frozen(self):
        e = SystemEvent(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            event_type="test",
        )
        with pytest.raises(AttributeError):
            e.event_type = "changed"  # type: ignore[misc]


class TestCameraCapture:
    def test_creation(self):
        c = CameraCapture(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            filepath="/data/images/2026-01-01_00-00-00.jpg",
            filesize_bytes=1024000,
        )
        assert c.filepath == "/data/images/2026-01-01_00-00-00.jpg"
        assert c.filesize_bytes == 1024000

    def test_optional_filesize(self):
        c = CameraCapture(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            filepath="/test.jpg",
        )
        assert c.filesize_bytes is None
