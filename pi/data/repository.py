"""SQLite repository for sensor readings, events, and camera captures.

All queries are parameterized. All returned objects are frozen dataclasses.
Business logic never constructs SQL directly — it goes through this module.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import aiosqlite

from pi.data.migrations import apply_migrations
from pi.data.models import CameraCapture, SensorReading, SystemEvent

logger = logging.getLogger(__name__)


def _parse_dt(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str)


class SensorRepository:
    """Async SQLite repository wrapping all data access."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the database and apply migrations."""
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await apply_migrations(self._db)
        logger.info("Database connected: %s", self._db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Repository not connected. Call connect() first.")
        return self._db

    # -- Sensor Readings --

    async def save_reading(self, reading: SensorReading) -> None:
        await self.db.execute(
            """INSERT INTO sensor_readings (timestamp, sensor_id, value, unit, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (
                reading.iso_timestamp,
                reading.sensor_id,
                reading.value,
                reading.unit,
                reading.metadata,
            ),
        )
        await self.db.commit()

    async def get_latest(self, sensor_id: str) -> SensorReading | None:
        cursor = await self.db.execute(
            """SELECT timestamp, sensor_id, value, unit, metadata
               FROM sensor_readings
               WHERE sensor_id = ?
               ORDER BY timestamp DESC LIMIT 1""",
            (sensor_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return SensorReading(
            timestamp=_parse_dt(row[0]),
            sensor_id=row[1],
            value=row[2],
            unit=row[3],
            metadata=row[4],
        )

    async def get_range(
        self,
        sensor_id: str,
        start: datetime,
        end: datetime,
    ) -> list[SensorReading]:
        cursor = await self.db.execute(
            """SELECT timestamp, sensor_id, value, unit, metadata
               FROM sensor_readings
               WHERE sensor_id = ? AND timestamp >= ? AND timestamp <= ?
               ORDER BY timestamp ASC""",
            (sensor_id, start.isoformat(), end.isoformat()),
        )
        rows = await cursor.fetchall()
        return [
            SensorReading(
                timestamp=_parse_dt(r[0]),
                sensor_id=r[1],
                value=r[2],
                unit=r[3],
                metadata=r[4],
            )
            for r in rows
        ]

    async def get_all_readings(
        self, limit: int = 100, offset: int = 0
    ) -> list[SensorReading]:
        cursor = await self.db.execute(
            """SELECT timestamp, sensor_id, value, unit, metadata
               FROM sensor_readings
               ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [
            SensorReading(
                timestamp=_parse_dt(r[0]),
                sensor_id=r[1],
                value=r[2],
                unit=r[3],
                metadata=r[4],
            )
            for r in rows
        ]

    async def count_readings(self, sensor_id: str | None = None) -> int:
        if sensor_id is not None:
            cursor = await self.db.execute(
                "SELECT COUNT(*) FROM sensor_readings WHERE sensor_id = ?",
                (sensor_id,),
            )
        else:
            cursor = await self.db.execute("SELECT COUNT(*) FROM sensor_readings")
        row = await cursor.fetchone()
        return row[0] if row else 0

    # -- System Events --

    async def save_event(self, event: SystemEvent) -> None:
        await self.db.execute(
            """INSERT INTO system_events (timestamp, event_type, description, metadata)
               VALUES (?, ?, ?, ?)""",
            (
                event.iso_timestamp,
                event.event_type,
                event.description,
                event.metadata,
            ),
        )
        await self.db.commit()

    async def get_events(self, limit: int = 50) -> list[SystemEvent]:
        cursor = await self.db.execute(
            """SELECT timestamp, event_type, description, metadata
               FROM system_events
               ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            SystemEvent(
                timestamp=_parse_dt(r[0]),
                event_type=r[1],
                description=r[2],
                metadata=r[3],
            )
            for r in rows
        ]

    # -- Camera Captures --

    async def save_capture(self, capture: CameraCapture) -> None:
        await self.db.execute(
            """INSERT INTO camera_captures (timestamp, filepath, filesize_bytes)
               VALUES (?, ?, ?)""",
            (capture.iso_timestamp, capture.filepath, capture.filesize_bytes),
        )
        await self.db.commit()

    async def get_captures(self, limit: int = 50) -> list[CameraCapture]:
        cursor = await self.db.execute(
            """SELECT timestamp, filepath, filesize_bytes
               FROM camera_captures
               ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            CameraCapture(
                timestamp=_parse_dt(r[0]),
                filepath=r[1],
                filesize_bytes=r[2],
            )
            for r in rows
        ]

    # -- Stats --

    async def get_sensor_ids(self) -> list[str]:
        cursor = await self.db.execute(
            "SELECT DISTINCT sensor_id FROM sensor_readings ORDER BY sensor_id"
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

    # Allowlist of table names — safe to interpolate (never from user input)
    _TABLE_NAMES = ("sensor_readings", "system_events", "camera_captures")

    # Pre-built queries — no f-string at runtime
    _COUNT_QUERIES = {t: f"SELECT COUNT(*) FROM {t}" for t in _TABLE_NAMES}

    async def get_db_info(self) -> dict[str, int]:
        """Return row counts for each table."""
        info: dict[str, int] = {}
        for table, query in self._COUNT_QUERIES.items():
            cursor = await self.db.execute(query)
            row = await cursor.fetchone()
            info[table] = row[0] if row else 0
        return info

    # --- Stage 1 security baseline: privacy-preserving access log ---

    async def log_access(
        self,
        *,
        timestamp: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int,
        ip_hash: str,
        ua_hash: str,
        referrer: str,
    ) -> None:
        """Insert one row into access_log.

        Called by RequestLoggerMiddleware. All identifying fields
        (ip_hash, ua_hash) are pre-hashed by the caller; this method
        does no hashing itself.
        """
        await self.db.execute(
            "INSERT INTO access_log("
            "timestamp, method, path, status_code, duration_ms,"
            " ip_hash, user_agent_hash, referrer"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                timestamp,
                method,
                path,
                status_code,
                duration_ms,
                ip_hash,
                ua_hash,
                referrer,
            ),
        )
        await self.db.commit()

    async def access_count_since(self, since_iso: str) -> int:
        """Count total access_log rows since `since_iso` (inclusive)."""
        cursor = await self.db.execute(
            "SELECT COUNT(*) FROM access_log WHERE timestamp >= ?",
            (since_iso,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def access_distinct_ips_since(self, since_iso: str) -> int:
        """Count distinct ip_hash values since `since_iso`."""
        cursor = await self.db.execute(
            "SELECT COUNT(DISTINCT ip_hash) FROM access_log"
            " WHERE timestamp >= ? AND ip_hash != ''",
            (since_iso,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def access_distinct_uas_since(self, since_iso: str) -> int:
        """Count distinct user_agent_hash values since `since_iso`."""
        cursor = await self.db.execute(
            "SELECT COUNT(DISTINCT user_agent_hash) FROM access_log"
            " WHERE timestamp >= ? AND user_agent_hash != ''",
            (since_iso,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def access_top_paths_since(
        self, since_iso: str, limit: int = 10
    ) -> list[tuple[str, int]]:
        """Return [(path, count), ...] descending since `since_iso`."""
        cursor = await self.db.execute(
            "SELECT path, COUNT(*) AS n FROM access_log"
            " WHERE timestamp >= ?"
            " GROUP BY path ORDER BY n DESC LIMIT ?",
            (since_iso, limit),
        )
        rows = await cursor.fetchall()
        return [(r[0], int(r[1])) for r in rows]

    async def access_recent(self, limit: int = 50) -> list[dict]:
        """Return the most recent N access_log rows as dicts."""
        cursor = await self.db.execute(
            "SELECT timestamp, method, path, status_code, duration_ms,"
            " ip_hash, user_agent_hash"
            " FROM access_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "timestamp": r[0],
                "method": r[1],
                "path": r[2],
                "status_code": r[3],
                "duration_ms": r[4],
                "ip_hash": r[5],
                "user_agent_hash": r[6],
            }
            for r in rows
        ]
