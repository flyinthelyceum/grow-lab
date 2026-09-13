"""The canopy sensor case: a printed block on the CMU's centre-rear.

Carries the AS7341, the BME280 and the ADS1115, facing up through a PTFE
diffuser at its centre. The two plants grow from cores at either end of the
block, so the centre is the one place on it that stays open — and the one place
neither canopy shades. That is why it is here rather than beside a core.

It is held by nothing but its own weight and a lip: the rear wall carries on
down past the floor and bears on the block's rear face from **outside** it,
which is all it takes to stop the case sliding forward. (Outside, not flush —
flush puts 0.08 in3 of printed plastic inside the block, which is what the
interference check against the CMU is there to say.) Nothing is drilled, so the
position can be lived with for a season before anyone commits a masonry bit.

Two parts
---------
**Body**, printed *top face down*. The face you see is then the bed face, which
on a textured sheet is a uniform matte no other method matches — and matte white
is the whole point of the object. Everything inside it hangs from the top wall,
so the print has no internal bridge.

**Base plate**, printed flat, carrying the two boards that do not need to see
anything. Populate and wire it on the bench, then bring the two halves together.

Why the boards sit on two levels
--------------------------------
Laid end to end the three boards come to 83 mm and the case would be 100 long.
Split across two levels the length is set by the AS7341 alone — and the AS7341
is the reason for every dimension here. Its sensor sits about 5 mm from one end
of a 40 mm board, and the port is centred on the *sensor*, so 35 mm of board has
to lie on one side of the port. The 32 mm of dead space on the other side is
where the loom lives.

The baffle
----------
The AS7341 breakout carries two illumination LEDs flanking the sensor, for
reflectance work. They are millimetres away and pointing the same way, so with
an open cavity they would light the diffuser from beneath and the sensor would
read its own board. A short collar around the sensor blocks them, stops internal
reflection off white walls, and sets the field stop. It is also the standoff
that fixes sensor-to-diffuser distance, which is the one height in this part
that has to be right — so the optical fix and the mechanical one are the same
feature.

**Keep the illumination LEDs off in firmware regardless.** The baffle is a
second line, not the first.

Sealing, deliberately not
-------------------------
This case is **vented, not sealed**. A sealed box in a humid, lit, thermally
cycling place is a condensation trap — it collects the water it was meant to
exclude and then holds it against the boards. Air enters under the perimeter
(the plate stands on four silicone feet), crosses the chamber through slots in
the plate, and leaves through slots high in the rear wall. Protect the boards
with conformal coating instead of a gasket, and bond the diffuser in with
silicone: that joint is the only one that has to keep water out, and it is
never opened.
"""

from __future__ import annotations

from . import params as P

# The kernel is imported inside the build functions, not at module scope. Every
# function above them is arithmetic over the parameters — where the boards land,
# what clears what — and that is exactly the part worth testing on a machine with
# no OCP installed. Deferring the import is what lets the collision tests run
# everywhere instead of only in CI. Annotations are strings (`from __future__`),
# so naming Part here costs nothing.


# --------------------------------------------------------------------------
# Levels, in world Z
# --------------------------------------------------------------------------

def plate_top() -> float:
    """Top face of the base plate — the floor everything below sits on."""
    return P.SC_Z0 + P.SC_BASE_T


def top_face() -> float:
    """The face you see. The bed face, when it prints."""
    return P.SC_Z0 + P.SC_HGT


def ceiling() -> float:
    """Inner face of the top wall — everything in the body hangs from here."""
    return top_face() - P.SC_WALL


