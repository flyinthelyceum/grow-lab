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
from pi.dashboard.panel_geometry import FACE_HEIGHT, FACE_WIDTH, LAYOUTS  # noqa: E402

# The table, verbatim from the doc (console layout, 2026-09-04).
DOC_HEIGHTS = {
    "shadow_gap": 2.0,
    "face_bottom": 22.2,
    "panel_centre": 28.2,
    "reservoir_shelf": 28.0,
    "water_low": 30.0,
    "water_full": 32.1,
    "face_top": 34.2,
    "tray_floor": 36.0,
    "tray_rim": 38.0,
    "cmu_underside": 36.75,
    "media_surface": 42.9,
    "emitter": 43.0,
    "cmu_top": 44.4,
    "fixture": 57.9,
    "mast_top": 59.4,
}


class TestHeightStackMatchesTheDocs:
    @pytest.mark.parametrize("name,expected", DOC_HEIGHTS.items())
    def test_height(self, name, expected):
        actual = getattr(P.HEIGHTS, name)
        # The doc rounds to one decimal.
        assert actual == pytest.approx(expected, abs=0.05), name

    def test_static_lift_is_thirteen_inches(self):
        """The number the pump lives or dies by — and the reason the pan sits
        behind the console rather than under it."""
        assert P.HEIGHTS.static_lift == pytest.approx(13.0)
        assert P.HEIGHTS.static_lift <= 17.0, "the docs' design target for the SICCE"

    def test_cabinet_is_20_by_16_and_36_to_the_tray_floor(self):
        assert (P.PLINTH_W, P.PLINTH_D, P.PLINTH_H) == (20.0, 16.0, 36.0)


class TestTheInstrumentIsBehindTheGlass:
    """The design: a clear fascia over an open bay, the metal case behind it."""

    def test_the_design_is_the_default(self):
        assert P.FASCIA is True
        assert P.FRAME is False

    def test_plate_is_centred_on_the_cabinet(self):
        assert P.FACE_X0 == pytest.approx(-FACE_WIDTH / 2)

    def test_plate_sits_just_behind_the_fascia(self):
        assert P.FACE_Y0 == pytest.approx(P.FASCIA_POCKET + P.CASE_GAP)
        assert P.FACE_T == P.PLATE_T
        assert 0 < P.CASE_GAP <= 0.125, "a knob bushing has to span this"

    def test_plate_clears_the_rail_by_its_margin(self):
        assert P.FACE_Z1 + P.FACE_MARGIN == pytest.approx(P.RAIL_BOTTOM_Z)
        assert P.FACE_Z1 - P.FACE_Z0 == pytest.approx(FACE_HEIGHT)

    def test_case_fits_the_console_bay_with_a_cable_gap_behind(self):
        assert P.CASE_Y1 <= P.CONSOLE_Y1 - P.BACKPLATE_T
        assert P.CONSOLE_Y1 - P.BACKPLATE_T - P.CASE_Y1 >= 0.375, "the loom has to turn down behind the case"

    def test_case_holds_what_the_plans_say_needs_three_inches(self):
        """INSTRUMENT_HEAD_PLANS.md § Depth stack: meters, Inky, i3 and Pi 'both
        fit inside 3.00 clear' — of a head 3.50 deep. The case is shallower;
        the Pi stack sits beside the movements, not behind."""
        assert P.CASE_D - P.PLATE_T - P.CASE_SHEET_T >= 2.5

    def test_ledge_leaves_the_chase_open(self):
        assert P.LEDGE_CHASE >= 0.5
        assert P.CONSOLE_Y1 - P.LEDGE_CHASE > P.FASCIA_POCKET

    @pytest.mark.parametrize("layout", LAYOUTS, ids=lambda l: l.id)
    def test_every_layouts_knobs_are_inside_the_fascia(self, layout):
        """The knob holes in the fascia must land inside the band."""
        for e in layout.elements:
            if e.kind != "knob":
                continue
            r = e.width / 2 + P.KNOB_HOLE_CLEARANCE
            assert P.FACE_Z0 + e.y - r > P.FACE_Z0 - P.FASCIA_MARGIN, (layout.id, e.id)
            assert abs(P.FACE_X0 + e.x) + r < P.PLINTH_W / 2 - P.CHAMFER, (layout.id, e.id)


