"""BME280 driver — air temperature, humidity, and atmospheric pressure.

Communicates over I²C using smbus2. Returns three SensorReading
objects per poll (one for each measurement).

BME280 register map (datasheet section 5.3):
  0xF7-0xFC: raw ADC data (pressure, temperature, humidity)
  0x88-0xA1: calibration data block 1
  0xE1-0xE7: calibration data block 2
  0xF2: ctrl_hum (humidity oversampling)
  0xF4: ctrl_meas (temp/pressure oversampling + mode)
  0xF5: config (standby, filter, SPI)
"""

from __future__ import annotations

import asyncio
import logging
import struct
from dataclasses import dataclass
from datetime import datetime, timezone

from pi.data.models import SensorReading

logger = logging.getLogger(__name__)

# Registers
REG_CALIB_00 = 0x88
REG_CALIB_26 = 0xE1
REG_CTRL_HUM = 0xF2
REG_CTRL_MEAS = 0xF4
REG_DATA = 0xF7

# Oversampling x1 for all, normal mode
OVERSAMPLE_1X = 0x01
MODE_FORCED = 0x01


@dataclass(frozen=True)
class CalibrationData:
    """Compensation parameters from BME280 calibration registers."""

    dig_t1: int
    dig_t2: int
    dig_t3: int
    dig_p1: int
    dig_p2: int
    dig_p3: int
    dig_p4: int
    dig_p5: int
    dig_p6: int
    dig_p7: int
    dig_p8: int
    dig_p9: int
    dig_h1: int
    dig_h2: int
    dig_h3: int
    dig_h4: int
    dig_h5: int
    dig_h6: int


def _parse_calibration(block1: bytes, block2: bytes) -> CalibrationData:
    """Parse calibration data from two register blocks.

    block1: 26 bytes from 0x88-0xA1
    block2: 7 bytes from 0xE1-0xE7
    """
    # Temperature and pressure calibration (block1)
    t1 = struct.unpack_from("<H", block1, 0)[0]
    t2 = struct.unpack_from("<h", block1, 2)[0]
    t3 = struct.unpack_from("<h", block1, 4)[0]

    p1 = struct.unpack_from("<H", block1, 6)[0]
    p2 = struct.unpack_from("<h", block1, 8)[0]
    p3 = struct.unpack_from("<h", block1, 10)[0]
    p4 = struct.unpack_from("<h", block1, 12)[0]
    p5 = struct.unpack_from("<h", block1, 14)[0]
    p6 = struct.unpack_from("<h", block1, 16)[0]
    p7 = struct.unpack_from("<h", block1, 18)[0]
    p8 = struct.unpack_from("<h", block1, 20)[0]
    p9 = struct.unpack_from("<h", block1, 22)[0]

    # Humidity calibration (split across blocks)
    h1 = block1[25]  # 0xA1
    h2 = struct.unpack_from("<h", block2, 0)[0]
    h3 = block2[2]
    h4 = (block2[3] << 4) | (block2[4] & 0x0F)
    h5 = (block2[5] << 4) | ((block2[4] >> 4) & 0x0F)
    h6_bytes = block2[6:7]
    h6 = struct.unpack("b", h6_bytes)[0]

    return CalibrationData(
        dig_t1=t1, dig_t2=t2, dig_t3=t3,
        dig_p1=p1, dig_p2=p2, dig_p3=p3,
        dig_p4=p4, dig_p5=p5, dig_p6=p6,
        dig_p7=p7, dig_p8=p8, dig_p9=p9,
        dig_h1=h1, dig_h2=h2, dig_h3=h3,
        dig_h4=h4, dig_h5=h5, dig_h6=h6,
    )


def _compensate_temperature(adc_t: int, cal: CalibrationData) -> tuple[float, int]:
    """Compensate raw temperature ADC value.

    Returns (temperature_celsius, t_fine) where t_fine is used
    for pressure and humidity compensation.
    """
    var1 = ((adc_t / 16384.0) - (cal.dig_t1 / 1024.0)) * cal.dig_t2
    var2 = (
        ((adc_t / 131072.0) - (cal.dig_t1 / 8192.0))
        * ((adc_t / 131072.0) - (cal.dig_t1 / 8192.0))
    ) * cal.dig_t3
    t_fine = int(var1 + var2)
    temperature = (var1 + var2) / 5120.0
    return round(temperature, 2), t_fine


