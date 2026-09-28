#!/usr/bin/env python3
"""The fabrication pack: DXFs to cut from, and a list of what to buy.

    python cad/fabrication.py          # writes cad/out/fab/

Outputs
-------
fab/plate.dxf          the instrument plate, 1/8 mild steel, full hole schedule
fab/case_body.dxf      the case's flat development, 16 ga, with bend lines
fab/fascia.dxf         the clear acrylic band
fab/backplate.dxf      the console backplate, a plain blank (no shear in the shop)
fab/lightbox.dxf       the lightbox shell's flat, 16 ga, vents and bend lines
fab/tray.dxf           the drip tray's flat, 304 stainless 16 ga, bend lines
fab/ply_*.dxf          every carcass panel, rail and cleat, for the CNC router
fab/cutlist.md         ply panels, frame members, sheet and bought stock
fab/cutlist.json       the same, for anything that wants to read it
fab/README.md          what each file is and how to read it

**The DXFs are in inches, 1:1.** build123d's exporter tags a unit in the
header but does not convert, so the flat patterns here are authored directly
in inch coordinates rather than in the millimetres the solid model is built
in — and ``test_cad_fabrication`` reads the written files back to check both
the tag and a known coordinate. Do not "fix" that by reusing ``_shapes``.

Layers: ``cut`` is the profile and every hole, ``bend`` is a fold line and
must not be cut, ``mark`` is scribe-only (the dial witness rings).

Bend lines are drawn at the theoretical fold, with no bend allowance: the
K-factor belongs to whoever is folding it, and the blank sizes here are the
sum of the flat faces. Give the shop the STEP as well and let them develop
it their way if they would rather.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from build123d import (  # noqa: E402
    Circle,
    Line,
    Pos,
    Rectangle,
    Sketch,
    Unit,
)
from build123d.exporters import ExportDXF, LineType  # noqa: E402

from cad.growlab_cad import canopy as _canopy, case, fixture, mast, params as P, plinth, tray  # noqa: E402
from cad.growlab_cad.face import corner_screw_points, knob_points  # noqa: E402
from pi.dashboard.panel_geometry import (  # noqa: E402
    DIAL_BEZEL_OD,
    FACE_HEIGHT,
    FACE_WIDTH,
    SCHEDULE,
)

OUT = REPO / "cad" / "out" / "fab"


# ---------------------------------------------------------------------------
# 2D helpers. Everything here is in INCHES — see the module docstring.
# ---------------------------------------------------------------------------

def rect(w: float, h: float, at: tuple[float, float]) -> Sketch:
    """A rectangle by its bottom-left corner."""
    return Pos(at[0] + w / 2, at[1] + h / 2) * Rectangle(w, h)


def holes(sk: Sketch, pts: list[tuple[float, float]], dia: float) -> Sketch:
    for x, y in pts:
        sk -= Pos(x, y) * Circle(dia / 2)
    return sk


def _write(path: Path, cut, bend=None, mark=None) -> None:
    ex = ExportDXF(unit=Unit.IN, line_weight=0.35)
    ex.add_layer("cut", line_weight=0.5)
    ex.add_shape(cut, layer="cut")
    if bend:
        ex.add_layer("bend", line_type=LineType.ISO_DASH, line_weight=0.25)
        ex.add_shape(bend, layer="bend")
    if mark:
        ex.add_layer("mark", line_type=LineType.ISO_DOT, line_weight=0.18)
        ex.add_shape(mark, layer="mark")
    ex.write(str(path))


# ---------------------------------------------------------------------------
# The instrument plate — 1/8 in mild steel, white DTM acrylic.
# Origin at the plate's bottom-left, which is how the hole schedule is written.
# ---------------------------------------------------------------------------

def plate_flat() -> tuple[Sketch, list]:
    sk = rect(FACE_WIDTH, FACE_HEIGHT, (0, 0))
    marks = []
    for e in SCHEDULE.elements:
        if e.kind == "dial":
            if P.DIAL_CUT_DIAMETER is not None:
                sk -= Pos(e.x, e.y) * Circle(P.DIAL_CUT_DIAMETER / 2)
            else:
                # Not cut: a scribe ring at the bezel OD on the back, so the
                # position is on the part and the cut is not guessed.
                marks.extend((Pos(e.x, e.y) * Circle(DIAL_BEZEL_OD / 2)).edges())
        elif e.kind == "window":
            sk -= rect(e.width, e.height, (e.x - e.width / 2, e.y - e.height / 2))
        else:
            sk -= Pos(e.x, e.y) * Circle(e.width / 2)
    sk = holes(sk, corner_screw_points(), P.FACE_SCREW_DIA)
    return sk, marks


# ---------------------------------------------------------------------------
# The case body — 16 ga, one blank, four walls up and two return flanges in.
#
#   +--------+-----------+--------+      arms:  side = wall + flange
#   |        |    top    |        |             top/bottom = wall only
#   +--------+-----------+--------+      (no flange top or bottom: it would
#   | flange |           | flange |       reach behind the plate's edge and
#   |  wall  |   BACK    |  wall  |       foul a high dial — see params)
#   +--------+-----------+--------+
#   |        |  bottom   |        |
#   +--------+-----------+--------+
# ---------------------------------------------------------------------------

def case_metrics() -> dict:
    t, f = P.CASE_SHEET_T, P.CASE_FLANGE
    wall = (case.Y1 - t) - case.y_front()      # back's inner face to the front edge
    return {
        "t": t,
        "flange": f,
        "wall": wall,
        "back_w": FACE_WIDTH - 2 * t,
        "back_h": FACE_HEIGHT - 2 * t,
        "blank_w": FACE_WIDTH - 2 * t + 2 * (wall + f),
        "blank_h": FACE_HEIGHT - 2 * t + 2 * wall,
    }


def case_flat() -> tuple[Sketch, list]:
    m = case_metrics()
    arm_x, arm_y = m["wall"] + m["flange"], m["wall"]
    bw, bh = m["back_w"], m["back_h"]

    back = rect(bw, bh, (arm_x, arm_y))
    sk = (
        back
        + rect(arm_x, bh, (0, arm_y))                    # left wall + flange
        + rect(arm_x, bh, (arm_x + bw, arm_y))           # right wall + flange
        + rect(bw, arm_y, (arm_x, 0))                    # bottom wall
        + rect(bw, arm_y, (arm_x, arm_y + bh))           # top wall
    )

    # Holes. The back's own coordinates run from its bottom-left; a point at
    # plate height z sits (z - t) above the back's bottom edge.
    sk -= Pos(arm_x + bw / 2, arm_y + 1.5 - m["t"]) * Circle(P.CASE_LOOM_DIA / 2)

    # The four taps, in the side flanges, on the plate's own F1-4 centres.
    # Each flange folds in from its wall's bend; the screw's distance from that
    # bend is what survives the fold, measured from the near edge of the plate.
    taps = []
    for px, py in corner_screw_points():
        y = arm_y + (py - m["t"])
        if px < FACE_WIDTH / 2:
            from_bend = px - m["t"]
            taps.append((m["flange"] - from_bend, y))
        else:
            from_bend = (FACE_WIDTH - m["t"]) - px
            taps.append((m["blank_w"] - m["flange"] + from_bend, y))
    sk = holes(sk, taps, P.CASE_TAP_DIA)

    # Bend lines: four at the back's edges, two more at the flanges.
    bends = [
        Line((arm_x, arm_y), (arm_x, arm_y + bh)),
        Line((arm_x + bw, arm_y), (arm_x + bw, arm_y + bh)),
        Line((arm_x, arm_y), (arm_x + bw, arm_y)),
        Line((arm_x, arm_y + bh), (arm_x + bw, arm_y + bh)),
        Line((m["flange"], arm_y), (m["flange"], arm_y + bh)),
        Line((m["blank_w"] - m["flange"], arm_y), (m["blank_w"] - m["flange"], arm_y + bh)),
    ]
    return sk, bends


# ---------------------------------------------------------------------------
# The fascia — 1/4 in clear cast acrylic. Origin at its bottom-left.
# ---------------------------------------------------------------------------

def fascia_metrics() -> dict:
    bz0, bz1 = plinth._fascia_band()
    return {
        "x0": -P.PLINTH_W / 2 + P.CHAMFER,
        "z0": bz0,
        "w": P.PLINTH_W - 2 * P.CHAMFER,
        "h": bz1 - bz0,
    }


def fascia_flat() -> Sketch:
    m = fascia_metrics()
    sk = rect(m["w"], m["h"], (0, 0))
    sk = holes(sk, [(wx - m["x0"], wz - m["z0"]) for wx, wz, _ in knob_points()],
               knob_points()[0][2] + 2 * P.KNOB_HOLE_CLEARANCE)
    sk = holes(sk, [(wx - m["x0"], wz - m["z0"]) for wx, wz in plinth.fascia_screw_points()],
               P.FASCIA_SCREW_DIA)
    return sk


# ---------------------------------------------------------------------------
# Pans — the lightbox and the tray are the same shape: a base with four walls
# folded off its edges, corners notched square and welded.
#
#            +--------------+
#            |     wall     |
#   +--------+--------------+--------+
#   |  wall  |     BASE     |  wall  |      walls fold off the base's edges;
#   +--------+--------------+--------+      the corner squares are cut away
#            |     wall     |               and the seams welded after folding
#            +--------------+
#
# As with the case, the base is the modelled outside less a wall thickness each
# side, and each wall is the modelled height less one thickness, so the blank is
# the sum of the flat faces and the folded outside is the modelled outside.
# Four-sided pans want a box-and-pan (finger) brake for the last two folds.
# ---------------------------------------------------------------------------

def pan_metrics(outer_w: float, outer_d: float, outer_h: float, t: float) -> dict:
    base_w, base_d, wall = outer_w - 2 * t, outer_d - 2 * t, outer_h - t
    return {"t": t, "base_w": base_w, "base_d": base_d, "wall": wall,
            "blank_w": base_w + 2 * wall, "blank_d": base_d + 2 * wall}


def pan_flat(m: dict) -> tuple[Sketch, list]:
    """The cruciform blank and its four bend lines, origin bottom-left."""
    a, bw, bd = m["wall"], m["base_w"], m["base_d"]
    sk = (rect(bw, bd, (a, a))
          + rect(a, bd, (0, a)) + rect(a, bd, (a + bw, a))
          + rect(bw, a, (a, 0)) + rect(bw, a, (a, a + bd)))
    bends = [
        Line((a, a), (a, a + bd)),
        Line((a + bw, a), (a + bw, a + bd)),
        Line((a, a), (a + bw, a)),
        Line((a, a + bd), (a + bw, a + bd)),
    ]
    return sk, bends


def _to_base(m: dict, centre: tuple[float, float]):
    """Model plan (x, y) -> flat coordinates on the base."""
    x0 = centre[0] - m["base_w"] / 2
    y0 = centre[1] - m["base_d"] / 2
    return lambda x, y: (m["wall"] + x - x0, m["wall"] + y - y0)


def lightbox_metrics() -> dict:
    return pan_metrics(P.FIXTURE_W, P.FIXTURE_D, P.FIXTURE_H, P.LIGHTBOX_T)


def lightbox_flat() -> tuple[Sketch, list]:
    """Drawn from above: the base is the top, the walls fold down away from you.

    Nine vents in the top over the heatsink, and one slot in each end wall at
    mid-height — the same slots ``fixture.py`` cuts, from the same functions.
    """
    m = lightbox_metrics()
    sk, bends = pan_flat(m)
    to = _to_base(m, (P.FIXTURE_X, P.FIXTURE_Y))
    for x in fixture.vent_xs():
        fx, fy = to(x, P.FIXTURE_Y)
        sk -= rect(P.LIGHTBOX_VENT_W, P.LIGHTBOX_VENT_L,
                   (fx - P.LIGHTBOX_VENT_W / 2, fy - P.LIGHTBOX_VENT_L / 2))
    # End slots: in the end walls, which are the left and right arms. The arm's
    # free edge is the wall's bottom, so the slot's height up the wall is its
    # distance in from the blank's edge.
    up = fixture.end_slot_zc() - fixture.shell_z0()
    _, fy = to(P.FIXTURE_X, P.FIXTURE_Y)
    for fx in (up, m["blank_w"] - up):
        sk -= rect(P.LIGHTBOX_VENT_W, P.LIGHTBOX_VENT_L,
                   (fx - P.LIGHTBOX_VENT_W / 2, fy - P.LIGHTBOX_VENT_L / 2))
    return sk, bends


def tray_metrics() -> dict:
    return pan_metrics(P.TRAY_W, P.TRAY_D, P.TRAY_UPSTAND + P.TRAY_T, P.TRAY_T)


def tray_flat() -> tuple[Sketch, list]:
    """Drawn from above: the floor's inside face, upstands fold UP toward you.

    That matters here, unlike the lightbox: the mast notch is off-centre, and
    folding the other way makes its mirror image. Four pad cutouts in the
    floor, and the mast notch through the floor and on out through the back
    upstand — so the back bend is two lines, either side of it.
    """
    m = tray_metrics()
    sk, bends = pan_flat(m)
    to = _to_base(m, tray.plan_centre())
    cut = P.PAD_SIZE + 2 * P.PAD_CUTOUT_CLEARANCE
    for px, py in tray.pad_centres():
        fx, fy = to(px, py)
        sk -= rect(cut, cut, (fx - cut / 2, fy - cut / 2))

    x0, x1, y_front = tray_notch_flat()
    sk -= rect(x1 - x0, m["blank_d"] - y_front + 0.5, (x0, y_front))

    # The back bend is the last of pan_flat's four; the notch splits it.
    a, bw, bd = m["wall"], m["base_w"], m["base_d"]
    bends = bends[:3] + [Line((a, a + bd), (x0, a + bd)),
                         Line((x1, a + bd), (a + bw, a + bd))]
    return sk, bends


def tray_notch_flat() -> tuple[float, float, float]:
    """(x0, x1, y_front) of the mast notch, in flat coordinates."""
    m = tray_metrics()
    nx, ny, ncx, ncy = tray.mast_notch()
    fx, fy = _to_base(m, tray.plan_centre())(ncx, ncy - ny / 2)
    return fx - nx / 2, fx + nx / 2, fy


def backplate_size() -> tuple[float, float]:
    bz0, bz1 = plinth._fascia_band()
    return P.INSIDE_X1 - P.INSIDE_X0, bz1 - bz0


def backplate_flat() -> Sketch:
    """A plain rectangle — but there is no shear, so it goes on the plasma too."""
    return rect(*backplate_size(), (0, 0))


# ---------------------------------------------------------------------------
# The carcass — birch ply, every part a 2D profile for the CNC router.
#
# Each file is one part, origin at its bottom-left, drawn as seen from the
# front (panels facing forward) or from the viewer's left (panels running
# front to back, x = 0 at the FRONT edge). Everything is a through-cut, so a
# part flipped on the table is the same part.
#
# What a 2D profile cannot carry, and the cut list says instead: the 45°
# chamfer on the sides' outer vertical edges, and the header's rebate.
# ---------------------------------------------------------------------------

_Z0 = plinth.Z0
_BAND = plinth._fascia_band()


def _dogbone(corner: tuple[float, float], void: tuple[int, int]) -> Sketch:
    """A relief at an inside corner, so a square-edged part seats in it.

    ``void`` points from the corner into the cut-away region. The bit is run
    diagonally into the corner until its edge reaches it: the circle's centre
    is in the void, r from the corner, and the circle passes through it.
    """
    r = P.ROUTER_BIT_DIA / 2
    d = r / 2 ** 0.5
    return Pos(corner[0] + void[0] * d, corner[1] + void[1] * d) * Circle(r)


def _side(vents: list[tuple[float, float]], vent_dia: float) -> Sketch:
    """A carcass side, x = model y (0 at the front), y = height above its foot.

    The band notch in the front edge is where the fascia's ends sit: through
    the full thickness, FASCIA_POCKET deep, dogboned so the acrylic's square
    corners reach the back of it.
    """
    w, h = P.PLINTH_D, plinth.Z1 - _Z0
    a, b = _BAND[0] - _Z0, _BAND[1] - _Z0
    sk = rect(w, h, (0, 0)) - rect(P.FASCIA_POCKET, b - a, (0, a))
    sk -= _dogbone((P.FASCIA_POCKET, a), (-1, 1))
    sk -= _dogbone((P.FASCIA_POCKET, b), (-1, -1))
    return holes(sk, [(y, z - _Z0) for y, z in vents], vent_dia)


def ply_side_left() -> Sketch:
    """Wet-bay vents: an open reservoir in a sealed box makes a humid box."""
    z = plinth.RAIL_BOTTOM - 1.0
    return _side([(P.RESERVOIR_Y0 + 1.5 + i * 2.5, z) for i in range(4)], 1.0)


def ply_side_right() -> Sketch:
    """Console-bay vents, low and forward, for the PSU and driver."""
    y = (P.CONSOLE_Y0 + P.CONSOLE_Y1) / 2
    return _side([(y, plinth.FLOOR_TOP + 2.0 + i * 1.5) for i in range(3)], 0.75)


def ply_rear() -> tuple[Sketch, list]:
    """Between the sides, seen from the front. The door opening is a notch in
    its left edge, the wet bay's full width and height.

    The U-bolt holes are MARKED, not cut: their spacing is a CHOICE and the
    U-bolts are not bought. Drill them from the U-bolt in hand.
    """
    w, h = P.INSIDE_X1 - P.INSIDE_X0, plinth.Z1 - _Z0
    sk = rect(w, h, (0, 0)) - rect(plinth.DOOR_X1 - P.INSIDE_X0 + 0.5,
                                   plinth.DOOR_Z1 - plinth.DOOR_Z0,
                                   (-0.5, plinth.DOOR_Z0 - _Z0))
    marks = []
    for z in mast.strap_heights():
        for x in mast.strap_bolt_x():
            marks.extend((Pos(x - P.INSIDE_X0, z - _Z0)
                          * Circle(P.MAST_STRAP_BOLT_DIA / 2)).edges())
    return sk, marks


def ply_floor() -> Sketch:
    """Between the sides, front panel to rear panel, seen from above. The mast
    passes through a notch in its back edge to the frame below."""
    w, d = P.INSIDE_X1 - P.INSIDE_X0, P.REAR_INSIDE_Y - P.CARCASS_T
    c = P.MAST_NOTCH_CLEARANCE
    x0 = P.MAST_X - P.MAST_W / 2 - c - P.INSIDE_X0
    y0 = P.MAST_Y - P.MAST_D / 2 - c - P.CARCASS_T
    return rect(w, d, (0, 0)) - rect(P.MAST_W + 2 * c, d - y0 + 0.5, (x0, y0))


def ply_front_lower() -> Sketch:
    """The removable panel below the band: the PSU and driver are behind it."""
    return rect(P.INSIDE_X1 - P.INSIDE_X0, _BAND[0] - _Z0, (0, 0))


def ply_front_header() -> Sketch:
    """What is left of the front panel above the open band: a strip the
    fascia's top row screws into. Rebated FASCIA_POCKET from its face, so it
    finishes CARCASS_T - FASCIA_POCKET thick."""
    x0, z0 = P.INSIDE_X0, _BAND[1] - P.FASCIA_TOP_LIP
    sk = rect(P.INSIDE_X1 - P.INSIDE_X0, P.FASCIA_TOP_LIP, (0, 0))
    return holes(sk, [(x - x0, z - z0) for x, z in plinth.fascia_screw_points()
                      if z > z0], P.PILOT_DIA)


def ply_partition() -> Sketch:
    return rect(plinth.DIVIDER_X - P.DIVIDER_T / 2 - P.INSIDE_X0,
                plinth.RAIL_BOTTOM - plinth.FLOOR_TOP, (0, 0))


def ply_divider() -> Sketch:
    """Seen from the viewer's left, x = 0 at its front edge (the partition)."""
    w = P.REAR_INSIDE_Y - P.PARTITION_Y0
    sk = rect(w, plinth.RAIL_BOTTOM - plinth.FLOOR_TOP, (0, 0))
    # The U-bolt reliefs, in its back edge.
    for y0, _, z0, z1 in plinth.divider_reliefs():
        sk -= rect(w - (y0 - P.PARTITION_Y0) + 0.5, z1 - z0,
                   (y0 - P.PARTITION_Y0, z0 - plinth.FLOOR_TOP))
    return holes(sk, [(plinth.LINE_PASS_Y - P.PARTITION_Y0,
                       plinth.LINE_PASS_Z - plinth.FLOOR_TOP)], P.MAST_LINE_PASS_H)


