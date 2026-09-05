"""The built solids must sit where the docs say and must not interfere.

Needs build123d, which is a large optional dependency (the `cad` extra); the
whole module skips cleanly without it, the way the browser and node tests do.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

build123d = pytest.importorskip("build123d")

from cad.growlab_cad import assembly, canopy, case, cmu, face, mast, params as P, plinth, tray  # noqa: E402
from cad.growlab_cad._shapes import bbox_in, box  # noqa: E402

from pi.dashboard.panel_geometry import FACE_HEIGHT, FACE_WIDTH, SCHEDULE  # noqa: E402


@pytest.fixture(scope="module")
def parts():
    return assembly.fabricated()


@pytest.fixture(scope="module")
def refs():
    return assembly.reference()


class TestEveryPartBuilds:
    def test_fabricated(self, parts):
        assert set(parts) == {"plinth", "base_frame", "rear_door", "tray", "pads", "mast",
                              "case", "fascia", "backplate", "canopy_carriage"}
        for name, p in parts.items():
            assert p.volume > 0, name

    def test_reference(self, refs):
        assert set(refs) == {"cmu", "reservoir", "fixture"}


class TestWhereThingsSit:
    def test_plinth_from_the_base_to_the_tray_rim(self, parts):
        bb = bbox_in(parts["plinth"])
        assert bb["z0"] == pytest.approx(P.SHADOW_GAP_H)
        assert bb["z1"] == pytest.approx(P.TRAY_RIM_Z)
        base = bbox_in(parts["base_frame"])
        assert base["z0"] == pytest.approx(0.0)
        assert base["z1"] == pytest.approx(P.SHADOW_GAP_H)
        assert bb["x1"] - bb["x0"] == pytest.approx(P.PLINTH_W)
        assert bb["y1"] - bb["y0"] == pytest.approx(P.PLINTH_D)

    def test_tray_floor_and_rim(self, parts):
        bb = bbox_in(parts["tray"])
        assert bb["z0"] == pytest.approx(P.TRAY_FLOOR_Z - P.TRAY_T)
        assert bb["z1"] == pytest.approx(P.TRAY_RIM_Z)

    def test_tray_finishes_flush_with_the_sides(self, parts):
        assert bbox_in(parts["tray"])["z1"] == pytest.approx(bbox_in(parts["plinth"])["z1"])

    def test_pads_top_out_at_the_cmu_underside(self, parts):
        assert bbox_in(parts["pads"])["z1"] == pytest.approx(P.CMU_UNDERSIDE_Z)

    def test_cmu_on_the_pads_at_the_documented_height(self, refs):
        bb = bbox_in(refs["cmu"])
        assert bb["z0"] == pytest.approx(P.CMU_UNDERSIDE_Z)
        assert bb["z1"] == pytest.approx(P.CMU_TOP_Z)

    def test_mast_stands_on_the_floor_and_ends_at_its_cap(self, parts):
        # abs= rather than the default rel=: the kernel's bounding box of a
        # curved face is a hair loose (~1e-9 in), which a relative tolerance
        # against zero cannot absorb.
        bb = bbox_in(parts["mast"])
        assert bb["z0"] == pytest.approx(P.MAST_BOTTOM, abs=1e-6)
        assert bb["z1"] == pytest.approx(P.MAST_TOP, abs=1e-6)
        assert bb["x1"] - bb["x0"] == pytest.approx(P.MAST_OD, abs=1e-6)
        assert bb["y1"] - bb["y0"] == pytest.approx(P.MAST_OD, abs=1e-6)

    def test_case_is_behind_the_fascia_in_the_console_bay(self, parts):
        bb = bbox_in(parts["case"])
        assert bb["y0"] == pytest.approx(P.FACE_Y0)
        assert bb["y1"] == pytest.approx(P.CASE_Y1)
        assert bb["x1"] - bb["x0"] == pytest.approx(FACE_WIDTH)
        assert bb["z1"] - bb["z0"] == pytest.approx(FACE_HEIGHT)
        assert (bb["z0"] + bb["z1"]) / 2 == pytest.approx(P.PANEL_CENTRE_Z)
        fascia = bbox_in(parts["fascia"])
        assert bb["y0"] - fascia["y1"] == pytest.approx(P.CASE_GAP)

    def test_fascia_is_recessed_in_the_front_and_spans_the_bay(self, parts):
        bb = bbox_in(parts["fascia"])
        assert bb["y0"] == pytest.approx(P.FASCIA_RECESS)
        assert bb["y1"] == pytest.approx(P.FASCIA_POCKET)
        assert bb["z0"] == pytest.approx(P.FACE_Z0 - P.FASCIA_MARGIN)
        assert bb["z1"] == pytest.approx(P.RAIL_BOTTOM_Z)
        assert bb["x0"] == pytest.approx(-P.PLINTH_W / 2 + P.CHAMFER)

    def test_case_sits_on_the_ledge(self, parts):
        """Touching, not floating: the ledge's top is the case's bottom."""
        ledge_top = P.FACE_Z0
        probe = box(FACE_WIDTH - 1, 1.0, 0.1, at=(0, P.FASCIA_POCKET + 0.6, ledge_top - 0.1))
        assert (parts["plinth"] & probe).volume > 1.0
        assert bbox_in(parts["case"])["z0"] == pytest.approx(ledge_top)

    def test_fixture_rides_the_carriage_over_the_block(self, refs, parts):
        """It used to hang off the mast cap at one welded height."""
        car = bbox_in(parts["canopy_carriage"])
        env = bbox_in(refs["fixture"])
        block = bbox_in(refs["cmu"])
        assert car["z1"] < bbox_in(parts["mast"])["z1"], "the carriage rides below the cap"
        assert env["z1"] == pytest.approx(P.CARRIAGE_Z), "the arm lands on the fixture's top"
        assert (env["y0"] + env["y1"]) / 2 == pytest.approx((block["y0"] + block["y1"]) / 2)
        assert (env["x0"] + env["x1"]) / 2 == pytest.approx((block["x0"] + block["x1"]) / 2)

    def test_reservoir_is_behind_the_console_on_its_shelf(self, refs):
        bb = bbox_in(refs["reservoir"])
        assert bb["z0"] == pytest.approx(P.SHELF_H)
        assert bb["y0"] >= P.PARTITION_Y1
        assert bb["y1"] <= P.REAR_INSIDE_Y

    def test_rear_door_is_in_the_rear_panel_behind_the_wet_bay(self, parts):
        bb = bbox_in(parts["rear_door"])
        assert bb["y1"] == pytest.approx(P.PLINTH_D)
        assert bb["x1"] < P.DIVIDER_X
        assert bb["z0"] >= P.FLOOR_TOP_Z
        assert bb["z1"] <= P.RAIL_BOTTOM_Z

    def test_nothing_fabricated_is_below_the_floor(self, parts):
        for name, p in parts.items():
            assert bbox_in(p)["z0"] >= -1e-6, name


class TestTheCaseComesOut:
    def test_case_sweeps_forward_through_nothing_but_the_fascia(self, parts):
        """Fascia off, knob caps off, the case pulls straight out."""
        c = bbox_in(parts["case"])
        sweep = box(c["x1"] - c["x0"], c["y1"] + 3.0, c["z1"] - c["z0"],
                    at=((c["x0"] + c["x1"]) / 2, (c["y1"] - 3.0) / 2, c["z0"]))
        for name, part in parts.items():
            if name in ("case", "fascia"):
                continue
            assert (sweep & part).volume < 1.0, name

    def test_fascia_has_holes_only_for_the_knobs(self, parts):
        import math

        from cad.growlab_cad.face import knob_points

        band_w = P.PLINTH_W - 2 * P.CHAMFER
        band_h = P.RAIL_BOTTOM_Z - (P.FACE_Z0 - P.FASCIA_MARGIN)
        solid = band_w * band_h * P.FASCIA_T
        holes = sum(math.pi * (d / 2 + P.KNOB_HOLE_CLEARANCE) ** 2 * P.FASCIA_T for _, _, d in knob_points())
        assert parts["fascia"].volume / P.IN**3 == pytest.approx(solid - holes, rel=1e-3)
        assert len(knob_points()) == 2

    def test_knob_holes_line_up_with_the_plate(self, parts):
        from cad.growlab_cad.face import knob_points

        for wx, wz, d in knob_points():
            probe = box(0.1, 1.0, 0.1, at=(wx, (P.FASCIA_RECESS + P.CASE_Y0) / 2, wz - 0.05))
            assert (probe & parts["fascia"]).volume < 1.0
            assert (probe & parts["case"]).volume < 1.0

    def test_loom_pass_is_in_the_case_back(self):
        body = case.build_body()
        probe = box(0.2, 1.0, 0.2, at=(0, P.CASE_Y1 - 0.03, P.FACE_Z0 + 1.5 - 0.1))
        assert (probe & body).volume < 1.0


class TestTheCanopyTravels:
    """The head is adjustable; drawing it parked proves nothing.

    LIGHTING_SYSTEM has always required an adjustable height. The old model had
    the arm welded to the mast cap at one position, and every test agreed with
    it, because they only ever checked the one position it was drawn in.
    """

    def test_the_collar_is_a_slip_fit_over_the_tube(self):
        assert canopy.collar_id() > P.MAST_OD, "it has to slide"
        assert canopy.collar_id() - P.MAST_OD == pytest.approx(2 * P.CARRIAGE_CLEAR)
        assert canopy.collar_od() - canopy.collar_id() == pytest.approx(2 * P.CARRIAGE_WALL)

    def test_the_split_reaches_the_bore(self):
        """A kerf that stops short of the bore cannot close on the tube."""
        probe = box(canopy.KERF / 2, 0.05, 0.5,
                    at=(P.MAST_X, P.MAST_Y + canopy.collar_od() / 2 - 0.02,
                        P.CARRIAGE_Z - 0.25))
        assert (probe & assembly.fabricated()["canopy_carriage"]).volume < 1.0

    def test_the_carriage_clears_the_shaft(self, parts):
        """A slip fit, not an interference fit — it has to slide."""
        car, mast = bbox_in(parts["canopy_carriage"]), bbox_in(parts["mast"])
        assert car["z1"] < mast["z1"], "the carriage rides below the cap"
        assert assembly._shared_in3(parts["canopy_carriage"], parts["mast"]) < 0.001

    def test_the_collar_clears_the_cap_at_full_lift(self):
        """Full lift is set by the travel, not by where the collar happens to be
        parked. The tube has to still be there above it."""
        collar_top = P.CARRIAGE_Z_MAX + P.CARRIAGE_H / 2
        assert collar_top < P.MAST_TOP - P.MAST_CAP_T, "the collar would foul the cap"

    def test_it_builds_clean_at_full_lift(self):
        """The end of travel is a configuration nobody looks at. Build it."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("GROWLAB_")}
        env["GROWLAB_FIXTURE_ABOVE_MEDIA"] = str(P.FIXTURE_ABOVE_MEDIA_MAX)
        r = subprocess.run(
            [sys.executable, str(REPO / "cad" / "build.py"), "--check"],
            env=env, cwd=str(REPO), capture_output=True, text=True, timeout=600,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "no interference between fabricated parts" in r.stdout, r.stdout


class TestTheViewerKnowsEveryPart:
    def test_materials_cover_the_assembly_exactly(self):
        """Adding a part to the assembly must not silently vanish in the viewer.

        The canopy mechanism did exactly that: four new parts went into the
        assembly and the viewer's materials table was never updated, so they had
        no label, no colour and no toggle. The model was right and the picture
        of it was quietly incomplete.
        """
        from cad.viewer import MATERIALS

        parts = {**assembly.fabricated(), **assembly.reference()}
        assert set(parts) == set(MATERIALS), (
            f"missing from the viewer: {set(parts) - set(MATERIALS)}; "
            f"stale in the viewer: {set(MATERIALS) - set(parts)}"
        )


class TestNothingInterferes:
    def test_fabricated_parts_do_not_overlap(self, parts):
        """Touching is fine. Shared volume is a build error."""
        clashes = assembly.interferences(parts)
        assert clashes == [], clashes

    def test_cmu_sits_on_the_pads(self, parts, refs):
        assert bbox_in(refs["cmu"])["z0"] == pytest.approx(bbox_in(parts["pads"])["z1"])

    def test_pan_passes_through_the_rear_door(self):
        w, h = plinth.door_opening()
        assert w > P.RESERVOIR_L
        assert h > P.RESERVOIR_H + P.RESERVOIR_LIFT_CLEARANCE

    def test_pan_slides_straight_out(self, refs, parts):
        """Sweep the pan backwards through the door opening: nothing in its way."""
        pan = bbox_in(refs["reservoir"])
        sweep = box(pan["x1"] - pan["x0"], P.PLINTH_D - pan["y0"] + 1.0, pan["z1"] - pan["z0"],
                    at=((pan["x0"] + pan["x1"]) / 2, (pan["y0"] + P.PLINTH_D + 1.0) / 2, pan["z0"]))
        assert (sweep & parts["plinth"]).volume < 1.0
        assert (sweep & parts["mast"]).volume < 1.0


class TestTheFaceReadsThePanelGeometry:
    """The face and the emulator draw from one module."""

    def _probe(self, wx, wz):
        return box(0.2, P.FACE_T * 2, 0.2, at=(wx, face.FACE_MID_Y, wz - 0.1))

    def test_face_without_dial_cuts_is_nearly_solid(self):
        """Dials are witness rings, not holes, until calipers arrive."""
        assert P.DIAL_CUT_DIAMETER is None
        f = face.build_face()
        plate = FACE_WIDTH * FACE_HEIGHT * P.FACE_T * P.IN**3
        window = next(e for e in SCHEDULE.elements if e.kind == "window")
        removed = window.width * window.height * P.FACE_T * P.IN**3
        assert f.volume < plate - removed
        assert f.volume > (plate - removed) * 0.97

    def test_window_is_cut_where_the_schedule_puts_it(self):
        window = next(e for e in SCHEDULE.elements if e.kind == "window")
        wx, wz = face.panel_to_world(window.x, window.y)
        assert (face.build_face() & self._probe(wx, wz)).volume < 1.0

    def test_dial_witness_ring_marks_the_bezel_but_does_not_cut(self):
        dial = next(e for e in SCHEDULE.elements if e.kind == "dial")
        wx, wz = face.panel_to_world(dial.x, dial.y)
        assert (face.build_face() & self._probe(wx, wz)).volume > 1.0

    def test_a_measured_cut_diameter_opens_the_dial(self, monkeypatch):
        monkeypatch.setattr(P, "DIAL_CUT_DIAMETER", 3.0)
        dial = next(e for e in SCHEDULE.elements if e.kind == "dial")
        wx, wz = face.panel_to_world(dial.x, dial.y)
        assert (face.build_face() & self._probe(wx, wz)).volume < 1.0

    def test_alternate_layouts_also_build(self):
        from pi.dashboard.panel_geometry import LAYOUTS

        for layout in LAYOUTS:
            assert face.build_face(layout).volume > 0, layout.id

    def test_nothing_but_glass_is_in_front_of_the_window(self, parts):
        """From the front plane to the plate, the e-ink window sees only the fascia."""
        window = next(e for e in SCHEDULE.elements if e.kind == "window")
        wx, wz = face.panel_to_world(window.x, window.y)
        probe = box(0.2, P.FACE_Y0, 0.2, at=(wx, P.FACE_Y0 / 2, wz - 0.1))
        for name, part in parts.items():
            if name == "fascia":
                continue
            assert (part & probe).volume < 1.0, name


class TestMastDetails:
    def test_shaft_is_hollow(self):
        solid = (P.MAST_OD / 2) ** 2 * 3.14159265 * (mast.shaft_top() - P.MAST_BOTTOM) * P.IN**3
        assert mast.build_shaft().volume < solid * 0.5

    def test_u_bolts_land_in_the_fixed_rear_panel(self, parts):
        """Both legs of every U-bolt are behind the dry bay, never in the door."""
        door = bbox_in(parts["rear_door"])
        left, right = mast.strap_bolt_x()
        assert left - P.MAST_STRAP_BOLT_DIA / 2 > door["x1"]
        assert left < P.MAST_X < right
        for z in mast.strap_heights():
            assert P.MAST_BOTTOM < z < P.RAIL_BOTTOM_Z

    def test_nothing_is_drilled_through_the_mast_but_the_line_pass(self):
        """The tube is painted and shows, so it carries exactly one hole.

        Compare the built shaft against a plain length of tube: the difference
        has to be the line pass and nothing else. The U-bolts go round the tube
        precisely so this stays true.
        """
        import math

        length = mast.shaft_top() - P.MAST_BOTTOM
        plain = (math.pi / 4
                 * (P.MAST_OD**2 - (P.MAST_OD - 2 * P.MAST_WALL) ** 2)
                 * length)
        one_hole = math.pi / 4 * P.MAST_LINE_PASS_DIA**2 * P.MAST_WALL
        removed = plain - mast.build_shaft().volume / P.IN**3
        assert removed == pytest.approx(one_hole, rel=0.25)

    def test_line_pass_is_over_the_pan_rim_and_under_the_rail(self):
        y, z = mast.line_pass()
        assert z - P.MAST_LINE_PASS_DIA / 2 > P.SHELF_H + P.RESERVOIR_H
        assert z + P.MAST_LINE_PASS_DIA / 2 < P.RAIL_BOTTOM_Z
        assert P.PARTITION_Y1 < y < P.REAR_INSIDE_Y


class TestTrayDetails:
    def test_four_pad_cutouts(self):
        assert len(tray.pad_centres()) == P.PAD_COUNT

    def test_pads_pass_through_the_tray_without_touching(self, parts):
        assert (parts["pads"] & parts["tray"]).volume < 1.0

    def test_mast_passes_through_the_notch(self, parts):
        assert (parts["mast"] & parts["tray"]).volume < 1.0


class TestCmuDetails:
    def test_two_cores_either_side_of_the_web(self):
        (ax, ay), (bx, by) = cmu.core_centres()
        assert ax < P.CMU_X < bx
        assert ay == by == P.CMU_Y

    def test_block_volume_is_plausible_for_a_two_core_cmu(self, refs):
        gross = P.CMU_L * P.CMU_W * P.CMU_H * P.IN**3
        v = refs["cmu"].volume
        # Standard blocks are roughly 45–60% solid.
        assert 0.40 * gross < v < 0.65 * gross
