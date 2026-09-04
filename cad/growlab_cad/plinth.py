"""The plinth: a cabinet carcass on a recessed base or a steel frame, with the
instrument face in its front.

V1_PHYSICAL_BUILD.md § Station geometry (console layout, 2026-09-04).

Front to back: the front panel with the acrylic face pocketed into it; the
console bay, 3 in clear, full width, where the meters, Inky and Pi live; a
partition; then the wet bay (reservoir on its adjustable shelf, viewer's left)
and the dry bay (mast, PSU, driver) side by side, hard-divided. The rear panel
is full height and the mast bolts through it; behind the wet bay it becomes a
door so the pan slides out at working height.

The carcass sides rise to the tray rim so the tray nests inside and finishes
flush; a rail under the tray floor carries it and, through the tray's cutouts,
the four pads the block bears on.

The console bay is open to the front behind a clear fascia band; the
instrument case (``case.py``) sits in it on a ledge, with a dark backplate on
the partition behind. The ply front panel below the band is removable for the
PSU and driver. The partition stops at the divider, so the dry bay behind it
is reached the same way.
"""

from __future__ import annotations

from build123d import Part, Rot

from pi.dashboard.panel_geometry import CORNER_SCREW_INSET, FACE_HEIGHT, FACE_WIDTH

from . import params as P
from ._shapes import box, cyl_x, cyl_y, labelled, location_in

# Plan of the carcass box, in world coordinates.
X0, X1 = -P.PLINTH_W / 2, P.PLINTH_W / 2
Y0, Y1 = 0.0, P.PLINTH_D
Z0, Z1 = P.SHADOW_GAP_H, P.TRAY_RIM_Z

# Inside faces.
IX0, IX1 = P.INSIDE_X0, P.INSIDE_X1
IY0, IY1 = Y0 + P.CARCASS_T, P.REAR_INSIDE_Y
FLOOR_TOP = P.FLOOR_TOP_Z

DIVIDER_X = P.DIVIDER_X
RAIL_TOP, RAIL_BOTTOM = P.RAIL_TOP_Z, P.RAIL_BOTTOM_Z

# The rear door: the wet bay's full width and the full height of the bay.
DOOR_X0, DOOR_X1 = IX0, DIVIDER_X - P.DIVIDER_T / 2
DOOR_Z0, DOOR_Z1 = FLOOR_TOP, RAIL_BOTTOM

# Where the drip line and the LED cable leave the wet bay for the mast: over
# the pan's rim, through the divider, into the shaft's side. CHOICE.
LINE_PASS_Z = P.SHELF_H + P.RESERVOIR_H + 0.4
LINE_PASS_Y = P.RESERVOIR_Y1 - 1.0


def _panel(x0, x1, y0, y1, z0, z1) -> Part:
    return box(
        x1 - x0, y1 - y0, z1 - z0,
        at=((x0 + x1) / 2, (y0 + y1) / 2, z0),
    )


def build_base() -> Part:
    """What the carcass stands on: the recessed plinth, or the steel frame."""
    if P.FRAME:
        return build_frame()
    i = P.SHADOW_GAP_INSET
    return labelled(
        _panel(X0 + i, X1 - i, Y0 + i, Y1 - i, 0.0, P.SHADOW_GAP_H), "base_recess"
    )


def build_frame() -> Part:
    """The frame candidate: four 1 x 1 legs inset under the cabinet and a ring
    at the top the floor sits on. The mast runs to the floor beside the rear
    rail, which is notched for it, and is welded to it — one armature."""
    t, i = P.FRAME_TUBE, P.FRAME_LEG_INSET
    lx0, lx1 = X0 + i, X1 - i
    ly0, ly1 = Y0 + i, Y1 - i
    top = P.SHADOW_GAP_H
    legs = None
    for (x0, y0) in ((lx0, ly0), (lx1 - t, ly0), (lx0, ly1 - t), (lx1 - t, ly1 - t)):
        leg = _panel(x0, x0 + t, y0, y0 + t, 0.0, top - t)
        legs = leg if legs is None else legs + leg
    ring = (
        _panel(lx0, lx1, ly0, ly0 + t, top - t, top)
        + _panel(lx0, lx1, ly1 - t, ly1, top - t, top)
        + _panel(lx0, lx0 + t, ly0, ly1, top - t, top)
        + _panel(lx1 - t, lx1, ly0, ly1, top - t, top)
    )
    frame = legs + ring
    c = P.MAST_NOTCH_CLEARANCE
    frame -= box(P.MAST_W + 2 * c, P.MAST_D + 2 * c, top + 1.0, at=(P.MAST_X, P.MAST_Y, -0.5))
    return labelled(frame, "base_frame_1x1_hss")


