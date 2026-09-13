"""The canopy sensor case has to fit three boards, an optic, and a printer.

Split in two on purpose. The layout class needs no kernel — it is arithmetic
over the parameters, and it is where the collisions live, so it fails fast and
runs everywhere. The geometry class needs build123d and runs in CI.

Rev E exists because five adversarial reviews found four things that would not
print, and the kernel tests of the day passed on every one of them: they checked
bounding boxes and volumes, and a bounding box cannot tell a solid from a
collection of parts floating inside it. So the rules below are of two kinds.

The layout rules say a feature is *carried* by something — the collar sits on a
ring of wall, the bosses reach the ceiling, the webs reach both outer faces. The
kernel rules then say the result is **one solid**, which is the assertion that
would have failed on all four blockers at once, and the cheapest true thing this
file can say about a part that has to come off a bed in one piece.
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


def discs_clash(ax: float, ay: float, ar: float,
                bx: float, by: float, br: float, gap: float = 0.0) -> bool:
    return math.hypot(ax - bx, ay - by) < ar + br + gap


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

    def test_the_lip_hangs_on_the_block_not_in_it(self):
        """The lip bears on the block's rear face from outside. Its inner face
        is where that face is; flush-and-outboard, not flush-and-through."""
        lip_inner = P.SC_Y1 - P.SC_WALL
        assert lip_inner == pytest.approx(P.CMU_Y + P.CMU_W / 2)
        assert P.SC_Y1 > P.CMU_Y + P.CMU_W / 2, "the lip would be inside the block"

    def test_it_is_centred_on_the_block(self):
        assert P.SC_X == pytest.approx(P.CMU_X)

    def test_it_stands_on_the_block_not_in_it(self):
        assert P.SC_Z0 == pytest.approx(P.CMU_TOP_Z)

    def test_it_is_small_against_the_block(self):
        """It is meant to read as a datum on a big coarse object, not a lump."""
        assert P.SC_LEN / P.CMU_L < 0.20
        assert P.SC_HGT / P.CMU_H < 0.12

    def test_three_feet_never_rock(self):
        """Four feet on a surface as wavy as a block is a rocking chair."""
        feet = SC.foot_points()
        assert len(feet) == 3
        (ax, ay), (bx, by), (cx, cy) = feet
        area = abs((bx - ax) * (cy - ay) - (cx - ax) * (by - ay)) / 2
        assert mm(mm(area)) > 100.0, "the three feet are nearly in a line"

    def test_the_feet_are_on_the_plate_and_clear_of_the_screws(self):
        """A foot over a screw means peeling a foot to open the case, and
        adhesive landing in a countersink."""
        fy0, fy1 = P.SC_Y - P.SC_WID / 2, P.SC_Y1 - P.SC_WALL
        r = P.SC_FOOT_DIA / 2
        for fx, fy in SC.foot_points():
            assert abs(fx - P.SC_X) + r < P.SC_LEN / 2, "foot off the end of the plate"
            assert fy0 + r < fy < fy1 - r, "foot off the side of the plate"
            for bx, by in SC.boss_points():
                assert not discs_clash(fx, fy, r, bx, by, P.SC_SCREW_CSK / 2), \
                    "a foot lands on a screw"


class TestTheOpticalStack:
    def test_the_port_is_the_case_centre(self):
        """The block's centre is the open spot; the port marks it."""
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

    def test_the_wall_still_reaches_under_the_collar(self):
        """Rev D's blocker, and the one worth stating first. The collar hangs
        from the ceiling. Open the wall wider than the collar and there is no
        ceiling under it — it prints in mid-air, held by whatever the screw
        boss happens to overlap. The bore through the wall is the bore, no
        wider."""
        assert P.SC_APERTURE_DIA <= P.SC_BAFFLE_OD, "the collar hangs over the hole"
        carried = (P.SC_BAFFLE_OD - P.SC_APERTURE_DIA) / 2
        assert mm(carried) >= 1.0, f"only {mm(carried):.2f} mm of wall under the collar"

    def test_the_bore_is_one_diameter_all_the_way_up(self):
        """Collar and wall share a bore, so the field stop is a plain tube and
        the arithmetic below means what it says."""
        assert P.SC_APERTURE_DIA == pytest.approx(P.SC_BAFFLE_ID)

    def test_the_hole_boss_lands_on_the_board(self):
        """The one board whose position matters is screwed, not taped. The
        boss has to sit over the board's own hole, on the board."""
        hx, hy = SC.as7341_hole()
        x0, x1 = SC.as7341_span()
        y0, y1 = SC.as7341_y_span()
        r = P.SC_AS7341_BOSS_DIA / 2
        assert x0 + r < hx < x1 - r, "boss overhangs the board in X"
        assert y0 + r < hy < y1 - r, "boss overhangs the board in Y"

    def test_the_bore_keeps_its_own_wall(self):
        """The boss and the collar deliberately merge into one lozenge — the
        board puts its hole 6.7 mm from the sensor and two rings of the sizes
        needed cannot both fit in that. What must survive is the bore, and what
        would break into it is the drilled pilot, not the boss's outside."""
        hx, hy = SC.as7341_hole()
        px, py = SC.port_centre()
        d = math.hypot(hx - px, hy - py)
        wall = d - P.SC_AS7341_PILOT / 2 - P.SC_BAFFLE_ID / 2
        assert mm(wall) >= 1.0, f"only {mm(wall):.2f} mm between the pilot and the bore"

    def test_the_pilot_stops_short_of_the_diffuser(self):
        """The pilot's blind end is under the diffuser recess in plan, and the
        recess floor is the thinnest skin in the part. Rev D ran the pilot to
        exactly that floor: threads into the disc's bond face."""
        skin = SC.recess_floor() - SC.pilot_top()
        assert skin > 0, "the pilot breaks into the diffuser recess"
        assert mm(skin) >= 0.5, f"only {mm(skin):.2f} mm under the disc"

    def test_the_screw_clamps_the_board_before_it_bottoms_out(self):
        """The skin under the diffuser caps the pilot at 2.3, so the screw is
        chosen to suit the pilot rather than the other way round. A screw that
        reaches the blind end first holds nothing at all."""
        into_pilot = P.SC_AS7341_SCREW_LEN - P.SC_BOARD_T
        assert into_pilot < P.SC_AS7341_PILOT_DEPTH, \
            "the screw bottoms out before the board is clamped"
        assert mm(into_pilot) >= 1.2, f"only {mm(into_pilot):.2f} mm of thread"

    def test_the_disc_sits_on_a_ledge_worth_bonding_to(self):
        ledge = (P.SC_PORT_DIA - P.SC_APERTURE_DIA) / 2
        assert ledge > 0, "the disc would fall through"
        assert mm(ledge) >= 1.5, "too little to bond to"

    def test_the_recess_takes_the_disc_as_bought(self):
        """The recess mouth is on the bed, where elephant's foot and hole
        shrink both eat into it, and PTFE does not compress."""
        assert P.SC_PORT_DIA - P.SC_DISC_DIA >= 0.4 * P.MM
        assert P.SC_PORT_DEPTH >= P.SC_DISC_T

    def test_the_recess_is_a_whole_number_of_layers(self):
        """Proud and it collects a droplet; recessed and it holds a puddle.
        A printer can only finish flush on a layer boundary."""
        layers = mm(P.SC_PORT_DEPTH) / 0.15
        assert layers == pytest.approx(round(layers), abs=1e-6), f"{layers:.2f} layers"

    def test_the_baffle_shadows_the_boards_own_led(self):
        """The LED sits a few millimetres from the sensor, pointing the same
        way. The collar's bore has to be tighter than that offset."""
        lx, ly = SC.as7341_led()
        px, py = SC.port_centre()
        offset = math.hypot(lx - px, ly - py)
        assert P.SC_BAFFLE_ID / 2 < offset, "the LED is inside the field stop"
        assert P.SC_BAFFLE_OD / 2 < offset, "the collar wall lands on the LED"
        assert P.SC_APERTURE_DIA / 2 < offset, \
            "the LED points straight up through the wall at the diffuser"

    def test_the_baffle_clears_every_part_on_the_sensor_face(self):
        """The board hangs sensor-side up, so the collar's height is the
        headroom for everything on that face, the sensor package included."""
        assert P.SC_BAFFLE_DROP > P.SC_AS7341_PART_H + 0.2 * P.MM
        assert P.SC_BAFFLE_DROP > P.SC_AS7341_PKG_H + 0.2 * P.MM

    def test_the_collar_mostly_lands_on_the_board(self):
        """The sensor is near an edge, so part of the ring overhangs. It has to
        be a minority: the ring is what stops the board rocking on its one
        screw."""
        _, x1 = SC.as7341_span()
        reach = x1 - P.SC_X  # board edge beyond the sensor, toward +X
        assert reach > P.SC_BAFFLE_ID / 2 * 0.9, "the bore itself is off the board"
        frac_off = math.acos(min(1.0, reach / (P.SC_BAFFLE_OD / 2))) / math.pi
        assert frac_off < 0.35, f"{frac_off:.0%} of the collar overhangs"

    def test_the_sensor_sees_the_whole_diffuser(self):
        """The bore is a tube of one diameter from the board to the disc, so
        the field stop is honest arithmetic: the half-angle is the tube's.
        Wide enough and the detector sees the entire disc, which is what makes
        a diffuser a diffuser rather than a window at the end of a telescope."""
        tube = SC.recess_floor() - SC.board_top()
        half_angle = math.degrees(math.atan((P.SC_BAFFLE_ID / 2) / tube))
        assert half_angle > 45.0, f"field half-angle only {half_angle:.0f} deg"
        # And the package cannot crowd the bore, at the half millimetre the
        # photo-scaled numbers are good to.
        assert mm(P.SC_BAFFLE_ID / 2) - 1.9 >= 0.5, "the bore rim lands on the package"


