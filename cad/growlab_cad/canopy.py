"""The counterweighted canopy: the head rides the mast instead of being welded to it.

`LIGHTING_SYSTEM.md` § Light Positioning has always required this — "Height
should remain adjustable", to accommodate plant growth, allow intensity tuning
and prevent light stress — and named a pulley or sliding mount. It was never
specced and never modelled, and the head sat welded to the mast cap at one fixed
height. A ranunculus reaches 12-18 in; at 15 in the canopy touched the fixture
and at 18 in it was 3 in inside it.

The mechanism, from the top down:

* a **sheave** in the mast's cap;
* a **cable** from the carriage, up the mast's back face, over the sheave, and
  down the mast's own bore;
* a **counterweight** sliding in that bore. This is the one job the bore is good
  for. It was rejected as an air duct because 4.9 in2 cannot pass a 120 mm fan's
  flow; a falling weight has no such objection;
* a **carriage** — a sleeve swallowing the shaft, with the arm and cross bar
  welded to it as one piece. Rectangular section means it cannot rotate, and the
  sleeve length sets how much the head can rack under its own cantilever.

**The loom problem, and why the conduit is here.** The mast bore already carried
the drip line and the LED cable. A slug sliding 21 in up and down that bore would
chafe them. So the loom now runs in a fixed tube in one corner of the bore and
the slug is notched around it — which turns the conduit into the weight's guide
rail and stops it swinging. The drip line does not move: the emitters are at a
fixed height. **The LED cable does**, and needs a service loop at the carriage
sized for the full travel; that is noted in the build docs, not modelled here.

**Balance.** A perfectly balanced head drifts. Size the slug slightly light -- 90
to 95 per cent of the head -- so it settles down rather than creeping up, and
lock it with a cam collar on the carriage. `CW_MASS_LB` is an estimate and the
one number here that wants a scale before anything is cut.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, cyl_y, cyl_z, labelled


def bore() -> tuple[float, float]:
    """Internal width and depth of the mast section."""
    return P.MAST_W - 2 * P.MAST_WALL, P.MAST_D - 2 * P.MAST_WALL


def conduit_xy() -> tuple[float, float]:
    """The loom tube sits in one corner of the bore, clear of the slug's body."""
    bw, bd = bore()
    r = P.CONDUIT_DIA / 2
    return (P.MAST_X - bw / 2 + r + 0.06, P.MAST_Y - bd / 2 + r + 0.06)


def slug_section() -> tuple[float, float, float]:
    """(width, depth, area) of the counterweight, after clearance and the notch."""
    bw, bd = bore()
    w, d = bw - 2 * P.CW_CLEAR, bd - 2 * P.CW_CLEAR
    notch = (P.CONDUIT_DIA + 2 * P.CW_CLEAR) ** 2
    return w, d, w * d - notch


def slug_length() -> float:
    """Length of slug needed to reach CW_MASS_LB at CW_DENSITY."""
    return P.CW_MASS_LB / (slug_section()[2] * P.CW_DENSITY)


def sheave_z() -> float:
    """The sheave's centre, tucked under the cap."""
    return P.MAST_TOP - P.MAST_CAP_T - P.SHEAVE_DIA / 2


def counterweight_z() -> float:
    """Top of the slug, for the head's drawn position.

    The weight rises as the head falls, so it is highest at the bottom of travel.
    """
    highest = sheave_z() - P.SHEAVE_DIA / 2 - 0.5
    return highest - (P.FIXTURE_Z - P.FIXTURE_Z_MIN)


def build_carriage() -> Part:
    """Sleeve, arm and cross bar as one weldment.

    Fabricated, and modelled as one part because that is what it is -- welded
    together, it cannot interfere with itself, and splitting it would report a
    false clash between the sleeve and the arm it carries.
    """
    clear, wall = P.CARRIAGE_CLEAR, P.CARRIAGE_WALL
    inner_w, inner_d = P.MAST_W + 2 * clear, P.MAST_D + 2 * clear
    z0 = P.CARRIAGE_Z - P.CARRIAGE_H / 2

    sleeve = box(inner_w + 2 * wall, inner_d + 2 * wall, P.CARRIAGE_H,
                 at=(P.MAST_X, P.MAST_Y, z0))
    sleeve -= box(inner_w, inner_d, P.CARRIAGE_H + 1,
                  at=(P.MAST_X, P.MAST_Y, z0 - 0.5))

    # The arm cantilevers from the sleeve's FRONT face. It used to run from the
    # mast's back face, which was fine when it sat on the cap above everything;
    # at mid-height that drives it straight through the shaft and the conduit.
    y_front = P.MAST_Y - P.MAST_D / 2 - clear - wall
    bar_y1 = P.FIXTURE_Y + P.FIXTURE_D / 2
    bar_y0 = bar_y1 - P.FIXTURE_BAR_D
    arm = box(P.FIXTURE_ARM_W, y_front - bar_y0, P.FIXTURE_ARM_T,
              at=(P.MAST_X, (y_front + bar_y0) / 2, P.CARRIAGE_Z))
    bar = box(P.FIXTURE_W, P.FIXTURE_BAR_D, P.FIXTURE_ARM_T,
              at=(P.FIXTURE_X, (bar_y0 + bar_y1) / 2, P.CARRIAGE_Z))
    return labelled(sleeve + arm + bar, "canopy_carriage")


def build_counterweight() -> Part:
    w, d, _ = slug_section()
    length = slug_length()
    slug = box(w, d, length, at=(P.MAST_X, P.MAST_Y, counterweight_z() - length))
    cx, cy = conduit_xy()
    slug -= cyl_z(P.CONDUIT_DIA + 2 * P.CW_CLEAR, length + 1,
                  at=(cx, cy, counterweight_z() - length - 0.5))
    return labelled(slug, "counterweight")


def build_conduit() -> Part:
    """The loom's tube: fixed, full height, and the slug's guide rail."""
    cx, cy = conduit_xy()
    top = sheave_z() - P.SHEAVE_DIA / 2
    return labelled(
        cyl_z(P.CONDUIT_DIA, top - P.RAIL_BOTTOM_Z, at=(cx, cy, P.RAIL_BOTTOM_Z)),
        "loom_conduit",
    )


def build_sheave() -> Part:
    """Bought: a ball-race sheave on a shoulder bolt through the mast head."""
    return labelled(
        cyl_y(P.SHEAVE_DIA, P.SHEAVE_T, at=(P.MAST_X, P.MAST_Y, sheave_z())),
        "sheave",
    )
