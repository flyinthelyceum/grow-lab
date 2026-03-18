"""Tests for the fan PWM driver — Noctua NF-A12x25 on Pi GPIO."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pi.drivers.fan_pwm import FanPWMDriver


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


class TestFanPWMTemperatureRamp:
    def test_duty_for_temp_below_low(self) -> None:
        driver = FanPWMDriver()
        assert driver.duty_for_temperature(60.0) == 0

    def test_duty_for_temp_at_low(self) -> None:
        driver = FanPWMDriver()
        assert driver.duty_for_temperature(70.0) == driver._min_duty

    def test_duty_for_temp_at_high(self) -> None:
        driver = FanPWMDriver()
        assert driver.duty_for_temperature(85.0) == 100

    def test_duty_for_temp_above_high(self) -> None:
        driver = FanPWMDriver()
        assert driver.duty_for_temperature(95.0) == 100

    def test_duty_for_temp_midpoint(self) -> None:
        """Midpoint between 70-85°F should give ~60% duty."""
        driver = FanPWMDriver()
        duty = driver.duty_for_temperature(77.5)
        assert 45 <= duty <= 75  # Roughly middle of range

    def test_custom_ramp_range(self) -> None:
        driver = FanPWMDriver(ramp_temp_low_f=65.0, ramp_temp_high_f=80.0)
        assert driver.duty_for_temperature(64.0) == 0
        assert driver.duty_for_temperature(80.0) == 100


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
