"""Feature extraction helpers for AS7341 calibration and runtime estimation."""

from __future__ import annotations

from pi.data.models import SensorReading

RAW_CHANNEL_FIELDS = [
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

DEFAULT_FEATURE_NAMES = list(RAW_CHANNEL_FIELDS)


def extract_channel_map(readings: list[SensorReading]) -> dict[str, float]:
    """Pull AS7341 raw channels out of a sensor reading batch."""
    channels = {
        reading.sensor_id: reading.value
        for reading in readings
        if reading.sensor_id in RAW_CHANNEL_FIELDS
    }
    missing = [name for name in RAW_CHANNEL_FIELDS if name not in channels]
    if missing:
        raise ValueError(f"Missing AS7341 channels: {', '.join(missing)}")
    return channels


def build_feature_vector(record: dict[str, object], feature_names: list[str]) -> list[float]:
    return [float(record[name]) for name in feature_names]
