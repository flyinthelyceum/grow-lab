"""Sensor driver protocol — the contract every hardware driver must follow.

Drivers return frozen SensorReading objects or None on failure.
No driver mutates shared state. Each is independently testable.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pi.data.models import SensorReading


@runtime_checkable
class SensorDriver(Protocol):
    """Interface for all sensor drivers."""

    @property
    def sensor_id(self) -> str:
        """Unique identifier for this sensor (e.g., 'bme280_temperature')."""
        ...

    async def read(self) -> list[SensorReading]:
        """Read current values from the sensor.

        Returns a list of SensorReading (some sensors produce multiple
        readings per poll, e.g., BME280 returns temp + humidity + pressure).
        Returns an empty list on failure.
        """
        ...

    async def is_available(self) -> bool:
        """Check if the sensor hardware is reachable."""
        ...

    async def close(self) -> None:
        """Release any hardware resources."""
        ...
