"""The LED fixture — an envelope, not a part — and the arm that carries it.

Two LM301H boards on a heatsink, hung over the block from the mast. No
dimensions exist for the heatsink, so this is a box of plausible size at the
right place. The arm is real enough to check: it runs forward from the mast's
cap over the fixture's back edge, and a cross bar along that edge carries the
fixture, whose centre is off to the side of the mast (the mast is in the dry
bay; the block is centred). The moment arm at the mast — mast centreline to
fixture centreline — is ``params.FIXTURE_CANTILEVER``, derived not asserted.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, labelled


def arm_z0() -> float:
    """The arm sits on the mast's cap."""
    return P.MAST_TOP


def build_arm() -> Part:
    """From the back of the mast's cap forward to the fixture's back edge, plus
    the cross bar along that edge out to both ends of the fixture."""
    z0 = arm_z0()
    y_back = P.MAST_Y + P.MAST_D / 2
    bar_y1 = P.FIXTURE_Y + P.FIXTURE_D / 2
    bar_y0 = bar_y1 - P.FIXTURE_BAR_D
    forward = box(P.FIXTURE_ARM_W, y_back - bar_y0, P.FIXTURE_ARM_T,
                  at=(P.MAST_X, (y_back + bar_y0) / 2, z0))
    bar = box(P.FIXTURE_W, P.FIXTURE_BAR_D, P.FIXTURE_ARM_T,
              at=(P.FIXTURE_X, (bar_y0 + bar_y1) / 2, z0))
    return labelled(forward + bar, "fixture_arm")


def build_envelope() -> Part:
    return labelled(
        box(P.FIXTURE_W, P.FIXTURE_D, P.FIXTURE_H, at=(P.FIXTURE_X, P.FIXTURE_Y, P.FIXTURE_Z)),
        "led_fixture_envelope",
    )


def build() -> Part:
    return labelled(build_arm() + build_envelope(), "fixture")
