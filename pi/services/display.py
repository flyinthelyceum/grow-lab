"""Display service — rotating OLED screens showing live system data.

Cycles through pages: current sensor values, irrigation status,
and sparkline trends. Each page displays for a configurable duration.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pi.config.schema import DisplayConfig, IrrigationConfig

logger = logging.getLogger(__name__)

# Short display labels for sensor IDs
SENSOR_LABELS = {
    "bme280_temperature": ("TEMP", "C"),
    "bme280_humidity": ("RH", "%"),
    "bme280_pressure": ("PRES", "hPa"),
    "ezo_ph": ("PH", ""),
    "ezo_ec": ("EC", "uS"),
    "ds18b20_temperature": ("WTEMP", "C"),
}


def render_values_page(oled, readings: dict) -> None:
    """Render current sensor values on the OLED."""
    oled.clear()
    oled.draw_text(0, 0, "LIVING LIGHT", size=10)

    y = 14
    for sensor_id, reading in readings.items():
        label, unit = SENSOR_LABELS.get(sensor_id, (sensor_id[:6], ""))
        text = f"{label:6s}{reading.value:>6.1f}{unit}"
        oled.draw_text(0, y, text, size=10)
        y += 12
        if y > 56:
            break

    if not readings:
        oled.draw_text(0, 28, "No sensors yet", size=10)

    oled.show()


def render_irrigation_page(
    oled,
    schedules: tuple,
    last_pump_event: str | None,
    now: datetime,
) -> None:
    """Render irrigation schedule and last pump event."""
    oled.clear()
    oled.draw_text(0, 0, "IRRIGATION", size=10)

    # Show schedule times
    y = 14
    for s in schedules[:3]:
        marker = ">"
        sched_min = s.hour * 60 + s.minute
        now_min = now.hour * 60 + now.minute
        # Mark next upcoming schedule
        if sched_min > now_min:
            marker = ">"
        else:
            marker = " "
        text = f"{marker}{s.hour:02d}:{s.minute:02d}  {s.duration_seconds}s"
        oled.draw_text(0, y, text, size=10)
        y += 12

    # Show last pump event
    if last_pump_event:
        oled.draw_text(0, 52, last_pump_event[:21], size=9)
    else:
        oled.draw_text(0, 52, "No pump events", size=9)

    oled.show()


def render_system_page(oled, uptime: timedelta, subsystems: dict[str, bool]) -> None:
    """Render system overview — uptime and subsystem status."""
    oled.clear()
    oled.draw_text(0, 0, "SYSTEM", size=10)

    # Uptime
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes = remainder // 60
    oled.draw_text(0, 14, f"UP {hours:3d}h{minutes:02d}m", size=10)

    # Subsystem checklist
    y = 28
    for name, ok in subsystems.items():
        icon = "+" if ok else "-"
        oled.draw_text(0, y, f"{icon} {name}", size=9)
        y += 11
        if y > 58:
            break

    oled.show()


def render_sparkline_page(
    oled, label: str, values: list[float], unit: str
) -> None:
    """Render a sparkline trend chart on the OLED."""
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

    def __init__(
        self,
        oled,
        repo,
        config: DisplayConfig,
        irrigation_config: IrrigationConfig | None = None,
        irrigator=None,
    ) -> None:
        self._oled = oled
        self._repo = repo
        self._config = config
        self._irrigation_config = irrigation_config
        self._irrigator = irrigator
        self._task: asyncio.Task | None = None
        self._page_index = 0
        self._page_duration = 5  # seconds per page
        self._start_time = datetime.now(timezone.utc)

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

        self._start_time = datetime.now(timezone.utc)
        logger.info("Display service started")
        self._task = asyncio.create_task(
            self._rotation_loop(), name="display-rotation"
        )

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
            self._render_system,
            self._render_irrigation,
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

    async def _render_system(self) -> None:
        """Render system overview page."""
        now = datetime.now(timezone.utc)
        uptime = now - self._start_time

        sensor_ids = await self._repo.get_sensor_ids()
        subsystems = {
            "sensors": len(sensor_ids) > 0,
            "irrigation": self._irrigator is not None and self._irrigator.is_running,
            "display": True,
        }

        render_system_page(self._oled, uptime, subsystems)

    async def _render_irrigation(self) -> None:
        """Render irrigation schedule page."""
        if self._irrigation_config is None:
            self._oled.clear()
            self._oled.draw_text(0, 0, "IRRIGATION", size=10)
            self._oled.draw_text(0, 20, "Not configured", size=10)
            self._oled.show()
            return

        now = datetime.now(timezone.utc)

        # Get last irrigation event
        events = await self._repo.get_events(limit=10)
        last_pump = None
        for e in events:
            if e.event_type == "irrigation":
                last_pump = e.description
                break

        render_irrigation_page(
            self._oled,
            self._irrigation_config.schedules,
            last_pump,
            now,
        )

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
