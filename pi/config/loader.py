"""Load and validate TOML configuration into frozen dataclasses.

Returns an immutable AppConfig. Falls back to defaults for any
missing section or key.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pi.config.schema import (
    AppConfig,
    CameraConfig,
    CalibrationConfig,
    DisplayConfig,
    EmailConfig,
    FanConfig,
    I2CConfig,
    InstallationConfig,
    IrrigationConfig,
    IrrigationScheduleEntry,
    LightingConfig,
    NotificationConfig,
    SensorEntry,
    SensorsConfig,
    SerialConfig,
    SystemConfig,
    WebhookConfig,
)

logger = logging.getLogger(__name__)

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


def _to_path(value: Any) -> Path:
    """Convert config path values and expand ~ for user-home paths."""
    path = Path(str(value)).expanduser()
    legacy_root = Path("/home/pi/grow-lab-data")
    if Path.home() != Path("/home/pi") and path == legacy_root:
        return Path.home() / "grow-lab-data"
    if Path.home() != Path("/home/pi") and legacy_root in path.parents:
        rel = path.relative_to(legacy_root)
        return Path.home() / "grow-lab-data" / rel
    return path


def _build_system(raw: dict[str, Any]) -> SystemConfig:
    data = raw.get("system", {})
    defaults = SystemConfig()
    return SystemConfig(
        log_level=data.get("log_level", "INFO"),
        data_dir=_to_path(data.get("data_dir", defaults.data_dir)),
        db_path=_to_path(data.get("db_path", defaults.db_path)),
    )


def _build_sensor_entry(data: dict[str, Any]) -> SensorEntry:
    return SensorEntry(
        address=data.get("address", 0),
        gpio=data.get("gpio", 0),
        interval_seconds=data.get("interval_seconds", 120),
        enabled=data.get("enabled", True),
    )


def _build_installation(raw: dict[str, Any]) -> InstallationConfig:
    data = raw.get("installation", {})
    defaults = InstallationConfig()
    return InstallationConfig(
        node_id=data.get("node_id", defaults.node_id),
        fixture_id=data.get("fixture_id", defaults.fixture_id),
        fixture_model=data.get("fixture_model", defaults.fixture_model),
        sensor_board_id=data.get("sensor_board_id", defaults.sensor_board_id),
    )


def _build_sensors(raw: dict[str, Any]) -> SensorsConfig:
    sensors = raw.get("sensors", {})
    defaults = SensorsConfig()
    return SensorsConfig(
        bme280=_build_sensor_entry(sensors.get("bme280", {}))
        if "bme280" in sensors
        else defaults.bme280,
        ezo_ph=_build_sensor_entry(sensors.get("ezo_ph", {}))
        if "ezo_ph" in sensors
        else defaults.ezo_ph,
        ezo_ec=_build_sensor_entry(sensors.get("ezo_ec", {}))
        if "ezo_ec" in sensors
        else defaults.ezo_ec,
        ds18b20=_build_sensor_entry(sensors.get("ds18b20", {}))
        if "ds18b20" in sensors
        else defaults.ds18b20,
        soil_moisture=_build_sensor_entry(sensors.get("soil_moisture", {}))
        if "soil_moisture" in sensors
        else defaults.soil_moisture,
        as7341=_build_sensor_entry(sensors.get("as7341", {}))
        if "as7341" in sensors
        else defaults.as7341,
        soil_moisture_channel=sensors.get("soil_moisture_channel", 0),
    )


def _build_irrigation(raw: dict[str, Any]) -> IrrigationConfig:
    data = raw.get("irrigation", {})
    schedules_raw = data.get("schedules", None)
    if schedules_raw is not None:
        schedules = tuple(
            IrrigationScheduleEntry(
                hour=s.get("hour", 8),
                minute=s.get("minute", 0),
                duration_seconds=s.get("duration_seconds", 10),
            )
            for s in schedules_raw
        )
    else:
        schedules = IrrigationConfig().schedules

    pump_controller = data.get("pump_controller", "gpio")
    if pump_controller not in ("gpio", "esp32"):
        raise ValueError(
            f"irrigation.pump_controller must be 'gpio' or 'esp32', got '{pump_controller}'"
        )

    return IrrigationConfig(
        pump_controller=pump_controller,
        schedules=schedules,
        max_runtime_seconds=data.get("max_runtime_seconds", 30),
        min_interval_minutes=data.get("min_interval_minutes", 60),
        relay_gpio=data.get("relay_gpio", 17),
    )


def _build_camera(raw: dict[str, Any]) -> CameraConfig:
    data = raw.get("camera", {})
    defaults = CameraConfig()
    res = data.get("resolution", [4608, 2592])
    return CameraConfig(
        interval_seconds=data.get("interval_seconds", 600),
        resolution=(res[0], res[1]),
        output_dir=_to_path(data.get("output_dir", defaults.output_dir)),
        enabled=data.get("enabled", True),
    )


def _build_notifications(raw: dict[str, Any]) -> NotificationConfig:
    data = raw.get("notifications", {})
    wh = data.get("webhook", {})
    em = data.get("email", {})

    to_addrs = em.get("to_addresses", ())
    if isinstance(to_addrs, list):
        to_addrs = tuple(to_addrs)

    return NotificationConfig(
        webhook=WebhookConfig(
            enabled=wh.get("enabled", False),
            url=wh.get("url", ""),
            timeout_seconds=wh.get("timeout_seconds", 10.0),
        ),
        email=EmailConfig(
            enabled=em.get("enabled", False),
            smtp_host=em.get("smtp_host", ""),
            smtp_port=em.get("smtp_port", 587),
            smtp_user=em.get("smtp_user", ""),
            smtp_password=em.get("smtp_password", ""),
            use_tls=em.get("use_tls", True),
            from_address=em.get("from_address", ""),
            to_addresses=to_addrs,
        ),
        cooldown_seconds=data.get("cooldown_seconds", 300),
    )


def _build_calibration(raw: dict[str, Any]) -> CalibrationConfig:
    data = raw.get("calibration", {})
    defaults = CalibrationConfig()
    return CalibrationConfig(
        enabled=data.get("enabled", defaults.enabled),
        profile_dir=_to_path(data.get("profile_dir", defaults.profile_dir)),
        active_profile=data.get("active_profile", defaults.active_profile),
    )


def _validate_config(config: AppConfig) -> None:
    """Validate config values are within acceptable ranges."""
    lc = config.lighting
    if not (0 <= lc.on_hour <= 23):
        raise ValueError(f"lighting.on_hour must be 0-23, got {lc.on_hour}")
    if not (0 <= lc.off_hour <= 23):
        raise ValueError(f"lighting.off_hour must be 0-23, got {lc.off_hour}")
    if not (0 <= lc.intensity <= 255):
        raise ValueError(f"lighting.intensity must be 0-255, got {lc.intensity}")
    if lc.ramp_minutes < 0:
        raise ValueError(f"lighting.ramp_minutes must be >= 0, got {lc.ramp_minutes}")

    ic = config.irrigation
    if ic.max_runtime_seconds < 1:
        raise ValueError(f"irrigation.max_runtime_seconds must be >= 1, got {ic.max_runtime_seconds}")
    if ic.min_interval_minutes < 0:
        raise ValueError(f"irrigation.min_interval_minutes must be >= 0, got {ic.min_interval_minutes}")
    for entry in ic.schedules:
        if not (0 <= entry.hour <= 23):
            raise ValueError(f"irrigation schedule hour must be 0-23, got {entry.hour}")
        if not (0 <= entry.minute <= 59):
            raise ValueError(f"irrigation schedule minute must be 0-59, got {entry.minute}")


def load_config(path: Path | None = None) -> AppConfig:
    """Load config from a TOML file. Returns defaults if file not found."""
    if path is None:
        path = Path("config.toml")

    raw: dict[str, Any] = {}
    if path.exists():
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        logger.info("Loaded config from %s", path)
    else:
        logger.warning("Config file %s not found, using defaults", path)

    i2c_data = raw.get("i2c", {})
    serial_data = raw.get("serial", {})
    lighting_data = raw.get("lighting", {})
    fan_data = raw.get("fan", {})
    display_data = raw.get("display", {})

    config = AppConfig(
        system=_build_system(raw),
        i2c=I2CConfig(bus=i2c_data.get("bus", 1)),
        serial=SerialConfig(
            port=serial_data.get("port", "/dev/ttyACM0"),
            baud=serial_data.get("baud", 115200),
            timeout=serial_data.get("timeout", 2.0),
        ),
        installation=_build_installation(raw),
        sensors=_build_sensors(raw),
        camera=_build_camera(raw),
        lighting=LightingConfig(
            mode=lighting_data.get("mode", "veg"),
            on_hour=lighting_data.get("on_hour", 6),
            off_hour=lighting_data.get("off_hour", 22),
            intensity=lighting_data.get("intensity", 200),
            ramp_minutes=lighting_data.get("ramp_minutes", 15),
        ),
        irrigation=_build_irrigation(raw),
        fan=FanConfig(
            enabled=fan_data.get("enabled", False),
            gpio_pin=fan_data.get("gpio_pin", 18),
            frequency=fan_data.get("frequency", 25000),
            min_duty=fan_data.get("min_duty", 20),
            max_duty=fan_data.get("max_duty", 100),
            ramp_temp_low_f=fan_data.get("ramp_temp_low_f", 70.0),
            ramp_temp_high_f=fan_data.get("ramp_temp_high_f", 85.0),
            poll_interval_seconds=fan_data.get("poll_interval_seconds", 30),
        ),
        display=DisplayConfig(
            enabled=display_data.get("enabled", False),
            address=display_data.get("address", 0x3C),
            controller=display_data.get("controller", "sh1106"),
        ),
        calibration=_build_calibration(raw),
        notifications=_build_notifications(raw),
    )

    _validate_config(config)
    return config
