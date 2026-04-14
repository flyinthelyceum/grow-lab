"""Async polling loop — one task per sensor, each on its own interval.

Each tick: read sensor -> construct SensorReading -> write to repository.
Errors are caught, logged, and counted. A single sensor failure does
not affect others. The loop never crashes.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any

from pi.config.schema import AppConfig
from pi.data.models import SensorReading
from pi.data.repository import SensorRepository
from pi.discovery.registry import SensorRegistry
from pi.drivers.base import SensorDriver
from pi.drivers.ezo_ec import EZOECDriver

logger = logging.getLogger(__name__)

# After this many consecutive failures, log a warning
FAILURE_WARNING_THRESHOLD = 3


class PollingService:
    """Manages async polling tasks for all available sensors."""

    def __init__(
        self,
        registry: SensorRegistry,
        repository: SensorRepository,
        config: AppConfig,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self._config = config
        self._tasks: list[asyncio.Task] = []
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Start a polling task for each available sensor."""
        if self._running:
            logger.warning("Polling service already running")
            return

        self._running = True
        drivers = self._registry.available_drivers

        if not drivers:
            logger.warning("No sensors available — polling service idle")
            return

        # Wire DS18B20 water temperature into EZO-EC compensation.
        # Before each EC read, fetch the latest DS18B20 value from the repo
        # and pass it to the driver so it sends T,<temp> before R.
        ec_temp_hook: Callable[[], Coroutine[Any, Any, None]] | None = None
        ec_driver = drivers.get("ezo_ec")
        ds18b20_ids = [s for s in drivers if s.startswith("ds18b20_")]
        if isinstance(ec_driver, EZOECDriver) and ds18b20_ids:
            ds18b20_id = ds18b20_ids[0]

            async def _inject_water_temp(
                _driver: EZOECDriver = ec_driver,
                _sid: str = ds18b20_id,
            ) -> None:
                reading = await self._repository.get_latest(_sid)
                if reading is not None:
                    _driver.update_temp(reading.value)

            ec_temp_hook = _inject_water_temp
            logger.info(
                "EC temperature compensation enabled via %s", ds18b20_id
            )

        for sensor_id, driver in drivers.items():
            interval = self._get_interval(sensor_id)
            hook = ec_temp_hook if sensor_id == "ezo_ec" else None
            task = asyncio.create_task(
                self._poll_loop(driver, interval, pre_poll=hook),
                name=f"poll-{sensor_id}",
            )
            self._tasks.append(task)
            logger.info(
                "Started polling %s every %ds", sensor_id, interval
            )

    async def stop(self) -> None:
        """Cancel all polling tasks and wait for them to finish."""
        self._running = False
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            logger.info("Stopped %d polling task(s)", len(self._tasks))

        self._tasks.clear()

    def _get_interval(self, sensor_id: str) -> int:
        """Look up the polling interval for a sensor from config."""
        sensor_configs = {
            "bme280": self._config.sensors.bme280,
            "ezo_ph": self._config.sensors.ezo_ph,
            "ezo_ec": self._config.sensors.ezo_ec,
            "ds18b20": self._config.sensors.ds18b20,
            "soil_moisture": self._config.sensors.soil_moisture,
            "as7341": self._config.sensors.as7341,
        }
        entry = sensor_configs.get(sensor_id)
        if entry is not None:
            return entry.interval_seconds
        return 120  # default fallback

    async def _poll_loop(
        self,
        driver: SensorDriver,
        interval: int,
        pre_poll: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """Poll a single sensor on a fixed interval.

        If pre_poll is provided it is awaited before each read — used to
        inject cross-sensor state (e.g. water temperature into EC driver).
        """
        consecutive_failures = 0

        try:
            while self._running:
                if pre_poll is not None:
                    try:
                        await pre_poll()
                    except Exception as exc:
                        logger.warning("Pre-poll hook failed for %s: %s", driver.sensor_id, exc)

                readings = await self._poll_once(driver)

                if readings:
                    for reading in readings:
                        await self._repository.save_reading(reading)
                    consecutive_failures = 0
                    logger.debug(
                        "Saved %d reading(s) from %s",
                        len(readings),
                        driver.sensor_id,
                    )
                else:
                    consecutive_failures += 1
                    if consecutive_failures == FAILURE_WARNING_THRESHOLD:
                        logger.warning(
                            "%s has failed %d consecutive reads",
                            driver.sensor_id,
                            consecutive_failures,
                        )

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.debug("Polling task for %s cancelled", driver.sensor_id)
            raise

    async def _poll_once(self, driver: SensorDriver) -> list[SensorReading]:
        """Execute a single poll. Returns readings or empty list on failure."""
        try:
            return await driver.read()
        except Exception as exc:
            logger.error(
                "Error reading %s: %s", driver.sensor_id, exc
            )
            return []