def ply_ledge() -> Sketch:
    return rect(P.INSIDE_X1 - P.INSIDE_X0,
                P.CONSOLE_Y1 - P.LEDGE_CHASE - P.FASCIA_POCKET, (0, 0))


def ply_shelf() -> Sketch:
    return rect(plinth.DIVIDER_X - P.DIVIDER_T / 2 - P.INSIDE_X0,
                P.REAR_INSIDE_Y - P.PARTITION_Y1, (0, 0))


SHELF_CLEAT_H = 1.5  # as plinth.build_shelf


def ply_shelf_cleat() -> Sketch:
    return rect(P.REAR_INSIDE_Y - P.PARTITION_Y1, SHELF_CLEAT_H, (0, 0))


def ply_door() -> Sketch:
    g = P.DOOR_GAP
    return rect(plinth.DOOR_X1 - plinth.DOOR_X0 - 2 * g,
                plinth.DOOR_Z1 - plinth.DOOR_Z0 - 2 * g, (0, 0))


def rail_lengths() -> dict[str, float]:
    """The top rail as sticks that butt, not the model's overlapping union.

    Front and back run the full inside width; sides and cross rails run
    between them. The back member is two pieces — the mast stands in its line.
    """
    t, c = P.CARCASS_T, P.MAST_NOTCH_CLEARANCE
    w = P.INSIDE_X1 - P.INSIDE_X0
    notch_x0 = P.MAST_X - P.MAST_W / 2 - c
    notch_x1 = P.MAST_X + P.MAST_W / 2 + c
    return {
        "front": w,
        "back_left": notch_x0 - P.INSIDE_X0,
        "back_right": P.INSIDE_X1 - notch_x1,
        "between": P.REAR_INSIDE_Y - P.CARCASS_T - 2 * t,
    }


