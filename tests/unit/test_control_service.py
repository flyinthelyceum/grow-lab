"""Tests for the cross-process control channel reconciler.

The dashboard writes desired state into `control_state`; this service reads it
and pushes changes into the live fan and meter services. These cover the three
properties the design depends on: idempotence, edge-triggering, and expiry.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from pi.config.schema import ControlConfig
from pi.data.models import ControlEntry
from pi.services.control import (
    FAN_OVERRIDE,
    METER_EC_OVERRIDE,
    METER_PH_OVERRIDE,
    ControlService,
    parse_deflection,
    parse_duty,
)


def _entry(key, value, *, expires_in=None):
    now = datetime.now(timezone.utc)
    return ControlEntry(
        key=key,
        value=value,
        updated_at=now,
        expires_at=now + timedelta(seconds=expires_in) if expires_in else None,
    )


@pytest.fixture
def repo():
    r = AsyncMock()
    r.get_all_control = AsyncMock(return_value={})
    return r


@pytest.fixture
def fan():
    return MagicMock()


@pytest.fixture
def meters():
    return MagicMock()


@pytest.fixture
def service(repo, fan, meters):
    return ControlService(
        repo, ControlConfig(), fan_service=fan, meter_service=meters
    )


class TestParsing:
    def test_duty_clamped(self):
        assert parse_duty("150") == 100
        assert parse_duty("-5") == 0
        assert parse_duty("60") == 60

    def test_duty_accepts_float_text(self):
        assert parse_duty("59.6") == 60

    def test_duty_none_is_auto(self):
        assert parse_duty(None) is None

    def test_unparseable_duty_reads_auto_not_zero(self):
        """A corrupt row must not be read as 'fan off'."""
        assert parse_duty("banana") is None

    def test_deflection_clamped(self):
        assert parse_deflection("2.0") == 1.0
        assert parse_deflection("-9") == -1.0
        assert parse_deflection("0.25") == 0.25

    def test_unparseable_deflection_reads_auto(self):
        assert parse_deflection("") is None


class TestReconcile:
    async def test_first_poll_applies_stored_override(self, service, repo, fan):
        """An override set before a restart must survive it."""
        repo.get_all_control.return_value = {FAN_OVERRIDE: _entry(FAN_OVERRIDE, "70")}
        await service.reconcile_once()
        fan.set_override.assert_called_once_with(70)

    async def test_unchanged_value_is_not_reapplied(self, service, repo, fan):
        repo.get_all_control.return_value = {FAN_OVERRIDE: _entry(FAN_OVERRIDE, "70")}
        await service.reconcile_once()
        await service.reconcile_once()
        await service.reconcile_once()
        fan.set_override.assert_called_once_with(70)

    async def test_change_is_applied(self, service, repo, fan):
        repo.get_all_control.return_value = {FAN_OVERRIDE: _entry(FAN_OVERRIDE, "70")}
        await service.reconcile_once()
        repo.get_all_control.return_value = {FAN_OVERRIDE: _entry(FAN_OVERRIDE, "40")}
        await service.reconcile_once()
        assert [c.args[0] for c in fan.set_override.call_args_list] == [70, 40]

    async def test_clearing_returns_to_auto(self, service, repo, fan):
        repo.get_all_control.return_value = {FAN_OVERRIDE: _entry(FAN_OVERRIDE, "70")}
        await service.reconcile_once()
        repo.get_all_control.return_value = {FAN_OVERRIDE: _entry(FAN_OVERRIDE, None)}
        await service.reconcile_once()
        fan.clear_override.assert_called_once()

    async def test_absent_row_reads_auto_and_applies_once(self, service, fan):
        await service.reconcile_once()
        await service.reconcile_once()
        fan.clear_override.assert_called_once()

    async def test_expired_override_lapses_to_auto(self, service, repo, fan):
        """The safety property: a forgotten override must not hold the fan."""
        repo.get_all_control.return_value = {
            FAN_OVERRIDE: _entry(FAN_OVERRIDE, "0", expires_in=60)
        }
        await service.reconcile_once()
        fan.set_override.assert_called_once_with(0)

        later = datetime.now(timezone.utc) + timedelta(seconds=120)
        await service.reconcile_once(now=later)
        fan.clear_override.assert_called_once()

    async def test_meters_route_to_their_own_channels(self, service, repo, meters):
        repo.get_all_control.return_value = {
            METER_PH_OVERRIDE: _entry(METER_PH_OVERRIDE, "0.5"),
            METER_EC_OVERRIDE: _entry(METER_EC_OVERRIDE, "-1.0"),
        }
        await service.reconcile_once()
        meters.set_override.assert_any_call("ph", 0.5)
        meters.set_override.assert_any_call("ec", -1.0)

    async def test_returns_effective_values(self, service, repo):
        repo.get_all_control.return_value = {FAN_OVERRIDE: _entry(FAN_OVERRIDE, "70")}
        effective = await service.reconcile_once()
        assert effective[FAN_OVERRIDE] == "70"
        assert effective[METER_PH_OVERRIDE] is None

    async def test_unknown_keys_are_ignored(self, service, repo, fan, meters):
        repo.get_all_control.return_value = {
            "something.else": _entry("something.else", "1")
        }
        effective = await service.reconcile_once()
        assert "something.else" not in effective

    async def test_missing_service_is_not_an_error(self, repo, meters):
        """Meters configured, fan absent — the fan key must be a no-op."""
        service = ControlService(
            repo, ControlConfig(), fan_service=None, meter_service=meters
        )
        repo.get_all_control.return_value = {FAN_OVERRIDE: _entry(FAN_OVERRIDE, "70")}
        await service.reconcile_once()  # must not raise


class TestLifecycle:
    async def test_disabled_does_not_start(self, repo, fan):
        service = ControlService(
            repo, ControlConfig(enabled=False), fan_service=fan
        )
        await service.start()
        assert not service.is_running

    async def test_no_targets_does_not_start(self, repo):
        service = ControlService(repo, ControlConfig())
        await service.start()
        assert not service.is_running

    async def test_start_and_stop(self, service):
        await service.start()
        assert service.is_running
        await service.stop()
        assert not service.is_running

    async def test_loop_survives_a_read_error(self, service, repo):
        """A locked database must not kill the reconciler."""
        repo.get_all_control.side_effect = RuntimeError("database is locked")
        await service.start()
        assert service.is_running
        await service.stop()
