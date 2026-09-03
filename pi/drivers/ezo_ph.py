"""Atlas EZO-pH driver — reservoir pH measurement.

Communicates over I²C using the shared EZO protocol. Sends a "R"
command, waits ~900ms, reads back an ASCII pH value (e.g., "6.42").

Valid pH range: 0.00 – 14.00.
Default I²C address: 0x63 (99 decimal), set via `I2C,99` command
during UART-to-I²C mode switch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from pi.data.models import SensorReading
from pi.drivers.ezo_base import EZOBase

logger = logging.getLogger(__name__)

PH_MIN = 0.0
PH_MAX = 14.0

# Probe health thresholds, from the EZO-pH datasheet (V6.1), "Understanding
# pH slope", pages 68-70. These are the manufacturer's numbers, not ours:
#
#   "A new pH probe should have a slope of >95%."
#   "A new pH probe should give a millivolt offset no greater than -5mV to
#    5mV ... A reading >10mV will result in noticeable performance issues."
#
# Slope is how closely the probe's calibrated response matched an ideal
# probe, separately for the acid (pH 1-6.9) and base (pH 7.1-14) halves.
# Offset is how far its zero point sits from true 0 mV at pH 7.
SLOPE_HEALTHY_PERCENT = 95.0
OFFSET_HEALTHY_MV = 5.0
OFFSET_DEGRADED_MV = 10.0

# The circuit reports exactly this before any calibration has been done: a
# mathematically perfect probe, which does not exist. Reading it back means
# the slope is meaningless, not that the probe is flawless.
UNCALIBRATED_SLOPE = (100.0, 100.0, 0.0)


@dataclass(frozen=True)
class ProbeSlope:
    """Probe health, as reported by the EZO-pH `Slope,?` command.

    Slope is only updated by a calibration — it does not refresh on its own.
    So this describes the probe as of its last calibration, not as of now.
    """

    acid_percent: float
    base_percent: float
    offset_mv: float

    @property
    def is_uncalibrated(self) -> bool:
        """True when the circuit is reporting its pre-calibration default."""
        return (
            self.acid_percent,
            self.base_percent,
            self.offset_mv,
        ) == UNCALIBRATED_SLOPE

    @property
    def worst_slope(self) -> float:
        return min(self.acid_percent, self.base_percent)

    @property
    def verdict(self) -> str:
        """One of: uncalibrated, healthy, marginal, failing."""
        if self.is_uncalibrated:
            return "uncalibrated"

        offset = abs(self.offset_mv)
        if self.worst_slope >= SLOPE_HEALTHY_PERCENT and offset <= OFFSET_HEALTHY_MV:
            return "healthy"
        if self.worst_slope >= SLOPE_HEALTHY_PERCENT and offset <= OFFSET_DEGRADED_MV:
            return "marginal"
        if self.worst_slope < SLOPE_HEALTHY_PERCENT or offset > OFFSET_DEGRADED_MV:
            return "failing"
        return "marginal"


def parse_slope(data: str) -> ProbeSlope | None:
    """Parse a `Slope,?` response: `?Slope,99.7,100.3,-0.89`.

    Returns None if the response is not that shape, so a garbled read is
    never mistaken for a health verdict.
    """
    text = data.strip().lstrip("?")
    if not text.lower().startswith("slope,"):
        logger.warning("EZO-pH: %r is not a Slope response", data)
        return None

    parts = [p.strip() for p in text.split(",")[1:]]
    if len(parts) < 3:
        logger.warning("EZO-pH: Slope response %r has too few fields", data)
        return None

    try:
        acid, base, offset = (float(p) for p in parts[:3])
    except ValueError:
        logger.warning("EZO-pH: cannot parse Slope numbers from %r", data)
        return None

    return ProbeSlope(acid_percent=acid, base_percent=base, offset_mv=offset)


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

    async def read_slope(self) -> ProbeSlope | None:
        """Query probe health via the `Slope,?` command.

        The datasheet calls slope "a powerful tool used to verify calibration
        and determine the overall health of a pH probe ... or when that probe
        is reaching end of life." It is the honest way to decide whether a
        probe is worth reconditioning, as opposed to reading a buffer and
        squinting at the number.

        Note the caveat the datasheet raises: a bad number is not proof the
        probe is dead. Contaminated calibration solution produces the same
        symptom. Fresh solution first, then trust the reading.
        """
        response = await self.query("Slope,?")
        if response is None:
            return None
        return parse_slope(response)
