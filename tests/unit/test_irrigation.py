"""Tests for the irrigation scheduler service."""

from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import IrrigationConfig, IrrigationScheduleEntry
from pi.drivers.esp32_serial import ESP32Response
from pi.services.irrigation import IrrigationService


def _ok_response() -> ESP32Response:
    return ESP32Response(raw='{"ok":true}', data={"ok": True}, ok=True)


def _fail_response() -> ESP32Response:
    return ESP32Response(raw="", data={}, ok=False, error="not connected")


def _make_service(
    config: IrrigationConfig | None = None,
) -> tuple[IrrigationService, MagicMock, AsyncMock]:
    esp32 = MagicMock()
    esp32.set_pump.return_value = _ok_response()
    repo = AsyncMock()
    cfg = config or IrrigationConfig()
    service = IrrigationService(esp32, repo, cfg)
    return service, esp32, repo


class TestIrrigationServiceInit:
    def test_initial_state(self) -> None:
        service, _, _ = _make_service()
        assert service.is_running is False
        assert service.pump_active is False
        assert service.last_activation is None


class TestPulse:
    async def test_pulse_turns_pump_on_and_off(self) -> None:
        service, esp32, repo = _make_service()

        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock):
            result = await service.pulse(5)

        assert result is True
        assert esp32.set_pump.call_count == 2
        # First call: ON, second call: OFF
        esp32.set_pump.assert_any_call(True)
        esp32.set_pump.assert_any_call(False)
        assert service.pump_active is False

    async def test_pulse_clamps_to_max_runtime(self) -> None:
        config = IrrigationConfig(max_runtime_seconds=10)
        service, _, repo = _make_service(config)

        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await service.pulse(60)

        # Should sleep for max_runtime (10), not requested (60)
        mock_sleep.assert_called_once_with(10)

    async def test_pulse_logs_events(self) -> None:
        service, _, repo = _make_service()

        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock):
            await service.pulse(5)

        assert repo.save_event.call_count == 2
        events = [call[0][0] for call in repo.save_event.call_args_list]
        assert "ON" in events[0].description
        assert "OFF" in events[1].description
        assert all(e.event_type == "irrigation" for e in events)

    async def test_pulse_rejected_zero_duration(self) -> None:
        config = IrrigationConfig(max_runtime_seconds=0)
        service, esp32, _ = _make_service(config)

        result = await service.pulse(5)

        assert result is False
        esp32.set_pump.assert_not_called()

    async def test_pulse_records_last_activation(self) -> None:
        service, _, _ = _make_service()
        assert service.last_activation is None

        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock):
            await service.pulse(5)

        assert service.last_activation is not None


class TestMinInterval:
    async def test_cooldown_blocks_second_pulse(self) -> None:
        config = IrrigationConfig(min_interval_minutes=60)
        service, esp32, _ = _make_service(config)

        # First pulse succeeds
        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock):
            result1 = await service.pulse(5)
        assert result1 is True

        # Second pulse immediately after should be blocked
        result2 = await service.pulse(5)
        assert result2 is False

    async def test_cooldown_allows_after_interval(self) -> None:
        config = IrrigationConfig(min_interval_minutes=60)
        service, _, _ = _make_service(config)

        # Simulate a pulse that happened 61 minutes ago
        service._last_activation = datetime.now(timezone.utc) - timedelta(minutes=61)

        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock):
            result = await service.pulse(5)
        assert result is True

    async def test_no_cooldown_on_first_pulse(self) -> None:
        service, _, _ = _make_service()
        assert service.last_activation is None

        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock):
            result = await service.pulse(5)
        assert result is True


