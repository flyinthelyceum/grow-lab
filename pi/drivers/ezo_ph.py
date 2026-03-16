"""Atlas EZO-pH driver — reservoir pH measurement.

Communicates over I²C using the shared EZO protocol. Sends a "R"
command, waits ~900ms, reads back an ASCII pH value (e.g., "6.42").

Valid pH range: 0.00 – 14.00.
Default I²C address: 0x63 (99 decimal), set via `I2C,99` command
during UART-to-I²C mode switch.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pi.data.models import SensorReading
from pi.drivers.ezo_base import EZOBase

logger = logging.getLogger(__name__)

PH_MIN = 0.0
PH_MAX = 14.0


class EZOPhDriver(EZOBase):
    """I²C driver for the Atlas EZO-pH circuit."""

    def __init__(self, bus_number: int = 1, address: int = 0x63) -> None:
        super().__init__(bus_number=bus_number, address=address)

    @property
    def sensor_id(self) -> str:
        return "ezo_ph"

    def _parse_response(self, data: str) -> list[SensorReading]:
        """Parse pH value from EZO ASCII response.

        Returns a single SensorReading or empty list if invalid.
        """
        try:
            ph = float(data.strip())
        except ValueError:
            logger.warning("EZO-pH: cannot parse '%s' as float", data)
            return []

        if ph < PH_MIN or ph > PH_MAX:
            logger.warning("EZO-pH: value %.2f outside valid range [0, 14]", ph)
            return []

        return [
            SensorReading(
                timestamp=datetime.now(timezone.utc),
                sensor_id="ezo_ph",
                value=round(ph, 2),
                unit="pH",
            )
        ]