def _compensate_pressure(adc_p: int, t_fine: int, cal: CalibrationData) -> float:
    """Compensate raw pressure ADC value. Returns pressure in hPa."""
    var1 = t_fine / 2.0 - 64000.0
    var2 = var1 * var1 * cal.dig_p6 / 32768.0
    var2 = var2 + var1 * cal.dig_p5 * 2.0
    var2 = var2 / 4.0 + cal.dig_p4 * 65536.0
    var1 = (cal.dig_p3 * var1 * var1 / 524288.0 + cal.dig_p2 * var1) / 524288.0
    var1 = (1.0 + var1 / 32768.0) * cal.dig_p1
    if var1 == 0:
        return 0.0
    pressure = 1048576.0 - adc_p
    pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
    var1 = cal.dig_p9 * pressure * pressure / 2147483648.0
    var2 = pressure * cal.dig_p8 / 32768.0
    pressure = pressure + (var1 + var2 + cal.dig_p7) / 16.0
    return round(pressure / 100.0, 2)  # Convert Pa to hPa


def _compensate_humidity(adc_h: int, t_fine: int, cal: CalibrationData) -> float:
    """Compensate raw humidity ADC value. Returns relative humidity %."""
    h = t_fine - 76800.0
    if h == 0:
        return 0.0
    h = (adc_h - (cal.dig_h4 * 64.0 + cal.dig_h5 / 16384.0 * h)) * (
        cal.dig_h2
        / 65536.0
        * (
            1.0
            + cal.dig_h6
            / 67108864.0
            * h
            * (1.0 + cal.dig_h3 / 67108864.0 * h)
        )
    )
    h = h * (1.0 - cal.dig_h1 * h / 524288.0)
    return round(max(0.0, min(100.0, h)), 2)


class BME280Driver:
    """I²C driver for the BME280 environmental sensor."""

    def __init__(self, bus_number: int = 1, address: int = 0x76) -> None:
        self._bus_number = bus_number
        self._address = address
        self._bus = None
        self._calibration: CalibrationData | None = None

    @property
    def sensor_id(self) -> str:
        return "bme280"

    def _get_bus(self):
        if self._bus is None:
            import smbus2

            self._bus = smbus2.SMBus(self._bus_number)
        return self._bus

    def _load_calibration(self) -> CalibrationData:
        """Read calibration registers from the sensor."""
        bus = self._get_bus()
        block1 = bytes(bus.read_i2c_block_data(self._address, REG_CALIB_00, 26))
        block2 = bytes(bus.read_i2c_block_data(self._address, REG_CALIB_26, 7))
        return _parse_calibration(block1, block2)

    def _trigger_measurement(self) -> None:
        """Configure and trigger a forced measurement."""
        bus = self._get_bus()
        # Set humidity oversampling x1
        bus.write_byte_data(self._address, REG_CTRL_HUM, OVERSAMPLE_1X)
        # Set temp/pressure oversampling x1, forced mode
        ctrl_meas = (OVERSAMPLE_1X << 5) | (OVERSAMPLE_1X << 2) | MODE_FORCED
        bus.write_byte_data(self._address, REG_CTRL_MEAS, ctrl_meas)

    def _read_raw(self) -> tuple[int, int, int]:
        """Read raw ADC values for pressure, temperature, humidity."""
        bus = self._get_bus()
        data = bus.read_i2c_block_data(self._address, REG_DATA, 8)
        adc_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        adc_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        adc_h = (data[6] << 8) | data[7]
        return adc_p, adc_t, adc_h

    async def read(self) -> list[SensorReading]:
        """Read temperature, humidity, and pressure.

        Returns three SensorReading objects or empty list on failure.
        """
        try:

            def _do_read():
                if self._calibration is None:
                    self._calibration = self._load_calibration()
                self._trigger_measurement()
                import time

                time.sleep(0.05)  # Wait for measurement to complete
                return self._read_raw()

            adc_p, adc_t, adc_h = await asyncio.to_thread(_do_read)

            cal = self._calibration
            assert cal is not None

            temp, t_fine = _compensate_temperature(adc_t, cal)
            pressure = _compensate_pressure(adc_p, t_fine, cal)
            humidity = _compensate_humidity(adc_h, t_fine, cal)

            now = datetime.now(timezone.utc)

            return [
                SensorReading(
                    timestamp=now,
                    sensor_id="bme280_temperature",
                    value=temp,
                    unit="°C",
                ),
                SensorReading(
                    timestamp=now,
                    sensor_id="bme280_humidity",
                    value=humidity,
                    unit="%",
                ),
                SensorReading(
                    timestamp=now,
                    sensor_id="bme280_pressure",
                    value=pressure,
                    unit="hPa",
                ),
            ]

        except Exception as exc:
            logger.error("BME280 read failed: %s", exc)
            return []

    async def is_available(self) -> bool:
        """Check if the BME280 is responding on the I²C bus."""
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
