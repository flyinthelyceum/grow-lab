"""E2E tests for pump CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from pi.cli.main import cli


def _make_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"

[irrigation]
max_runtime_seconds = 30
min_interval_minutes = 5
relay_gpio = 17
"""
    )
    return str(config_path)


def _mock_gpio_pump(ok: bool = True, error: str | None = None):
    """Create a mock GPIORelayPump for tests."""
    mock = MagicMock()
    mock.set_pump.return_value = MagicMock(ok=ok, error=error)
    return mock


def _patch_get_pump(mock_pump):
    """Patch _get_pump_controller to return a specific mock."""
    return patch("pi.cli.pump_control._get_pump_controller", return_value=mock_pump)


async def _async_none():
    return None


async def _async_true():
    return True


async def _async_false():
    return False


class TestPumpPulse:
    def test_pulse_success(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_pump = _mock_gpio_pump()

        mock_repo = MagicMock()
        mock_repo.connect = MagicMock(return_value=_async_none())
        mock_repo.close = MagicMock(return_value=_async_none())
        mock_repo.save_event = MagicMock(return_value=_async_none())

        mock_svc = MagicMock()
        mock_svc.pulse = MagicMock(return_value=_async_true())

        with _patch_get_pump(mock_pump):
            with patch("pi.data.repository.SensorRepository", return_value=mock_repo):
                with patch("pi.services.irrigation.IrrigationService", return_value=mock_svc):
                    result = runner.invoke(
                        cli, ["--config", config, "pump", "pulse", "10"]
                    )

        assert result.exit_code == 0
        assert "complete" in result.output.lower() or "10s" in result.output

    def test_pulse_blocked_by_cooldown(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_pump = _mock_gpio_pump()

        mock_repo = MagicMock()
        mock_repo.connect = MagicMock(return_value=_async_none())
        mock_repo.close = MagicMock(return_value=_async_none())
        mock_repo.save_event = MagicMock(return_value=_async_none())

        mock_svc = MagicMock()
        mock_svc.pulse = MagicMock(return_value=_async_false())

        with _patch_get_pump(mock_pump):
            with patch("pi.data.repository.SensorRepository", return_value=mock_repo):
                with patch("pi.services.irrigation.IrrigationService", return_value=mock_svc):
                    result = runner.invoke(
                        cli, ["--config", config, "pump", "pulse", "10"]
                    )

        assert "cooldown" in result.output.lower() or "blocked" in result.output.lower()


class TestPumpOnOff:
    def test_pump_on_success(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_pump = _mock_gpio_pump()

        with _patch_get_pump(mock_pump), \
             patch("time.sleep"):
            result = runner.invoke(cli, ["--config", config, "pump", "on", "--max-seconds", "1"])

        assert result.exit_code == 0
        assert "ON" in result.output

    def test_pump_off_success(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_pump = _mock_gpio_pump()

        with _patch_get_pump(mock_pump):
            result = runner.invoke(cli, ["--config", config, "pump", "off"])

        assert result.exit_code == 0
        assert "OFF" in result.output

    def test_pump_on_error(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_pump = _mock_gpio_pump(ok=False, error="relay stuck")

        with _patch_get_pump(mock_pump):
            result = runner.invoke(cli, ["--config", config, "pump", "on", "--max-seconds", "1"])

        assert "Error:" in result.output


class TestPumpSchedule:
    def test_shows_schedule(self, tmp_path):
        runner = CliRunner()
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"

[irrigation]
max_runtime_seconds = 30
min_interval_minutes = 5
relay_gpio = 17

[[irrigation.schedules]]
hour = 8
minute = 0
duration_seconds = 15

[[irrigation.schedules]]
hour = 18
minute = 30
duration_seconds = 10
"""
        )
        result = runner.invoke(
            cli, ["--config", str(config_path), "pump", "schedule"]
        )
        assert result.exit_code == 0
        assert "Max runtime:" in result.output
        assert "30s" in result.output
        assert "Min interval:" in result.output
        assert "Scheduled pulses (2):" in result.output
        assert "08:00" in result.output
        assert "18:30" in result.output
