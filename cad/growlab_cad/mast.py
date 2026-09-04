"""The vertical armature: a 2 × 3 hollow section, capped, carrying the light.

The shaft stands on the carcass floor in the dry bay, bolts through its back
wall into the fixed rear panel, passes up through a notch in the rail and the
tray, and ends at a welded cap plate the fixture arm lands on. Inside it: the
drip line to the emitters and the LED cable, which enter through a grommeted
hole in the side wall facing the divider. Nothing else runs up it — the
sensor loom stays in the cabinet now that the panel is in the front.

"2 x 3 in hollow section" — V1_PHYSICAL_BUILD.md § Mast. Orientation as drawn:
the 3 in dimension front-to-back, where the fixture's moment is.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, cyl_x, cyl_y, labelled


def shaft_top() -> float:
    """The shaft stops under the cap; the cap's top face is MAST_TOP."""
    return P.MAST_TOP - P.MAST_CAP_T


def bolt_heights() -> list[float]:
    """Where the shaft bolts through the rear panel, spread along its hidden length."""
    fixing_length = P.RAIL_BOTTOM_Z - P.MAST_BOTTOM  # the part inside the cabinet
    span = P.MAST_BOLT_PITCH * (P.MAST_BOLT_COUNT - 1)
    start = P.MAST_BOTTOM + (fixing_length - span) / 2
    return [start + i * P.MAST_BOLT_PITCH for i in range(P.MAST_BOLT_COUNT)]


def line_pass() -> tuple[float, float]:
    """(y, z) of the grommeted hole in the divider-side wall."""
    from .plinth import LINE_PASS_Y, LINE_PASS_Z

    return LINE_PASS_Y, LINE_PASS_Z


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

    # The line pass, through the wall that faces the divider.
    y, z = line_pass()
    side_wall_x = P.MAST_X - P.MAST_W / 2 + P.MAST_WALL / 2
    shaft -= cyl_x(P.MAST_LINE_PASS_DIA, P.MAST_WALL * 3, at=(side_wall_x, y, z))

    return labelled(shaft, "mast_shaft_2x3_hss")


def build_cap() -> Part:
    """A plate welded over the open top; the fixture arm is welded to it."""
    return labelled(
        box(P.MAST_W, P.MAST_D, P.MAST_CAP_T, at=(P.MAST_X, P.MAST_Y, shaft_top())),
        "mast_cap",
    )


def build() -> Part:
    return labelled(build_shaft() + build_cap(), "mast")
