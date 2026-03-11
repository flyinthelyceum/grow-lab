"""Shared test fixtures — mock hardware, in-memory DB, config."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio

from pi.config.schema import AppConfig, SystemConfig
from pi.data.models import SensorReading, SystemEvent
from pi.data.repository import SensorRepository


@pytest.fixture
def sample_reading() -> SensorReading:
    return SensorReading(
        timestamp=datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc),
        sensor_id="bme280_temperature",
        value=23.5,
        unit="°C",
        metadata='{"location": "canopy"}',
    )


@pytest.fixture
def sample_event() -> SystemEvent:
    return SystemEvent(
        timestamp=datetime(2026, 3, 11, 12, 0, 0, tzinfo=timezone.utc),
        event_type="irrigation",
        description="Pump pulse 10s",
        metadata=None,
    )


@pytest.fixture
def test_config(tmp_path: Path) -> AppConfig:
    """AppConfig pointing to a temp directory for tests."""
    db_path = tmp_path / "test.db"
    return AppConfig(
        system=SystemConfig(
            log_level="DEBUG",
            data_dir=tmp_path,
            db_path=db_path,
        )
    )


@pytest_asyncio.fixture
async def repo(test_config: AppConfig) -> SensorRepository:
    """Connected repository using an in-memory-like temp database."""
    repository = SensorRepository(test_config.system.db_path)
    await repository.connect()
    yield repository
    await repository.close()
