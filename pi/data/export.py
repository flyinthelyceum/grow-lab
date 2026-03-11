"""CSV and JSON export utilities for sensor data."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from pi.data.models import SensorReading, SystemEvent


def readings_to_csv(readings: list[SensorReading]) -> str:
    """Export sensor readings to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "sensor_id", "value", "unit", "metadata"])
    for r in readings:
        writer.writerow([r.iso_timestamp, r.sensor_id, r.value, r.unit, r.metadata])
    return output.getvalue()


def readings_to_json(readings: list[SensorReading]) -> str:
    """Export sensor readings to JSON string."""
    data = [
        {
            "timestamp": r.iso_timestamp,
            "sensor_id": r.sensor_id,
            "value": r.value,
            "unit": r.unit,
            "metadata": r.metadata,
        }
        for r in readings
    ]
    return json.dumps(data, indent=2)


def events_to_csv(events: list[SystemEvent]) -> str:
    """Export system events to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "event_type", "description", "metadata"])
    for e in events:
        writer.writerow([e.iso_timestamp, e.event_type, e.description, e.metadata])
    return output.getvalue()


def events_to_json(events: list[SystemEvent]) -> str:
    """Export system events to JSON string."""
    data = [
        {
            "timestamp": e.iso_timestamp,
            "event_type": e.event_type,
            "description": e.description,
            "metadata": e.metadata,
        }
        for e in events
    ]
    return json.dumps(data, indent=2)
