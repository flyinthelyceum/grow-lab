"""The canopy sensor case has to fit three boards, an optic, and a printer.

Split in two on purpose. The layout class needs no kernel — it is arithmetic
over the parameters, and it is where the collisions live, so it fails fast and
runs everywhere. The geometry class needs build123d and runs in CI.

The printability class is the interesting one: it turns "printed to best
practice" from a claim in a docstring into something that fails a build. Every
rule in it is one that, broken, produces a part that comes off the bed wrong
rather than a part that is merely ugly.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from cad.growlab_cad import params as P  # noqa: E402
from cad.growlab_cad import sensor_case as SC  # noqa: E402


def mm(inches: float) -> float:
    """Read a parameter back in the units it was written in."""
    return inches / P.MM


def overlaps(a0: float, a1: float, b0: float, b1: float) -> bool:
    return a0 < b1 and b0 < a1


class TestItSitsOnTheBlock:
    def test_it_fits_on_the_rear_face_shell(self):
        """The whole case has to land on solid concrete, not over a core.

        A standard block's rear face shell is 1.25 in. Overhang it and the case
        is cantilevered over a hole full of media.
        """
        assert P.SC_WID < P.CMU_FACE_SHELL, (mm(P.SC_WID), mm(P.CMU_FACE_SHELL))
        front_edge = P.SC_Y - P.SC_WID / 2
        shell_inner = P.CMU_Y + P.CMU_W / 2 - P.CMU_FACE_SHELL
        assert front_edge > shell_inner, "the front wall would overhang the core"

    def test_the_rear_face_is_flush_with_the_block(self):
        """The lip bears on the block's rear face. Flush, or it does not bear."""
        assert P.SC_Y + P.SC_WID / 2 == pytest.approx(P.CMU_Y + P.CMU_W / 2)

    def test_it_is_centred_on_the_block(self):
        assert P.SC_X == pytest.approx(P.CMU_X)

    def test_it_stands_on_the_block_not_in_it(self):
        assert P.SC_Z0 == pytest.approx(P.CMU_TOP_Z)

    def test_it_is_small_against_the_block(self):
        """It is meant to read as a datum on a big coarse object, not a lump."""
        assert P.SC_LEN / P.CMU_L < 0.20
        assert P.SC_HGT / P.CMU_H < 0.12


