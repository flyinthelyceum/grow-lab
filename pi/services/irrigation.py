"""Irrigation scheduler with safety limits.

Controls pump relay via the ESP32. Supports scheduled pulses and
manual one-shot pulses with configurable max runtime and minimum
interval between activations.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta, timezone

from pi.config.schema import IrrigationConfig
from pi.data.models import SystemEvent
from pi.data.repository import SensorRepository
from pi.drivers.esp32_serial import ESP32Serial

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Current UTC time (seam for testing)."""
    return datetime.now(timezone.utc)


class IrrigationService:
    """Manages scheduled and manual pump activation with safety limits."""

    def __init__(
        self,
        esp32: ESP32Serial,
        repository: SensorRepository,
        config: IrrigationConfig,
    ) -> None:
        self._esp32 = esp32
        self._repository = repository
        self._config = config
        self._task: asyncio.Task | None = None
        self._running = False
        self._pump_active = False
        self._last_activation: datetime | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def pump_active(self) -> bool:
        return self._pump_active

    @property
    def last_activation(self) -> datetime | None:
        return self._last_activation

    async def start(self) -> None:
        """Start the irrigation schedule loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(
            self._schedule_loop(), name="irrigation-scheduler"
        )
        schedule_desc = ", ".join(
            f"{s.hour:02d}:{s.minute:02d} ({s.duration_seconds}s)"
            for s in self._config.schedules
        )
        logger.info("Irrigation scheduler started: %s", schedule_desc)

    async def stop(self) -> None:
        """Stop the scheduler and ensure pump is off."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        await self._pump_off()
        logger.info("Irrigation scheduler stopped, pump off")

    async def pulse(self, duration_seconds: int) -> bool:
        """Run a single pump pulse with safety checks.

        Returns True if the pulse completed, False if blocked by safety limits.
        """
        clamped = min(duration_seconds, self._config.max_runtime_seconds)
        if clamped <= 0:
            logger.warning("Pulse rejected: duration %d <= 0", duration_seconds)
            return False

        if not self._check_min_interval():
            return False

        logger.info("Pump pulse: %ds (requested %ds)", clamped, duration_seconds)
        await self._pump_on()
        await self._log_event(f"Pump ON for {clamped}s")

        await asyncio.sleep(clamped)

        await self._pump_off()
        await self._log_event(f"Pump OFF after {clamped}s")
        return True

    def _check_min_interval(self) -> bool:
        """Verify minimum interval between pump activations."""
        if self._last_activation is None:
            return True

        elapsed = _utcnow() - self._last_activation
        min_gap = timedelta(minutes=self._config.min_interval_minutes)

        if elapsed < min_gap:
            remaining = min_gap - elapsed
            logger.warning(
                "Pump activation blocked: %d min remaining in cooldown",
                int(remaining.total_seconds() / 60) + 1,
            )
            return False

        return True

    async def _schedule_loop(self) -> None:
        """Check schedule every 30 seconds, trigger pulses at scheduled times."""
        fired_today: set[tuple[int, int]] = set()

        try:
            while self._running:
                now = _utcnow()
                current_time = now.time()
                today_key = now.date()

                # Reset fired set at midnight
                if hasattr(self, "_last_date") and self._last_date != today_key:
                    fired_today.clear()
                self._last_date = today_key

                for schedule in self._config.schedules:
                    key = (schedule.hour, schedule.minute)
                    if key in fired_today:
                        continue

                    sched_time = time(schedule.hour, schedule.minute)
                    # Fire if we're within 60 seconds past the scheduled time
                    sched_minutes = schedule.hour * 60 + schedule.minute
                    now_minutes = current_time.hour * 60 + current_time.minute
                    if now_minutes == sched_minutes:
                        fired_today.add(key)
                        await self.pulse(schedule.duration_seconds)

                await asyncio.sleep(30)

        except asyncio.CancelledError:
            raise

    async def _pump_on(self) -> None:
        """Turn the pump on via ESP32."""
        response = self._esp32.set_pump(True)
        self._pump_active = True
        self._last_activation = _utcnow()

        if response.ok:
            logger.debug("Pump ON")
        else:
            logger.warning("Pump ON command failed: %s", response.error)

    async def _pump_off(self) -> None:
        """Turn the pump off via ESP32."""
        response = self._esp32.set_pump(False)
        self._pump_active = False

        if response.ok:
            logger.debug("Pump OFF")
        else:
            logger.warning("Pump OFF command failed: %s", response.error)

    async def _log_event(self, description: str) -> None:
        """Log an irrigation event to the database."""
        await self._repository.save_event(
            SystemEvent(
                timestamp=_utcnow(),
                event_type="irrigation",
                description=description,
            )
        )
