"""Tests for the GPIO relay pump controller."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pi.drivers.esp32_serial import ESP32Response


class TestGPIORelayPump:
    def _make_driver(self, gpio_pin: int = 17):
        from pi.drivers.gpio_relay import GPIORelayPump

        return GPIORelayPump(gpio_pin=gpio_pin)

    def test_set_pump_on_returns_ok_response(self):
        mock_gpio = MagicMock()
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=mock_gpio):
            driver = self._make_driver()
            response = driver.set_pump(True)

        assert response.ok is True
        mock_gpio.setup.assert_called_once_with(17, mock_gpio.OUT, initial=mock_gpio.HIGH)
        mock_gpio.output.assert_called_once_with(17, mock_gpio.LOW)

    def test_set_pump_off_returns_ok_response(self):
        mock_gpio = MagicMock()
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=mock_gpio):
            driver = self._make_driver()
            response = driver.set_pump(False)

        assert response.ok is True
        mock_gpio.output.assert_called_once_with(17, mock_gpio.HIGH)

    def test_set_pump_returns_error_on_gpio_failure(self):
        mock_gpio = MagicMock()
        mock_gpio.output.side_effect = RuntimeError("GPIO not available")
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=mock_gpio):
            driver = self._make_driver()
            response = driver.set_pump(True)

        assert response.ok is False
        assert "GPIO not available" in response.error

    def test_set_pump_returns_error_when_no_gpio_module(self):
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=None):
            driver = self._make_driver()
            response = driver.set_pump(True)

        assert response.ok is False
        assert response.error is not None

    def test_close_cleans_up_gpio(self):
        mock_gpio = MagicMock()
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=mock_gpio):
            driver = self._make_driver()
            driver.set_pump(True)  # Initialize pin
            driver.close()

        mock_gpio.output.assert_any_call(17, mock_gpio.HIGH)
        mock_gpio.cleanup.assert_called_once_with(17)

    def test_close_without_activation_is_safe(self):
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=None):
            driver = self._make_driver()
            driver.close()  # Should not raise

    def test_response_is_esp32_response(self):
        """GPIORelayPump returns ESP32Response for irrigation service compat."""
        mock_gpio = MagicMock()
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=mock_gpio):
            driver = self._make_driver()
            response = driver.set_pump(True)

        assert isinstance(response, ESP32Response)

    def test_custom_gpio_pin(self):
        mock_gpio = MagicMock()
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=mock_gpio):
            driver = self._make_driver(gpio_pin=27)
            driver.set_pump(True)

        mock_gpio.setup.assert_called_once_with(27, mock_gpio.OUT, initial=mock_gpio.HIGH)
        mock_gpio.output.assert_called_once_with(27, mock_gpio.LOW)

    def test_close_handles_cleanup_error(self):
        """close() should not raise even if GPIO cleanup fails."""
        mock_gpio = MagicMock()
        mock_gpio.cleanup.side_effect = RuntimeError("bus error")
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=mock_gpio):
            driver = self._make_driver()
            driver.set_pump(True)  # Initialize
            driver.close()  # Should not raise

    def test_active_high_mode(self):
        """Active-high relay should invert pin logic."""
        from pi.drivers.gpio_relay import GPIORelayPump

        mock_gpio = MagicMock()
        with patch("pi.drivers.gpio_relay._get_gpio", return_value=mock_gpio):
            driver = GPIORelayPump(gpio_pin=17, active_low=False)
            response = driver.set_pump(True)

        assert response.ok is True
        mock_gpio.setup.assert_called_once_with(17, mock_gpio.OUT, initial=mock_gpio.LOW)
        mock_gpio.output.assert_called_once_with(17, mock_gpio.HIGH)
