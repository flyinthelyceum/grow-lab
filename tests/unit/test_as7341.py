"""Tests for the AS7341 spectral light sensor driver with mocked I2C bus."""

from unittest.mock import MagicMock

from pi.drivers.as7341 import (
    AS7341Driver,
    DEVICE_ID,
    ENABLE_PON,
    ENABLE_SMUX_EN,
    ENABLE_SP_EN,
    REG_ASTATUS,
    REG_CFG0,
    REG_CFG1,
    REG_ENABLE,
    REG_ID,
    REG_STATUS2,
    STATUS2_AVALID,
    SPECTRAL_CHANNELS,
    _calculate_lux_like,
)


def _pack_channels(values: tuple[int, int, int, int, int, int]) -> list[int]:
    payload = [0]
    for value in values:
        payload.extend([value & 0xFF, (value >> 8) & 0xFF])
    return payload


def _make_mock_bus():
    """Create a mock bus that can step through low/high SMUX reads."""
    registers = {
        REG_ID: DEVICE_ID << 2,
        REG_ENABLE: 0,
        REG_CFG0: 0,
        REG_CFG1: 0,
        REG_STATUS2: STATUS2_AVALID,
    }
    smux_mode = {"value": "low"}
    low_channels = (110, 210, 310, 410, 510, 610)
    high_channels = (710, 810, 910, 1010, 1110, 1210)

    mock_bus = MagicMock()

    def read_byte_data(addr, reg):
        if reg == REG_ID:
            return registers[REG_ID]
        if reg == REG_ENABLE and registers[REG_ENABLE] & ENABLE_SMUX_EN:
            registers[REG_ENABLE] &= ~ENABLE_SMUX_EN
        return registers.get(reg, 0)

    def write_byte_data(addr, reg, value):
        registers[reg] = value
        if reg == 0x13:
            smux_mode["value"] = "high" if value == 0x06 and registers.get(0x00) == 0x00 else smux_mode["value"]

    def read_i2c_block_data(addr, reg, length):
        if reg == REG_ASTATUS and length == 13:
            if smux_mode["value"] == "low":
                smux_mode["value"] = "high"
                return _pack_channels(low_channels)
            return _pack_channels(high_channels)
        return [0] * length

    mock_bus.read_byte_data.side_effect = read_byte_data
    mock_bus.write_byte_data.side_effect = write_byte_data
    mock_bus.read_i2c_block_data.side_effect = read_i2c_block_data
    return mock_bus


class TestCalculateLuxLike:
    def test_returns_positive_float(self):
        channels = {
            "as7341_415nm": 100,
            "as7341_445nm": 200,
            "as7341_480nm": 300,
            "as7341_515nm": 400,
            "as7341_555nm": 500,
            "as7341_590nm": 400,
            "as7341_630nm": 300,
            "as7341_680nm": 200,
            "as7341_clear": 600,
            "as7341_nir": 50,
        }
        lux = _calculate_lux_like(channels, gain=7, atime=29, astep=599)
        assert isinstance(lux, float)
        assert lux > 0.0

    def test_invalid_exposure_returns_zero(self):
        channels = {sensor_id: 0 for sensor_id in SPECTRAL_CHANNELS}
        lux = _calculate_lux_like(channels, gain=7, atime=-1, astep=0)
        assert lux == 0.0


class TestAS7341Driver:
    async def test_read_returns_primary_and_spectral_readings(self):
        driver = AS7341Driver(bus_number=1, address=0x39)
        driver._bus = _make_mock_bus()

        readings = await driver.read()

        ids = {reading.sensor_id for reading in readings}
        assert "as7341_lux" in ids
        assert set(SPECTRAL_CHANNELS).issubset(ids)
        assert len(readings) == 1 + len(SPECTRAL_CHANNELS)

    async def test_read_returns_empty_on_error(self):
        mock_bus = MagicMock()
        mock_bus.read_byte_data.side_effect = OSError("Bus error")

        driver = AS7341Driver(bus_number=1, address=0x39)
        driver._bus = mock_bus

        assert await driver.read() == []

    async def test_is_available_true(self):
        mock_bus = MagicMock()
        mock_bus.read_byte_data.return_value = DEVICE_ID << 2

        driver = AS7341Driver(bus_number=1, address=0x39)
        driver._bus = mock_bus

        assert await driver.is_available() is True

    async def test_is_available_false(self):
        mock_bus = MagicMock()
        mock_bus.read_byte_data.side_effect = OSError("No device")

        driver = AS7341Driver(bus_number=1, address=0x39)
        driver._bus = mock_bus

        assert await driver.is_available() is False

    async def test_close(self):
        mock_bus = MagicMock()
        driver = AS7341Driver(bus_number=1, address=0x39)
        driver._bus = mock_bus

        await driver.close()

        mock_bus.close.assert_called_once()
        assert driver._bus is None

    async def test_sensor_id(self):
        driver = AS7341Driver()
        assert driver.sensor_id == "as7341"

    async def test_read_powers_sensor_and_enables_spectral_mode(self):
        mock_bus = _make_mock_bus()
        driver = AS7341Driver(bus_number=1, address=0x39)
        driver._bus = mock_bus

        await driver.read()

        writes = mock_bus.write_byte_data.call_args_list
        enable_writes = [call for call in writes if call.args[1] == REG_ENABLE]
        assert any(call.args[2] & ENABLE_PON for call in enable_writes)
        assert any(call.args[2] & ENABLE_SP_EN for call in enable_writes)

