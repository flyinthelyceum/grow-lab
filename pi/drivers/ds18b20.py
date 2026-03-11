"""DS18B20 driver — 1-Wire waterproof temperature probe.

Reads temperature from the Linux kernel 1-Wire interface at
/sys/bus/w1/devices/28-xxxx/w1_slave. The kernel handles bus
timing and CRC — we just parse the sysfs file.

w1_slave file format (two lines):
  Line 1: hex bytes + "crc=XX YES" (or "NO" on CRC failure)
  Line 2: hex bytes + "t=NNNNN" (temperature in millidegrees C)

The DS18B20 reports 85000 (85°C) as its power-on reset value,
which we discard as invalid.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pi.data.models import SensorReading

logger = logging.getLogger(__name__)

# DS18B20 power-on reset value in millidegrees — not a real reading
_POWER_ON_RESET_MILLIDEGREES = 85000


class DS18B20Driver:
    """1-Wire driver for DS18B20 temperature sensors."""

    def __init__(self, device_id: str, device_path: Path) -> None:
        self._device_id = device_id
        self._device_path = device_path

    @property
    def sensor_id(self) -> str:
        return f"ds18b20_{self._device_id}"

    async def read(self) -> list[SensorReading]:
        """Read temperature from the 1-Wire sysfs file.

        Returns a single SensorReading or empty list on failure.
        """
        try:
            content = await asyncio.to_thread(self._read_file)
            if content is None:
                return []

            temp_c = _parse_w1_slave(content)
            if temp_c is None:
                return []

            from datetime import datetime, timezone

            return [
                SensorReading(
                    timestamp=datetime.now(timezone.utc),
                    sensor_id=self.sensor_id,
                    value=temp_c,
                    unit="°C",
                )
            ]
        except Exception as exc:
            logger.error("DS18B20 %s read failed: %s", self._device_id, exc)
            return []

    async def is_available(self) -> bool:
        """Check if the 1-Wire device file exists."""
        return self._device_path.exists()

    async def close(self) -> None:
        """No persistent connection to release for 1-Wire."""

    def _read_file(self) -> str | None:
        """Synchronous file read (called via to_thread)."""
        try:
            return self._device_path.read_text()
        except OSError as exc:
            logger.warning("Cannot read %s: %s", self._device_path, exc)
            return None


def _parse_w1_slave(content: str) -> float | None:
    """Parse a w1_slave file and return temperature in Celsius.

    Returns None if CRC check failed, temperature field is missing,
    or the value is the 85°C power-on reset.
    """
    lines = content.strip().splitlines()
    if len(lines) < 2:
        return None

    # Line 1 must end with "YES" for valid CRC
    if not lines[0].rstrip().endswith("YES"):
        return None

    # Line 2 contains "t=NNNNN" with temperature in millidegrees
    parts = lines[1].split("t=")
    if len(parts) < 2:
        return None

    try:
        millidegrees = int(parts[1])
    except ValueError:
        return None

    if millidegrees == _POWER_ON_RESET_MILLIDEGREES:
        logger.warning("DS18B20 returned power-on reset value (85°C), discarding")
        return None

    return millidegrees / 1000.0
