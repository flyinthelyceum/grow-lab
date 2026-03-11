"""E2E tests for CLI commands."""

from click.testing import CliRunner

from pi.cli.main import cli


class TestDbCommands:
    def test_db_init(self, tmp_path):
        runner = CliRunner()
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"
"""
        )
        result = runner.invoke(cli, ["--config", str(config_path), "db", "init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower()

    def test_db_info_empty(self, tmp_path):
        runner = CliRunner()
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"
"""
        )
        result = runner.invoke(cli, ["--config", str(config_path), "db", "info"])
        assert result.exit_code == 0
        assert "sensor_readings: 0 rows" in result.output

    def test_db_export_csv_empty(self, tmp_path):
        runner = CliRunner()
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"
"""
        )
        # Init first
        runner.invoke(cli, ["--config", str(config_path), "db", "init"])
        result = runner.invoke(
            cli, ["--config", str(config_path), "db", "export", "--format", "csv"]
        )
        assert result.exit_code == 0
        assert "timestamp,sensor_id" in result.output

    def test_db_export_json_empty(self, tmp_path):
        runner = CliRunner()
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"
"""
        )
        runner.invoke(cli, ["--config", str(config_path), "db", "init"])
        result = runner.invoke(
            cli, ["--config", str(config_path), "db", "export", "--format", "json"]
        )
        assert result.exit_code == 0
        assert "[]" in result.output

    def test_db_export_to_file(self, tmp_path):
        runner = CliRunner()
        config_path = tmp_path / "config.toml"
        output_path = tmp_path / "export.csv"
        config_path.write_text(
            f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"
"""
        )
        runner.invoke(cli, ["--config", str(config_path), "db", "init"])
        result = runner.invoke(
            cli,
            [
                "--config", str(config_path),
                "db", "export",
                "--output", str(output_path),
            ],
        )
        assert result.exit_code == 0
        assert output_path.exists()
        assert "Exported to" in result.output

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Living Light System" in result.output
