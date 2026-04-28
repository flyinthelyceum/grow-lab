"""REST API routes for sensor data, events, and camera captures.

All endpoints return JSON. Time-windowed queries support
window parameter: 1h, 24h, 7d.

Stage 1 security: POST /fan/override is gated by `require_admin` and
limited via slowapi at security.rate_limit_admin. All other routes
remain public (read-only).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path as FsPath, PurePosixPath

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from pi.dashboard.security import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Stage 2: live webcam streaming.
# rpicam-vid produces concatenated JPEGs; we re-emit each as a multipart
# x-mixed-replace frame so browsers render it natively in <img>. Single
# concurrent stream enforced via asyncio.Lock; second caller gets 409.
_STREAM_DURATION_SECONDS = 30
_STREAM_BOUNDARY = "growlabframe"
_stream_lock = asyncio.Lock()

class TimeWindow(str, Enum):
    one_hour = "1h"
    twenty_four_hours = "24h"
    seven_days = "7d"

WINDOW_MAP = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


def _reading_to_dict(r) -> dict:
    return {
        "timestamp": r.iso_timestamp,
        "sensor_id": r.sensor_id,
        "value": r.value,
        "unit": r.unit,
        "metadata": r.metadata,
    }


def _event_to_dict(e) -> dict:
    return {
        "timestamp": e.iso_timestamp,
        "event_type": e.event_type,
        "description": e.description,
        "metadata": e.metadata,
    }


def _capture_to_dict(c) -> dict:
    capture_path = FsPath(c.filepath).expanduser()
    filename = PurePosixPath(c.filepath).name

    return {
        "timestamp": c.iso_timestamp,
        "filename": filename,
        "filesize_bytes": c.filesize_bytes,
        "available": capture_path.exists(),
        "url": f"/api/images/{filename}/file",
    }


@router.get("/readings/latest")
async def get_latest_readings(request: Request) -> dict:
    """Get the most recent reading for each known sensor."""
    repo = request.app.state.repo
    sensor_ids = await repo.get_sensor_ids()
    result = {}
    for sid in sensor_ids:
        reading = await repo.get_latest(sid)
        if reading is not None:
            result[sid] = _reading_to_dict(reading)
    return result


@router.get("/readings/{sensor_id}")
async def get_readings(
    request: Request,
    sensor_id: str = Path(..., pattern=r"^[a-zA-Z0-9_]{1,64}$"),
    window: TimeWindow = Query(default=TimeWindow.twenty_four_hours),
) -> list[dict]:
    """Get time-windowed sensor readings."""
    repo = request.app.state.repo
    delta = WINDOW_MAP.get(window.value, timedelta(hours=24))
    end = datetime.now(timezone.utc)
    start = end - delta
    readings = await repo.get_range(sensor_id, start, end)
    return [_reading_to_dict(r) for r in readings]


# Bucket sizes: 5min for 24h (288 points), 1min for 1h (60 points), 30min for 7d (336 points)
_BUCKET_SECONDS = {
    "1h": 60,
    "24h": 300,
    "7d": 1800,
}


@router.get("/readings/{sensor_id}/downsampled")
async def get_readings_downsampled(
    request: Request,
    sensor_id: str = Path(..., pattern=r"^[a-zA-Z0-9_]{1,64}$"),
    window: TimeWindow = Query(default=TimeWindow.twenty_four_hours),
) -> list[dict]:
    """Get downsampled sensor readings bucketed by time interval.

    Returns averaged values per bucket: 288 points for 24h,
    60 points for 1h, 336 points for 7d.
    """
    repo = request.app.state.repo
    delta = WINDOW_MAP.get(window.value, timedelta(hours=24))
    bucket_sec = _BUCKET_SECONDS.get(window.value, 300)
    end = datetime.now(timezone.utc)
    start = end - delta

    cursor = await repo.db.execute(
        "SELECT"
        "    CAST(strftime('%s', replace(timestamp, '+00:00', 'Z')) AS INTEGER)"
        "        / ? * ? AS bucket,"
        "    AVG(value) AS avg_value,"
        "    unit"
        " FROM sensor_readings"
        " WHERE sensor_id = ? AND timestamp >= ? AND timestamp <= ?"
        " GROUP BY bucket"
        " ORDER BY bucket ASC",
        (bucket_sec, bucket_sec, sensor_id, start.isoformat(), end.isoformat()),
    )
    rows = await cursor.fetchall()
    return [
        {
            "timestamp": datetime.fromtimestamp(row[0], tz=timezone.utc).isoformat(),
            "sensor_id": sensor_id,
            "value": row[1],
            "unit": row[2],
        }
        for row in rows
    ]


@router.get("/events")
async def get_events(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    """Get recent system events."""
    repo = request.app.state.repo
    events = await repo.get_events(limit=limit)
    return [_event_to_dict(e) for e in events]


@router.get("/images/latest")
async def get_latest_image(request: Request) -> dict | None:
    """Get the most recent camera capture."""
    repo = request.app.state.repo
    captures = await repo.get_captures(limit=1)
    if not captures:
        return None
    return _capture_to_dict(captures[0])


@router.get("/images/{filename}/file")
async def get_image_file(
    request: Request,
    filename: str = Path(..., pattern=r"^[^/]+$"),
) -> FileResponse:
    """Serve an image file by filename if it exists in recent captures."""
    repo = request.app.state.repo
    captures = await repo.get_captures(limit=100)
    for capture in captures:
        if PurePosixPath(capture.filepath).name != filename:
            continue

        capture_path = FsPath(capture.filepath).expanduser()
        if not capture_path.exists():
            raise HTTPException(status_code=404, detail="Capture file not found")

        return FileResponse(capture_path)

    raise HTTPException(status_code=404, detail="Capture not found")


@router.get("/images")
async def get_images(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict]:
    """Get recent camera captures."""
    repo = request.app.state.repo
    captures = await repo.get_captures(limit=limit)
    return [_capture_to_dict(c) for c in captures]


@router.get("/alerts")
async def get_alerts(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    """Get recent alert events (warning and critical only)."""
    repo = request.app.state.repo
    events = await repo.get_events(limit=limit)
    return [
        _event_to_dict(e)
        for e in events
        if e.event_type in ("alert_warning", "alert_critical")
    ]


@router.get("/alerts/rules")
async def get_alert_rules() -> list[dict]:
    """Get the current threshold alerting rules."""
    from pi.services.alerts import DEFAULT_RULES

    return [
        {
            "sensor_id": r.sensor_id,
            "label": r.label or r.sensor_id,
            "unit": r.unit,
            "warning_low": r.warning_low,
            "warning_high": r.warning_high,
            "critical_low": r.critical_low,
            "critical_high": r.critical_high,
        }
        for r in DEFAULT_RULES
    ]


@router.get("/fan/status")
async def get_fan_status(request: Request) -> dict:
    """Get fan status based on latest air temperature and config."""
    from pi.config.schema import FanConfig
    from pi.drivers.fan_pwm import FanPWMDriver

    repo = request.app.state.repo
    reading = await repo.get_latest("bme280_temperature")

    config = getattr(request.app.state, "fan_config", FanConfig())
    temp_f = None
    duty = None

    if reading is not None:
        temp_f = reading.value * 9.0 / 5.0 + 32.0
        duty = FanPWMDriver.static_duty_for_temperature(
            temp_f,
            min_duty=config.min_duty,
            max_duty=config.max_duty,
            ramp_low=config.ramp_temp_low_f,
            ramp_high=config.ramp_temp_high_f,
        )

    return {
        "enabled": config.enabled,
        "temp_f": round(temp_f, 1) if temp_f is not None else None,
        "duty_percent": duty,
        "gpio_pin": config.gpio_pin,
        "ramp_temp_low_f": config.ramp_temp_low_f,
        "ramp_temp_high_f": config.ramp_temp_high_f,
        "min_duty": config.min_duty,
        "max_duty": config.max_duty,
    }


class FanOverrideRequest(BaseModel):
    duty: int | None = Field(default=None, ge=0, le=100)
    mode: str | None = Field(default=None, pattern=r"^auto$")


def _admin_rate_limit():
    """Return a slowapi limit decorator pinned to security.rate_limit_admin.

    Resolved at request time so it reflects the live SecurityConfig on
    app.state. Falls back to "10/minute" if state is missing.
    """

    def _decorator(func):
        # Wrap with a closure that defers limiter binding until call time.
        async def _wrapped(request: Request, *args, **kwargs):
            limiter = getattr(request.app.state, "limiter", None)
            sec = getattr(request.app.state, "security_config", None)
            limit_str = sec.rate_limit_admin if sec else "10/minute"
            if limiter is not None:
                # Apply limit via slowapi's `limit` decorator dynamically.
                limited = limiter.limit(limit_str)(func)
                return await limited(request, *args, **kwargs)
            return await func(request, *args, **kwargs)

        _wrapped.__name__ = func.__name__
        _wrapped.__doc__ = func.__doc__
        return _wrapped

    return _decorator


@router.post("/fan/override", dependencies=[Depends(require_admin)])
async def set_fan_override(request: Request, body: FanOverrideRequest) -> dict:
    """Set a manual fan duty cycle or return to auto mode (admin only)."""
    fan_svc = getattr(request.app.state, "fan_service", None)
    if fan_svc is None:
        raise HTTPException(status_code=503, detail="Fan service not available")

    if body.mode == "auto":
        fan_svc.clear_override()
    elif body.duty is not None:
        fan_svc.set_override(body.duty)
    else:
        raise HTTPException(status_code=422, detail="Provide 'duty' or 'mode: auto'")

    return {
        "override_duty": fan_svc.override_duty,
        "mode": "auto" if fan_svc.override_duty is None else "manual",
    }


@router.get("/system/status")
async def get_system_status(request: Request) -> dict:
    """Get system status: database stats and active sensors."""
    repo = request.app.state.repo
    db_info = await repo.get_db_info()
    sensor_ids = await repo.get_sensor_ids()
    return {
        "db": db_info,
        "sensors": sensor_ids,
    }


@router.get(
    "/stream/live",
    dependencies=[Depends(require_admin)],
)
async def stream_live() -> StreamingResponse:
    """30-second admin-only MJPEG live feed.

    Spawns rpicam-vid (libcamera) as a subprocess emitting MJPEG to stdout,
    parses JPEG frame boundaries (FFD8 / FFD9), wraps each frame in
    multipart/x-mixed-replace so browsers render it as a live <img src=...>
    feed. Hard-capped at 30 seconds; subprocess auto-exits via -t flag and
    is also terminated on client disconnect. Single concurrent stream;
    second caller gets 409.
    """
    if _stream_lock.locked():
        raise HTTPException(status_code=409, detail="Stream already in progress")

    async def frame_stream():
        async with _stream_lock:
            duration_ms = _STREAM_DURATION_SECONDS * 1000
            proc = await asyncio.create_subprocess_exec(
                "rpicam-vid",
                "--codec", "mjpeg",
                "-t", str(duration_ms),
                "--width", "1280",
                "--height", "720",
                "--framerate", "10",
                "-n",
                "-o", "-",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            buffer = b""
            try:
                while True:
                    chunk = await proc.stdout.read(8192)
                    if not chunk:
                        break
                    buffer += chunk
                    while True:
                        soi = buffer.find(b"\xff\xd8")
                        if soi < 0:
                            break
                        eoi = buffer.find(b"\xff\xd9", soi + 2)
                        if eoi < 0:
                            break
                        eoi_end = eoi + 2
                        frame = buffer[soi:eoi_end]
                        buffer = buffer[eoi_end:]
                        yield (
                            f"--{_STREAM_BOUNDARY}\r\n"
                            f"Content-Type: image/jpeg\r\n"
                            f"Content-Length: {len(frame)}\r\n\r\n"
                        ).encode("ascii")
                        yield frame
                        yield b"\r\n"
            except asyncio.CancelledError:
                logger.info("[stream] client disconnected")
                raise
            finally:
                if proc.returncode is None:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                logger.info("[stream] session ended")

    return StreamingResponse(
        frame_stream(),
        media_type=f"multipart/x-mixed-replace; boundary={_STREAM_BOUNDARY}",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
