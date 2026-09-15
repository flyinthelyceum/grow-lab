"""The canopy sensor case: a printed block on the CMU's centre-rear.

Carries the AS7341, the BME280 and the ADS1115, facing up through a PTFE
diffuser at its centre. The two plants grow from cores at either end of the
block, so the centre is the one place on it that stays open early in the
season. It will not stay unshaded: ranunculus close over the web by week eight
or so, and from then on the AS7341 reads under-canopy light. That is a real
quantity — see the changelog — but it is not the fixture's output, and the
docs say so rather than claiming a property the geometry does not have.

It is held by three dabs of neutral-cure silicone cast in place in the plate's
recesses, which bond to concrete and to PETG and hold over a newton each
against a case that weighs a quarter of one. Nothing is drilled and the
silicone cuts free with a blade, so the position stays a decision rather than a
commitment — until someone mortises it in, which is where this is going.

**There is no lip**, and the earlier revisions' insistence on one is worth
recording because it was a vestige for two revisions before anyone said so. It
began as the whole fixing: a fin off the plate's rear edge, down the block's
rear face, holding the case by weight and friction. The silicone feet replaced
that, and from then on the fin held nothing — but it still set the datum,
pushing the case 2 mm proud of the block's rear face so it had room to hang. A
feature with no job was deciding where the whole part went, and it was in the
way of the mortise: a pocket in the top face is one cut, a pocket plus a slot
down the outside of the rear face shell is two.

The strain relief that used to run through it is now a zip tie cinched on the
jacket **outside** the wall. Its head stands about 4 mm proud of a 5.5 mm
cable; the notch is 5.3 wide. A pull stops at the wall.

Two parts
---------
**Body**, printed *top face down*. The face you see is then the bed face, which
on a textured sheet is a uniform matte no other method matches — and matte white
is the whole point of the object. Everything inside it hangs from the top wall:
the baffle, the AS7341's four bosses, and the four corner bosses, which run the
full height from the ceiling to the plate and are fused into their corners by a
web. In the print every one of them is a column growing from the bed, and the
part has no internal bridge longer than a vent slot.

**Base plate**, printed top face down as well, so its countersinks and foot
recesses open upward and nothing on it bridges. The walls stand on it and it is
the full footprint, chamfered to match — a plain butt joint with no fit to get
wrong, and no slot at the back for the block's own damp air. The seam is a
hairline 2.5 mm above the block. With the lip gone the plate is a flat
rectangle with four holes and three recesses in it, which is the whole of what
it ever needed to be. The ADS1115 and the BME280 are taped to its inner face.

The AS7341 that is actually in hand
-----------------------------------
Rev G. The first cut was drawn to a vendor datasheet for a 40 × 20 T-shaped
board; Rev E to a photo of what was thought to be a 21 × 16 generic. The board
in hand, photographed properly on 2026-09-14, is the **Adafruit STEMMA QT**
breakout: 1.0 × 0.7 in, four Ø2.5 holes on a 0.8 × 0.5 in grid, the header along
a long edge, the sensor dead centre, and — the part that changes the case — two
JST SH sockets standing 2.9 mm tall *on the sensor face*, one at each end.

So it hangs on its own four holes, from four Ø5.5 bosses under the ceiling,
with M2.5 × 4 thread-forming screws up through the board. Four points fix
position, rotation and rock, and the collar has no mechanical job any more.
The bosses set the drop at 3.2, which is the sockets plus 0.3; nothing else on
that face comes within a millimetre of the ceiling. The header edge faces the
rear wall, so the four wires go straight to the cable notch.

At 25.4 mm the board takes the whole middle of the upper level, and the corner
bosses take both ends of it, so the BME280 can no longer hang beside it. It is
taped to the plate at the −X end instead, sensor up, with the ADS1115 shifted
6.5 mm toward +X to make the room. Its lid faces the open cavity and the −X
inlet slot is beside it. Two more millimetres of length put the ADS1115's
corner a clear half millimetre off the +X corner bosses.

The baffle
----------
The breakout carries an illumination LED 7 mm from the sensor, pointing the
same way. A short collar round the sensor is its shield and the field stop. It
hangs from the ceiling and stops 1.5 mm above the board, over the two SOT-23s
that sit inside its radius; it no longer touches the board, and it does not
need to — the case is dark inside, and the bore is what defines the field.

The bore runs straight through the top wall at the collar's own diameter. Rev D
opened the wall to Ø10.5 — wider than the collar — which took the ceiling out
from under it: the collar would have printed in mid-air. Now the collar sits
on a full ring of wall, and the disc's ledge is 3 mm wide, which is bond area.

White PETG at 1 mm is a diffuser rather than a shield, so the collar attenuates
the LED rather than killing it: **keep the LED off in firmware regardless**, and
paint the interior matte black before assembly if the dark-period reading has
to be zero.

Sealing, deliberately not
-------------------------
This case is **vented, not sealed** — the BME280 has to sample the air, and a
sealed box in a humid, lit, thermally cycling place is a condensation trap. Air
enters through slots low in the rear wall and leaves through slots high in it;
the lid warms under the fixture and drives the exchange. Nothing opens in the
plate: Rev D's plate slots faced the block, whose top stays damp for weeks after
a leach, and would have fed the box the block's own boundary layer. Protect the
boards with conformal coating instead of a gasket — with the BME280's lid and
the AS7341's window masked, or the coat blinds both — and bond the diffuser in
with neutral-cure silicone onto *etched* PTFE, because silicone does not bond to
the plain kind at all.
"""

