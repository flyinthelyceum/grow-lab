"""Tests for the display service — rotating OLED screens."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import DisplayConfig
from pi.data.models import SensorReading
from pi.services.display import (
    DisplayService,
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
