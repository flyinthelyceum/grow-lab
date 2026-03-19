"""EZO UART helper — switch Atlas Scientific sensors from UART to I2C mode.

The Atlas EZO sensors ship in UART mode by default. This helper sends
the I2C mode-switch command over UART so the sensor reboots into I2C
mode and becomes accessible to the existing I2C drivers.

Protocol: Send "I2C,<address>\r" at 9600 baud.
Response: "*OK" followed by sensor reboot into I2C mode.
"""

from __future__ import annotations

import logging

import serial

logger = logging.getLogger(__name__)

# Decimal I2C addresses for each EZO sensor type
EZO_ADDRESSES: dict[str, int] = {
    "ph": 99,   # 0x63
    "ec": 100,  # 0x64
}


def switch_to_i2c(port: str, baud: int, i2c_address: int) -> str:
    """Send the I2C mode-switch command to an EZO sensor via UART.

    Args:
        port: Serial port path (e.g., /dev/ttyUSB0).
        baud: Baud rate (EZO default is 9600).
        i2c_address: Target I2C address (decimal, e.g., 99 for pH).

    Returns:
        Response string from the sensor (e.g., "*OK" or "*RS").

    Raises:
        serial.SerialException: If the port cannot be opened.
    """
    with serial.Serial(port, baud, timeout=2) as conn:
        command = f"I2C,{i2c_address}\r".encode()
        conn.write(command)
        response = conn.readline().decode().strip()
        logger.info(
            "EZO UART → I2C switch: sent I2C,%d on %s, response: %s",
            i2c_address,
            port,
            response,
        )
        return response
