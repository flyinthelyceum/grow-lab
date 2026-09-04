"""The CAD parameters must reproduce the height stack the docs publish.

V1_PHYSICAL_BUILD.md § Station geometry gives a table of heights. This holds
``cad/growlab_cad/params.py`` against that table exactly, so a change to
either has to be made in both — the same discipline as the emulator's
parity test. No build123d needed: this is arithmetic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cad.growlab_cad import params as P  # noqa: E402

# The table, verbatim from the doc.
DOC_HEIGHTS = {
    "shadow_gap": 2.0,
    "reservoir_shelf": 12.0,
    "water_low": 14.0,
    "water_full": 16.1,
    "tray_floor": 24.0,
    "tray_rim": 26.0,
    "cmu_underside": 24.75,
    "media_surface": 30.9,
    "emitter": 31.0,
    "cmu_top": 32.4,
    "fixture": 46.0,
}


class TestHeightStackMatchesTheDocs:
    @pytest.mark.parametrize("name,expected", DOC_HEIGHTS.items())
    def test_height(self, name, expected):
        actual = getattr(P.HEIGHTS, name)
        # The doc rounds the block figures to one decimal.
        assert actual == pytest.approx(expected, abs=0.05), name

    def test_static_lift_is_seventeen_inches(self):
        """The number the pump lives or dies by."""
        assert P.HEIGHTS.static_lift == pytest.approx(17.0)

    def test_head_spans_46_to_58_with_centre_at_52(self):
        assert P.HEIGHTS.head_bottom == 46.0
        assert P.HEIGHTS.head_top == 58.0
        assert P.HEIGHTS.panel_centre == 52.0


class TestDerivedGeometry:
    def test_tray_nests_inside_the_carcass(self):
        assert P.TRAY_W == P.PLINTH_W - 2 * P.CARCASS_T
        assert P.TRAY_D == P.PLINTH_D - 2 * P.CARCASS_T

    def test_mast_is_against_the_rear_panel(self):
        back_face = P.MAST_Y + P.MAST_D / 2
        assert back_face == pytest.approx(P.PLINTH_D - P.REAR_PANEL_T)

    def test_fixture_cantilever_is_derived_not_asserted(self):
        """The doc's "~10 in" assumed the mast behind the cabinet. It is inside,
        and the block sits forward of it, so the cantilever is what those two
        positions make it — and well short of 10."""
        assert P.FIXTURE_CANTILEVER == pytest.approx(P.MAST_Y - P.CMU_Y)
        assert 4.0 < P.FIXTURE_CANTILEVER < 8.0

    def test_block_clears_the_mast(self):
        """Back face of the block in front of the front face of the mast."""
        block_back = P.CMU_Y + P.CMU_W / 2
        mast_front = P.MAST_Y - P.MAST_D / 2
        assert block_back < mast_front, (block_back, mast_front)

    def test_block_sits_inside_the_tray(self):
        tray_front_inside = P.CARCASS_T + P.TRAY_T
        assert P.CMU_Y - P.CMU_W / 2 >= tray_front_inside

    def test_fixture_is_centred_over_the_block(self):
        assert P.FIXTURE_Y == P.CMU_Y

    def test_pads_land_under_solid_block(self):
        """Under the corners, where a face shell meets an end shell."""
        assert P.PAD_X < P.CMU_L / 2
        assert P.PAD_X > P.CMU_L / 2 - P.CMU_END_SHELL
        assert P.PAD_Y_OFFSET < P.CMU_W / 2
        assert P.PAD_Y_OFFSET > P.CMU_W / 2 - P.CMU_FACE_SHELL

    def test_dial_cut_is_not_asserted(self):
        """Pending calipers. A number here would be a guess in the drawings."""
        assert P.DIAL_CUT_DIAMETER is None

    def test_wet_bay_leaves_room_for_the_dry_bay(self):
        inside = P.PLINTH_W - 2 * P.CARCASS_T
        dry = inside - P.WET_BAY_W - P.DIVIDER_T
        assert dry >= 5.0, "dry bay too narrow for the Pi, PSU and driver"
        assert P.WET_BAY_W > P.RESERVOIR_L, "reservoir must fit the wet bay"

    def test_reservoir_fits_the_cabinet_depth(self):
        assert P.RESERVOIR_W < P.PLINTH_D - P.CARCASS_T - P.REAR_PANEL_T
