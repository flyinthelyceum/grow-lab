"""E2E tests for fan CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from pi.cli.main import cli


def _make_config(tmp_path, extra: str = "") -> str:
    """Create a minimal config file pointing to tmp_path."""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"

[fan]
enabled = true
gpio_pin = 18
frequency = 25000
min_duty = 20
max_duty = 100
{extra}
"""
    )
    return str(config_path)


class TestFanStatus:
    def test_shows_gust_config_and_current_duty(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)
        result = runner.invoke(cli, ["--config", config, "fan", "status"])
        assert result.exit_code == 0
        assert "Enabled:" in result.output
        assert "GPIO:      18 @ 25000 Hz" in result.output
        assert "Duty span: 20-100%" in result.output
        assert "Gusts:     06:00-22:00" in result.output
        assert "Right now:" in result.output

    def test_needs_no_sensor_reading(self, tmp_path):
        """It used to require a bme280 reading to say anything useful."""
        runner = CliRunner()
        config = _make_config(tmp_path)
        result = runner.invoke(cli, ["--config", config, "fan", "status"])
        assert result.exit_code == 0
        assert "cannot compute" not in result.output
        assert "Air temp" not in result.output

class TestFanSet:
    def test_reports_gpio_unavailable(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        driver = MagicMock()
        driver.is_available = False

        with patch("pi.drivers.fan_pwm.FanPWMDriver", return_value=driver):
            result = runner.invoke(cli, ["--config", config, "fan", "set", "50"])

        assert result.exit_code == 1
        assert "GPIO PWM unavailable" in result.output

    def test_sets_duty(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        driver = MagicMock()
        driver.is_available = True
        driver.set_duty.return_value = True
        driver.duty_cycle = 50

        with patch("pi.drivers.fan_pwm.FanPWMDriver", return_value=driver):
            result = runner.invoke(cli, ["--config", config, "fan", "set", "50"])

        assert result.exit_code == 0
        assert "Fan duty set to 50%" in result.output
        driver.set_duty.assert_called_once_with(50)

    def test_reports_clamped_duty(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        driver = MagicMock()
        driver.is_available = True
        driver.set_duty.return_value = True
        driver.duty_cycle = 20  # clamped up from 5 by min_duty

        with patch("pi.drivers.fan_pwm.FanPWMDriver", return_value=driver):
            result = runner.invoke(cli, ["--config", config, "fan", "set", "5"])

        assert result.exit_code == 0
        assert "clamped" in result.output

    def test_rejects_out_of_range(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)
        result = runner.invoke(cli, ["--config", config, "fan", "set", "150"])
        assert result.exit_code != 0


class TestFanSweep:
    def test_reports_gpio_unavailable(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        driver = MagicMock()
        driver.is_available = False

        with patch("pi.drivers.fan_pwm.FanPWMDriver", return_value=driver):
            result = runner.invoke(cli, ["--config", config, "fan", "sweep"])

        assert result.exit_code == 1
        assert "GPIO PWM unavailable" in result.output

    def test_steps_through_range_and_shuts_off(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        driver = MagicMock()
        driver.is_available = True
        driver.set_duty.return_value = True
        driver.duty_cycle = 0

        with patch("pi.drivers.fan_pwm.FanPWMDriver", return_value=driver):
            result = runner.invoke(
                cli, ["--config", config, "fan", "sweep", "--dwell", "0.5"]
            )

        assert result.exit_code == 0
        duties = [c.args[0] for c in driver.set_duty.call_args_list]
        assert duties[:6] == [0, 20, 40, 60, 80, 100]
        # Always returns to 0 and releases the pin.
        assert duties[-1] == 0
        driver.close.assert_called_once()
        assert "Sweep complete" in result.output


async def _noop():
    return None
