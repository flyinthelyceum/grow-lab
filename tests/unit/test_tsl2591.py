"""Tests for the TSL2591 light sensor driver with mocked I2C bus."""

from unittest.mock import MagicMock

import pytest

from pi.drivers.tsl2591 import (
    TSL2591Driver,
    _calculate_lux,
    REG_ENABLE,
    REG_CONFIG,
    REG_CHAN0_LOW,
    ENABLE_POWERON,
    ENABLE_AEN,
    ENABLE_POWEROFF,
    GAIN_MED,
    INTEG_100MS,
)


COMMAND_BIT = 0xA0  # Driver ORs this into register addresses


def _make_mock_bus(ch0: int = 300, ch1: int = 40):
    """Create a mock I2C bus returning specified channel values."""
    mock_bus = MagicMock()

    def read_block(addr, reg, length):
        # Driver sends COMMAND_BIT | REG_CHAN0_LOW
        if reg == (COMMAND_BIT | REG_CHAN0_LOW) and length == 4:
            return [ch0 & 0xFF, (ch0 >> 8) & 0xFF, ch1 & 0xFF, (ch1 >> 8) & 0xFF]
        return [0] * length

    mock_bus.read_i2c_block_data = read_block
    mock_bus.write_byte_data = MagicMock()
    mock_bus.read_byte = MagicMock(return_value=0x50)
    return mock_bus


class TestCalculateLux:
    def test_typical_indoor_light(self):
        # ch0=300, ch1=40 at medium gain, 100ms → should produce a positive lux value
        lux = _calculate_lux(ch0=300, ch1=40, gain=GAIN_MED, integration=INTEG_100MS)
        assert lux > 0.0
        assert lux < 100000.0

    def test_zero_channels_returns_zero(self):
        lux = _calculate_lux(ch0=0, ch1=0, gain=GAIN_MED, integration=INTEG_100MS)
        assert lux == 0.0

    def test_saturated_returns_zero(self):
        # Both channels at max (65535) indicates saturation
        lux = _calculate_lux(ch0=65535, ch1=65535, gain=GAIN_MED, integration=INTEG_100MS)
        assert lux == 0.0

    def test_ir_dominant_returns_zero(self):
        # ch1 (IR) much higher than ch0 (visible+IR) → negative CPL ratio → clamp to 0
        lux = _calculate_lux(ch0=10, ch1=500, gain=GAIN_MED, integration=INTEG_100MS)
        assert lux == 0.0

    def test_lux_is_float(self):
        lux = _calculate_lux(ch0=1000, ch1=100, gain=GAIN_MED, integration=INTEG_100MS)
        assert isinstance(lux, float)


class TestTSL2591Driver:
    async def test_read_returns_two_readings(self):
        mock_bus = _make_mock_bus(ch0=300, ch1=40)
        driver = TSL2591Driver(bus_number=1, address=0x29)
        driver._bus = mock_bus

        readings = await driver.read()

        assert len(readings) == 2
        ids = {r.sensor_id for r in readings}
        assert ids == {"tsl2591_lux", "tsl2591_ir"}

        lux = next(r for r in readings if r.sensor_id == "tsl2591_lux")
        assert lux.value >= 0.0
        assert lux.unit == "lux"

        ir = next(r for r in readings if r.sensor_id == "tsl2591_ir")
        assert ir.value == 40
        assert ir.unit == "raw"

    async def test_read_returns_empty_on_error(self):
        mock_bus = MagicMock()
        mock_bus.write_byte_data = MagicMock(side_effect=OSError("Bus error"))

        driver = TSL2591Driver(bus_number=1, address=0x29)
        driver._bus = mock_bus
        readings = await driver.read()

        assert readings == []

    async def test_is_available_true(self):
        mock_bus = MagicMock()
        mock_bus.read_byte.return_value = 0x50

        driver = TSL2591Driver(bus_number=1, address=0x29)
        driver._bus = mock_bus
        assert await driver.is_available() is True

    async def test_is_available_false(self):
        mock_bus = MagicMock()
        mock_bus.read_byte.side_effect = OSError("No device")

        driver = TSL2591Driver(bus_number=1, address=0x29)
        driver._bus = mock_bus
        assert await driver.is_available() is False

    async def test_close(self):
        mock_bus = MagicMock()
        driver = TSL2591Driver(bus_number=1, address=0x29)
        driver._bus = mock_bus

        await driver.close()

        mock_bus.close.assert_called_once()
        assert driver._bus is None

    async def test_sensor_id(self):
        driver = TSL2591Driver()
        assert driver.sensor_id == "tsl2591"

    async def test_read_enables_and_disables_sensor(self):
        mock_bus = _make_mock_bus(ch0=300, ch1=40)
        driver = TSL2591Driver(bus_number=1, address=0x29)
        driver._bus = mock_bus

        await driver.read()

        # Should have written enable (power on + AEN), then disable (power off)
        # Driver ORs COMMAND_BIT into register address
        calls = mock_bus.write_byte_data.call_args_list
        enable_reg = COMMAND_BIT | REG_ENABLE
        enable_calls = [c for c in calls if c[0][1] == enable_reg]
        assert any(c[0][2] == (ENABLE_POWERON | ENABLE_AEN) for c in enable_calls)
        assert any(c[0][2] == ENABLE_POWEROFF for c in enable_calls)
