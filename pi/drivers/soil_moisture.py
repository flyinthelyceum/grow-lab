"""Soil moisture driver — DFRobot SEN0308 via ADS1115 ADC.

The SEN0308 is an analog capacitive soil moisture sensor (IP65).
It outputs a voltage inversely proportional to moisture:
  ~3.0V = dry air
  ~1.1V = fully submerged in water

The ADS1115 is a 16-bit I²C ADC that reads the sensor's analog
output. At gain=1 (±4.096V), 1 LSB = 0.125mV.

ADS1115 register map:
  0x00: conversion register (16-bit, big-endian, signed)
  0x01: config register (16-bit, big-endian)

Config register layout (see TI datasheet Table 6):
  [15]    OS:     1 = start single-shot conversion
  [14:12] MUX:    channel select (100=AIN0, 101=AIN1, 110=AIN2, 111=AIN3)
  [11:9]  PGA:    001 = ±4.096V (gain=1)
  [8]     MODE:   1 = single-shot
  [7:5]   DR:     100 = 128 SPS
  [4:0]   comp:   11111 = disable comparator
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from pi.data.models import SensorReading

logger = logging.getLogger(__name__)

# ADS1115 registers
REG_CONVERSION = 0x00
REG_CONFIG = 0x01

# ADS1115 config: single-shot, ±4.096V gain, 128 SPS, comparator off
# MUX bits are set per-channel in _build_config()
_CONFIG_BASE = (
    (1 << 15)       # OS: start conversion
    | (0b001 << 9)  # PGA: ±4.096V
    | (1 << 8)      # MODE: single-shot
    | (0b100 << 5)  # DR: 128 SPS
    | 0b11111       # Disable comparator
)

# ADS1115 at gain=1: 1 LSB = 0.125 mV = 0.000125 V
LSB_VOLTAGE = 4.096 / 32768.0

# SEN0308 voltage-to-moisture mapping
# Sensor outputs ~3.0V dry, ~1.1V submerged
VOLTAGE_DRY = 3.0
VOLTAGE_WET = 1.1


def _build_config(channel: int) -> int:
    """Build ADS1115 config word for single-ended read on given channel.

    Channel 0-3 maps to MUX values 0b100-0b111 (AINx vs GND).
    """
    mux = (0b100 + channel) << 12
    return _CONFIG_BASE | mux


def _voltage_to_raw_moisture(voltage: float) -> float:
    """Convert SEN0308 output voltage to moisture percentage.

    Linear mapping: VOLTAGE_DRY -> 0%, VOLTAGE_WET -> 100%.
    Clamped to [0, 100].
    """
    if voltage >= VOLTAGE_DRY:
        return 0.0
    if voltage <= VOLTAGE_WET:
        return 100.0

    # Inverted linear interpolation (lower voltage = more moisture)
    fraction = (VOLTAGE_DRY - voltage) / (VOLTAGE_DRY - VOLTAGE_WET)
    return round(fraction * 100.0, 1)


class SoilMoistureDriver:
    """I²C driver for DFRobot SEN0308 via ADS1115 ADC."""

    def __init__(
        self,
        bus_number: int = 1,
        address: int = 0x48,
        channel: int = 0,
    ) -> None:
        self._bus_number = bus_number
        self._address = address
        self._channel = channel
        self._bus = None

    @property
    def sensor_id(self) -> str:
        return "soil_moisture"

    def _get_bus(self):
        if self._bus is None:
            import smbus2

            self._bus = smbus2.SMBus(self._bus_number)
        return self._bus

    def _read_adc(self) -> int:
        """Start a single-shot conversion and read the result.

        Returns the raw 16-bit signed ADC value.
        """
        bus = self._get_bus()
        config = _build_config(self._channel)

        # Write config to start conversion (big-endian)
        config_high = (config >> 8) & 0xFF
        config_low = config & 0xFF
        bus.write_i2c_block_data(
            self._address, REG_CONFIG, [config_high, config_low]
        )

        # Wait for conversion (~8ms at 128 SPS)
        time.sleep(0.01)

        # Read conversion register
        raw = bus.read_i2c_block_data(self._address, REG_CONVERSION, 2)
        value = (raw[0] << 8) | raw[1]

        # Convert from unsigned to signed 16-bit
        if value > 32767:
            value -= 65536

        return value

    async def read(self) -> list[SensorReading]:
        """Read soil moisture from the SEN0308 via ADS1115.

        Returns a single SensorReading with moisture % or empty list on failure.
        """
        try:
            raw = await asyncio.to_thread(self._read_adc)
            voltage = raw * LSB_VOLTAGE
            moisture = _voltage_to_raw_moisture(voltage)

            return [
                SensorReading(
                    timestamp=datetime.now(timezone.utc),
                    sensor_id="soil_moisture",
                    value=moisture,
                    unit="%",
                    metadata=f"voltage={voltage:.3f}V,raw={raw}",
                )
            ]

        except Exception as exc:
            logger.error("Soil moisture read failed: %s", exc)
            return []

    async def is_available(self) -> bool:
        """Check if the ADS1115 is responding on the I²C bus."""
        try:

            def _check():
                bus = self._get_bus()
                bus.read_byte(self._address)

            await asyncio.to_thread(_check)
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Release the I²C bus."""
        if self._bus is not None:
            self._bus.close()
            self._bus = None
