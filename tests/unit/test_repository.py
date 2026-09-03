"""Tests for the SQLite repository."""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from pi.data.models import CameraCapture, SensorReading, SystemEvent
from pi.data.repository import SensorRepository


class TestSaveAndRetrieveReadings:
    async def test_save_and_get_latest(self, repo: SensorRepository, sample_reading: SensorReading):
        await repo.save_reading(sample_reading)
        latest = await repo.get_latest("bme280_temperature")
        assert latest is not None
        assert latest.value == 23.5
        assert latest.unit == "°C"
        assert latest.sensor_id == "bme280_temperature"

    async def test_get_latest_returns_none_for_unknown(self, repo: SensorRepository):
        result = await repo.get_latest("nonexistent")
        assert result is None

    async def test_count_readings(self, repo: SensorRepository, sample_reading: SensorReading):
        assert await repo.count_readings() == 0
        await repo.save_reading(sample_reading)
        assert await repo.count_readings() == 1
        assert await repo.count_readings("bme280_temperature") == 1
        assert await repo.count_readings("other") == 0

    async def test_get_range(self, repo: SensorRepository):
        base = datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(5):
            reading = SensorReading(
                timestamp=base + timedelta(minutes=i * 10),
                sensor_id="bme280_temperature",
                value=20.0 + i,
                unit="°C",
            )
            await repo.save_reading(reading)

        start = base + timedelta(minutes=10)
        end = base + timedelta(minutes=30)
        results = await repo.get_range("bme280_temperature", start, end)
        assert len(results) == 3
        assert results[0].value == 21.0
        assert results[-1].value == 23.0

    async def test_get_all_readings_with_limit(self, repo: SensorRepository):
        base = datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(10):
            await repo.save_reading(
                SensorReading(
                    timestamp=base + timedelta(minutes=i),
                    sensor_id="test",
                    value=float(i),
                    unit="x",
                )
            )
        results = await repo.get_all_readings(limit=3)
        assert len(results) == 3
        # Most recent first
        assert results[0].value == 9.0


class TestEvents:
    async def test_save_and_get_events(self, repo: SensorRepository, sample_event: SystemEvent):
        await repo.save_event(sample_event)
        events = await repo.get_events()
        assert len(events) == 1
        assert events[0].event_type == "irrigation"
        assert events[0].description == "Pump pulse 10s"


class TestCaptures:
    async def test_save_and_get_captures(self, repo: SensorRepository):
        capture = CameraCapture(
            timestamp=datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc),
            filepath="/data/images/test.jpg",
            filesize_bytes=500000,
        )
        await repo.save_capture(capture)
        captures = await repo.get_captures()
        assert len(captures) == 1
        assert captures[0].filepath == "/data/images/test.jpg"


class TestDbInfo:
    async def test_db_info_empty(self, repo: SensorRepository):
        info = await repo.get_db_info()
        assert info["sensor_readings"] == 0
        assert info["system_events"] == 0
        assert info["camera_captures"] == 0

    async def test_db_info_with_data(self, repo: SensorRepository, sample_reading, sample_event):
        await repo.save_reading(sample_reading)
        await repo.save_event(sample_event)
        info = await repo.get_db_info()
        assert info["sensor_readings"] == 1
        assert info["system_events"] == 1

    async def test_get_sensor_ids(self, repo: SensorRepository):
        base = datetime(2026, 3, 11, tzinfo=timezone.utc)
        await repo.save_reading(
            SensorReading(timestamp=base, sensor_id="bme280_temperature", value=22.0, unit="°C")
        )
        await repo.save_reading(
            SensorReading(timestamp=base, sensor_id="bme280_humidity", value=55.0, unit="%")
        )
        ids = await repo.get_sensor_ids()
        assert ids == ["bme280_humidity", "bme280_temperature"]