from __future__ import annotations

from . import params as P

# The kernel is imported inside the build functions, not at module scope. Every
# function above them is arithmetic over the parameters — where the boards land,
# what clears what — and that is exactly the part worth testing on a machine with
# no OCP installed. Deferring the import is what lets the collision tests run
# everywhere instead of only in CI. Annotations are strings (`from __future__`),
# so naming Part here costs nothing.

_MM = P.MM


# --------------------------------------------------------------------------
# Levels, in world Z
# --------------------------------------------------------------------------

def plate_top() -> float:
    """Top face of the base plate — the floor the walls stand on."""
    return P.SC_Z0 + P.SC_BASE_T


def top_face() -> float:
    """The face you see. The bed face, when it prints."""
    return P.SC_Z0 + P.SC_HGT


def ceiling() -> float:
    """Inner face of the top wall — everything in the body hangs from here."""
    return top_face() - P.SC_WALL


def board_top() -> float:
    """Top surface of the hanging AS7341, set by its four bosses."""
    return ceiling() - P.SC_BAFFLE_DROP


def collar_bottom() -> float:
    """Where the baffle stops: clear of the parts round the sensor."""
    return board_top() + P.SC_BAFFLE_CLEAR


def recess_floor() -> float:
    """The ledge the diffuser sits on. The thinnest part of the top wall."""
    return top_face() - P.SC_PORT_DEPTH


def pilot_top() -> float:
    """Blind end of the AS7341's screw pilot."""
    return board_top() + P.SC_AS7341_PILOT_DEPTH


def ads1115_stack_top() -> float:
    """Highest point of the taped board: tape, board, tallest part, no header."""
    return plate_top() + P.SC_TAPE_T + P.SC_BOARD_T + P.SC_ADS1115_PART_H


def bme280_stack_top() -> float:
    """The other taped board: tape, board, the lid."""
    return plate_top() + P.SC_TAPE_T + P.SC_BOARD_T + P.SC_BME280_PART_H


# --------------------------------------------------------------------------
# Plan positions. Tests assert these do not collide rather than trusting the
# arithmetic here — the layout is tight and hand-checking it is how it breaks.
# --------------------------------------------------------------------------

def inner_half() -> tuple[float, float]:
    """Half-extents of the cavity, in X and Y."""
    return P.SC_LEN / 2 - P.SC_WALL, P.SC_WID / 2 - P.SC_WALL


def port_centre() -> tuple[float, float]:
    """The diffuser, and therefore the AS7341's sensor. Case plan centre."""
    return P.SC_X, P.SC_Y


