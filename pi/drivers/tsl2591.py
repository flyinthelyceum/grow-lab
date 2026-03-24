"""TSL2591 high-dynamic-range light sensor driver.

Measures visible + IR light via I2C. Returns lux (computed from
both channels) and raw IR count. Used to verify grow light output
at canopy level.

TSL2591 register map (datasheet AMS-TAOS):
  0x00: ENABLE (power on/off, AEN)
  0x01: CONFIG (gain, integration time)
  0x14-0x17: CH0/CH1 ADC data (visible+IR / IR only)
  0x12: ID register (expected 0x50)
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from pi.data.models import SensorReading

logger = logging.getLogger(__name__)

# Command register bit
COMMAND_BIT = 0xA0

# Register addresses (ORed with COMMAND_BIT for I2C transactions)
REG_ENABLE = 0x00
REG_CONFIG = 0x01
REG_ID = 0x12
REG_CHAN0_LOW = 0x14

# Enable register values
ENABLE_POWERON = 0x01
ENABLE_AEN = 0x02  # ALS enable
ENABLE_POWEROFF = 0x00

# Gain values
GAIN_LOW = 0x00   # 1x
GAIN_MED = 0x10   # 25x
GAIN_HIGH = 0x20  # 428x
GAIN_MAX = 0x30   # 9876x

# Integration time values
INTEG_100MS = 0x00
INTEG_200MS = 0x01
INTEG_300MS = 0x02
INTEG_400MS = 0x03
INTEG_500MS = 0x04
INTEG_600MS = 0x05

# Gain multipliers for lux calculation
_GAIN_FACTOR = {
    GAIN_LOW: 1.0,
    GAIN_MED: 25.0,
    GAIN_HIGH: 428.0,
    GAIN_MAX: 9876.0,
}

# Integration time in ms for lux calculation
_INTEG_MS = {
    INTEG_100MS: 100.0,
    INTEG_200MS: 200.0,
    INTEG_300MS: 300.0,
    INTEG_400MS: 400.0,
    INTEG_500MS: 500.0,
    INTEG_600MS: 600.0,
}

# TSL2591 lux coefficients (from datasheet application note)
LUX_COEFF_A = 1.0
LUX_COEFF_B = 1.64
LUX_COEFF_C = 0.59
LUX_COEFF_D = 0.86
LUX_DF = 408.0  # Device factor


def _calculate_lux(ch0: int, ch1: int, gain: int, integration: int) -> float:
    """Calculate lux from raw channel values.

    ch0: visible + IR channel
    ch1: IR only channel
    Returns 0.0 on saturation or invalid readings.
    """
    if ch0 == 0 and ch1 == 0:
        return 0.0

    # Saturation check
    if ch0 == 65535 or ch1 == 65535:
        return 0.0

    gain_factor = _GAIN_FACTOR.get(gain, 25.0)
    integ_ms = _INTEG_MS.get(integration, 100.0)

    # Counts per lux (CPL)
    cpl = (integ_ms * gain_factor) / LUX_DF

    # Two lux formulas from datasheet, take the max
    lux1 = (ch0 - LUX_COEFF_B * ch1) / cpl
    lux2 = (LUX_COEFF_C * ch0 - LUX_COEFF_D * ch1) / cpl

    lux = max(lux1, lux2, 0.0)
    return round(lux, 2)


class TSL2591Driver:
    """I2C driver for the TSL2591 high-dynamic-range light sensor."""

    def __init__(
        self,
        bus_number: int = 1,
        address: int = 0x29,
        gain: int = GAIN_MED,
        integration: int = INTEG_100MS,
    ) -> None:
        self._bus_number = bus_number
        self._address = address
        self._gain = gain
        self._integration = integration
        self._bus = None

    @property
    def sensor_id(self) -> str:
        return "tsl2591"

    def _get_bus(self):
        if self._bus is None:
            import smbus2
            self._bus = smbus2.SMBus(self._bus_number)
        return self._bus

    def _write_register(self, reg: int, value: int) -> None:
        bus = self._get_bus()
        bus.write_byte_data(self._address, COMMAND_BIT | reg, value)

    def _read_register_block(self, reg: int, length: int) -> list[int]:
        bus = self._get_bus()
        return bus.read_i2c_block_data(self._address, COMMAND_BIT | reg, length)

    def _enable(self) -> None:
        self._write_register(REG_ENABLE, ENABLE_POWERON | ENABLE_AEN)

    def _disable(self) -> None:
        self._write_register(REG_ENABLE, ENABLE_POWEROFF)

    def _configure(self) -> None:
        self._write_register(REG_CONFIG, self._gain | self._integration)

    def _read_channels(self) -> tuple[int, int]:
        """Read CH0 (visible+IR) and CH1 (IR) raw ADC values."""
        data = self._read_register_block(REG_CHAN0_LOW, 4)
        ch0 = data[0] | (data[1] << 8)
        ch1 = data[2] | (data[3] << 8)
        return ch0, ch1

    async def read(self) -> list[SensorReading]:
        """Read lux and IR values.

        Powers on the sensor, waits for integration, reads, then powers off.
        Returns two SensorReading objects or empty list on failure.
        """
        try:
            def _do_read():
                self._enable()
                self._configure()
                # Wait for integration to complete (add 20ms margin)
                integ_ms = _INTEG_MS.get(self._integration, 100.0)
                time.sleep((integ_ms + 20) / 1000.0)
                ch0, ch1 = self._read_channels()
                self._disable()
                return ch0, ch1

            ch0, ch1 = await asyncio.to_thread(_do_read)
            lux = _calculate_lux(ch0, ch1, self._gain, self._integration)

            now = datetime.now(timezone.utc)

            return [
                SensorReading(
                    timestamp=now,
                    sensor_id="tsl2591_lux",
                    value=lux,
                    unit="lux",
                ),
                SensorReading(
                    timestamp=now,
                    sensor_id="tsl2591_ir",
                    value=float(ch1),
                    unit="raw",
                ),
            ]

        except Exception as exc:
            logger.error("TSL2591 read failed: %s", exc)
            return []

    async def is_available(self) -> bool:
        """Check if the TSL2591 is responding on the I2C bus."""
        try:
            def _check():
                bus = self._get_bus()
                bus.read_byte(self._address)

            await asyncio.to_thread(_check)
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Release the I2C bus."""
        if self._bus is not None:
            self._bus.close()
            self._bus = None
