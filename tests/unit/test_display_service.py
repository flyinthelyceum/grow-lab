"""Tests for the display service — rotating OLED screens."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import DisplayConfig
from pi.data.models import SensorReading
from pi.config.schema import IrrigationConfig, IrrigationScheduleEntry
from pi.services.display import (
    DisplayService,
    _format_reading,
    _lookup_sensor,
    render_irrigation_page,
    render_system_page,
    render_sparkline_page,
    render_values_page,
)


def _reading(sensor_id: str, value: float, unit: str):
    return SensorReading(
        timestamp=datetime.now(timezone.utc),
        sensor_id=sensor_id,
        value=value,
        unit=unit,
    )


@pytest.fixture
def mock_oled():
    oled = MagicMock()
    oled.is_available = True
    oled.WIDTH = 128
    oled.HEIGHT = 64
    return oled


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_sensor_ids = AsyncMock(return_value=[
        "bme280_temperature", "bme280_humidity", "bme280_pressure"
    ])

    def _latest_for(sid):
        vals = {
            "bme280_temperature": _reading("bme280_temperature", 23.5, "°C"),
            "bme280_humidity": _reading("bme280_humidity", 55.0, "%"),
            "bme280_pressure": _reading("bme280_pressure", 1013.2, "hPa"),
        }
        return vals.get(sid)

    repo.get_latest = AsyncMock(side_effect=_latest_for)
    repo.get_range = AsyncMock(return_value=[
        _reading("bme280_temperature", 22.0 + i * 0.3, "°C")
        for i in range(10)
    ])
    return repo


@pytest.fixture
def config():
    return DisplayConfig(enabled=True, address=0x3C)


class TestRenderValuesPage:
    def test_draws_header_and_values(self, mock_oled):
        readings = {
            "bme280_temperature": _reading("bme280_temperature", 23.5, "°C"),
            "bme280_humidity": _reading("bme280_humidity", 55.0, "%"),
        }
        render_values_page(mock_oled, readings)

        mock_oled.clear.assert_called_once()
        assert mock_oled.draw_text.call_count >= 3  # Header + at least 2 values
        mock_oled.show.assert_called_once()

    def test_handles_empty_readings(self, mock_oled):
        render_values_page(mock_oled, {})
        mock_oled.clear.assert_called_once()
        mock_oled.show.assert_called_once()


class TestRenderSystemPage:
    def test_draws_system_status(self, mock_oled):
        from datetime import timedelta

        subsystems = {
            "sensors": True,
            "irrigation": False,
            "display": True,
        }
        render_system_page(mock_oled, timedelta(hours=3, minutes=12), subsystems)

        mock_oled.clear.assert_called_once()
        assert mock_oled.draw_text.call_count >= 5
        mock_oled.show.assert_called_once()

    def test_handles_empty_status(self, mock_oled):
        from datetime import timedelta

        render_system_page(mock_oled, timedelta(), {})
        mock_oled.clear.assert_called_once()
        mock_oled.show.assert_called_once()


class TestRenderSparklinePage:
    def test_draws_sparkline(self, mock_oled):
        values = [22.0, 22.5, 23.0, 22.8, 23.5]
        render_sparkline_page(mock_oled, "TEMP", values, "°C")

        mock_oled.clear.assert_called_once()
        mock_oled.draw_text.assert_called()  # Header
        mock_oled.draw_sparkline.assert_called_once()
        mock_oled.show.assert_called_once()

    def test_handles_empty_values(self, mock_oled):
        render_sparkline_page(mock_oled, "TEMP", [], "°C")
        mock_oled.clear.assert_called_once()
        mock_oled.show.assert_called_once()


class TestDisplayServiceInit:
    def test_initial_state(self, mock_oled, mock_repo, config):
        svc = DisplayService(mock_oled, mock_repo, config)
        assert svc._task is None
        assert svc._page_index == 0
        assert svc._page_duration == 5  # default seconds per page


class TestDisplayServiceStartStop:
    async def test_start_creates_task(self, mock_oled, mock_repo, config):
        svc = DisplayService(mock_oled, mock_repo, config)
        await svc.start()
        assert svc._task is not None
        await svc.stop()

    async def test_start_skips_when_unavailable(self, mock_oled, mock_repo, config):
        mock_oled.is_available = False
        svc = DisplayService(mock_oled, mock_repo, config)
        await svc.start()
        assert svc._task is None

    async def test_start_skips_when_disabled(self, mock_oled, mock_repo):
        config = DisplayConfig(enabled=False)
        svc = DisplayService(mock_oled, mock_repo, config)
        await svc.start()
        assert svc._task is None

    async def test_start_idempotent(self, mock_oled, mock_repo, config):
        svc = DisplayService(mock_oled, mock_repo, config)
        await svc.start()
        task1 = svc._task
        await svc.start()
        assert svc._task is task1
        await svc.stop()

    async def test_stop_clears_and_closes(self, mock_oled, mock_repo, config):
        svc = DisplayService(mock_oled, mock_repo, config)
        await svc.start()
        await svc.stop()
        mock_oled.clear.assert_called()
        mock_oled.show.assert_called()


class TestDisplayServiceRotation:
    async def test_rotates_pages(self, mock_oled, mock_repo, config):
        """Service should cycle through page renderers."""
        svc = DisplayService(mock_oled, mock_repo, config)
        svc._page_duration = 0.01  # Fast rotation for test

        with patch("pi.services.display.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, None, None, asyncio.CancelledError()]
            try:
                await svc._rotation_loop()
            except asyncio.CancelledError:
                pass

        # Should have rendered at least 3 pages
        assert mock_oled.clear.call_count >= 3
        assert mock_oled.show.call_count >= 3


class TestLookupSensor:
    def test_exact_match(self):
        label, unit, convert = _lookup_sensor("bme280_temperature")
        assert label == "Air"
        assert unit == "F"
        assert convert is not None

    def test_as7341_light_label(self):
        label, unit, convert = _lookup_sensor("as7341_lux")
        assert label == "Light"
        assert unit == "lx"
        assert convert is None

    def test_prefix_match_ds18b20(self):
        label, unit, convert = _lookup_sensor("ds18b20_abc123")
        assert label == "H2O Temp"
        assert unit == "F"

    def test_unknown_sensor(self):
        label, unit, convert = _lookup_sensor("some_unknown_sensor")
        assert label == "some_unk"  # truncated to 8 chars
        assert convert is None


class TestFormatReading:
    def test_temperature_converted(self):
        label, val = _format_reading("bme280_temperature", 20.0)
        assert label == "Air"
        assert "68.0" in val  # 20C = 68F

    def test_humidity_no_conversion(self):
        label, val = _format_reading("bme280_humidity", 55.0)
        assert label == "Humidity"
        assert "55.0" in val


class TestRenderIrrigationPage:
    def test_draws_schedule(self, mock_oled):
        schedules = (
            IrrigationScheduleEntry(hour=8, minute=0, duration_seconds=10),
            IrrigationScheduleEntry(hour=14, minute=0, duration_seconds=10),
        )
        now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)
        render_irrigation_page(mock_oled, schedules, "Pump fired at 08:00", now)
        mock_oled.clear.assert_called_once()
        mock_oled.show.assert_called_once()

    def test_no_pump_events(self, mock_oled):
        schedules = (IrrigationScheduleEntry(hour=8),)
        now = datetime(2026, 3, 18, 6, 0, tzinfo=timezone.utc)
        render_irrigation_page(mock_oled, schedules, None, now)
        mock_oled.show.assert_called_once()


class TestDisplayServiceIrrigation:
    async def test_render_irrigation_no_config(self, mock_oled, mock_repo, config):
        """Should render 'Not configured' when no irrigation config."""
        svc = DisplayService(mock_oled, mock_repo, config, irrigation_config=None)
        await svc._render_irrigation()
        mock_oled.show.assert_called()

    async def test_render_irrigation_with_config(self, mock_oled, mock_repo, config):
        """Should render irrigation schedule page."""
        irr_config = IrrigationConfig()
        mock_repo.get_events = AsyncMock(return_value=[])
        svc = DisplayService(
            mock_oled, mock_repo, config, irrigation_config=irr_config
        )
        await svc._render_irrigation()
        mock_oled.show.assert_called()

    async def test_render_sparkline_no_sensors(self, mock_oled, mock_repo, config):
        """Should handle no sensors gracefully."""
        mock_repo.get_sensor_ids = AsyncMock(return_value=[])
        svc = DisplayService(mock_oled, mock_repo, config)
        await svc._render_sparkline()
        mock_oled.show.assert_called()
