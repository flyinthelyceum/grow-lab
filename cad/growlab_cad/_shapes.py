"""Small helpers so the part modules read as dimensions, not kernel calls.

Everything here takes inches and returns build123d parts in millimetres,
positioned in world coordinates. The ``at`` argument is always the part's
**minimum corner in Z** and its **centre in X and Y** unless an ``align`` says
otherwise — that matches how the docs give positions: a plan centre and a
height off the floor.
"""

from __future__ import annotations

from build123d import Align, Box, Cylinder, Location, Part, Pos, Rot

from .params import IN

CENTRE_BOTTOM = (Align.CENTER, Align.CENTER, Align.MIN)
CENTRE = (Align.CENTER, Align.CENTER, Align.CENTER)
MIN = (Align.MIN, Align.MIN, Align.MIN)


def box(
    lx: float,
    ly: float,
    lz: float,
    *,
    at: tuple[float, float, float] = (0.0, 0.0, 0.0),
    align=CENTRE_BOTTOM,
) -> Part:
    """A box of ``lx × ly × lz`` inches with its alignment point at ``at``."""
    return Pos(at[0] * IN, at[1] * IN, at[2] * IN) * Box(
        lx * IN, ly * IN, lz * IN, align=align
    )


def cyl_z(dia: float, length: float, *, at: tuple[float, float, float]) -> Part:
    """A cylinder along Z, centred in X/Y at ``at``, starting at ``at[2]``."""
    return Pos(at[0] * IN, at[1] * IN, at[2] * IN) * Cylinder(
        dia / 2 * IN, length * IN, align=CENTRE_BOTTOM
    )


def cyl_y(dia: float, length: float, *, at: tuple[float, float, float]) -> Part:
    """A cylinder along Y, centred on ``at`` in all three axes.

    For cutting holes through the instrument face, which lies in the XZ plane.
    Made longer than the panel it cuts so the boolean is never coplanar.
    """
    return (
        Pos(at[0] * IN, at[1] * IN, at[2] * IN)
        * Rot(90, 0, 0)
        * Cylinder(dia / 2 * IN, length * IN, align=CENTRE)
    )


def slot_z(lx: float, ly: float, depth: float, *, at: tuple[float, float, float]) -> Part:
    """A rectangular through-slot cutter along Z, centred in X/Y at ``at``."""
    return box(lx, ly, depth, at=at, align=CENTRE)


def labelled(part: Part, label: str) -> Part:
    part.label = label
    return part


def bbox_in(part) -> dict[str, float]:
    """Bounding box in inches — for tests and the build report."""
    bb = part.bounding_box()
    return {
        "x0": bb.min.X / IN, "x1": bb.max.X / IN,
        "y0": bb.min.Y / IN, "y1": bb.max.Y / IN,
        "z0": bb.min.Z / IN, "z1": bb.max.Z / IN,
    }


def location_in(x: float, y: float, z: float) -> Location:
    return Pos(x * IN, y * IN, z * IN)
