"""Tests for the hardware bus scanner."""

import sys
from unittest.mock import MagicMock, patch

from pi.discovery.scanner import (
    I2CDevice,
    SerialDevice,
    scan_all,
    scan_i2c,
    scan_onewire,
    scan_serial,
)


def _mock_smbus2(read_byte_side_effect=None):
    """Create a mock smbus2 module with configurable SMBus behavior."""
    mock_module = MagicMock()
    mock_bus = MagicMock()
    if read_byte_side_effect:
        mock_bus.read_byte = read_byte_side_effect
    mock_module.SMBus.return_value = mock_bus
    return mock_module, mock_bus


class TestI2CScan:
    def test_scan_finds_devices(self):
        def read_byte(addr):
            if addr in (0x76, 0x36):
                return 0x00
            raise OSError("No device")

        mock_module, mock_bus = _mock_smbus2()
        mock_bus.read_byte = read_byte

        with patch.dict(sys.modules, {"smbus2": mock_module}):
            devices = scan_i2c(bus_number=1)

        assert len(devices) == 2
        assert I2CDevice(bus=1, address=0x76) in devices
        assert I2CDevice(bus=1, address=0x36) in devices
        mock_bus.close.assert_called_once()

    def test_scan_returns_empty_when_no_bus(self):
        mock_module = MagicMock()
        mock_module.SMBus.side_effect = FileNotFoundError("No I2C bus")

        with patch.dict(sys.modules, {"smbus2": mock_module}):
            devices = scan_i2c(bus_number=1)

        assert devices == ()

    def test_scan_returns_empty_when_smbus_not_installed(self):
        # Remove smbus2 from modules to simulate ImportError
        with patch.dict(sys.modules, {"smbus2": None}):
            devices = scan_i2c(bus_number=1)

        assert devices == ()

    def test_scan_empty_bus(self):
        mock_module, mock_bus = _mock_smbus2()
        mock_bus.read_byte.side_effect = OSError("No device")

        with patch.dict(sys.modules, {"smbus2": mock_module}):
            devices = scan_i2c(bus_number=1)

        assert devices == ()


class TestOneWireScan:
    def test_returns_empty_when_path_missing(self):
        with patch("pi.discovery.scanner.Path") as MockPath:
            mock_w1 = MagicMock()
            mock_w1.exists.return_value = False
            MockPath.return_value = mock_w1
            devices = scan_onewire()

        assert devices == ()

    def test_finds_ds18b20(self, tmp_path):
        w1_dir = tmp_path / "w1_devices"
        w1_dir.mkdir()
        dev_dir = w1_dir / "28-0000abcd1234"
        dev_dir.mkdir()
        (dev_dir / "w1_slave").write_text("YES\nt=22500")

        with patch("pi.discovery.scanner.Path", return_value=w1_dir):
            devices = scan_onewire()

        assert len(devices) == 1
        assert devices[0].device_id == "28-0000abcd1234"


class TestSerialScan:
    def test_finds_serial_device(self, tmp_path):
        fake_port = tmp_path / "ttyUSB0"
        fake_port.touch()

        devices = scan_serial(preferred_port=str(fake_port))
        assert len(devices) == 1
        assert devices[0].port == str(fake_port)

    def test_returns_empty_when_no_ports(self):
        devices = scan_serial(preferred_port="/dev/nonexistent_port_xyz")
        assert devices == ()


class TestScanAll:
    def test_combines_results(self):
        with (
            patch("pi.discovery.scanner.scan_i2c") as mock_i2c,
            patch("pi.discovery.scanner.scan_onewire") as mock_ow,
            patch("pi.discovery.scanner.scan_serial") as mock_serial,
        ):
            mock_i2c.return_value = (I2CDevice(1, 0x76),)
            mock_ow.return_value = ()
            mock_serial.return_value = (SerialDevice("/dev/ttyUSB0"),)

            result = scan_all(i2c_bus=1, serial_port="/dev/ttyUSB0")

        assert len(result.i2c_devices) == 1
        assert len(result.onewire_devices) == 0
        assert len(result.serial_devices) == 1