class TestNothingCollides:
    """The layout is tight. This is the class that catches hand arithmetic."""

    def test_the_corner_bosses_reach_the_ceiling(self):
        """Rev D's second blocker. A boss that stops short of the ceiling is,
        in the print, a disc starting in mid-air over the cavity."""
        assert P.SC_BOSS_DIA > P.SC_INSERT_OD
        assert SC.ceiling() - SC.plate_top() > P.SC_INSERT_DEPTH, \
            "the insert would come out the top of the boss"

    def test_each_boss_is_fused_into_its_corner(self):
        """Tangent to a wall is a line of contact, which is no contact at all.
        The web has to reach both outer faces."""
        for (bx, by), (wx, wy, wl, ww) in zip(SC.boss_points(), SC.web_boxes()):
            assert abs(wx - P.SC_X) + wl / 2 >= P.SC_LEN / 2 - 1e-9, "web short of the end"
            assert abs(wy - P.SC_Y) + ww / 2 >= P.SC_WID / 2 - 1e-9, "web short of the side"
            assert abs(wx - bx) <= wl / 2 + 1e-9, "web misses its boss in X"
            assert abs(wy - by) <= ww / 2 + 1e-9, "web misses its boss in Y"

    def test_the_insert_has_meat_around_it(self):
        """A heat-set insert splits a thin boss as it goes in. The rule is wall
        >= the insert's own radius — and the insert's, not the pilot hole's,
        which is what Rev D measured."""
        wall = (P.SC_BOSS_DIA - P.SC_INSERT_OD) / 2
        assert wall >= P.SC_INSERT_OD / 2, f"only {mm(wall):.2f} mm round the insert"

    def test_the_insert_hole_is_the_size_its_maker_asks_for(self):
        """0.6 mm of interference is 14 mm3 of displaced plastic with nowhere
        to go but up, onto the face the plate lands on."""
        assert P.SC_INSERT_HOLE >= P.SC_INSERT_OD - 0.3 * P.MM

    def test_no_hanging_board_lies_over_a_corner_boss(self):
        """The bosses are full height now, so a board over one does not clear
        it — this is the test that replaces the Z gap Rev D relied on."""
        x0, x1 = SC.as7341_span()
        y0, y1 = SC.as7341_y_span()
        bx0, bx1, by0, by1 = SC.bme280_span()
        r = P.SC_BOSS_DIA / 2
        for cx, cy in SC.boss_points():
            for name, (px0, px1, py0, py1) in (("AS7341", (x0, x1, y0, y1)),
                                               ("BME280", (bx0, bx1, by0, by1))):
                assert not (overlaps(px0, px1, cx - r, cx + r)
                            and overlaps(py0, py1, cy - r, cy + r)), \
                    f"{name} lies over a corner boss"

    def test_the_bme_hangs_clear_of_the_as7341(self):
        _, x1 = SC.as7341_span()
        bx0, _, _, _ = SC.bme280_span()
        assert mm(bx0 - x1) >= 1.5, f"only {mm(bx0 - x1):.1f} mm between them"

    def test_the_bme_fits_the_cavity(self):
        ix, iy = SC.inner_half()
        bx0, bx1, by0, by1 = SC.bme280_span()
        assert bx1 < P.SC_X + ix and bx0 > P.SC_X - ix
        assert by1 < P.SC_Y + iy and by0 > P.SC_Y - iy

    def test_the_bme_hangs_on_its_own_holes(self):
        """Rev D sat it on four bare posts with nothing retaining it, inverted.
        It hangs on two bosses by its own mounting holes, like the AS7341."""
        holes = SC.bme280_hole_points()
        assert len(holes) == 2
        bx0, bx1, by0, by1 = SC.bme280_span()
        for hx, hy in holes:
            assert bx0 < hx < bx1 and by0 < hy < by1, "a hole is off the board"
        pitch = math.hypot(holes[0][0] - holes[1][0], holes[0][1] - holes[1][1])
        assert pitch == pytest.approx(P.SC_BME280_HOLE_PITCH)
        assert P.SC_AS7341_PILOT < P.SC_BME280_HOLE_DIA, "no clearance through the board"

    def test_the_bme_bosses_clear_the_corner_bosses(self):
        for hx, hy in SC.bme280_hole_points():
            for cx, cy in SC.boss_points():
                assert not discs_clash(hx, hy, P.SC_BME280_BOSS_DIA / 2,
                                       cx, cy, P.SC_BOSS_DIA / 2, 1.0 * P.MM), \
                    "a BME boss runs into a corner boss"

    def test_the_lozenge_and_the_bme_bosses_do_not_touch(self):
        px, py = SC.port_centre()
        hx, hy = SC.as7341_hole()
        for mx, my in SC.bme280_hole_points():
            assert not discs_clash(mx, my, P.SC_BME280_BOSS_DIA / 2,
                                   px, py, P.SC_BAFFLE_OD / 2)
            assert not discs_clash(mx, my, P.SC_BME280_BOSS_DIA / 2,
                                   hx, hy, P.SC_AS7341_BOSS_DIA / 2)

    def test_the_taped_ads_fits_under_the_hanging_boards(self):
        """It is the only board with anything above it. Its stack — tape,
        board, tallest part — has to pass under both, with no header fitted."""
        assert SC.ads1115_stack_top() < SC.board_top() - P.SC_BOARD_T, \
            (mm(SC.ads1115_stack_top()), mm(SC.board_top() - P.SC_BOARD_T))

    def test_the_taped_ads_lands_clear_of_everything_on_the_plate(self):
        """Nothing is fenced, but it still has to miss the screws."""
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

    def test_air_enters_above_the_plate_and_leaves_higher(self):
        """Rev D drew its inlet through the plate, facing the block — whose top
        stays damp for weeks after a leach. The box then breathes the block's
        own boundary layer and dews on the lid every time the lamp goes off.
        Both openings are in the rear wall now, and the inlet is above the
        plate's top face."""
        assert SC.inlet_z() > SC.plate_top(), "the inlet opens at the block"
        assert SC.outlet_z() > SC.inlet_z() + 3.0 * P.MM, "no height to drive it"
        assert mm(SC.ceiling() - (SC.outlet_z() + P.SC_VENT_W / 2)) >= 1.0, \
            "no wall left above the outlet to bridge from"
        assert len(SC.inlet_xs()) >= 2 and len(SC.outlet_xs()) >= 2

    def test_the_vents_clear_the_cable_notch(self):
        for vx in SC.inlet_xs():
            assert abs(vx - P.SC_X) - P.SC_VENT_L / 2 > P.SC_CABLE_W / 2, \
                "an inlet runs into the cable notch"

    def test_the_tie_holes_flank_the_notch_without_breaking_into_it(self):
        """The zip tie through the lip is the strain relief; two holes, one
        each side of the channel, neither of them opening into it."""
        clear = P.SC_TIE_HOLE_DX - P.SC_TIE_HOLE_DIA / 2 - P.SC_CABLE_W / 2
        assert mm(clear) >= 1.0, f"only {mm(clear):.2f} mm of lip between them"
        assert P.SC_TIE_HOLE_DX + P.SC_TIE_HOLE_DIA / 2 < P.SC_LEN / 2

    def test_the_probe_comes_in_over_its_own_core(self):
        """It goes to the media in one of the cores, so it leaves through an
        end wall — not the front, where it would be a black lead at eye height
        crossing the block in full view."""
        assert P.SC_PROBE_W > 0 and P.SC_PROBE_H > 0
        _, iy = SC.inner_half()
        assert P.SC_PROBE_W / 2 < iy, "the probe notch is wider than the wall it is in"