class TestTheOpticalStack:
    def test_the_port_is_the_case_centre(self):
        """The block's centre is the unshaded spot; the port marks it."""
        px, py = SC.port_centre()
        assert (px, py) == (P.SC_X, P.SC_Y)

    def test_the_sensor_lands_under_the_port(self):
        """The board is placed by its sensor, not by its outline."""
        x0, x1 = SC.as7341_span()
        y0, y1 = SC.as7341_y_span()
        assert x0 + P.SC_AS7341_SENSOR_X == pytest.approx(P.SC_X)
        assert y1 - P.SC_AS7341_SENSOR_Y == pytest.approx(P.SC_Y)
        assert mm(x1 - x0) == pytest.approx(mm(P.SC_AS7341_L))
        assert mm(y1 - y0) == pytest.approx(mm(P.SC_AS7341_W))

    def test_the_board_fits_the_cavity_with_clearance(self):
        ix, iy = SC.inner_half()
        x0, x1 = SC.as7341_span()
        y0, y1 = SC.as7341_y_span()
        assert x0 > P.SC_X - ix and x1 < P.SC_X + ix, "through an end wall"
        assert y0 > P.SC_Y - iy and y1 < P.SC_Y + iy, "through a side wall"
        assert mm(min(x0 - (P.SC_X - ix), (P.SC_X + ix) - x1)) >= 1.5
        assert mm(min(y0 - (P.SC_Y - iy), (P.SC_Y + iy) - y1)) >= 1.5

    def test_the_hole_boss_lands_on_the_board(self):
        """The one board whose position matters is screwed, not taped. The
        boss has to sit over the board's own hole, on the board."""
        hx, hy = SC.as7341_hole()
        x0, x1 = SC.as7341_span()
        y0, y1 = SC.as7341_y_span()
        r = P.SC_AS7341_BOSS_DIA / 2
        assert x0 + r < hx < x1 - r, "boss overhangs the board in X"
        assert y0 + r < hy < y1 - r, "boss overhangs the board in Y"

    def test_the_hole_boss_keeps_out_of_the_bore(self):
        """The boss and the baffle deliberately merge into one lozenge — the
        board puts its hole 6.7 mm from the sensor, and two rings of the sizes
        needed cannot both fit in that. What must survive is the bore: a clean
        circle, with wall on every side of it."""
        hx, hy = SC.as7341_hole()
        px, py = SC.port_centre()
        nearest = math.hypot(hx - px, hy - py) - P.SC_AS7341_BOSS_DIA / 2
        assert nearest > P.SC_BAFFLE_ID / 2, "the boss breaks into the bore"
        assert mm(nearest - P.SC_BAFFLE_ID / 2) >= 0.4, "less than a line of bore wall"

    def test_the_pilot_stops_short_of_the_show_face(self):
        """The screw's pilot runs up into the top wall for thread. It must not
        reach the face on the bed, or the print has a dimple where it shows."""
        into_wall = P.SC_AS7341_PILOT_DEPTH - P.SC_BAFFLE_DROP
        assert into_wall > 0, "no thread in the wall"
        assert P.SC_WALL - into_wall >= 0.8 * P.MM, "too little skin over the pilot"

    def test_the_diffuser_finishes_flush(self):
        """Proud and it collects a droplet; recessed and it holds a puddle.
        The recess is exactly the disc's thickness."""
        assert P.SC_PORT_DEPTH == pytest.approx(1.0 * P.MM)

    def test_the_disc_has_a_ledge_to_sit_on(self):
        ledge = (P.SC_PORT_DIA - P.SC_APERTURE_DIA) / 2
        assert ledge > 0, "the disc would fall through"
        assert mm(ledge) >= 0.6, "too little to bond to"

    def test_the_baffle_shadows_the_boards_own_led(self):
        """The LED sits a few millimetres from the sensor, pointing the same
        way. The collar's bore has to be tighter than that offset."""
        lx, ly = SC.as7341_led()
        px, py = SC.port_centre()
        offset = math.hypot(lx - px, ly - py)
        assert P.SC_BAFFLE_ID / 2 < offset, "the LED is inside the field stop"
        assert P.SC_BAFFLE_OD / 2 < offset, "the collar wall lands on the LED"

    def test_the_baffle_clears_every_part_on_the_sensor_face(self):
        """The board hangs sensor-side up, so the collar's height is the
        headroom for everything on that face."""
        assert P.SC_BAFFLE_DROP > P.SC_AS7341_PART_H + 0.2 * P.MM

    def test_the_collar_mostly_lands_on_the_board(self):
        """The sensor is near an edge, so part of the ring overhangs. It has to
        be a minority: the ring is what stops the board rocking on its one
        screw."""
        _, x1 = SC.as7341_span()
        reach = x1 - P.SC_X  # board edge beyond the sensor, toward +X
        assert reach > P.SC_BAFFLE_ID / 2 * 0.9, "the bore itself is off the board"
        # The overhang is the sliver between the board edge and the outer
        # radius; the ring touches over the arc where r_outer cos(theta) < reach.
        frac_off = math.acos(min(1.0, reach / (P.SC_BAFFLE_OD / 2))) / math.pi
        assert frac_off < 0.35, f"{frac_off:.0%} of the collar overhangs"

    def test_the_sensor_is_close_enough_for_a_wide_field(self):
        """A cosine corrector wants the sensor near the diffuser. Far away
        behind a small hole and the thing is a telescope, not a light meter."""
        gap = P.SC_BAFFLE_DROP + (P.SC_WALL - P.SC_PORT_DEPTH)
        half_angle = math.degrees(math.atan((P.SC_BAFFLE_ID / 2) / gap))
        assert half_angle > 45.0, f"field half-angle only {half_angle:.0f} deg"