def as7341_span() -> tuple[float, float]:
    """X extent of the AS7341, placed so its sensor lands under the port.

    The sensor is at the board's centre, so this is symmetric about the port;
    it is written from SENSOR_X so a calipered offset moves the board, not the
    port.
    """
    x0 = P.SC_X - P.SC_AS7341_SENSOR_X
    return x0, x0 + P.SC_AS7341_L


def as7341_y_span() -> tuple[float, float]:
    """Y extent. The LED edge is -Y; the header edge is +Y, toward the rear
    wall and the cable notch."""
    y0 = P.SC_Y - P.SC_AS7341_SENSOR_Y
    return y0, y0 + P.SC_AS7341_W


def as7341_centre() -> tuple[float, float]:
    x0, x1 = as7341_span()
    y0, y1 = as7341_y_span()
    return (x0 + x1) / 2, (y0 + y1) / 2


def as7341_hole_points() -> list[tuple[float, float]]:
    """The board's four mounting holes, in world XY: a grid about its centre."""
    cx, cy = as7341_centre()
    return [(cx + sx * P.SC_AS7341_HOLE_PITCH_X / 2, cy + sy * P.SC_AS7341_HOLE_PITCH_Y / 2)
            for sx in (-1, 1) for sy in (-1, 1)]


def as7341_led() -> tuple[float, float]:
    """Where the illumination LED lands. Advisory: the baffle test uses it."""
    y0, _ = as7341_y_span()
    return P.SC_X, y0 + P.SC_AS7341_LED_Y


def as7341_qt_boxes() -> list[tuple[float, float, float, float]]:
    """The two STEMMA QT sockets on the sensor face, (cx, cy, lx, ly). One at
    each end, reaching QT_L inboard, on the board's mid-line."""
    x0, x1 = as7341_span()
    _, cy = as7341_centre()
    return [(x0 + P.SC_AS7341_QT_L / 2, cy, P.SC_AS7341_QT_L, P.SC_AS7341_QT_W),
            (x1 - P.SC_AS7341_QT_L / 2, cy, P.SC_AS7341_QT_L, P.SC_AS7341_QT_W)]


def boss_points() -> list[tuple[float, float]]:
    """The four corner bosses. Ø7, hanging the full height from the ceiling."""
    dx = P.SC_LEN / 2 - P.SC_BOSS_INSET_X
    dy = P.SC_WID / 2 - P.SC_BOSS_INSET_Y
    return [(P.SC_X + sx * dx, P.SC_Y + sy * dy)
            for sx in (-1, 1) for sy in (-1, 1)]


def web_boxes() -> list[tuple[float, float, float, float]]:
    """A block from each boss to its outer corner, (cx, cy, lx, ly). It fuses
    the boss into both walls so the column is part of the shell, not a
    cylinder touching it along a line. The chamfer cuts its corner off
    afterwards, like everything else's."""
    out = []
    for bx, by in boss_points():
        sx = 1 if bx > P.SC_X else -1
        sy = 1 if by > P.SC_Y else -1
        out.append((bx + sx * P.SC_BOSS_INSET_X / 2, by + sy * P.SC_BOSS_INSET_Y / 2,
                    P.SC_BOSS_INSET_X, P.SC_BOSS_INSET_Y))
    return out


def ads1115_centre() -> tuple[float, float]:
    """On the plate, taped, shifted toward +X to leave the -X end to the
    BME280. Advisory: the tests prove a board of this size lands clear of the
    screws, and the build sheet says where to stick it."""
    return P.SC_X + P.SC_ADS1115_DX, P.SC_Y


def ads1115_span() -> tuple[float, float, float, float]:
    """(x0, x1, y0, y1) of the board."""
    cx, cy = ads1115_centre()
    return (cx - P.SC_ADS1115_L / 2, cx + P.SC_ADS1115_L / 2,
            cy - P.SC_ADS1115_W / 2, cy + P.SC_ADS1115_W / 2)


