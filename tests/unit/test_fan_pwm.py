"""Tests for the fan PWM driver — Noctua NF-A12x25 on Pi GPIO."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pi.drivers.fan_pwm import FanPWMDriver
from pi.drivers.fan_pwm import FanPWMDriver as F


class TestFanPWMInit:
    def test_defaults(self) -> None:
        driver = FanPWMDriver()
        assert driver._gpio_pin == 18
        assert driver._frequency == 25000
        assert driver._duty_cycle == 0
        assert driver._min_duty == 20
        assert driver._max_duty == 100

    def test_custom_pin_and_frequency(self) -> None:
        driver = FanPWMDriver(gpio_pin=12, frequency=10000)
        assert driver._gpio_pin == 12
        assert driver._frequency == 10000


class TestFanPWMAvailability:
    def test_not_available_without_gpio(self) -> None:
        driver = FanPWMDriver()
        with patch("pi.drivers.fan_pwm._get_gpio", return_value=None):
            assert driver.is_available is False

    def test_available_with_gpio(self) -> None:
        mock_gpio = MagicMock()
        driver = FanPWMDriver()
        with patch("pi.drivers.fan_pwm._get_gpio", return_value=mock_gpio):
            assert driver.is_available is True


class TestFanPWMSetDuty:
    def test_set_duty_initializes_pwm(self) -> None:
        mock_gpio = MagicMock()
        mock_pwm = MagicMock()
        mock_gpio.PWM.return_value = mock_pwm
        driver = FanPWMDriver()

        with patch("pi.drivers.fan_pwm._get_gpio", return_value=mock_gpio):
            result = driver.set_duty(50)

        assert result is True
        assert driver._duty_cycle == 50
        mock_gpio.setup.assert_called_once()
        mock_gpio.PWM.assert_called_once_with(18, 25000)
        mock_pwm.start.assert_called_once_with(50)

    def test_set_duty_updates_existing_pwm(self) -> None:
        mock_gpio = MagicMock()
        mock_pwm = MagicMock()
        mock_gpio.PWM.return_value = mock_pwm
        driver = FanPWMDriver()

        with patch("pi.drivers.fan_pwm._get_gpio", return_value=mock_gpio):
            driver.set_duty(50)
            driver.set_duty(75)

        mock_pwm.ChangeDutyCycle.assert_called_with(75)
        assert driver._duty_cycle == 75

    def test_set_duty_clamps_below_min(self) -> None:
        """Non-zero values below min_duty get clamped up."""
        mock_gpio = MagicMock()
        mock_pwm = MagicMock()
        mock_gpio.PWM.return_value = mock_pwm
        driver = FanPWMDriver(min_duty=20)

        with patch("pi.drivers.fan_pwm._get_gpio", return_value=mock_gpio):
            driver.set_duty(10)

        assert driver._duty_cycle == 20

    def test_set_duty_zero_stops_fan(self) -> None:
        """Duty of 0 should be allowed (fan off)."""
        mock_gpio = MagicMock()
        mock_pwm = MagicMock()
        mock_gpio.PWM.return_value = mock_pwm
        driver = FanPWMDriver()

        with patch("pi.drivers.fan_pwm._get_gpio", return_value=mock_gpio):
            driver.set_duty(50)
            driver.set_duty(0)

        assert driver._duty_cycle == 0

    def test_set_duty_clamps_above_max(self) -> None:
        mock_gpio = MagicMock()
        mock_pwm = MagicMock()
        mock_gpio.PWM.return_value = mock_pwm
        driver = FanPWMDriver()

        with patch("pi.drivers.fan_pwm._get_gpio", return_value=mock_gpio):
            driver.set_duty(120)

        assert driver._duty_cycle == 100

    def test_set_duty_returns_false_without_gpio(self) -> None:
        driver = FanPWMDriver()
        with patch("pi.drivers.fan_pwm._get_gpio", return_value=None):
            result = driver.set_duty(50)
        assert result is False

    def test_set_duty_handles_gpio_error(self) -> None:
        mock_gpio = MagicMock()
        mock_gpio.setup.side_effect = RuntimeError("pin busy")
        driver = FanPWMDriver()

        with patch("pi.drivers.fan_pwm._get_gpio", return_value=mock_gpio):
            result = driver.set_duty(50)
        assert result is False


class TestTheGustField:
    """The fan is for canopy strength, not cooling.

    Duty is a deterministic function of the clock. These assert the properties
    that make it wind rather than a metronome or a thermostat.
    """

    def test_deterministic(self) -> None:
        assert F.static_duty_for_time(12345.0) == F.static_duty_for_time(12345.0)
        assert F.gust_field(999.0) == F.gust_field(999.0)

    def test_field_stays_in_range(self) -> None:
        assert all(0.0 <= F.gust_field(t) <= 1.0 for t in range(0, 86400, 7))

    def test_duty_respects_the_stall_floor_and_ceiling(self) -> None:
        duties = [F.static_duty_for_time(t, min_duty=20, max_duty=100)
                  for t in range(0, 86400, 5)]
        assert max(duties) <= 100
        assert all(d == 0 or d >= 20 for d in duties), (
            "a non-zero duty below min_duty would sit in the stall band and buzz"
        )

    def test_it_actually_stops(self) -> None:
        """The lulls are the point — intermittent loading thickens stems."""
        duties = [F.static_duty_for_time(t) for t in range(0, 86400, 5)]
        calm = sum(1 for d in duties if d == 0) / len(duties)
        assert 0.15 < calm < 0.55, f"calm fraction {calm:.2f} is not a rhythm"

    def test_it_gusts_in_spells_not_ticks(self) -> None:
        """Slow octaves dominate, so windy and quiet periods last minutes."""
        import itertools

        duties = [F.static_duty_for_time(t) for t in range(0, 86400, 5)]
        gusts = [len(list(g)) * 5 for k, g in itertools.groupby(duties, key=bool) if k]
        assert max(gusts) > 180, "no gust outlasted three minutes; this is a metronome"

    def test_it_does_not_repeat_within_a_day(self) -> None:
        """Incommensurate periods make the field quasi-periodic."""
        head = [round(F.gust_field(t), 6) for t in range(0, 1800, 5)]
        later = [round(F.gust_field(t + 43200), 6) for t in range(0, 1800, 5)]
        assert head != later

    def test_night_is_a_stir_not_a_stop(self) -> None:
        """Still wet air overnight grows mould, not stems."""
        night = [F.static_duty_for_time(t) for t in range(0, 5 * 3600, 5)]
        day = [F.static_duty_for_time(t) for t in range(7 * 3600, 21 * 3600, 5)]
        night_mean = sum(night) / len(night)
        day_mean = sum(day) / len(day)
        assert night_mean > 5, "the canopy must not sit in dead air until dawn"
        assert night_mean < day_mean, "nights should be calmer than days"

    def test_envelope_eases_at_the_edges(self) -> None:
        """The fan must not slam to full the instant the lights come on."""
        dawn = F.diurnal_envelope(6 * 3600, 6, 22, 0.35)
        midday = F.diurnal_envelope(13 * 3600, 6, 22, 0.35)
        assert dawn < midday
        assert F.diurnal_envelope(3 * 3600, 6, 22, 0.35) == pytest.approx(0.35)

    def test_photoperiod_over_midnight(self) -> None:
        """A night-shift photoperiod must not invert the envelope."""
        assert F.diurnal_envelope(23 * 3600, 20, 4, 0.35) > 0.35
        assert F.diurnal_envelope(12 * 3600, 20, 4, 0.35) == pytest.approx(0.35)


class TestFanPWMClose:
    def test_close_stops_pwm(self) -> None:
        mock_gpio = MagicMock()
        mock_pwm = MagicMock()
        mock_gpio.PWM.return_value = mock_pwm
        driver = FanPWMDriver()

        with patch("pi.drivers.fan_pwm._get_gpio", return_value=mock_gpio):
            driver.set_duty(50)
            driver.close()

        mock_pwm.stop.assert_called_once()
        mock_gpio.cleanup.assert_called_once_with(18)

    def test_close_without_init_is_safe(self) -> None:
        driver = FanPWMDriver()
        driver.close()  # Should not raise

    def test_close_handles_error(self) -> None:
        mock_gpio = MagicMock()
        mock_pwm = MagicMock()
        mock_pwm.stop.side_effect = RuntimeError("already stopped")
        mock_gpio.PWM.return_value = mock_pwm
        driver = FanPWMDriver()

        with patch("pi.drivers.fan_pwm._get_gpio", return_value=mock_gpio):
            driver.set_duty(50)
            driver.close()  # Should not raise
