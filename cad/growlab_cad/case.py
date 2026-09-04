"""The instrument case: a black metal box behind the clear fascia.

The plate from ``face.py`` is its front; behind it a folded sheet box the
meters, Inky, i3, Pi and meter driver mount inside, closed at the back with
a grommeted pass for the loom. It sits on the console ledge and is removed
forward as one unit: fascia off, knob caps off, unplug at the terminal block,
lift out. Everything the apparatus needs to be serviced is then on a bench.

Behind the glass the case is what the eye reads as the instrument; the
cabinet is what carries it.
"""

from __future__ import annotations

from build123d import Part

from pi.dashboard.panel_geometry import FACE_HEIGHT, FACE_WIDTH, Layout, SCHEDULE

from . import params as P
from ._shapes import box, cyl_y, labelled
from .face import build_plate

X0, X1 = P.FACE_X0, P.FACE_X0 + FACE_WIDTH
Z0, Z1 = P.FACE_Z0, P.FACE_Z1
Y0, Y1 = P.CASE_Y0, P.CASE_Y1


def _panel(x0, x1, y0, y1, z0, z1) -> Part:
    return box(x1 - x0, y1 - y0, z1 - z0, at=((x0 + x1) / 2, (y0 + y1) / 2, z0))


def build_body() -> Part:
    """The folded box behind the plate: sides, top, bottom, back."""
    t = P.CASE_SHEET_T
    y_front = Y0 + P.PLATE_T  # the body starts where the plate ends
    left = _panel(X0, X0 + t, y_front, Y1, Z0, Z1)
    right = _panel(X1 - t, X1, y_front, Y1, Z0, Z1)
    bottom = _panel(X0 + t, X1 - t, y_front, Y1, Z0, Z0 + t)
    top = _panel(X0 + t, X1 - t, y_front, Y1, Z1 - t, Z1)
    back = _panel(X0 + t, X1 - t, Y1 - t, Y1, Z0 + t, Z1 - t)
    body = left + right + bottom + top + back
    # Loom pass in the back, low and central: the cables drop into the chase.
    body -= cyl_y(P.CASE_LOOM_DIA, t * 3, at=((X0 + X1) / 2, Y1 - t / 2, Z0 + 1.5))
    return labelled(body, "instrument_case_body")


def build(layout: Layout = SCHEDULE) -> Part:
    return labelled(build_plate(layout) + build_body(), "instrument_case")


def interior() -> tuple[float, float, float]:
    """Clear inside dimensions (W, D, H), for checking what has to fit."""
    t = P.CASE_SHEET_T
    return FACE_WIDTH - 2 * t, P.CASE_D - P.PLATE_T - t, FACE_HEIGHT - 2 * t
