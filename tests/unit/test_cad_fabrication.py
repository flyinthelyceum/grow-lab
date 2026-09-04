"""The fabrication pack has to be cuttable, and in the units it claims.

These read the written DXFs back rather than trusting the code that wrote
them, because the two ways this goes wrong are both invisible from inside:
a unit tag that does not match the coordinates (build123d's exporter labels
but does not convert), and a hole that lands off the blank.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("build123d")
ezdxf = pytest.importorskip("ezdxf")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from cad import fabrication as F  # noqa: E402
from cad.growlab_cad import params as P, plinth  # noqa: E402
from cad.growlab_cad.face import corner_screw_points  # noqa: E402
from pi.dashboard.panel_geometry import (  # noqa: E402
    DIAL_BEZEL_OD,
    FACE_HEIGHT,
    FACE_WIDTH,
    LAYOUTS,
    SCHEDULE,
)


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    out = tmp_path_factory.mktemp("fab")
    assert F.main(["--out", str(out)]) == 0
    return out


def read(pack, name):
    return ezdxf.readfile(str(pack / name))


def entities(doc, layer=None, kind=None):
    return [e for e in doc.modelspace()
            if (layer is None or e.dxf.layer == layer)
            and (kind is None or e.dxftype() == kind)]


def circles(doc, layer="cut"):
    return [(round(e.dxf.center.x, 5), round(e.dxf.center.y, 5), round(e.dxf.radius * 2, 5))
            for e in entities(doc, layer, "CIRCLE")]


def extents(doc, layer="cut"):
    xs, ys = [], []
    for e in entities(doc, layer):
        if e.dxftype() == "LINE":
            xs += [e.dxf.start.x, e.dxf.end.x]
            ys += [e.dxf.start.y, e.dxf.end.y]
        elif e.dxftype() == "CIRCLE":
            xs += [e.dxf.center.x - e.dxf.radius, e.dxf.center.x + e.dxf.radius]
            ys += [e.dxf.center.y - e.dxf.radius, e.dxf.center.y + e.dxf.radius]
    return min(xs), min(ys), max(xs), max(ys)


class TestTheFilesSayInchesAndMeanIt:
    """The exporter tags a unit without converting. Both have to agree."""

    @pytest.mark.parametrize("name", ["plate", "case_body", "fascia", "backplate"])
    def test_header_says_inches(self, pack, name):
        assert read(pack, f"{name}.dxf").header["$INSUNITS"] == 1  # 1 = inches

    def test_and_the_coordinates_are_inches_too(self, pack):
        x0, y0, x1, y1 = extents(read(pack, "plate.dxf"))
        assert (x1 - x0) == pytest.approx(FACE_WIDTH, abs=1e-6)
        assert (y1 - y0) == pytest.approx(FACE_HEIGHT, abs=1e-6)
        assert (x1 - x0) < 20, "millimetres would be 241 — the tag would be a lie"


class TestThePlate:
    def test_every_element_of_the_schedule_is_on_it(self, pack):
        doc = read(pack, "plate.dxf")
        cut = circles(doc)
        for e in SCHEDULE.elements:
            if e.kind in ("jewel", "amber", "knob"):
                assert (round(e.x, 5), round(e.y, 5), round(e.width, 5)) in cut, e.id

    def test_the_window_is_a_rectangle_of_the_right_size(self, pack):
        w = next(e for e in SCHEDULE.elements if e.kind == "window")
        doc = read(pack, "plate.dxf")
        lines = entities(doc, "cut", "LINE")
        # The outline is 4; the window adds 4 more at its own extents.
        xs = {round(ln.dxf.start.x, 4) for ln in lines} | {round(ln.dxf.end.x, 4) for ln in lines}
        assert round(w.x - w.width / 2, 4) in xs and round(w.x + w.width / 2, 4) in xs

    def test_the_corner_screws_are_drilled(self, pack):
        cut = circles(read(pack, "plate.dxf"))
        for px, py in corner_screw_points():
            assert (round(px, 5), round(py, 5), round(P.FACE_SCREW_DIA, 5)) in cut

    def test_the_dials_are_scribed_not_cut(self, pack):
        """Pending calipers: a ring on `mark`, and no hole on `cut`."""
        assert P.DIAL_CUT_DIAMETER is None
        doc = read(pack, "plate.dxf")
        dials = [e for e in SCHEDULE.elements if e.kind == "dial"]
        marks = entities(doc, "mark")
        assert len(marks) == len(dials)
        for m in marks:
            assert round(m.dxf.radius * 2, 5) == round(DIAL_BEZEL_OD, 5)
        for d in dials:
            assert not [c for c in circles(doc) if abs(c[0] - d.x) < 1e-6 and abs(c[1] - d.y) < 1e-6]

    def test_a_measured_diameter_turns_the_rings_into_holes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(P, "DIAL_CUT_DIAMETER", 3.0)
        assert F.main(["--out", str(tmp_path)]) == 0
        doc = ezdxf.readfile(str(tmp_path / "plate.dxf"))
        assert entities(doc, "mark") == []
        cut = circles(doc)
        for d in (e for e in SCHEDULE.elements if e.kind == "dial"):
            assert (round(d.x, 5), round(d.y, 5), 3.0) in cut


class TestTheCaseBlankFoldsBackIntoThePart:
    def test_the_blank_is_the_sum_of_the_faces(self, pack):
        m = F.case_metrics()
        x0, y0, x1, y1 = extents(read(pack, "case_body.dxf"))
        assert (x1 - x0) == pytest.approx(m["blank_w"], abs=1e-6)
        assert (y1 - y0) == pytest.approx(m["blank_h"], abs=1e-6)
        assert m["blank_w"] == pytest.approx(m["back_w"] + 2 * (m["wall"] + m["flange"]))
        assert m["blank_h"] == pytest.approx(m["back_h"] + 2 * m["wall"])

    def test_folded_it_is_the_case_that_is_modelled(self):
        """back + two wall thicknesses = the case's outside, both ways."""
        m = F.case_metrics()
        assert m["back_w"] + 2 * m["t"] == pytest.approx(FACE_WIDTH)
        assert m["back_h"] + 2 * m["t"] == pytest.approx(FACE_HEIGHT)
        assert m["wall"] + m["t"] == pytest.approx(P.CASE_D - P.PLATE_T)

    def test_six_bends_and_they_are_on_their_own_layer(self, pack):
        doc = read(pack, "case_body.dxf")
        assert len(entities(doc, "bend")) == 6
        assert all(e.dxftype() == "LINE" for e in entities(doc, "bend"))

    def test_every_hole_lands_on_the_blank(self, pack):
        m = F.case_metrics()
        for x, y, dia in circles(read(pack, "case_body.dxf")):
            assert 0 < x - dia / 2 and x + dia / 2 < m["blank_w"], (x, dia)
            assert 0 < y - dia / 2 and y + dia / 2 < m["blank_h"], (y, dia)

    def test_four_taps_in_the_flanges_mirroring_the_plate(self, pack):
        m = F.case_metrics()
        taps = [c for c in circles(read(pack, "case_body.dxf"))
                if c[2] == pytest.approx(P.CASE_TAP_DIA, abs=1e-5)]
        assert len(taps) == 4
        left = sorted(x for x, _, _ in taps if x < m["blank_w"] / 2)
        right = sorted(m["blank_w"] - x for x, _, _ in taps if x > m["blank_w"] / 2)
        assert left == pytest.approx(right), "the flanges are mirror images"
        # Each tap sits inside its flange, at the plate's own inset from the bend.
        for x, _, _ in taps:
            from_edge = min(x, m["blank_w"] - x)
            assert 0 < from_edge < m["flange"]
            from_bend = m["flange"] - from_edge
            assert from_bend == pytest.approx(corner_screw_points()[0][0] - m["t"])

    def test_the_loom_pass_is_in_the_back(self, pack):
        m = F.case_metrics()
        loom = [c for c in circles(read(pack, "case_body.dxf"))
                if c[2] == pytest.approx(P.CASE_LOOM_DIA, abs=1e-5)]
        assert len(loom) == 1
        x, y, _ = loom[0]
        arm_x, arm_y = m["wall"] + m["flange"], m["wall"]
        assert arm_x < x < arm_x + m["back_w"]
        assert arm_y < y < arm_y + m["back_h"]

    @pytest.mark.parametrize("layout", LAYOUTS, ids=lambda l: l.id)
    def test_the_side_flanges_clear_every_layout(self, layout):
        """A flange behind the plate must not foul what the plate carries.
        This is why there is no flange on the top and bottom walls."""
        reach = P.CASE_SHEET_T + P.CASE_FLANGE
        for e in layout.elements:
            assert min(e.left, FACE_WIDTH - e.right) >= reach, (layout.id, e.id)


