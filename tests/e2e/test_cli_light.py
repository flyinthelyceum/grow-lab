"""E2E tests for light CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from pi.cli.main import cli


def _make_config(tmp_path):
    """Create a minimal config file pointing to tmp_path."""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"

[lighting]
mode = "veg"
on_hour = 6
off_hour = 22
intensity = 200
ramp_minutes = 30
"""
    )
    return str(config_path)


class TestLightSchedule:
    def test_shows_schedule_info(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)
        result = runner.invoke(cli, ["--config", config, "light", "schedule"])
        assert result.exit_code == 0
        assert "Mode:" in result.output
        assert "veg" in result.output
        assert "On hour:" in result.output
        assert "Off hour:" in result.output
        assert "Intensity:" in result.output
        assert "Ramp:" in result.output
        assert "Current:" in result.output


class TestLightSet:
    def test_set_no_esp32_connection(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_esp = MagicMock()
        mock_esp.connect.return_value = False

        with patch("pi.drivers.esp32_serial.ESP32Serial", return_value=mock_esp):
            result = runner.invoke(cli, ["--config", config, "light", "set", "128"])

        assert "Could not connect" in result.output

    def test_set_success(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_esp = MagicMock()
        mock_esp.connect.return_value = True
        mock_esp.set_light.return_value = MagicMock(ok=True, data={"pwm": 128})

        mock_repo = MagicMock()
        mock_repo.connect = MagicMock(return_value=_async_none())
        mock_repo.close = MagicMock(return_value=_async_none())
        mock_repo.save_event = MagicMock(return_value=_async_none())

        with patch("pi.drivers.esp32_serial.ESP32Serial", return_value=mock_esp):
            with patch("pi.data.repository.SensorRepository", return_value=mock_repo):
                result = runner.invoke(
                    cli, ["--config", config, "light", "set", "128"]
                )

        assert result.exit_code == 0
        assert "128" in result.output


class TestLightStatus:
    def test_status_no_esp32(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_esp = MagicMock()
        mock_esp.connect.return_value = False

        with patch("pi.drivers.esp32_serial.ESP32Serial", return_value=mock_esp):
            result = runner.invoke(cli, ["--config", config, "light", "status"])

        assert "Could not connect" in result.output

    def test_status_success(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_esp = MagicMock()
        mock_esp.connect.return_value = True
        mock_esp.get_status.return_value = MagicMock(
            ok=True, data={"pwm": 200, "pump": False, "uptime": 3600}
        )

        with patch("pi.drivers.esp32_serial.ESP32Serial", return_value=mock_esp):
            result = runner.invoke(cli, ["--config", config, "light", "status"])

        assert result.exit_code == 0
        assert "PWM:" in result.output
        assert "200" in result.output
        assert "Pump:" in result.output
        assert "Uptime:" in result.output

    def test_status_error_response(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_esp = MagicMock()
        mock_esp.connect.return_value = True
        mock_esp.get_status.return_value = MagicMock(ok=False, error="timeout")

        with patch("pi.drivers.esp32_serial.ESP32Serial", return_value=mock_esp):
            result = runner.invoke(cli, ["--config", config, "light", "status"])

        assert "Error:" in result.output


async def _async_none():
    return None
