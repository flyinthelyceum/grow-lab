"""ESP32 serial command interface.

Sends newline-delimited commands to the ESP32 over USB serial.
Parses JSON responses. Gracefully handles missing ESP32.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ESP32Response:
    """Parsed response from the ESP32."""

    raw: str
    data: dict
    ok: bool
    error: str | None = None


class ESP32Serial:
    """Serial command interface to the ESP32 controller."""

    def __init__(self, port: str = "/dev/ttyACM0", baud: int = 115200, timeout: float = 2.0) -> None:
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._serial = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def connect(self) -> bool:
        """Open the serial connection. Returns True on success."""
        try:
            import serial

            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baud,
                timeout=self._timeout,
            )
            # Give USB CDC devices a brief moment after open/reset.
            time.sleep(0.3)
            # Drain any boot messages
            self._serial.reset_input_buffer()
            logger.info("ESP32 connected on %s @ %d baud", self._port, self._baud)
            return True
        except Exception as exc:
            logger.warning("ESP32 connection failed on %s: %s", self._port, exc)
            self._serial = None
            return False

    def close(self) -> None:
        """Close the serial connection."""
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def send_command(self, command: str) -> ESP32Response:
        """Send a command and read the JSON response.

        Returns an ESP32Response with ok=False if the ESP32 is not
        connected or the response can't be parsed.
        """
        if not self.is_connected:
            return ESP32Response(
                raw="", data={}, ok=False, error="not connected"
            )

        try:
            line = command.strip() + "\n"
            self._serial.write(line.encode("utf-8"))
            self._serial.flush()

            response_line = self._serial.readline().decode("utf-8").strip()

            if not response_line:
                return ESP32Response(
                    raw="", data={}, ok=False, error="no response (timeout)"
                )

            data = json.loads(response_line)
            error = data.get("error")
            ok = error is None

            return ESP32Response(raw=response_line, data=data, ok=ok, error=error)

        except json.JSONDecodeError as exc:
            logger.error("ESP32 invalid JSON: %s", exc)
            return ESP32Response(
                raw=response_line,
                data={},
                ok=False,
                error=f"invalid JSON: {exc}",
            )
        except Exception as exc:
            logger.error("ESP32 communication error: %s", exc)
            return ESP32Response(
                raw="", data={}, ok=False, error=str(exc)
            )

    def set_light(self, pwm: int) -> ESP32Response:
        """Set LED PWM duty cycle (0-255)."""
        pwm = max(0, min(255, pwm))
        return self.send_command(f"LIGHT {pwm}")

    def set_pump(self, on: bool) -> ESP32Response:
        """Set pump relay state."""
        return self.send_command(f"PUMP {1 if on else 0}")

    def get_status(self) -> ESP32Response:
        """Request current ESP32 status."""
        return self.send_command("STATUS")
