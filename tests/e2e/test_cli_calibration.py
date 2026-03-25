"""E2E tests for calibration CLI commands."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from pi.cli.main import cli
from pi.data.models import SensorReading


def _config_text(tmp_path: Path) -> str:
    return f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"

[installation]
node_id = "growlab-v0"
fixture_id = "fixture-a"
fixture_model = "LM301H strip"
sensor_board_id = "board-01"

[sensors.as7341]
enabled = true
address = 0x39
"""


class TestCalibrationCli:
    def test_init_session(self, tmp_path: Path):
        runner = CliRunner()
        config_path = tmp_path / "config.toml"
        config_path.write_text(_config_text(tmp_path))
        session_path = tmp_path / "session.csv"

        result = runner.invoke(
            cli,
            ["--config", str(config_path), "calibration", "as7341", "init-session", "--output", str(session_path)],
        )

        assert result.exit_code == 0
        assert session_path.exists()
        assert "timestamp,node_id" in session_path.read_text()

    def test_capture_row(self, tmp_path: Path):
        runner = CliRunner()
        config_path = tmp_path / "config.toml"
        config_path.write_text(_config_text(tmp_path))
        session_path = tmp_path / "session.csv"

        mock_driver = AsyncMock()
        mock_driver.sensor_id = "as7341"
        mock_driver._gain = 7
        mock_driver._atime = 29
        mock_driver._astep = 599
        mock_driver.read.return_value = [
            SensorReading(timestamp=datetime.now(timezone.utc), sensor_id="as7341_lux", value=100.0, unit="lux"),
            *[
                SensorReading(timestamp=datetime.now(timezone.utc), sensor_id=name, value=10.0 + idx, unit="raw")
                for idx, name in enumerate([
                    "as7341_415nm",
                    "as7341_445nm",
                    "as7341_480nm",
                    "as7341_515nm",
                    "as7341_555nm",
                    "as7341_590nm",
                    "as7341_630nm",
                    "as7341_680nm",
                    "as7341_clear",
                    "as7341_nir",
                ])
            ],
        ]

        mock_registry = MagicMock()
        mock_registry.get_driver.return_value = mock_driver

        with patch("pi.cli.calibration_cmd.scan_all") as mock_scan, patch(
            "pi.cli.calibration_cmd.build_registry", return_value=mock_registry
        ):
            mock_scan.return_value = MagicMock()
            result = runner.invoke(
                cli,
                [
                    "--config", str(config_path),
                    "calibration", "as7341", "capture",
                    "--session", str(session_path),
                    "--operator", "Tester",
                    "--pwm-percent", "50",
                    "--distance-cm", "35",
                    "--reference-ppfd", "220",
                ],
            )

        assert result.exit_code == 0
        text = session_path.read_text()
        assert "reference_ppfd" in text
        assert "220.0" in text

    def test_fit_and_validate(self, tmp_path: Path):
        runner = CliRunner()
        config_path = tmp_path / "config.toml"
        config_path.write_text(_config_text(tmp_path))
        session_path = tmp_path / "session.csv"
        session_path.write_text(
            "timestamp,node_id,fixture_id,fixture_model,calibration_profile_id,operator,sensor_board_id,gain,integration_time,astep,led_pwm_percent,fixture_distance_cm,lateral_offset_cm,reference_ppfd,split,notes,as7341_415nm,as7341_445nm,as7341_480nm,as7341_515nm,as7341_555nm,as7341_590nm,as7341_630nm,as7341_680nm,as7341_clear,as7341_nir\n"
            "2026-03-24T21:00:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,20,25,0,100,train,,10,20,30,40,50,45,25,15,60,8\n"
            "2026-03-24T21:01:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,35,25,0,160,train,,15,30,45,60,75,68,38,23,90,11\n"
            "2026-03-24T21:02:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,50,25,0,220,train,,20,40,60,80,100,90,50,30,120,14\n"
            "2026-03-24T21:03:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,65,25,0,280,train,,25,50,75,100,125,113,63,38,150,17\n"
            "2026-03-24T21:04:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,80,25,0,340,train,,30,60,90,120,150,135,75,45,180,20\n"
            "2026-03-24T21:05:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,100,25,0,410,train,,35,70,105,140,175,158,88,53,210,24\n"
            "2026-03-24T21:06:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,20,35,0,82,train,,8,16,24,32,40,36,20,12,48,6\n"
            "2026-03-24T21:07:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,35,35,0,126,train,,12,24,36,48,60,54,30,18,72,9\n"
            "2026-03-24T21:08:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,50,35,0,172,train,,16,32,48,64,80,72,40,24,96,12\n"
            "2026-03-24T21:09:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,65,35,0,218,train,,20,40,60,80,100,90,50,30,120,15\n"
            "2026-03-24T21:10:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,80,35,0,266,validate,,24,48,72,96,120,108,60,36,144,18\n"
            "2026-03-24T21:11:00+00:00,growlab-v0,fixture-a,LM301H strip,,Tester,board-01,7,29,599,100,35,0,320,validate,,28,56,84,112,140,126,70,42,168,21\n"
        )
        profile_path = tmp_path / "profile.json"
        report_path = tmp_path / "report.md"

        fit_result = runner.invoke(
            cli,
            [
                "--config", str(config_path),
                "calibration", "as7341", "fit",
                "--session", str(session_path),
                "--profile-out", str(profile_path),
                "--regression", "ridge",
            ],
        )
        validate_result = runner.invoke(
            cli,
            [
                "--config", str(config_path),
                "calibration", "as7341", "validate",
                "--session", str(session_path),
                "--profile", str(profile_path),
                "--report-out", str(report_path),
            ],
        )

        assert fit_result.exit_code == 0
        assert validate_result.exit_code == 0
        assert profile_path.exists()
        assert report_path.exists()
        assert "RMSE" in report_path.read_text()