class TestNothingCollides:
    """The layout is tight. This is the class that catches hand arithmetic."""

    def test_bosses_pass_under_the_hanging_boards(self):
        """The bosses are short so the upper boards can lie over them. If a
        boss ever grows, this is what says it now fouls the board."""
        board_underside = SC.board_top() - P.SC_BOARD_T
        boss_top = SC.plate_top() + P.SC_BOSS_H
        assert boss_top < board_underside, (mm(boss_top), mm(board_underside))

    def test_bosses_are_inside_the_walls(self):
        ix, iy = SC.inner_half()
        for bx, by in SC.boss_points():
            assert abs(bx - P.SC_X) + P.SC_BOSS_DIA / 2 <= ix + P.SC_WALL
            assert abs(by - P.SC_Y) + P.SC_BOSS_DIA / 2 <= iy + P.SC_WALL

    def test_the_bme_hangs_clear_of_the_as7341(self):
        _, x1 = SC.as7341_span()
        cx, _ = SC.bme280_centre()
        gap = (cx - P.SC_BME280_L / 2) - x1
        assert mm(gap) >= 2.0, f"only {mm(gap):.1f} mm between them"

    def test_the_bme_fits_the_cavity(self):
        ix, iy = SC.inner_half()
        cx, cy = SC.bme280_centre()
        assert cx + P.SC_BME280_L / 2 < P.SC_X + ix
        assert abs(cy - P.SC_Y) + P.SC_BME280_W / 2 < iy

    def test_the_bme_standoffs_land_on_it(self):
        cx, cy = SC.bme280_centre()
        for sx, sy in SC.bme280_standoff_points():
            assert abs(sx - cx) + P.SC_POST_DIA / 2 < P.SC_BME280_L / 2
            assert abs(sy - cy) + P.SC_POST_DIA / 2 < P.SC_BME280_W / 2

    def test_the_taped_ads_lands_clear_of_everything_on_the_plate(self):
        """Nothing is fenced, but it still has to miss the screws and vents."""
        cx, cy = SC.ads1115_centre()
        bx0, bx1 = cx - P.SC_ADS1115_L / 2, cx + P.SC_ADS1115_L / 2
        by0, by1 = cy - P.SC_ADS1115_W / 2, cy + P.SC_ADS1115_W / 2

        ix, iy = SC.inner_half()
        assert bx0 > P.SC_X - ix and bx1 < P.SC_X + ix, "off the plate in X"
        assert by0 > P.SC_Y - iy and by1 < P.SC_Y + iy, "off the plate in Y"

        for hx, hy in SC.boss_points():
            r = P.SC_BOSS_DIA / 2  # the boss itself, not just the screw
            assert not (overlaps(bx0, bx1, hx - r, hx + r)
                        and overlaps(by0, by1, hy - r, hy + r)), "under a boss"

        for vx in SC.vent_xs():
            assert not (overlaps(bx0, bx1, vx - P.SC_VENT_W / 2, vx + P.SC_VENT_W / 2)
                        and overlaps(by0, by1, P.SC_Y - P.SC_VENT_L / 2,
                                     P.SC_Y + P.SC_VENT_L / 2)), "over a vent"

    def test_the_vents_sit_between_the_ads_and_the_bosses(self):
        cx, _ = SC.ads1115_centre()
        half = P.SC_ADS1115_L / 2
        boss_inner = P.SC_LEN / 2 - P.SC_SCREW_INSET - P.SC_BOSS_DIA / 2
        for vx in SC.vent_xs():
            d = abs(vx - cx)
            assert half + P.SC_VENT_W / 2 < d, "vent under the ADS"
            assert d + P.SC_VENT_W / 2 < boss_inner, "vent under a boss"

    def test_the_cable_notch_misses_the_ads(self):
        """The notch cutter reaches a wall's thickness into the cavity."""
        _, iy = SC.inner_half()
        reach = P.SC_Y + iy - P.SC_WALL  # deepest the cutter comes in
        _, cy = SC.ads1115_centre()
        assert cy + P.SC_ADS1115_W / 2 < reach

    def test_air_can_cross_the_chamber(self):
        """Inlet low in the plate, outlet high in the rear wall. One opening is
        a dead end; two at different heights is a convection path."""
        assert len(SC.vent_xs()) >= 2
        assert len(SC.wall_vent_xs()) >= 2