def bme280_centre() -> tuple[float, float]:
    """On the plate at the -X end, taped, sensor up, long side along Y, a gap
    from the ADS1115.

    Rev E hung it inverted beside the AS7341 so its lid faced the open cavity
    rather than a 2 mm slot under the ceiling. On the plate it faces the open
    cavity the right way up, with the -X inlet slot beside it; and there is no
    upper-level spot for it any more — see the module docstring.
    """
    ax0, _, _, _ = ads1115_span()
    return ax0 - P.SC_BME280_GAP - P.SC_BME280_W / 2, P.SC_Y


def bme280_span() -> tuple[float, float, float, float]:
    """(x0, x1, y0, y1) of the board."""
    cx, cy = bme280_centre()
    return (cx - P.SC_BME280_W / 2, cx + P.SC_BME280_W / 2,
            cy - P.SC_BME280_L / 2, cy + P.SC_BME280_L / 2)


def inlet_xs() -> list[float]:
    """Inlet slots, low in the rear wall, either side of the cable notch."""
    return [P.SC_X - 10.0 * _MM, P.SC_X + 10.0 * _MM]


def outlet_xs() -> list[float]:
    """Outlet slots, high in the rear wall."""
    return [P.SC_X + d * _MM for d in (-18.0, -9.0, 0.0, 9.0, 18.0)]


def inlet_z() -> float:
    return plate_top() + P.SC_INLET_Z


def outlet_z() -> float:
    return ceiling() - P.SC_OUTLET_DROP


def rear_wall_y() -> float:
    """Mid-plane of the rear wall. Its outer face is the block's rear face."""
    return P.SC_Y1 - P.SC_WALL / 2


def foot_points() -> list[tuple[float, float]]:
    """Three cast feet. Three points never rock."""
    return [(P.SC_X - 21.0 * _MM, P.SC_Y), (P.SC_X + 21.0 * _MM, P.SC_Y),
            (P.SC_X, P.SC_Y - 8.0 * _MM)]


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def _chamfer_verticals(part: "Part", z0: float, z1: float) -> "Part":
    """Take SC_CHAMFER off the four vertical corners, as plinth.py does.

    Cut with a rotated box rather than a kernel fillet: this package has no
    edge-selection anywhere, and a chamfer a cutter makes is a chamfer you can
    reason about. Runs last, so it also trims the corner webs.
    """
    from build123d import Rot

    from ._shapes import box, location_in

    s = P.SC_CHAMFER * 2 ** 0.5
    hx, hy = P.SC_LEN / 2, P.SC_WID / 2
    over = 1.0 * _MM
    for sx in (-1, 1):
        for sy in (-1, 1):
            cutter = Rot(0, 0, 45) * box(s, s, (z1 - z0) + 2 * over, at=(0, 0, 0))
            part -= location_in(P.SC_X + sx * hx, P.SC_Y + sy * hy, z0 - over) * cutter
    return part


