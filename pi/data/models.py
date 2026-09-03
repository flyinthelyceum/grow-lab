"""Immutable data models for GROWLAB.

All models are frozen dataclasses — no mutation after creation.
These flow through the entire pipeline: drivers -> repository -> dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SensorReading:
    """A single sensor measurement at a point in time."""

    timestamp: datetime
    sensor_id: str
    value: float
    unit: str
    metadata: str | None = None

    @property
    def iso_timestamp(self) -> str:
        return self.timestamp.isoformat()


@dataclass(frozen=True)
class SystemEvent:
    """A discrete system event (irrigation, calibration, config change, etc.)."""

    timestamp: datetime
    event_type: str
    description: str | None = None
    metadata: str | None = None

    @property
    def iso_timestamp(self) -> str:
        return self.timestamp.isoformat()


@dataclass(frozen=True)
class CameraCapture:
    """Record of a captured image."""

    timestamp: datetime
    filepath: str
    filesize_bytes: int | None = None

    @property
    def iso_timestamp(self) -> str:
        return self.timestamp.isoformat()


@dataclass(frozen=True)
class ControlEntry:
    """One desired-state row from the cross-process control channel.

    The dashboard writes these; the orchestrator reconciles toward them. A
    ``value`` of None means "no override — follow the automatic behaviour",
    which is how a control is returned to auto without deleting its row.
    """

    key: str
    value: str | None
    updated_at: datetime
    expires_at: datetime | None = None
    updated_by: str | None = None

    def is_expired(self, now: datetime) -> bool:
        """True once a bounded override has lapsed."""
        return self.expires_at is not None and now >= self.expires_at

    def effective_value(self, now: datetime) -> str | None:
        """The value to act on: None once expired, so a lapse reads as auto."""
        return None if self.is_expired(now) else self.value
