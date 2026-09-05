"""Tests for the fan control service."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import FanConfig
from pi.services.fan import FanService


@pytest.fixture
def mock_fan():
    fan = MagicMock()
    fan.is_available = True
    fan.duty_cycle = 0
    fan.set_duty = MagicMock(return_value=True)
    fan.duty_for_time = MagicMock(return_value=50)
    fan.close = MagicMock()
    return fan


@pytest.fixture
def config():
    return FanConfig(enabled=True, poll_interval_seconds=1)


class TestFanServiceInit:
    def test_initial_state(self, mock_fan, config):
        svc = FanService(mock_fan, config)
        assert svc._task is None
        assert svc.is_running is False


class TestFanServiceStartStop:
    async def test_start_creates_task(self, mock_fan, config):
        svc = FanService(mock_fan, config)
        await svc.start()
        assert svc.is_running is True
        await svc.stop()

    async def test_start_skips_when_disabled(self, mock_fan):
        config = FanConfig(enabled=False)
        svc = FanService(mock_fan, config)
        await svc.start()
        assert svc.is_running is False

    async def test_start_skips_when_unavailable(self, mock_fan, config):
        mock_fan.is_available = False
        svc = FanService(mock_fan, config)
        await svc.start()
        assert svc.is_running is False

    async def test_start_idempotent(self, mock_fan, config):
        svc = FanService(mock_fan, config)
        await svc.start()
        task1 = svc._task
        await svc.start()
        assert svc._task is task1
        await svc.stop()

    async def test_stop_closes_fan(self, mock_fan, config):
        svc = FanService(mock_fan, config)
        await svc.start()
        await svc.stop()
        mock_fan.close.assert_called_once()


class TestFanServiceControlLoop:
    async def test_follows_the_gust_field(self, mock_fan, config):
        """The loop asks the driver for a duty from the clock, nothing else."""
        svc = FanService(mock_fan, config)

        with patch("pi.services.fan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._control_loop()
            except asyncio.CancelledError:
                pass

        mock_fan.duty_for_time.assert_called()
        mock_fan.set_duty.assert_called()

    async def test_takes_no_sensor_input(self, mock_fan, config):
        """The service holds no repository and reads no sensor.

        The fan is for canopy strength, not cooling. If a temperature read ever
        reappears here, the control law has quietly become a thermostat again.
        """
        svc = FanService(mock_fan, config)
        assert not hasattr(svc, "_repo")
        assert not hasattr(svc, "_get_air_temp_f")

    async def test_no_adjustment_when_same_duty(self, mock_fan, config):
        """Should skip set_duty if target matches current duty."""
        mock_fan.duty_cycle = 50
        mock_fan.duty_for_time.return_value = 50
        svc = FanService(mock_fan, config)

        with patch("pi.services.fan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._control_loop()
            except asyncio.CancelledError:
                pass

        mock_fan.set_duty.assert_not_called()

    async def test_survives_a_driver_error(self, mock_fan, config):
        """A GPIO failure must not kill the loop on a live plant."""
        mock_fan.duty_for_time = MagicMock(side_effect=RuntimeError("gpio gone"))
        svc = FanService(mock_fan, config)

        with patch("pi.services.fan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._control_loop()
            except asyncio.CancelledError:
                pass
        # caught internally; no raise


class TestFanServiceOverride:
    def test_no_override_by_default(self, mock_fan, config):
        svc = FanService(mock_fan, config)
        assert svc.override_duty is None

    def test_set_override(self, mock_fan, config):
        svc = FanService(mock_fan, config)
        svc.set_override(75)
        assert svc.override_duty == 75

    def test_set_override_clamps_to_range(self, mock_fan, config):
        svc = FanService(mock_fan, config)
        svc.set_override(150)
        assert svc.override_duty == 100
        svc.set_override(-10)
        assert svc.override_duty == 0

    def test_clear_override(self, mock_fan, config):
        svc = FanService(mock_fan, config)
        svc.set_override(75)
        svc.clear_override()
        assert svc.override_duty is None

    async def test_control_loop_uses_override(self, mock_fan, config):
        """When override is set, control loop uses override duty instead of temp ramp."""
        svc = FanService(mock_fan, config)
        svc.set_override(80)

        with patch("pi.services.fan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._control_loop()
            except asyncio.CancelledError:
                pass

        # Should use override value, not temp-derived value
        mock_fan.set_duty.assert_called_with(80)
        mock_fan.duty_for_time.assert_not_called()

    async def test_control_loop_auto_when_no_override(self, mock_fan, config):
        """When no override, control loop uses temp-based ramp as before."""
        svc = FanService(mock_fan, config)

        with patch("pi.services.fan.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._control_loop()
            except asyncio.CancelledError:
                pass

        mock_fan.duty_for_time.assert_called()