class TestTheFascia:
    def test_the_only_holes_are_knobs_and_fixings(self, pack):
        cut = circles(read(pack, "fascia.dxf"))
        knobs = [c for c in cut if c[2] == pytest.approx(
            0.375 + 2 * P.KNOB_HOLE_CLEARANCE, abs=1e-5)]
        screws = [c for c in cut if c[2] == pytest.approx(P.FASCIA_SCREW_DIA, abs=1e-5)]
        assert len(knobs) == 2
        assert len(screws) == 2 * P.FASCIA_SCREW_COLUMNS
        assert len(cut) == len(knobs) + len(screws)

    def test_every_hole_is_clear_of_the_acrylic_edge(self, pack):
        """1/4 in cast acrylic: a hole too near an edge chips out."""
        m = F.fascia_metrics()
        for x, y, dia in circles(read(pack, "fascia.dxf")):
            edge = min(x, y, m["w"] - x, m["h"] - y) - dia / 2
            assert edge >= 0.25, (x, y, edge)

    def test_the_fixings_find_ply_behind_the_glass(self):
        """The band is wider than the front panel, so the rows must land
        inside it: the header above, the ledge below."""
        bz0, bz1 = plinth._fascia_band()
        for wx, wz in plinth.fascia_screw_points():
            assert P.INSIDE_X0 < wx < P.INSIDE_X1, wx
            in_header = wz > bz1 - P.FASCIA_TOP_LIP
            in_ledge = P.FACE_Z0 - P.LEDGE_T < wz < P.FACE_Z0
            assert in_header or in_ledge, wz


