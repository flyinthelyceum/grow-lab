"""GPIO relay pump controller — direct Pi GPIO without ESP32.

Controls a 5V relay module connected to a Pi GPIO pin.
Returns ESP32Response objects for compatibility with the
IrrigationService (drop-in replacement for ESP32Serial pump control).

Default relay logic is active-low for the SunFounder-style modules used in V0:
LOW = relay ON (pump running), HIGH = relay OFF.
"""

from __future__ import annotations

import logging

from pi.drivers._gpio import get_gpio as _get_gpio
from pi.drivers.esp32_serial import ESP32Response

logger = logging.getLogger(__name__)


class GPIORelayPump:
    """Pump controller using a GPIO-driven relay (no ESP32 needed).

    Compatible with the ESP32Serial.set_pump() interface so
    IrrigationService can use either backend.
    """

    def __init__(self, gpio_pin: int = 17, active_low: bool = True) -> None:
        self._gpio_pin = gpio_pin
        self._active_low = active_low
        self._initialized = False

    def set_pump(self, on: bool) -> ESP32Response:
        """Set pump relay state via GPIO.

        Returns ESP32Response for irrigation service compatibility.
        """
        gpio = _get_gpio()
        if gpio is None:
            return ESP32Response(
                raw="",
                data={},
                ok=False,
                error="RPi.GPIO not available (not running on Pi?)",
            )

        try:
            if not self._initialized:
                initial = gpio.HIGH if self._active_low else gpio.LOW
                gpio.setup(self._gpio_pin, gpio.OUT, initial=initial)
                self._initialized = True

            if self._active_low:
                state = gpio.LOW if on else gpio.HIGH
            else:
                state = gpio.HIGH if on else gpio.LOW
            gpio.output(self._gpio_pin, state)

            logger.debug("GPIO%d relay %s", self._gpio_pin, "ON" if on else "OFF")
            return ESP32Response(
                raw=f"PUMP {'ON' if on else 'OFF'}",
                data={"pump": on},
                ok=True,
            )
        except Exception as exc:
            logger.error("GPIO relay error on pin %d: %s", self._gpio_pin, exc)
            return ESP32Response(
                raw="",
                data={},
                ok=False,
                error=str(exc),
            )

    def close(self) -> None:
        """Ensure relay is off and release GPIO pin."""
        gpio = _get_gpio()
        if gpio is None or not self._initialized:
            return

        try:
            off_state = gpio.HIGH if self._active_low else gpio.LOW
            gpio.output(self._gpio_pin, off_state)
            gpio.cleanup(self._gpio_pin)
            self._initialized = False
            logger.debug("GPIO%d relay cleaned up", self._gpio_pin)
        except Exception as exc:
            logger.warning("GPIO cleanup error: %s", exc)
