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
        assert P.SC_LEN / P.CMU_L < 0.25
        assert P.SC_HGT / P.CMU_H < 0.12


class TestTheOpticalStack:
    def test_the_port_is_the_case_centre(self):
        """The block's centre is the unshaded spot; the port marks it."""
        px, py = SC.port_centre()
        assert (px, py) == (P.SC_X, P.SC_Y)

    def test_the_sensor_lands_under_the_port(self):
        """The AS7341's sensor is ~5 mm from one end of a 40 mm board, so the
        board is placed by its sensor, not by its outline."""
        x0, x1 = SC.as7341_span()
        assert x0 + P.SC_AS7341_SENSOR_FROM_END == pytest.approx(P.SC_X)
        assert mm(x1 - x0) == pytest.approx(40.0)

    def test_the_board_fits_the_cavity_with_clearance(self):
        ix, _ = SC.inner_half()
        x0, x1 = SC.as7341_span()
        assert x1 < P.SC_X + ix, "the board would foul the end wall"
        assert x0 > P.SC_X - ix
        assert mm(P.SC_X + ix - x1) >= 1.5, "less than 1.5 mm at the tight end"

    def test_the_diffuser_finishes_flush(self):
        """Proud and it collects a droplet; recessed and it holds a puddle.
        The recess is exactly the disc's thickness."""
        assert P.SC_PORT_DEPTH == pytest.approx(1.0 * P.MM)

    def test_the_disc_has_a_ledge_to_sit_on(self):
        ledge = (P.SC_PORT_DIA - P.SC_APERTURE_DIA) / 2
        assert ledge > 0, "the disc would fall through"
        assert mm(ledge) >= 0.6, "too little to bond to"

    def test_the_baffle_stops_the_boards_own_leds(self):
        """The AS7341 carries illumination LEDs beside the sensor. The baffle
        is narrower than the tongue they sit on, so it shadows them."""
        assert P.SC_BAFFLE_ID < P.SC_AS7341_TONGUE_W
        assert P.SC_BAFFLE_OD > P.SC_BAFFLE_ID

    def test_the_sensor_is_close_enough_for_a_wide_field(self):
        """A cosine corrector wants the sensor near the diffuser. Far away
        behind a small hole and the thing is a telescope, not a light meter."""
        import math

        gap = P.SC_BAFFLE_DROP + (P.SC_WALL - P.SC_PORT_DEPTH)
        half_angle = math.degrees(math.atan((P.SC_BAFFLE_ID / 2) / gap))
        assert half_angle > 45.0, f"field half-angle only {half_angle:.0f} deg"


