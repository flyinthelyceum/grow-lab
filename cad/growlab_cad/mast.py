"""The vertical armature: a Ø 1.5 in round tube, capped, carrying the light.

The shaft stands on the carcass floor in the dry bay, is held to the fixed rear
panel by U-bolts, passes up through a notch in the rail and the tray, and ends
at a welded disc. Inside it: the drip line to the emitters, the LED pair, the
camera's HDMI and the fixture fans' lead, all entering through a grommeted hole
in the side facing the divider. The sensor loom stays in the cabinet — the
canopy sensors live on the block, not on the mast.

**The cable slot (2026-09-12).** The three fixture leads leave the bore through a
longitudinal slot in the *rear* face, so they reach the travelling collar without
a single cable showing on the mast. It replaces the coiled external lead from the
cap that ``canopy.py`` used to describe. The slot spans the collar's travel and
stops there: 3.75 in of closed tube remain below the cap, 56 in below the slot's
foot. Neither end of the section is opened, which is what keeps the welded cap
doing its job as an end closure — a removable cap would be strictly worse here.

The honest cost is **torsion**. Opening the section drops J from 0.151 to
0.00041 in⁴ — about 365x — so a sideways shove at the fixture now twists the mast
elastically where it used to be rigid: roughly 6° under a casual bump and 20°
under a hard one, worst at full lift where the whole slot lies between the collar
and closed tube. It springs back and nothing yields (12,600 psi shear against
~20,800 at yield). Bending is untouched: 3.1% of allowable against 2.7%.

**Why a tube.** The 2 × 3 hollow section this replaces was never calculated.
The head is 12 lb at a 5.75 in offset — 69 in-lb, against a section modulus of
0.94 in³. That is 73 psi in steel good for 21,600: three tenths of one per cent
of allowable. What actually sized the section was the *bore*, because the
counterweight fell down it. With the counterweight gone there is nothing left
to size the mast but the load, and the load is two LED strips.

Ø 1.5 × 0.065 is 1.0 lb/ft against the old 3.9, carries the head at about 3% of
allowable, and moves 0.16 in at the head under a deliberate 10 lb shove. The
head is welded to nothing here: it rides on a split clamp collar — see
``canopy.py``.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import CENTRE, box, cyl_x, cyl_y, cyl_z, labelled


def shaft_top() -> float:
    """The shaft stops under the cap; the cap's top face is MAST_TOP."""
    return P.MAST_TOP - P.MAST_CAP_T


def strap_heights() -> list[float]:
    """Where the U-bolts land, spread along the length hidden in the cabinet."""
    fixing_length = P.RAIL_BOTTOM_Z - P.MAST_BOTTOM  # the part inside the cabinet
    span = P.MAST_STRAP_PITCH * (P.MAST_STRAP_COUNT - 1)
    start = P.MAST_BOTTOM + (fixing_length - span) / 2
    return [start + i * P.MAST_STRAP_PITCH for i in range(P.MAST_STRAP_COUNT)]


def strap_bolt_x() -> tuple[float, float]:
    """The two leg centres of a U-bolt, straddling the tube."""
    half = P.MAST_STRAP_SPAN / 2
    return P.MAST_X - half, P.MAST_X + half


def line_pass() -> tuple[float, float]:
    """(y, z) of the grommeted hole in the divider-side wall.

    On the tube's own centreline in Y. The divider's matching hole sits a little
    forward of this (``plinth.LINE_PASS_Y``, over the pan rim); a round tube has
    to be drilled at its widest point or the hole comes out a tangential gash,
    so the loom makes up the 0.6 in between them on the way across.
    """
    from .plinth import LINE_PASS_Z

    return P.MAST_Y, LINE_PASS_Z


def slot_y() -> float:
    """Mid-thickness of the rear wall, where the slot cutter is centred."""
    return P.MAST_Y + P.MAST_OD / 2 - P.MAST_WALL / 2


def build_shaft() -> Part:
    length = shaft_top() - P.MAST_BOTTOM
    shaft = cyl_z(P.MAST_OD, length, at=(P.MAST_X, P.MAST_Y, P.MAST_BOTTOM))
    shaft -= cyl_z(
        P.MAST_OD - 2 * P.MAST_WALL,
        length + 1.0,
        at=(P.MAST_X, P.MAST_Y, P.MAST_BOTTOM - 0.5),
    )

    # The line pass, through the wall that faces the divider. One wall only:
    # the cutter is centred in that wall and is not long enough to reach the far
    # side. The U-bolts go round the tube rather than through it.
    #
    # An obround, stretched along the tube's axis rather than across it. Wrap
    # round the circumference is set by the Y width, which stays at the old
    # Ø0.50; the extra height in Z is free and is what passes the camera's
    # connector. Built as two end radii and the rectangle between them.
    y, z = line_pass()
    near_wall_x = P.MAST_X - P.MAST_OD / 2 + P.MAST_WALL / 2
    through = P.MAST_WALL * 3
    straight = P.MAST_LINE_PASS_H - P.MAST_LINE_PASS_DIA
    shaft -= box(through, P.MAST_LINE_PASS_DIA, straight,
                 at=(near_wall_x, y, z), align=CENTRE)
    for dz in (-straight / 2, straight / 2):
        shaft -= cyl_x(P.MAST_LINE_PASS_DIA, through, at=(near_wall_x, y, z + dz))

    # The cable slot, through the rear wall only, spanning the collar's travel.
    # Cut in the same one-wall way: the cutter is centred in the rear wall's
    # thickness and is three walls deep, so it never reaches the front.
    wall_y, through = slot_y(), P.MAST_WALL * 3
    shaft -= box(
        P.MAST_SLOT_W, through, P.MAST_SLOT_LEN,
        at=(P.MAST_X, wall_y, P.MAST_SLOT_Z0),
    )
    # Both ends are drilled round. The top one is sized to pass an HDMI
    # connector at assembly so the welded cap is never disturbed.
    shaft -= cyl_y(P.MAST_SLOT_KEYHOLE_DIA, through, at=(P.MAST_X, wall_y, P.MAST_SLOT_Z1))
    shaft -= cyl_y(P.MAST_SLOT_END_DIA, through, at=(P.MAST_X, wall_y, P.MAST_SLOT_Z0))

    return labelled(shaft, "mast_shaft_tube")


def build_cap() -> Part:
    """A disc welded over the open top."""
    return labelled(
        cyl_z(P.MAST_OD, P.MAST_CAP_T, at=(P.MAST_X, P.MAST_Y, shaft_top())),
        "mast_cap",
    )


def build() -> Part:
    return labelled(build_shaft() + build_cap(), "mast")
