"""The built solids must sit where the docs say and must not interfere.

Needs build123d, which is a large optional dependency (the `cad` extra); the
whole module skips cleanly without it, the way the browser and node tests do.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

build123d = pytest.importorskip("build123d")

from cad.growlab_cad import assembly, cmu, head, mast, params as P, plinth, tray  # noqa: E402
from cad.growlab_cad._shapes import bbox_in  # noqa: E402

from pi.dashboard.panel_geometry import FACE_HEIGHT, FACE_WIDTH, SCHEDULE  # noqa: E402


@pytest.fixture(scope="module")
def parts():
    return assembly.fabricated()


@pytest.fixture(scope="module")
def refs():
    return assembly.reference()


class TestEveryPartBuilds:
    def test_fabricated(self, parts):
        assert set(parts) == {"plinth", "tray", "pads", "mast", "head"}
        for name, p in parts.items():
            assert p.volume > 0, name

    def test_reference(self, refs):
        assert set(refs) == {"cmu", "media", "reservoir", "fixture"}


class TestWhereThingsSit:
    def test_plinth_from_floor_to_tray_rim(self, parts):
        bb = bbox_in(parts["plinth"])
        assert bb["z0"] == pytest.approx(0.0)
        assert bb["z1"] == pytest.approx(P.TRAY_RIM_Z)
        assert bb["x1"] - bb["x0"] == pytest.approx(P.PLINTH_W)
        assert bb["y1"] - bb["y0"] == pytest.approx(P.PLINTH_D)

    def test_tray_floor_at_24_rim_at_26(self, parts):
        bb = bbox_in(parts["tray"])
        assert bb["z0"] == pytest.approx(P.TRAY_FLOOR_Z - P.TRAY_T)
        assert bb["z1"] == pytest.approx(P.TRAY_RIM_Z)

    def test_tray_finishes_flush_with_the_sides(self, parts):
        assert bbox_in(parts["tray"])["z1"] == pytest.approx(bbox_in(parts["plinth"])["z1"])

    def test_pads_top_out_at_the_cmu_underside(self, parts):
        assert bbox_in(parts["pads"])["z1"] == pytest.approx(P.CMU_UNDERSIDE_Z)

    def test_cmu_from_24_75_to_32_375(self, refs):
        bb = bbox_in(refs["cmu"])
        assert bb["z0"] == pytest.approx(24.75)
        assert bb["z1"] == pytest.approx(32.375)

    def test_mast_stands_on_the_floor_and_ends_at_46(self, parts):
        bb = bbox_in(parts["mast"])
        assert bb["z0"] == pytest.approx(P.MAST_BOTTOM)
        assert bb["z1"] == pytest.approx(P.MAST_TOP)

    def test_head_46_to_58(self, parts):
        bb = bbox_in(parts["head"])
        assert bb["z0"] == pytest.approx(P.HEAD_BOTTOM)
        assert bb["z1"] == pytest.approx(P.HEAD_TOP)
        assert bb["x1"] - bb["x0"] == pytest.approx(FACE_WIDTH)
        assert bb["z1"] - bb["z0"] == pytest.approx(FACE_HEIGHT)
        assert bb["y1"] - bb["y0"] == pytest.approx(P.HEAD_D)

    def test_head_sits_on_the_flange(self, parts):
        """Steel to acrylic, touching: the moment goes into the mast, not the box."""
        assert bbox_in(parts["mast"])["z1"] == pytest.approx(bbox_in(parts["head"])["z0"])

    def test_fixture_hangs_below_the_head_over_the_block(self, refs):
        from cad.growlab_cad import fixture

        assert bbox_in(refs["fixture"])["z1"] <= P.HEAD_BOTTOM + 1e-6
        env = bbox_in(fixture.build_envelope())
        block = bbox_in(refs["cmu"])
        assert (env["y0"] + env["y1"]) / 2 == pytest.approx((block["y0"] + block["y1"]) / 2)
        assert (env["x0"] + env["x1"]) / 2 == pytest.approx((block["x0"] + block["x1"]) / 2)

    def test_nothing_fabricated_is_below_the_floor(self, parts):
        for name, p in parts.items():
            assert bbox_in(p)["z0"] >= -1e-6, name


class TestNothingInterferes:
    def test_fabricated_parts_do_not_overlap(self, parts):
        """Touching is fine. Shared volume is a build error."""
        clashes = assembly.interferences(parts)
        assert clashes == [], clashes

    def test_cmu_does_not_hit_the_tray(self, parts, refs):
        shared = (refs["cmu"] & parts["tray"]).volume
        assert shared < 1.0  # mm³ — effectively zero

    def test_cmu_sits_on_the_pads(self, parts, refs):
        assert bbox_in(refs["cmu"])["z0"] == pytest.approx(bbox_in(parts["pads"])["z1"])


class TestTheFaceReadsThePanelGeometry:
    """The head's face and the emulator draw from one module."""

    def test_face_without_dial_cuts_is_nearly_solid(self):
        """Dials are witness rings, not holes, until calipers arrive."""
        assert P.DIAL_CUT_DIAMETER is None
        face = head.build_face()
        plate = FACE_WIDTH * FACE_HEIGHT * P.ACRYLIC_T * P.IN**3
        window = next(e for e in SCHEDULE.elements if e.kind == "window")
        removed = window.width * window.height * P.ACRYLIC_T * P.IN**3
        # Plate minus the window, minus the small holes, minus two hairline rings.
        assert face.volume < plate - removed
        assert face.volume > (plate - removed) * 0.97

    def test_window_is_cut_where_the_schedule_puts_it(self):
        window = next(e for e in SCHEDULE.elements if e.kind == "window")
        wx, wz = head.panel_to_world(window.x, window.y)
        # A probe box at the window centre should NOT intersect the face.
        probe = head.box(0.2, P.ACRYLIC_T * 2, 0.2, at=(wx, (head.FACE_Y0 + head.FACE_Y1) / 2, wz - 0.1))
        assert (head.build_face() & probe).volume < 1.0

    def test_dial_witness_ring_marks_the_bezel_but_does_not_cut(self):
        dial = next(e for e in SCHEDULE.elements if e.kind == "dial")
        wx, wz = head.panel_to_world(dial.x, dial.y)
        # A probe at the dial centre should still hit solid acrylic.
        probe = head.box(0.2, P.ACRYLIC_T * 2, 0.2, at=(wx, (head.FACE_Y0 + head.FACE_Y1) / 2, wz - 0.1))
        assert (head.build_face() & probe).volume > 1.0

    def test_a_measured_cut_diameter_opens_the_dial(self, monkeypatch):
        monkeypatch.setattr(P, "DIAL_CUT_DIAMETER", 3.0)
        dial = next(e for e in SCHEDULE.elements if e.kind == "dial")
        wx, wz = head.panel_to_world(dial.x, dial.y)
        probe = head.box(0.2, P.ACRYLIC_T * 2, 0.2, at=(wx, (head.FACE_Y0 + head.FACE_Y1) / 2, wz - 0.1))
        assert (head.build_face() & probe).volume < 1.0

    def test_alternate_layouts_also_build(self):
        from pi.dashboard.panel_geometry import LAYOUTS

        for layout in LAYOUTS:
            assert head.build_face(layout).volume > 0, layout.id


class TestMastDetails:
    def test_shaft_is_hollow(self):
        solid = P.MAST_W * P.MAST_D * (mast.shaft_top() - P.MAST_BOTTOM) * P.IN**3
        assert mast.build_shaft().volume < solid * 0.5

    def test_flange_bolts_match_the_head_bottom(self):
        """Same four points cut the flange and the acrylic bottom panel."""
        pts = mast.flange_bolt_points()
        assert len(pts) == 4
        xs = sorted({round(x, 6) for x, _ in pts})
        ys = sorted({round(y, 6) for _, y in pts})
        assert xs[1] - xs[0] == pytest.approx(P.FLANGE_BOLT_PATTERN_X)
        assert ys[1] - ys[0] == pytest.approx(P.FLANGE_BOLT_PATTERN_Y)


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