class TestNothingCollides:
    """The layout is tight. This is the class that catches hand arithmetic."""

    def test_standoffs_land_on_the_board(self):
        x0, x1 = SC.as7341_span()
        for sx, sy in SC.standoff_points():
            assert x0 < sx < x1, (mm(sx), "outside the board in X")
            assert abs(sy - P.SC_Y) < P.SC_AS7341_W / 2, "outside the board in Y"

    def test_standoffs_keep_off_the_tongue(self):
        """The tongue carries the sensor and the LEDs. Only the baffle touches
        it; a post there would sit on components."""
        x0, _ = SC.as7341_span()
        tongue_x1 = x0 + P.SC_AS7341_TONGUE_L
        for sx, sy in SC.standoff_points():
            on_tongue_x = sx < tongue_x1
            on_tongue_y = abs(sy - P.SC_Y) < P.SC_AS7341_TONGUE_W / 2
            assert not (on_tongue_x and on_tongue_y), (mm(sx), mm(sy))

    def test_bosses_pass_under_the_board(self):
        """The bosses are short so the AS7341 can lie over them. If a boss ever
        grows, this is what says it now fouls the board."""
        board_underside = SC.board_top() - P.SC_BOARD_T
        boss_top = SC.plate_top() + P.SC_BOSS_H
        assert boss_top < board_underside, (mm(boss_top), mm(board_underside))

    def test_bosses_are_inside_the_walls(self):
        ix, iy = SC.inner_half()
        for bx, by in SC.boss_points():
            assert abs(bx - P.SC_X) + P.SC_BOSS_DIA / 2 <= ix + P.SC_WALL
            assert abs(by - P.SC_Y) + P.SC_BOSS_DIA / 2 <= iy + P.SC_WALL

    def test_the_ads_fits_the_dead_space_beside_the_as7341(self):
        """The board that would not fit on the plate. It only works because the
        AS7341's sensor offset leaves 32 mm of dead space, and it is 28 long."""
        cx, _ = SC.ads1115_centre()
        ax0, _ = SC.as7341_span()
        ix, _ = SC.inner_half()
        x0, x1 = cx - P.SC_ADS1115_L / 2, cx + P.SC_ADS1115_L / 2
        assert x0 > P.SC_X - ix, "through the end wall"
        assert x1 < ax0, "into the AS7341"
        assert mm(ax0 - x1) >= 1.0, f"only {mm(ax0 - x1):.1f} mm to the AS7341"

    def test_the_ads_standoffs_land_on_it(self):
        cx, cy = SC.ads1115_centre()
        for sx, sy in SC.ads1115_standoff_points():
            assert abs(sx - cx) < P.SC_ADS1115_L / 2
            assert abs(sy - cy) < P.SC_ADS1115_W / 2

    def test_the_upper_boards_do_not_overlap_each_other(self):
        cx, _ = SC.ads1115_centre()
        ax0, _ = SC.as7341_span()
        assert cx + P.SC_ADS1115_L / 2 < ax0

    def test_the_bme_is_the_only_thing_on_the_plate_and_it_is_clear(self):
        """Everything else moved upstairs, so this one just has to miss the
        screws, the vents and the tie posts."""
        cx, cy = SC.bme280_centre()
        bx0, bx1 = cx - P.SC_BME280_L / 2, cx + P.SC_BME280_L / 2
        by0, by1 = cy - P.SC_BME280_W / 2, cy + P.SC_BME280_W / 2

        ix, iy = SC.inner_half()
        assert bx0 > P.SC_X - ix and bx1 < P.SC_X + ix, "off the plate in X"
        assert by0 > P.SC_Y - iy and by1 < P.SC_Y + iy, "off the plate in Y"

        for hx, hy in SC.boss_points():
            r = P.SC_SCREW_CSK / 2
            assert not (overlaps(bx0, bx1, hx - r, hx + r)
                        and overlaps(by0, by1, hy - r, hy + r)), "over a screw"

        for vx in SC.vent_xs():
            assert not (overlaps(bx0, bx1, vx - P.SC_VENT_W / 2, vx + P.SC_VENT_W / 2)
                        and overlaps(by0, by1, P.SC_Y - P.SC_VENT_L / 2,
                                     P.SC_Y + P.SC_VENT_L / 2)), "over a vent"

    def test_the_bme_sits_in_the_moving_air(self):
        """It reads canopy air, so it belongs near the inlet, not in a corner."""
        cx, _ = SC.bme280_centre()
        nearest = min(abs(cx - vx) for vx in SC.vent_xs())
        assert mm(nearest) < 25.0, f"{mm(nearest):.0f} mm from the nearest inlet"

    def test_the_vents_are_clear_of_the_board_on_the_plate(self):
        cx, _ = SC.bme280_centre()
        for vx in SC.vent_xs():
            assert vx < cx - P.SC_BME280_L / 2

    def test_air_can_cross_the_chamber(self):
        """Inlet low in the plate, outlet high in the rear wall. One opening is
        a dead end; two at different heights is a convection path."""
        assert len(SC.vent_xs()) >= 2
        assert len(SC.wall_vent_xs()) >= 2
        inlet = set(round(mm(v)) for v in SC.vent_xs())
        outlet = set(round(mm(v)) for v in SC.wall_vent_xs())
        assert not inlet & outlet, "inlet and outlet stacked over each other"


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
        assert P.SC_CABLE_W >= 5.0 * P.MM, "Cat5e will not pass"

    def test_the_insert_boss_has_meat_around_it(self):
        """A heat-set insert splits a thin boss as it goes in. Rule of thumb is
        wall >= the insert's own radius."""
        wall = (P.SC_BOSS_DIA - P.SC_INSERT_HOLE) / 2
        assert wall >= P.SC_INSERT_HOLE / 2, f"only {mm(wall):.2f} mm round the insert"

    def test_the_insert_does_not_come_out_the_top(self):
        assert P.SC_INSERT_DEPTH < P.SC_BOSS_H

    def test_the_countersink_does_not_break_through(self):
        """An M2 countersink is deeper than people expect and the plate is 2 mm."""
        depth = P.SC_SCREW_CSK / 2
        assert depth <= P.SC_BASE_T, f"csk {mm(depth):.2f} through a {mm(P.SC_BASE_T)} plate"

    def test_the_screw_clears_its_hole(self):
        assert P.SC_SCREW_DIA > 2.0 * P.MM, "M2 needs clearance, not a thread"
        assert P.SC_SCREW_CSK > P.SC_SCREW_DIA

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
        assert mm(bb["y1"] - bb["y0"]) == pytest.approx(mm(P.SC_WID), abs=0.01)
        assert bb["z1"] == pytest.approx(SC.top_face())
        assert bb["z0"] == pytest.approx(SC.plate_top() - P.SC_LIP_DROP)

    def test_the_two_halves_do_not_interfere(self, parts):
        shared = (parts["body"] & parts["base"]).volume / P.IN**3
        assert shared < 1e-4, f"{shared:.5f} in3 of overlap"

    def test_assembled_it_is_the_envelope(self):
        pytest.importorskip("build123d")
        from cad.growlab_cad._shapes import bbox_in

        bb = bbox_in(SC.build())
        assert bb["z1"] - (SC.plate_top() - P.SC_LIP_DROP) == pytest.approx(
            P.SC_HGT + P.SC_LIP_DROP - P.SC_BASE_T
        )

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
        """The show face has to be the bed face. After the flip the top wall is
        the thing at z = 0, so the widest section is at the bottom."""
        pytest.importorskip("build123d")
        from cad.growlab_cad._shapes import bbox_in

        body = SC.for_print()["sensor_case_body"]
        bb = bbox_in(body)
        assert mm(bb["z1"] - bb["z0"]) == pytest.approx(
            mm(P.SC_HGT - P.SC_BASE_T + P.SC_LIP_DROP), abs=0.01
        )
