"""E2E tests for camera CLI commands."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from pi.cli.main import cli
from pi.data.models import CameraCapture


def _make_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[system]
data_dir = "{tmp_path}"
db_path = "{tmp_path / 'test.db'}"

[camera]
enabled = true
interval_seconds = 300
resolution = [1920, 1080]
output_dir = "{tmp_path / 'captures'}"
"""
    )
    return str(config_path)


async def _async_none():
    return None


class TestCameraCaptureCmd:
    def test_capture_no_camera(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_cam = MagicMock()
        mock_cam.is_available = False

        with patch("pi.drivers.camera.CameraDriver", return_value=mock_cam):
            result = runner.invoke(cli, ["--config", config, "camera", "capture"])

        assert "No camera detected" in result.output

    def test_capture_success(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        capture_result = CameraCapture(
            timestamp=datetime.now(timezone.utc),
            filepath=str(tmp_path / "captures" / "test.jpg"),
            filesize_bytes=12345,
        )

        mock_cam = MagicMock()
        mock_cam.is_available = True

        mock_svc = MagicMock()

        async def _capture():
            return capture_result

        mock_svc.capture_now = _capture

        mock_repo = MagicMock()
        mock_repo.connect = MagicMock(return_value=_async_none())
        mock_repo.close = MagicMock(return_value=_async_none())

        with patch("pi.drivers.camera.CameraDriver", return_value=mock_cam):
            with patch("pi.services.camera_capture.CameraCaptureService", return_value=mock_svc):
                with patch("pi.data.repository.SensorRepository", return_value=mock_repo):
                    result = runner.invoke(
                        cli, ["--config", config, "camera", "capture"]
                    )

        assert result.exit_code == 0
        assert "Captured:" in result.output
        assert "12,345 bytes" in result.output

    def test_capture_fails(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_cam = MagicMock()
        mock_cam.is_available = True

        mock_svc = MagicMock()

        async def _capture():
            return None

        mock_svc.capture_now = _capture

        mock_repo = MagicMock()
        mock_repo.connect = MagicMock(return_value=_async_none())
        mock_repo.close = MagicMock(return_value=_async_none())

        with patch("pi.drivers.camera.CameraDriver", return_value=mock_cam):
            with patch("pi.services.camera_capture.CameraCaptureService", return_value=mock_svc):
                with patch("pi.data.repository.SensorRepository", return_value=mock_repo):
                    result = runner.invoke(
                        cli, ["--config", config, "camera", "capture"]
                    )

        assert "Capture failed" in result.output


class TestCameraList:
    def test_list_empty(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        # Init db first so real repo works
        runner.invoke(cli, ["--config", config, "db", "init"])
        result = runner.invoke(cli, ["--config", config, "camera", "list"])

        assert result.exit_code == 0
        assert "No captures found" in result.output

    def test_list_with_captures(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        captures = [
            CameraCapture(
                timestamp=datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc),
                filepath="/data/captures/img_001.jpg",
                filesize_bytes=54321,
            ),
        ]

        mock_repo = MagicMock()
        mock_repo.connect = MagicMock(return_value=_async_none())
        mock_repo.close = MagicMock(return_value=_async_none())

        async def _get_captures(limit=10):
            return captures

        mock_repo.get_captures = _get_captures

        with patch("pi.data.repository.SensorRepository", return_value=mock_repo):
            result = runner.invoke(cli, ["--config", config, "camera", "list"])

        assert result.exit_code == 0
        assert "Recent captures" in result.output
        assert "img_001.jpg" in result.output
        assert "54,321B" in result.output


class TestCameraStatus:
    def test_shows_config_and_availability(self, tmp_path):
        runner = CliRunner()
        config = _make_config(tmp_path)

        mock_cam = MagicMock()
        mock_cam.is_available = False

        with patch("pi.drivers.camera.CameraDriver", return_value=mock_cam):
            result = runner.invoke(cli, ["--config", config, "camera", "status"])

        assert result.exit_code == 0
        assert "Enabled:" in result.output
        assert "Interval:" in result.output
        assert "Resolution:" in result.output
        assert "Available:" in result.output
