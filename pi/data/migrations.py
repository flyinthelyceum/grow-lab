"""SQLite schema creation and versioning.

Creates tables on first run. Uses a simple version table
to track schema changes for future migrations.
"""

from __future__ import annotations

import logging

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL,
    applied_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_readings_sensor_time
    ON sensor_readings(sensor_id, timestamp);

CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_time
    ON system_events(timestamp);

CREATE TABLE IF NOT EXISTS camera_captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    filepath TEXT NOT NULL,
    filesize_bytes INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- V2: privacy-preserving HTTP access log (Stage 1 security baseline, 2026-04-28).
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER,
    ip_hash TEXT,
    user_agent_hash TEXT,
    referrer TEXT
);

CREATE INDEX IF NOT EXISTS idx_access_log_timestamp
    ON access_log(timestamp);

CREATE INDEX IF NOT EXISTS idx_access_log_ip_hash
    ON access_log(ip_hash);
"""


async def apply_migrations(db: aiosqlite.Connection) -> None:
    """Create tables if they don't exist and record schema version."""
    await db.executescript(SCHEMA_SQL)

    cursor = await db.execute("SELECT MAX(version) FROM schema_version")
    row = await cursor.fetchone()
    current_version = row[0] if row and row[0] is not None else 0

    if current_version < SCHEMA_VERSION:
        await db.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        await db.commit()
        logger.info(
            "Applied schema version %d (was %d)", SCHEMA_VERSION, current_version
        )
    else:
        logger.debug("Schema is up to date (version %d)", current_version)
