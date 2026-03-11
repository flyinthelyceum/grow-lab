"""Immutable data models for the Living Light System.

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