def _chamfer_corners(part: Part, z0: float, z1: float) -> Part:
    """Take CHAMFER off the four vertical outer corners, full height."""
    if not P.CHAMFER:
        return part
    s = P.CHAMFER * 2 ** 0.5
    for (x, y) in ((X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1)):
        cutter = Rot(0, 0, 45) * box(s, s, (z1 - z0) + 2.0, at=(0, 0, 0))
        part -= location_in(x, y, z0 - 1.0) * cutter
    return part


def _fascia_band() -> tuple[float, float]:
    return P.FACE_Z0 - P.FASCIA_MARGIN, P.FACE_Z1 + P.FASCIA_MARGIN


def fascia_screw_points() -> list[tuple[float, float]]:
    """(world X, world Z) of the fascia's fixings — two rows, no side screws.

    The acrylic is not drilled anywhere it would have to reach the carcass
    sides: the band is wider than the front panel, so its side edges are only
    captured in the sides' rebate. Everything that carries load lands where
    there is real material behind the glass — the ply header along the top
    (FASCIA_TOP_LIP of front panel left standing behind the band) and the
    console ledge along the bottom. Both rows are inside the front panel's
    width, so both find ply.
    """
    bz0, bz1 = _fascia_band()
    rows = [
        bz1 - P.FASCIA_TOP_LIP / 2,          # into the header
        bz0 + (P.FASCIA_MARGIN + P.LEDGE_T) / 2,   # into the ledge below the plate
    ]
    n = P.FASCIA_SCREW_COLUMNS
    span = (IX1 - IX0) - 2 * P.CARCASS_T
    xs = [IX0 + P.CARCASS_T + span * i / (n - 1) for i in range(n)]
    return [(x, z) for z in rows for x in xs]


def build_shell() -> Part:
    """Sides, rear panel and floor — the parts that are one welded/glued unit.

    The rear panel has the door opening behind the wet bay; what remains of
    it behind the dry bay is the fixed panel the mast bolts through.
    """
    left = _panel(X0, IX0, Y0, Y1, Z0, Z1)
    right = _panel(IX1, X1, Y0, Y1, Z0, Z1)
    rear = _panel(IX0, IX1, IY1, Y1, Z0, Z1)
    floor = _panel(IX0, IX1, IY0, IY1, Z0, FLOOR_TOP)
    shell = left + right + rear + floor
    shell = _chamfer_corners(shell, Z0, Z1)

    if P.FASCIA:
        # The band pocket runs across the sides' front edges too.
        bz0, bz1 = _fascia_band()
        shell -= _panel(X0 - 0.5, X1 + 0.5, Y0 - 0.5, P.FASCIA_POCKET, bz0, bz1)

    if P.MAST_BOTTOM < FLOOR_TOP:
        # The mast passes through the floor to the frame below it.
        c = P.MAST_NOTCH_CLEARANCE
        shell -= box(P.MAST_W + 2 * c, P.MAST_D + 2 * c, P.CARCASS_T * 3, at=(P.MAST_X, P.MAST_Y, Z0 - P.CARCASS_T))

    # The door opening, through the rear panel.
    shell -= _panel(DOOR_X0, DOOR_X1, IY1 - 0.5, Y1 + 0.5, DOOR_Z0, DOOR_Z1)

    # Mast through-bolt holes in the fixed rear panel, matching the shaft.
    from .mast import bolt_heights

    for z in bolt_heights():
        shell -= cyl_y(P.MAST_BOLT_DIA, P.REAR_PANEL_T * 3, at=(P.MAST_X, (IY1 + Y1) / 2, z))

    # Wet-bay vent: "an open reservoir in a sealed box makes a humid box."
    # A row of holes high in the left side, over the pan. CHOICE.
    vent_z = RAIL_BOTTOM - 1.0
    for i in range(4):
        y = P.RESERVOIR_Y0 + 1.5 + i * 2.5
        shell -= cyl_x(1.0, P.CARCASS_T * 3, at=((X0 + IX0) / 2, y, vent_z))

    # Console-bay vent: PSU and driver heat, out through the right side, low
    # and forward — away from the wet bay. CHOICE.
    for i in range(3):
        z = FLOOR_TOP + 2.0 + i * 1.5
        shell -= cyl_x(0.75, P.CARCASS_T * 3, at=((IX1 + X1) / 2, (P.CONSOLE_Y0 + P.CONSOLE_Y1) / 2, z))

    return labelled(shell, "carcass_shell")


