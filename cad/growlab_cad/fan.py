"""The canopy fan and the bracket that carries it.

The fan is a bought part at a known size -- Noctua NF-A12x25, 120 x 120 x 25 mm
-- so unlike the LED fixture this is the real envelope rather than a plausible
box. What was missing was never the size. The documents specify the fan's rail,
its 4-pin wiring, its PWM pin, its 25 kHz frequency and its whole control law,
and do not say anywhere what holds it or where it points.

**It blows in -Y: back to front, across the block's short axis.** That is the
decision worth recording. The two cores are separated along X, so blowing along
X would hand the downwind core the upwind core's exhaust; blowing along Y gives
both the same air over a 7.6 in path. The short path also keeps velocity up at
the low duties the gust field spends most of its time at.

It sits mid-canopy -- between the media surface and the fixture -- and centred
on the block rather than on the mast, because the mast is off in the dry bay and
a fan hung on its centreline would favour one end of the block. That offset is
what the bracket exists to cross.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, labelled


def build_envelope() -> Part:
    """The fan itself. Bought, so this is its catalogue size."""
    # FAN_Z is the fan's axis, not its underside -- what matters for a fan is
    # where the air goes. box() aligns bottom in Z, hence the half offset.
    return labelled(
        box(P.FAN_SIZE, P.FAN_THICK, P.FAN_SIZE,
            at=(P.FAN_X, P.FAN_Y, P.FAN_Z - P.FAN_SIZE / 2)),
        "canopy_fan",
    )


def build_bracket() -> Part:
    """A flat bar from the mast's front face out to the fan's centreline.

    Fabricated, unlike the fan. Kept deliberately plain: the real bracket wants
    vibration isolation and the fan's own 105 mm screw pattern, and neither is
    worth inventing before the parts are in hand and the mast is welded.
    """
    y_face = P.MAST_Y - P.MAST_D / 2
    x0, x1 = P.FAN_X, P.MAST_X + P.MAST_W / 2
    return labelled(
        box(x1 - x0, P.FAN_BRACKET_T, P.FAN_BRACKET_W,
            at=((x0 + x1) / 2, y_face - P.FAN_BRACKET_T / 2,
                P.FAN_Z - P.FAN_BRACKET_W / 2)),
        "fan_bracket",
    )


def build() -> Part:
    return build_envelope()