def ply_parts() -> list[dict]:
    """Every ply part: its file, stock, count, and the sketch it is cut from.

    The cut list's ply table is this, so the list and the files cannot drift.
    """
    T, H = P.CARCASS_T, P.DIVIDER_T
    rl = rail_lengths()
    rear, rear_marks = ply_rear()
    return [
        {"part": "Side, left", "file": "ply_side_left.dxf", "t": T, "qty": 1,
         "sketch": ply_side_left(),
         "note": f"{P.CHAMFER} × 45° chamfer on the outer face of both vertical edges, "
                 "after cutting. Wet-bay vents"},
        {"part": "Side, right", "file": "ply_side_right.dxf", "t": T, "qty": 1,
         "sketch": ply_side_right(),
         "note": f"{P.CHAMFER} × 45° chamfer as the left. Console-bay vents"},
        {"part": "Rear panel", "file": "ply_rear.dxf", "t": P.REAR_PANEL_T, "qty": 1,
         "sketch": rear, "marks": rear_marks,
         "note": "door opening notched in; U-bolt holes MARKED — drill from the U-bolt in hand"},
        {"part": "Rear door", "file": "ply_door.dxf", "t": P.REAR_PANEL_T, "qty": 1,
         "sketch": ply_door(), "note": "hinge and catch TBD — cut it now, hang it later"},
        {"part": "Floor", "file": "ply_floor.dxf", "t": T, "qty": 1,
         "sketch": ply_floor(), "note": "mast notch in the back edge"},
        {"part": "Front panel, lower", "file": "ply_front_lower.dxf", "t": T, "qty": 1,
         "sketch": ply_front_lower(), "note": "removable; screws to the sides"},
        {"part": "Front header", "file": "ply_front_header.dxf", "t": T, "qty": 1,
         "sketch": ply_front_header(),
         "note": f"rebate the face {P.FASCIA_POCKET} deep over its full height, leaving "
                 f"{T - P.FASCIA_POCKET:.2f}; fascia top-row pilots"},
        {"part": "Console ledge", "file": "ply_ledge.dxf", "t": P.LEDGE_T, "qty": 1,
         "sketch": ply_ledge(),
         "note": "fascia bottom-row pilots go in its front edge: drill through the fascia"},
        {"part": "Reservoir shelf", "file": "ply_shelf.dxf", "t": P.SHELF_T, "qty": 1,
         "sketch": ply_shelf(), "note": ""},
        {"part": "Shelf cleat", "file": "ply_shelf_cleat.dxf", "t": T, "qty": 2,
         "sketch": ply_shelf_cleat(),
         "note": "one on the left side, one on the divider; slot the fixings on the bench "
                 "once the flow test sets the lift"},
        {"part": "Console partition", "file": "ply_partition.dxf", "t": P.CONSOLE_PARTITION_T,
         "qty": 1, "sketch": ply_partition(), "note": ""},
        {"part": "Bay divider", "file": "ply_divider.dxf", "t": H, "qty": 1,
         "sketch": ply_divider(),
         "note": "grommeted line pass; three notches in the back edge for the U-bolts"},
        {"part": "Top rail, front", "file": "ply_rail_front.dxf", "t": T, "qty": 1,
         "sketch": rect(rl["front"], T, (0, 0)), "note": f"{T} × {T} stick"},
        {"part": "Top rail, back left", "file": "ply_rail_back_left.dxf", "t": T, "qty": 1,
         "sketch": rect(rl["back_left"], T, (0, 0)), "note": "the mast stands in the gap"},
        {"part": "Top rail, back right", "file": "ply_rail_back_right.dxf", "t": T, "qty": 1,
         "sketch": rect(rl["back_right"], T, (0, 0)), "note": ""},
        {"part": "Top rail, side and cross", "file": "ply_rail_between.dxf", "t": T, "qty": 4,
         "sketch": rect(rl["between"], T, (0, 0)),
         "note": "two at the sides, two under the pads; all butt between front and back"},
    ]