def build_front() -> Part:
    """The removable front panel.

    Fascia form: the ply stops at the bottom of the band; above it the console
    bay is open behind the clear fascia. Unscrew this panel and the PSU and
    driver below the case are reached.

    Box form: one panel to the rail, with a pocket the acrylic face sits in
    and a through-opening FACE_LIP smaller all round for F1–4 to land in.
    """
    fx0, fx1 = P.FACE_X0, P.FACE_X0 + FACE_WIDTH
    fz0, fz1 = P.FACE_Z0, P.FACE_Z1

    if P.FASCIA:
        bz0, bz1 = _fascia_band()
        panel = _panel(IX0, IX1, Y0, IY0, Z0, RAIL_BOTTOM)
        # Rebate the whole band FASCIA_POCKET deep — the acrylic sits in it.
        panel -= _panel(IX0 - 0.5, IX1 + 0.5, Y0 - 0.5, P.FASCIA_POCKET, bz0, bz1)
        # Then take the rest of the way through, except the top lip: what is
        # left standing behind the glass there is the header the fascia's top
        # row screws into. Below it the console bay is open to be seen.
        panel -= _panel(IX0 - 0.5, IX1 + 0.5, Y0 - 0.5, IY0 + 0.5, bz0, bz1 - P.FASCIA_TOP_LIP)
        for wx, wz in fascia_screw_points():
            if wz > bz1 - P.FASCIA_TOP_LIP:
                panel -= cyl_y(P.PILOT_DIA, P.CARCASS_T * 3, at=(wx, (Y0 + IY0) / 2, wz))
        return labelled(panel, "front_panel_removable")

    panel = _panel(IX0, IX1, Y0, IY0, Z0, RAIL_BOTTOM)
    panel -= _panel(fx0, fx1, Y0 - 0.5, Y0 + P.ACRYLIC_T, fz0, fz1)  # face pocket
    lip = P.FACE_LIP
    panel -= _panel(fx0 + lip, fx1 - lip, Y0 - 0.5, IY0 + 0.5, fz0 + lip, fz1 - lip)  # opening
    # Tap drill for M3 (2.5 mm) on the F1–4 centres, into the lip.
    for px, py in _corner_screws():
        panel -= cyl_y(2.5 / 25.4, P.CARCASS_T * 3, at=(fx0 + px, (Y0 + IY0) / 2, fz0 + py))
    return labelled(panel, "front_panel_removable")


def build_fascia() -> Part:
    """The clear band: full width between the chamfers, recessed behind the
    front plane, over the open console bay. The only holes in it are for the
    knob shafts; the dials and the e-ink are read through it."""
    from .face import knob_points

    bz0, bz1 = _fascia_band()
    band = _panel(X0 + P.CHAMFER, X1 - P.CHAMFER, P.FASCIA_RECESS, P.FASCIA_POCKET, bz0, bz1)
    mid_y = (P.FASCIA_RECESS + P.FASCIA_POCKET) / 2
    for wx, wz, dia in knob_points():
        band -= cyl_y(dia + 2 * P.KNOB_HOLE_CLEARANCE, P.FASCIA_T * 4, at=(wx, mid_y, wz))
    for wx, wz in fascia_screw_points():
        band -= cyl_y(P.FASCIA_SCREW_DIA, P.FASCIA_T * 4, at=(wx, mid_y, wz))
    return labelled(band, "fascia_clear_acrylic")


def build_ledge() -> Part:
    """The ply ledge the instrument case sits on, flush behind the fascia so
    the fascia's bottom screws land in it. Stops short of the partition: the
    chase behind it is where the loom drops to the PSU."""
    ledge = _panel(IX0, IX1, P.FASCIA_POCKET, P.CONSOLE_Y1 - P.LEDGE_CHASE,
                   P.FACE_Z0 - P.LEDGE_T, P.FACE_Z0)
    for wx, wz in fascia_screw_points():
        if P.FACE_Z0 - P.LEDGE_T < wz < P.FACE_Z0:
            ledge -= cyl_y(P.PILOT_DIA, P.LEDGE_T * 3, at=(wx, P.FASCIA_POCKET + P.LEDGE_T, wz))
    return labelled(ledge, "console_ledge")


def build_backplate() -> Part:
    """A dark sheet on the partition, behind the case, filling the band zone:
    what shows through the glass beside the instrument is black, not ply."""
    bz0, bz1 = _fascia_band()
    return labelled(
        _panel(IX0, IX1, P.PARTITION_Y0 - P.BACKPLATE_T, P.PARTITION_Y0, bz0, bz1),
        "console_backplate",
    )


def _corner_screws() -> list[tuple[float, float]]:
    i = CORNER_SCREW_INSET
    return [(i, i), (FACE_WIDTH - i, i), (i, FACE_HEIGHT - i), (FACE_WIDTH - i, FACE_HEIGHT - i)]


