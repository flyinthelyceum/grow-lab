"""The CAD parameters must reproduce the height stack the docs publish.

V1_PHYSICAL_BUILD.md § Station geometry gives a table of heights. This holds
``cad/growlab_cad/params.py`` against that table exactly, so a change to
either has to be made in both — the same discipline as the emulator's
parity test. No build123d needed: this is arithmetic.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cad.growlab_cad import params as P  # noqa: E402
from pi.dashboard.panel_geometry import FACE_HEIGHT, FACE_WIDTH, LAYOUTS  # noqa: E402

# The table, verbatim from the doc (console layout, 2026-09-04).
DOC_HEIGHTS = {
    "shadow_gap": 6.0,   # the cabinet floats on the frame
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
    "fixture": 54.9,   # the bottom of travel; the head is adjustable now
    "mast_top": 81.4,  # tall enough for the collar at full lift
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


class TestTheCabinetFloatsOnTheFrame:
    def test_the_mast_is_a_member_of_the_frame(self):
        """Not standing on the carcass floor: it runs to the ground."""
        assert P.MAST_BOTTOM == 0.0
        assert P.MAST_BOTTOM < P.FLOOR_TOP_Z

    def test_legs_are_inset_so_the_cabinet_overhangs(self):
        assert P.FRAME_LEG_INSET >= P.FRAME_TUBE
        assert P.FRAME_LEG_INSET < P.PLINTH_D / 4

    def test_the_frame_does_not_move_the_lift(self):
        """Everything above the carcass floor is measured from PLINTH_H."""
        assert P.HEIGHTS.static_lift == pytest.approx(13.0)
        assert P.TRAY_FLOOR_Z == P.PLINTH_H


class TestTheInstrumentIsBehindTheGlass:
    """The design: a clear fascia over an open bay, the metal case behind it."""

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
        """Round tube. The section answers to the load now that the bore has no
        counterweight in it — see mast.py for the arithmetic."""
        assert (P.MAST_OD, P.MAST_WALL) == (1.5, 0.065)
        assert P.MAST_W == P.MAST_D == P.MAST_OD

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

    def test_the_head_travels_far_enough_for_a_mature_plant(self):
        """LIGHTING_SYSTEM: "Height should remain adjustable".

        A ranunculus reaches 12-18 in. A head fixed at 15 in above the media has
        the canopy touching it at 15 in tall and 3 in inside it at 18. The top of
        travel must clear a mature plant by a useful working distance.
        """
        assert P.FIXTURE_Z_MIN - P.MEDIA_SURFACE_Z == pytest.approx(12.0)
        mature_canopy = P.MEDIA_SURFACE_Z + 18.0
        assert P.FIXTURE_Z_MAX - mature_canopy >= 15.0, (
            "the plant grows into the light at the top of travel"
        )
        assert P.FIXTURE_TRAVEL == pytest.approx(21.0)

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


def test_a_bad_knob_names_itself():
    """``_knob()`` refuses a value it cannot read, and says which variable and
    what it was. A knob that silently fell back to its default would build a
    station nobody asked for and report the design's numbers for it."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GROWLAB_")}
    env["GROWLAB_PLINTH_H"] = "tall"
    r = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); import cad.growlab_cad.params"],
        env=env, cwd=str(Path(__file__).resolve().parents[2]),
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "GROWLAB_PLINTH_H='tall'" in r.stderr