# ---------------------------------------------------------------------------
# The cut list — what to buy and saw, from the same parameters.
# ---------------------------------------------------------------------------

def _bbox(sk: Sketch) -> tuple[float, float]:
    bb = sk.bounding_box()
    return bb.size.X, bb.size.Y


def cutlist() -> dict:
    m = case_metrics()
    fm = fascia_metrics()
    lm, tm = lightbox_metrics(), tray_metrics()
    frame_leg = P.SHADOW_GAP_H - P.FRAME_TUBE
    ring_x = P.PLINTH_W - 2 * P.FRAME_LEG_INSET
    ring_y = P.PLINTH_D - 2 * P.FRAME_LEG_INSET

    return {
        "units": "inches",
        "ply": {
            "stock": f"{P.CARCASS_T} and {P.DIVIDER_T} in birch ply",
            "parts": [
                {"part": r["part"], "qty": r["qty"], "t": r["t"],
                 "w": _bbox(r["sketch"])[0], "h": _bbox(r["sketch"])[1],
                 "file": r["file"], "note": r["note"]}
                for r in ply_parts()
            ] + [
                {"part": "Block pad", "qty": 4, "t": P.CMU_UNDERSIDE_Z - P.RAIL_TOP_Z,
                 "w": P.PAD_SIZE, "h": P.PAD_SIZE, "file": "—",
                 "note": "hardwood, or ply plus a shim to the height in t; glued to the "
                         "cross rails through the tray's cutouts"},
            ],
        },
        "steel": {
            "stock": f"{P.FRAME_TUBE} x {P.FRAME_TUBE} HSS or solid bar; "
                     f"Ø{P.MAST_OD} x {P.MAST_WALL} round tube for the mast",
            "parts": [
                {"part": "Frame leg", "qty": 4, "length": frame_leg,
                 "note": "levelling feet in the ends"},
                {"part": "Frame ring, left/right", "qty": 2, "length": ring_y, "note": ""},
                {"part": "Frame ring, front/back", "qty": 2, "length": ring_x,
                 "note": "back member notched for the mast"},
                {"part": "Mast", "qty": 1, "length": P.MAST_TOP,
                 "note": f"floor to cap. Side line pass {P.MAST_LINE_PASS_DIA} x "
                         f"{P.MAST_LINE_PASS_H} obround, grommeted. Rear cable slot "
                         f"{P.MAST_SLOT_W} wide, {P.MAST_SLOT_Z0}-{P.MAST_SLOT_Z1}, "
                         f"BOTH ENDS DRILLED ROUND (Ø{P.MAST_SLOT_KEYHOLE_DIA} top, "
                         f"Ø{P.MAST_SLOT_END_DIA} foot) — an undrilled end cracks. "
                         f"Deburr the slot. {P.MAST_STRAP_COUNT} U-bolts go round it"},
                {"part": "Mast cap", "qty": 1, "length": P.MAST_OD,
                 "note": f"Ø{P.MAST_OD} disc, {P.MAST_CAP_T} plate, welded solid — "
                         "no grommet, no removable cap. It is the tube's end "
                         "closure and the slot stops short of it"},
                {"part": "Carriage collar", "qty": 1, "length": P.CARRIAGE_H,
                 "note": f"Ø{_canopy.collar_od():.3f} over Ø{_canopy.collar_id():.3f} bore, "
                         f"{P.CARRIAGE_WALL} wall; front pad for the arm, rear boss "
                         f"saw-split {_canopy.KERF} and pinched by 2 x 1/4-20"},
                {"part": "Fixture arm, forward", "qty": 1,
                 "length": _canopy.collar_front_y()
                           - (P.FIXTURE_Y + P.FIXTURE_D / 2 - P.FIXTURE_BAR_D),
                 "note": f"{P.FIXTURE_ARM_W} x {P.FIXTURE_ARM_T} flat, welded to the "
                         "collar's front pad"},
                {"part": "Fixture arm, cross bar", "qty": 1, "length": P.FIXTURE_W,
                 "note": "along the fixture's back edge; spans the mast's offset"},
            ],
        },
        "sheet": [
            {"part": "Instrument plate", "material": f"{P.PLATE_T} mild steel, white DTM",
             "blank": [FACE_WIDTH, FACE_HEIGHT], "file": "plate.dxf",
             "cut_on": "waterjet",
             "note": f"{FACE_HEIGHT:g} long is the waterjet's whole bed; plasma if it "
                     "will not sit. The one visible cut edge, so the cleanest machine"},
            {"part": "Instrument case body", "material": "16 ga mild steel, white DTM",
             "blank": [m["blank_w"], m["blank_h"]], "file": "case_body.dxf",
             "cut_on": "CNC plasma",
             "note": "6 bends; see the drawing. 0.0625 is modelled; 16 ga steel is "
                     f"0.0598, inside the bend allowance. The four Ø{P.CASE_TAP_DIA:.3f} "
                     "taps: pierce only on the plasma, drill to size and tap M3"},
            {"part": "Console backplate", "material": f"{P.BACKPLATE_T} mild steel, white DTM",
             "blank": list(backplate_size()), "file": "backplate.dxf",
             "cut_on": "CNC plasma",
             "note": "plain rectangle — a DXF only because there is no shear"},
            {"part": "Fascia", "material": f"{P.FASCIA_T} clear cast acrylic",
             "blank": [fm["w"], fm["h"]], "file": "fascia.dxf",
             "cut_on": "CO2 laser",
             "note": "cast, not extruded — cast laser-cuts to a polished edge"},
            {"part": "Lightbox shell", "material": f"{P.LIGHTBOX_T} mild steel, white DTM",
             "blank": [lm["blank_w"], lm["blank_d"]], "file": "lightbox.dxf",
             "cut_on": "CNC plasma",
             "note": "4 bends, walls fold down; weld the four corner seams and dress "
                     "them. 9 top vents, 1 slot per end"},
            {"part": "Tray", "material": "304 stainless, 16 ga",
             "blank": [tm["blank_w"], tm["blank_d"]], "file": "tray.dxf",
             "cut_on": "CNC plasma",
             "note": "4 bends (the back one split by the mast notch), upstands fold UP "
                     "toward you as drawn. TIG the corner seams watertight"},
        ],
        "pending": [
            "Dial mounting studs — Simpson pattern, does not apply.",
            "Inky standoffs — transfer from the board in hand.",
        ],
    }