def build_top_rail() -> Part:
    """The frame under the tray floor that the pads rise from.

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


def build_partition() -> Part:
    """Console bay from wet bay, floor to rail. Stops at the divider, so the
    dry bay behind it is open to the console bay and reached from the front."""
    return labelled(
        _panel(IX0, DIVIDER_X - P.DIVIDER_T / 2, P.PARTITION_Y0, P.PARTITION_Y1, FLOOR_TOP, RAIL_BOTTOM),
        "console_partition",
    )


def build_divider() -> Part:
    """Wet bay / dry bay, hard-divided, floor to rail, partition to rear panel.

    One grommeted pass for the drip line and the LED cable, over the pan's
    rim, on the way to the mast's side.
    """
    divider = _panel(
        DIVIDER_X - P.DIVIDER_T / 2, DIVIDER_X + P.DIVIDER_T / 2,
        P.PARTITION_Y0, IY1, FLOOR_TOP, RAIL_BOTTOM,
    )
    divider -= cyl_x(P.MAST_LINE_PASS_DIA, P.DIVIDER_T * 3, at=(DIVIDER_X, LINE_PASS_Y, LINE_PASS_Z))
    return labelled(divider, "bay_divider")


def build_shelf() -> Part:
    """The reservoir shelf at the design height, on slotted cleats.

    "Build the reservoir shelf adjustable — slotted supports." The cleats
    carry a column of holes at SHELF_SLOT_PITCH so the shelf can move by an
    inch at a time after the flow test decides the real lift.
    """
    shelf_x0, shelf_x1 = IX0, DIVIDER_X - P.DIVIDER_T / 2
    y0, y1 = P.PARTITION_Y1, IY1
    plate = _panel(shelf_x0, shelf_x1, y0, y1, P.SHELF_H - P.SHELF_T, P.SHELF_H)

    # Cleats on the left side and on the divider, full depth of the bay.
    cleat_h = 1.5
    left_cleat = _panel(shelf_x0, shelf_x0 + P.CARCASS_T, y0, y1,
                        P.SHELF_H - P.SHELF_T - cleat_h, P.SHELF_H - P.SHELF_T)
    right_cleat = _panel(shelf_x1 - P.CARCASS_T, shelf_x1, y0, y1,
                         P.SHELF_H - P.SHELF_T - cleat_h, P.SHELF_H - P.SHELF_T)
    shelf = plate + left_cleat + right_cleat

    # Slot holes in the carcass side and the divider are the adjustment;
    # marked here on the cleats as a column of reference holes.
    n = P.SHELF_SLOT_COUNT
    z_lo = P.SHELF_H - P.SHELF_T - cleat_h / 2 - P.SHELF_SLOT_PITCH * (n - 1) / 2
    for i in range(n):
        z = z_lo + i * P.SHELF_SLOT_PITCH
        for x in (shelf_x0 + P.CARCASS_T / 2, shelf_x1 - P.CARCASS_T / 2):
            shelf -= box(P.CARCASS_T * 3, 0.25, 0.25, at=(x, (y0 + y1) / 2, z - 0.125))

    return labelled(shelf, "reservoir_shelf_adjustable")


def build_rear_door() -> Part:
    """The door behind the wet bay: the pan slides out through it."""
    g = P.DOOR_GAP
    return labelled(
        _panel(DOOR_X0 + g, DOOR_X1 - g, IY1, Y1, DOOR_Z0 + g, DOOR_Z1 - g),
        "rear_door_wet_bay",
    )


def door_opening() -> tuple[float, float]:
    """(width, height) of the opening the pan has to pass through."""
    return DOOR_X1 - DOOR_X0, DOOR_Z1 - DOOR_Z0


def build_reservoir() -> Part:
    """The steam-table pan, as a reference envelope on the shelf.

    Placed from the FRONT of the wet bay with ``RESERVOIR_FRONT_CLEARANCE``
    behind the partition, so whatever depth is left at the back — where the
    door is — is explicit. See ``params.DEPTH``.
    """
    return labelled(
        box(P.RESERVOIR_L, P.RESERVOIR_W, P.RESERVOIR_H,
            at=(P.RESERVOIR_X, (P.RESERVOIR_Y0 + P.RESERVOIR_Y1) / 2, P.SHELF_H)),
        "reservoir_reference",
    )


def build_console_electronics() -> Part:
    """What lives behind the face — meters, Inky, i3, Pi — as an envelope the
    plans say fits "inside 3.00 clear". If it meets the partition, the console
    bay is too shallow."""
    return labelled(
        _panel(P.FACE_X0, P.FACE_X0 + FACE_WIDTH,
               P.CONSOLE_Y0, P.CONSOLE_Y0 + P.CONSOLE_ELECTRONICS_D,
               P.FACE_Z0, P.FACE_Z1),
        "console_electronics_reference",
    )


def build() -> Part:
    """The carcass as one part, for the assembly. The base, the door and the
    fascia are separate parts: different materials, different fabrication."""
    carcass = (build_shell() + build_front() + build_top_rail()
               + build_partition() + build_divider() + build_shelf())
    if P.FASCIA:
        carcass += build_ledge()
    return labelled(carcass, "plinth")
