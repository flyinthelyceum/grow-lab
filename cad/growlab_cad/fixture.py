"""The LED fixture — an envelope, not a part.

The arm that carries it now lives in ``canopy.py``, welded to the carriage that
rides the mast: the head is height-adjustable and the arm moves with it.

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


def build_envelope() -> Part:
    return labelled(
        box(P.FIXTURE_W, P.FIXTURE_D, P.FIXTURE_H, at=(P.FIXTURE_X, P.FIXTURE_Y, P.FIXTURE_Z)),
        "led_fixture_envelope",
    )


def build() -> Part:
    return build_envelope()
