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
class MeterChannelConfig:
    """One centre-zero movement on a differential DAC pair."""

    sensor_id: str = "ezo_ph"
    centre: float = 6.0  # sensor value at mechanical centre
    span: float = 1.0  # half-range: deflection reaching a full endpoint
    scale: float = 1.0  # applied to the raw reading (e.g. uS/cm -> mS/cm)
    dac_positive: str = "A"
    dac_negative: str = "B"
    midpoint_code: int = 2048
    span_counts: int = 2048
    invert: bool = False
    # (commanded, actual) pairs, ascending — five-point linearisation.
    calibration: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class MetersConfig:
    enabled: bool = False
    i2c_address: int = 0x60
    update_hz: int = 30
    time_constant_seconds: float = 2.0
    sample_interval_seconds: float = 10.0
    fault_timeout_seconds: float = 900.0
    ph: MeterChannelConfig = field(
        default_factory=lambda: MeterChannelConfig(
            sensor_id="ezo_ph", centre=6.0, span=1.0,
            dac_positive="A", dac_negative="B",
        )
    )
    ec: MeterChannelConfig = field(
        default_factory=lambda: MeterChannelConfig(
            sensor_id="ezo_ec", centre=1.0, span=1.0, scale=0.001,
            dac_positive="C", dac_negative="D",
        )
    )


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
    """Outbound alert delivery.

    format="raw" POSTs the event as JSON, for a generic receiver.
    format="ntfy" POSTs a human-readable line to an ntfy topic URL
    (https://ntfy.sh/<topic>), with title and priority as headers, so
    alerts arrive as a legible push notification on a phone.
    """

    enabled: bool = False
    url: str = ""
    timeout_seconds: float = 10.0
    format: str = "raw"


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
    """Outbound alerting.

    muted_sensors suppresses *delivery* for the named sensor ids while
    still recording the alert, so a bench rig whose probes sit in a mug
    does not train you to ignore your own notifications. The dashboard
    and system_events still show the out-of-range state.
    """

    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    cooldown_seconds: int = 300
    muted_sensors: tuple[str, ...] = ()


@dataclass(frozen=True)
class SecurityConfig:
    """Stage 1 security baseline for the public dashboard.

    Auth, rate limits, and request logging knobs. The admin password is
    stored as a hex sha256 of the plaintext (never the plaintext itself).
    Empty admin_password_sha256 disables auth and emits a WARN at startup
    (useful for local dev only).
    """

    enabled: bool = True
    admin_password_sha256: str = ""
    session_secret_key: str = ""
    session_max_age_seconds: int = 86400 * 7  # 1 week
    rate_limit_default: str = "60/minute"
    rate_limit_admin: str = "10/minute"
    log_requests: bool = True
    log_user_agents: bool = True

    def __repr__(self) -> str:
        masked_pw = "***" if self.admin_password_sha256 else ""
        masked_sk = "***" if self.session_secret_key else ""
        return (
            f"SecurityConfig(enabled={self.enabled!r}, "
            f"admin_password_sha256={masked_pw!r}, "
            f"session_secret_key={masked_sk!r}, "
            f"session_max_age_seconds={self.session_max_age_seconds!r}, "
            f"rate_limit_default={self.rate_limit_default!r}, "
            f"rate_limit_admin={self.rate_limit_admin!r}, "
            f"log_requests={self.log_requests!r}, "
            f"log_user_agents={self.log_user_agents!r})"
        )


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
    meters: MetersConfig = field(default_factory=MetersConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
