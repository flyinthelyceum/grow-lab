"""The reservoir targets are one writer, and the impossible case is refused.

Three files used to carry EC numbers and all three disagreed. These tests hold
the two properties that stop that happening again: the dials and the alert
bands are *computed* from `[reservoir]` rather than restated beside it, and a
target that cannot be reached from the source water fails to load instead of
being recorded in prose and worked around.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from pi.config.loader import _validate_config, load_config
from pi.config.schema import AppConfig, LightingConfig, ReservoirConfig
from pi.services.alerts import DEFAULT_RULES, classify_reading, rules_from_config

REPO_ROOT = Path(__file__).resolve().parents[2]


def _cfg(**reservoir) -> AppConfig:
    return AppConfig(reservoir=replace(ReservoirConfig(), **reservoir))


class TestTheDialsDeriveFromTheTargets:
    def test_ph_centre_is_the_ph_target(self, tmp_path):
        path = tmp_path / "c.toml"
        path.write_text("[reservoir]\nph_target = 5.9\n", encoding="utf-8")
        assert load_config(path).meters.ph.centre == pytest.approx(5.9)

    def test_ec_centre_is_the_ec_target_in_the_dials_units(self, tmp_path):
        # The dial reads mS/cm and the probe reports uS/cm; scale bridges them,
        # and the centre has to come out the other side of it.
        path = tmp_path / "c.toml"
        path.write_text(
            "[reservoir]\n"
            "ec_target_us = 1400.0\n"
            "ec_warning_low_us = 1200.0\n"
            "ec_warning_high_us = 1600.0\n"
            "ec_critical_low_us = 800.0\n"
            "ec_critical_high_us = 2000.0\n",
            encoding="utf-8",
        )
        cfg = load_config(path)
        assert cfg.meters.ec.centre == pytest.approx(1.4)
        assert cfg.meters.ec.centre == pytest.approx(
            cfg.reservoir.ec_target_us * cfg.meters.ec.scale
        )

    def test_an_explicit_centre_still_wins(self, tmp_path):
        """A dial can be deliberately off-target; it just cannot drift there."""
        path = tmp_path / "c.toml"
        path.write_text(
            "[reservoir]\n"
            "ec_target_us = 1400.0\n"
            "ec_warning_low_us = 1200.0\n"
            "ec_warning_high_us = 1600.0\n"
            "ec_critical_low_us = 800.0\n"
            "ec_critical_high_us = 2000.0\n"
            "\n[meters.ec]\ncentre = 2.0\n",
            encoding="utf-8",
        )
        assert load_config(path).meters.ec.centre == pytest.approx(2.0)

    def test_the_shipped_configs_agree_with_their_own_targets(self):
        for name in ("config.example.toml", "config.demo.toml"):
            cfg = load_config(REPO_ROOT / name)
            assert cfg.meters.ph.centre == pytest.approx(cfg.reservoir.ph_target), name
            assert cfg.meters.ec.centre == pytest.approx(
                cfg.reservoir.ec_target_us * cfg.meters.ec.scale
            ), name


class TestTheAlertBandsDeriveFromTheTargets:
    def test_ph_and_ec_rules_follow_the_config(self):
        cfg = _cfg(
            ec_warning_low_us=900.0,
            ec_warning_high_us=1100.0,
            ec_critical_low_us=500.0,
            ec_critical_high_us=1500.0,
        )
        ec = next(r for r in rules_from_config(cfg) if r.sensor_id == "ezo_ec")
        assert (ec.warning_low, ec.warning_high) == (900.0, 1100.0)
        assert (ec.critical_low, ec.critical_high) == (500.0, 1500.0)

    def test_other_sensors_are_untouched(self):
        derived = {r.sensor_id: r for r in rules_from_config(_cfg())}
        for rule in DEFAULT_RULES:
            if rule.sensor_id not in ("ezo_ph", "ezo_ec"):
                assert derived[rule.sensor_id] is rule

    def test_every_default_sensor_survives(self):
        assert {r.sensor_id for r in rules_from_config(_cfg())} == {
            r.sensor_id for r in DEFAULT_RULES
        }

    def test_the_documented_band_is_what_actually_alerts(self):
        """The drift this replaces: the docs called 1,300 out of range while
        alerts.py called it normal, because the two were written separately."""
        ec = next(r for r in rules_from_config(_cfg()) if r.sensor_id == "ezo_ec")
        assert classify_reading(1000.0, ec) == "normal"
        assert classify_reading(1300.0, ec) == "warning"
        assert classify_reading(1700.0, ec) == "critical"

    def test_the_march_baseline_would_now_read_critical(self):
        """1,529 uS/cm of plain water is not a normal reading against this
        target, and nothing in the repo should imply it is."""
        ec = next(r for r in rules_from_config(_cfg()) if r.sensor_id == "ezo_ec")
        assert classify_reading(1529.0, ec) == "warning"
        assert classify_reading(1529.0, ec) != "normal"


class TestAnUnreachableTargetIsRefused:
    def test_source_at_or_above_target_fails(self):
        with pytest.raises(ValueError, match="can only raise EC"):
            _validate_config(_cfg(source_water_ec_us=1529.0))

    def test_the_exact_march_numbers_fail(self):
        """800-1,200 against 1,529 uS/cm of tap water. This is the config the
        project carried in prose for months; it does not load."""
        with pytest.raises(ValueError):
            _validate_config(
                _cfg(
                    ec_target_us=1000.0,
                    ec_warning_low_us=800.0,
                    ec_warning_high_us=1200.0,
                    source_water_ec_us=1529.0,
                )
            )

    def test_source_inside_the_warning_band_fails(self):
        """A freshly filled reservoir must not start out already warning."""
        with pytest.raises(ValueError, match="freshly filled"):
            _validate_config(_cfg(source_water_ec_us=850.0))

    def test_ro_water_passes(self):
        _validate_config(_cfg(source_water_ec_us=15.0))

    def test_unmeasured_source_passes(self):
        """None means nobody has measured it, which must not block a bench run."""
        _validate_config(_cfg(source_water_ec_us=None))

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"ec_warning_low_us": 1300.0},          # above the target
            {"ec_critical_high_us": 1100.0},        # inside the warning band
            {"ph_warning_low": 6.4},                # above the target
            {"ph_critical_low": 5.9},               # inside the warning band
        ],
    )
    def test_bands_must_nest_around_the_target(self, kwargs):
        with pytest.raises(ValueError, match="nest around the target|is inverted"):
            _validate_config(_cfg(**kwargs))

    def test_the_shipped_configs_load(self):
        for name in ("config.example.toml", "config.demo.toml"):
            load_config(REPO_ROOT / name)


class TestFixtureHeight:
    def test_unset_by_default(self):
        """Nobody has written it down, and the config should say so rather than
        invent a number the collar has never been set to."""
        assert LightingConfig().fixture_above_media_in is None

    def test_reads_from_the_file(self, tmp_path):
        path = tmp_path / "c.toml"
        path.write_text("[lighting]\nfixture_above_media_in = 18.5\n", encoding="utf-8")
        assert load_config(path).lighting.fixture_above_media_in == pytest.approx(18.5)

    @pytest.mark.parametrize("value", [12.0, 22.5, 33.0])
    def test_accepts_the_cads_travel(self, value):
        _validate_config(AppConfig(lighting=LightingConfig(fixture_above_media_in=value)))

    @pytest.mark.parametrize("value", [11.9, 33.1, 0.0, -5.0])
    def test_refuses_a_height_the_collar_cannot_reach(self, value):
        with pytest.raises(ValueError, match="fixture_above_media_in"):
            _validate_config(
                AppConfig(lighting=LightingConfig(fixture_above_media_in=value))
            )

    def test_the_bounds_match_the_cad(self):
        """If the mast's travel changes, this is the test that notices."""
        import sys

        sys.path.insert(0, str(REPO_ROOT))
        from cad.growlab_cad import params as P  # noqa: E402

        from pi.config.schema import (  # noqa: E402
            FIXTURE_ABOVE_MEDIA_MAX_IN,
            FIXTURE_ABOVE_MEDIA_MIN_IN,
        )

        assert FIXTURE_ABOVE_MEDIA_MIN_IN == pytest.approx(P.FIXTURE_ABOVE_MEDIA_MIN)
        assert FIXTURE_ABOVE_MEDIA_MAX_IN == pytest.approx(P.FIXTURE_ABOVE_MEDIA_MAX)


