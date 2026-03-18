"""Camera driver wrapping picamera2.

Captures still images at configurable resolution. Falls back to
rpicam-still (or legacy libcamera-still) if picamera2 is unavailable.
Returns None when no camera hardware is detected.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class CameraDriver:
    """Thin wrapper over picamera2 / libcamera-still."""

    def __init__(
        self,
        resolution: tuple[int, int] = (4608, 2592),
    ) -> None:
        self._resolution = resolution
        self._picamera2 = None
        self._still_cmd: str = "rpicam-still"
        self._available: bool | None = None

    @property
    def is_available(self) -> bool:
        """Check if a camera is connected."""
        if self._available is not None:
            return self._available

        self._available = self._try_init_picamera2() or self._check_libcamera()
        return self._available

    def capture(self, output_path: Path) -> bool:
        """Capture a still image to output_path.

        Returns True on success, False on failure.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self._picamera2 is not None:
            return self._capture_picamera2(output_path)

        return self._capture_libcamera(output_path)

    def close(self) -> None:
        """Release camera resources."""
        if self._picamera2 is not None:
            try:
                self._picamera2.stop()
                self._picamera2.close()
            except Exception as exc:
                logger.debug("Camera close error: %s", exc)
            self._picamera2 = None

    def _try_init_picamera2(self) -> bool:
        """Try to initialize picamera2. Returns True on success."""
        try:
            from picamera2 import Picamera2

            cam = Picamera2()
            config = cam.create_still_configuration(
                main={"size": self._resolution}
            )
            cam.configure(config)
            cam.start()
            self._picamera2 = cam
            logger.info(
                "Camera initialized via picamera2 (%dx%d)",
                self._resolution[0],
                self._resolution[1],
            )
            return True
        except Exception as exc:
            logger.debug("picamera2 unavailable: %s", exc)
            return False

    def _check_libcamera(self) -> bool:
        """Check if rpicam-still (or legacy libcamera-still) is available."""
        for cmd in ("rpicam-still", "libcamera-still"):
            try:
                result = subprocess.run(
                    [cmd, "--list-cameras"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and "Available" in result.stdout:
                    self._still_cmd = cmd
                    logger.info("Camera available via %s", cmd)
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        logger.debug("No camera CLI tool found")
        return False

    def _capture_picamera2(self, output_path: Path) -> bool:
        """Capture using picamera2."""
        try:
            self._picamera2.capture_file(str(output_path))
            logger.debug("Captured image: %s", output_path)
            return True
        except Exception as exc:
            logger.error("picamera2 capture failed: %s", exc)
            return False

    def _capture_libcamera(self, output_path: Path) -> bool:
        """Capture using rpicam-still (or legacy libcamera-still) subprocess."""
        try:
            result = subprocess.run(
                [
                    self._still_cmd,
                    "-o", str(output_path),
                    "--width", str(self._resolution[0]),
                    "--height", str(self._resolution[1]),
                    "--nopreview",
                    "-t", "1000",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                logger.debug("Captured image via libcamera-still: %s", output_path)
                return True
            else:
                logger.error("%s failed: %s", self._still_cmd, result.stderr)
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.error("%s capture error: %s", self._still_cmd, exc)
            return False