def board_top() -> float:
    """Top surface of the AS7341, set by the baffle's length."""
    return ceiling() - P.SC_BAFFLE_DROP


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

    The tongue points toward -X, so the board runs from a little before the
    port out to +35.
    """
    x0 = P.SC_X - P.SC_AS7341_SENSOR_FROM_END
    return x0, x0 + P.SC_AS7341_L


def boss_points() -> list[tuple[float, float]]:
    dx = P.SC_LEN / 2 - P.SC_SCREW_INSET
    dy = P.SC_WID / 2 - P.SC_SCREW_INSET
    return [(P.SC_X + sx * dx, P.SC_Y + sy * dy)
            for sx in (-1, 1) for sy in (-1, 1)]


def standoff_points() -> list[tuple[float, float]]:
    """Three posts besides the baffle, so the AS7341 seats flat.

    All three land on the board's 20 mm body, clear of the 10 mm tongue.
    """
    _, x1 = as7341_span()
    near = P.SC_X + P.SC_AS7341_TONGUE_W  # just past the tongue
    far = x1 - 3.0 * P.MM
    dy = P.SC_AS7341_W / 2 - 3.0 * P.MM
    return [(near, P.SC_Y - dy), (near, P.SC_Y + dy), (far, P.SC_Y)]


def ads1115_centre() -> tuple[float, float]:
    """Upper level, in the dead space beside the AS7341 — **not on the plate**.

    It started on the plate and would not fit. At 28 mm long it needs a clear
    run, and the plate's clear runs are chopped up by the corner screw holes at
    one end and the cable tie posts at the other: 26.7 mm between them, against
    28 mm of board. Moving it up beside the AS7341 solves it outright, because
    the bosses are short and both boards simply pass over them. The dead space
    the AS7341's sensor offset forces is exactly 32 mm — which is what this
    board needed.
    """
    return P.SC_X - 21.0 * P.MM, P.SC_Y


def ads1115_standoff_points() -> list[tuple[float, float]]:
    """Four posts, so the ADS hangs from the top wall like the AS7341."""
    cx, _ = ads1115_centre()
    dx = P.SC_ADS1115_L / 2 - 3.0 * P.MM
    dy = P.SC_ADS1115_W / 2 - 3.0 * P.MM
    return [(cx + sx * dx, P.SC_Y + sy * dy) for sx in (-1, 1) for sy in (-1, 1)]


def bme280_centre() -> tuple[float, float]:
    """The only board on the plate, at the vented end, in the moving air.

    It is the one that has to read the canopy rather than the box, so it sits
    lowest, nearest the inlet slots, and furthest from anything that dissipates.
    """
    return P.SC_X + 22.0 * P.MM, P.SC_Y


def vent_xs() -> list[float]:
    """Slot centres in the plate, in the clear band between the two boards."""
    first = P.SC_X + 2.0 * P.MM
    return [first + i * P.SC_VENT_PITCH for i in range(3)]


def wall_vent_xs() -> list[float]:
    """Slots high in the rear wall — the outlet of the convection path."""
    return [P.SC_X + d * P.MM for d in (-30.0, -18.0, -6.0)]


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def _chamfer_verticals(part: "Part", z0: float, z1: float) -> "Part":
    """Take SC_CHAMFER off the four vertical corners, as plinth.py does.

    Cut with a rotated box rather than a kernel fillet: this package has no
    edge-selection anywhere, and a chamfer a cutter makes is a chamfer you can
    reason about.
    """
    from build123d import Rot

    from ._shapes import box, location_in

    s = P.SC_CHAMFER * 2 ** 0.5
    hx, hy = P.SC_LEN / 2, P.SC_WID / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            cutter = Rot(0, 0, 45) * box(s, s, (z1 - z0) + 2.0, at=(0, 0, 0))
            part -= location_in(P.SC_X + sx * hx, P.SC_Y + sy * hy, z0 - 1.0) * cutter
    return part


def build_body() -> "Part":
    """The upper half: top face, four walls, the optics, the lip."""
    from ._shapes import CENTRE, box, cyl_z, labelled

    z0, z1 = plate_top(), top_face()
    h = z1 - z0
    ix, iy = inner_half()
    px, py = port_centre()

    body = box(P.SC_LEN, P.SC_WID, h, at=(P.SC_X, P.SC_Y, z0))
    body = _chamfer_verticals(body, z0, z1)

    # Hollow from below. The top wall stays; the bottom is open to the plate.
    body -= box(2 * ix, 2 * iy, h - P.SC_WALL + 1.0, at=(P.SC_X, P.SC_Y, z0 - 1.0))

    # The lip: the rear wall carries on down past the floor and bears on the
    # block's rear face. It hangs **outboard** of that face, not flush with it —
    # flush means inside, and inside means 0.08 in3 of printed plastic sharing
    # space with the block. It stands 2 mm proud at the back, where nothing
    # looks. Caught by the interference check against the CMU.
    lip = box(P.SC_LEN, P.SC_WALL, P.SC_LIP_DROP,
              at=(P.SC_X, P.SC_Y + P.SC_WID / 2 + P.SC_WALL / 2, z0 - P.SC_LIP_DROP))
    body += lip

    # Diffuser recess from the top face, then the aperture through the rest of
    # the top wall. The 0.9 mm ledge between them is what the disc sits on.
    body -= cyl_z(P.SC_PORT_DIA, P.SC_PORT_DEPTH + 0.5,
                  at=(px, py, z1 - P.SC_PORT_DEPTH))
    body -= cyl_z(P.SC_APERTURE_DIA, P.SC_WALL + 1.0,
                  at=(px, py, z1 - P.SC_WALL - 0.5))

    # The baffle: field stop, LED shield and the standoff that sets sensor
    # height, in one feature.
    baffle = cyl_z(P.SC_BAFFLE_OD, P.SC_BAFFLE_DROP, at=(px, py, board_top()))
    baffle -= cyl_z(P.SC_BAFFLE_ID, P.SC_BAFFLE_DROP + 1.0, at=(px, py, board_top() - 0.5))
    body += baffle

    for sx, sy in standoff_points() + ads1115_standoff_points():
        body += cyl_z(P.SC_POST_DIA, P.SC_BAFFLE_DROP, at=(sx, sy, board_top()))

    # Bosses for the heat-set inserts. Deliberately short — the AS7341 lies
    # above them, and a full-height boss would foul it.
    for bx, by in boss_points():
        body += cyl_z(P.SC_BOSS_DIA, P.SC_BOSS_H, at=(bx, by, z0))
        body -= cyl_z(P.SC_INSERT_HOLE, P.SC_INSERT_DEPTH + 0.5, at=(bx, by, z0 - 0.5))

    # Cable entries: notches in the walls' bottom edge, closed by the plate. A
    # hole through a vertical wall wants a teardrop or a bridge; a notch wants
    # neither, and the cable drops in instead of threading. The rear notch runs
    # on down through the lip, so the loom drops into a channel rather than
    # bending over an edge.
    body -= box(P.SC_CABLE_W, P.SC_WALL * 4, P.SC_LIP_DROP + P.SC_CABLE_H,
                at=(P.SC_X, P.SC_Y + P.SC_WID / 2, z0 - P.SC_LIP_DROP))
    body -= box(P.SC_PROBE_W, P.SC_WALL * 3, P.SC_PROBE_H,
                at=(P.SC_X, P.SC_Y - P.SC_WID / 2, z0))

    # Strain relief: a pair of posts inside each notch, zip tie between them.
    for sy, gap in ((1, P.SC_TIE_POST_GAP), (-1, P.SC_TIE_POST_GAP)):
        wall_y = P.SC_Y + sy * (iy - P.SC_TIE_POST_DIA)
        for sx in (-1, 1):
            body += cyl_z(P.SC_TIE_POST_DIA, P.SC_BOSS_H,
                          at=(P.SC_X + sx * gap / 2, wall_y, z0))

    # Convection outlet, high in the rear wall. 2 mm tall, so the top edge is a
    # bridge the length of the slot and nothing more.
    for vx in wall_vent_xs():
        body -= box(P.SC_VENT_L, P.SC_WALL * 3, P.SC_VENT_W,
                    at=(vx, P.SC_Y + P.SC_WID / 2, ceiling() - 4.0 * P.MM), align=CENTRE)

    return labelled(body, "sensor_case_body")


def build_base() -> "Part":
    """The lower half: the two blind boards, the inlet vents, the feet."""
    from ._shapes import box, cyl_z, labelled

    ix, iy = inner_half()
    z0 = P.SC_Z0
    # Sits inside the body's cavity, with a running clearance so it drops in.
    clear = 0.2 * P.MM
    plate = box(2 * (ix - clear), 2 * (iy - clear), P.SC_BASE_T, at=(P.SC_X, P.SC_Y, z0))

    # **No printed fences round the boards, deliberately.** A fence has to be
    # sized to an outline, and these outlines come off vendor listings rather
    # than a caliper. A fence that is 1 mm wrong is a board that will not go in;
    # foam tape is 1 mm wrong and does not care. It also removes every collision
    # between a fence and a boss — there is no position where a fenced ADS1115
    # clears both the corner boss and the tie posts. Tape the two blind boards
    # to the plate; nothing here is subject to vibration.
    #
    # Inlet vents, in the clear band between where the two boards land.
    for vx in vent_xs():
        plate -= box(P.SC_VENT_W, P.SC_VENT_L, P.SC_BASE_T + 1.0,
                     at=(vx, P.SC_Y, z0 - 0.5))

    # Screw clearance and countersink, so nothing proud bears on the block.
    for bx, by in boss_points():
        plate -= cyl_z(P.SC_SCREW_DIA, P.SC_BASE_T + 1.0, at=(bx, by, z0 - 0.5))
        plate -= cyl_z(P.SC_SCREW_CSK, P.SC_SCREW_CSK / 2, at=(bx, by, z0 - 0.01))

    # Recesses for four self-adhesive silicone feet. They set the seating plane,
    # grip the block, and hold the perimeter open so air can get under.
    for fx, fy in boss_points():
        plate -= cyl_z(P.SC_FOOT_DIA, P.SC_FOOT_DEPTH, at=(fx, fy, z0 - 0.001))

    return labelled(plate, "sensor_case_base")


def build() -> "Part":
    """Both halves, assembled, where they sit on the block."""
    from ._shapes import labelled

    return labelled(build_body() + build_base(), "sensor_case")


# --------------------------------------------------------------------------
# Print orientation
# --------------------------------------------------------------------------

def for_print() -> dict[str, Part]:
    """Each half moved to the origin and turned the way it prints.

    The body goes top-face-down: that face is the only one on show, and a bed
    face on a textured sheet is the matte this object wants. The plate prints
    the way it is modelled, underside on the bed, so the face that meets the
    block is flat and takes the adhesive feet cleanly.
    """
    from build123d import Rot

    from ._shapes import bbox_in, labelled, location_in

    out: dict[str, "Part"] = {}
    for name, part, flip in (("sensor_case_body", build_body(), True),
                             ("sensor_case_base", build_base(), False)):
        if flip:
            part = Rot(180, 0, 0) * part
        bb = bbox_in(part)
        placed = location_in(-(bb["x0"] + bb["x1"]) / 2,
                             -(bb["y0"] + bb["y1"]) / 2,
                             -bb["z0"]) * part
        out[name] = labelled(placed, name)
    return out
