"""Tests for the ESP32 serial command interface."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import sys

from pi.drivers.esp32_serial import ESP32Response, ESP32Serial


class TestESP32Response:
    def test_frozen(self) -> None:
        resp = ESP32Response(raw='{"ok":true}', data={"ok": True}, ok=True)
        assert resp.ok is True
        assert resp.error is None

    def test_error_response(self) -> None:
        resp = ESP32Response(raw="", data={}, ok=False, error="not connected")
        assert resp.ok is False
        assert resp.error == "not connected"


class TestESP32SerialInit:
    def test_defaults(self) -> None:
        esp = ESP32Serial()
        assert esp._port == "/dev/ttyUSB0"
        assert esp._baud == 115200
        assert esp.is_connected is False

    def test_custom_port(self) -> None:
        esp = ESP32Serial(port="/dev/ttyACM0", baud=9600, timeout=5.0)
        assert esp._port == "/dev/ttyACM0"
        assert esp._baud == 9600


class TestESP32SerialConnect:
    def test_connect_success(self) -> None:
        esp = ESP32Serial()
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_mod = MagicMock()
        mock_serial_mod.Serial.return_value = mock_serial_instance

        with patch.dict("sys.modules", {"serial": mock_serial_mod}):
            result = esp.connect()

        assert result is True
        assert esp.is_connected is True

    def test_connect_failure(self) -> None:
        esp = ESP32Serial()
        mock_serial_mod = MagicMock()
        mock_serial_mod.Serial.side_effect = Exception("port busy")

        with patch.dict("sys.modules", {"serial": mock_serial_mod}):
            result = esp.connect()

        assert result is False
        assert esp.is_connected is False

    def test_close(self) -> None:
        esp = ESP32Serial()
        mock_serial = MagicMock()
        mock_serial.is_open = True
        esp._serial = mock_serial

        esp.close()
        mock_serial.close.assert_called_once()
        assert esp._serial is None


class TestESP32SerialCommands:
    def _connected_esp(self) -> tuple[ESP32Serial, MagicMock]:
        esp = ESP32Serial()
        mock_serial = MagicMock()
        mock_serial.is_open = True
        esp._serial = mock_serial
        return esp, mock_serial

    def test_send_command_not_connected(self) -> None:
        esp = ESP32Serial()
        resp = esp.send_command("STATUS")
        assert resp.ok is False
        assert resp.error == "not connected"

    def test_send_command_success(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b'{"ok":true,"pwm":128}\n'

        resp = esp.send_command("LIGHT 128")

        mock_serial.write.assert_called_once_with(b"LIGHT 128\n")
        assert resp.ok is True
        assert resp.data == {"ok": True, "pwm": 128}

    def test_send_command_timeout(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b""

        resp = esp.send_command("STATUS")
        assert resp.ok is False
        assert "timeout" in resp.error

    def test_send_command_invalid_json(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b"not json\n"

        resp = esp.send_command("STATUS")
        assert resp.ok is False
        assert "invalid JSON" in resp.error

    def test_send_command_error_response(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b'{"error":"LIGHT value must be 0-255"}\n'

        resp = esp.send_command("LIGHT 999")
        assert resp.ok is False
        assert "0-255" in resp.error

    def test_send_command_serial_exception(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.write.side_effect = OSError("device disconnected")

        resp = esp.send_command("STATUS")
        assert resp.ok is False
        assert "disconnected" in resp.error

    def test_set_light(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b'{"ok":true,"pwm":200}\n'

        resp = esp.set_light(200)
        mock_serial.write.assert_called_once_with(b"LIGHT 200\n")
        assert resp.ok is True

    def test_set_light_clamps(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b'{"ok":true,"pwm":255}\n'

        esp.set_light(999)
        mock_serial.write.assert_called_once_with(b"LIGHT 255\n")

    def test_set_light_clamps_negative(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b'{"ok":true,"pwm":0}\n'

        esp.set_light(-50)
        mock_serial.write.assert_called_once_with(b"LIGHT 0\n")

    def test_set_pump_on(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b'{"ok":true,"pump":true}\n'

        resp = esp.set_pump(True)
        mock_serial.write.assert_called_once_with(b"PUMP 1\n")
        assert resp.ok is True

    def test_set_pump_off(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b'{"ok":true,"pump":false}\n'

        resp = esp.set_pump(False)
        mock_serial.write.assert_called_once_with(b"PUMP 0\n")

    def test_get_status(self) -> None:
        esp, mock_serial = self._connected_esp()
        mock_serial.readline.return_value = b'{"pwm":128,"pump":false,"uptime":3600}\n'

        resp = esp.get_status()
        mock_serial.write.assert_called_once_with(b"STATUS\n")
        assert resp.ok is True
        assert resp.data["uptime"] == 3600
