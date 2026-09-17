"""The coupon has to be the same geometry as the part, or it proves nothing.

A test coupon that quietly differs from what it is testing is worse than no
coupon: it gives a number, and the number is wrong. These hold it against
`params.py` rather than against its own constants.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cad.growlab_cad import params as P  # noqa: E402
from cad.growlab_cad import thread_coupon as T  # noqa: E402


def mm(v: float) -> float:
    return v / P.MM


class TestItMirrorsTheRealGeometry:
    def test_board_bosses_are_the_cases_board_bosses(self):
        board = [b for b in T.boss_positions() if b[2] == P.SC_AS7341_BOSS_DIA]
        assert len(board) == len(T.M2_PILOTS)
        for _, _, boss_dia, _, depth, _ in board:
            assert boss_dia == P.SC_AS7341_BOSS_DIA
            assert depth == P.SC_AS7341_PILOT_DEPTH

    def test_closure_bosses_are_the_cases_closure_bosses(self):
        closure = [b for b in T.boss_positions() if b[2] == P.SC_BOSS_DIA]
        assert len(closure) == len(T.M25_PILOTS)
        for _, _, boss_dia, _, depth, _ in closure:
            assert boss_dia == P.SC_BOSS_DIA
            assert depth == P.SC_CLOSURE_PILOT_DEPTH

    def test_the_slab_is_the_top_wall(self):
        """The bosses have to grow from the same thickness they grow from in
        the part, or the first layers see a different thermal history."""
        assert T.SLAB_T == P.SC_WALL

    def test_the_board_boss_keeps_its_real_length(self):
        assert T.BOARD_BOSS_H == P.SC_BAFFLE_DROP

    def test_the_closure_boss_is_shortened_but_keeps_the_whole_thread(self):
        """Cut down to halve the print. Everything the screw touches stays."""
        assert T.CLOSURE_BOSS_H < mm(14.0) * P.MM
        assert T.CLOSURE_BOSS_H >= P.SC_CLOSURE_PILOT_DEPTH + 2.0 * P.MM

    def test_the_countersink_pad_is_the_plates_thickness(self):
        assert T.CSK_PAD_T == P.SC_BASE_T


class TestTheSweepIsUseful:
    def test_each_row_brackets_its_nominal(self):
        assert min(T.M2_PILOTS) < P.SC_AS7341_PILOT < max(T.M2_PILOTS)
        assert min(T.M25_PILOTS) < P.SC_CLOSURE_PILOT < max(T.M25_PILOTS)

    def test_the_nominal_is_actually_on_the_coupon(self):
        """A sweep that skips the value you are shipping is a wasted print."""
        assert any(d == pytest.approx(P.SC_AS7341_PILOT) for d in T.M2_PILOTS)
        assert any(d == pytest.approx(P.SC_CLOSURE_PILOT) for d in T.M25_PILOTS)

    def test_the_steps_are_finer_than_the_uncertainty(self):
        """The unknown is hole shrink, believed 0.2. Steps have to resolve it."""
        for row in (T.M2_PILOTS, T.M25_PILOTS):
            steps = [mm(b - a) for a, b in zip(row, row[1:])]
            assert all(s == pytest.approx(0.1, abs=1e-9) for s in steps)

    def test_the_m2_row_reaches_below_the_screws_minor_diameter(self):
        """The failure being hunted is a pilot at or under M2's 1.567 minor,
        where the screw cuts the root instead of forming the flanks. With
        0.2 of shrink the smallest column prints at 1.5, which is past it."""
        assert mm(min(T.M2_PILOTS)) - 0.2 < 1.567

    def test_every_pilot_leaves_wall_around_it(self):
        for _, _, boss_dia, pilot_dia, _, _ in T.boss_positions():
            wall = (boss_dia - pilot_dia) / 2
            assert mm(wall) >= 1.5, f"only {mm(wall):.2f} mm of wall"


class TestTheLayoutWorksOnABench:
    def test_pips_count_the_column(self):
        # Filter by boss diameter, not pilot: Ø2.1 appears in both rows.
        for boss_dia, row in (
            (P.SC_AS7341_BOSS_DIA, T.M2_PILOTS),
            (P.SC_BOSS_DIA, T.M25_PILOTS),
        ):
            indices = [b[5] for b in T.boss_positions() if b[2] == boss_dia]
            assert indices == list(range(1, len(row) + 1))

    def test_bosses_do_not_touch_each_other(self):
        bosses = T.boss_positions()
        for i, a in enumerate(bosses):
            for b in bosses[i + 1:]:
                if a[1] != b[1]:  # different rows, handled separately
                    continue
                gap = abs(a[0] - b[0]) - (a[2] + b[2]) / 2
                assert mm(gap) >= 4.0, "no room for fingers or a driver"

    def test_the_rows_clear_each_other(self):
        y_m2, y_m25 = T._row_y()
        gap = abs(y_m25 - y_m2) - (P.SC_AS7341_BOSS_DIA + P.SC_BOSS_DIA) / 2
        assert mm(gap) >= 3.0

    def test_the_pad_stands_clear_of_the_last_boss(self):
        """A boss on the pad would grow from 2.5 of material, not 2.0."""
        pad_x = T.csk_positions()[0][0]
        pad_edge = pad_x - T.PITCH / 2
        for x, _, boss_dia, _, _, _ in T.boss_positions():
            assert x + boss_dia / 2 < pad_edge

    def test_everything_sits_inside_the_slab(self):
        lx, ly = T.slab_size()
        for x, y, boss_dia, _, _, _ in T.boss_positions():
            assert abs(x) + boss_dia / 2 <= lx / 2
            assert abs(y) + boss_dia / 2 <= ly / 2

    def test_it_is_small_enough_to_be_worth_printing(self):
        lx, ly = T.slab_size()
        assert mm(lx) <= 120.0
        assert mm(ly) <= 60.0


class TestItPrints:
    """Kernel tests. The coupon has to be one solid for the same reason the
    case does: a bounding box cannot tell a part from a pile of parts."""

    def test_it_is_one_solid(self):
        pytest.importorskip("build123d")
        part = T.build()
        assert len(part.solids()) == 1, "the coupon prints as loose pieces"

    def test_it_sits_on_the_bed(self):
        pytest.importorskip("build123d")
        from cad.growlab_cad._shapes import bbox_in

        bb = bbox_in(T.for_print()["thread_coupon"])
        assert bb["z0"] == pytest.approx(0.0, abs=1e-9)

    def test_its_envelope_is_what_the_layout_says(self):
        pytest.importorskip("build123d")
        from cad.growlab_cad._shapes import bbox_in

        lx, ly = T.slab_size()
        bb = bbox_in(T.build())
        assert bb["x1"] - bb["x0"] == pytest.approx(lx)
        assert bb["y1"] - bb["y0"] == pytest.approx(ly)
        # Tallest thing on it is a closure boss standing on the slab.
        assert bb["z1"] - bb["z0"] == pytest.approx(T.SLAB_T + T.CLOSURE_BOSS_H)

    def test_the_pilots_are_blind(self):
        """Every pilot stops inside its boss. A through hole tests nothing:
        the screw would bottom out in air instead of forming a thread."""
        for _, _, boss_dia, _, depth, _ in T.boss_positions():
            height = (T.BOARD_BOSS_H if boss_dia == P.SC_AS7341_BOSS_DIA
                      else T.CLOSURE_BOSS_H)
            assert depth < height + T.SLAB_T
