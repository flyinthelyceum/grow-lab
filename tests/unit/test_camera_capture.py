"""Tests for the camera capture service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import CameraConfig
from pi.data.models import CameraCapture
from pi.services.camera_capture import CameraCaptureService, _compute_dir_size


def _make_service(
    tmp_path: Path,
    camera_available: bool = True,
    max_storage: int = 1024 * 1024,
) -> tuple[CameraCaptureService, MagicMock, AsyncMock]:
    camera = MagicMock()
    camera.is_available = camera_available
    camera.capture.return_value = True
    repo = AsyncMock()

    config = CameraConfig(
        interval_seconds=60,
        resolution=(1920, 1080),
        output_dir=tmp_path / "images",
        enabled=True,
    )

    service = CameraCaptureService(camera, repo, config, max_storage_bytes=max_storage)
    return service, camera, repo


class TestCameraCaptureInit:
    def test_initial_state(self, tmp_path: Path) -> None:
        service, _, _ = _make_service(tmp_path)
        assert service.is_running is False
        assert service.capture_count == 0


class TestCaptureNow:
    async def test_capture_saves_to_db(self, tmp_path: Path) -> None:
        service, camera, repo = _make_service(tmp_path)

        # Create the fake image file so stat() works
        output_dir = tmp_path / "images"
        output_dir.mkdir(parents=True)

        def fake_capture(path: Path) -> bool:
            path.write_bytes(b"fake image data")
            return True

        camera.capture.side_effect = fake_capture

        result = await service.capture_now()

        assert result is not None
        assert result.filesize_bytes == 15  # len(b"fake image data")
        repo.save_capture.assert_called_once()
        assert service.capture_count == 1

    async def test_capture_returns_none_on_failure(self, tmp_path: Path) -> None:
        service, camera, repo = _make_service(tmp_path)
        camera.capture.return_value = False

        result = await service.capture_now()

        assert result is None
        repo.save_capture.assert_not_called()
        assert service.capture_count == 0

    async def test_capture_increments_count(self, tmp_path: Path) -> None:
        service, camera, repo = _make_service(tmp_path)
        output_dir = tmp_path / "images"
        output_dir.mkdir(parents=True)

        def fake_capture(path: Path) -> bool:
            path.write_bytes(b"img")
            return True

        camera.capture.side_effect = fake_capture

        await service.capture_now()
        await service.capture_now()

        assert service.capture_count == 2


class TestStorageManagement:
    def test_compute_dir_size(self, tmp_path: Path) -> None:
        (tmp_path / "a.jpg").write_bytes(b"x" * 100)
        (tmp_path / "b.jpg").write_bytes(b"y" * 200)
        assert _compute_dir_size(tmp_path) == 300

    def test_compute_dir_size_empty(self, tmp_path: Path) -> None:
        assert _compute_dir_size(tmp_path) == 0

    def test_compute_dir_size_missing(self, tmp_path: Path) -> None:
        assert _compute_dir_size(tmp_path / "nonexistent") == 0

    async def test_enforce_storage_removes_oldest(self, tmp_path: Path) -> None:
        # Max storage = 200 bytes
        service, _, repo = _make_service(tmp_path, max_storage=200)

        output_dir = tmp_path / "images"
        output_dir.mkdir(parents=True)

        # Create files totaling 300 bytes (over 200 limit)
        import time as _time

        f1 = output_dir / "old.jpg"
        f1.write_bytes(b"x" * 100)

        # Ensure different mtime
        _time.sleep(0.05)

        f2 = output_dir / "new.jpg"
        f2.write_bytes(b"y" * 200)

        await service._enforce_storage_limit()

        # Old file should be removed, new file kept
        assert not f1.exists()
        assert f2.exists()
        repo.save_event.assert_called_once()

    async def test_no_cleanup_when_under_limit(self, tmp_path: Path) -> None:
        service, _, repo = _make_service(tmp_path, max_storage=1000)

        output_dir = tmp_path / "images"
        output_dir.mkdir(parents=True)
        (output_dir / "small.jpg").write_bytes(b"x" * 100)

        await service._enforce_storage_limit()

        assert (output_dir / "small.jpg").exists()
        repo.save_event.assert_not_called()


class TestStartStop:
    async def test_start_creates_task(self, tmp_path: Path) -> None:
        service, _, _ = _make_service(tmp_path)
        await service.start()
        assert service.is_running is True
        assert service._task is not None
        await service.stop()

    async def test_start_skips_when_no_camera(self, tmp_path: Path) -> None:
        service, _, _ = _make_service(tmp_path, camera_available=False)
        await service.start()
        assert service.is_running is False
        assert service._task is None

    async def test_start_idempotent(self, tmp_path: Path) -> None:
        service, _, _ = _make_service(tmp_path)
        await service.start()
        task1 = service._task
        await service.start()
        assert service._task is task1
        await service.stop()

    async def test_stop_closes_camera(self, tmp_path: Path) -> None:
        service, camera, _ = _make_service(tmp_path)
        await service.start()
        await service.stop()
        camera.close.assert_called_once()
        assert service.is_running is False


class TestCaptureLoop:
    async def test_loop_captures_and_sleeps(self, tmp_path: Path) -> None:
        service, camera, repo = _make_service(tmp_path)
        service._running = True

        output_dir = tmp_path / "images"
        output_dir.mkdir(parents=True)

        def fake_capture(path: Path) -> bool:
            path.write_bytes(b"img")
            return True

        camera.capture.side_effect = fake_capture

        call_count = 0

        async def counting_sleep(seconds: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()

        with patch("pi.services.camera_capture.asyncio.sleep", side_effect=counting_sleep):
            try:
                await service._capture_loop()
            except asyncio.CancelledError:
                pass

        assert service.capture_count >= 1
        assert repo.save_capture.call_count >= 1
