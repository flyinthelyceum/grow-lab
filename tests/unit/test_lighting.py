"""Tests for the photoperiod lighting scheduler."""

from __future__ import annotations

import asyncio
from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import LightingConfig
from pi.drivers.esp32_serial import ESP32Response
from pi.services.lighting import (
    LightingScheduler,
    _is_light_on,
    compute_ramp_intensity,
)


# --- Schedule logic ---


class TestIsLightOn:
    """Test light-on/off schedule determination."""

    def _config(self, on: int, off: int) -> LightingConfig:
        return LightingConfig(mode="veg", on_hour=on, off_hour=off, intensity=255)

    def test_normal_schedule_on(self) -> None:
        # 6:00 to 22:00 — check at noon
        assert _is_light_on(self._config(6, 22), time(12, 0)) is True

    def test_normal_schedule_off(self) -> None:
        # 6:00 to 22:00 — check at 23:00
        assert _is_light_on(self._config(6, 22), time(23, 0)) is False

    def test_normal_schedule_boundary_on(self) -> None:
        assert _is_light_on(self._config(6, 22), time(6, 0)) is True

    def test_normal_schedule_boundary_off(self) -> None:
        assert _is_light_on(self._config(6, 22), time(22, 0)) is False

    def test_midnight_wrap_on_evening(self) -> None:
        # 22:00 to 14:00 — check at 23:00
        assert _is_light_on(self._config(22, 14), time(23, 0)) is True

    def test_midnight_wrap_on_morning(self) -> None:
        # 22:00 to 14:00 — check at 8:00
        assert _is_light_on(self._config(22, 14), time(8, 0)) is True

    def test_midnight_wrap_off(self) -> None:
        # 22:00 to 14:00 — check at 15:00
        assert _is_light_on(self._config(22, 14), time(15, 0)) is False

    def test_midnight_wrap_boundary_on(self) -> None:
        assert _is_light_on(self._config(22, 14), time(22, 0)) is True

    def test_midnight_wrap_boundary_off(self) -> None:
        assert _is_light_on(self._config(22, 14), time(14, 0)) is False


class TestComputeRampIntensity:
    """Test sunrise/sunset ramp calculations."""

    def _config(self, on: int = 6, off: int = 22, intensity: int = 200, ramp: int = 30) -> LightingConfig:
        return LightingConfig(mode="veg", on_hour=on, off_hour=off, intensity=intensity, ramp_minutes=ramp)

    def test_off_period_returns_zero(self) -> None:
        assert compute_ramp_intensity(self._config(), time(23, 0)) == 0

    def test_fully_on_returns_intensity(self) -> None:
        assert compute_ramp_intensity(self._config(), time(12, 0)) == 200

    def test_sunrise_start_returns_zero(self) -> None:
        # At exactly on_hour, progress=0 → intensity=0
        assert compute_ramp_intensity(self._config(), time(6, 0)) == 0

    def test_sunrise_midpoint(self) -> None:
        # 15 min into 30 min ramp → 50% of 200 = 100
        assert compute_ramp_intensity(self._config(), time(6, 15)) == 100

    def test_sunrise_end(self) -> None:
        # At 6:30 (end of ramp) → fully on
        assert compute_ramp_intensity(self._config(), time(6, 30)) == 200

    def test_sunset_start(self) -> None:
        # 30 min before off (21:30), full ramp remaining → intensity
        result = compute_ramp_intensity(self._config(), time(21, 30))
        assert result == 200

    def test_sunset_midpoint(self) -> None:
        # 15 min before off (21:45), progress=0.5 → 100
        assert compute_ramp_intensity(self._config(), time(21, 45)) == 100

    def test_sunset_near_end(self) -> None:
        # 1 min before off → very dim
        result = compute_ramp_intensity(self._config(), time(21, 59))
        assert 0 < result < 20

    def test_no_ramp_on(self) -> None:
        cfg = self._config(ramp=0)
        assert compute_ramp_intensity(cfg, time(12, 0)) == 200

    def test_no_ramp_off(self) -> None:
        cfg = self._config(ramp=0)
        assert compute_ramp_intensity(cfg, time(23, 0)) == 0


# --- LightingScheduler ---


def _ok_response(pwm: int = 0) -> ESP32Response:
    return ESP32Response(raw=f'{{"ok":true,"pwm":{pwm}}}', data={"ok": True, "pwm": pwm}, ok=True)


def _make_scheduler(config: LightingConfig | None = None) -> tuple[LightingScheduler, MagicMock, AsyncMock]:
    esp32 = MagicMock()
    esp32.set_light.return_value = _ok_response()
    repo = AsyncMock()
    cfg = config or LightingConfig(mode="veg", on_hour=6, off_hour=22, intensity=200)
    scheduler = LightingScheduler(esp32, repo, cfg)
    return scheduler, esp32, repo


class TestLightingScheduler:
    def test_initial_state(self) -> None:
        scheduler, _, _ = _make_scheduler()
        assert scheduler.is_running is False
        assert scheduler.current_pwm == 0

    async def test_start_creates_task(self) -> None:
        scheduler, _, _ = _make_scheduler()
        await scheduler.start()
        assert scheduler.is_running is True
        assert scheduler._task is not None
        await scheduler.stop()

    async def test_start_idempotent(self) -> None:
        scheduler, _, _ = _make_scheduler()
        await scheduler.start()
        task1 = scheduler._task
        await scheduler.start()  # second call should be no-op
        assert scheduler._task is task1
        await scheduler.stop()

    async def test_stop_turns_off_lights(self) -> None:
        scheduler, esp32, _ = _make_scheduler()
        await scheduler.start()
        await scheduler.stop()
        assert scheduler.is_running is False
        # Last call should be set_light(0)
        esp32.set_light.assert_called_with(0)

    async def test_set_manual(self) -> None:
        scheduler, esp32, repo = _make_scheduler()
        esp32.set_light.return_value = _ok_response(128)

        await scheduler.set_manual(128)

        esp32.set_light.assert_called_once_with(128)
        repo.save_event.assert_called_once()
        event = repo.save_event.call_args[0][0]
        assert "128" in event.description

    async def test_schedule_loop_sets_pwm(self) -> None:
        scheduler, esp32, _ = _make_scheduler()
        scheduler._running = True

        # Mock time to noon (lights should be fully on)
        with patch("pi.services.lighting._time_now", return_value=time(12, 0)):
            with patch("pi.services.lighting.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError()]
                try:
                    await scheduler._schedule_loop()
                except asyncio.CancelledError:
                    pass

        esp32.set_light.assert_called_with(200)

    async def test_schedule_loop_skips_redundant(self) -> None:
        scheduler, esp32, _ = _make_scheduler()
        scheduler._current_pwm = 200  # Already at target

        with patch("pi.services.lighting._time_now", return_value=time(12, 0)):
            with patch("pi.services.lighting.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError()]
                scheduler._running = True
                try:
                    await scheduler._schedule_loop()
                except asyncio.CancelledError:
                    pass

        # Should not have called set_light since PWM hasn't changed
        esp32.set_light.assert_not_called()

    async def test_set_pwm_logs_failure(self) -> None:
        scheduler, esp32, _ = _make_scheduler()
        esp32.set_light.return_value = ESP32Response(
            raw="", data={}, ok=False, error="not connected"
        )

        await scheduler._set_pwm(128)
        assert scheduler._current_pwm == -1  # Not updated on failure — forces retry
