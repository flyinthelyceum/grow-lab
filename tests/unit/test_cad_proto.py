"""P1, the first-install prototype: two blocks, a conduit, a light.

The layout and the bend sheet are arithmetic, so most of this runs without a
kernel. What it holds the design to: every cut in the instrument block lands in
a tunnel and leaves concrete beside it; the crook bends on a hand bender and
fits one stick; the light is where the plant needs it and hides its LEDs; and
the instrument block cannot be tipped by the thing it carries.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from components import lm301h_heatsink_module as HS  # noqa: E402

from cad.growlab_cad import proto as Q  # noqa: E402


class TestTheFaceIsCoredWhereItCanBe:
    """The one step that cannot be undone. Every cut is through the face
    shell into a tunnel, never into the web or an end shell behind it, and
    every cut leaves concrete between it and a free edge."""

    def test_the_dial_holes_are_inside_the_upper_tunnel(self):
        z0, z1 = Q.tunnels()["upper"]
        for _, z in Q.dial_centres():
            assert z - Q.DIAL_HOLE / 2 > z0 + Q.MIN_LIGAMENT
            assert z + Q.DIAL_HOLE / 2 < z1 - Q.MIN_LIGAMENT

    def test_the_dial_holes_leave_concrete_at_the_edges_and_between(self):
        x0, x1, *_ = Q.instrument_box()
        (xa, _), (xb, _) = Q.dial_centres()
        assert xa - Q.DIAL_HOLE / 2 - x0 >= Q.MIN_LIGAMENT
        assert x1 - (xb + Q.DIAL_HOLE / 2) >= Q.MIN_LIGAMENT
        assert (xb - xa) - Q.DIAL_HOLE >= Q.MIN_LIGAMENT

    def test_the_flanges_fit_the_face_without_touching(self):
        x0, x1, *_ = Q.instrument_box()
        (xa, _), (xb, _) = Q.dial_centres()
        assert xb - xa >= Q.DIAL_FLANGE
        assert xa - Q.DIAL_FLANGE / 2 >= x0 and xb + Q.DIAL_FLANGE / 2 <= x1

    def test_the_window_is_inside_the_lower_tunnel(self):
        x0, x1, *_ = Q.instrument_box()
        wx0, wx1, wz0, wz1 = Q.window_rect()
        z0, z1 = Q.tunnels()["lower"]
        assert wz0 > z0 + Q.MIN_LIGAMENT and wz1 < z1 - Q.MIN_LIGAMENT
        assert wx0 - x0 >= Q.MIN_LIGAMENT and x1 - wx1 >= Q.MIN_LIGAMENT

    def test_the_eink_board_fits_its_tunnel(self):
        x0, x1, *_ = Q.instrument_box()
        z0, z1 = Q.tunnels()["lower"]
        w, h = Q.INKY_BOARD
        assert w < x1 - x0 and h < z1 - z0


class TestTheCrookBendsOnAHandBender:
    def test_it_is_three_nineties_in_one_stick(self):
        assert Q.total_bend() <= 360
        assert Q.developed_length() < Q.STICK
        # What is left over is enough to practise the stub and a back-to-back.
        assert Q.STICK - Q.developed_length() > Q.STUB_BACK + Q.bend_sheet()[1]["mark"]

    def test_the_stub_is_long_enough_to_bend(self):
        """A hand bender cannot make a stub shorter than its take-up."""
        first = Q.bend_sheet()[0]
        assert first["back_of_bend"] > Q.TAKE_UP
        assert first["mark"] > 0

    def test_the_drop_leaves_room_for_the_connector(self):
        assert Q.bend_sheet()[-1]["mark"] >= Q.TAKE_UP + Q.DROP_STRAIGHT - 1e-9

    def test_the_marks_add_back_up_to_the_shape(self):
        """Out-to-out dimensions the tape reads, against the centreline."""
        c, d = Q.crook_points(), Q.EMT_OD
        sheet = {r["step"]: r["back_of_bend"] for r in Q.bend_sheet()}
        assert sheet[2] == pytest.approx(c["p2"][1] - c["p1"][1] + d)
        assert sheet[3] == pytest.approx(c["p2"][0] - c["p3"][0] + d)

    def test_the_radius_follows_the_bender(self):
        assert Q.bend_radius() == pytest.approx(Q.TAKE_UP - Q.EMT_OD / 2)

    def test_the_stub_sits_in_the_lower_tunnel(self):
        c = Q.crook_points()
        x0, x1, *_ = Q.instrument_box()
        assert x0 < c["end"][0] < x1, "the stub's end is inside the block"
        assert c["end"][1] - Q.EMT_OD / 2 == pytest.approx(Q.tunnels()["lower"][0])

    def test_the_first_bend_clears_the_web_on_its_way_out(self):
        """At the bender's radius the stub's bend sweeps up and out through the
        tunnel's side opening. It has to leave below the web."""
        zb, zt = Q.stub_exit()
        lo, hi = Q.tunnels()["lower"]
        assert lo < zb < zt < hi - 1.0

    def test_the_run_clears_the_instrument_block(self):
        c = Q.crook_points()
        assert c["p2"][1] - Q.EMT_OD / 2 > Q.instrument_box()[5] + 6.0

    def test_the_drop_lands_over_the_planter(self):
        x0, x1, y0, y1, *_ = Q.planter_box()
        assert Q.crook_points()["p3"][0] == pytest.approx((x0 + x1) / 2)
        assert Q.crook_y() == pytest.approx((y0 + y1) / 2)