class TestScheduleLoop:
    async def test_schedule_fires_at_correct_time(self) -> None:
        config = IrrigationConfig(
            schedules=(IrrigationScheduleEntry(hour=12, minute=0, duration_seconds=5),),
        )
        service, esp32, _ = _make_service(config)
        service._running = True

        now = datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc)

        call_count = 0

        async def counting_sleep(seconds: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()

        with patch("pi.services.irrigation._utcnow", return_value=now):
            with patch("pi.services.irrigation.asyncio.sleep", side_effect=counting_sleep):
                try:
                    await service._schedule_loop()
                except asyncio.CancelledError:
                    pass

        # Should have activated the pump (set_pump True then False)
        assert esp32.set_pump.call_count >= 2

    async def test_schedule_skips_wrong_time(self) -> None:
        config = IrrigationConfig(
            schedules=(IrrigationScheduleEntry(hour=12, minute=0, duration_seconds=5),),
        )
        service, esp32, _ = _make_service(config)
        service._running = True

        # 11:00 — not scheduled
        now = datetime(2026, 3, 11, 11, 0, 0, tzinfo=timezone.utc)

        with patch("pi.services.irrigation._utcnow", return_value=now):
            with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError()]
                try:
                    await service._schedule_loop()
                except asyncio.CancelledError:
                    pass

        esp32.set_pump.assert_not_called()

    async def test_schedule_fires_only_once_per_day(self) -> None:
        config = IrrigationConfig(
            schedules=(IrrigationScheduleEntry(hour=12, minute=0, duration_seconds=5),),
            min_interval_minutes=0,  # No cooldown for this test
        )
        service, esp32, _ = _make_service(config)
        service._running = True

        now = datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc)
        loop_count = 0

        async def fast_sleep(seconds: float) -> None:
            nonlocal loop_count
            loop_count += 1
            if loop_count >= 3:
                raise asyncio.CancelledError()

        with patch("pi.services.irrigation._utcnow", return_value=now):
            with patch("pi.services.irrigation.asyncio.sleep", side_effect=fast_sleep):
                try:
                    await service._schedule_loop()
                except asyncio.CancelledError:
                    pass

        # Pump should only fire once even though we looped 3 times at 12:00
        # set_pump called twice per pulse (on + off)
        assert esp32.set_pump.call_count == 2


class TestPulseStartCallback:
    async def test_on_pulse_start_fires_during_pump_active(self) -> None:
        """on_pulse_start should fire while the pump is still running."""
        callback = AsyncMock()
        service, esp32, repo = _make_service()
        service._on_pulse_start = callback
        service._pulse_start_delay = 3.0

        sleep_calls = []

        async def track_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        with patch("pi.services.irrigation.asyncio.sleep", side_effect=track_sleep):
            await service.pulse(10)

        callback.assert_called_once()
        # Should sleep 3s (delay), then callback, then 7s (remainder)
        assert sleep_calls[0] == 3.0
        assert sleep_calls[1] == 7.0

    async def test_on_pulse_start_skipped_for_short_pulse(self) -> None:
        """on_pulse_start should not fire if pulse is shorter than delay."""
        callback = AsyncMock()
        config = IrrigationConfig(max_runtime_seconds=2)
        service, esp32, repo = _make_service(config)
        service._on_pulse_start = callback
        service._pulse_start_delay = 3.0

        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock):
            await service.pulse(2)

        callback.assert_not_called()

    async def test_on_pulse_start_error_doesnt_block_pump(self) -> None:
        """Callback error should not prevent pump from turning off."""
        callback = AsyncMock(side_effect=RuntimeError("camera failed"))
        service, esp32, repo = _make_service()
        service._on_pulse_start = callback
        service._pulse_start_delay = 1.0

        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock):
            result = await service.pulse(10)

        assert result is True
        esp32.set_pump.assert_any_call(False)  # Pump still turned off

    async def test_both_callbacks_can_fire(self) -> None:
        """Both on_pulse_start and on_pulse_complete can coexist."""
        start_cb = AsyncMock()
        complete_cb = AsyncMock()
        service, esp32, repo = _make_service()
        service._on_pulse_start = start_cb
        service._on_pulse_complete = complete_cb
        service._pulse_start_delay = 1.0

        with patch("pi.services.irrigation.asyncio.sleep", new_callable=AsyncMock):
            await service.pulse(10)

        start_cb.assert_called_once()
        complete_cb.assert_called_once()


class TestStartStop:
    async def test_start_creates_task(self) -> None:
        service, _, _ = _make_service()
        await service.start()
        assert service.is_running is True
        assert service._task is not None
        await service.stop()

    async def test_start_idempotent(self) -> None:
        service, _, _ = _make_service()
        await service.start()
        task1 = service._task
        await service.start()
        assert service._task is task1
        await service.stop()

    async def test_stop_turns_pump_off(self) -> None:
        service, esp32, _ = _make_service()
        await service.start()
        await service.stop()
        assert service.is_running is False
        esp32.set_pump.assert_called_with(False)

    async def test_pump_command_failure_still_updates_state(self) -> None:
        service, esp32, _ = _make_service()
        esp32.set_pump.return_value = _fail_response()

        await service._pump_on()
        assert service.pump_active is True

        await service._pump_off()
        assert service.pump_active is False