class TestItPrintsWithoutTricks:
    """Best practice, made into something that can fail.

    Both parts top face down on a textured sheet, 0.50 extrusion width, no
    support anywhere, no bridge longer than the slicer will span cleanly.
    """

    EXTRUSION = 0.50  # mm — a 0.4 nozzle run wide, so walls land on whole lines
    LAYER = 0.15
    BRIDGE_LIMIT = 6.0  # mm of unsupported span we are willing to ask for

    def test_walls_are_whole_extrusion_lines(self):
        """A wall that is not a multiple of the line width leaves the slicer a
        sliver to fill, and a sliver is where a leak and a weak seam start."""
        for name, t in (("wall", P.SC_WALL), ("base", P.SC_BASE_T)):
            lines = mm(t) / self.EXTRUSION
            assert lines == pytest.approx(round(lines)), f"{name} is {lines:.2f} lines"
            assert round(lines) >= 4, f"{name} is only {round(lines)} lines"

    def test_every_bridge_in_the_part_is_short(self):
        """The unsupported span of a slot is its LENGTH, which is the axis Rev D
        measured the wrong way round: it checked the 2 mm height of a 10 mm
        slot against a 6 mm limit and passed."""
        spans = {
            "disc ledge": (P.SC_PORT_DIA - P.SC_APERTURE_DIA) / 2,
            "vent slot": P.SC_VENT_L,
            "cable notch": P.SC_CABLE_W,
            "probe notch": P.SC_PROBE_W,
        }
        for name, span in spans.items():
            assert mm(span) < self.BRIDGE_LIMIT, f"{name} spans {mm(span):.1f} mm"

    def test_cable_entries_are_notches_not_holes(self):
        """A hole through a vertical wall needs a teardrop. A notch open to the
        bottom edge needs nothing — and the bottom edge prints last."""
        assert P.SC_CABLE_H > 0 and P.SC_PROBE_H > 0
        assert 5.0 * P.MM <= P.SC_CABLE_W < 5.6 * P.MM, "a friction fit on Cat5e"

    def test_the_countersink_is_a_cone_and_leaves_plate_under_the_head(self):
        """Rev D cut a Ø4.4 counterbore 2.2 deep and called it a countersink.
        That leaves 0.3 mm of bridged plate for a 90 degree head to bear on,
        through which it pulls. A countersink is a cone: its depth is set by
        its mouth and the clearance hole, and it is not a free parameter."""
        assert P.SC_SCREW_CSK_DEPTH == pytest.approx(
            (P.SC_SCREW_CSK - P.SC_SCREW_DIA) / 2), "not a 90 degree cone"
        left = P.SC_BASE_T - P.SC_SCREW_CSK_DEPTH
        assert mm(left) >= 1.0, f"only {mm(left):.2f} mm of plate under the head"

    def test_the_screw_clears_its_hole(self):
        assert P.SC_SCREW_DIA > 2.0 * P.MM, "M2 needs clearance, not a thread"
        assert P.SC_SCREW_CSK > P.SC_SCREW_DIA

    def test_the_as7341_screw_clears_the_boards_hole(self):
        """M2.5 through the board's Ø3 — clearance, so the board can be nudged
        onto the baffle before the screw bites."""
        assert P.SC_AS7341_PILOT < P.SC_AS7341_HOLE_DIA

    def test_the_pilot_suits_a_thread_forming_screw_in_petg(self):
        """Too tight and the boss splits; too loose and there is no thread. An
        M2.5's minor diameter is 1.95, and a vertical hole prints ~0.2 small."""
        printed = P.SC_AS7341_PILOT - 0.2 * P.MM
        assert 1.95 * P.MM < printed < 2.3 * P.MM, f"{mm(printed):.2f} mm as printed"

    def test_the_boss_has_meat_around_its_pilot(self):
        for name, dia in (("AS7341", P.SC_AS7341_BOSS_DIA),
                          ("BME280", P.SC_BME280_BOSS_DIA)):
            wall = (dia - P.SC_AS7341_PILOT) / 2
            assert mm(wall) >= 1.5, f"{name}: only {mm(wall):.2f} mm round the pilot"

    def test_nothing_opens_in_the_face_that_meets_the_block(self):
        """The plate's underside is a seating face and a splash shield. Every
        opening in the case is in a wall."""
        assert not hasattr(P, "SC_VENT_X"), "plate vents are back"
        assert P.SC_FOOT_DEPTH < P.SC_BASE_T - P.SC_SCREW_CSK_DEPTH, \
            "a foot recess would break into a countersink"


