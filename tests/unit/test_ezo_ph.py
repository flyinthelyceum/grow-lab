"""Tests for the EZO-pH driver with mocked I²C bus."""

from unittest.mock import MagicMock

import pytest

from pi.drivers.ezo_ph import EZOPhDriver


def _make_mock_bus(response_bytes: bytes | None = None):
    """Create a mock I²C bus that returns a canned response.

    Atlas EZO response format:
      byte 0: status code (1=success, 2=syntax error, 254=pending, 255=no data)
      bytes 1+: ASCII payload (e.g., b"6.42")
    """
    mock_bus = MagicMock()

    if response_bytes is not None:
        padded = list(response_bytes) + [0x00] * (31 - len(response_bytes))
        mock_bus.read_i2c_block_data.return_value = padded
    else:
        mock_bus.read_i2c_block_data.side_effect = OSError("No device")

    mock_bus.read_byte.return_value = 0x01
    return mock_bus


class TestEZOPhRead:
    async def test_read_returns_ph_reading(self):
        response = bytes([0x01]) + b"6.42"
        mock_bus = _make_mock_bus(response)

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus

        readings = await driver.read()

        assert len(readings) == 1
        assert readings[0].sensor_id == "ezo_ph"
        assert readings[0].value == pytest.approx(6.42)
        assert readings[0].unit == "pH"

    async def test_read_returns_empty_on_bus_error(self):
        mock_bus = _make_mock_bus(None)

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_returns_empty_on_not_ready(self):
        """Status code 254 means sensor is still processing."""
        response = bytes([0xFE]) + b"0.00"
        mock_bus = _make_mock_bus(response)

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_returns_empty_on_syntax_error(self):
        """Status code 2 means the command had a syntax error."""
        response = bytes([0x02])
        mock_bus = _make_mock_bus(response)

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_returns_empty_on_no_data(self):
        """Status code 255 means no data to send."""
        response = bytes([0xFF])
        mock_bus = _make_mock_bus(response)

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_rejects_out_of_range_high(self):
        """pH values above 14 are invalid."""
        response = bytes([0x01]) + b"15.20"
        mock_bus = _make_mock_bus(response)

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_rejects_negative(self):
        """pH values below 0 are invalid."""
        response = bytes([0x01]) + b"-1.50"
        mock_bus = _make_mock_bus(response)

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_accepts_boundary_values(self):
        """pH 0.0 and 14.0 are valid edge values."""
        for value in ["0.00", "14.00"]:
            response = bytes([0x01]) + value.encode()
            mock_bus = _make_mock_bus(response)

            driver = EZOPhDriver(bus_number=1, address=0x63)
            driver._bus = mock_bus

            readings = await driver.read()
            assert len(readings) == 1
            assert readings[0].value == pytest.approx(float(value))


class TestEZOPhAvailability:
    async def test_is_available_true(self):
        mock_bus = MagicMock()
        mock_bus.read_byte.return_value = 0x01

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus

        assert await driver.is_available() is True

    async def test_is_available_false(self):
        mock_bus = MagicMock()
        mock_bus.read_byte.side_effect = OSError("No device")

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus

        assert await driver.is_available() is False


class TestEZOPhLifecycle:
    async def test_close_releases_bus(self):
        mock_bus = MagicMock()

        driver = EZOPhDriver(bus_number=1, address=0x63)
        driver._bus = mock_bus
        await driver.close()

        mock_bus.close.assert_called_once()
        assert driver._bus is None

    async def test_sensor_id(self):
        driver = EZOPhDriver()
        assert driver.sensor_id == "ezo_ph"

    async def test_close_when_no_bus(self):
        driver = EZOPhDriver()
        await driver.close()  # should not raise