class TestDerivedGeometry:
    def test_tray_nests_inside_the_carcass(self):
        assert P.TRAY_W == P.PLINTH_W - 2 * P.CARCASS_T
        assert P.TRAY_D == P.PLINTH_D - 2 * P.CARCASS_T

    def test_mast_is_against_the_rear_panel_in_the_dry_bay(self):
        back_face = P.MAST_Y + P.MAST_D / 2
        assert back_face == pytest.approx(P.PLINTH_D - P.REAR_PANEL_T)
        assert P.MAST_X - P.MAST_W / 2 >= P.DRY_BAY_X0
        assert P.MAST_X + P.MAST_W / 2 <= P.INSIDE_X1

    def test_mast_is_as_drawn(self):
        assert (P.MAST_W, P.MAST_D) == (2.0, 3.0)

    def test_mast_clears_the_rear_door(self):
        """The door is the wet bay's width; the mast is in the dry bay."""
        door_x1 = P.DIVIDER_X - P.DIVIDER_T / 2
        assert P.MAST_X - P.MAST_W / 2 > door_x1

    def test_fixture_cantilever_is_derived_not_asserted(self):
        assert P.FIXTURE_CANTILEVER == pytest.approx(P.MAST_Y - P.FIXTURE_Y)
        assert 4.0 < P.FIXTURE_CANTILEVER < 8.0

    def test_block_is_centred_and_clears_the_mast(self):
        assert P.CMU_Y == pytest.approx(P.PLINTH_D / 2)
        block_back = P.CMU_Y + P.CMU_W / 2
        mast_front = P.MAST_Y - P.MAST_D / 2
        assert block_back < mast_front, (block_back, mast_front)

    def test_block_sits_inside_the_tray(self):
        assert P.CMU_Y - P.CMU_W / 2 >= P.CARCASS_T + P.TRAY_T
        assert P.CMU_Y + P.CMU_W / 2 <= P.PLINTH_D - P.CARCASS_T - P.TRAY_T

    def test_fixture_is_centred_over_the_block(self):
        assert P.FIXTURE_Y == P.CMU_Y
        assert P.FIXTURE_X == P.CMU_X

    def test_fixture_keeps_the_docs_distance_above_the_media(self):
        """46 − 30.9 in the old stack; the light-to-canopy distance is what matters."""
        assert P.FIXTURE_Z - P.MEDIA_SURFACE_Z == pytest.approx(15.0, abs=0.15)

    def test_pads_land_under_solid_block(self):
        """Under the corners, where a face shell meets an end shell."""
        assert P.PAD_X < P.CMU_L / 2
        assert P.PAD_X > P.CMU_L / 2 - P.CMU_END_SHELL
        assert P.PAD_Y_OFFSET < P.CMU_W / 2
        assert P.PAD_Y_OFFSET > P.CMU_W / 2 - P.CMU_FACE_SHELL

    def test_dial_cut_is_not_asserted(self):
        """Pending calipers. A number here would be a guess in the drawings."""
        assert P.DIAL_CUT_DIAMETER is None


class TestTheReservoirFits:
    def test_wet_bay_leaves_room_for_the_dry_bay(self):
        assert P.DRY_BAY_W >= P.MAST_W + 2 * P.MAST_SIDE_CLEARANCE + 2.0, "room beside the mast for the PSU and driver"
        assert P.WET_BAY_W > P.RESERVOIR_L, "reservoir must fit the wet bay"

    def test_depth_budget_is_positive(self):
        assert P.DEPTH.slack >= 0.25, P.DEPTH.slack
        assert P.RESERVOIR_Y1 <= P.REAR_INSIDE_Y

    def test_pan_can_be_lifted_off_the_shelf(self):
        assert P.SHELF_H + P.RESERVOIR_H + P.RESERVOIR_LIFT_CLEARANCE <= P.RAIL_BOTTOM_Z

    def test_water_lines_follow_the_shelf(self):
        assert P.WATER_LOW == P.SHELF_H + 2.0
        assert P.WATER_FULL == pytest.approx(P.SHELF_H + 4.1)