@pytest.fixture(scope="module")
def parts():
    pytest.importorskip("build123d")
    return {"body": SC.build_body(), "base": SC.build_base()}


class TestTheGeometryBuilds:
    """Needs the kernel. CI is the first place these actually run."""

    def test_each_half_is_a_single_solid(self, parts):
        """The assertion Rev D was missing, and the one that would have caught
        all four of its blockers at once: a collar hanging over its own hole,
        a lip touching along an edge, four bosses tangent to the walls. A
        bounding box cannot tell a part from a pile of parts."""
        for name, part in parts.items():
            n = len(part.solids())
            assert n == 1, f"{name} is {n} solids — something is not attached"

    def test_the_body_is_hollow(self, parts):
        from cad.growlab_cad._shapes import bbox_in

        bb = bbox_in(parts["body"])
        solid = (bb["x1"] - bb["x0"]) * (bb["y1"] - bb["y0"]) * (bb["z1"] - bb["z0"])
        assert parts["body"].volume / P.IN**3 < solid * 0.55

    def test_the_body_is_the_envelope(self, parts):
        from cad.growlab_cad._shapes import bbox_in

        bb = bbox_in(parts["body"])
        assert mm(bb["x1"] - bb["x0"]) == pytest.approx(mm(P.SC_LEN), abs=0.01)
        assert mm(bb["y1"] - bb["y0"]) == pytest.approx(mm(P.SC_WID), abs=0.01)
        assert bb["z1"] == pytest.approx(SC.top_face())
        assert bb["z0"] == pytest.approx(SC.plate_top())

    def test_the_plate_carries_the_lip(self, parts):
        from cad.growlab_cad._shapes import bbox_in

        bb = bbox_in(parts["base"])
        assert bb["z0"] == pytest.approx(P.SC_Z0 - P.SC_LIP_DROP)
        assert bb["z1"] == pytest.approx(SC.plate_top())
        assert bb["y1"] > P.CMU_Y + P.CMU_W / 2, "the lip is not outside the block"

    def test_the_two_halves_meet_without_interfering(self, parts):
        shared = (parts["body"] & parts["base"]).volume / P.IN**3
        assert shared < 1e-4, f"{shared:.5f} in3 of overlap"

    def test_the_walls_stand_on_the_plate(self, parts):
        """Not floating above it: the seam is a joint, not a shadow gap."""
        from cad.growlab_cad._shapes import bbox_in

        assert bbox_in(parts["body"])["z0"] == pytest.approx(
            bbox_in(parts["base"])["z1"])

    def test_the_baffle_bore_is_clear_through(self, parts):
        """From the board right out through the diffuser recess. The boss
        merges into the collar on purpose; the bore is cut after both."""
        from cad.growlab_cad._shapes import cyl_z

        px, py = SC.port_centre()
        probe = cyl_z(P.SC_BAFFLE_ID - 0.4 * P.MM,
                      SC.recess_floor() - SC.board_top(),
                      at=(px, py, SC.board_top()))
        assert (probe & parts["body"]).volume < 1e-6, "something is in the bore"

    def test_the_pilot_does_not_reach_the_diffuser(self, parts):
        """A cut through the recess floor over the pilot would show as a hole
        in the disc's bond face."""
        from cad.growlab_cad._shapes import cyl_z

        hx, hy = SC.as7341_hole()
        skin = cyl_z(P.SC_AS7341_PILOT, SC.recess_floor() - SC.pilot_top(),
                     at=(hx, hy, SC.pilot_top()))
        assert (skin & parts["body"]).volume > 1e-7, "no material over the pilot"

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

    def test_the_show_face_is_the_bed_face(self):
        """Both parts go top-face-down. Rev D asserted a bounding-box height,
        which the unflipped part satisfies just as well — so this looks for the
        diffuser recess at the bed instead, which only the flipped body has."""
        pytest.importorskip("build123d")
        from cad.growlab_cad._shapes import cyl_z

        body = SC.for_print()["sensor_case_body"]
        at_bed = cyl_z(P.SC_PORT_DIA - 1.0 * P.MM, P.SC_PORT_DEPTH / 2,
                       at=(0, 0, 0)) & body
        assert at_bed.volume < 1e-6, "the port is not at the bed — body is upside down"

    def test_nothing_in_either_part_needs_support(self):
        """The claim "no supports" made checkable, by asking the solid rather
        than the parameters: every downward-facing face in the print, other
        than the bed itself, is a bridge, and every bridge is short.

        The one annulus is the disc's ledge, whose span is its radial width and
        not its diameter — the distinction Rev D's bridge test got wrong in the
        other direction, measuring a 10 mm slot by its 2 mm height.
        """
        pytest.importorskip("build123d")

        limit = TestItPrintsWithoutTricks.BRIDGE_LIMIT
        ledge = mm((P.SC_PORT_DIA - P.SC_APERTURE_DIA) / 2)
        for name, part in SC.for_print().items():
            for face in part.faces():
                try:
                    normal = face.normal_at(face.center())
                except ValueError:
                    continue
                centre = face.center()
                if normal.Z > -0.35 or centre.Z / P.IN < 0.05 * P.MM:
                    continue  # upward, vertical, or the bed face itself
                area = face.area / P.IN**2
                if mm(mm(area)) < 0.5:
                    continue
                bb = face.bounding_box()
                at_port = (abs(bb.center().X) / P.IN < 0.1 * P.MM
                           and abs(bb.center().Y) / P.IN < 0.1 * P.MM)
                span = ledge if at_port else mm(min(bb.size.X, bb.size.Y) / P.IN)
                assert span < limit, (
                    f"{name}: a {span:.1f} mm overhang at z={mm(centre.Z / P.IN):.1f}")

    def test_the_plate_has_no_overhang_at_all(self):
        """It prints top face down precisely so that the countersinks and the
        foot recesses open upward. If one of them ever points the other way
        this is what says so."""
        pytest.importorskip("build123d")

        plate = SC.for_print()["sensor_case_base"]
        for face in plate.faces():
            try:
                normal = face.normal_at(face.center())
            except ValueError:
                continue
            if face.center().Z / P.IN < 0.05 * P.MM:
                continue
            assert normal.Z > -0.35, "something on the plate hangs downward"

    def test_the_bed_face_is_big_enough_to_hold_on(self):
        """A part this size with a hole in its bed face still needs the area."""
        pytest.importorskip("build123d")
        from build123d import Plane

        for name, part in SC.for_print().items():
            section = part.intersect(Plane.XY.offset(0.05 * P.MM))
            area = sum(f.area for f in section.faces()) / P.IN**2
            assert mm(mm(area)) > 400.0, f"{name}: {mm(mm(area)):.0f} mm2 on the bed"
