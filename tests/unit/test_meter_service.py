"""Tests for the panel meter service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from pi.config.schema import MeterChannelConfig, MetersConfig
from pi.data.models import SensorReading
from pi.drivers.mcp4728 import MIDPOINT_CODE
from pi.services.meters import (
    MeterService,
    apply_calibration,
    ease_alpha,
    normalise,
)


def _reading(sensor_id: str, value: float) -> SensorReading:
    return SensorReading(
        timestamp=datetime.now(timezone.utc),
        sensor_id=sensor_id,
        value=value,
        unit="",
    )


def _config(**kw) -> MetersConfig:
    base = dict(
        enabled=True,
        update_hz=100,
        time_constant_seconds=0.01,
        sample_interval_seconds=0.0,
        fault_timeout_seconds=1.0,
    )
    base.update(kw)
    return MetersConfig(**base)


@pytest.fixture
def mock_dac():
    dac = MagicMock()
    dac.is_available = True
    dac.codes = (MIDPOINT_CODE,) * 4
    dac.write_all = MagicMock(return_value=True)
    dac.centre_all = MagicMock(return_value=True)
    return dac


class TestNormalise:
    def test_target_is_centre(self):
        assert normalise(6.0, 6.0, 1.0) == 0.0

    def test_span_reaches_the_endpoint(self):
        assert normalise(7.0, 6.0, 1.0) == 1.0
        assert normalise(5.0, 6.0, 1.0) == -1.0

    def test_beyond_span_pegs_rather_than_overruns(self):
        assert normalise(8.3, 6.0, 1.0) == 1.0
        assert normalise(0.0, 6.0, 1.0) == -1.0

    def test_partial_deflection_is_proportional(self):
        assert normalise(6.2, 6.0, 1.0) == pytest.approx(0.2)

    def test_zero_span_cannot_divide(self):
        assert normalise(9.0, 6.0, 0.0) == 0.0


class TestApplyCalibration:
    def test_passthrough_without_enough_points(self):
        assert apply_calibration(0.4, ()) == 0.4
        assert apply_calibration(0.4, ((0.0, 0.0),)) == 0.4

    def test_identity_table_changes_nothing(self):
        pts = ((-1.0, -1.0), (0.0, 0.0), (1.0, 1.0))
        assert apply_calibration(0.37, pts) == pytest.approx(0.37)

    def test_interpolates_between_points(self):
        # A needle reading 10% high at half deflection.
        pts = ((0.0, 0.0), (0.5, 0.6), (1.0, 1.0))
        assert apply_calibration(0.25, pts) == pytest.approx(0.3)

    def test_clamps_outside_the_table(self):
        pts = ((-0.5, -0.4), (0.5, 0.4))
        assert apply_calibration(-1.0, pts) == -0.4
        assert apply_calibration(1.0, pts) == 0.4


class TestEaseAlpha:
    def test_long_constant_moves_slowly(self):
        assert ease_alpha(1 / 30, 2.0) < 0.02

    def test_step_equal_to_constant_is_most_of_the_way(self):
        assert ease_alpha(1.0, 1.0) == pytest.approx(0.632, abs=0.01)

    def test_zero_constant_snaps(self):
        assert ease_alpha(0.01, 0.0) == 1.0


class TestMeterService:
    def test_disabled_service_does_not_start(self, mock_dac):
        svc = MeterService(mock_dac, AsyncMock(), _config(enabled=False))
        asyncio.run(svc.start())
        assert svc.is_running is False

    def test_start_centres_the_needles_first(self, mock_dac):
        repo = AsyncMock()
        repo.get_latest = AsyncMock(return_value=None)
        svc = MeterService(mock_dac, repo, _config())

        async def _run():
            await svc.start()
            await svc.stop()

        asyncio.run(_run())
        mock_dac.centre_all.assert_called()

    def test_needle_eases_toward_its_reading(self, mock_dac):
        repo = AsyncMock()
        repo.get_latest = AsyncMock(
            side_effect=lambda sid: _reading(sid, 7.0 if sid == "ezo_ph" else 2000.0)
        )
        svc = MeterService(mock_dac, repo, _config())

        async def _run():
            await svc.start()
            await asyncio.sleep(0.25)
            await svc.stop()

        asyncio.run(_run())
        st = svc.status()
        assert st["ph"]["target"] == pytest.approx(1.0)
        # Eased, so it has travelled but is not required to have arrived.
        assert st["ph"]["displayed"] > 0.5

    def test_ec_scale_converts_us_to_ms(self, mock_dac):
        repo = AsyncMock()
        repo.get_latest = AsyncMock(
            side_effect=lambda sid: _reading(sid, 1500.0) if sid == "ezo_ec" else None
        )
        svc = MeterService(mock_dac, repo, _config())

        async def _run():
            await svc.start()
            await asyncio.sleep(0.1)
            await svc.stop()

        asyncio.run(_run())
        # 1500 uS/cm = 1.5 mS/cm; centre 1.0, span 1.0 -> +0.5
        assert svc.status()["ec"]["target"] == pytest.approx(0.5)

    def test_stale_reading_eases_to_centre_and_flags(self, mock_dac):
        repo = AsyncMock()
        repo.get_latest = AsyncMock(return_value=None)
        svc = MeterService(mock_dac, repo, _config(fault_timeout_seconds=0.0))

        async def _run():
            await svc.start()
            await asyncio.sleep(0.1)
            await svc.stop()

        asyncio.run(_run())
        st = svc.status()
        assert st["ph"]["faulted"] is True
        assert st["ph"]["target"] == 0.0

    def test_override_pins_one_needle(self, mock_dac):
        repo = AsyncMock()
        repo.get_latest = AsyncMock(return_value=None)
        svc = MeterService(mock_dac, repo, _config())

        assert svc.set_override("ph", 1.0) is True
        assert svc.set_override("nonesuch", 1.0) is False

        async def _run():
            await svc.start()
            await asyncio.sleep(0.25)
            await svc.stop()

        asyncio.run(_run())
        assert svc.status()["ph"]["displayed"] > 0.5
        assert svc.status()["ec"]["displayed"] == pytest.approx(0.0, abs=1e-6)

        svc.clear_override()
        assert svc.status()["ph"]["override"] is None

    def test_override_is_clamped(self, mock_dac):
        svc = MeterService(mock_dac, AsyncMock(), _config())
        svc.set_override("ec", 5.0)
        assert svc.status()["ec"]["override"] == 1.0

    def test_each_meter_writes_its_own_channel_pair(self, mock_dac):
        repo = AsyncMock()
        repo.get_latest = AsyncMock(return_value=None)
        cfg = _config(
            ph=MeterChannelConfig(dac_positive="A", dac_negative="B"),
            ec=MeterChannelConfig(dac_positive="C", dac_negative="D"),
        )
        svc = MeterService(mock_dac, repo, cfg)
        svc.set_override("ph", 1.0)
        svc.set_override("ec", -1.0)

        async def _run():
            await svc.start()
            await asyncio.sleep(0.25)
            await svc.stop()

        asyncio.run(_run())
        a, b, c, d = mock_dac.write_all.call_args.args[0]
        assert a > b  # pH deflected right
        assert c < d  # EC deflected left

    def test_invert_flips_the_pair(self, mock_dac):
        repo = AsyncMock()
        repo.get_latest = AsyncMock(return_value=None)
        cfg = _config(ph=MeterChannelConfig(dac_positive="A", dac_negative="B", invert=True))
        svc = MeterService(mock_dac, repo, cfg)
        svc.set_override("ph", 1.0)

        async def _run():
            await svc.start()
            await asyncio.sleep(0.25)
            await svc.stop()

        asyncio.run(_run())
        a, b, _, _ = mock_dac.write_all.call_args.args[0]
        assert a < b  # inverted, so a right-hand command drives left

    def test_stop_closes_the_dac(self, mock_dac):
        repo = AsyncMock()
        repo.get_latest = AsyncMock(return_value=None)
        svc = MeterService(mock_dac, repo, _config())

        async def _run():
            await svc.start()
            await svc.stop()

        asyncio.run(_run())
        mock_dac.close.assert_called_once()
