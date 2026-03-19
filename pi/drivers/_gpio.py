"""Shared GPIO module — ensures setmode is called exactly once.

Both fan_pwm.py and gpio_relay.py need RPi.GPIO in BCM mode.
This module initializes it once and caches the result.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_gpio = None
_initialized = False


def get_gpio():
    """Return the RPi.GPIO module in BCM mode, or None if unavailable."""
    global _gpio, _initialized

    if _initialized:
        return _gpio

    _initialized = True
    try:
        import RPi.GPIO as GPIO

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        _gpio = GPIO
    except (ImportError, RuntimeError):
        _gpio = None

    return _gpio
