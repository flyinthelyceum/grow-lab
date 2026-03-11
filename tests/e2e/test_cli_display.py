"""E2E tests for display CLI commands."""

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

[display]
enabled = true
address = 60
"""
    )
    return str(config_path)


class TestDisplayStatus:
    def test_shows_config(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_oled = MagicMock()
        mock_oled.is_available = False

        with patch("pi.drivers.oled_ssd1306.OLEDDriver", return_value=mock_oled):
            result = runner.invoke(cli, ["--config", config, "display", "status"])

        assert result.exit_code == 0
        assert "Enabled:" in result.output
        assert "Address:" in result.output
        assert "Available:" in result.output


class TestDisplayTest:
    def test_no_hardware(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_oled = MagicMock()
        mock_oled.is_available = False

        with patch("pi.drivers.oled_ssd1306.OLEDDriver", return_value=mock_oled):
            result = runner.invoke(cli, ["--config", config, "display", "test"])

        assert "not detected" in result.output

    def test_with_hardware(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_oled = MagicMock()
        mock_oled.is_available = True

        with patch("pi.drivers.oled_ssd1306.OLEDDriver", return_value=mock_oled):
            result = runner.invoke(cli, ["--config", config, "display", "test"])

        assert result.exit_code == 0
        assert "Test pattern displayed" in result.output
        mock_oled.clear.assert_called()
        mock_oled.show.assert_called()


class TestDisplayClear:
    def test_clears_display(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_oled = MagicMock()

        with patch("pi.drivers.oled_ssd1306.OLEDDriver", return_value=mock_oled):
            result = runner.invoke(cli, ["--config", config, "display", "clear"])

        assert result.exit_code == 0
        assert "cleared" in result.output.lower()
        mock_oled.clear.assert_called()
        mock_oled.show.assert_called()
