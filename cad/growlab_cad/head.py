"""The instrument head: a five-sided acrylic box with a removable face.

INSTRUMENT_HEAD_PLANS.md § Panel schedule, § Face — hole schedule.

The face's layout is not restated here. It is read from
``pi.dashboard.panel_geometry`` — the same module the ``/panel`` emulator
draws from — so the acrylic that gets cut, the emulator on the dashboard, and
the hole schedule in the docs are one set of numbers. Change a dial position
there and it moves in all three.

Sizes follow the schedule's butt-joint convention: sides fit between face and
back (3.50 − 0.50), top and bottom between the sides (9.50 − 0.50), all from
1/4 in stock.

What is and is not cut
----------------------
* Window, jewel, amber, knobs, corner screws, vents, flange bolts, loom pass:
  cut, from the schedule.
* **Dials: not cut** unless ``params.DIAL_CUT_DIAMETER`` is set. The Weston
  301 bezels are pending calipers and the schedule's Ø 2.79 is a Simpson
  figure. Instead the face carries a shallow witness ring at the bezel OD,
  engraved from the back — the reverse-engraving the plans call for — so the
  position is on the part and the cut is not guessed.
* **Dial mounting studs: not cut.** Same reason; their pattern is Simpson's.
* **Inky standoffs: not cut.** "Transfer from the board in hand — do not
  pre-cut."
"""

from __future__ import annotations

from build123d import Part

from pi.dashboard.panel_geometry import (
    CORNER_SCREW_INSET,
    DIAL_BEZEL_OD,
    FACE_HEIGHT,
    FACE_WIDTH,
    SCHEDULE,
    Layout,
)

from . import params as P
from ._shapes import box, cyl_y, cyl_z, labelled
from .mast import flange_bolt_points

# World extents of the head.
X0, X1 = -FACE_WIDTH / 2, FACE_WIDTH / 2
Y0, Y1 = P.MAST_Y - P.HEAD_D / 2, P.MAST_Y + P.HEAD_D / 2
Z0, Z1 = P.HEAD_BOTTOM, P.HEAD_TOP

T = P.ACRYLIC_T
FACE_Y0, FACE_Y1 = Y0, Y0 + T
BACK_Y0, BACK_Y1 = Y1 - T, Y1
INNER_X0, INNER_X1 = X0 + T, X1 - T
INNER_Z0, INNER_Z1 = Z0 + T, Z1 - T

WITNESS_RING_WIDTH = 0.03  # CHOICE: a fine engraved line


def panel_to_world(px: float, py: float) -> tuple[float, float]:
    """Face coordinates (inches, origin bottom-left, Y up) → world (X, Z)."""
    return X0 + px, Z0 + py


def _plate(x0, x1, y0, y1, z0, z1) -> Part:
    return box(x1 - x0, y1 - y0, z1 - z0, at=((x0 + x1) / 2, (y0 + y1) / 2, z0))


def _through_y(dia: float, x: float, z: float) -> Part:
    """A cutter through the face along Y."""
    return cyl_y(dia, T * 4, at=(x, (FACE_Y0 + FACE_Y1) / 2, z))


def build_face(layout: Layout = SCHEDULE) -> Part:
    """The removable front panel, with the hole schedule from the layout."""
    face = _plate(X0, X1, FACE_Y0, FACE_Y1, Z0, Z1)
    face_mid_y = (FACE_Y0 + FACE_Y1) / 2

    for e in layout.elements:
        wx, wz = panel_to_world(e.x, e.y)

        if e.kind == "dial":
            if P.DIAL_CUT_DIAMETER is not None:
                face -= _through_y(P.DIAL_CUT_DIAMETER, wx, wz)
            else:
                # Witness ring at bezel OD, engraved into the BACK face.
                ring_y = FACE_Y1 - P.WITNESS_DEPTH / 2
                outer = cyl_y(DIAL_BEZEL_OD, P.WITNESS_DEPTH, at=(wx, ring_y, wz))
                inner = cyl_y(DIAL_BEZEL_OD - 2 * WITNESS_RING_WIDTH, P.WITNESS_DEPTH + 0.01,
                              at=(wx, ring_y, wz))
                face -= (outer - inner)

        elif e.kind == "window":
            face -= box(e.width, T * 4, e.height, at=(wx, face_mid_y, wz),
                        align=(__import__("build123d").Align.CENTER,) * 3)

        elif e.kind in ("jewel", "amber", "knob"):
            face -= _through_y(e.width, wx, wz)

    # F1–4: corner screws into the corner blocks.
    for px, py in (
        (CORNER_SCREW_INSET, CORNER_SCREW_INSET),
        (FACE_WIDTH - CORNER_SCREW_INSET, CORNER_SCREW_INSET),
        (CORNER_SCREW_INSET, FACE_HEIGHT - CORNER_SCREW_INSET),
        (FACE_WIDTH - CORNER_SCREW_INSET, FACE_HEIGHT - CORNER_SCREW_INSET),
    ):
        wx, wz = panel_to_world(px, py)
        face -= _through_y(P.FACE_SCREW_DIA, wx, wz)

    return labelled(face, "head_face_removable")


