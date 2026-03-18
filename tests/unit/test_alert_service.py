"""Tests for the threshold alerting service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from pi.data.models import SensorReading, SystemEvent
from pi.services.alerts import (
    AlertService,
    ThresholdRule,
    classify_reading,
)


def _reading(sensor_id: str, value: float, unit: str = "") -> SensorReading:
    return SensorReading(
        timestamp=datetime.now(timezone.utc),
        sensor_id=sensor_id,
        value=value,
        unit=unit,
    )


# --- classify_reading ---

class TestClassifyReading:
    def test_normal_range(self):
        rule = ThresholdRule(
            sensor_id="bme280_temperature",
            warning_low=65.0,
            warning_high=80.0,
            critical_low=60.0,
            critical_high=85.0,
        )
        assert classify_reading(72.0, rule) == "normal"

    def test_warning_low(self):
        rule = ThresholdRule(
            sensor_id="bme280_temperature",
            warning_low=65.0,
            warning_high=80.0,
            critical_low=60.0,
            critical_high=85.0,
        )
        assert classify_reading(63.0, rule) == "warning"

    def test_warning_high(self):
        rule = ThresholdRule(
            sensor_id="bme280_temperature",
            warning_low=65.0,
            warning_high=80.0,
            critical_low=60.0,
            critical_high=85.0,
        )
        assert classify_reading(82.0, rule) == "warning"

    def test_critical_low(self):
        rule = ThresholdRule(
            sensor_id="bme280_temperature",
            warning_low=65.0,
            warning_high=80.0,
            critical_low=60.0,
            critical_high=85.0,
        )
        assert classify_reading(58.0, rule) == "critical"

    def test_critical_high(self):
        rule = ThresholdRule(
            sensor_id="bme280_temperature",
            warning_low=65.0,
            warning_high=80.0,
            critical_low=60.0,
            critical_high=85.0,
        )
        assert classify_reading(87.0, rule) == "critical"

    def test_boundary_warning_low(self):
        rule = ThresholdRule(
            sensor_id="bme280_temperature",
            warning_low=65.0,
            warning_high=80.0,
            critical_low=60.0,
            critical_high=85.0,
        )
        # At exactly warning_low, should be normal (inside the band)
        assert classify_reading(65.0, rule) == "normal"

    def test_boundary_critical_low(self):
        rule = ThresholdRule(
            sensor_id="bme280_temperature",
            warning_low=65.0,
            warning_high=80.0,
            critical_low=60.0,
            critical_high=85.0,
        )
        # At exactly critical_low, should be warning (not yet critical)
        assert classify_reading(60.0, rule) == "warning"


# --- ThresholdRule ---

class TestThresholdRule:
    def test_immutable(self):
        rule = ThresholdRule(
            sensor_id="test",
            warning_low=0.0,
            warning_high=100.0,
            critical_low=-10.0,
            critical_high=110.0,
        )
        with pytest.raises(AttributeError):
            rule.sensor_id = "changed"

    def test_optional_convert_fn(self):
        fn = lambda x: x * 2
        rule = ThresholdRule(
            sensor_id="test",
            warning_low=0.0,
            warning_high=100.0,
            critical_low=-10.0,
            critical_high=110.0,
            convert_fn=fn,
        )
        assert rule.convert_fn is fn


# --- AlertService ---

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_sensor_ids = AsyncMock(return_value=["bme280_temperature"])
    repo.get_latest = AsyncMock(return_value=_reading("bme280_temperature", 23.0, "°C"))
    repo.save_event = AsyncMock()
    return repo


@pytest.fixture
def rules():
    return [
        ThresholdRule(
            sensor_id="bme280_temperature",
            warning_low=65.0,
            warning_high=80.0,
            critical_low=60.0,
            critical_high=85.0,
            convert_fn=lambda c: c * 9.0 / 5.0 + 32.0,
            label="Air",
            unit="°F",
        ),
    ]


class TestAlertServiceInit:
    def test_initial_state(self, mock_repo, rules):
        svc = AlertService(mock_repo, rules, poll_interval=10)
        assert svc._task is None
        assert svc.is_running is False


class TestAlertServiceStartStop:
    async def test_start_creates_task(self, mock_repo, rules):
        svc = AlertService(mock_repo, rules, poll_interval=10)
        await svc.start()
        assert svc.is_running is True
        await svc.stop()

    async def test_start_idempotent(self, mock_repo, rules):
        svc = AlertService(mock_repo, rules, poll_interval=10)
        await svc.start()
        task1 = svc._task
        await svc.start()
        assert svc._task is task1
        await svc.stop()

    async def test_stop_when_not_started(self, mock_repo, rules):
        svc = AlertService(mock_repo, rules, poll_interval=10)
        await svc.stop()  # Should not raise


class TestAlertServiceCheckLoop:
    async def test_normal_reading_no_event(self, mock_repo, rules):
        """Normal reading should not generate an alert event."""
        # 23°C = 73.4°F → normal
        mock_repo.get_latest = AsyncMock(
            return_value=_reading("bme280_temperature", 23.0, "°C")
        )
        svc = AlertService(mock_repo, rules, poll_interval=1)

        with patch("pi.services.alerts.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._check_loop()
            except asyncio.CancelledError:
                pass

        mock_repo.save_event.assert_not_called()

    async def test_warning_generates_event(self, mock_repo, rules):
        """Warning-level reading should generate a system event."""
        # 28°C = 82.4°F → warning
        mock_repo.get_latest = AsyncMock(
            return_value=_reading("bme280_temperature", 28.0, "°C")
        )
        svc = AlertService(mock_repo, rules, poll_interval=1)

        with patch("pi.services.alerts.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._check_loop()
            except asyncio.CancelledError:
                pass

        mock_repo.save_event.assert_called_once()
        event = mock_repo.save_event.call_args[0][0]
        assert event.event_type == "alert_warning"
        assert "Air" in event.description

    async def test_critical_generates_event(self, mock_repo, rules):
        """Critical-level reading should generate a system event."""
        # 32°C = 89.6°F → critical
        mock_repo.get_latest = AsyncMock(
            return_value=_reading("bme280_temperature", 32.0, "°C")
        )
        svc = AlertService(mock_repo, rules, poll_interval=1)

        with patch("pi.services.alerts.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._check_loop()
            except asyncio.CancelledError:
                pass

        mock_repo.save_event.assert_called_once()
        event = mock_repo.save_event.call_args[0][0]
        assert event.event_type == "alert_critical"

    async def test_no_duplicate_alert_same_state(self, mock_repo, rules):
        """Should not re-alert when sensor stays in the same alert state."""
        # 28°C = 82.4°F → warning, stays warning
        mock_repo.get_latest = AsyncMock(
            return_value=_reading("bme280_temperature", 28.0, "°C")
        )
        svc = AlertService(mock_repo, rules, poll_interval=1)

        with patch("pi.services.alerts.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, None, asyncio.CancelledError()]
            try:
                await svc._check_loop()
            except asyncio.CancelledError:
                pass

        # Only one event for the first transition, not one per poll
        assert mock_repo.save_event.call_count == 1

    async def test_recovery_clears_state(self, mock_repo, rules):
        """Returning to normal should clear alert state for future alerts."""
        readings = [
            _reading("bme280_temperature", 28.0, "°C"),  # warning
            _reading("bme280_temperature", 23.0, "°C"),  # normal
            _reading("bme280_temperature", 28.0, "°C"),  # warning again
        ]
        mock_repo.get_latest = AsyncMock(side_effect=readings)
        svc = AlertService(mock_repo, rules, poll_interval=1)

        with patch("pi.services.alerts.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, None, None, asyncio.CancelledError()]
            try:
                await svc._check_loop()
            except asyncio.CancelledError:
                pass

        # Should fire twice: warning → normal (recovery) → warning
        assert mock_repo.save_event.call_count == 2

    async def test_handles_missing_sensor(self, mock_repo, rules):
        """Should not crash when a rule's sensor has no readings."""
        mock_repo.get_latest = AsyncMock(return_value=None)
        svc = AlertService(mock_repo, rules, poll_interval=1)

        with patch("pi.services.alerts.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            try:
                await svc._check_loop()
            except asyncio.CancelledError:
                pass

        mock_repo.save_event.assert_not_called()
