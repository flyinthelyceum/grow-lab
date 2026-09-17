"""A test coupon for the two thread-forming pilots, before the case is printed.

Why this exists
---------------
Both pilot diameters in the case are CHOICE values, and the reasoning behind
them contains one number nobody here has measured: **a vertical hole prints
about 0.2 mm small**. That figure is printer, filament, nozzle and flow
specific. Everything downstream rests on it.

    M2   pilot Ø1.9  ->  prints ~1.7  ->  0.13 of flank engaged per side
    M2.5 pilot Ø2.3  ->  prints ~2.1  ->  0.20 of flank engaged per side

M2's minor diameter is 1.567. If this printer's shrink is 0.3 rather than 0.2,
the M2 pilot comes out at 1.6 and the screw has to cut the thread root instead
of forming the flanks. That is how a boss splits, and the boss is a structural
column: a split corner boss is a reprinted body, which is the long print with
the show face on it. The coupon is minutes.

There is a second unknown the coupon settles cheaply: **how many open/close
cycles a formed thread in PETG really gives.** The case is documented at about
ten. Nobody counted.

What it reproduces, and what it does not
----------------------------------------
The bosses are the real geometry in the real print orientation. Both parts of
the case print top-face-down, which puts the ceiling on the bed and stands
every boss up as a column growing from it, with its pilot a blind hole opening
*upward*. That is what the slab and its bosses are: the slab is the top wall,
the bosses stand on it, and the blind end of each pilot sits on solid material
exactly as it does in the part.

One deliberate difference: the closure bosses are shortened. In the case they
run the full 14 mm interior height, and printing five of those tests nothing —
the thread forms in the top 4 mm and the wall around it is at steady state long
before that. They are cut to 8 mm here, which keeps the whole thread region and
its surrounding wall identical and halves the print.

Sweep both rows around the nominal, print once, and let the screws say which
column was right.
"""

from __future__ import annotations

from . import params as P
from ._shapes import box, cone_z, cyl_z, labelled

_MM = P.MM

# CHOICE: the sweep. Five steps of 0.1 either side of nominal is wider than the
# answer can plausibly be, which is the point -- a coupon that only brackets
# the expected answer cannot tell you the expected answer was wrong.
M2_PILOTS = (1.7 * _MM, 1.8 * _MM, 1.9 * _MM, 2.0 * _MM, 2.1 * _MM)
M25_PILOTS = (2.1 * _MM, 2.2 * _MM, 2.3 * _MM, 2.4 * _MM, 2.5 * _MM)

# CHOICE: room for fingers and a driver between bosses, and for the boss that
# splits to fail without taking its neighbour with it.
PITCH = 14.0 * _MM
ROW_GAP = 16.0 * _MM
MARGIN = 6.0 * _MM

SLAB_T = P.SC_WALL  # the top wall the bosses grow from, at its real thickness

# The board bosses keep their real length; the closure bosses are cut down.
BOARD_BOSS_H = P.SC_BAFFLE_DROP  # 5.0: ceiling to board, the real column
CLOSURE_BOSS_H = 8.0 * _MM  # CHOICE: 4.0 of pilot over 4.0 of solid

# Index pips, so a boss on the bench says which column it is without a card.
PIP_DIA = 1.2 * _MM
PIP_DEPTH = 0.6 * _MM
PIP_PITCH = 2.0 * _MM

# The plate half of the same joint: does an M2.5 countersunk head sit flush in
# 2.5 mm of PETG, or dimple it? Two holes at the real thickness answer it.
CSK_PAD_T = P.SC_BASE_T
CSK_COUNT = 2

_OVER = 0.01 * _MM


def slab_size() -> tuple[float, float]:
    """Outside dimensions of the coupon's base slab, in inches.

    One PITCH-wide column per boss, plus one more at the +X end for the
    countersink pad, which needs to stand clear: a boss sitting on the pad
    would grow from 2.5 mm of material instead of the top wall's 2.0.
    """
    n = max(len(M2_PILOTS), len(M25_PILOTS))
    lx = (n - 1) * PITCH + 2 * MARGIN + 2 * PITCH
    ly = ROW_GAP + 2 * MARGIN
    return lx, ly


def _row_y() -> tuple[float, float]:
    """Y centres of the M2 row and the M2.5 row."""
    return -ROW_GAP / 2, ROW_GAP / 2


def boss_positions() -> list[tuple[float, float, float, float, float, int]]:
    """Every boss: (x, y, boss_dia, pilot_dia, pilot_depth, index).

    Ordered M2 row first, then M2.5, each left to right ascending. The index is
    what the pips count, starting at 1.
    """
    lx, _ = slab_size()
    x0 = -lx / 2 + MARGIN + PITCH / 2
    y_m2, y_m25 = _row_y()
    out: list[tuple[float, float, float, float, float, int]] = []
    for i, d in enumerate(M2_PILOTS):
        out.append((x0 + i * PITCH, y_m2, P.SC_AS7341_BOSS_DIA, d,
                    P.SC_AS7341_PILOT_DEPTH, i + 1))
    for i, d in enumerate(M25_PILOTS):
        out.append((x0 + i * PITCH, y_m25, P.SC_BOSS_DIA, d,
                    P.SC_CLOSURE_PILOT_DEPTH, i + 1))
    return out


def csk_positions() -> list[tuple[float, float]]:
    """Centres of the countersink test holes, on the pad at the +X end."""
    lx, _ = slab_size()
    x = lx / 2 - MARGIN - PITCH / 2
    return [(x, y) for y in _row_y()]


def build() -> "Part":
    """The coupon, sitting on Z=0 the way it prints."""
    lx, ly = slab_size()
    part = box(lx, ly, SLAB_T, at=(0.0, 0.0, 0.0))

    # The countersink pad is the plate's thickness, not the top wall's, so the
    # head seats in exactly the material it will seat in.
    pad_x = csk_positions()[0][0]
    part += box(PITCH, ly, CSK_PAD_T, at=(pad_x, 0.0, 0.0))

    for x, y, boss_dia, pilot_dia, pilot_depth, index in boss_positions():
        height = (BOARD_BOSS_H if boss_dia == P.SC_AS7341_BOSS_DIA
                  else CLOSURE_BOSS_H)
        part += cyl_z(boss_dia, height, at=(x, y, SLAB_T))
        # Blind, opening upward, cut down from the boss's top face -- the same
        # way round as the print, which is the only way the walls around it see
        # the same thermal history.
        part -= cyl_z(pilot_dia, pilot_depth + _OVER,
                      at=(x, y, SLAB_T + height - pilot_depth))
        # Pips, counting the column, recessed into the slab beside the boss.
        span = (index - 1) * PIP_PITCH
        for k in range(index):
            px = x - span / 2 + k * PIP_PITCH
            py = y - boss_dia / 2 - 2.0 * _MM
            part -= cyl_z(PIP_DIA, PIP_DEPTH + _OVER,
                          at=(px, py, SLAB_T - PIP_DEPTH))

    for cx, cy in csk_positions():
        part -= cyl_z(P.SC_SCREW_DIA, CSK_PAD_T + 2 * _OVER,
                      at=(cx, cy, -_OVER))
        # A cone, not a counterbore: the same cut the plate takes.
        part -= cone_z(P.SC_SCREW_CSK, P.SC_SCREW_DIA, P.SC_SCREW_CSK_DEPTH,
                       at=(cx, cy, CSK_PAD_T - P.SC_SCREW_CSK_DEPTH))

    return labelled(part, "thread_coupon")


def for_print() -> dict[str, "Part"]:
    """Already flat on the bed and already the right way up."""
    return {"thread_coupon": build()}
