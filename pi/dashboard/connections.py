"""WebSocket connection manager for server-push broadcasts.

Maintains a set of active WebSocket connections and provides
broadcast capability for pushing events (alerts, etc.) to all
connected dashboard clients.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for broadcast messaging."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def active_connections(self) -> set[WebSocket]:
        """Currently connected WebSocket clients."""
        return self._connections

    async def connect(self, websocket: WebSocket) -> None:
        """Register a new WebSocket connection."""
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self._connections.discard(websocket)

    async def broadcast_json(self, payload: dict) -> None:
        """Send a JSON payload to all connected clients.

        Silently removes connections that fail to send.
        """
        failed: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                failed.append(ws)

        for ws in failed:
            self._connections.discard(ws)
            logger.debug("Removed failed WebSocket connection")
