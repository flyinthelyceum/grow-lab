"""Tests for the async polling service."""

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import AppConfig
from pi.data.models import SensorReading
from pi.data.repository import SensorRepository
from pi.discovery.registry import SensorRegistry, SensorStatus
from pi.services.polling import PollingService


def _make_mock_driver(sensor_id: str, readings: list[SensorReading] | None = None):
    """Create a mock sensor driver."""
    driver = AsyncMock()
    driver.sensor_id = sensor_id
    if readings is not None:
        driver.read.return_value = readings
    else:
        driver.read.return_value = [
            SensorReading(
                timestamp=datetime.now(timezone.utc),
                sensor_id=f"{sensor_id}_temperature",
                value=22.5,
                unit="°C",
            )
        ]
    return driver


def _make_registry(*drivers) -> SensorRegistry:
    """Create a registry with the given mock drivers."""
    statuses = tuple(
        SensorStatus(d.sensor_id, True, d, "detected") for d in drivers
    )
    return SensorRegistry(statuses)


class TestPollingService:
    async def test_start_and_stop(self, repo: SensorRepository):
        driver = _make_mock_driver("bme280")
        registry = _make_registry(driver)
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        assert not poller.is_running

        await poller.start()
        assert poller.is_running

        # Let it poll at least once
        await asyncio.sleep(0.1)

        await poller.stop()
        assert not poller.is_running

        # Verify readings were saved
        count = await repo.count_readings()
        assert count >= 1

    async def test_no_sensors_available(self, repo: SensorRepository):
        registry = SensorRegistry(())
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        await poller.start()
        assert poller.is_running

        await asyncio.sleep(0.05)
        await poller.stop()

        # No readings should be saved
        count = await repo.count_readings()
        assert count == 0

    async def test_multiple_sensors(self, repo: SensorRepository):
        driver1 = _make_mock_driver("bme280")
        driver2 = _make_mock_driver("soil_moisture", [
            SensorReading(
                timestamp=datetime.now(timezone.utc),
                sensor_id="soil_moisture_raw",
                value=450.0,
                unit="raw",
            )
        ])
        registry = _make_registry(driver1, driver2)
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        await poller.start()
        await asyncio.sleep(0.1)
        await poller.stop()

        # Both sensors should have saved readings
        ids = await repo.get_sensor_ids()
        assert len(ids) >= 2

    async def test_sensor_failure_continues_polling(self, repo: SensorRepository):
        driver = _make_mock_driver("bme280")
        # First call fails, second succeeds, third fails
        driver.read.side_effect = [
            Exception("I2C error"),
            [SensorReading(
                timestamp=datetime.now(timezone.utc),
                sensor_id="bme280_temperature",
                value=23.0,
                unit="°C",
            )],
            Exception("I2C error again"),
        ]
        registry = _make_registry(driver)
        config = AppConfig()

        poller = PollingService(registry, repo, config)

        # Patch the poll loop's sleep to not actually wait
        original_sleep = asyncio.sleep

        async def fast_sleep(delay):
            await original_sleep(0.01)

        with patch("pi.services.polling.asyncio.sleep", side_effect=fast_sleep):
            await poller.start()
            await original_sleep(0.1)
            await poller.stop()

        # Should have at least the one successful reading
        count = await repo.count_readings()
        assert count >= 1

    async def test_sensor_returns_empty_list(self, repo: SensorRepository):
        driver = _make_mock_driver("bme280", readings=[])
        registry = _make_registry(driver)
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        await poller.start()
        await asyncio.sleep(0.1)
        await poller.stop()

        count = await repo.count_readings()
        assert count == 0

    async def test_as7341_multi_reading_payload_is_persisted(self, repo: SensorRepository):
        now = datetime.now(timezone.utc)
        driver = _make_mock_driver("as7341", [
            SensorReading(timestamp=now, sensor_id="as7341_lux", value=123.4, unit="lux"),
            SensorReading(timestamp=now, sensor_id="as7341_415nm", value=10.0, unit="raw"),
            SensorReading(timestamp=now, sensor_id="as7341_445nm", value=20.0, unit="raw"),
            SensorReading(timestamp=now, sensor_id="as7341_clear", value=30.0, unit="raw"),
            SensorReading(timestamp=now, sensor_id="as7341_nir", value=40.0, unit="raw"),
        ])
        registry = _make_registry(driver)
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        await poller.start()
        await asyncio.sleep(0.1)
        await poller.stop()

        sensor_ids = set(await repo.get_sensor_ids())
        assert {
            "as7341_lux",
            "as7341_415nm",
            "as7341_445nm",
            "as7341_clear",
            "as7341_nir",
        }.issubset(sensor_ids)

    async def test_double_start_warns(self, repo: SensorRepository):
        driver = _make_mock_driver("bme280")
        registry = _make_registry(driver)
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        await poller.start()
        # Second start should be a no-op
        await poller.start()
        await poller.stop()