def build_body() -> "Part":
    """The upper half: top face, four walls, the optics, the bosses."""
    from ._shapes import CENTRE, box, cyl_z, labelled

    z0, z1 = plate_top(), top_face()
    h = z1 - z0
    ix, iy = inner_half()
    px, py = port_centre()
    over = 0.5 * _MM

    body = box(P.SC_LEN, P.SC_WID, h, at=(P.SC_X, P.SC_Y, z0))

    # Hollow from below. The top wall stays; the bottom is open to the plate.
    body -= box(2 * ix, 2 * iy, h - P.SC_WALL + over, at=(P.SC_X, P.SC_Y, z0 - over))

    # Corner bosses, ceiling to plate, each fused to its corner by a web.
    for (bx, by), (wx, wy, wl, ww) in zip(boss_points(), web_boxes()):
        body += cyl_z(P.SC_BOSS_DIA, ceiling() - z0, at=(bx, by, z0))
        body += box(wl, ww, ceiling() - z0, at=(wx, wy, z0))

    # Chamfer the four vertical corners, webs included.
    body = _chamfer_verticals(body, z0, z1)

    # Closure pilots, from the boss's bottom face: the plate screws form their
    # own thread up the column, as the board screws do in theirs.
    for bx, by in boss_points():
        body -= cyl_z(P.SC_CLOSURE_PILOT, P.SC_CLOSURE_PILOT_DEPTH + over, at=(bx, by, z0 - over))

    # Diffuser recess from the top face. The aperture through the rest of the
    # wall is the bore's own diameter — see the module docstring for why it is
    # not wider than the collar.
    body -= cyl_z(P.SC_PORT_DIA, P.SC_PORT_DEPTH + over, at=(px, py, recess_floor()))

    # The baffle: field stop and LED shield, hanging from the ceiling and
    # stopping clear of the board. Then the AS7341's four bosses over its own
    # holes, ceiling to board; their pilots, 0.3 into the top wall; then the
    # bore, last, straight through collar and wall so no union can close it.
    body += cyl_z(P.SC_BAFFLE_OD, ceiling() - collar_bottom(), at=(px, py, collar_bottom()))
    for hx, hy in as7341_hole_points():
        body += cyl_z(P.SC_AS7341_BOSS_DIA, P.SC_BAFFLE_DROP, at=(hx, hy, board_top()))
        body -= cyl_z(P.SC_AS7341_PILOT, P.SC_AS7341_PILOT_DEPTH + over,
                      at=(hx, hy, board_top() - over))
    body -= cyl_z(P.SC_BAFFLE_ID, ceiling() - collar_bottom() + P.SC_WALL + 2 * over,
                  at=(px, py, collar_bottom() - over))

    # Cable entry: a notch in the rear wall's bottom edge, closed by the plate
    # the wall stands on. A shade under the cable for a friction fit, and the
    # strain relief is a zip tie cinched on the jacket just outside it — the
    # tie's head cannot be drawn back through a 5.3 mm notch, so a pull stops
    # at the wall instead of reaching the solder joints.
    body -= box(P.SC_CABLE_W, P.SC_WALL * 3, P.SC_CABLE_H + over,
                at=(P.SC_X, rear_wall_y(), z0 - over))

    # Probe entry: the same, in the +X end wall, over that end's core.
    body -= box(P.SC_WALL * 3, P.SC_PROBE_W, P.SC_PROBE_H + over,
                at=(P.SC_X + P.SC_LEN / 2, P.SC_Y, z0 - over))

    # Ventilation, all in the rear wall where nothing looks: inlets low, outlets
    # high. Each slot's top edge is a bridge the length of the slot.
    for vx in inlet_xs():
        body -= box(P.SC_VENT_L, P.SC_WALL * 3, P.SC_VENT_W,
                    at=(vx, rear_wall_y(), inlet_z()), align=CENTRE)
    for vx in outlet_xs():
        body -= box(P.SC_VENT_L, P.SC_WALL * 3, P.SC_VENT_W,
                    at=(vx, rear_wall_y(), outlet_z()), align=CENTRE)

    return labelled(body, "sensor_case_body")


def build_base() -> "Part":
    """The lower half: the plate the walls stand on, the ADS1115, the feet."""
    from ._shapes import box, cone_z, cyl_z, labelled

    z0 = P.SC_Z0
    over = 0.5 * _MM

    plate = box(P.SC_LEN, P.SC_WID, P.SC_BASE_T, at=(P.SC_X, P.SC_Y, z0))
    plate = _chamfer_verticals(plate, z0, z0 + P.SC_BASE_T)

    # No printed fence round the ADS1115, deliberately. A fence has to be sized
    # to an outline, and this one comes off a vendor listing rather than a
    # caliper. A fence that is 1 mm wrong is a board that will not go in; foam
    # tape is 1 mm wrong and does not care. Nothing here is subject to
    # vibration.

    # Screw clearance and a true 90-degree countersink, so the head sits below
    # the face that meets the block and bears on a cone, not on a hole's rim.
    for bx, by in boss_points():
        plate -= cyl_z(P.SC_SCREW_DIA, P.SC_BASE_T + 2 * over, at=(bx, by, z0 - over))
        plate -= cone_z(P.SC_SCREW_CSK + 2 * over, P.SC_SCREW_DIA,
                        P.SC_SCREW_CSK_DEPTH + over, at=(bx, by, z0 - over))

    # Recesses for the three cast feet.
    for fx, fy in foot_points():
        plate -= cyl_z(P.SC_FOOT_DIA, P.SC_FOOT_DEPTH + over, at=(fx, fy, z0 - over))

    return labelled(plate, "sensor_case_base")


