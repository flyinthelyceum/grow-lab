"""The instrument face: 1/4 in acrylic, pocketed into the cabinet's front panel.

INSTRUMENT_HEAD_PLANS.md § Face — hole schedule. The box that used to
surround it is superseded; the cabinet is the box now (see ``plinth.py``).

The face's layout is not restated here. It is read from
``pi.dashboard.panel_geometry`` — the same module the ``/panel`` emulator
draws from — so the acrylic that gets cut, the emulator on the dashboard, and
the hole schedule in the docs are one set of numbers. Change a dial position
there and it moves in all three.

What is and is not cut
----------------------
* Window, jewel, amber, knobs, corner screws: cut, from the schedule.
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

# World extents of the face.
X0, X1 = P.FACE_X0, P.FACE_X0 + FACE_WIDTH
Z0, Z1 = P.FACE_Z0, P.FACE_Z1

T = P.ACRYLIC_T
FACE_Y0, FACE_Y1 = P.FACE_Y0, P.FACE_Y0 + T
FACE_MID_Y = (FACE_Y0 + FACE_Y1) / 2

WITNESS_RING_WIDTH = 0.03  # CHOICE: a fine engraved line


def panel_to_world(px: float, py: float) -> tuple[float, float]:
    """Face coordinates (inches, origin bottom-left, Y up) → world (X, Z)."""
    return X0 + px, Z0 + py


def corner_screw_points() -> list[tuple[float, float]]:
    """F1–4, in face coordinates."""
    i = CORNER_SCREW_INSET
    return [(i, i), (FACE_WIDTH - i, i), (i, FACE_HEIGHT - i), (FACE_WIDTH - i, FACE_HEIGHT - i)]


def _through_y(dia: float, x: float, z: float) -> Part:
    """A cutter through the face along Y."""
    return cyl_y(dia, T * 4, at=(x, FACE_MID_Y, z))


def build_face(layout: Layout = SCHEDULE) -> Part:
    """The acrylic face, with the hole schedule from the layout."""
    face = box(FACE_WIDTH, T, FACE_HEIGHT, at=((X0 + X1) / 2, FACE_MID_Y, Z0))

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
            face -= box(e.width, T * 4, e.height, at=(wx, FACE_MID_Y, wz),
                        align=(Align.CENTER,) * 3)

        elif e.kind in ("jewel", "amber", "knob"):
            face -= _through_y(e.width, wx, wz)

    # F1–4: corner screws into the front panel's lip.
    for px, py in corner_screw_points():
        wx, wz = panel_to_world(px, py)
        face -= _through_y(P.FACE_SCREW_DIA, wx, wz)

    return labelled(face, "instrument_face_acrylic")


def build(layout: Layout = SCHEDULE) -> Part:
    return build_face(layout)
