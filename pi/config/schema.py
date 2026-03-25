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
    port: str = "/dev/ttyACM0"
    baud: int = 115200
    timeout: float = 2.0


@dataclass(frozen=True)
class InstallationConfig:
    node_id: str = "growlab-node"
    fixture_id: str = ""
    fixture_model: str = ""
    sensor_board_id: str = ""


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
        default_factory=lambda: SensorEntry(address=0x48, interval_seconds=300)
    )
    soil_moisture_channel: int = 0  # ADS1115 channel (0-3) for SEN0308
    as7341: SensorEntry = field(
        default_factory=lambda: SensorEntry(address=0x39, interval_seconds=120)
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
    pump_controller: str = "gpio"  # "gpio" (direct Pi relay) or "esp32" (serial)
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
class FanConfig:
    enabled: bool = False
    gpio_pin: int = 18
    frequency: int = 25000
    min_duty: int = 20
    max_duty: int = 100
    ramp_temp_low_f: float = 70.0
    ramp_temp_high_f: float = 85.0
    poll_interval_seconds: int = 30


@dataclass(frozen=True)
class DisplayConfig:
    enabled: bool = False
    address: int = 0x3C
    controller: str = "sh1106"  # "sh1106" or "ssd1306"


@dataclass(frozen=True)
class CalibrationConfig:
    enabled: bool = False
    profile_dir: Path = field(default_factory=lambda: Path("config") / "calibration")
    active_profile: str = ""


@dataclass(frozen=True)
class WebhookConfig:
    enabled: bool = False
    url: str = ""
    timeout_seconds: float = 10.0


@dataclass(frozen=True)
class EmailConfig:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    use_tls: bool = True
    from_address: str = ""
    to_addresses: tuple[str, ...] = ()

    def __repr__(self) -> str:
        masked = "***" if self.smtp_password else ""
        return (
            f"EmailConfig(enabled={self.enabled!r}, smtp_host={self.smtp_host!r}, "
            f"smtp_port={self.smtp_port!r}, smtp_user={self.smtp_user!r}, "
            f"smtp_password={masked!r}, use_tls={self.use_tls!r}, "
            f"from_address={self.from_address!r}, "
            f"to_addresses={self.to_addresses!r})"
        )


@dataclass(frozen=True)
class NotificationConfig:
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    cooldown_seconds: int = 300


@dataclass(frozen=True)
class AppConfig:
    system: SystemConfig = field(default_factory=SystemConfig)
    i2c: I2CConfig = field(default_factory=I2CConfig)
    serial: SerialConfig = field(default_factory=SerialConfig)
    installation: InstallationConfig = field(default_factory=InstallationConfig)
    sensors: SensorsConfig = field(default_factory=SensorsConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    lighting: LightingConfig = field(default_factory=LightingConfig)
    irrigation: IrrigationConfig = field(default_factory=IrrigationConfig)
    fan: FanConfig = field(default_factory=FanConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
