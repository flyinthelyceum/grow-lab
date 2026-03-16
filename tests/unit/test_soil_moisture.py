"""Tests for the ADS1115 + DFRobot SEN0308 soil moisture driver."""

from unittest.mock import MagicMock

import pytest

from pi.drivers.soil_moisture import SoilMoistureDriver, _voltage_to_raw_moisture


def _make_mock_bus(raw_adc: int | None = None):
    """Create a mock I²C bus that returns a canned ADS1115 conversion.

    ADS1115 conversion register (0x00) is 16-bit big-endian signed.
    Config register (0x01) is used to start a single-shot conversion.
    """
    mock_bus = MagicMock()

    if raw_adc is not None:
        # Conversion result: 2 bytes big-endian signed
        high = (raw_adc >> 8) & 0xFF
        low = raw_adc & 0xFF
        mock_bus.read_i2c_block_data.return_value = [high, low]

        # Config register: bit 15 = 1 means conversion complete
        mock_bus.read_word_data.return_value = 0x8583  # OS bit set
    else:
        mock_bus.read_i2c_block_data.side_effect = OSError("No device")

    mock_bus.read_byte.return_value = 0x00
    return mock_bus


class TestVoltageToMoisture:
    def test_dry_air_returns_zero(self):
        """~3.0V output = bone dry (SEN0308 spec)."""
        result = _voltage_to_raw_moisture(3.0)
        assert result == pytest.approx(0.0, abs=5.0)

    def test_submerged_returns_high(self):
        """~1.1V output = submerged in water (SEN0308 spec)."""
        result = _voltage_to_raw_moisture(1.1)
        assert result > 90.0

    def test_mid_range(self):
        """~2.0V = roughly half moisture."""
        result = _voltage_to_raw_moisture(2.0)
        assert 40.0 < result < 70.0

    def test_clamps_below_minimum(self):
        """Voltage below sensor floor clamps to 100%."""
        result = _voltage_to_raw_moisture(0.5)
        assert result == pytest.approx(100.0)

    def test_clamps_above_maximum(self):
        """Voltage above sensor ceiling clamps to 0%."""
        result = _voltage_to_raw_moisture(3.5)
        assert result == pytest.approx(0.0)


class TestSoilMoistureRead:
    async def test_read_returns_moisture_reading(self):
        # ADS1115 at gain=1 (±4.096V): 1 LSB = 0.125mV
        # 2.0V = 16000 raw counts
        mock_bus = _make_mock_bus(raw_adc=16000)

        driver = SoilMoistureDriver(bus_number=1, address=0x48, channel=0)
        driver._bus = mock_bus

        readings = await driver.read()

        assert len(readings) == 1
        assert readings[0].sensor_id == "soil_moisture"
        assert readings[0].unit == "%"
        assert 0.0 <= readings[0].value <= 100.0

    async def test_read_dry_sensor(self):
        # ~3.0V = 24000 raw counts -> should be near 0%
        mock_bus = _make_mock_bus(raw_adc=24000)

        driver = SoilMoistureDriver(bus_number=1, address=0x48, channel=0)
        driver._bus = mock_bus

        readings = await driver.read()

        assert len(readings) == 1
        assert readings[0].value < 10.0

    async def test_read_wet_sensor(self):
        # ~1.2V = 9600 raw counts -> should be high moisture
        mock_bus = _make_mock_bus(raw_adc=9600)

        driver = SoilMoistureDriver(bus_number=1, address=0x48, channel=0)
        driver._bus = mock_bus

        readings = await driver.read()

        assert len(readings) == 1
        assert readings[0].value > 80.0

    async def test_read_returns_empty_on_bus_error(self):
        mock_bus = _make_mock_bus(None)

        driver = SoilMoistureDriver(bus_number=1, address=0x48, channel=0)
        driver._bus = mock_bus

        readings = await driver.read()
        assert readings == []

    async def test_read_includes_voltage_in_metadata(self):
        mock_bus = _make_mock_bus(raw_adc=16000)

        driver = SoilMoistureDriver(bus_number=1, address=0x48, channel=0)
        driver._bus = mock_bus

        readings = await driver.read()

        assert readings[0].metadata is not None
        assert "voltage" in readings[0].metadata


class TestSoilMoistureAvailability:
    async def test_is_available_true(self):
        mock_bus = MagicMock()
        mock_bus.read_byte.return_value = 0x00

        driver = SoilMoistureDriver(bus_number=1, address=0x48, channel=0)
        driver._bus = mock_bus

        assert await driver.is_available() is True

    async def test_is_available_false(self):
        mock_bus = MagicMock()
        mock_bus.read_byte.side_effect = OSError("No device")

        driver = SoilMoistureDriver(bus_number=1, address=0x48, channel=0)
        driver._bus = mock_bus

        assert await driver.is_available() is False


class TestSoilMoistureLifecycle:
    async def test_close_releases_bus(self):
        mock_bus = MagicMock()

        driver = SoilMoistureDriver(bus_number=1, address=0x48, channel=0)
        driver._bus = mock_bus
        await driver.close()

        mock_bus.close.assert_called_once()
        assert driver._bus is None

    async def test_sensor_id(self):
        driver = SoilMoistureDriver(channel=0)
        assert driver.sensor_id == "soil_moisture"

    async def test_close_when_no_bus(self):
        driver = SoilMoistureDriver(channel=0)
        await driver.close()

    async def test_different_channels(self):
        """Driver should accept channels 0-3."""
        for ch in range(4):
            driver = SoilMoistureDriver(channel=ch)
            assert driver._channel == ch
