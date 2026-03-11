"""Sensor registry — maps discovered hardware to driver instances.

At startup, the registry scans hardware buses, matches discovered
devices against configured sensors, and builds an immutable map of
sensor_id -> SensorDriver. Missing sensors are logged but don't
prevent the system from running.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pi.config.schema import AppConfig
from pi.discovery.scanner import I2CDevice, ScanResult
from pi.drivers.base import SensorDriver

logger = logging.getLogger(__name__)

# Known I²C address -> sensor name mapping
I2C_ADDRESS_MAP: dict[int, str] = {
    0x76: "bme280",
    0x77: "bme280",  # alternate address
    0x63: "ezo_ph",
    0x64: "ezo_ec",
    0x36: "soil_moisture",
    0x37: "soil_moisture",  # alternate
    0x38: "soil_moisture",  # alternate
    0x39: "soil_moisture",  # alternate
    0x3C: "oled_display",
    0x3D: "oled_display",
}


@dataclass(frozen=True)
class SensorStatus:
    sensor_id: str
    available: bool
    driver: SensorDriver | None
    reason: str


class SensorRegistry:
    """Immutable registry of available sensor drivers.

    Built once at startup from scan results + config.
    """

    def __init__(self, statuses: tuple[SensorStatus, ...]) -> None:
        self._statuses = statuses
        self._drivers: dict[str, SensorDriver] = {
            s.sensor_id: s.driver
            for s in statuses
            if s.available and s.driver is not None
        }

    @property
    def available_drivers(self) -> dict[str, SensorDriver]:
        """All available sensor drivers, keyed by sensor_id."""
        return dict(self._drivers)

    @property
    def all_statuses(self) -> tuple[SensorStatus, ...]:
        return self._statuses

    def get_driver(self, sensor_id: str) -> SensorDriver | None:
        return self._drivers.get(sensor_id)

    def is_available(self, sensor_id: str) -> bool:
        return sensor_id in self._drivers


def _find_i2c_device(
    address: int, scan: ScanResult
) -> I2CDevice | None:
    """Find an I²C device by address in scan results."""
    for device in scan.i2c_devices:
        if device.address == address:
            return device
    return None


def build_registry(config: AppConfig, scan: ScanResult) -> SensorRegistry:
    """Build a sensor registry from config and scan results.

    Attempts to create a driver for each configured sensor.
    Sensors not found on the bus are marked unavailable.
    """
    statuses: list[SensorStatus] = []

    # BME280
    if config.sensors.bme280.enabled:
        addr = config.sensors.bme280.address
        device = _find_i2c_device(addr, scan)
        if device is not None:
            try:
                from pi.drivers.bme280 import BME280Driver

                driver = BME280Driver(
                    bus_number=config.i2c.bus, address=addr
                )
                statuses.append(
                    SensorStatus("bme280", True, driver, "detected")
                )
                logger.info("BME280 registered at 0x%02X", addr)
            except Exception as exc:
                statuses.append(
                    SensorStatus("bme280", False, None, f"init failed: {exc}")
                )
                logger.error("BME280 init failed: %s", exc)
        else:
            statuses.append(
                SensorStatus(
                    "bme280",
                    False,
                    None,
                    f"not found at 0x{addr:02X}",
                )
            )
            logger.warning("BME280 not found at 0x%02X", addr)

    # DS18B20 (1-Wire)
    if config.sensors.ds18b20.enabled:
        if scan.onewire_devices:
            for ow_device in scan.onewire_devices:
                try:
                    from pi.drivers.ds18b20 import DS18B20Driver

                    driver = DS18B20Driver(
                        device_id=ow_device.device_id,
                        device_path=ow_device.path,
                    )
                    sid = driver.sensor_id
                    statuses.append(
                        SensorStatus(sid, True, driver, "detected")
                    )
                    logger.info("DS18B20 registered: %s", sid)
                except Exception as exc:
                    statuses.append(
                        SensorStatus(
                            f"ds18b20_{ow_device.device_id}",
                            False,
                            None,
                            f"init failed: {exc}",
                        )
                    )
                    logger.error("DS18B20 %s init failed: %s", ow_device.device_id, exc)
        else:
            statuses.append(
                SensorStatus("ds18b20", False, None, "no 1-Wire devices found")
            )

    # Atlas EZO-pH
    if config.sensors.ezo_ph.enabled:
        addr = config.sensors.ezo_ph.address
        device = _find_i2c_device(addr, scan)
        if device is not None:
            statuses.append(
                SensorStatus("ezo_ph", False, None, "driver not yet implemented")
            )
            logger.info("EZO-pH detected at 0x%02X, driver pending", addr)
        else:
            msg = f"not found at 0x{addr:02X} — may still be in UART mode"
            statuses.append(SensorStatus("ezo_ph", False, None, msg))
            logger.warning("EZO-pH %s", msg)

    # Atlas EZO-EC
    if config.sensors.ezo_ec.enabled:
        addr = config.sensors.ezo_ec.address
        device = _find_i2c_device(addr, scan)
        if device is not None:
            statuses.append(
                SensorStatus("ezo_ec", False, None, "driver not yet implemented")
            )
            logger.info("EZO-EC detected at 0x%02X, driver pending", addr)
        else:
            msg = f"not found at 0x{addr:02X} — may still be in UART mode"
            statuses.append(SensorStatus("ezo_ec", False, None, msg))
            logger.warning("EZO-EC %s", msg)

    # Soil Moisture (STEMMA)
    if config.sensors.soil_moisture.enabled:
        addr = config.sensors.soil_moisture.address
        device = _find_i2c_device(addr, scan)
        if device is not None:
            statuses.append(
                SensorStatus(
                    "soil_moisture", False, None, "driver not yet implemented"
                )
            )
            logger.info("Soil moisture detected at 0x%02X, driver pending", addr)
        else:
            statuses.append(
                SensorStatus(
                    "soil_moisture",
                    False,
                    None,
                    f"not found at 0x{addr:02X}",
                )
            )

    # ESP32 serial
    if scan.serial_devices:
        statuses.append(
            SensorStatus(
                "esp32",
                False,
                None,
                f"serial detected at {scan.serial_devices[0].port}, driver pending",
            )
        )
    else:
        statuses.append(
            SensorStatus("esp32", False, None, "no serial device found")
        )

    return SensorRegistry(tuple(statuses))
