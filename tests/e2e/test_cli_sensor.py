"""E2E tests for sensor CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from pi.cli.main import cli
from pi.discovery.scanner import ScanResult


def _make_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"
"""
    )
    return str(config_path)


def _empty_scan():
    return ScanResult(
        i2c_devices=(),
        onewire_devices=(),
        serial_devices=(),
    )


class TestSensorScan:
    def test_scan_no_hardware(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_registry = MagicMock()
        mock_registry.all_statuses = []
        mock_registry.available_drivers = {}

        with patch("pi.discovery.scanner.scan_all", return_value=_empty_scan()):
            with patch("pi.discovery.registry.build_registry", return_value=mock_registry):
                result = runner.invoke(
                    cli, ["--config", config, "sensor", "scan"]
                )

        assert result.exit_code == 0
        assert "Scanning" in result.output
        assert "no devices found" in result.output
        assert "0/0 sensors available" in result.output

    def test_scan_with_i2c_device(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        i2c_dev = MagicMock()
        i2c_dev.address = 0x76
        scan = ScanResult(
            i2c_devices=(i2c_dev,),
            onewire_devices=(),
            serial_devices=(),
        )

        status = MagicMock()
        status.sensor_id = "bme280"
        status.available = True
        status.reason = "detected at 0x76"

        mock_registry = MagicMock()
        mock_registry.all_statuses = [status]
        mock_registry.available_drivers = {"bme280": MagicMock()}

        with patch("pi.discovery.scanner.scan_all", return_value=scan):
            with patch("pi.discovery.registry.build_registry", return_value=mock_registry):
                result = runner.invoke(
                    cli, ["--config", config, "sensor", "scan"]
                )

        assert result.exit_code == 0
        assert "0x76" in result.output
        assert "1/1 sensors available" in result.output


class TestSensorStatus:
    def test_status_no_hardware(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_registry = MagicMock()
        mock_registry.all_statuses = []

        with patch("pi.discovery.scanner.scan_all", return_value=_empty_scan()):
            with patch("pi.discovery.registry.build_registry", return_value=mock_registry):
                result = runner.invoke(
                    cli, ["--config", config, "sensor", "status"]
                )

        assert result.exit_code == 0

    def test_status_with_sensors(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        status_ok = MagicMock()
        status_ok.sensor_id = "bme280"
        status_ok.available = True
        status_ok.reason = "OK"

        status_missing = MagicMock()
        status_missing.sensor_id = "ezo_ph"
        status_missing.available = False
        status_missing.reason = "not detected"

        mock_registry = MagicMock()
        mock_registry.all_statuses = [status_ok, status_missing]

        with patch("pi.discovery.scanner.scan_all", return_value=_empty_scan()):
            with patch("pi.discovery.registry.build_registry", return_value=mock_registry):
                result = runner.invoke(
                    cli, ["--config", config, "sensor", "status"]
                )

        assert "[OK]" in result.output
        assert "[--]" in result.output
        assert "bme280" in result.output
        assert "ezo_ph" in result.output


class TestSensorRead:
    def test_read_unknown_sensor(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_registry = MagicMock()
        mock_registry.get_driver.return_value = None
        mock_registry.all_statuses = []
        mock_registry.available_drivers = {}

        with patch("pi.discovery.scanner.scan_all", return_value=_empty_scan()):
            with patch("pi.discovery.registry.build_registry", return_value=mock_registry):
                result = runner.invoke(
                    cli, ["--config", config, "sensor", "read", "nonexistent"]
                )

        assert result.exit_code == 0
        assert "Unknown sensor" in result.output

    def test_read_unavailable_sensor(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        status = MagicMock()
        status.sensor_id = "bme280"
        status.available = False
        status.reason = "not detected on I2C bus"

        mock_registry = MagicMock()
        mock_registry.get_driver.return_value = None
        mock_registry.all_statuses = [status]
        mock_registry.available_drivers = {}

        with patch("pi.discovery.scanner.scan_all", return_value=_empty_scan()):
            with patch("pi.discovery.registry.build_registry", return_value=mock_registry):
                result = runner.invoke(
                    cli, ["--config", config, "sensor", "read", "bme280"]
                )

        assert "not available" in result.output

    def test_read_success(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        from datetime import datetime, timezone

        from pi.data.models import SensorReading

        readings = [
            SensorReading(
                timestamp=datetime.now(timezone.utc),
                sensor_id="bme280_temperature",
                value=23.5,
                unit="°C",
            ),
            SensorReading(
                timestamp=datetime.now(timezone.utc),
                sensor_id="bme280_humidity",
                value=55.2,
                unit="%",
            ),
        ]

        mock_driver = MagicMock()

        async def _read():
            return readings

        mock_driver.read = _read

        mock_registry = MagicMock()
        mock_registry.get_driver.return_value = mock_driver

        with patch("pi.discovery.scanner.scan_all", return_value=_empty_scan()):
            with patch("pi.discovery.registry.build_registry", return_value=mock_registry):
                result = runner.invoke(
                    cli, ["--config", config, "sensor", "read", "bme280"]
                )

        assert result.exit_code == 0
        assert "23.50" in result.output
        assert "55.20" in result.output

    def test_read_empty_result(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_driver = MagicMock()

        async def _read():
            return []

        mock_driver.read = _read

        mock_registry = MagicMock()
        mock_registry.get_driver.return_value = mock_driver

        with patch("pi.discovery.scanner.scan_all", return_value=_empty_scan()):
            with patch("pi.discovery.registry.build_registry", return_value=mock_registry):
                result = runner.invoke(
                    cli, ["--config", config, "sensor", "read", "bme280"]
                )

        assert "No readings" in result.output or "empty" in result.output
