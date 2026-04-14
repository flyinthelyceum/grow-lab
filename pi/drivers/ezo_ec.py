"""Atlas EZO-EC driver — reservoir electrical conductivity measurement.

Communicates over I²C using the shared EZO protocol. Sends a "R"
command, waits ~900ms, reads back an ASCII EC value in µS/cm
(e.g., "1413.00").

Valid range: 0 – 200,000 µS/cm (Atlas EZO-EC spec).
Default I²C address: 0x64 (100 decimal), set via `I2C,100` command
during UART-to-I²C mode switch.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from pi.data.models import SensorReading
from pi.drivers.ezo_base import EZOBase, READ_DELAY_MS, STATUS_SUCCESS

logger = logging.getLogger(__name__)

EC_MIN = 0.0
EC_MAX = 200_000.0

# Wait time for the T (temperature compensation) command (ms)
TEMP_CMD_DELAY_MS = 300


class EZOECDriver(EZOBase):
    """I²C driver for the Atlas EZO-EC circuit."""

    def __init__(self, bus_number: int = 1, address: int = 0x64) -> None:
        super().__init__(bus_number=bus_number, address=address)
        self._temp_c: float | None = None

    @property
    def sensor_id(self) -> str:
        return "ezo_ec"

    def update_temp(self, temp_c: float) -> None:
        """Set the water temperature used for EC compensation on the next read.

        The Atlas EZO-EC defaults to 25°C compensation when no temperature is
        provided. Call this before each read() with the latest DS18B20 value to
        correct for actual solution temperature (~2% EC error per °C deviation).
        """
        self._temp_c = temp_c

    async def read(self) -> list[SensorReading]:
        """Send optional temperature compensation then a read command.

        Overrides EZOBase.read() to inject T,<temp> before R when a water
        temperature is available via update_temp().
        """
        try:
            temp_c = self._temp_c

            def _do_read():
                if temp_c is not None:
                    self._send_command(f"T,{temp_c:.2f}")
                    time.sleep(TEMP_CMD_DELAY_MS / 1000.0)
                self._send_command("R")
                time.sleep(READ_DELAY_MS / 1000.0)
                return self._read_response()

            status, data = await asyncio.to_thread(_do_read)

            if status != STATUS_SUCCESS:
                logger.warning(
                    "%s read status %d (expected 1)", self.sensor_id, status
                )
                return []

            return self._parse_response(data)

        except Exception as exc:
            logger.error("%s read failed: %s", self.sensor_id, exc)
            return []

    def _parse_response(self, data: str) -> list[SensorReading]:
        """Parse EC value from EZO ASCII response.

        Returns a single SensorReading or empty list if invalid.
        """
        try:
            ec = float(data.strip())
        except ValueError:
            logger.warning("EZO-EC: cannot parse '%s' as float", data)
            return []

        if ec < EC_MIN or ec > EC_MAX:
            logger.warning(
                "EZO-EC: value %.2f outside valid range [0, 200000]", ec
            )
            return []

        return [
            SensorReading(
                timestamp=datetime.now(timezone.utc),
                sensor_id="ezo_ec",
                value=round(ec, 2),
                unit="µS/cm",
            )
        ]
