"""SSD1306 OLED display driver (128x64, I²C).

Renders framebuffer content to the physical OLED display.
Uses Pillow for software rendering. On Pi, luma.oled pushes
the framebuffer to hardware. On Mac, the image stays in memory
(useful for testing drawing logic).
"""

from __future__ import annotations

import logging

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class OLEDDriver:
    """Software framebuffer + optional hardware output via luma.oled."""

    WIDTH = 128
    HEIGHT = 64

    def __init__(self, address: int = 0x3C, bus: int = 1) -> None:
        self._address = address
        self._bus = bus
        self._device = None
        self._image = Image.new("1", (self.WIDTH, self.HEIGHT), 0)
        self._draw = ImageDraw.Draw(self._image)
        self._font = _load_font(10)
        self._try_init_device()

    @property
    def is_available(self) -> bool:
        """True if a physical OLED device is connected."""
        return self._device is not None

    def clear(self) -> None:
        """Reset the framebuffer to black."""
        self._image = Image.new("1", (self.WIDTH, self.HEIGHT), 0)
        self._draw = ImageDraw.Draw(self._image)

    def draw_text(self, x: int, y: int, text: str, size: int = 10) -> None:
        """Draw text at (x, y) with the given font size."""
        font = _load_font(size)
        self._draw.text((x, y), text, fill=1, font=font)

    def draw_bar(self, x: int, y: int, width: int, height: int, fill: float) -> None:
        """Draw a horizontal bar graph. fill is 0.0–1.0."""
        fill = max(0.0, min(1.0, fill))
        # Outline
        self._draw.rectangle([x, y, x + width, y + height], outline=1, fill=0)
        # Filled portion
        fill_width = int(width * fill)
        if fill_width > 0:
            self._draw.rectangle(
                [x + 1, y + 1, x + fill_width, y + height - 1], fill=1
            )

    def draw_sparkline(
        self, x: int, y: int, width: int, height: int, values: list[float]
    ) -> None:
        """Draw a sparkline chart from a list of values."""
        if len(values) < 2:
            return

        v_min = min(values)
        v_max = max(values)
        v_range = v_max - v_min if v_max != v_min else 1.0

        points = []
        for i, v in enumerate(values):
            px = x + int(i * width / (len(values) - 1))
            py = y + height - int((v - v_min) / v_range * height)
            points.append((px, py))

        # Draw connected line segments
        for i in range(len(points) - 1):
            self._draw.line([points[i], points[i + 1]], fill=1)

    def show(self) -> None:
        """Push the framebuffer to the physical display (if connected)."""
        if self._device is not None:
            self._device.display(self._image)

    def close(self) -> None:
        """Release the display device."""
        if self._device is not None:
            try:
                self._device.hide()
            except Exception as exc:
                logger.debug("OLED close error: %s", exc)
            self._device = None

    def _try_init_device(self) -> None:
        """Try to initialize the physical SSD1306 via luma.oled."""
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306

            serial = i2c(port=self._bus, address=self._address)
            self._device = ssd1306(serial)
            logger.info("OLED display initialized at 0x%02X on bus %d", self._address, self._bus)
        except Exception as exc:
            logger.debug("OLED not available: %s", exc)
            self._device = None


def _load_font(size: int) -> ImageFont.ImageFont:
    """Load a font, falling back to Pillow default."""
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size)
    except (IOError, OSError):
        return ImageFont.load_default()
