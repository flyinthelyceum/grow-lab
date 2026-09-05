"""Fan control service — a gust field, not a thermostat.

The fan is for canopy strength: moving air thickens stems. So duty comes from
a deterministic gust field over wall-clock time, gated by the plant's own
photoperiod, and takes no sensor input at all. It reads no temperature and
needs no repository.
"""

from __future__ import annotations

import asyncio
import logging
import time

from pi.config.schema import FanConfig
from pi.drivers.fan_pwm import FanPWMDriver

logger = logging.getLogger(__name__)


class FanService:
    """Background service that drives the fan from a gust field."""

    def __init__(
        self,
        fan: FanPWMDriver,
        config: FanConfig,
    ) -> None:
        self._fan = fan
        self._config = config
        self._task: asyncio.Task | None = None
        self._override_duty: int | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def override_duty(self) -> int | None:
        """Current manual override duty, or None if in auto mode."""
        return self._override_duty

    def set_override(self, duty: int) -> None:
        """Set a manual duty cycle override (0-100)."""
        self._override_duty = max(0, min(100, duty))

    def clear_override(self) -> None:
        """Return to the automatic gust field."""
        self._override_duty = None

    async def start(self) -> None:
        """Start the fan control loop."""
        if self.is_running:
            return

        if not self._config.enabled:
            logger.info("Fan service disabled in config")
            return

        if not self._fan.is_available:
            logger.warning("Fan PWM not available — skipping")
            return

        logger.info(
            "Fan service started (GPIO%d, gusts %02d:00–%02d:00, calm %.0f%%)",
            self._config.gpio_pin,
            self._config.day_start_hour,
            self._config.day_end_hour,
            self._config.calm_threshold * 100,
        )
        self._task = asyncio.create_task(
            self._control_loop(), name="fan-control"
        )

    async def stop(self) -> None:
        """Stop the fan and release resources."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._fan.close()

    async def _control_loop(self) -> None:
        """Follow the gust field."""
        while True:
            try:
                if self._override_duty is not None:
                    target = self._override_duty
                    if target != self._fan.duty_cycle:
                        self._fan.set_duty(target)
                        logger.debug("Fan override: %d%% duty", target)
                else:
                    target = self._fan.duty_for_time(time.time())
                    if target != self._fan.duty_cycle:
                        self._fan.set_duty(target)
                        logger.debug("Fan gust: %d%% duty", target)
            except Exception as exc:
                logger.error("Fan control error: %s", exc, exc_info=True)

            await asyncio.sleep(self._config.poll_interval_seconds)
