"""Timed camera capture service with storage management.

Captures images at a configurable interval, logs captures to the
database, and manages disk usage by removing oldest images when
storage limits are exceeded.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from pi.config.schema import CameraConfig
from pi.data.models import CameraCapture, SystemEvent
from pi.data.repository import SensorRepository
from pi.drivers.camera import CameraDriver

logger = logging.getLogger(__name__)

# Default max storage: 2 GB
DEFAULT_MAX_STORAGE_BYTES = 2 * 1024 * 1024 * 1024


def _utcnow() -> datetime:
    """Current UTC time (seam for testing)."""
    return datetime.now(timezone.utc)


def _compute_dir_size(directory: Path) -> int:
    """Sum file sizes in a directory (non-recursive for images dir)."""
    if not directory.exists():
        return 0
    return sum(f.stat().st_size for f in directory.iterdir() if f.is_file())


class CameraCaptureService:
    """Periodically captures images and manages storage."""

    def __init__(
        self,
        camera: CameraDriver,
        repository: SensorRepository,
        config: CameraConfig,
        max_storage_bytes: int = DEFAULT_MAX_STORAGE_BYTES,
    ) -> None:
        self._camera = camera
        self._repository = repository
        self._config = config
        self._max_storage = max_storage_bytes
        self._task: asyncio.Task | None = None
        self._running = False
        self._capture_count = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def capture_count(self) -> int:
        return self._capture_count

    async def start(self) -> None:
        """Start the periodic capture loop."""
        if self._running:
            return

        if not self._camera.is_available:
            logger.warning("Camera not available — capture service not started")
            return

        self._running = True
        self._task = asyncio.create_task(
            self._capture_loop(), name="camera-capture"
        )
        logger.info(
            "Camera capture started: interval=%ds, output=%s",
            self._config.interval_seconds,
            self._config.output_dir,
        )

    async def stop(self) -> None:
        """Stop the capture loop and release camera."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._camera.close()
        logger.info("Camera capture stopped (%d images captured)", self._capture_count)

    async def capture_now(self) -> CameraCapture | None:
        """Take a single capture immediately. Returns the capture record or None."""
        now = _utcnow()
        filename = now.strftime("%Y%m%d_%H%M%S") + ".jpg"
        output_path = self._config.output_dir / filename

        success = await asyncio.to_thread(self._camera.capture, output_path)

        if not success:
            logger.warning("Capture failed: %s", output_path)
            return None

        filesize = output_path.stat().st_size if output_path.exists() else None
        capture = CameraCapture(
            timestamp=now,
            filepath=str(output_path),
            filesize_bytes=filesize,
        )

        await self._repository.save_capture(capture)
        self._capture_count += 1

        logger.debug(
            "Captured: %s (%s bytes)",
            filename,
            f"{filesize:,}" if filesize else "unknown",
        )
        return capture

    async def _capture_loop(self) -> None:
        """Capture images at the configured interval."""
        try:
            while self._running:
                await self.capture_now()
                await self._enforce_storage_limit()
                await asyncio.sleep(self._config.interval_seconds)
        except asyncio.CancelledError:
            raise

    async def _enforce_storage_limit(self) -> None:
        """Remove oldest images if storage exceeds the limit."""
        output_dir = self._config.output_dir
        if not output_dir.exists():
            return

        current_size = await asyncio.to_thread(_compute_dir_size, output_dir)

        if current_size <= self._max_storage:
            return

        # Sort by modification time, remove oldest first
        images = sorted(
            (f for f in output_dir.iterdir() if f.is_file()),
            key=lambda f: f.stat().st_mtime,
        )

        removed = 0
        for image in images:
            if current_size <= self._max_storage:
                break
            size = image.stat().st_size
            image.unlink()
            current_size -= size
            removed += 1

        if removed > 0:
            logger.info("Storage cleanup: removed %d oldest images", removed)
            await self._repository.save_event(
                SystemEvent(
                    timestamp=_utcnow(),
                    event_type="camera_cleanup",
                    description=f"Removed {removed} images to free storage",
                )
            )
