"""The vertical armature: a 2 × 3 hollow section and its top flange.

The shaft carries the drip line and sensor loom inside it, stands on the
carcass floor, bolts through its back wall into the full-height rear panel,
passes up through a notch in the tray, and ends at the flange the instrument
head bolts down onto.

"The acrylic holds instruments, not loads. The 2 × 3 in shaft ends in the
1/4 in steel flange … The cantilever's moment goes steel-to-steel and never
through the box."  — INSTRUMENT_HEAD_PLANS.md § Structure
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, cyl_y, cyl_z, labelled


def shaft_top() -> float:
    """The shaft stops under the flange; the flange's top face is the head bottom."""
    return P.MAST_TOP - P.FLANGE_T


def bolt_heights() -> list[float]:
    """Where the shaft bolts through the rear panel, spread along its hidden length."""
    fixing_length = P.PLINTH_H - P.MAST_BOTTOM  # the part inside the cabinet
    span = P.MAST_BOLT_PITCH * (P.MAST_BOLT_COUNT - 1)
    start = P.MAST_BOTTOM + (fixing_length - span) / 2
    return [start + i * P.MAST_BOLT_PITCH for i in range(P.MAST_BOLT_COUNT)]


def flange_bolt_points() -> list[tuple[float, float]]:
    """The 2.00 × 1.50 pattern, centred on the shaft, in plan."""
    dx, dy = P.FLANGE_BOLT_PATTERN_X / 2, P.FLANGE_BOLT_PATTERN_Y / 2
    return [
        (P.MAST_X - dx, P.MAST_Y - dy),
        (P.MAST_X + dx, P.MAST_Y - dy),
        (P.MAST_X - dx, P.MAST_Y + dy),
        (P.MAST_X + dx, P.MAST_Y + dy),
    ]


def build_shaft() -> Part:
    length = shaft_top() - P.MAST_BOTTOM
    outer = box(P.MAST_W, P.MAST_D, length, at=(P.MAST_X, P.MAST_Y, P.MAST_BOTTOM))
    inner = box(
        P.MAST_W - 2 * P.MAST_WALL,
        P.MAST_D - 2 * P.MAST_WALL,
        length + 1.0,
        at=(P.MAST_X, P.MAST_Y, P.MAST_BOTTOM - 0.5),
    )
    shaft = outer - inner

    # Through-bolts into the rear panel: holes through the back wall only.
    back_wall_y = P.MAST_Y + P.MAST_D / 2 - P.MAST_WALL / 2
    for z in bolt_heights():
        shaft -= cyl_y(P.MAST_BOLT_DIA, P.MAST_WALL * 3, at=(P.MAST_X, back_wall_y, z))

    return labelled(shaft, "mast_shaft_2x3_hss")


def build_flange() -> Part:
    plate = box(
        P.FLANGE_W, P.FLANGE_D, P.FLANGE_T,
        at=(P.MAST_X, P.MAST_Y, shaft_top()),
    )
    # 4 × M6 tapped — modelled at tap drill (5.0 mm) so it reads as tapped.
    for x, y in flange_bolt_points():
        plate -= cyl_z(5.0 / 25.4, P.FLANGE_T + 1.0, at=(x, y, shaft_top() - 0.5))
    # Loom pass continues up through the flange into the head.
    plate -= cyl_z(P.LOOM_PASS_DIA, P.FLANGE_T + 1.0, at=(P.MAST_X, P.MAST_Y, shaft_top() - 0.5))
    return labelled(plate, "mast_flange_quarter_steel")


def build() -> Part:
    return labelled(build_shaft() + build_flange(), "mast")