class TestConnectionLifecycle:
    async def test_not_connected_raises(self, test_config):
        repo = SensorRepository(test_config.system.db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await repo.get_db_info()

    async def test_close_and_reopen(self, test_config):
        repo = SensorRepository(test_config.system.db_path)
        await repo.connect()
        await repo.close()
        # Can reconnect
        await repo.connect()
        info = await repo.get_db_info()
        assert info["sensor_readings"] == 0
        await repo.close()


async def test_busy_timeout_is_set(repo: SensorRepository):
    """Overlapping writes must wait, not raise 'database is locked' instantly.

    The collector and dashboard both write to this database; a bare
    default timeout is what surfaced the lock error that killed polling.
    """
    from pi.data.repository import BUSY_TIMEOUT_MS

    cursor = await repo.db.execute("PRAGMA busy_timeout")
    row = await cursor.fetchone()
    assert row[0] == BUSY_TIMEOUT_MS


class TestConnectionCannotGetStuck:
    """Regression cover for the 2026-08-25 frozen-dashboard incident.

    One access_log INSERT lost a race and raised "database is locked".
    The middleware caught it but nothing rolled back, so the implicit
    transaction stayed open on the dashboard's long-lived connection.
    That pinned its read snapshot for 33 hours -- every panel served
    data from the moment of the failure -- blocked WAL checkpointing,
    and left the connection permanently unable to write.
    """

    async def test_connection_is_autocommit(self, repo: SensorRepository):
        """No transaction may span an await, so none can be stranded."""
        assert repo.db.isolation_level is None

    async def test_failed_write_leaves_connection_usable(
        self, repo: SensorRepository
    ):
        """After a write error the connection must still see fresh data."""
        with pytest.raises(sqlite3.Error):
            await repo.db.execute("INSERT INTO access_log (nope) VALUES (1)")

        reading = SensorReading(
            timestamp=datetime.now(timezone.utc),
            sensor_id="canary",
            value=42.0,
            unit="x",
        )
        await repo.save_reading(reading)
        latest = await repo.get_latest("canary")
        assert latest is not None and latest.value == 42.0

    async def test_reads_are_not_pinned_to_a_stale_snapshot(
        self, repo: SensorRepository
    ):
        """A long-lived connection must observe writes made after a failure."""
        with pytest.raises(sqlite3.Error):
            await repo.db.execute("SELECT * FROM does_not_exist")

        before = await repo.count_readings()
        await repo.save_reading(
            SensorReading(
                timestamp=datetime.now(timezone.utc),
                sensor_id="canary2",
                value=1.0,
                unit="x",
            )
        )
        assert await repo.count_readings() == before + 1


class TestControlState:
    """The cross-process control channel, against a real database.

    These matter more than the mocked service tests: the whole point of the
    table is that two separate processes agree through it, so the round-trip
    has to hold in SQLite, not just in a mock.
    """

    async def test_unset_control_is_none(self, repo: SensorRepository):
        assert await repo.get_control("fan.override_duty") is None

    async def test_round_trip(self, repo: SensorRepository):
        await repo.set_control("fan.override_duty", "60", updated_by="admin")
        entry = await repo.get_control("fan.override_duty")
        assert entry is not None
        assert entry.value == "60"
        assert entry.updated_by == "admin"
        assert entry.expires_at is None

    async def test_upsert_replaces_rather_than_queues(self, repo: SensorRepository):
        """Desired state, not a command backlog."""
        await repo.set_control("fan.override_duty", "60")
        await repo.set_control("fan.override_duty", "80")
        await repo.set_control("fan.override_duty", "20")
        assert (await repo.get_control("fan.override_duty")).value == "20"
        assert len(await repo.get_all_control()) == 1

    async def test_ttl_sets_an_expiry_in_the_future(self, repo: SensorRepository):
        entry = await repo.set_control("fan.override_duty", "0", ttl_seconds=600)
        assert entry.expires_at is not None
        assert entry.expires_at > entry.updated_at
        stored = await repo.get_control("fan.override_duty")
        assert stored.expires_at is not None
        assert not stored.is_expired(datetime.now(timezone.utc))

    async def test_expired_entry_reads_as_auto(self, repo: SensorRepository):
        await repo.set_control("fan.override_duty", "0", ttl_seconds=1)
        stored = await repo.get_control("fan.override_duty")
        later = datetime.now(timezone.utc) + timedelta(seconds=5)
        assert stored.is_expired(later)
        assert stored.effective_value(later) is None

    async def test_clear_keeps_the_row_and_drops_the_expiry(
        self, repo: SensorRepository
    ):
        await repo.set_control("fan.override_duty", "60", ttl_seconds=600)
        await repo.clear_control("fan.override_duty", updated_by="admin")
        entry = await repo.get_control("fan.override_duty")
        assert entry is not None  # row kept, so updated_at still records the change
        assert entry.value is None
        assert entry.expires_at is None

    async def test_get_all_control(self, repo: SensorRepository):
        await repo.set_control("fan.override_duty", "60")
        await repo.set_control("meters.ph.override", "0.5")
        rows = await repo.get_all_control()
        assert set(rows) == {"fan.override_duty", "meters.ph.override"}
        assert rows["meters.ph.override"].value == "0.5"

    async def test_clearing_an_unset_control_is_fine(self, repo: SensorRepository):
        entry = await repo.clear_control("meters.ec.override")
        assert entry.value is None

    async def test_survives_reconnect(self, repo: SensorRepository, test_config):
        """A restart of either process must not lose the desired state."""
        await repo.set_control("fan.override_duty", "45")
        await repo.close()

        fresh = SensorRepository(test_config.system.db_path)
        await fresh.connect()
        try:
            assert (await fresh.get_control("fan.override_duty")).value == "45"
        finally:
            await fresh.close()
        await repo.connect()  # restore for fixture teardown


class TestSchemaUpgrade:
    async def test_v2_database_gains_control_state_in_place(self, tmp_path):
        """The Pi has a live v2 database — the upgrade must not disturb it."""
        import sqlite3 as sync_sqlite3

        from pi.data.migrations import SCHEMA_SQL, SCHEMA_VERSION

        db_path = tmp_path / "v2.db"
        v2_sql = SCHEMA_SQL.split("-- V3:")[0]

        conn = sync_sqlite3.connect(db_path)
        conn.executescript(v2_sql)
        conn.execute("INSERT INTO schema_version (version) VALUES (2)")
        conn.execute(
            """INSERT INTO sensor_readings (timestamp, sensor_id, value, unit)
               VALUES ('2026-09-01T00:00:00+00:00', 'ezo_ph', 6.4, 'pH')"""
        )
        conn.commit()
        conn.close()

        upgraded = SensorRepository(db_path)
        await upgraded.connect()
        try:
            # Existing data survives.
            reading = await upgraded.get_latest("ezo_ph")
            assert reading is not None and reading.value == 6.4

            # The new channel works.
            await upgraded.set_control("fan.override_duty", "42")
            assert (await upgraded.get_control("fan.override_duty")).value == "42"
        finally:
            await upgraded.close()

        conn = sync_sqlite3.connect(db_path)
        try:
            versions = [
                r[0]
                for r in conn.execute("SELECT version FROM schema_version ORDER BY version")
            ]
            assert versions == [2, SCHEMA_VERSION]
        finally:
            conn.close()