class TestTheCutList:
    def test_every_part_has_a_real_size(self):
        data = F.cutlist()
        for r in data["ply"]["parts"]:
            assert r["w"] > 0 and r["h"] > 0 and r["qty"] >= 1, r
        for r in data["steel"]["parts"]:
            assert r["length"] > 0 and r["qty"] >= 1, r
        for r in data["sheet"]:
            assert all(v > 0 for v in r["blank"]), r

    def test_it_agrees_with_the_model(self):
        data = F.cutlist()
        steel = {r["part"]: r for r in data["steel"]["parts"]}
        assert steel["Mast"]["length"] == pytest.approx(P.MAST_TOP)
        assert steel["Frame leg"]["length"] + P.FRAME_TUBE == pytest.approx(P.SHADOW_GAP_H)
        assert steel["Frame ring, front/back"]["length"] == pytest.approx(
            P.PLINTH_W - 2 * P.FRAME_LEG_INSET)
        # The arm's members are its real lengths, not its section.
        from cad.growlab_cad import fixture

        from cad.growlab_cad._shapes import bbox_in

        arm = bbox_in(fixture.build_arm())
        assert steel["Fixture arm, cross bar"]["length"] == pytest.approx(arm["x1"] - arm["x0"])
        assert steel["Fixture arm, forward"]["length"] == pytest.approx(arm["y1"] - arm["y0"])
        sheet = {r["part"]: r for r in data["sheet"]}
        assert sheet["Instrument plate"]["blank"] == [FACE_WIDTH, FACE_HEIGHT]
        assert sheet["Instrument case body"]["blank"][0] == pytest.approx(
            F.case_metrics()["blank_w"])

    def test_it_says_what_is_still_unmeasured(self):
        pending = " ".join(F.cutlist()["pending"]).lower()
        assert "weston" in pending and "inky" in pending

    def test_the_markdown_renders_every_row(self):
        data = F.cutlist()
        md = F.cutlist_markdown(data)
        for r in data["ply"]["parts"] + data["steel"]["parts"]:
            assert r["part"] in md
        assert md.count("|") > 50


def test_the_pack_builds_from_a_clean_shell(tmp_path):
    """The entry point, in its own process, with no GROWLAB_* inherited."""
    import os

    env = {k: v for k, v in os.environ.items() if not k.startswith("GROWLAB_")}
    r = subprocess.run(
        [sys.executable, str(REPO / "cad" / "fabrication.py"), "--out", str(tmp_path)],
        env=env, cwd=str(REPO), capture_output=True, text=True, timeout=600,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SCRIBE RINGS" in r.stdout
    for name in ("plate.dxf", "case_body.dxf", "fascia.dxf", "backplate.dxf",
                 "cutlist.md", "cutlist.json", "README.md"):
        assert (tmp_path / name).exists(), name
