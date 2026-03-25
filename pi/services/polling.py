"""Async polling loop — one task per sensor, each on its own interval.

Each tick: read sensor -> construct SensorReading -> write to repository.
Errors are caught, logged, and counted. A single sensor failure does
not affect others. The loop never crashes.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from pi.config.schema import AppConfig
from pi.data.models import SensorReading
from pi.data.repository import SensorRepository
from pi.discovery.registry import SensorRegistry
from pi.drivers.base import SensorDriver

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

        for sensor_id, driver in drivers.items():
            interval = self._get_interval(sensor_id)
            task = asyncio.create_task(
                self._poll_loop(driver, interval),
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

    async def _poll_loop(self, driver: SensorDriver, interval: int) -> None:
        """Poll a single sensor on a fixed interval."""
        consecutive_failures = 0

        try:
            while self._running:
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
