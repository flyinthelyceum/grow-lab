"""REST API routes for sensor data, events, and camera captures.

All endpoints return JSON. Time-windowed queries support
window parameter: 1h, 24h, 7d.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path as FsPath, PurePosixPath

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api")

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
