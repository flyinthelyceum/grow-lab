"""Frozen dataclasses defining the configuration shape.

Every config section is immutable after load. Validated at startup,
referenced by all modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _default_data_dir() -> Path:
    return Path.home() / "grow-lab-data"


@dataclass(frozen=True)
class SystemConfig:
    log_level: str = "INFO"
    data_dir: Path = field(default_factory=_default_data_dir)
    db_path: Path = field(
        default_factory=lambda: _default_data_dir() / "growlab.db"
    )


@dataclass(frozen=True)
class I2CConfig:
    bus: int = 1


@dataclass(frozen=True)
class SerialConfig:
    port: str = "/dev/ttyUSB0"
    baud: int = 115200
    timeout: float = 2.0


@dataclass(frozen=True)
class SensorEntry:
    address: int = 0
    gpio: int = 0
    interval_seconds: int = 120
    enabled: bool = True


@dataclass(frozen=True)
class SensorsConfig:
    bme280: SensorEntry = field(
        default_factory=lambda: SensorEntry(address=0x76, interval_seconds=120)
    )
    ezo_ph: SensorEntry = field(
        default_factory=lambda: SensorEntry(address=0x63, interval_seconds=300)
    )
    ezo_ec: SensorEntry = field(
        default_factory=lambda: SensorEntry(address=0x64, interval_seconds=300)
    )
    ds18b20: SensorEntry = field(
        default_factory=lambda: SensorEntry(gpio=4, interval_seconds=120)
    )
    soil_moisture: SensorEntry = field(
        default_factory=lambda: SensorEntry(address=0x36, interval_seconds=300)
    )


@dataclass(frozen=True)
class CameraConfig:
    interval_seconds: int = 600
    resolution: tuple[int, int] = (4608, 2592)
    output_dir: Path = field(
        default_factory=lambda: _default_data_dir() / "images"
    )
    enabled: bool = True


@dataclass(frozen=True)
class IrrigationScheduleEntry:
    hour: int = 8
    minute: int = 0
    duration_seconds: int = 10


@dataclass(frozen=True)
class LightingConfig:
    mode: str = "veg"
    on_hour: int = 6
    off_hour: int = 22
    intensity: int = 200
    ramp_minutes: int = 15


@dataclass(frozen=True)
class IrrigationConfig:
    schedules: tuple[IrrigationScheduleEntry, ...] = field(
        default_factory=lambda: (
            IrrigationScheduleEntry(hour=8),
            IrrigationScheduleEntry(hour=14),
            IrrigationScheduleEntry(hour=20),
        )
    )
    max_runtime_seconds: int = 30
    min_interval_minutes: int = 60
    relay_gpio: int = 17


@dataclass(frozen=True)
class DisplayConfig:
    enabled: bool = False
    address: int = 0x3C


@dataclass(frozen=True)
class AppConfig:
    system: SystemConfig = field(default_factory=SystemConfig)
    i2c: I2CConfig = field(default_factory=I2CConfig)
    serial: SerialConfig = field(default_factory=SerialConfig)
    sensors: SensorsConfig = field(default_factory=SensorsConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    lighting: LightingConfig = field(default_factory=LightingConfig)
    irrigation: IrrigationConfig = field(default_factory=IrrigationConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
