"""Tests for config loading and schema."""

from pathlib import Path

import pytest

from pi.config.loader import load_config
from pi.config.schema import AppConfig, SensorEntry, SensorsConfig


class TestAppConfigDefaults:
    def test_default_config(self):
        config = AppConfig()
        assert config.system.log_level == "INFO"
        assert config.i2c.bus == 1
        assert config.serial.baud == 115200
        assert config.lighting.mode == "veg"

    def test_frozen(self):
        config = AppConfig()
        with pytest.raises(AttributeError):
            config.system = None  # type: ignore[misc]

    def test_sensor_defaults(self):
        config = AppConfig()
        assert config.sensors.bme280.address == 0x76
        assert config.sensors.ezo_ph.address == 0x63
        assert config.sensors.ezo_ec.address == 0x64
        assert config.sensors.ds18b20.gpio == 4
        assert config.sensors.soil_moisture.address == 0x36

    def test_irrigation_defaults(self):
        config = AppConfig()
        assert len(config.irrigation.schedules) == 3
        assert config.irrigation.max_runtime_seconds == 30
        assert config.irrigation.relay_gpio == 17

    def test_default_paths_use_user_home(self):
        config = AppConfig()
        expected_data_dir = Path.home() / "grow-lab-data"
        assert config.system.data_dir == expected_data_dir
        assert config.system.db_path == expected_data_dir / "growlab.db"
        assert config.camera.output_dir == expected_data_dir / "images"


class TestLoadConfig:
    def test_load_missing_file_returns_defaults(self, tmp_path: Path):
        config = load_config(tmp_path / "nonexistent.toml")
        assert isinstance(config, AppConfig)
        assert config.system.log_level == "INFO"

    def test_load_valid_toml(self, tmp_path: Path):
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(
            """
[system]
log_level = "DEBUG"
data_dir = "/tmp/test-data"
db_path = "/tmp/test-data/test.db"

[i2c]
bus = 2

[sensors.bme280]
address = 0x77
interval_seconds = 60
enabled = false
"""
        )
        config = load_config(toml_path)
        assert config.system.log_level == "DEBUG"
        assert config.system.data_dir == Path("/tmp/test-data")
        assert config.i2c.bus == 2
        assert config.sensors.bme280.address == 0x77
        assert config.sensors.bme280.interval_seconds == 60
        assert config.sensors.bme280.enabled is False
        # Other sensors should keep defaults
        assert config.sensors.ezo_ph.address == 0x63

    def test_partial_config_keeps_defaults(self, tmp_path: Path):
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(
            """
[system]
log_level = "WARNING"
"""
        )
        config = load_config(toml_path)
        assert config.system.log_level == "WARNING"
        # Everything else defaults
        assert config.i2c.bus == 1
        assert config.lighting.mode == "veg"

    def test_irrigation_schedules(self, tmp_path: Path):
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(
            """
[[irrigation.schedules]]
hour = 7
minute = 30
duration_seconds = 15

[[irrigation.schedules]]
hour = 19
minute = 0
duration_seconds = 20
"""
        )
        config = load_config(toml_path)
        assert len(config.irrigation.schedules) == 2
        assert config.irrigation.schedules[0].hour == 7
        assert config.irrigation.schedules[0].duration_seconds == 15
        assert config.irrigation.schedules[1].hour == 19

    def test_tilde_paths_are_expanded(self, tmp_path: Path):
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(
            """
[system]
data_dir = "~/grow-lab-data"
db_path = "~/grow-lab-data/growlab.db"

[camera]
output_dir = "~/grow-lab-data/images"
"""
        )
        config = load_config(toml_path)
        expected_data_dir = Path.home() / "grow-lab-data"
        assert config.system.data_dir == expected_data_dir
        assert config.system.db_path == expected_data_dir / "growlab.db"
        assert config.camera.output_dir == expected_data_dir / "images"

    def test_legacy_pi_paths_are_mapped_to_current_home(self, tmp_path: Path):
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(
            """
[system]
data_dir = "/home/pi/grow-lab-data"
db_path = "/home/pi/grow-lab-data/growlab.db"

[camera]
output_dir = "/home/pi/grow-lab-data/images"
"""
        )
        config = load_config(toml_path)
        expected_data_dir = Path.home() / "grow-lab-data"
        assert config.system.data_dir == expected_data_dir
        assert config.system.db_path == expected_data_dir / "growlab.db"
        assert config.camera.output_dir == expected_data_dir / "images"
