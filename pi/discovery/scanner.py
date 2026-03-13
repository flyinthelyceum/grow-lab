"""Hardware bus scanning — I²C, 1-Wire, and serial port detection.

Probes available buses and returns discovered device addresses/paths.
Used by the registry to build the sensor driver map at startup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class I2CDevice:
    bus: int
    address: int


@dataclass(frozen=True)
class OneWireDevice:
    device_id: str
    path: Path


@dataclass(frozen=True)
class SerialDevice:
    port: str


@dataclass(frozen=True)
class ScanResult:
    i2c_devices: tuple[I2CDevice, ...]
    onewire_devices: tuple[OneWireDevice, ...]
    serial_devices: tuple[SerialDevice, ...]


def scan_i2c(bus_number: int = 1) -> tuple[I2CDevice, ...]:
    """Scan the I²C bus for connected devices.

    Returns discovered devices as a tuple of I2CDevice.
    Returns empty tuple if the bus is not available.
    """
    try:
        import smbus2

        bus = smbus2.SMBus(bus_number)
        devices: list[I2CDevice] = []

        for address in range(0x03, 0x78):
            try:
                bus.read_byte(address)
                devices.append(I2CDevice(bus=bus_number, address=address))
                logger.debug("I²C device found at 0x%02X", address)
            except OSError:
                pass

        bus.close()
        logger.info(
            "I²C scan complete: %d device(s) on bus %d", len(devices), bus_number
        )
        return tuple(devices)

    except (ImportError, FileNotFoundError, OSError) as exc:
        logger.warning("I²C bus %d not available: %s", bus_number, exc)
        return ()


def scan_onewire() -> tuple[OneWireDevice, ...]:
    """Scan the 1-Wire bus for DS18B20 temperature sensors.

    Reads /sys/bus/w1/devices/ for device directories.
    Returns empty tuple if 1-Wire is not available.
    """
    w1_path = Path("/sys/bus/w1/devices")
    if not w1_path.exists():
        logger.warning("1-Wire bus not available at %s", w1_path)
        return ()

    devices: list[OneWireDevice] = []
    for entry in w1_path.iterdir():
        if entry.name.startswith("28-"):
            sensor_file = entry / "w1_slave"
            if sensor_file.exists():
                devices.append(
                    OneWireDevice(device_id=entry.name, path=sensor_file)
                )
                logger.debug("1-Wire device found: %s", entry.name)

    logger.info("1-Wire scan complete: %d device(s)", len(devices))
    return tuple(devices)


def scan_serial(preferred_port: str = "/dev/ttyACM0") -> tuple[SerialDevice, ...]:
    """Check for available serial ports (ESP32 connection).

    Checks the preferred port first, then scans common alternatives.
    Returns empty tuple if no serial device is found.
    """
    candidates = [preferred_port, "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]
    devices: list[SerialDevice] = []

    for port in candidates:
        if Path(port).exists():
            devices.append(SerialDevice(port=port))
            logger.debug("Serial device found: %s", port)

    logger.info("Serial scan complete: %d device(s)", len(devices))
    return tuple(devices)


def scan_all(
    i2c_bus: int = 1, serial_port: str = "/dev/ttyACM0"
) -> ScanResult:
    """Run all hardware scans and return a combined result."""
    return ScanResult(
        i2c_devices=scan_i2c(i2c_bus),
        onewire_devices=scan_onewire(),
        serial_devices=scan_serial(serial_port),
    )
