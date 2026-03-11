"""WebSocket endpoint for live sensor updates.

Broadcasts latest readings to all connected clients.
Sends one message immediately on connect, then the client
can poll or reconnect as needed. Rate-limited to prevent abuse.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

# Minimum interval between updates (seconds)
_MIN_UPDATE_INTERVAL = 1.0


def _reading_to_dict(r) -> dict:
    return {
        "sensor_id": r.sensor_id,
        "value": r.value,
        "unit": r.unit,
    }


async def _build_update(repo) -> dict:
    """Build a sensor update payload from the latest readings."""
    sensor_ids = await repo.get_sensor_ids()
    readings = []
    for sid in sensor_ids:
        r = await repo.get_latest(sid)
        if r is not None:
            readings.append(_reading_to_dict(r))
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "readings": readings,
    }


@router.websocket("/ws/updates")
async def ws_updates(websocket: WebSocket) -> None:
    """WebSocket endpoint pushing latest sensor readings."""
    await websocket.accept()
    repo = getattr(websocket.app.state, "repo", None)
    if repo is None:
        await websocket.close(code=1011, reason="Repository not available")
        return
    last_send = 0.0
    try:
        # Send initial update immediately
        update = await _build_update(repo)
        await websocket.send_json(update)
        last_send = time.monotonic()

        # Keep connection open, wait for client messages or disconnect
        while True:
            # Wait for a ping/request from client before sending next update
            await websocket.receive_text()

            # Rate limit: skip if too soon since last update
            elapsed = time.monotonic() - last_send
            if elapsed < _MIN_UPDATE_INTERVAL:
                await asyncio.sleep(_MIN_UPDATE_INTERVAL - elapsed)

            update = await _build_update(repo)
            await websocket.send_json(update)
            last_send = time.monotonic()
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    except Exception as exc:
        logger.debug("WebSocket error: %s", exc)
