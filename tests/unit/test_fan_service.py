"""Tests for the fan control service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import FanConfig
from pi.data.models import SensorReading
from pi.services.fan import FanService


def _reading(value: float) -> SensorReading:
    return SensorReading(
        timestamp=datetime.now(timezone.utc),
        sensor_id="bme280_temperature",
        value=value,
        unit="°C",
    )


@pytest.fixture
def mock_fan():
    fan = MagicMock()
    fan.is_available = True
    fan.duty_cycle = 0
    fan.set_duty = MagicMock(return_value=True)
    fan.duty_for_temperature = MagicMock(return_value=50)
    fan.close = MagicMock()
    return fan


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_latest = AsyncMock(return_value=_reading(23.0))  # ~73.4°F
    return repo


@pytest.fixture
def config():
    return FanConfig(enabled=True, poll_interval_seconds=1)


class TestFanServiceInit:
    def test_initial_state(self, mock_fan, mock_repo, config):
        svc = FanService(mock_fan, mock_repo, config)
        assert svc._task is None
        assert svc.is_running is False


class TestFanServiceStartStop:
    async def test_start_creates_task(self, mock_fan, mock_repo, config):
        svc = FanService(mock_fan, mock_repo, config)
        await svc.start()
        assert svc.is_running is True
        await svc.stop()

    async def test_start_skips_when_disabled(self, mock_fan, mock_repo):
        config = FanConfig(enabled=False)
        svc = FanService(mock_fan, mock_repo, config)
        await svc.start()
        assert svc.is_running is False

    async def test_start_skips_when_unavailable(self, mock_fan, mock_repo, config):
        mock_fan.is_available = False
        svc = FanService(mock_fan, mock_repo, config)
        await svc.start()
        assert svc.is_running is False

    async def test_start_idempotent(self, mock_fan, mock_repo, config):
        svc = FanService(mock_fan, mock_repo, config)
        await svc.start()
        task1 = svc._task
        await svc.start()
        assert svc._task is task1
        await svc.stop()

    async def test_stop_closes_fan(self, mock_fan, mock_repo, config):
        svc = FanService(mock_fan, mock_repo, config)
        await svc.start()
        await svc.stop()
        mock_fan.close.assert_called_once()


class TestFanServiceControlLoop:
    async def test_adjusts_duty_from_temperature(self, mock_fan, mock_repo, config):
        """Service should read temp and call set_duty with computed target."""
        svc = FanService(mock_fan, mock_repo, config)

        with patch("pi.services.fan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._control_loop()
            except asyncio.CancelledError:
                pass

        mock_repo.get_latest.assert_called()
        mock_fan.duty_for_temperature.assert_called()
        mock_fan.set_duty.assert_called()

    async def test_no_adjustment_when_same_duty(self, mock_fan, mock_repo, config):
        """Should skip set_duty if target matches current duty."""
        mock_fan.duty_cycle = 50  # Already at target
        mock_fan.duty_for_temperature.return_value = 50
        svc = FanService(mock_fan, mock_repo, config)

        with patch("pi.services.fan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._control_loop()
            except asyncio.CancelledError:
                pass

        mock_fan.set_duty.assert_not_called()

    async def test_handles_no_temperature_data(self, mock_fan, mock_repo, config):
        """Should not crash when no temperature readings are available."""
        mock_repo.get_latest = AsyncMock(return_value=None)
        svc = FanService(mock_fan, mock_repo, config)

        with patch("pi.services.fan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._control_loop()
            except asyncio.CancelledError:
                pass

        mock_fan.set_duty.assert_not_called()

    async def test_handles_repo_error(self, mock_fan, mock_repo, config):
        """Should catch and log errors, not crash."""
        mock_repo.get_latest = AsyncMock(side_effect=RuntimeError("db locked"))
        svc = FanService(mock_fan, mock_repo, config)

        with patch("pi.services.fan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._control_loop()
            except asyncio.CancelledError:
                pass

        # Should not raise — error caught internally


class TestGetAirTempF:
    async def test_converts_celsius_to_fahrenheit(self, mock_fan, mock_repo, config):
        mock_repo.get_latest = AsyncMock(return_value=_reading(20.0))
        svc = FanService(mock_fan, mock_repo, config)
        temp = await svc._get_air_temp_f()
        assert temp is not None
        assert abs(temp - 68.0) < 0.01  # 20°C = 68°F

    async def test_returns_none_when_no_data(self, mock_fan, mock_repo, config):
        mock_repo.get_latest = AsyncMock(return_value=None)
        svc = FanService(mock_fan, mock_repo, config)
        temp = await svc._get_air_temp_f()
        assert temp is None
