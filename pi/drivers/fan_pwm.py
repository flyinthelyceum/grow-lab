"""Fan PWM driver — Noctua NF-A12x25 on Pi GPIO.

Controls fan speed via hardware PWM on a Pi GPIO pin.
The Noctua NF-A12x25 accepts 3.3V PWM directly (no level shifting needed).

Includes a temperature-triggered ramp: maps air temperature (°F) to
duty cycle, ramping linearly from min_duty at ramp_temp_low_f to 100%
at ramp_temp_high_f. Below ramp_temp_low_f the fan is off.
"""

from __future__ import annotations

import logging

from pi.drivers._gpio import get_gpio as _get_gpio

logger = logging.getLogger(__name__)


class FanPWMDriver:
    """PWM fan controller using Pi GPIO hardware PWM.

    Compatible with Noctua 4-pin fans that accept 25kHz PWM.
    """

    def __init__(
        self,
        gpio_pin: int = 18,
        frequency: int = 25000,
        min_duty: int = 20,
        max_duty: int = 100,
        ramp_temp_low_f: float = 70.0,
        ramp_temp_high_f: float = 85.0,
    ) -> None:
        self._gpio_pin = gpio_pin
        self._frequency = frequency
        self._min_duty = min_duty
        self._max_duty = max_duty
        self._ramp_temp_low_f = ramp_temp_low_f
        self._ramp_temp_high_f = ramp_temp_high_f
        self._duty_cycle = 0
        self._pwm = None
        self._initialized = False

    @property
    def is_available(self) -> bool:
        """Check if GPIO PWM is available."""
        return _get_gpio() is not None

    @property
    def duty_cycle(self) -> int:
        """Current duty cycle (0-100)."""
        return self._duty_cycle

    def set_duty(self, duty: int) -> bool:
        """Set fan duty cycle (0-100).

        Values between 1 and min_duty are clamped up to min_duty.
        0 means fan off. Values above max_duty are clamped down.

        Returns True on success, False on failure.
        """
        gpio = _get_gpio()
        if gpio is None:
            logger.warning("Fan PWM unavailable — RPi.GPIO not found")
            return False

        # Clamp
        if duty > self._max_duty:
            duty = self._max_duty
        elif 0 < duty < self._min_duty:
            duty = self._min_duty

        try:
            if not self._initialized:
                gpio.setup(self._gpio_pin, gpio.OUT)
                self._pwm = gpio.PWM(self._gpio_pin, self._frequency)
                self._pwm.start(duty)
                self._initialized = True
            else:
                self._pwm.ChangeDutyCycle(duty)

            self._duty_cycle = duty
            logger.debug("Fan PWM GPIO%d → %d%%", self._gpio_pin, duty)
            return True
        except Exception as exc:
            logger.error("Fan PWM error on GPIO%d: %s", self._gpio_pin, exc)
            return False

    def duty_for_temperature(self, temp_f: float) -> int:
        """Calculate target duty cycle from air temperature (°F).

        Linear ramp from min_duty at ramp_temp_low to 100% at ramp_temp_high.
        Below ramp_temp_low: fan off (0%).
        Above ramp_temp_high: full speed (100%).
        """
        return self.static_duty_for_temperature(
            temp_f,
            min_duty=self._min_duty,
            max_duty=self._max_duty,
            ramp_low=self._ramp_temp_low_f,
            ramp_high=self._ramp_temp_high_f,
        )

    @staticmethod
    def static_duty_for_temperature(
        temp_f: float,
        *,
        min_duty: int = 20,
        max_duty: int = 100,
        ramp_low: float = 70.0,
        ramp_high: float = 85.0,
    ) -> int:
        """Calculate duty cycle without needing a driver instance."""
        if temp_f < ramp_low:
            return 0
        if temp_f >= ramp_high:
            return max_duty

        temp_range = ramp_high - ramp_low
        fraction = (temp_f - ramp_low) / temp_range
        duty_range = max_duty - min_duty
        return round(min_duty + fraction * duty_range)

    def close(self) -> None:
        """Stop PWM and release GPIO pin."""
        if self._pwm is not None:
            try:
                self._pwm.stop()
            except Exception as exc:
                logger.debug("Fan PWM stop error: %s", exc)

        gpio = _get_gpio()
        if gpio is not None and self._initialized:
            try:
                gpio.cleanup(self._gpio_pin)
            except Exception as exc:
                logger.debug("Fan GPIO cleanup error: %s", exc)

        self._pwm = None
        self._initialized = False
