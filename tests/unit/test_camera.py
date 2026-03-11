"""Tests for the camera driver."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from pi.drivers.camera import CameraDriver


class TestCameraDriverInit:
    def test_defaults(self) -> None:
        cam = CameraDriver()
        assert cam._resolution == (4608, 2592)
        assert cam._picamera2 is None

    def test_custom_resolution(self) -> None:
        cam = CameraDriver(resolution=(1920, 1080))
        assert cam._resolution == (1920, 1080)


class TestCameraAvailability:
    def test_not_available_when_no_camera(self) -> None:
        cam = CameraDriver()
        # Both picamera2 and libcamera-still will fail on Mac
        with patch.object(cam, "_try_init_picamera2", return_value=False):
            with patch.object(cam, "_check_libcamera", return_value=False):
                assert cam.is_available is False

    def test_available_via_picamera2(self) -> None:
        cam = CameraDriver()
        with patch.object(cam, "_try_init_picamera2", return_value=True):
            assert cam.is_available is True

    def test_available_via_libcamera(self) -> None:
        cam = CameraDriver()
        with patch.object(cam, "_try_init_picamera2", return_value=False):
            with patch.object(cam, "_check_libcamera", return_value=True):
                assert cam.is_available is True

    def test_caches_availability(self) -> None:
        cam = CameraDriver()
        cam._available = True
        # Should not re-check
        assert cam.is_available is True


class TestCameraCapture:
    def test_capture_via_picamera2(self, tmp_path: Path) -> None:
        cam = CameraDriver()
        mock_picam = MagicMock()
        cam._picamera2 = mock_picam

        output = tmp_path / "test.jpg"
        result = cam.capture(output)

        assert result is True
        mock_picam.capture_file.assert_called_once_with(str(output))

    def test_capture_picamera2_failure(self, tmp_path: Path) -> None:
        cam = CameraDriver()
        mock_picam = MagicMock()
        mock_picam.capture_file.side_effect = RuntimeError("camera error")
        cam._picamera2 = mock_picam

        output = tmp_path / "test.jpg"
        result = cam.capture(output)

        assert result is False

    def test_capture_creates_parent_dirs(self, tmp_path: Path) -> None:
        cam = CameraDriver()
        mock_picam = MagicMock()
        cam._picamera2 = mock_picam

        output = tmp_path / "subdir" / "deep" / "test.jpg"
        cam.capture(output)

        assert output.parent.exists()

    def test_capture_falls_back_to_libcamera(self, tmp_path: Path) -> None:
        cam = CameraDriver()
        # No picamera2 initialized

        with patch("pi.drivers.camera.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = cam.capture(tmp_path / "test.jpg")

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "libcamera-still"

    def test_capture_libcamera_failure(self, tmp_path: Path) -> None:
        cam = CameraDriver()

        with patch("pi.drivers.camera.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="no camera")
            result = cam.capture(tmp_path / "test.jpg")

        assert result is False

    def test_capture_libcamera_not_found(self, tmp_path: Path) -> None:
        cam = CameraDriver()

        with patch("pi.drivers.camera.subprocess.run", side_effect=FileNotFoundError):
            result = cam.capture(tmp_path / "test.jpg")

        assert result is False


class TestCameraClose:
    def test_close_with_picamera2(self) -> None:
        cam = CameraDriver()
        mock_picam = MagicMock()
        cam._picamera2 = mock_picam

        cam.close()

        mock_picam.stop.assert_called_once()
        mock_picam.close.assert_called_once()
        assert cam._picamera2 is None

    def test_close_without_camera(self) -> None:
        cam = CameraDriver()
        cam.close()  # Should not raise

    def test_close_handles_error(self) -> None:
        cam = CameraDriver()
        mock_picam = MagicMock()
        mock_picam.stop.side_effect = RuntimeError("already closed")
        cam._picamera2 = mock_picam

        cam.close()  # Should not raise
        assert cam._picamera2 is None
