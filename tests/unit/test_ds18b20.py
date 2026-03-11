"""Tests for the DS18B20 1-Wire temperature sensor driver."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pi.data.models import SensorReading


# Typical w1_slave file contents from a real DS18B20:
# Line 1: CRC check — ends with "YES" if valid
# Line 2: temperature in millidegrees after "t="
VALID_W1_CONTENT = """\
73 01 4b 46 7f ff 0d 10 41 : crc=41 YES
73 01 4b 46 7f ff 0d 10 41 t=23187
"""

NEGATIVE_TEMP_CONTENT = """\
d0 fe 4b 46 7f ff 0d 10 13 : crc=13 YES
d0 fe 4b 46 7f ff 0d 10 13 t=-2000
"""

CRC_FAIL_CONTENT = """\
73 01 4b 46 7f ff 0d 10 41 : crc=41 NO
73 01 4b 46 7f ff 0d 10 41 t=23187
"""

MISSING_TEMP_CONTENT = """\
73 01 4b 46 7f ff 0d 10 41 : crc=41 YES
73 01 4b 46 7f ff 0d 10 41
"""

# 85000 millidegrees = 85°C, the DS18B20 power-on reset value
POWER_ON_RESET_CONTENT = """\
50 05 4b 46 7f ff 0c 10 1c : crc=1c YES
50 05 4b 46 7f ff 0c 10 1c t=85000
"""


class TestDS18B20Driver:
    def _make_driver(self, tmp_path: Path, content: str, device_id: str = "28-0123456789ab"):
        """Create a driver with a fake w1_slave file."""
        from pi.drivers.ds18b20 import DS18B20Driver

        w1_file = tmp_path / device_id / "w1_slave"
        w1_file.parent.mkdir(parents=True, exist_ok=True)
        w1_file.write_text(content)
        return DS18B20Driver(device_id=device_id, device_path=w1_file)

    def test_sensor_id(self, tmp_path: Path):
        driver = self._make_driver(tmp_path, VALID_W1_CONTENT)
        assert driver.sensor_id == "ds18b20_28-0123456789ab"

    async def test_read_valid_temperature(self, tmp_path: Path):
        driver = self._make_driver(tmp_path, VALID_W1_CONTENT)
        readings = await driver.read()

        assert len(readings) == 1
        reading = readings[0]
        assert isinstance(reading, SensorReading)
        assert reading.sensor_id == "ds18b20_28-0123456789ab"
        assert reading.value == pytest.approx(23.187)
        assert reading.unit == "°C"

    async def test_read_negative_temperature(self, tmp_path: Path):
        driver = self._make_driver(tmp_path, NEGATIVE_TEMP_CONTENT)
        readings = await driver.read()

        assert len(readings) == 1
        assert readings[0].value == pytest.approx(-2.0)

    async def test_read_crc_failure_returns_empty(self, tmp_path: Path):
        driver = self._make_driver(tmp_path, CRC_FAIL_CONTENT)
        readings = await driver.read()
        assert readings == []

    async def test_read_missing_temp_returns_empty(self, tmp_path: Path):
        driver = self._make_driver(tmp_path, MISSING_TEMP_CONTENT)
        readings = await driver.read()
        assert readings == []

    async def test_read_power_on_reset_returns_empty(self, tmp_path: Path):
        """85°C is the DS18B20 power-on reset value — treat as invalid."""
        driver = self._make_driver(tmp_path, POWER_ON_RESET_CONTENT)
        readings = await driver.read()
        assert readings == []

    async def test_read_file_missing_returns_empty(self, tmp_path: Path):
        from pi.drivers.ds18b20 import DS18B20Driver

        missing_path = tmp_path / "28-ghost" / "w1_slave"
        driver = DS18B20Driver(device_id="28-ghost", device_path=missing_path)
        readings = await driver.read()
        assert readings == []

    async def test_is_available_when_file_exists(self, tmp_path: Path):
        driver = self._make_driver(tmp_path, VALID_W1_CONTENT)
        assert await driver.is_available() is True

    async def test_is_available_when_file_missing(self, tmp_path: Path):
        from pi.drivers.ds18b20 import DS18B20Driver

        missing_path = tmp_path / "28-ghost" / "w1_slave"
        driver = DS18B20Driver(device_id="28-ghost", device_path=missing_path)
        assert await driver.is_available() is False

    async def test_close_is_noop(self, tmp_path: Path):
        """1-Wire drivers have no persistent connection to release."""
        driver = self._make_driver(tmp_path, VALID_W1_CONTENT)
        await driver.close()  # Should not raise

    async def test_implements_sensor_driver_protocol(self, tmp_path: Path):
        from pi.drivers.base import SensorDriver

        driver = self._make_driver(tmp_path, VALID_W1_CONTENT)
        assert isinstance(driver, SensorDriver)