def cutlist_markdown(data: dict) -> str:
    out = ["# GROWLAB V1 — cut list", "",
           "Every figure is derived from `cad/growlab_cad/params.py`; nothing here is "
           "typed twice. Inches. Sizes are finished, not allowing for saw kerf or "
           "the rebates noted.", ""]

    out += ["## Ply — " + data["ply"]["stock"], "",
            "Cut on the CNC router. Sizes are finished; the files are the parts.", "",
            "| Part | Qty | T | W | H | File | Note |", "|---|---:|---:|---:|---:|---|---|"]
    for r in data["ply"]["parts"]:
        out.append(f"| {r['part']} | {r['qty']} | {r['t']:.4g} | {r['w']:.3f} | {r['h']:.3f} "
                   f"| {r['file']} | {r['note']} |")

    out += ["", "## Steel — " + data["steel"]["stock"], "",
            "| Part | Qty | Length | Note |", "|---|---:|---:|---|"]
    for r in data["steel"]["parts"]:
        out.append(f"| {r['part']} | {r['qty']} | {r['length']:.3f} | {r['note']} |")

    out += ["", "## Sheet and glazing", "",
            "| Part | Material | Blank | File | Cut on | Note |", "|---|---|---|---|---|---|"]
    for r in data["sheet"]:
        out.append(f"| {r['part']} | {r['material']} | {r['blank'][0]:.3f} × {r['blank'][1]:.3f} "
                   f"| {r.get('file', '—')} | {r.get('cut_on', '—')} | {r.get('note', '')} |")

    out += ["", "## Not on this list — measure first", ""]
    out += [f"- {p}" for p in data["pending"]]
    return "\n".join(out) + "\n"


