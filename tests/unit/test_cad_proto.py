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

    def test_the_stub_is_long_enough_to_bend(self):
        """A hand bender cannot make a stub shorter than its take-up."""
        first = Q.bend_sheet()[0]
        assert first["back_of_bend"] > Q.TAKE_UP
        assert first["mark"] > 0

    def test_the_drop_leaves_room_for_the_connector(self):
        drop = next(r for r in Q.bend_sheet() if r["step"] == 4)
        assert drop["mark"] >= Q.TAKE_UP + Q.travel() + Q.OVERLAP_MIN

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
    def test_it_hangs_where_it_is_drawn(self):
        assert Q.beam_box()[4] - Q.media_top() == pytest.approx(Q.DRAWN_GAP)
        assert Q.GAP_MIN <= Q.DRAWN_GAP <= Q.GAP_MAX


class TestTheTelescope:
    """12 to 24 in over the media, on a 1/2 EMT tube in the 3/4 drop."""

    def test_at_the_lowest_light_the_tube_is_still_held(self):
        z_tip = Q.crook_points()["tip"][1]
        assert Q.inner_tube(Q.GAP_MIN)[1] - z_tip == pytest.approx(Q.OVERLAP_MIN)

    def test_at_the_highest_light_the_tube_stops_short_of_the_bend(self):
        c = Q.crook_points()
        tangent = c["p3"][1] - Q.bend_radius()
        assert Q.inner_tube(Q.GAP_MAX)[1] <= tangent - Q.TANGENT_CLEAR + 1e-9

    def test_at_the_highest_light_the_hub_clears_the_coupling(self):
        assert Q.coupling_bottom() - Q.hub_top(Q.GAP_MAX) == pytest.approx(Q.SHOW_MIN)

    def test_the_tubes_nest(self):
        assert Q.INNER_OD < Q.EMT_ID - 0.05
        assert Q.INNER_OD < Q.EMT_ID - 0.02 < Q.EMT_ID, "the bushing slides in the bore"

    def test_the_cables_go_through_the_inner_tube(self):
        """The camera's micro-HDMI end is the one pulled; a standard HDMI
        plug would not pass."""
        w, t = Q.MICRO_HDMI
        assert math.hypot(w, t) < Q.INNER_ID

    def test_the_travel_is_the_gap_range(self):
        z_lo, _ = Q.inner_tube(Q.GAP_MIN)
        z_hi, _ = Q.inner_tube(Q.GAP_MAX)
        assert z_hi - z_lo == pytest.approx(Q.travel())


class TestTheCamera:
    @pytest.mark.parametrize("gap", [12.0, 18.0, 24.0])
    def test_it_frames_both_plants_at_every_height(self, gap):
        far, near = Q.camera_sees(gap)
        assert abs(far) < Q.CAM_HFOV / 2 and abs(near) < Q.CAM_HFOV / 2

    def test_its_bay_is_in_the_end_block(self):
        bx0, bx1, by0, by1 = Q.cam_bay()
        x0, x1, y0, y1, *_ = Q.beam_box()
        assert bx0 > HS.LENGTH / 2 + Q.BAR_CLEAR + 0.25 and bx1 < x1 - 0.25
        assert y0 + Q.BEAM_RAIL < by0 and by1 < y1 - Q.BEAM_RAIL

    def test_the_groove_keeps_walls_in_the_spine(self):
        assert (Q.BEAM_SPINE - Q.GROOVE) / 2 >= 0.125

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
        for name in ("plate", "instrument", "crook", "beam", "hub", "inner", "sleeve",
                     "bushing", "lid"):
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
        for name in ("p1.step", "beam_top.dxf", "beam_bottom.dxf", "hub.stl", "sleeve.stl",
                     "face_template.dxf", "plate.dxf", "cap_lower_right.dxf", "bend_sheet.md"):
            assert (tmp_path / name).exists(), name


class TestTheViewer:
    def test_it_knows_every_part(self, parts):
        """A part added to the model must not silently vanish from the page."""
        from cad.proto_viewer import PARTS

        assert set(PARTS) == set(parts)

    def test_what_rides_the_telescope_is_what_hangs_off_the_tube(self):
        from cad.proto_viewer import PARTS

        rides = {n for n, s in PARTS.items() if s.get("rides")}
        assert rides == {"inner", "bushing", "beam", "bars", "hub", "lid"}

    def test_the_slider_runs_the_whole_travel(self):
        from cad.proto_viewer import heights

        h = heights()
        assert h[0]["gap"] == Q.GAP_MIN and h[-1]["gap"] == Q.GAP_MAX
        assert h[0]["held"] == pytest.approx(Q.OVERLAP_MIN)
        assert h[-1]["hub_clear"] == pytest.approx(Q.SHOW_MIN)
