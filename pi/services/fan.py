"""Fan control service — temperature-triggered PWM ramp.

Polls the latest air temperature reading from the repository and
adjusts the Noctua fan duty cycle according to a linear ramp curve.
Runs as an async background task alongside polling and irrigation.
"""

from __future__ import annotations

import asyncio
import logging

from pi.config.schema import FanConfig
from pi.drivers.fan_pwm import FanPWMDriver

logger = logging.getLogger(__name__)

# Sensor IDs that carry air temperature (stored as °C in the DB)
_TEMP_SENSOR_IDS = ("bme280_temperature",)


def _c_to_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


class FanService:
    """Background service that maps air temperature to fan PWM duty."""

    def __init__(
        self,
        fan: FanPWMDriver,
        repo,
        config: FanConfig,
    ) -> None:
        self._fan = fan
        self._repo = repo
        self._config = config
        self._task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start the fan control loop."""
        if self._task is not None:
            return

        if not self._config.enabled:
            logger.info("Fan service disabled in config")
            return

        if not self._fan.is_available:
            logger.warning("Fan PWM not available — skipping")
            return

        logger.info(
            "Fan service started (GPIO%d, ramp %.0f–%.0f°F)",
            self._config.gpio_pin,
            self._config.ramp_temp_low_f,
            self._config.ramp_temp_high_f,
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
        """Poll temperature and adjust fan duty cycle."""
        while True:
            try:
                temp_f = await self._get_air_temp_f()
                if temp_f is not None:
                    target = self._fan.duty_for_temperature(temp_f)
                    if target != self._fan.duty_cycle:
                        self._fan.set_duty(target)
                        logger.debug(
                            "Fan adjusted: %.1f°F → %d%% duty",
                            temp_f,
                            target,
                        )
            except Exception as exc:
                logger.debug("Fan control error: %s", exc)

            await asyncio.sleep(self._config.poll_interval_seconds)

    async def _get_air_temp_f(self) -> float | None:
        """Get the latest air temperature in Fahrenheit from the repo."""
        for sid in _TEMP_SENSOR_IDS:
            reading = await self._repo.get_latest(sid)
            if reading is not None:
                return _c_to_f(reading.value)
        return None
