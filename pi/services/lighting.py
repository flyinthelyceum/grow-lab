"""Photoperiod lighting scheduler.

Controls light on/off cycles and intensity ramps via the ESP32.
Supports veg (16h/8h) and flower (12h/12h) modes with configurable
sunrise/sunset ramps to reduce plant stress.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timezone

from pi.config.schema import LightingConfig
from pi.data.models import SystemEvent
from pi.data.repository import SensorRepository
from pi.drivers.esp32_serial import ESP32Serial

logger = logging.getLogger(__name__)


def _time_now() -> time:
    """Current local time (hour, minute)."""
    return datetime.now().time()


def _is_light_on(config: LightingConfig, current_time: time) -> bool:
    """Determine if lights should be on based on schedule.

    Handles schedules that wrap past midnight (e.g., on_hour=22, off_hour=14).
    """
    on = time(config.on_hour, 0)
    off = time(config.off_hour, 0)

    if on < off:
        # Normal schedule: e.g., 6:00 to 22:00
        return on <= current_time < off
    else:
        # Wraps midnight: e.g., 22:00 to 14:00
        return current_time >= on or current_time < off


def _minutes_since(reference: int, now: int) -> int:
    """Minutes elapsed from reference to now, handling midnight wrap."""
    diff = now - reference
    if diff < 0:
        diff += 1440  # 24 * 60
    return diff


def compute_ramp_intensity(
    config: LightingConfig,
    current_time: time,
) -> int:
    """Compute the target PWM intensity including sunrise/sunset ramp.

    Returns 0 if lights should be off, config.intensity if fully on,
    or a linearly interpolated value during ramp periods.
    Handles schedules that wrap past midnight correctly.
    """
    light_on = _is_light_on(config, current_time)

    if config.ramp_minutes <= 0 or not light_on:
        return config.intensity if light_on else 0

    on_minutes = config.on_hour * 60
    off_minutes = config.off_hour * 60
    now_minutes = current_time.hour * 60 + current_time.minute
    ramp = config.ramp_minutes

    # Minutes since light-on time (handles midnight wrap)
    since_on = _minutes_since(on_minutes, now_minutes)

    # Sunrise ramp: first `ramp` minutes after on_hour
    if since_on < ramp:
        progress = since_on / ramp
        return int(config.intensity * progress)

    # Minutes until light-off time (handles midnight wrap)
    until_off = _minutes_since(now_minutes, off_minutes)

    # Sunset ramp: last `ramp` minutes before off_hour
    if until_off <= ramp:
        progress = until_off / ramp
        return int(config.intensity * progress)

    # Fully on (between sunrise end and sunset start)
    return config.intensity


class LightingScheduler:
    """Manages the photoperiod schedule and sends commands to ESP32."""

    def __init__(
        self,
        esp32: ESP32Serial,
        repository: SensorRepository,
        config: LightingConfig,
    ) -> None:
        self._esp32 = esp32
        self._repository = repository
        self._config = config
        self._task: asyncio.Task | None = None
        self._running = False
        self._current_pwm: int = -1  # Track to avoid redundant commands

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_pwm(self) -> int:
        return max(self._current_pwm, 0)

    async def start(self) -> None:
        """Start the lighting schedule loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(
            self._schedule_loop(), name="lighting-scheduler"
        )
        logger.info(
            "Lighting scheduler started: mode=%s, on=%02d:00, off=%02d:00, intensity=%d",
            self._config.mode,
            self._config.on_hour,
            self._config.off_hour,
            self._config.intensity,
        )

    async def stop(self) -> None:
        """Stop the schedule and turn lights off."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # Turn off lights on shutdown
        await self._set_pwm(0)
        logger.info("Lighting scheduler stopped, lights off")

    async def set_manual(self, pwm: int) -> None:
        """Manually override the light intensity (0-255)."""
        await self._set_pwm(pwm)
        await self._log_event(f"Manual light set to {pwm}")

    async def _schedule_loop(self) -> None:
        """Check the schedule every 30 seconds and adjust PWM."""
        try:
            while self._running:
                target = compute_ramp_intensity(self._config, _time_now())

                if target != self._current_pwm:
                    await self._set_pwm(target)

                await asyncio.sleep(30)

        except asyncio.CancelledError:
            raise

    async def _set_pwm(self, pwm: int) -> None:
        """Send a LIGHT command to the ESP32."""
        response = self._esp32.set_light(pwm)
        old_pwm = self._current_pwm
        self._current_pwm = pwm

        if response.ok:
            logger.debug("Light PWM: %d -> %d", old_pwm, pwm)
        else:
            logger.warning(
                "Light command failed (PWM %d): %s", pwm, response.error
            )

    async def _log_event(self, description: str) -> None:
        """Log a lighting event to the database."""
        await self._repository.save_event(
            SystemEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="light_change",
                description=description,
            )
        )
