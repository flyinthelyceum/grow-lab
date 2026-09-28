"""The carcass keeps the house CNC joinery grammar, and closes into a box.

Red-teamed 2026-09-28: the cabinet had no joinery at all -- every panel a
butt joint, and the block's weight carried through end grain. These tests hold
the rebuild to the grammar (``carcass.problems``) and to the three things a
joinery model can get wrong without a single rule failing: two parts in the
same place, a housing with nothing in it, and a finding quietly undone.
"""

from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import pytest

pytest.importorskip("build123d")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from cad.growlab_cad import carcass as C, params as P, tray  # noqa: E402
from cad.growlab_cad._shapes import MIN, box  # noqa: E402

IN3 = P.IN ** 3


@pytest.fixture(scope="module")
def solids():
    return {p.name: p.solid() for p in C.panels()}


class TestTheGrammar:
    def test_no_violations(self):
        assert C.problems() == []

    def test_every_housing_is_a_dado_or_a_rabbet(self):
        for p in C.panels():
            for pk in p.pockets:
                assert pk.kind in ("dado", "rabbet"), (p.name, pk.kind)

    def test_widths_are_measured_stock_never_nominal(self):
        """Rule 3, the one a nominal figure breaks silently."""
        for p in C.panels():
            for pk in p.pockets:
                assert p.across(pk) == pytest.approx(sum(pk.mates) + C.CLR)
                assert all(m in (C.TA, C.HA, P.FASCIA_TOP_LIP) for m in pk.mates), pk.note

    def test_the_check_catches_a_stopped_dado(self, monkeypatch):
        """The rule check is only worth something if it fails a bad panel."""
        p = C.by_name()["floor"]
        x0, x1, y0, y1, z0, z1 = p.pockets[0].box
        p.pockets[0] = C.Pocket((x0 + 1.0, x1, y0, y1, z0, z1), "dado", (C.HA,), "short")
        monkeypatch.setattr(C, "panels", lambda: [p])
        assert any("(rule 5)" in m for m in C.problems())

    def test_one_pocketed_face_and_it_is_not_the_finished_one(self):
        for p in C.panels():
            if p.pockets or p.bores:
                assert p.pocket_face not in ("none", p.finish_face), p.name


class TestTheBoxCloses:
    def test_no_two_panels_share_volume(self, solids):
        for a, b in combinations(solids, 2):
            assert (solids[a] & solids[b]).volume / IN3 < 1e-6, (a, b)

    def test_every_housing_has_its_part_in_it(self, solids):
        for p in C.panels():
            for pk in p.pockets:
                x0, x1, y0, y1, z0, z1 = pk.box
                probe = box(x1 - x0, y1 - y0, z1 - z0, at=(x0, y0, z0), align=MIN)
                filled = sum((probe & s).volume for n, s in solids.items() if n != p.name)
                assert filled / probe.volume > 0.15, (p.name, pk.note)

    def test_the_outside_is_the_modelled_outside(self):
        n = C.by_name()
        assert n["side_left"].box[0] == pytest.approx(-P.PLINTH_W / 2)
        assert n["side_right"].box[1] == pytest.approx(P.PLINTH_W / 2)
        assert n["rear"].box[3] == pytest.approx(P.PLINTH_D)
        assert n["floor"].box[4] == pytest.approx(P.SHADOW_GAP_H)
        assert n["side_left"].box[5] == pytest.approx(P.TRAY_RIM_Z)

    def test_the_tray_sits_on_the_deck(self):
        assert C.by_name()["deck"].box[5] == pytest.approx(P.TRAY_FLOOR_Z - P.TRAY_T)

    def test_the_case_sits_on_the_ledge(self):
        assert C.by_name()["ledge"].box[5] == pytest.approx(P.FACE_Z0)


class TestTheFindingsStayFixed:
    """Each of these was a red-team finding. A test per finding, so undoing one
    is a failure rather than a regression nobody notices."""

    def test_the_block_bears_on_a_housed_deck(self):
        deck = C.by_name()["deck"]
        housed_in = {pk.note for s in ("side_left", "side_right", "rear")
                     for pk in C.by_name()[s].pockets}
        assert any("deck" in n for n in housed_in)
        for px, py in tray.pad_centres():
            assert deck.box[0] < px < deck.box[1] and deck.box[2] < py < deck.box[3]
        assert len([h for h in deck.holes if "pad" in h.note]) == 4

    def test_the_shear_walls_are_housed_on_three_edges(self):
        notes = [pk.note for p in C.panels() for pk in p.pockets]
        assert sum("partition" in n for n in notes) >= 4  # left side, floor, deck, divider
        assert sum("divider" in n for n in notes) >= 3  # floor, deck, rear

    def test_the_fascia_screws_into_a_housed_apron(self):
        apron = C.by_name()["apron"]
        assert apron.t == pytest.approx(C.TA), "a full-thickness strip, not a 0.35 lip"
        assert apron.box[2] == pytest.approx(P.FASCIA_POCKET), "its face is the glass's backstop"
        assert len(apron.holes) == P.FASCIA_SCREW_COLUMNS

    def test_nothing_visible_is_dogboned(self):
        """Rule 6. The band notch is a reveal taller than the glass instead."""
        from cad.growlab_cad.plinth import _fascia_band

        bz0, bz1 = _fascia_band()
        notch = C.by_name()["side_left"].cutouts[0]
        assert notch[4] == pytest.approx(bz0 - P.BAND_REVEAL)
        assert notch[5] == pytest.approx(bz1 + P.BAND_REVEAL)
        assert P.BAND_REVEAL >= P.ROUTER_BIT_DIA / 2

    def test_the_shelf_stands_on_pins(self):
        n = C.by_name()
        side_pins = [b for b in n["side_left"].bores if b.kind == "pin"]
        div_pins = [h for h in n["divider"].holes if "pin" in h.note]
        assert len(side_pins) == len(div_pins) == 2 * P.SHELF_PIN_N
        # The top pin row carries the shelf at the design height.
        top = max(z for _, z in C.shelf_pins())
        assert top + P.SHELF_PIN_D / 2 == pytest.approx(P.SHELF_H - C.TA)

    def test_the_door_hangs_on_cups_in_its_inside_face(self):
        door = C.by_name()["door"]
        assert [b.kind for b in door.bores] == ["cup", "cup"]
        assert door.pocket_face == "inside"

    def test_the_front_panel_is_knock_down(self):
        front = C.by_name()["front"]
        assert len([h for h in front.holes if "M5" in h.note]) == 4
        assert not front.pockets, "rule 9: bolts through holes, no counterbores"

    def test_the_floor_bolts_to_the_frame_ring(self):
        floor = C.by_name()["floor"]
        ring = [h for h in floor.holes if "frame" in h.note]
        assert len(ring) == 4
        i, t = P.FRAME_LEG_INSET, P.FRAME_TUBE
        for h in ring:
            assert abs(abs(h.at[0]) - (P.PLINTH_W / 2 - i - t / 2)) < 1e-9
            # Clear of the partition's dado in the floor.
            assert not (C.PART_Y0 - 0.2 < h.at[1] < C.PART_Y1 + 0.2)

    def test_the_pan_still_leaves_by_the_door(self):
        w = C.OPEN_X1 - C.OPEN_X0
        h = C.OPEN_Z1 - C.OPEN_Z0
        assert w > P.RESERVOIR_L
        assert h > P.RESERVOIR_H + P.RESERVOIR_LIFT_CLEARANCE