class TestTheLight:
    def test_it_hangs_its_gap_over_the_media(self):
        assert Q.beam_box()[4] - Q.media_top() == pytest.approx(Q.LIGHT_GAP)

    def test_the_bars_are_flush_in_its_top(self):
        """They shed heat to the room exactly as they would bare."""
        assert Q.BEAM_H > HS.HEIGHT

    def test_the_leds_are_recessed_out_of_sight(self):
        """Glare: from beside it, no die is in view. The regress below the bars
        is deeper than half a channel is wide, so the cutoff is past 45 deg."""
        regress = Q.BEAM_H - HS.HEIGHT
        channel = HS.WIDTH - 2 * Q.LEDGE
        assert regress >= 1.5
        assert math.degrees(math.atan2(regress, channel / 2)) > 45

    def test_the_beam_holds_both_bars(self):
        x0, x1, y0, y1, *_ = Q.beam_box()
        assert x1 - x0 > HS.LENGTH + 2 * Q.BEAM_END - 1e-9
        assert y1 - y0 == pytest.approx(Q.beam_width())


class TestItStands:
    def test_free_standing_it_would_tip(self):
        """The reason for the ground plate, kept as a test so nobody deletes the
        plate as decoration."""
        assert Q.stability()["shove_lb"] < 5.0

    def test_on_the_plate_the_light_hangs_inside_its_footprint(self):
        pan, inst, bridge = Q.plate_outline()
        x, y = Q.crook_points()["p3"][0], Q.crook_y()
        assert pan[0] < x < pan[1] and pan[2] < y < pan[3]

    def test_the_plate_hides_under_everything(self):
        pan, inst, _ = Q.plate_outline()
        ib = Q.instrument_box()
        assert inst[0] > ib[0] and inst[1] < ib[1] and inst[2] > ib[2] and inst[3] < ib[3]
        assert pan[1] - pan[0] < Q.PAN_BOTTOM_L and pan[3] - pan[2] < Q.PAN_BOTTOM_W

    def test_the_plate_bolt_misses_the_stub(self):
        bx, by = Q.plate_bolt()
        assert abs(by - Q.crook_y()) > Q.EMT_OD


# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def parts():
    pytest.importorskip("build123d")
    return Q.build()


class TestTheGeometryBuilds:
    def test_every_fabricated_part_is_one_solid(self, parts):
        for name in ("plate", "instrument", "crook", "beam", "hub"):
            assert len(parts[name].solids()) == 1, name

    def test_nothing_collides(self, parts):
        from itertools import combinations

        from cad.growlab_cad.params import IN

        for a, b in combinations(parts, 2):
            shared = (parts[a] & parts[b]).volume / IN ** 3
            assert shared < 1e-4, (a, b, shared)

    def test_the_pack_builds(self, tmp_path):
        pytest.importorskip("build123d")
        from cad import proto_build

        assert proto_build.main(["--out", str(tmp_path)]) == 0
        for name in ("p1.step", "beam_top.dxf", "beam_bottom.dxf", "hub.stl",
                     "face_template.dxf", "plate.dxf", "cap_lower_right.dxf", "bend_sheet.md"):
            assert (tmp_path / name).exists(), name
