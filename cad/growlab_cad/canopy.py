"""The canopy carriage: a split clamp collar the head rides on.

`LIGHTING_SYSTEM.md` § Light Positioning has always required this — "Height
should remain adjustable", to accommodate plant growth, allow intensity tuning
and prevent light stress — and named a pulley or sliding mount. It was never
specced and never modelled, and the head sat welded to the mast cap at one fixed
height. A ranunculus reaches 12–18 in; at 15 in the canopy touched the fixture
and at 18 in it was 3 in inside it.

**Why there is no counterweight.** There was one, briefly: a sheave in the cap,
a cable down the mast's own bore, and a 12 lb steel slug falling inside it. It
worked on paper and it cost the whole silhouette, because the bore had to be big
enough to swallow the slug, which meant a 2 × 3 section, which meant a mast
sized like structure for a building to hold up two LED strips. Cutting the
counterweight cut the bore, the section and about three quarters of the mast's
visual weight with it.

What replaces it is the thing lab stands and mic booms use: a **split clamp
collar**. One part holds the head *and* locks its height. A saw kerf runs from
the bore out through a boss on the back; two pinch bolts across the kerf close
the collar onto the tube. Friction takes both loads — the 12 lb of head hanging
on it, and the 69 in-lb of moment trying to twist it round the tube — so a round
mast needs no key or flat to stop the head rotating.

**Setting the height is a two-handed job**, and deliberately so: slacken both
bolts, take the head's weight, slide, re-tighten. Twelve pounds at chest height
is a lift, not a nudge. It is also something that happens perhaps twice in a
growing season.

**The loom.** With the slug gone the bore is the loom's again: drip line and LED
cable up the inside, out under the cap. The drip line does not move — the
emitters are at a fixed height. The LED cable does, over the full 21 in of
travel, and takes up the slack in a coiled lead from the cap to the arm. That is
noted in the build docs, not modelled here.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, cyl_x, cyl_z, labelled

KERF = 0.09  # CHOICE: the saw cut the pinch bolts close
BOSS_W = 1.0  # CHOICE: across the kerf, in X
BOSS_PROJECTION = 0.45  # CHOICE: how far the boss stands off the collar's back
PINCH_BOLT_DIA = 0.28  # 1/4-20 clearance
PINCH_BOLT_SPACING = 2.2  # CHOICE: either side of the collar's mid-height


def collar_od() -> float:
    return P.MAST_OD + 2 * P.CARRIAGE_CLEAR + 2 * P.CARRIAGE_WALL


def collar_id() -> float:
    return P.MAST_OD + 2 * P.CARRIAGE_CLEAR


def collar_front_y() -> float:
    """The flat the fixture arm is welded to."""
    return P.MAST_Y - collar_od() / 2


def build_carriage() -> Part:
    """Collar, arm and cross bar as one weldment.

    Fabricated, and modelled as one part because that is what it is — welded
    together, it cannot interfere with itself, and splitting it would report a
    false clash between the collar and the arm it carries.
    """
    z0 = P.CARRIAGE_Z - P.CARRIAGE_H / 2
    od, idia = collar_od(), collar_id()

    collar = cyl_z(od, P.CARRIAGE_H, at=(P.MAST_X, P.MAST_Y, z0))

    # A flat pad on the front, so the arm lands on a flat rather than a tangent,
    # and a boss on the back to carry the pinch bolts. Both run the full height
    # of the collar, so the whole thing saws out of one piece.
    y_front = collar_front_y()
    collar += box(P.FIXTURE_ARM_W, P.MAST_Y - y_front, P.CARRIAGE_H,
                  at=(P.MAST_X, (y_front + P.MAST_Y) / 2, z0))
    boss_y1 = P.MAST_Y + od / 2 + BOSS_PROJECTION
    collar += box(BOSS_W, boss_y1 - P.MAST_Y, P.CARRIAGE_H,
                  at=(P.MAST_X, (P.MAST_Y + boss_y1) / 2, z0))

    # The bore, then the kerf: from the bore straight out through the back of
    # the boss, leaving the two halves joined only round the front.
    collar -= cyl_z(idia, P.CARRIAGE_H + 1, at=(P.MAST_X, P.MAST_Y, z0 - 0.5))
    collar -= box(KERF, boss_y1 - P.MAST_Y + 0.5, P.CARRIAGE_H + 1,
                  at=(P.MAST_X, (P.MAST_Y + boss_y1 + 0.5) / 2, z0 - 0.5))

    # Two pinch bolts across the kerf.
    bolt_y = P.MAST_Y + od / 2 + BOSS_PROJECTION / 2
    for dz in (-PINCH_BOLT_SPACING / 2, PINCH_BOLT_SPACING / 2):
        collar -= cyl_x(PINCH_BOLT_DIA, BOSS_W * 2,
                        at=(P.MAST_X, bolt_y, P.CARRIAGE_Z + dz))

    # The arm cantilevers forward off that front pad to the fixture's back edge.
    bar_y1 = P.FIXTURE_Y + P.FIXTURE_D / 2
    bar_y0 = bar_y1 - P.FIXTURE_BAR_D
    arm = box(P.FIXTURE_ARM_W, y_front - bar_y0, P.FIXTURE_ARM_T,
              at=(P.MAST_X, (y_front + bar_y0) / 2, P.CARRIAGE_Z))
    bar = box(P.FIXTURE_W, P.FIXTURE_BAR_D, P.FIXTURE_ARM_T,
              at=(P.FIXTURE_X, (bar_y0 + bar_y1) / 2, P.CARRIAGE_Z))
    return labelled(collar + arm + bar, "canopy_carriage")
