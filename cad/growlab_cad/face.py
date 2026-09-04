"""The instrument plate: the front of the instrument case, carrying the dials,
the e-ink window and the knobs.

INSTRUMENT_HEAD_PLANS.md § Face — hole schedule.

In the fascia form (the design) this is 1/8 in black aluminium, the front of
the removable case in ``case.py``, sitting behind the clear fascia. In the box
form (kept for the record) it is the 1/4 in acrylic face pocketed flush into
the ply front. Same schedule either way.

The layout is not restated here. It is read from
``pi.dashboard.panel_geometry`` — the same module the ``/panel`` emulator
draws from — so the plate that gets cut, the emulator on the dashboard, and
the hole schedule in the docs are one set of numbers. Change a dial position
there and it moves in all three.

What is and is not cut
----------------------
* Window, jewel, amber, knobs, corner screws: cut, from the schedule.
* **Dials: not cut** unless ``params.DIAL_CUT_DIAMETER`` is set. The Weston
  301 bezels are pending calipers and the schedule's Ø 2.79 is a Simpson
  figure. Instead the plate carries a shallow witness ring at the bezel OD on
  its back — a scribe line on metal, an engraving on acrylic — so the
  position is on the part and the cut is not guessed.
* **Dial mounting studs: not cut.** Same reason; their pattern is Simpson's.
* **Inky standoffs: not cut.** "Transfer from the board in hand — do not
  pre-cut."
"""

from __future__ import annotations

from build123d import Align, Part

from pi.dashboard.panel_geometry import (
    CORNER_SCREW_INSET,
    DIAL_BEZEL_OD,
    FACE_HEIGHT,
    FACE_WIDTH,
    SCHEDULE,
    Layout,
)

from . import params as P
from ._shapes import box, cyl_y, labelled

# World extents of the plate.
X0, X1 = P.FACE_X0, P.FACE_X0 + FACE_WIDTH
Z0, Z1 = P.FACE_Z0, P.FACE_Z1

T = P.FACE_T
FACE_Y0, FACE_Y1 = P.FACE_Y0, P.FACE_Y0 + T
FACE_MID_Y = (FACE_Y0 + FACE_Y1) / 2

WITNESS_RING_WIDTH = 0.03  # CHOICE: a fine line


def panel_to_world(px: float, py: float) -> tuple[float, float]:
    """Plate coordinates (inches, origin bottom-left, Y up) → world (X, Z)."""
    return X0 + px, Z0 + py


def corner_screw_points() -> list[tuple[float, float]]:
    """F1–4, in plate coordinates."""
    i = CORNER_SCREW_INSET
    return [(i, i), (FACE_WIDTH - i, i), (i, FACE_HEIGHT - i), (FACE_WIDTH - i, FACE_HEIGHT - i)]


def knob_points(layout: Layout = SCHEDULE) -> list[tuple[float, float, float]]:
    """(world X, world Z, diameter) of every knob — the fascia gets a hole for each."""
    pts = []
    for e in layout.elements:
        if e.kind == "knob":
            wx, wz = panel_to_world(e.x, e.y)
            pts.append((wx, wz, e.width))
    return pts


def _through_y(dia: float, x: float, z: float) -> Part:
    """A cutter through the plate along Y."""
    return cyl_y(dia, T * 4, at=(x, FACE_MID_Y, z))


def build_plate(layout: Layout = SCHEDULE) -> Part:
    """The plate, with the hole schedule from the layout."""
    plate = box(FACE_WIDTH, T, FACE_HEIGHT, at=((X0 + X1) / 2, FACE_MID_Y, Z0))

    for e in layout.elements:
        wx, wz = panel_to_world(e.x, e.y)

        if e.kind == "dial":
            if P.DIAL_CUT_DIAMETER is not None:
                plate -= _through_y(P.DIAL_CUT_DIAMETER, wx, wz)
            else:
                # Witness ring at bezel OD, on the BACK.
                ring_y = FACE_Y1 - P.WITNESS_DEPTH / 2
                outer = cyl_y(DIAL_BEZEL_OD, P.WITNESS_DEPTH, at=(wx, ring_y, wz))
                inner = cyl_y(DIAL_BEZEL_OD - 2 * WITNESS_RING_WIDTH, P.WITNESS_DEPTH + 0.01,
                              at=(wx, ring_y, wz))
                plate -= (outer - inner)

        elif e.kind == "window":
            plate -= box(e.width, T * 4, e.height, at=(wx, FACE_MID_Y, wz),
                         align=(Align.CENTER,) * 3)

        elif e.kind in ("jewel", "amber", "knob"):
            plate -= _through_y(e.width, wx, wz)

    # F1–4: corner screws — into the case's flanges, or the ply lip in the box form.
    for px, py in corner_screw_points():
        wx, wz = panel_to_world(px, py)
        plate -= _through_y(P.FACE_SCREW_DIA, wx, wz)

    label = "instrument_plate_aluminium" if P.FASCIA else "instrument_face_acrylic"
    return labelled(plate, label)


# The box form's name for the same part.
build_face = build_plate


def build(layout: Layout = SCHEDULE) -> Part:
    return build_plate(layout)
