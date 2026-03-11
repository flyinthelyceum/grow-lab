"""REST API routes for sensor data, events, and camera captures.

All endpoints return JSON. Time-windowed queries support
window parameter: 1h, 24h, 7d.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import APIRouter, Path, Query, Request

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
    from pathlib import PurePosixPath

    return {
        "timestamp": c.iso_timestamp,
        "filename": PurePosixPath(c.filepath).name,
        "filesize_bytes": c.filesize_bytes,
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
