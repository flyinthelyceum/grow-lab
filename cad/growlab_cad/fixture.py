"""The LED fixture — an envelope, not a part.

"Fixture: hangs from the head's underside at 46 in, cantilevered forward to
centre over the block. Hanging it from the head rather than the shaft puts the
moment over the column instead of bending it." — V1_PHYSICAL_BUILD.md § Mast

Two LM301H boards on a heatsink. No dimensions exist for the heatsink, so this
is a box of plausible size at the right place, plus the arm from the flange
boss that carries it. It is here so the assembly reads correctly and so the
cantilever — derived from where the mast and block actually are — is visible.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, labelled
from .mast import shaft_top


def build_arm() -> Part:
    """From the shaft's front face, just under the flange, forward to the fixture.

    Welded to the shaft rather than passing through it. Its rear end is
    coplanar with the shaft's front wall — touching, not overlapping.
    """
    z_top = shaft_top()
    z0 = z_top - P.FIXTURE_ARM_T
    shaft_front = P.MAST_Y - P.MAST_D / 2
    length = shaft_front - P.FIXTURE_Y + P.FIXTURE_D / 2
    y_centre = shaft_front - length / 2
    return labelled(box(P.FIXTURE_ARM_W, length, P.FIXTURE_ARM_T, at=(P.MAST_X, y_centre, z0)), "fixture_arm")


def build_envelope() -> Part:
    z0 = shaft_top() - P.FIXTURE_ARM_T - P.FIXTURE_H
    return labelled(
        box(P.FIXTURE_W, P.FIXTURE_D, P.FIXTURE_H, at=(P.CMU_X, P.FIXTURE_Y, z0)),
        "led_fixture_envelope",
    )


def build() -> Part:
    return labelled(build_arm() + build_envelope(), "fixture")
