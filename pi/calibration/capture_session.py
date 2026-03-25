"""CSV capture session helpers for AS7341 commissioning."""

from __future__ import annotations

import csv
from pathlib import Path

SESSION_HEADER = [
    "timestamp",
    "node_id",
    "fixture_id",
    "fixture_model",
    "calibration_profile_id",
    "operator",
    "sensor_board_id",
    "gain",
    "integration_time",
    "astep",
    "led_pwm_percent",
    "fixture_distance_cm",
    "lateral_offset_cm",
    "reference_ppfd",
    "split",
    "notes",
    "as7341_415nm",
    "as7341_445nm",
    "as7341_480nm",
    "as7341_515nm",
    "as7341_555nm",
    "as7341_590nm",
    "as7341_630nm",
    "as7341_680nm",
    "as7341_clear",
    "as7341_nir",
]


def ensure_session_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SESSION_HEADER)
        writer.writeheader()


def append_capture_row(path: Path, row: dict[str, object]) -> None:
    ensure_session_file(path)
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SESSION_HEADER)
        writer.writerow({key: row.get(key, "") for key in SESSION_HEADER})


def read_capture_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))
