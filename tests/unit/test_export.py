"""Tests for CSV/JSON export utilities."""

import csv
import io
import json
from datetime import datetime, timezone

from pi.data.export import (
    events_to_csv,
    events_to_json,
    readings_to_csv,
    readings_to_json,
)
from pi.data.models import SensorReading, SystemEvent


def _make_readings() -> list[SensorReading]:
    base = datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc)
    return [
        SensorReading(timestamp=base, sensor_id="temp", value=22.5, unit="°C"),
        SensorReading(
            timestamp=base, sensor_id="humidity", value=55.0, unit="%", metadata='{"x": 1}'
        ),
    ]


def _make_events() -> list[SystemEvent]:
    base = datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc)
    return [
        SystemEvent(timestamp=base, event_type="irrigation", description="pulse"),
    ]


class TestReadingsExport:
    def test_csv_has_header_and_rows(self):
        csv_str = readings_to_csv(_make_readings())
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert rows[0] == ["timestamp", "sensor_id", "value", "unit", "metadata"]
        assert len(rows) == 3  # header + 2 data rows
        assert rows[1][1] == "temp"
        assert rows[1][2] == "22.5"

    def test_json_is_valid(self):
        json_str = readings_to_json(_make_readings())
        data = json.loads(json_str)
        assert len(data) == 2
        assert data[0]["sensor_id"] == "temp"
        assert data[0]["value"] == 22.5
        assert data[1]["metadata"] == '{"x": 1}'

    def test_empty_list(self):
        assert readings_to_csv([]) == "timestamp,sensor_id,value,unit,metadata\r\n"
        assert json.loads(readings_to_json([])) == []


class TestEventsExport:
    def test_csv_has_header_and_rows(self):
        csv_str = events_to_csv(_make_events())
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert rows[0] == ["timestamp", "event_type", "description", "metadata"]
        assert len(rows) == 2

    def test_json_is_valid(self):
        json_str = events_to_json(_make_events())
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["event_type"] == "irrigation"
