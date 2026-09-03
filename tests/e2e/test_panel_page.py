"""The panel emulator, against a real database.

The replay endpoint's job is to hand the emulator a paired series on one
bucket grid, so both needles move in step as the scrubber is dragged. That
only means anything against real SQLite — the pairing and the null-filling are
where a mock would hide the behaviour.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from pi.config.schema import MeterChannelConfig, MetersConfig
from pi.dashboard.app import create_app
from pi.data.models import SensorReading
from pi.data.repository import SensorRepository

METERS = MetersConfig(
    enabled=True,
    ph=MeterChannelConfig(sensor_id="ezo_ph", centre=6.0, span=1.0),
    ec=MeterChannelConfig(sensor_id="ezo_ec", centre=1.0, span=1.0, scale=0.001),
)


@pytest.fixture
async def seeded(test_config):
    repo = SensorRepository(test_config.system.db_path)
    await repo.connect()
    yield repo
    await repo.close()


@pytest.fixture
async def client(seeded):
    app = create_app(seeded, meters_config=METERS)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed(repo, sensor_id, unit, minutes_ago_values):
    now = datetime.now(timezone.utc)
    for minutes, value in minutes_ago_values:
        await repo.save_reading(
            SensorReading(
                timestamp=now - timedelta(minutes=minutes),
                sensor_id=sensor_id,
                value=value,
                unit=unit,
            )
        )


class TestPanelPage:
    async def test_page_serves(self, client):
        response = await client.get("/panel")
        assert response.status_code == 200
        assert "Instrument Head" in response.text

    async def test_loads_the_module_not_an_inline_script(self, client):
        """CSP is script-src 'self' with no unsafe-inline."""
        body = (await client.get("/panel")).text
        assert 'type="module"' in body
        assert "panel/panel.js" in body


class TestReplayPairing:
    async def test_channels_share_one_bucket_grid(self, seeded, client):
        """Both needles must advance together as the scrubber moves."""
        await _seed(seeded, "ezo_ph", "pH", [(30, 6.4), (20, 6.1), (10, 5.8)])
        await _seed(
            seeded, "ezo_ec", "uS/cm", [(30, 1400.0), (20, 1100.0), (10, 900.0)]
        )

        data = (await client.get("/api/panel/replay?window=1h")).json()
        assert data["count"] == 3
        for frame in data["frames"]:
            assert frame["ph"] is not None
            assert frame["ec"] is not None

    async def test_frames_are_in_time_order(self, seeded, client):
        await _seed(seeded, "ezo_ph", "pH", [(45, 6.4), (5, 5.9), (25, 6.2)])
        frames = (await client.get("/api/panel/replay?window=1h")).json()["frames"]
        stamps = [f["t"] for f in frames]
        assert stamps == sorted(stamps)

    async def test_a_channel_with_no_reading_carries_null(self, seeded, client):
        """Null is a fault easing home, not a value of zero."""
        await _seed(seeded, "ezo_ph", "pH", [(30, 6.4), (10, 5.8)])
        await _seed(seeded, "ezo_ec", "uS/cm", [(10, 900.0)])

        frames = (await client.get("/api/panel/replay?window=1h")).json()["frames"]
        assert len(frames) == 2
        assert frames[0]["ph"] is not None
        assert frames[0]["ec"] is None  # older bucket, pH only
        assert frames[1]["ec"] is not None

    async def test_readings_outside_the_window_are_excluded(self, seeded, client):
        await _seed(seeded, "ezo_ph", "pH", [(10, 6.1), (600, 7.9)])
        frames = (await client.get("/api/panel/replay?window=1h")).json()["frames"]
        assert len(frames) == 1
        assert frames[0]["ph"] == pytest.approx(6.1)

    async def test_values_are_averaged_within_a_bucket(self, seeded, client):
        """1h buckets are 60s wide; two readings in one bucket average."""
        await _seed(seeded, "ezo_ph", "pH", [(10, 6.0), (10, 7.0)])
        frames = (await client.get("/api/panel/replay?window=1h")).json()["frames"]
        assert len(frames) == 1
        assert frames[0]["ph"] == pytest.approx(6.5)

    async def test_raw_units_are_returned_unscaled(self, seeded, client):
        """The emulator applies `scale` itself, using the shared maths."""
        await _seed(seeded, "ezo_ec", "uS/cm", [(10, 1250.0)])
        frames = (await client.get("/api/panel/replay?window=1h")).json()["frames"]
        assert frames[0]["ec"] == pytest.approx(1250.0)

    async def test_bucket_width_follows_the_window(self, client):
        for window, expected in (("1h", 60), ("24h", 300), ("7d", 1800)):
            data = (await client.get(f"/api/panel/replay?window={window}")).json()
            assert data["bucket_seconds"] == expected
