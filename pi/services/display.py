"""Display service — rotating OLED screens showing live sensor data.

Cycles through pages: current values, system status bars,
sparkline trends. Each page displays for a configurable duration.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pi.config.schema import DisplayConfig

logger = logging.getLogger(__name__)

# Short display labels for sensor IDs
SENSOR_LABELS = {
    "bme280_temperature": ("TEMP", "°C"),
    "bme280_humidity": ("RH", "%"),
    "bme280_pressure": ("PRES", "hPa"),
    "ezo_ph": ("PH", ""),
    "ezo_ec": ("EC", "µS"),
    "ds18b20_temperature": ("WTEMP", "°C"),
}


def render_values_page(oled, readings: dict) -> None:
    """Render current sensor values on the OLED.

    Args:
        oled: OLEDDriver instance.
        readings: Dict of sensor_id → SensorReading.
    """
    oled.clear()
    oled.draw_text(0, 0, "LIVING LIGHT", size=10)

    y = 14
    for sensor_id, reading in readings.items():
        label, unit = SENSOR_LABELS.get(sensor_id, (sensor_id[:6], ""))
        text = f"{label:6s} {reading.value:>7.1f}{unit}"
        oled.draw_text(0, y, text, size=10)
        y += 12
        if y > 56:
            break

    oled.show()


def render_status_page(oled, status: dict[str, float]) -> None:
    """Render subsystem status bars on the OLED.

    Args:
        oled: OLEDDriver instance.
        status: Dict of subsystem_name → fill (0.0–1.0).
    """
    oled.clear()
    oled.draw_text(0, 0, "SYSTEM STATUS", size=10)

    y = 16
    for name, fill in status.items():
        oled.draw_text(0, y, name.upper()[:5], size=9)
        oled.draw_bar(40, y + 1, 80, 8, fill=fill)
        y += 12
        if y > 56:
            break

    oled.show()


def render_sparkline_page(
    oled, label: str, values: list[float], unit: str
) -> None:
    """Render a sparkline trend chart on the OLED.

    Args:
        oled: OLEDDriver instance.
        label: Chart title (e.g., "TEMP").
        values: List of float values for the sparkline.
        unit: Unit string for the header.
    """
    oled.clear()

    if values:
        current = f"{values[-1]:.1f}"
        oled.draw_text(0, 0, f"{label} {current}{unit}", size=10)
    else:
        oled.draw_text(0, 0, f"{label} --{unit}", size=10)

    if len(values) >= 2:
        oled.draw_sparkline(0, 16, oled.WIDTH - 4, 44, values)

    oled.show()


class DisplayService:
    """Manages the OLED display lifecycle and page rotation."""

    def __init__(self, oled, repo, config: DisplayConfig) -> None:
        self._oled = oled
        self._repo = repo
        self._config = config
        self._task: asyncio.Task | None = None
        self._page_index = 0
        self._page_duration = 5  # seconds per page

    async def start(self) -> None:
        """Start the display rotation loop."""
        if self._task is not None:
            return

        if not self._config.enabled:
            logger.info("Display disabled in config")
            return

        if not self._oled.is_available:
            logger.warning("OLED display not available — skipping")
            return

        logger.info("Starting display service")
        self._task = asyncio.create_task(self._rotation_loop())

    async def stop(self) -> None:
        """Stop the display and clear the screen."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._oled.clear()
        self._oled.show()

    async def _rotation_loop(self) -> None:
        """Cycle through display pages."""
        pages = [
            self._render_values,
            self._render_status,
            self._render_sparkline,
        ]

        while True:
            page_fn = pages[self._page_index]
            try:
                await page_fn()
            except Exception as exc:
                logger.debug("Display render error: %s", exc)

            self._page_index = (self._page_index + 1) % len(pages)
            await asyncio.sleep(self._page_duration)

    async def _render_values(self) -> None:
        """Fetch latest readings and render values page."""
        sensor_ids = await self._repo.get_sensor_ids()
        readings = {}
        for sid in sensor_ids:
            r = await self._repo.get_latest(sid)
            if r is not None:
                readings[sid] = r
        render_values_page(self._oled, readings)

    async def _render_status(self) -> None:
        """Build subsystem status and render bars."""
        sensor_ids = await self._repo.get_sensor_ids()
        status = {}

        # Map sensors to subsystems with normalized values
        for sid in sensor_ids:
            r = await self._repo.get_latest(sid)
            if r is None:
                continue
            if "temperature" in sid:
                status["air"] = max(0.0, min(1.0, r.value / 40.0))
            elif "humidity" in sid:
                status["water"] = max(0.0, min(1.0, r.value / 100.0))
            elif "ph" in sid:
                status["root"] = max(0.0, min(1.0, r.value / 14.0))

        render_status_page(self._oled, status)

    async def _render_sparkline(self) -> None:
        """Fetch 1-hour trend for first available sensor and render."""
        sensor_ids = await self._repo.get_sensor_ids()
        if not sensor_ids:
            render_sparkline_page(self._oled, "DATA", [], "")
            return

        sid = sensor_ids[0]
        label, unit = SENSOR_LABELS.get(sid, (sid[:6], ""))

        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=1)
        readings = await self._repo.get_range(sid, start, end)
        values = [r.value for r in readings]

        render_sparkline_page(self._oled, label, values, unit)