class TestItPrintsWithoutTricks:
    """Best practice, made into something that can fail.

    Printed top face down on a textured sheet, 0.50 extrusion width, no support
    anywhere, no bridge longer than the slicer will span cleanly.
    """

    EXTRUSION = 0.50  # mm — a 0.4 nozzle run wide, so walls land on whole lines
    BRIDGE_LIMIT = 6.0  # mm of unsupported span we are willing to ask for

    def test_walls_are_whole_extrusion_lines(self):
        """A wall that is not a multiple of the line width leaves the slicer a
        sliver to fill, and a sliver is where a leak and a weak seam start."""
        for name, t in (("wall", P.SC_WALL), ("base", P.SC_BASE_T)):
            lines = mm(t) / self.EXTRUSION
            assert lines == pytest.approx(round(lines)), f"{name} is {lines:.2f} lines"
            assert round(lines) >= 4, f"{name} is only {round(lines)} lines"

    def test_the_only_bridge_is_the_disc_ledge_and_it_is_short(self):
        """Printed top-face-down the disc ledge is an annulus hanging over the
        aperture. It is the one overhang in the part."""
        span = (P.SC_PORT_DIA - P.SC_APERTURE_DIA) / 2
        assert mm(span) < self.BRIDGE_LIMIT

    def test_wall_vents_are_short_enough_to_bridge(self):
        """Their top edge is unsupported over the slot's height."""
        assert mm(P.SC_VENT_W) < self.BRIDGE_LIMIT

    def test_cable_entries_are_notches_not_holes(self):
        """A hole through a vertical wall needs a teardrop. A notch open to the
        bottom edge needs nothing — and the bottom edge prints last."""
        assert P.SC_CABLE_H > 0 and P.SC_PROBE_H > 0
        assert 5.0 * P.MM <= P.SC_CABLE_W < 5.6 * P.MM, "a friction fit on Cat5e"

    def test_the_insert_boss_has_meat_around_it(self):
        """A heat-set insert splits a thin boss as it goes in. Rule of thumb is
        wall >= the insert's own radius."""
        wall = (P.SC_BOSS_DIA - P.SC_INSERT_HOLE) / 2
        assert wall >= P.SC_INSERT_HOLE / 2, f"only {mm(wall):.2f} mm round the insert"

    def test_the_as7341_boss_has_meat_around_its_pilot(self):
        wall = (P.SC_AS7341_BOSS_DIA - P.SC_AS7341_PILOT) / 2
        assert mm(wall) >= 1.5, f"only {mm(wall):.2f} mm round the pilot"

    def test_the_insert_does_not_come_out_the_top(self):
        assert P.SC_INSERT_DEPTH < P.SC_BOSS_H

    def test_the_countersink_does_not_break_through(self):
        """An M2 countersink is deeper than people expect and the plate is 2 mm."""
        depth = P.SC_SCREW_CSK / 2
        assert depth <= P.SC_BASE_T, f"csk {mm(depth):.2f} through a {mm(P.SC_BASE_T)} plate"

    def test_the_screw_clears_its_hole(self):
        assert P.SC_SCREW_DIA > 2.0 * P.MM, "M2 needs clearance, not a thread"
        assert P.SC_SCREW_CSK > P.SC_SCREW_DIA

    def test_the_as7341_screw_clears_the_boards_hole(self):
        """M2.5 through the board's Ø3 — clearance, so the board can be nudged
        onto the baffle before the screw bites."""
        assert P.SC_AS7341_PILOT < P.SC_AS7341_HOLE_DIA

    def test_the_plate_drops_into_the_body(self):
        """Printed parts are not gauge blocks. Without clearance the plate is a
        press fit and the screws pull against it."""
        ix, iy = SC.inner_half()
        # build_base insets by 0.2 mm per side.
        assert mm(2 * ix) - mm(2 * (ix - 0.2 * P.MM)) == pytest.approx(0.4, abs=1e-6)
        assert iy > 0


