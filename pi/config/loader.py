"""Load and validate TOML configuration into frozen dataclasses.

Returns an immutable AppConfig. Falls back to defaults for any
missing section or key.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from dataclasses import replace
from typing import Any

from pi.config.schema import (
    FIXTURE_ABOVE_MEDIA_MAX_IN,
    FIXTURE_ABOVE_MEDIA_MIN_IN,
    MeterChannelConfig,
    MetersConfig,
    AppConfig,
    CameraConfig,
    ControlConfig,
    DisplayConfig,
    FanConfig,
    I2CConfig,
    IrrigationConfig,
    IrrigationScheduleEntry,
    LightingConfig,
    NotificationConfig,
    ReservoirConfig,
    SensorEntry,
    SensorsConfig,
    SerialConfig,
    SecurityConfig,
    SystemConfig,
    WebhookConfig,
)

logger = logging.getLogger(__name__)

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


WEBHOOK_FORMATS = ("raw", "ntfy")


def _webhook_format(value: Any) -> str:
    """Validate notifications.webhook.format at the config boundary."""
    if value not in WEBHOOK_FORMATS:
        raise ValueError(
            f"notifications.webhook.format must be one of "
            f"{', '.join(WEBHOOK_FORMATS)}, got {value!r}"
        )
    return value


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
        interval_seconds=data.get("interval_seconds", 120),
        enabled=data.get("enabled", True),
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


def _build_meter_channel(data: dict[str, Any], default: MeterChannelConfig) -> MeterChannelConfig:
    cal_raw = data.get("calibration", None)
    calibration = default.calibration
    if cal_raw:
        calibration = tuple((float(p[0]), float(p[1])) for p in cal_raw)
    return MeterChannelConfig(
        sensor_id=data.get("sensor_id", default.sensor_id),
        centre=data.get("centre", default.centre),
        span=data.get("span", default.span),
        scale=data.get("scale", default.scale),
        dac_positive=data.get("dac_positive", default.dac_positive),
        dac_negative=data.get("dac_negative", default.dac_negative),
        midpoint_code=data.get("midpoint_code", default.midpoint_code),
        span_counts=data.get("span_counts", default.span_counts),
        invert=data.get("invert", default.invert),
        calibration=calibration,
    )


def _build_reservoir(raw: dict[str, Any]) -> ReservoirConfig:
    data = raw.get("reservoir", {})
    d = ReservoirConfig()
    src = data.get("source_water_ec_us", d.source_water_ec_us)
    return ReservoirConfig(
        ph_target=data.get("ph_target", d.ph_target),
        ph_warning_low=data.get("ph_warning_low", d.ph_warning_low),
        ph_warning_high=data.get("ph_warning_high", d.ph_warning_high),
        ph_critical_low=data.get("ph_critical_low", d.ph_critical_low),
        ph_critical_high=data.get("ph_critical_high", d.ph_critical_high),
        ec_target_us=data.get("ec_target_us", d.ec_target_us),
        ec_warning_low_us=data.get("ec_warning_low_us", d.ec_warning_low_us),
        ec_warning_high_us=data.get("ec_warning_high_us", d.ec_warning_high_us),
        ec_critical_low_us=data.get("ec_critical_low_us", d.ec_critical_low_us),
        ec_critical_high_us=data.get("ec_critical_high_us", d.ec_critical_high_us),
        source_water_ec_us=None if src is None else float(src),
    )


def _build_meters(raw: dict[str, Any], reservoir: ReservoirConfig) -> MetersConfig:
    data = raw.get("meters", {})
    defaults = MetersConfig()
    # Centre is the target, so it is derived rather than restated. A file that
    # sets `centre` explicitly still wins -- the dial can be deliberately
    # off-target -- but nothing has to remember to keep two numbers in step.
    ph_default = replace(defaults.ph, centre=reservoir.ph_target)
    ec_default = replace(
        defaults.ec, centre=reservoir.ec_target_us * defaults.ec.scale
    )
    return MetersConfig(
        enabled=data.get("enabled", defaults.enabled),
        i2c_address=data.get("i2c_address", defaults.i2c_address),
        update_hz=data.get("update_hz", defaults.update_hz),
        time_constant_seconds=data.get(
            "time_constant_seconds", defaults.time_constant_seconds
        ),
        sample_interval_seconds=data.get(
            "sample_interval_seconds", defaults.sample_interval_seconds
        ),
        fault_timeout_seconds=data.get(
            "fault_timeout_seconds", defaults.fault_timeout_seconds
        ),
        ph=_build_meter_channel(data.get("ph", {}), ph_default),
        ec=_build_meter_channel(data.get("ec", {}), ec_default),
    )


def _build_control(raw: dict[str, Any]) -> ControlConfig:
    data = raw.get("control", {})
    defaults = ControlConfig()
    return ControlConfig(
        enabled=data.get("enabled", defaults.enabled),
        poll_interval_seconds=data.get(
            "poll_interval_seconds", defaults.poll_interval_seconds
        ),
        override_ttl_seconds=data.get(
            "override_ttl_seconds", defaults.override_ttl_seconds
        ),
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

    muted = data.get("muted_sensors", ())
    if isinstance(muted, str):
        raise ValueError(
            f"notifications.muted_sensors must be a list of sensor ids, got {muted!r}"
        )

    return NotificationConfig(
        muted_sensors=tuple(muted),
        webhook=WebhookConfig(
            enabled=wh.get("enabled", False),
            url=wh.get("url", ""),
            timeout_seconds=wh.get("timeout_seconds", 10.0),
            format=_webhook_format(wh.get("format", "raw")),
        ),
        cooldown_seconds=data.get("cooldown_seconds", 300),
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
    if lc.fixture_above_media_in is not None:
        if not (
            FIXTURE_ABOVE_MEDIA_MIN_IN
            <= lc.fixture_above_media_in
            <= FIXTURE_ABOVE_MEDIA_MAX_IN
        ):
            raise ValueError(
                "lighting.fixture_above_media_in must be between "
                f"{FIXTURE_ABOVE_MEDIA_MIN_IN} and {FIXTURE_ABOVE_MEDIA_MAX_IN} in, "
                f"got {lc.fixture_above_media_in}"
            )

    rc = config.reservoir
    for name, low, high in (
        ("ph warning", rc.ph_warning_low, rc.ph_warning_high),
        ("ph critical", rc.ph_critical_low, rc.ph_critical_high),
        ("ec warning", rc.ec_warning_low_us, rc.ec_warning_high_us),
        ("ec critical", rc.ec_critical_low_us, rc.ec_critical_high_us),
    ):
        if low >= high:
            raise ValueError(f"reservoir.{name} band is inverted: {low} >= {high}")
    if not (rc.ph_critical_low <= rc.ph_warning_low
            <= rc.ph_target <= rc.ph_warning_high <= rc.ph_critical_high):
        raise ValueError(
            "reservoir pH bands must nest around the target: "
            f"{rc.ph_critical_low} <= {rc.ph_warning_low} <= {rc.ph_target} "
            f"<= {rc.ph_warning_high} <= {rc.ph_critical_high}"
        )
    if not (rc.ec_critical_low_us <= rc.ec_warning_low_us <= rc.ec_target_us
            <= rc.ec_warning_high_us <= rc.ec_critical_high_us):
        raise ValueError(
            "reservoir EC bands must nest around the target: "
            f"{rc.ec_critical_low_us} <= {rc.ec_warning_low_us} <= {rc.ec_target_us} "
            f"<= {rc.ec_warning_high_us} <= {rc.ec_critical_high_us}"
        )
    # Nutrient salts only ever ADD conductivity. A target at or below the water
    # going in is unreachable however much you dose, and this is the check the
    # project spent months not making: it recorded a 1,529 uS/cm plain-water
    # baseline against an 800-1,200 target in prose, in a different document,
    # and carried on.
    if rc.source_water_ec_us is not None:
        if rc.source_water_ec_us >= rc.ec_target_us:
            raise ValueError(
                f"reservoir.source_water_ec_us ({rc.source_water_ec_us} uS/cm) is at or "
                f"above reservoir.ec_target_us ({rc.ec_target_us} uS/cm). Adding "
                "nutrient can only raise EC, so this target cannot be reached from "
                "this water. Use RO/distilled makeup water, or raise the target."
            )
        if rc.source_water_ec_us >= rc.ec_warning_low_us:
            raise ValueError(
                f"reservoir.source_water_ec_us ({rc.source_water_ec_us} uS/cm) is at or "
                f"above reservoir.ec_warning_low_us ({rc.ec_warning_low_us} uS/cm), so a "
                "freshly filled reservoir starts inside the warning band before any "
                "nutrient is added."
            )

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


def _build_security(raw: dict[str, Any]) -> SecurityConfig:
    """Build SecurityConfig from raw TOML, with env-var overrides for secrets."""
    data = raw.get("security", {})
    defaults = SecurityConfig()
    pw_hash = (
        os.environ.get("GROWLAB_ADMIN_PASSWORD_SHA256")
        or data.get("admin_password_sha256", defaults.admin_password_sha256)
    )
    secret_key = (
        os.environ.get("GROWLAB_SESSION_SECRET_KEY")
        or data.get("session_secret_key", defaults.session_secret_key)
    )
    return SecurityConfig(
        enabled=data.get("enabled", defaults.enabled),
        admin_password_sha256=pw_hash,
        session_secret_key=secret_key,
        session_max_age_seconds=data.get("session_max_age_seconds", defaults.session_max_age_seconds),
        rate_limit_default=data.get("rate_limit_default", defaults.rate_limit_default),
        log_requests=data.get("log_requests", defaults.log_requests),
        log_user_agents=data.get("log_user_agents", defaults.log_user_agents),
    )


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

    reservoir = _build_reservoir(raw)

    config = AppConfig(
        system=_build_system(raw),
        i2c=I2CConfig(bus=i2c_data.get("bus", 1)),
        serial=SerialConfig(
            port=serial_data.get("port", "/dev/ttyACM0"),
            baud=serial_data.get("baud", 115200),
            timeout=serial_data.get("timeout", 2.0),
        ),
        sensors=_build_sensors(raw),
        camera=_build_camera(raw),
        lighting=LightingConfig(
            on_hour=lighting_data.get("on_hour", 6),
            off_hour=lighting_data.get("off_hour", 22),
            intensity=lighting_data.get("intensity", 200),
            ramp_minutes=lighting_data.get("ramp_minutes", 15),
            fixture_above_media_in=lighting_data.get("fixture_above_media_in"),
        ),
        reservoir=reservoir,
        irrigation=_build_irrigation(raw),
        fan=FanConfig(
            enabled=fan_data.get("enabled", False),
            gpio_pin=fan_data.get("gpio_pin", 18),
            frequency=fan_data.get("frequency", 25000),
            min_duty=fan_data.get("min_duty", 20),
            max_duty=fan_data.get("max_duty", 100),
            day_start_hour=fan_data.get("day_start_hour", 6),
            day_end_hour=fan_data.get("day_end_hour", 22),
            night_factor=fan_data.get("night_factor", 0.35),
            calm_threshold=fan_data.get("calm_threshold", 0.40),
            poll_interval_seconds=fan_data.get("poll_interval_seconds", 5),
        ),
        meters=_build_meters(raw, reservoir),
        control=_build_control(raw),
        display=DisplayConfig(
            enabled=display_data.get("enabled", False),
            address=display_data.get("address", 0x3C),
            controller=display_data.get("controller", "sh1106"),
        ),
        notifications=_build_notifications(raw),
        security=_build_security(raw),
    )

    _validate_config(config)
    return config
