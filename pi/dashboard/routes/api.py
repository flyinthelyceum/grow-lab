"""REST API routes for sensor data, events, and camera captures.

All endpoints return JSON. Time-windowed queries support
window parameter: 1h, 24h, 7d.

Stage 1 security: POST /fan/override and POST /meters/override are gated
by `require_admin` and limited via slowapi at security.rate_limit_admin.
All other routes remain public (read-only), including /meters/status and
/control.

Both override endpoints write desired state to the `control_state` table
rather than calling a service object. The dashboard and the orchestrator
are separate processes; the table is the channel between them.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path as FsPath, PurePosixPath

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from pi.dashboard.security import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Stage 2: live webcam streaming with multi-viewer fan-out.
# Single rpicam-vid subprocess emits MJPEG; many HTTP response generators
# subscribe to a shared frame fan-out. Each session is hard-capped at
# 30 seconds via the rpicam-vid -t flag. Late joiners share the in-flight
# session (their countdown may end before local 30s if they joined mid-way).
_STREAM_DURATION_SECONDS = 30
_STREAM_BOUNDARY = "growlabframe"


class _LiveStreamHub:
    """Fan-out broker: one rpicam-vid subprocess, many HTTP viewers.

    Concurrency model: the first viewer starts a session (spawns
    rpicam-vid, kicks off a broadcaster task that splits MJPEG frames
    and pushes each into every subscriber's per-viewer queue). Subsequent
    viewers join the active session and receive frames from the same
    source. Sessions end when rpicam-vid exits (-t timeout, ~30s) or
    the broadcaster errors. New click after a session ends starts a
    fresh session.
    """

    def __init__(self) -> None:
        self._proc: asyncio.subprocess.Process | None = None
        self._broadcaster: asyncio.Task | None = None
        self._subscribers: list[asyncio.Queue] = []
        self._start_lock = asyncio.Lock()
        self._session_end_at: float = 0.0

    async def join(self) -> tuple[asyncio.Queue, float]:
        """Join the current session (or start a fresh one).

        Returns (queue, expires_at_unix). The queue receives raw JPEG
        bytes for each frame, then None when the session ends.
        """
        async with self._start_lock:
            now = time.time()
            if (
                self._proc is None
                or self._proc.returncode is not None
                or now >= self._session_end_at
            ):
                await self._start_new_session()
            queue: asyncio.Queue = asyncio.Queue(maxsize=4)
            self._subscribers.append(queue)
            return queue, self._session_end_at

    async def _start_new_session(self) -> None:
        # Notify any stragglers from a prior session and reset.
        self._notify_end()
        self._subscribers = []

        # Clean shutdown of any prior subprocess.
        if self._proc is not None and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                self._proc.kill()
                await self._proc.wait()

        self._proc = await asyncio.create_subprocess_exec(
            "rpicam-vid",
            "--codec", "mjpeg",
            "-t", str(_STREAM_DURATION_SECONDS * 1000),
            "--width", "1280",
            "--height", "720",
            "--framerate", "10",
            "-n",
            "-o", "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self._session_end_at = time.time() + _STREAM_DURATION_SECONDS
        self._broadcaster = asyncio.create_task(
            self._broadcast(self._proc), name="livehub-broadcast"
        )
        logger.info(
            "[stream] new session started; ends in %ds",
            _STREAM_DURATION_SECONDS,
        )

    async def _broadcast(self, proc: asyncio.subprocess.Process) -> None:
        """Read JPEG frames from rpicam-vid; push each to all subscribers."""
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
                    for queue in self._subscribers[:]:
                        try:
                            queue.put_nowait(frame)
                        except asyncio.QueueFull:
                            # Slow consumer: drop the frame for them.
                            pass
        except Exception as exc:
            logger.warning("[stream] broadcaster error: %r", exc)
        finally:
            self._notify_end()
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
            logger.info(
                "[stream] session ended; subscribers=%d",
                len(self._subscribers),
            )

    def _notify_end(self) -> None:
        for queue in self._subscribers[:]:
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

    def leave(self, queue: asyncio.Queue) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)


_stream_hub = _LiveStreamHub()

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


def _actor(request: Request) -> str | None:
    """Who set a control. The session carries only an admin flag, no username,
    so that flag is the whole of the identity available to record."""
    try:
        return "admin" if request.session.get("admin") else None
    except (AssertionError, AttributeError):
        # SessionMiddleware not installed (bare test app).
        return None


def _control_ttl(request: Request) -> float:
    from pi.config.schema import ControlConfig

    config = getattr(request.app.state, "control_config", None) or ControlConfig()
    return config.override_ttl_seconds


def _control_response(entry, *, value_key: str, parse) -> dict:
    """Shape one control row for a JSON response."""
    return {
        value_key: parse(entry.value),
        "mode": "auto" if entry.value is None else "manual",
        "updated_at": entry.updated_at.isoformat(),
        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
    }


@router.post("/fan/override", dependencies=[Depends(require_admin)])
async def set_fan_override(request: Request, body: FanOverrideRequest) -> dict:
    """Set a manual fan duty cycle or return to auto mode (admin only).

    Writes desired state to the control table rather than touching a service
    object: the orchestrator owns the fan and runs in a different process. The
    change reaches the hardware on that process's next control poll, within
    `[control] poll_interval_seconds`.

    A manual duty expires after `[control] override_ttl_seconds` so one left
    on by accident lapses back to the temperature ramp.
    """
    from pi.services.control import FAN_OVERRIDE, parse_duty

    repo = request.app.state.repo
    actor = _actor(request)

    if body.mode == "auto":
        entry = await repo.clear_control(FAN_OVERRIDE, updated_by=actor)
    elif body.duty is not None:
        entry = await repo.set_control(
            FAN_OVERRIDE,
            str(body.duty),
            ttl_seconds=_control_ttl(request),
            updated_by=actor,
        )
    else:
        raise HTTPException(status_code=422, detail="Provide 'duty' or 'mode: auto'")

    return _control_response(entry, value_key="override_duty", parse=parse_duty)


class MeterOverrideRequest(BaseModel):
    meter: str = Field(pattern=r"^(ph|ec)$")
    deflection: float | None = Field(default=None, ge=-1.0, le=1.0)
    mode: str | None = Field(default=None, pattern=r"^auto$")


@router.post("/meters/override", dependencies=[Depends(require_admin)])
async def set_meter_override(request: Request, body: MeterOverrideRequest) -> dict:
    """Pin one needle to a deflection, or return it to its sensor (admin only).

    Same channel as the fan override: desired state in the control table, read
    by the orchestrator that owns the DAC. Useful for checking a movement from
    the web without stopping the service to run `growlab meter set`.
    """
    from pi.services.control import (
        METER_EC_OVERRIDE,
        METER_PH_OVERRIDE,
        parse_deflection,
    )

    repo = request.app.state.repo
    actor = _actor(request)
    key = METER_PH_OVERRIDE if body.meter == "ph" else METER_EC_OVERRIDE

    if body.mode == "auto":
        entry = await repo.clear_control(key, updated_by=actor)
    elif body.deflection is not None:
        entry = await repo.set_control(
            key,
            str(body.deflection),
            ttl_seconds=_control_ttl(request),
            updated_by=actor,
        )
    else:
        raise HTTPException(
            status_code=422, detail="Provide 'deflection' or 'mode: auto'"
        )

    payload = _control_response(
        entry, value_key="deflection", parse=parse_deflection
    )
    payload["meter"] = body.meter
    return payload


@router.get("/control")
async def get_control_state(request: Request) -> dict:
    """Every control and what it is currently asking the hardware to do.

    Read-only, so it stays public alongside the other status endpoints. An
    expired override reports `mode: auto` with `expired: true`, which is what
    the orchestrator acts on — the stale value is shown for context only.
    """
    from pi.services.control import CONTROL_KEYS

    repo = request.app.state.repo
    rows = await repo.get_all_control()
    now = datetime.now(timezone.utc)

    controls = {}
    for key in CONTROL_KEYS:
        entry = rows.get(key)
        if entry is None:
            controls[key] = {
                "value": None,
                "mode": "auto",
                "expired": False,
                "updated_at": None,
                "expires_at": None,
                "updated_by": None,
            }
            continue
        expired = entry.is_expired(now)
        controls[key] = {
            "value": entry.effective_value(now),
            "mode": "auto" if entry.effective_value(now) is None else "manual",
            "expired": expired,
            "updated_at": entry.updated_at.isoformat(),
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            "updated_by": entry.updated_by,
        }

    return {"controls": controls}


@router.get("/meters/status")
async def get_meters_status(request: Request) -> dict:
    """Where the two physical panel needles are pointing, and why.

    The orchestrator (`growlab start`) owns the MCP4728 and eases the
    needles; the dashboard runs in a separate process and cannot reach that
    service object. So this endpoint recomputes the deflection from the same
    two inputs the service uses — the meter config and the latest reading in
    the database — which is what makes the web view and the panel agree
    without a channel between the processes.

    Deflection runs -1.0 (full left) through 0.0 (on target) to +1.0. A
    reading older than `fault_timeout_seconds` reads as faulted at centre,
    mirroring how the service eases a stale needle home.
    """
    from pi.config.schema import MetersConfig
    from pi.services.control import (
        METER_EC_OVERRIDE,
        METER_PH_OVERRIDE,
        parse_deflection,
    )
    from pi.services.meters import normalise

    repo = request.app.state.repo
    config = getattr(request.app.state, "meters_config", None) or MetersConfig()
    now = datetime.now(timezone.utc)

    # An override outranks the sensor, so report it or the panel and the page
    # disagree about why a needle is where it is.
    control = await repo.get_all_control()
    override_keys = {"ph": METER_PH_OVERRIDE, "ec": METER_EC_OVERRIDE}

    meters = {}
    for name, cc in (("ph", config.ph), ("ec", config.ec)):
        entry = control.get(override_keys[name])
        override = (
            parse_deflection(entry.effective_value(now)) if entry else None
        )
        reading = await repo.get_latest(cc.sensor_id)
        entry = {
            "sensor_id": cc.sensor_id,
            "centre": cc.centre,
            "span": cc.span,
            "dac_positive": cc.dac_positive,
            "dac_negative": cc.dac_negative,
            "value": None,
            "unit": None,
            "timestamp": None,
            "age_seconds": None,
            "deflection": 0.0,
            "faulted": True,
            "override": override,
        }

        if reading is not None:
            timestamp = reading.timestamp
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            age = (now - timestamp).total_seconds()
            stale = age >= config.fault_timeout_seconds
            value = reading.value * cc.scale
            entry.update({
                "value": round(value, 4),
                "unit": reading.unit,
                "timestamp": reading.iso_timestamp,
                "age_seconds": round(age, 1),
                "deflection": 0.0 if stale else round(
                    normalise(value, cc.centre, cc.span), 4
                ),
                "faulted": stale,
            })

        if override is not None:
            entry["deflection"] = override

        meters[name] = entry

    return {
        "enabled": config.enabled,
        "i2c_address": config.i2c_address,
        "fault_timeout_seconds": config.fault_timeout_seconds,
        "meters": meters,
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


@router.get("/stream/snapshot")
async def stream_snapshot():
    """Single JPEG frame from the active live session (iOS-friendly).

    Polled by clients that can't render multipart/x-mixed-replace in
    <img> (notably iOS WebKit / iOS Chrome). First call starts a session
    if none is active; subsequent calls during the session return the
    latest frame. Returns 410 Gone after session expiry so the client
    knows to stop polling.
    """
    from fastapi import Response

    queue, expires_at = await _stream_hub.join()
    if time.time() >= expires_at:
        _stream_hub.leave(queue)
        raise HTTPException(status_code=410, detail="Session expired")
    try:
        frame = await asyncio.wait_for(queue.get(), timeout=1.5)
        if frame is None:
            raise HTTPException(status_code=410, detail="Session ended")
        return Response(
            content=frame,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Stream-Expires-At": str(int(expires_at)),
                "X-Stream-Remaining-Seconds": str(
                    max(0, int(expires_at - time.time()))
                ),
                "Access-Control-Expose-Headers": (
                    "X-Stream-Expires-At, X-Stream-Remaining-Seconds"
                ),
            },
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Frame timeout")
    finally:
        _stream_hub.leave(queue)


@router.get("/stream/live")
async def stream_live() -> StreamingResponse:
    """Public MJPEG live feed with multi-viewer fan-out.

    Up to N concurrent viewers share a single 30-second rpicam-vid session.
    First click starts a session; later joiners receive frames from the
    in-flight session for whatever seconds remain. The next click after a
    session ends starts a fresh one. The X-Stream-Expires-At and
    X-Stream-Remaining-Seconds response headers let clients sync local
    countdown to actual session end (relevant for late joiners).
    """
    queue, expires_at = await _stream_hub.join()
    now = time.time()
    remaining = max(0, int(expires_at - now))

    async def frame_stream():
        try:
            while True:
                try:
                    frame = await asyncio.wait_for(queue.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    if time.time() >= expires_at:
                        break
                    continue
                if frame is None:  # session-ended sentinel
                    break
                yield (
                    f"--{_STREAM_BOUNDARY}\r\n"
                    f"Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(frame)}\r\n\r\n"
                ).encode("ascii")
                yield frame
                yield b"\r\n"
        except asyncio.CancelledError:
            logger.info("[stream] viewer disconnected")
            raise
        finally:
            _stream_hub.leave(queue)

    return StreamingResponse(
        frame_stream(),
        media_type=f"multipart/x-mixed-replace; boundary={_STREAM_BOUNDARY}",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Stream-Expires-At": str(int(expires_at)),
            "X-Stream-Remaining-Seconds": str(remaining),
            "Access-Control-Expose-Headers": (
                "X-Stream-Expires-At, X-Stream-Remaining-Seconds"
            ),
        },
    )