@pytest.fixture(scope="module")
def parts():
    pytest.importorskip("build123d")
    return {"body": SC.build_body(), "base": SC.build_base()}


class TestTheGeometryBuilds:
    """Needs the kernel. CI is the first place these actually run."""

    def test_the_body_is_hollow(self, parts):
        from cad.growlab_cad._shapes import bbox_in

        bb = bbox_in(parts["body"])
        solid = (bb["x1"] - bb["x0"]) * (bb["y1"] - bb["y0"]) * (bb["z1"] - bb["z0"])
        assert parts["body"].volume / P.IN**3 < solid * 0.55

    def test_the_body_is_the_envelope_plus_its_lip(self, parts):
        from cad.growlab_cad._shapes import bbox_in

        bb = bbox_in(parts["body"])
        assert mm(bb["x1"] - bb["x0"]) == pytest.approx(mm(P.SC_LEN), abs=0.01)
        # Deeper than the envelope by one wall: the lip hangs outboard of the
        # block's rear face rather than flush with it.
        assert mm(bb["y1"] - bb["y0"]) == pytest.approx(mm(P.SC_WID + P.SC_WALL), abs=0.01)
        assert bb["z1"] == pytest.approx(SC.top_face())
        assert bb["z0"] == pytest.approx(SC.plate_top() - P.SC_LIP_DROP)

    def test_the_lip_hangs_outside_the_block(self, parts):
        from cad.growlab_cad._shapes import bbox_in

        assert bbox_in(parts["body"])["y1"] > P.CMU_Y + P.CMU_W / 2

    def test_the_two_halves_do_not_interfere(self, parts):
        shared = (parts["body"] & parts["base"]).volume / P.IN**3
        assert shared < 1e-4, f"{shared:.5f} in3 of overlap"

    def test_the_baffle_bore_is_clear_through(self, parts):
        """The boss merges into the collar's outer wall on purpose; the bore
        must still be empty from the aperture down to the board."""
        from cad.growlab_cad._shapes import cyl_z

        px, py = SC.port_centre()
        probe = cyl_z(P.SC_BAFFLE_ID - 0.4 * P.MM, P.SC_BAFFLE_DROP + P.SC_WALL,
                      at=(px, py, SC.board_top()))
        assert (probe & parts["body"]).volume < 1e-6, "something is in the bore"

    def test_it_does_not_interfere_with_the_block(self):
        """It rests on the top face; the lip lies against the rear face. Resting
        is not intersecting, and this says so."""
        pytest.importorskip("build123d")
        from cad.growlab_cad import cmu

        shared = (SC.build() & cmu.build()).volume / P.IN**3
        assert shared < 1e-4, f"{shared:.5f} in3 into the block"

    def test_print_orientation_puts_each_part_flat_on_the_bed(self):
        pytest.importorskip("build123d")
        from cad.growlab_cad._shapes import bbox_in

        for name, part in SC.for_print().items():
            bb = bbox_in(part)
            assert bb["z0"] == pytest.approx(0.0, abs=1e-6), f"{name} floats off the bed"
            assert (bb["x0"] + bb["x1"]) / 2 == pytest.approx(0.0, abs=1e-6)
            assert (bb["y0"] + bb["y1"]) / 2 == pytest.approx(0.0, abs=1e-6)

    def test_the_body_prints_top_face_down(self):
        pytest.importorskip("build123d")
        from cad.growlab_cad._shapes import bbox_in

        body = SC.for_print()["sensor_case_body"]
        bb = bbox_in(body)
        assert mm(bb["z1"] - bb["z0"]) == pytest.approx(
            mm(P.SC_HGT - P.SC_BASE_T + P.SC_LIP_DROP), abs=0.01
        )
