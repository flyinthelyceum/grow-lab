"""Atlas EZO-EC driver — reservoir electrical conductivity measurement.

Communicates over I²C using the shared EZO protocol. Sends a "R"
command, waits ~900ms, reads back an ASCII EC value in µS/cm
(e.g., "1413.00").

Valid range: 0 – 200,000 µS/cm (Atlas EZO-EC spec).
Default I²C address: 0x64 (100 decimal), set via `I2C,100` command
during UART-to-I²C mode switch.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pi.data.models import SensorReading
from pi.drivers.ezo_base import EZOBase

logger = logging.getLogger(__name__)

EC_MIN = 0.0
EC_MAX = 200_000.0


class EZOECDriver(EZOBase):
    """I²C driver for the Atlas EZO-EC circuit."""

    def __init__(self, bus_number: int = 1, address: int = 0x64) -> None:
        super().__init__(bus_number=bus_number, address=address)

    @property
    def sensor_id(self) -> str:
        return "ezo_ec"

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
