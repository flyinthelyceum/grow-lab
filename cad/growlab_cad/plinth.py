"""The plinth: a cabinet carcass on a recessed base.

V1_PHYSICAL_BUILD.md § Station geometry. The carcass sides rise to the tray
rim (26) so the tray nests inside and finishes flush; a rail at 24 carries the
tray floor and, through the tray's cutouts, the four pads the block bears on.
Below that: a reservoir shelf on slotted supports in the wet bay, a hard
divider to the dry bay, and a full-height rear panel the mast bolts to.

The front is one panel, labelled so the door split can be decided in Fusion —
the doc says the reservoir "slides out through a front door" but not where
the door stops and the dry-bay panel begins.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, cyl_y, cyl_z, labelled


# Plan of the carcass box, in world coordinates.
X0, X1 = -P.PLINTH_W / 2, P.PLINTH_W / 2
Y0, Y1 = 0.0, P.PLINTH_D
Z0, Z1 = P.SHADOW_GAP_H, P.TRAY_RIM_Z  # 2 → 26

# Inside faces.
IX0, IX1 = X0 + P.CARCASS_T, X1 - P.CARCASS_T
IY0, IY1 = Y0 + P.CARCASS_T, Y1 - P.REAR_PANEL_T
FLOOR_TOP = Z0 + P.CARCASS_T

# The divider's X: the wet bay is on the viewer's left.
DIVIDER_X = IX0 + P.WET_BAY_W + P.DIVIDER_T / 2

# The rail the tray floor rests on.
RAIL_TOP = P.TRAY_FLOOR_Z - P.TRAY_T
RAIL_BOTTOM = RAIL_TOP - P.CARCASS_T


def _panel(x0, x1, y0, y1, z0, z1) -> Part:
    return box(
        x1 - x0, y1 - y0, z1 - z0,
        at=((x0 + x1) / 2, (y0 + y1) / 2, z0),
    )


def build_base() -> Part:
    """The recessed block under the carcass — the shadow gap."""
    i = P.SHADOW_GAP_INSET
    return labelled(
        _panel(X0 + i, X1 - i, Y0 + i, Y1 - i, 0.0, P.SHADOW_GAP_H), "plinth_base_recess"
    )


def build_shell() -> Part:
    """Sides, rear panel and floor — the parts that are one welded/glued unit."""
    left = _panel(X0, IX0, Y0, Y1, Z0, Z1)
    right = _panel(IX1, X1, Y0, Y1, Z0, Z1)
    rear = _panel(IX0, IX1, IY1, Y1, Z0, Z1)
    floor = _panel(IX0, IX1, IY0, IY1, Z0, FLOOR_TOP)
    shell = left + right + rear + floor

    # Mast through-bolt holes in the rear panel, matching the shaft.
    from .mast import bolt_heights

    for z in bolt_heights():
        shell -= cyl_y(P.MAST_BOLT_DIA, P.REAR_PANEL_T * 3, at=(P.MAST_X, (IY1 + Y1) / 2, z))

    # Wet-bay vent: "an open reservoir in a sealed box makes a humid box."
    # A row of holes high in the left side. CHOICE.
    vent_z = P.PLINTH_H - 3.0
    for i in range(4):
        y = IY0 + 2.0 + i * 2.5
        # Cylinder along X through the left side.
        hole = box(P.CARCASS_T * 3, 1.0, 1.0, at=((X0 + IX0) / 2, y, vent_z - 0.5))
        shell -= hole

    return labelled(shell, "carcass_shell")


def build_front() -> Part:
    """One front panel from the base to the rail. Door split: decide in Fusion."""
    return labelled(_panel(IX0, IX1, Y0, IY0, Z0, RAIL_BOTTOM), "front_panel_door_split_tbd")


def build_top_rail() -> Part:
    """The frame at 24 that the tray floor sits on and the pads rise from.

    A perimeter plus two cross rails under the block's corner pads — "the
    cabinet rail carries the load." The back member is notched for the mast.
    """
    t = P.CARCASS_T
    front = _panel(IX0, IX1, IY0, IY0 + t, RAIL_BOTTOM, RAIL_TOP)
    back = _panel(IX0, IX1, IY1 - t, IY1, RAIL_BOTTOM, RAIL_TOP)
    left = _panel(IX0, IX0 + t, IY0, IY1, RAIL_BOTTOM, RAIL_TOP)
    right = _panel(IX1 - t, IX1, IY0, IY1, RAIL_BOTTOM, RAIL_TOP)
    rail = front + back + left + right

    # Cross rails under the pads, front to back.
    for px in (P.CMU_X - P.PAD_X, P.CMU_X + P.PAD_X):
        rail += _panel(px - t / 2, px + t / 2, IY0, IY1, RAIL_BOTTOM, RAIL_TOP)

    # Notch the back member for the mast.
    c = P.MAST_NOTCH_CLEARANCE
    rail -= box(
        P.MAST_W + 2 * c, P.MAST_D + 2 * c, t * 3,
        at=(P.MAST_X, P.MAST_Y, RAIL_BOTTOM - t),
    )
    return labelled(rail, "top_rail")


def build_divider() -> Part:
    """Wet bay / dry bay, hard-divided, floor to rail."""
    return labelled(
        _panel(
            DIVIDER_X - P.DIVIDER_T / 2, DIVIDER_X + P.DIVIDER_T / 2,
            IY0, IY1, FLOOR_TOP, RAIL_BOTTOM,
        ),
        "bay_divider",
    )


def build_shelf() -> Part:
    """The reservoir shelf at the design height, on slotted cleats.

    "Build the reservoir shelf adjustable — slotted supports." The cleats
    carry a column of holes at SHELF_SLOT_PITCH so the shelf can move by an
    inch at a time after the flow test decides the real lift.
    """
    shelf_x0, shelf_x1 = IX0, DIVIDER_X - P.DIVIDER_T / 2
    plate = _panel(shelf_x0, shelf_x1, IY0, IY1, P.SHELF_H - P.SHELF_T, P.SHELF_H)

    # Cleats on the left side and on the divider, full depth.
    cleat_h = 1.5
    left_cleat = _panel(shelf_x0, shelf_x0 + P.CARCASS_T, IY0, IY1,
                        P.SHELF_H - P.SHELF_T - cleat_h, P.SHELF_H - P.SHELF_T)
    right_cleat = _panel(shelf_x1 - P.CARCASS_T, shelf_x1, IY0, IY1,
                         P.SHELF_H - P.SHELF_T - cleat_h, P.SHELF_H - P.SHELF_T)
    shelf = plate + left_cleat + right_cleat

    # The mast passes through the wet bay at the back; notch the shelf for it.
    c = P.MAST_NOTCH_CLEARANCE
    shelf -= box(
        P.MAST_W + 2 * c, P.MAST_D + 2 * c, P.SHELF_T * 4,
        at=(P.MAST_X, P.MAST_Y, P.SHELF_H - P.SHELF_T * 2),
    )

    # Slot holes in the carcass side and the divider are the adjustment;
    # marked here on the cleats as a column of reference holes.
    n = P.SHELF_SLOT_COUNT
    z_lo = P.SHELF_H - P.SHELF_T - cleat_h / 2 - P.SHELF_SLOT_PITCH * (n - 1) / 2
    for i in range(n):
        z = z_lo + i * P.SHELF_SLOT_PITCH
        for x in (shelf_x0 + P.CARCASS_T / 2, shelf_x1 - P.CARCASS_T / 2):
            shelf -= box(P.CARCASS_T * 3, 0.25, 0.25, at=(x, (IY0 + IY1) / 2, z - 0.125))

    return labelled(shelf, "reservoir_shelf_adjustable")


def build_reservoir() -> Part:
    """The steam-table pan, as a reference envelope on the shelf.

    Placed from the FRONT with ``RESERVOIR_FRONT_CLEARANCE`` behind the front
    panel, so whatever depth is left at the back — where the mast is — is
    explicit. See ``params.depth_budget()``.
    """
    x = IX0 + P.WET_BAY_W / 2
    y = IY0 + P.RESERVOIR_FRONT_CLEARANCE + P.RESERVOIR_W / 2
    return labelled(
        box(P.RESERVOIR_L, P.RESERVOIR_W, P.RESERVOIR_H, at=(x, y, P.SHELF_H)),
        "reservoir_reference",
    )


def build() -> Part:
    """The whole plinth as one part, for the assembly."""
    return labelled(
        build_base() + build_shell() + build_front() + build_top_rail()
        + build_divider() + build_shelf(),
        "plinth",
    )
