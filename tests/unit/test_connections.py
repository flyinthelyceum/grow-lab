"""Tests for the WebSocket connection manager."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from pi.dashboard.connections import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


class TestConnectionManager:
    async def test_connect_adds_websocket(self, manager):
        ws = AsyncMock()
        await manager.connect(ws)
        assert ws in manager.active_connections

    async def test_disconnect_removes_websocket(self, manager):
        ws = AsyncMock()
        await manager.connect(ws)
        manager.disconnect(ws)
        assert ws not in manager.active_connections

    async def test_disconnect_ignores_unknown(self, manager):
        ws = AsyncMock()
        manager.disconnect(ws)  # Should not raise

    async def test_broadcast_json_sends_to_all(self, manager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1)
        await manager.connect(ws2)

        payload = {"type": "alert", "message": "test"}
        await manager.broadcast_json(payload)

        ws1.send_json.assert_called_once_with(payload)
        ws2.send_json.assert_called_once_with(payload)

    async def test_broadcast_removes_failed_connections(self, manager):
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_json.side_effect = Exception("connection closed")

        await manager.connect(ws_good)
        await manager.connect(ws_bad)

        await manager.broadcast_json({"type": "test"})

        # Bad connection should be removed
        assert ws_bad not in manager.active_connections
        assert ws_good in manager.active_connections

    async def test_broadcast_to_empty(self, manager):
        # Should not raise
        await manager.broadcast_json({"type": "test"})