PACK_README = """# fab/ — the pack you cut from

Generated by `python cad/fabrication.py` from the same parameters as the solid
model. If a number here disagrees with the STEP, the STEP is stale — rebuild.

| File | What |
|---|---|
| `plate.dxf` | Instrument plate, {plate_t} mild steel. Hole schedule from `panel_geometry.py`. |
| `case_body.dxf` | Case body flat, 16 ga. Blank {cbw:.3f} × {cbh:.3f}, six bends. |
| `fascia.dxf` | Clear cast acrylic band, {fascia_t}. Two knob holes, ten fixings. |
| `backplate.dxf` | Console backplate, {bpw:.3f} × {bph:.3f}. A plain blank. |
| `lightbox.dxf` | Lightbox shell flat, 16 ga. Blank {lbw:.3f} × {lbd:.3f}, four bends. |
| `tray.dxf` | Drip tray flat, 304 stainless 16 ga. Blank {tw:.3f} × {td:.3f}, four bends. |
| `ply_*.dxf` | Every carcass part for the CNC router, one file each. See the cut list. |
| `cutlist.md` | Ply, steel, sheet and glazing, with quantities. |

**Units: inches, 1:1.** The exporter tags the unit but does not convert, so
these are authored in inches directly; a test reads the files back and checks
both the tag and a coordinate.

**Layers.** `cut` — profile and holes. `bend` — fold lines, do not cut.
`mark` — scribe only.

**Bends** are drawn at the theoretical fold with no bend allowance; the
K-factor is the shop's. The blank is the sum of the flat faces.

**Which machine.** The cut list's *Cut on* column says. In short: the plate
on the waterjet (12 × 12 bed — it is the only steel part that fits, and the
one whose edge is seen), the fascia on the CO2 laser, everything else steel on
the CNC plasma. Nothing needs the shear the shop does not have.

**Plasma and small holes.** Anything under about 1/4 in comes off the plasma
as a pierce, not a hole: use it as a centre mark and drill to size.

**Ply** (CNC router): every file is a through-cut profile, so a part flipped
on the table is still the same part. The sides' band notch is dogboned for a
{bit} in bit; a bigger bit leaves corners the acrylic will not seat in. The
chamfer on the sides and the rebate on the header are not in the files — the
cut list says where. The rear panel's U-bolt holes are on `mark`: drill them
from the U-bolts in hand.

**Pans** (lightbox, tray): corners are notched square to the bend lines, so
after folding each corner is an open seam to weld. The last two folds of a
four-sided pan want a box-and-pan brake. The tray is stainless and carries
water: TIG its corners, and fold it with the drawing face up — the mast notch
is off-centre, so folding it the other way makes the mirror image.

**The dials are cut** at Ø 2.75, calipered from the Weston 301 bezels.

**Order of assembly** for the console, which is the only fiddly part: fold and
finish the case body, fit the electronics to it on the bench, screw the plate
on through F1–4 into the side flanges, drop the case onto the ledge, connect
at the terminal block, then glaze — the fascia sits in the rebate, screws into
the header above and the ledge below, and the knob caps go on last through it.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    plate, marks = plate_flat()
    _write(args.out / "plate.dxf", plate, mark=marks)

    body, bends = case_flat()
    _write(args.out / "case_body.dxf", body, bend=bends)

    _write(args.out / "fascia.dxf", fascia_flat())
    _write(args.out / "backplate.dxf", backplate_flat())

    shell, shell_bends = lightbox_flat()
    _write(args.out / "lightbox.dxf", shell, bend=shell_bends)

    pan, pan_bends = tray_flat()
    _write(args.out / "tray.dxf", pan, bend=pan_bends)

    for r in ply_parts():
        _write(args.out / r["file"], r["sketch"], mark=r.get("marks"))

    data = cutlist()
    (args.out / "cutlist.json").write_text(json.dumps(data, indent=2))
    (args.out / "cutlist.md").write_text(cutlist_markdown(data))

    m = case_metrics()
    (args.out / "README.md").write_text(PACK_README.format(
        plate_t=P.PLATE_T, fascia_t=P.FASCIA_T,
        cbw=m["blank_w"], cbh=m["blank_h"],
        bpw=backplate_size()[0], bph=backplate_size()[1],
        lbw=lightbox_metrics()["blank_w"], lbd=lightbox_metrics()["blank_d"],
        tw=tray_metrics()["blank_w"], td=tray_metrics()["blank_d"],
        bit=P.ROUTER_BIT_DIA,
    ))

    for f in sorted(args.out.iterdir()):
        shown = f.relative_to(REPO) if f.is_relative_to(REPO) else f
        print(f"wrote {shown}  ({f.stat().st_size // 1024 or 1} KB)")
    print(f"\ncase blank {m['blank_w']:.3f} × {m['blank_h']:.3f} in "
          f"(back {m['back_w']:.3f} × {m['back_h']:.3f}, wall {m['wall']:.4f}, flange {m['flange']})")
    if P.DIAL_CUT_DIAMETER is None:
        print("plate: dials are SCRIBE RINGS, not holes — caliper the Weston bezels first")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
