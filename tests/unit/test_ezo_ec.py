"""Tests for the EZO-EC driver with mocked I²C bus."""

from unittest.mock import MagicMock

import pytest

from pi.drivers.ezo_ec import EZOECDriver


def _make_mock_bus(response_bytes: bytes | None = None):
    """Create a mock I²C bus that returns a canned response."""
    mock_bus = MagicMock()

    if response_bytes is not None:
        padded = list(response_bytes) + [0x00] * (31 - len(response_bytes))
        mock_bus.read_i2c_block_data.return_value = padded
    else:
        mock_bus.read_i2c_block_data.side_effect = OSError("No device")

    mock_bus.read_byte.return_value = 0x01
    return mock_bus


class TestEZOECRead:
    async def test_read_returns_ec_reading(self):
        """Standard EC reading in µS/cm."""
        response = bytes([0x01]) + b"1413.00"
        mock_bus = _make_mock_bus(response)

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        readings = await driver.read()

        assert len(readings) == 1
        assert readings[0].sensor_id == "ezo_ec"
        assert readings[0].value == pytest.approx(1413.0)
        assert readings[0].unit == "µS/cm"

    async def test_read_low_ec_seedling_range(self):
        """Low EC typical for seedlings (~500 µS/cm)."""
        response = bytes([0x01]) + b"523.50"
        mock_bus = _make_mock_bus(response)

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        readings = await driver.read()

        assert len(readings) == 1
        assert readings[0].value == pytest.approx(523.5)

    async def test_read_returns_empty_on_bus_error(self):
        mock_bus = _make_mock_bus(None)

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_returns_empty_on_not_ready(self):
        response = bytes([0xFE]) + b"0.00"
        mock_bus = _make_mock_bus(response)

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_returns_empty_on_syntax_error(self):
        response = bytes([0x02])
        mock_bus = _make_mock_bus(response)

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_rejects_negative(self):
        """EC cannot be negative."""
        response = bytes([0x01]) + b"-100.00"
        mock_bus = _make_mock_bus(response)

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_rejects_absurdly_high(self):
        """EC above 200,000 µS/cm is unrealistic."""
        response = bytes([0x01]) + b"250000.00"
        mock_bus = _make_mock_bus(response)

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_accepts_zero(self):
        """EC of 0 is valid (pure water)."""
        response = bytes([0x01]) + b"0.00"
        mock_bus = _make_mock_bus(response)

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        readings = await driver.read()
        assert len(readings) == 1
        assert readings[0].value == pytest.approx(0.0)


class TestEZOECAvailability:
    async def test_is_available_true(self):
        mock_bus = MagicMock()
        mock_bus.read_byte.return_value = 0x01

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        assert await driver.is_available() is True

    async def test_is_available_false(self):
        mock_bus = MagicMock()
        mock_bus.read_byte.side_effect = OSError("No device")

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus

        assert await driver.is_available() is False


class TestEZOECLifecycle:
    async def test_close_releases_bus(self):
        mock_bus = MagicMock()

        driver = EZOECDriver(bus_number=1, address=0x64)
        driver._bus = mock_bus
        await driver.close()

        mock_bus.close.assert_called_once()
        assert driver._bus is None

    async def test_sensor_id(self):
        driver = EZOECDriver()
        assert driver.sensor_id == "ezo_ec"

    async def test_close_when_no_bus(self):
        driver = EZOECDriver()
        await driver.close()
