"""Fan PWM driver — Noctua NF-A12x25 on Pi GPIO.

Controls fan speed via hardware PWM on a Pi GPIO pin.
The Noctua NF-A12x25 accepts 3.3V PWM directly (no level shifting needed).

The fan is not cooling. Its job is canopy strength — moving air thickens
stems (thigmomorphogenesis) — so duty is a gust field over time rather than a
ramp against temperature. A thermostat would still the air exactly when a cool
room made it least likely to move, which is backwards for this purpose.
"""

from __future__ import annotations

import logging
import math

from pi.drivers._gpio import get_gpio as _get_gpio

# Periods in seconds, deliberately not multiples of one another, so the sum
# is quasi-periodic rather than a loop anyone could learn the length of.
# The slow octaves carry the most weight, which is what makes this read as
# weather rather than a metronome: the ten-minute term decides whether it is a
# windy spell or a quiet one, and the faster terms texture it. Weighted the
# other way round the fan just breathes on a fixed ~40s cycle.
_GUST_OCTAVES = (
    (37.0, 0.12, 0.0),
    (91.0, 0.20, 1.7),
    (223.0, 0.28, 3.9),
    (613.0, 0.40, 5.2),
)

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
        day_start_hour: int = 6,
        day_end_hour: int = 22,
        night_factor: float = 0.35,
        calm_threshold: float = 0.40,
    ) -> None:
        self._gpio_pin = gpio_pin
        self._frequency = frequency
        self._min_duty = min_duty
        self._max_duty = max_duty
        self._day_start_hour = day_start_hour
        self._day_end_hour = day_end_hour
        self._night_factor = night_factor
        self._calm_threshold = calm_threshold
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

    def duty_for_time(self, now: float) -> int:
        """Gust duty for a moment in time. No sensor input."""
        return self.static_duty_for_time(
            now,
            min_duty=self._min_duty,
            max_duty=self._max_duty,
            day_start_hour=self._day_start_hour,
            day_end_hour=self._day_end_hour,
            night_factor=self._night_factor,
            calm_threshold=self._calm_threshold,
        )

    @staticmethod
    def gust_field(now: float) -> float:
        """A fractal gust field in [0, 1] — the shape of wind.

        Four sine octaves at mutually incommensurate periods. Their ratios are
        irrational, so the sum is quasi-periodic: it never exactly repeats, and
        there is no seed or accumulated state to drift. The same instant always
        gives the same answer, which is what makes this testable.
        """
        total = 0.0
        for period, weight, phase in _GUST_OCTAVES:
            total += weight * (0.5 + 0.5 * math.sin(2.0 * math.pi * now / period + phase))
        return min(1.0, max(0.0, total))

    @staticmethod
    def diurnal_envelope(
        now: float, day_start_hour: int, day_end_hour: int, night_factor: float
    ) -> float:
        """Scale gusts by the plant's own day, not the room's temperature.

        Full strength through the photoperiod, easing in and out over an hour
        at each edge so the fan does not slam on with the lights, and settling
        to ``night_factor`` overnight — a stir rather than stillness, because
        still wet air overnight is how you get mould, not a stronger stem.
        """
        hour = (now % 86400.0) / 3600.0
        if day_start_hour == day_end_hour:
            return 1.0
        lit = (
            day_start_hour <= hour < day_end_hour
            if day_start_hour < day_end_hour
            else hour >= day_start_hour or hour < day_end_hour
        )
        if not lit:
            return night_factor
        edge = min((hour - day_start_hour) % 24.0, (day_end_hour - hour) % 24.0)
        if edge >= 1.0:
            return 1.0
        return night_factor + (1.0 - night_factor) * edge

    @staticmethod
    def static_duty_for_time(
        now: float,
        *,
        min_duty: int = 20,
        max_duty: int = 100,
        day_start_hour: int = 6,
        day_end_hour: int = 22,
        night_factor: float = 0.35,
        calm_threshold: float = 0.40,
    ) -> int:
        """Map a moment to a duty cycle.

        Below ``calm_threshold`` the fan stops outright rather than idling at
        the stall floor. The lulls are the point: intermittent loading is what
        thickens a stem, and a fan that never stops is a constant the plant
        simply grows around.
        """
        gust = FanPWMDriver.gust_field(now)
        if gust < calm_threshold:
            return 0
        strength = (gust - calm_threshold) / (1.0 - calm_threshold)
        # The envelope scales how hard it blows, never whether it blows at all.
        # Folding it in before the threshold instead would push the whole night
        # under the cutoff and leave the canopy in dead air until dawn.
        strength *= FanPWMDriver.diurnal_envelope(
            now, day_start_hour, day_end_hour, night_factor
        )
        span = max_duty - min_duty
        return round(min_duty + span * min(1.0, strength))

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