def boards() -> dict[str, "Part"]:
    """The three boards and the disc, as blocks, where the layout puts them.

    Mock-ups, not models: an outline, a thickness, and for the AS7341 the
    sensor package and the two sockets, because those are the parts whose
    heights decide the drop. They exist for two reasons. The viewer is the obvious one —
    an empty box tells you nothing about a case whose whole job is what is
    inside it. The other is that a kernel intersection against these is a
    stronger statement than the plan arithmetic that proves the same thing in
    two dimensions: it is the difference between "these rectangles do not
    overlap" and "no part of this board is inside that plastic".
    """
    from ._shapes import box, cyl_z, labelled

    out: dict[str, "Part"] = {}
    bt = board_top()

    x0, x1 = as7341_span()
    y0, y1 = as7341_y_span()
    as7341 = box(P.SC_AS7341_L, P.SC_AS7341_W, P.SC_BOARD_T,
                 at=((x0 + x1) / 2, (y0 + y1) / 2, bt - P.SC_BOARD_T))
    px, py = port_centre()
    as7341 += box(3.1 * _MM, 2.0 * _MM, P.SC_AS7341_PKG_H, at=(px, py, bt))
    # The two sockets: the tallest thing on the face, and the reason for the
    # drop. If they are in the plastic, the kernel test says so.
    for cx, cy, lx, ly in as7341_qt_boxes():
        as7341 += box(lx, ly, P.SC_AS7341_QT_H, at=(cx, cy, bt))
    out["as7341"] = labelled(as7341, "as7341")

    bx0, bx1, by0, by1 = bme280_span()
    bme = box(bx1 - bx0, by1 - by0, P.SC_BOARD_T,
              at=((bx0 + bx1) / 2, (by0 + by1) / 2, plate_top() + P.SC_TAPE_T))
    bme += box(2.5 * _MM, 2.5 * _MM, P.SC_BME280_PART_H,
               at=((bx0 + bx1) / 2, (by0 + by1) / 2, plate_top() + P.SC_TAPE_T + P.SC_BOARD_T))
    out["bme280"] = labelled(bme, "bme280")

    ax, ay = ads1115_centre()
    out["ads1115"] = labelled(
        box(P.SC_ADS1115_L, P.SC_ADS1115_W, P.SC_BOARD_T,
            at=(ax, ay, plate_top() + P.SC_TAPE_T)),
        "ads1115")

    out["diffuser"] = labelled(
        cyl_z(P.SC_DISC_DIA, P.SC_DISC_T, at=(px, py, recess_floor())),
        "diffuser")
    return out


def build() -> "Part":
    """Both halves, assembled, where they sit on the block."""
    from ._shapes import labelled

    return labelled(build_body() + build_base(), "sensor_case")


# --------------------------------------------------------------------------
# Print orientation
# --------------------------------------------------------------------------

def for_print() -> dict[str, "Part"]:
    """Each half moved to the origin and turned the way it prints.

    Both go top-face-down. For the body that face is the only one on show,
    and a bed face on a textured sheet is the matte this object wants. For the
    plate it means the countersinks and the foot recesses open upward, so the
    part has no bridge at all; its bed face is the inside, where the ADS1115
    is taped.
    """
    from build123d import Rot

    from ._shapes import bbox_in, labelled, location_in

    out: dict[str, "Part"] = {}
    for name, part in (("sensor_case_body", build_body()),
                       ("sensor_case_base", build_base())):
        part = Rot(180, 0, 0) * part
        bb = bbox_in(part)
        placed = location_in(-(bb["x0"] + bb["x1"]) / 2,
                             -(bb["y0"] + bb["y1"]) / 2,
                             -bb["z0"]) * part
        out[name] = labelled(placed, name)
    return out
