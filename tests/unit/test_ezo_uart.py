"""Tests for the EZO UART mode-switch helper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pi.drivers.ezo_uart import switch_to_i2c, EZO_ADDRESSES


class TestEzoAddresses:
    def test_ph_address(self):
        assert EZO_ADDRESSES["ph"] == 99

    def test_ec_address(self):
        assert EZO_ADDRESSES["ec"] == 100


def _make_mock_serial(readline_value=b"*OK\r"):
    """Create a mock serial port that works as a context manager."""
    mock_conn = MagicMock()
    mock_conn.readline.return_value = readline_value
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn


class TestSwitchToI2C:
    def test_sends_correct_command(self):
        mock_serial = _make_mock_serial()

        with patch("pi.drivers.ezo_uart.serial.Serial", return_value=mock_serial):
            result = switch_to_i2c("/dev/ttyUSB0", 9600, 99)

        mock_serial.write.assert_called_once_with(b"I2C,99\r")
        assert result == "*OK"

    def test_sends_ec_address(self):
        mock_serial = _make_mock_serial()

        with patch("pi.drivers.ezo_uart.serial.Serial", return_value=mock_serial):
            switch_to_i2c("/dev/ttyUSB0", 9600, 100)

        mock_serial.write.assert_called_once_with(b"I2C,100\r")

    def test_handles_restart_response(self):
        mock_serial = _make_mock_serial(b"*RS\r")

        with patch("pi.drivers.ezo_uart.serial.Serial", return_value=mock_serial):
            result = switch_to_i2c("/dev/ttyUSB0", 9600, 99)

        assert result == "*RS"

    def test_closes_port_via_context_manager(self):
        mock_serial = _make_mock_serial()

        with patch("pi.drivers.ezo_uart.serial.Serial", return_value=mock_serial):
            switch_to_i2c("/dev/ttyUSB0", 9600, 99)

        mock_serial.__exit__.assert_called_once()

    def test_closes_port_on_error(self):
        mock_serial = _make_mock_serial()
        mock_serial.write.side_effect = Exception("write failed")

        with patch("pi.drivers.ezo_uart.serial.Serial", return_value=mock_serial):
            with pytest.raises(Exception, match="write failed"):
                switch_to_i2c("/dev/ttyUSB0", 9600, 99)

        mock_serial.__exit__.assert_called_once()

    def test_serial_open_params(self):
        mock_serial = _make_mock_serial()

        with patch("pi.drivers.ezo_uart.serial.Serial", return_value=mock_serial) as MockSerial:
            switch_to_i2c("/dev/ttyUSB0", 9600, 99)

        MockSerial.assert_called_once_with("/dev/ttyUSB0", 9600, timeout=2)

    def test_empty_response(self):
        mock_serial = _make_mock_serial(b"")

        with patch("pi.drivers.ezo_uart.serial.Serial", return_value=mock_serial):
            result = switch_to_i2c("/dev/ttyUSB0", 9600, 99)

        assert result == ""