class TestConfigShow:
    """`growlab config show` is the affordance the whole change depends on:
    'read the config, not the doc' only works if the config can be read."""

    def _run(self, path: Path):
        from click.testing import CliRunner

        from pi.cli.main import cli

        return CliRunner().invoke(cli, ["--config", str(path), "config", "show"])

    def test_prints_the_targets_and_the_derived_centres(self, tmp_path):
        path = tmp_path / "c.toml"
        path.write_text("[reservoir]\nec_target_us = 1000.0\n", encoding="utf-8")
        result = self._run(path)
        assert result.exit_code == 0, result.output
        assert "EC target      1000 uS/cm" in result.output
        assert "800 uS/cm to 1200 uS/cm" in result.output
        assert "derived from the targets" in result.output

    def test_says_plainly_when_the_source_water_is_unmeasured(self, tmp_path):
        path = tmp_path / "c.toml"
        path.write_text("[reservoir]\n", encoding="utf-8")
        out = self._run(path).output
        assert "NOT MEASURED" in out
        assert "D.0" in out

    def test_reports_headroom_once_it_is_measured(self, tmp_path):
        path = tmp_path / "c.toml"
        path.write_text(
            "[reservoir]\nsource_water_ec_us = 120.0\n", encoding="utf-8"
        )
        out = self._run(path).output
        assert "120 uS/cm" in out
        assert "880 uS/cm of headroom" in out

    def test_says_plainly_when_the_fixture_height_is_unrecorded(self, tmp_path):
        path = tmp_path / "c.toml"
        path.write_text("[lighting]\n", encoding="utf-8")
        out = self._run(path).output
        assert "NOT RECORDED" in out

    def test_reports_the_fixture_height_once_set(self, tmp_path):
        path = tmp_path / "c.toml"
        path.write_text(
            "[lighting]\nfixture_above_media_in = 18.5\n", encoding="utf-8"
        )
        assert "18.5 in above media" in self._run(path).output

    def test_the_shipped_config_shows(self):
        assert self._run(REPO_ROOT / "config.example.toml").exit_code == 0
