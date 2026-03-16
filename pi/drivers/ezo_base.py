"""Shared Atlas EZO I²C protocol driver.

Atlas EZO boards (pH, EC, ORP, DO, etc.) all use the same I²C
command/response protocol:

  1. Write an ASCII command string to the device address.
  2. Wait for processing (read commands need ~900ms).
  3. Read back a response: byte 0 is status, bytes 1+ are ASCII data.

Status codes:
  1   = success, data follows
  2   = syntax error in command
  254 = still processing (not ready)
  255 = no data to send

This module provides the shared read/write/parse logic. Sensor-specific
drivers (ezo_ph, ezo_ec) subclass and add their own parsing/validation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod

from pi.data.models import SensorReading

logger = logging.getLogger(__name__)

# EZO response status codes
STATUS_SUCCESS = 1
STATUS_SYNTAX_ERROR = 2
STATUS_PENDING = 254
STATUS_NO_DATA = 255

# Default wait time for a read command (ms)
READ_DELAY_MS = 900


class EZOBase(ABC):
    """Base driver for Atlas EZO I²C sensors."""

    def __init__(self, bus_number: int = 1, address: int = 0x00) -> None:
        self._bus_number = bus_number
        self._address = address
        self._bus = None

    @property
    @abstractmethod
    def sensor_id(self) -> str: ...

    @abstractmethod
    def _parse_response(self, data: str) -> list[SensorReading]:
        """Parse a successful ASCII response into SensorReading(s).

        Subclasses validate range and build typed readings.
        Returns empty list if data is invalid.
        """
        ...

    def _get_bus(self):
        if self._bus is None:
            import smbus2

            self._bus = smbus2.SMBus(self._bus_number)
        return self._bus

    def _send_command(self, command: str) -> None:
        """Write an ASCII command to the EZO device."""
        bus = self._get_bus()
        cmd_bytes = [ord(c) for c in command]
        bus.write_i2c_block_data(self._address, cmd_bytes[0], cmd_bytes[1:])

    def _read_response(self) -> tuple[int, str]:
        """Read response from the EZO device.

        Returns (status_code, ascii_data).
        """
        bus = self._get_bus()
        raw = bus.read_i2c_block_data(self._address, 0x00, 31)
        status = raw[0]
        # Strip null bytes from payload
        payload_bytes = bytes(b for b in raw[1:] if b != 0x00)
        return status, payload_bytes.decode("ascii", errors="replace")

    async def read(self) -> list[SensorReading]:
        """Send a read command and parse the response.

        Returns SensorReading(s) or empty list on failure.
        """
        try:

            def _do_read():
                self._send_command("R")
                time.sleep(READ_DELAY_MS / 1000.0)
                return self._read_response()

            status, data = await asyncio.to_thread(_do_read)

            if status != STATUS_SUCCESS:
                logger.warning(
                    "%s read status %d (expected 1)", self.sensor_id, status
                )
                return []

            return self._parse_response(data)

        except Exception as exc:
            logger.error("%s read failed: %s", self.sensor_id, exc)
            return []

    async def is_available(self) -> bool:
        """Check if the EZO device is responding on the I²C bus."""
        try:

            def _check():
                bus = self._get_bus()
                bus.read_byte(self._address)

            await asyncio.to_thread(_check)
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Release the I²C bus."""
        if self._bus is not None:
            self._bus.close()
            self._bus = None