def build_back() -> Part:
    return labelled(_plate(X0, X1, BACK_Y0, BACK_Y1, Z0, Z1), "head_back")


def build_sides() -> Part:
    left = _plate(X0, INNER_X0, FACE_Y1, BACK_Y0, Z0, Z1)
    right = _plate(INNER_X1, X1, FACE_Y1, BACK_Y0, Z0, Z1)
    return labelled(left + right, "head_sides")


def _vents(plate: Part, z_centre: float) -> Part:
    """8 slots 2.00 × 0.125 at 0.75 pitch, centred, running front-to-back."""
    n, pitch = P.VENT_SLOT_COUNT, P.VENT_SLOT_PITCH
    x_start = -(pitch * (n - 1)) / 2
    y_mid = (FACE_Y1 + BACK_Y0) / 2
    for i in range(n):
        x = x_start + i * pitch
        plate -= box(P.VENT_SLOT_W, P.VENT_SLOT_L, T * 4,
                     at=(x, y_mid, z_centre - T * 2))
    return plate


def build_top() -> Part:
    top = _plate(INNER_X0, INNER_X1, FACE_Y1, BACK_Y0, INNER_Z1, Z1)
    return labelled(_vents(top, (INNER_Z1 + Z1) / 2), "head_top_vented")


def build_bottom() -> Part:
    bottom = _plate(INNER_X0, INNER_X1, FACE_Y1, BACK_Y0, Z0, INNER_Z0)
    bottom = _vents(bottom, (Z0 + INNER_Z0) / 2)
    # 4 × Ø 0.257 on 2.00 × 1.50 for the flange bolts.
    for x, y in flange_bolt_points():
        bottom -= cyl_z(P.FLANGE_BOLT_CLEARANCE_DIA, T * 4, at=(x, y, Z0 - T * 2))
    # Ø 0.75 loom pass, grommeted.
    bottom -= cyl_z(P.LOOM_PASS_DIA, T * 4, at=(P.MAST_X, P.MAST_Y, Z0 - T * 2))
    return labelled(bottom, "head_bottom_vented_flanged")


def build_corner_blocks() -> Part:
    """Four 0.75 cubes welded into the front corners; the face screws into them."""
    c = P.CORNER_BLOCK
    blocks = None
    for x0 in (INNER_X0, INNER_X1 - c):
        for z0 in (INNER_Z0, INNER_Z1 - c):
            b = _plate(x0, x0 + c, FACE_Y1, FACE_Y1 + c, z0, z0 + c)
            blocks = b if blocks is None else blocks + b
    # Tap drill for M3 (2.5 mm) into each block, on the F1–4 centres.
    for px, py in (
        (CORNER_SCREW_INSET, CORNER_SCREW_INSET),
        (FACE_WIDTH - CORNER_SCREW_INSET, CORNER_SCREW_INSET),
        (CORNER_SCREW_INSET, FACE_HEIGHT - CORNER_SCREW_INSET),
        (FACE_WIDTH - CORNER_SCREW_INSET, FACE_HEIGHT - CORNER_SCREW_INSET),
    ):
        wx, wz = panel_to_world(px, py)
        blocks -= cyl_y(2.5 / 25.4, c, at=(wx, FACE_Y1 + c / 2, wz))
    return labelled(blocks, "head_corner_blocks")


def build_box() -> Part:
    """The five welded panels plus corner blocks — everything but the face."""
    return labelled(
        build_back() + build_sides() + build_top() + build_bottom() + build_corner_blocks(),
        "head_box_welded",
    )


def build(layout: Layout = SCHEDULE) -> Part:
    return labelled(build_box() + build_face(layout), "instrument_head")
