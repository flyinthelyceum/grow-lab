"""Tests for the BME280 driver with mocked I²C bus."""

import struct
import sys
from unittest.mock import MagicMock, patch

import pytest

from pi.drivers.bme280 import (
    CalibrationData,
    _compensate_humidity,
    _compensate_pressure,
    _compensate_temperature,
    _parse_calibration,
)

# Known calibration values from a real BME280 datasheet example
SAMPLE_CAL = CalibrationData(
    dig_t1=27504, dig_t2=26435, dig_t3=-1000,
    dig_p1=36477, dig_p2=-10685, dig_p3=3024,
    dig_p4=2855, dig_p5=140, dig_p6=-7,
    dig_p7=15500, dig_p8=-14600, dig_p9=6000,
    dig_h1=75, dig_h2=370, dig_h3=0,
    dig_h4=313, dig_h5=50, dig_h6=30,
)


def _make_cal_blocks():
    """Build fake calibration register blocks."""
    block1 = bytearray(26)
    struct.pack_into("<H", block1, 0, 27504)
    struct.pack_into("<h", block1, 2, 26435)
    struct.pack_into("<h", block1, 4, -1000)
    struct.pack_into("<H", block1, 6, 36477)
    struct.pack_into("<h", block1, 8, -10685)
    struct.pack_into("<h", block1, 10, 3024)
    struct.pack_into("<h", block1, 12, 2855)
    struct.pack_into("<h", block1, 14, 140)
    struct.pack_into("<h", block1, 16, -7)
    struct.pack_into("<h", block1, 18, 15500)
    struct.pack_into("<h", block1, 20, -14600)
    struct.pack_into("<h", block1, 22, 6000)
    block1[25] = 75

    block2 = bytearray(7)
    struct.pack_into("<h", block2, 0, 370)

    # ADC values producing ~25°C, ~1102 hPa, ~28% with SAMPLE_CAL
    adc_data = [
        0x57, 0xE4, 0x00,  # pressure ADC = 360000
        0x7E, 0xF4, 0x00,  # temp ADC = 520000
        0x61, 0xA8,         # humidity ADC = 25000
    ]
    return bytes(block1), bytes(block2), adc_data


def _make_mock_bus(block1, block2, adc_data):
    """Create a mock bus with given register data."""
    mock_bus = MagicMock()

    def read_block(addr, reg, length):
        if reg == 0x88:
            return list(block1[:length])
        elif reg == 0xE1:
            return list(block2[:length])
        elif reg == 0xF7:
            return adc_data[:length]
        return [0] * length

    mock_bus.read_i2c_block_data = read_block
    mock_bus.write_byte_data = MagicMock()
    mock_bus.read_byte = MagicMock(return_value=0x60)
    return mock_bus


class TestCompensation:
    def test_temperature_reasonable(self):
        temp, t_fine = _compensate_temperature(519888, SAMPLE_CAL)
        assert 15.0 < temp < 35.0
        assert isinstance(t_fine, int)

    def test_pressure_reasonable(self):
        _, t_fine = _compensate_temperature(519888, SAMPLE_CAL)
        pressure = _compensate_pressure(415148, t_fine, SAMPLE_CAL)
        assert 900.0 < pressure < 1100.0

    def test_humidity_clamped(self):
        _, t_fine = _compensate_temperature(519888, SAMPLE_CAL)
        humidity = _compensate_humidity(30000, t_fine, SAMPLE_CAL)
        assert 0.0 <= humidity <= 100.0

    def test_pressure_zero_division(self):
        zero_cal = CalibrationData(
            dig_t1=27504, dig_t2=26435, dig_t3=-1000,
            dig_p1=0, dig_p2=0, dig_p3=0,
            dig_p4=0, dig_p5=0, dig_p6=0,
            dig_p7=0, dig_p8=0, dig_p9=0,
            dig_h1=0, dig_h2=0, dig_h3=0,
            dig_h4=0, dig_h5=0, dig_h6=0,
        )
        _, t_fine = _compensate_temperature(519888, zero_cal)
        pressure = _compensate_pressure(415148, t_fine, zero_cal)
        assert pressure == 0.0


class TestParseCalibration:
    def test_round_trip(self):
        block1, block2, _ = _make_cal_blocks()
        cal = _parse_calibration(block1, block2)
        assert cal.dig_t1 == 27504
        assert cal.dig_t2 == 26435
        assert cal.dig_t3 == -1000
        assert cal.dig_p1 == 36477
        assert cal.dig_h1 == 75
        assert cal.dig_h2 == 370


class TestBME280Driver:
    async def test_read_returns_three_readings(self):
        from pi.drivers.bme280 import BME280Driver

        block1, block2, adc_data = _make_cal_blocks()
        mock_bus = _make_mock_bus(block1, block2, adc_data)

        driver = BME280Driver(bus_number=1, address=0x76)
        driver._bus = mock_bus
        # Pre-inject known calibration so compensation produces sensible values
        driver._calibration = SAMPLE_CAL
        readings = await driver.read()

        assert len(readings) == 3
        ids = {r.sensor_id for r in readings}
        assert ids == {"bme280_temperature", "bme280_humidity", "bme280_pressure"}

        temp = next(r for r in readings if r.sensor_id == "bme280_temperature")
        assert 15.0 < temp.value < 40.0
        assert temp.unit == "°C"

        pressure = next(r for r in readings if r.sensor_id == "bme280_pressure")
        assert 900.0 < pressure.value < 1200.0

        humidity = next(r for r in readings if r.sensor_id == "bme280_humidity")
        assert 0.0 <= humidity.value <= 100.0

    async def test_read_returns_empty_on_error(self):
        from pi.drivers.bme280 import BME280Driver

        mock_bus = MagicMock()
        mock_bus.read_i2c_block_data.side_effect = OSError("Bus error")

        driver = BME280Driver(bus_number=1, address=0x76)
        driver._bus = mock_bus
        readings = await driver.read()

        assert readings == []

    async def test_is_available_true(self):
        from pi.drivers.bme280 import BME280Driver

        mock_bus = MagicMock()
        mock_bus.read_byte.return_value = 0x60

        driver = BME280Driver(bus_number=1, address=0x76)
        driver._bus = mock_bus
        assert await driver.is_available() is True

    async def test_is_available_false(self):
        from pi.drivers.bme280 import BME280Driver

        mock_bus = MagicMock()
        mock_bus.read_byte.side_effect = OSError("No device")

        driver = BME280Driver(bus_number=1, address=0x76)
        driver._bus = mock_bus
        assert await driver.is_available() is False

    async def test_close(self):
        from pi.drivers.bme280 import BME280Driver

        mock_bus = MagicMock()

        driver = BME280Driver(bus_number=1, address=0x76)
        driver._bus = mock_bus
        await driver.close()

        mock_bus.close.assert_called_once()
        assert driver._bus is None

    async def test_sensor_id(self):
        from pi.drivers.bme280 import BME280Driver

        driver = BME280Driver()
        assert driver.sensor_id == "bme280"