class TestPollingInterval:
    async def test_uses_config_interval(self, repo: SensorRepository):
        driver = _make_mock_driver("bme280")
        registry = _make_registry(driver)
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        interval = poller._get_interval("bme280")
        assert interval == 120  # default from SensorEntry

    async def test_unknown_sensor_uses_default(self, repo: SensorRepository):
        driver = _make_mock_driver("unknown_sensor")
        registry = _make_registry(driver)
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        interval = poller._get_interval("unknown_sensor")
        assert interval == 120


class TestPollOnce:
    async def test_poll_once_success(self, repo: SensorRepository):
        now = datetime.now(timezone.utc)
        readings = [
            SensorReading(timestamp=now, sensor_id="test", value=1.0, unit="x")
        ]
        driver = _make_mock_driver("test", readings)
        registry = _make_registry(driver)
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        result = await poller._poll_once(driver)
        assert len(result) == 1
        assert result[0].value == 1.0

    async def test_poll_once_exception(self, repo: SensorRepository):
        driver = _make_mock_driver("test")
        driver.read.side_effect = OSError("bus error")
        registry = _make_registry(driver)
        config = AppConfig()

        poller = PollingService(registry, repo, config)
        result = await poller._poll_once(driver)
        assert result == []


class TestPollLoopSurvivesRepositoryFailure:
    """Regression cover for the July/August 2026 silent-collector outages.

    A transient `database is locked` from save_reading escaped _poll_loop's
    only handler (asyncio.CancelledError) and killed the task. The process
    stayed alive and kept feeding the systemd watchdog, so the collector was
    dead for weeks with no failure signal anywhere.
    """

    async def test_write_failure_does_not_kill_the_loop(
        self, repo: SensorRepository
    ):
        driver = _make_mock_driver("bme280")
        registry = _make_registry(driver)

        saved: list[SensorReading] = []
        calls = {"n": 0}

        async def flaky_save(reading: SensorReading) -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.OperationalError("database is locked")
            saved.append(reading)

        repo.save_reading = flaky_save  # type: ignore[method-assign]

        poller = PollingService(registry, repo, AppConfig())
        with patch.object(PollingService, "_get_interval", return_value=0):
            await poller.start()
            for _ in range(50):
                await asyncio.sleep(0)
                if saved:
                    break
            task_alive = [t for t in poller._tasks if not t.done()]
            await poller.stop()

        assert calls["n"] >= 2, "loop stopped calling save_reading after the failure"
        assert saved, "loop never recovered to save a reading"
        assert task_alive, "poll task died on a repository write failure"

    async def test_write_failure_is_logged(self, repo: SensorRepository, caplog):
        driver = _make_mock_driver("bme280")
        registry = _make_registry(driver)

        async def always_fails(reading: SensorReading) -> None:
            raise sqlite3.OperationalError("database is locked")

        repo.save_reading = always_fails  # type: ignore[method-assign]

        poller = PollingService(registry, repo, AppConfig())
        with caplog.at_level(logging.ERROR):
            with patch.object(PollingService, "_get_interval", return_value=0):
                await poller.start()
                for _ in range(20):
                    await asyncio.sleep(0)
                await poller.stop()

        assert any(
            "database is locked" in r.message or "database is locked" in str(r.args)
            for r in caplog.records
        ), "write failure was swallowed without an ERROR log"
