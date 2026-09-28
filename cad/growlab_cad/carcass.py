"""The carcass as panels with joinery: the one model the router files, the STEPs
and the assembled plinth all come from.

The house CNC joinery grammar (v1.4, ``lib/house.py`` in workbench and
fabrication) is the rulebook. Three-axis, one-sided, flat: every cut comes from
the up face, so the vocabulary is PROFILE, POCKET (dado, rabbet, bore) and HOLE.

1. One pocketed face per panel, declared; the other face gets through holes only.
3. Housing widths are MEASURED stock plus JOINT_CLEAR. Nominal never mates.
4. Dado T/3, rabbet T/2 at a panel end, of the panel the pocket is cut in.
5. Through, never stopped: every dado and rabbet runs edge to edge.
6. Nothing visible is dogboned. Apertures keep the cutter's fillet.
7. Always housed. Where a housing will not go, a screwed bearing joint.
9. Knock-down is bolts through holes.

Red-teamed 2026-09-28 against that grammar. What it found, and what replaced it:

* **The block stood on end-grain butt joints.** Six 3/4 sticks, each butted to
  the next, carried ~50 lb of CMU through two end-grain joints in series. Now a
  **deck**: one panel housed in both sides and the rear, the pads screwed up
  into it from below. It is also the diaphragm that squares the top of the box.
* **Nothing resisted racking.** The front is open across the band, the lower
  front comes off, and the rear is mostly door. The **partition and divider**
  are the shear walls, so they are housed on three edges each and glued.
* **The fascia's top row screwed into a floating strip** 0.35 thick. Now an
  **apron**: a 3/4 strip on edge, housed in the sides, glued under the deck's
  front edge, its face the glass's backstop.
* **Every panel was a butt joint**, floor and ledge included. Floor in rabbets
  at the foot of the sides and the rear; ledge, deck and apron in dados.
* The front panel now bolts to cleats, the door hangs on cup hinges, the shelf
  stands on pins, and the floor bolts down to the frame.

COORDINATES
    Every panel is written in WORLD coordinates (inches, the model's frame),
    because that is where it has to meet its neighbours. Its pockets, bores,
    holes and cutouts are world boxes and points too. ``flat()`` projects a
    panel onto its own sheet as the machine sees it: looking down on the
    pocketed face, which is up on the bed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import params as P

EPS = 1e-9

# Stock, as it is.
TA = P.PLY_T_ACTUAL
HA = P.HALF_T_ACTUAL
CLR = P.JOINT_CLEAR

# The box's outside, and the faces the stock puts inside it.
X0, X1 = -P.PLINTH_W / 2, P.PLINTH_W / 2
Y0, Y1 = 0.0, P.PLINTH_D
Z0, Z1 = P.SHADOW_GAP_H, P.TRAY_RIM_Z
XI0, XI1 = X0 + TA, X1 - TA        # the sides' inside faces
YR = Y1 - TA                       # the rear panel's inside face
FLOOR_TOP = Z0 + TA
DECK_TOP = P.RAIL_TOP_Z            # the tray floor rests on it
DECK_BOT = DECK_TOP - TA
APRON_Z0 = DECK_BOT - P.FASCIA_TOP_LIP
LEDGE_Z0, LEDGE_Z1 = P.FACE_Z0 - TA, P.FACE_Z0
PART_Y0, PART_Y1 = P.PARTITION_Y0, P.PARTITION_Y0 + HA
DIV_X0 = P.DIVIDER_X - P.DIVIDER_T / 2  # the divider's wet face: the door's jamb
DIV_X1 = DIV_X0 + HA

# The door opening in the rear panel: the wet bay's width, from the floor's
# rabbet to the deck's dado.
OPEN_X0, OPEN_X1 = XI0, DIV_X0
OPEN_Z0, OPEN_Z1 = Z0 + TA + CLR, DECK_BOT - CLR


def band() -> tuple[float, float]:
    from .plinth import _fascia_band

    return _fascia_band()


# ---------------------------------------------------------------------------
# The vocabulary
# ---------------------------------------------------------------------------

Box3 = tuple[float, float, float, float, float, float]  # x0, x1, y0, y1, z0, z1


@dataclass(frozen=True)
class Pocket:
    """A housing: a world box cut down from the panel's pocketed face.

    ``mates`` are the thicknesses of what goes in it, so its width can be
    checked against rule 3: the sum of the mates plus one JOINT_CLEAR.
    """

    box: Box3
    kind: str  # "dado" | "rabbet"
    mates: tuple[float, ...]
    note: str = ""


@dataclass(frozen=True)
class Bore:
    """A blind round pocket from the pocketed face: a shelf pin, a hinge cup."""

    at: tuple[float, float, float]  # world point on the pocketed face
    d: float
    depth: float
    kind: str


@dataclass(frozen=True)
class Hole:
    """Through the panel, along its normal."""

    at: tuple[float, float, float]
    d: float
    note: str = ""


@dataclass
class Panel:
    name: str
    file: str
    stock: str  # "3/4" | "1/2"
    box: Box3
    normal: str  # "x" | "y" | "z": the thickness axis
    up: int  # +1 / -1: which way the pocketed face (or the machine's up face) points
    pocket_face: str = "none"
    finish_face: str = "outside"
    qty: int = 1
    pockets: list[Pocket] = field(default_factory=list)
    bores: list[Bore] = field(default_factory=list)
    holes: list[Hole] = field(default_factory=list)
    cutouts: list[Box3] = field(default_factory=list)  # through: notches and openings
    marks: list[Hole] = field(default_factory=list)  # scribe or drill on the bench
    note: str = ""
    fabricated_elsewhere: bool = False  # in the assembly, not in the plinth union

    @property
    def t(self) -> float:
        a = "xyz".index(self.normal)
        return self.box[2 * a + 1] - self.box[2 * a]

    @property
    def nominal_t(self) -> float:
        return P.CARCASS_T if self.stock == "3/4" else P.DIVIDER_T

    def up_face(self) -> float:
        """World coordinate of the pocketed face along the normal."""
        a = "xyz".index(self.normal)
        return self.box[2 * a + 1] if self.up > 0 else self.box[2 * a]

    # -- the sheet, as the machine sees it ------------------------------------

    def axes(self) -> tuple[tuple[str, int], tuple[str, int]]:
        """(world axis, sign) of the sheet's u and v, looking down on the up
        face, right-handed, so a drawing is never a mirror image."""
        return {
            ("z", +1): (("x", +1), ("y", +1)),
            ("z", -1): (("x", +1), ("y", -1)),
            ("x", +1): (("y", +1), ("z", +1)),
            ("x", -1): (("y", -1), ("z", +1)),
            ("y", +1): (("x", -1), ("z", +1)),
            ("y", -1): (("x", +1), ("z", +1)),
        }[(self.normal, self.up)]

    def to_uv(self, pt: tuple[float, float, float]) -> tuple[float, float]:
        out = []
        for ax, sgn in self.axes():
            a = "xyz".index(ax)
            lo, hi = self.box[2 * a], self.box[2 * a + 1]
            out.append(pt[a] - lo if sgn > 0 else hi - pt[a])
        return out[0], out[1]

    def rect_uv(self, b: Box3) -> tuple[float, float, float, float]:
        """A world box's footprint on the sheet: (u0, u1, v0, v1)."""
        corners = [(b[0], b[2], b[4]), (b[1], b[3], b[5])]
        (ua, va), (ub, vb) = (self.to_uv(c) for c in corners)
        return min(ua, ub), max(ua, ub), min(va, vb), max(va, vb)

    def size_uv(self) -> tuple[float, float]:
        u0, u1, v0, v1 = self.rect_uv(self.box)
        return u1 - u0, v1 - v0

    def depth_of(self, pk: Pocket) -> float:
        a = "xyz".index(self.normal)
        return pk.box[2 * a + 1] - pk.box[2 * a]

    def across(self, pk: Pocket) -> float:
        """The housing's width: its short in-plane dimension, which is what the
        mating stock fits in."""
        u0, u1, v0, v1 = self.rect_uv(pk.box)
        su, sv = self.size_uv()
        through_u = u0 <= EPS and u1 >= su - EPS
        through_v = v0 <= EPS and v1 >= sv - EPS
        if through_u and not through_v:
            return v1 - v0
        if through_v and not through_u:
            return u1 - u0
        return min(u1 - u0, v1 - v0)

    def through(self, pk: Pocket) -> bool:
        u0, u1, v0, v1 = self.rect_uv(pk.box)
        su, sv = self.size_uv()
        return (u0 <= EPS and u1 >= su - EPS) or (v0 <= EPS and v1 >= sv - EPS)

    # -- the solid -----------------------------------------------------------

    def solid(self):
        """The panel in world position, every feature cut. Millimetres."""
        from ._shapes import MIN, box, cyl_x, cyl_y, cyl_z

        def wbox(b: Box3, grow: float = 0.0):
            x0, x1, y0, y1, z0, z1 = b
            return box(x1 - x0 + 2 * grow, y1 - y0 + 2 * grow, z1 - z0 + 2 * grow,
                       at=(x0 - grow, y0 - grow, z0 - grow), align=MIN)

        s = wbox(self.box)
        a = "xyz".index(self.normal)
        for pk in self.pockets:
            # Run the cutter out past the up face and past any edge it is flush
            # with, so no boolean resolves two coincident faces.
            b = list(pk.box)
            for i in range(3):
                lo, hi = self.box[2 * i], self.box[2 * i + 1]
                if i == a:
                    if self.up > 0:
                        b[2 * i + 1] += 0.01
                    else:
                        b[2 * i] -= 0.01
                    continue
                if b[2 * i] <= lo + EPS:
                    b[2 * i] -= 0.01
                if b[2 * i + 1] >= hi - EPS:
                    b[2 * i + 1] += 0.01
            s -= wbox(tuple(b))
        for c in self.cutouts:
            s -= wbox(_grow_along(c, a, self.box))
        cyl = {"x": cyl_x, "y": cyl_y}
        for h in self.holes:
            if self.normal == "z":
                s -= cyl_z(h.d, self.t + 0.2, at=(h.at[0], h.at[1], self.box[4] - 0.1))
            else:
                s -= cyl[self.normal](h.d, self.t + 0.2, at=h.at)
        for bo in self.bores:
            s -= _bore(self, bo)
        s.label = self.name
        return s


def _grow_along(b: Box3, a: int, host: Box3) -> Box3:
    """A cutout runs through the panel's thickness and past its edges."""
    out = list(b)
    out[2 * a] = host[2 * a] - 0.01
    out[2 * a + 1] = host[2 * a + 1] + 0.01
    return tuple(out)


def _bore(panel: Panel, bo: Bore):
    """A blind cylinder from the up face, ``depth`` into the panel, run 0.01 out
    past the face so the boolean is clean."""
    from ._shapes import cyl_x, cyl_y, cyl_z

    a = "xyz".index(panel.normal)
    face, up = panel.up_face(), panel.up
    length = bo.depth + 0.01
    if panel.normal == "z":
        z0 = face - bo.depth if up > 0 else face - 0.01
        return cyl_z(bo.d, length, at=(bo.at[0], bo.at[1], z0))
    c = list(bo.at)
    c[a] = face - up * bo.depth / 2 + up * 0.005
    return {"x": cyl_x, "y": cyl_y}[panel.normal](bo.d, length, at=tuple(c))


# ---------------------------------------------------------------------------
# The panels
# ---------------------------------------------------------------------------

def _side(left: bool) -> Panel:
    sx0, sx1 = (X0, XI0) if left else (XI1, X1)
    face = XI0 if left else XI1  # the inside, pocketed face
    inward = -1 if left else +1  # from the face into the panel

    def into(depth: float) -> tuple[float, float]:
        a, b = face, face + inward * depth
        return min(a, b), max(a, b)

    bz0, bz1 = band()
    pk = [
        Pocket((*into(P.RABBET_D), YR - CLR, Y1, Z0, Z1), "rabbet", (TA,), "the rear panel"),
        Pocket((*into(P.RABBET_D), Y0, Y1, Z0, Z0 + TA + CLR), "rabbet", (TA,), "the floor"),
        Pocket((*into(P.DADO_D), Y0, Y1, APRON_Z0 - CLR, DECK_TOP), "dado",
               (P.FASCIA_TOP_LIP, TA), "the apron under the deck, glued as one"),
        Pocket((*into(P.DADO_D), Y0, Y1, LEDGE_Z0 - CLR, LEDGE_Z1), "dado", (TA,), "the ledge"),
    ]
    bores, holes = [], []
    if left:
        pk.append(Pocket((*into(P.DADO_D), PART_Y0, PART_Y1 + CLR, Z0, Z1), "dado", (HA,),
                         "the console partition"))
        for y, z in shelf_pins():
            bores.append(Bore((face, y, z), P.SHELF_PIN_D, P.SHELF_PIN_DEPTH, "pin"))
        vz = P.RAIL_BOTTOM_Z - 1.0
        for i in range(4):
            holes.append(Hole(((sx0 + sx1) / 2, P.RESERVOIR_Y0 + 1.5 + i * 2.5, vz), 1.0,
                              "wet-bay vent"))
    else:
        y = (P.CONSOLE_Y0 + P.CONSOLE_Y1) / 2
        for i in range(3):
            holes.append(Hole(((sx0 + sx1) / 2, y, FLOOR_TOP + 2.0 + i * 1.5), 0.75,
                              "console-bay vent"))
    # The band notch in the front edge: the fascia's end sits in it. Taller
    # than the glass by BAND_REVEAL each way, so its rounded inside corners are
    # never where the glass's square corners go.
    notch = (sx0, sx1, Y0 - 0.01, P.FASCIA_POCKET, bz0 - P.BAND_REVEAL, bz1 + P.BAND_REVEAL)
    return Panel(
        name=f"side_{'left' if left else 'right'}", file=f"ply_side_{'left' if left else 'right'}",
        stock="3/4", box=(sx0, sx1, Y0, Y1, Z0, Z1), normal="x", up=+1 if left else -1,
        pocket_face="inside", finish_face="outside", pockets=pk, bores=bores, holes=holes,
        cutouts=[notch],
        note=f"{P.CHAMFER} × 45° chamfer on the outside face of both vertical edges, on the "
             "router table after cutting (it is on the down face). "
             + ("Partition dado, shelf pins, wet-bay vents" if left else "Console-bay vents"),
    )


def shelf_pins() -> list[tuple[float, float]]:
    """(y, z) of every pin hole: two rows, SHELF_PIN_N heights, the top one the
    design height."""
    s = shelf_box()
    ys = (s[2] + P.SHELF_PIN_INSET, s[3] - P.SHELF_PIN_INSET)
    z_top = P.SHELF_H - TA - P.SHELF_PIN_D / 2
    return [(y, z_top - k * P.SHELF_PIN_PITCH) for y in ys for k in range(P.SHELF_PIN_N)]


def shelf_box() -> Box3:
    g = P.SHELF_GAP
    return (XI0 + g, DIV_X0 - g, PART_Y1 + g, YR - g, P.SHELF_H - TA, P.SHELF_H)


def _rear() -> Panel:
    x0, x1 = XI0 - P.RABBET_D, XI1 + P.RABBET_D
    into = (YR, YR + P.RABBET_D)
    dado = (YR, YR + P.DADO_D)
    from .mast import strap_bolt_x, strap_heights

    return Panel(
        name="rear", file="ply_rear", stock="3/4", box=(x0, x1, YR, Y1, Z0, Z1),
        normal="y", up=-1, pocket_face="inside", finish_face="outside",
        pockets=[
            Pocket((x0, x1, *into, Z0, Z0 + TA + CLR), "rabbet", (TA,), "the floor"),
            Pocket((x0, x1, *dado, DECK_BOT - CLR, DECK_TOP), "dado", (TA,), "the deck"),
            Pocket((DIV_X0, DIV_X1 + CLR, *dado, Z0, Z1), "dado", (HA,), "the divider"),
        ],
        cutouts=[(OPEN_X0, OPEN_X1, YR, Y1, OPEN_Z0, OPEN_Z1)],
        marks=[Hole((x, (YR + Y1) / 2, z), P.MAST_STRAP_BOLT_DIA, "U-bolt")
               for z in strap_heights() for x in strap_bolt_x()],
        note="door opening cut out; U-bolt holes MARKED — drill them through the steel "
             "backing plates",
    )


def _floor() -> Panel:
    x0, x1 = XI0 - P.RABBET_D, XI1 + P.RABBET_D
    y0, y1 = Y0 + TA, YR + P.RABBET_D
    top = (FLOOR_TOP - P.DADO_D, FLOOR_TOP)
    c = P.MAST_NOTCH_CLEARANCE
    i, t = P.FRAME_LEG_INSET, P.FRAME_TUBE
    ring_x = (X0 + i + t / 2, X1 - i - t / 2)  # on the left and right members' centrelines
    ring_y = (Y0 + i + P.FRAME_BOLT_INSET, Y1 - i - P.FRAME_BOLT_INSET)
    return Panel(
        name="floor", file="ply_floor", stock="3/4", box=(x0, x1, y0, y1, Z0, FLOOR_TOP),
        normal="z", up=+1, pocket_face="top", finish_face="bottom",
        pockets=[
            Pocket((x0, x1, PART_Y0, PART_Y1 + CLR, *top), "dado", (HA,), "the partition"),
            Pocket((DIV_X0, DIV_X1 + CLR, y0, y1, *top), "dado", (HA,), "the divider"),
        ],
        cutouts=[(P.MAST_X - P.MAST_W / 2 - c, P.MAST_X + P.MAST_W / 2 + c,
                  P.MAST_Y - P.MAST_D / 2 - c, y1 + 0.01, Z0, FLOOR_TOP)],
        holes=[Hole((x, y, Z0), P.FRAME_BOLT_DIA, "to the frame ring")
               for x in ring_x for y in ring_y],
        note="mast notch in the back edge; four bolts down through the frame ring",
    )


def _deck() -> Panel:
    x0, x1 = XI0 - P.DADO_D, XI1 + P.DADO_D
    y0, y1 = P.FASCIA_POCKET, YR + P.DADO_D
    bot = (DECK_BOT, DECK_BOT + P.DADO_D)
    c = P.MAST_NOTCH_CLEARANCE
    from .tray import pad_centres

    return Panel(
        name="deck", file="ply_deck", stock="3/4", box=(x0, x1, y0, y1, DECK_BOT, DECK_TOP),
        normal="z", up=-1, pocket_face="bottom", finish_face="top",
        pockets=[
            Pocket((x0, x1, PART_Y0, PART_Y1 + CLR, *bot), "dado", (HA,), "the partition"),
            Pocket((DIV_X0, DIV_X1 + CLR, y0, y1, *bot), "dado", (HA,), "the divider"),
        ],
        cutouts=[(P.MAST_X - P.MAST_W / 2 - c, P.MAST_X + P.MAST_W / 2 + c,
                  P.MAST_Y - P.MAST_D / 2 - c, y1 + 0.01, DECK_BOT, DECK_TOP)],
        holes=[Hole((x, y, DECK_BOT), P.PAD_SCREW_DIA, "screw up into a pad")
               for x, y in pad_centres()],
        note="carries the block: the pads stand on it, screwed up from below. Glue the "
             "apron under its front edge. Seal it — it is under the tray's cutouts",
    )


def _apron() -> Panel:
    from .plinth import fascia_screw_points

    x0, x1 = XI0 - P.DADO_D, XI1 + P.DADO_D
    y0, y1 = P.FASCIA_POCKET, P.FASCIA_POCKET + TA
    return Panel(
        name="apron", file="ply_apron", stock="3/4", box=(x0, x1, y0, y1, APRON_Z0, DECK_BOT),
        normal="y", up=-1, finish_face="front",
        holes=[Hole((x, (y0 + y1) / 2, z), P.PILOT_DIA, "fascia top row")
               for x, z in fascia_screw_points() if z > APRON_Z0],
        note="glued under the deck's front edge; its face is the glass's backstop",
    )


def _ledge() -> Panel:
    return Panel(
        name="ledge", file="ply_ledge", stock="3/4",
        box=(XI0 - P.DADO_D, XI1 + P.DADO_D, P.FASCIA_POCKET, P.CONSOLE_Y1 - P.LEDGE_CHASE,
             LEDGE_Z0, LEDGE_Z1),
        normal="z", up=+1, finish_face="top",
        note="the case sits on it; drill the fascia's bottom row into its front edge "
             "through the fascia",
    )


def _partition() -> Panel:
    return Panel(
        name="partition", file="ply_partition", stock="1/2",
        box=(XI0 - P.DADO_D, DIV_X0 + P.HALF_RABBET_D, PART_Y0, PART_Y1,
             FLOOR_TOP - P.DADO_D, DECK_BOT + P.DADO_D),
        normal="y", up=-1, finish_face="front",
        note="a shear wall: housed in the left side, floor, deck and divider, and glued",
    )


def _divider() -> Panel:
    from .plinth import LINE_PASS_Y, LINE_PASS_Z, divider_reliefs

    y1 = YR + P.DADO_D
    z0, z1 = FLOOR_TOP - P.DADO_D, DECK_BOT + P.DADO_D
    return Panel(
        name="divider", file="ply_divider", stock="1/2", box=(DIV_X0, DIV_X1, PART_Y0, y1, z0, z1),
        normal="x", up=-1, pocket_face="wet (left)", finish_face="dry (right)",
        pockets=[Pocket((DIV_X0, DIV_X0 + P.HALF_RABBET_D, PART_Y0, PART_Y1 + CLR, z0, z1),
                        "rabbet", (HA,), "the partition's end")],
        cutouts=[(DIV_X0, DIV_X1, ry0, y1 + 0.01, rz0, rz1)
                 for ry0, _, rz0, rz1 in divider_reliefs()],
        holes=[Hole(((DIV_X0 + DIV_X1) / 2, LINE_PASS_Y, LINE_PASS_Z), P.MAST_LINE_PASS_H,
                    "line pass, grommeted")]
              + [Hole(((DIV_X0 + DIV_X1) / 2, y, z), P.SHELF_PIN_D, "shelf pin")
                 for y, z in shelf_pins()],
        note="a shear wall: housed in the floor, deck and rear, and glued. U-bolt reliefs "
             "in its back edge",
    )


def _door() -> Panel:
    g = P.DOOR_GAP
    x0, x1 = OPEN_X0 + g, OPEN_X1 - g
    z0, z1 = OPEN_Z0 + g, OPEN_Z1 - g
    return Panel(
        name="door", file="ply_door", stock="3/4", box=(x0, x1, YR, Y1, z0, z1),
        normal="y", up=-1, pocket_face="inside", finish_face="outside",
        bores=[Bore((x0 + P.HINGE_CUP_INSET, YR, z), P.HINGE_CUP_D, P.HINGE_CUP_DEPTH, "cup")
               for z in (z0 + P.HINGE_FROM_END, z1 - P.HINGE_FROM_END)],
        holes=[Hole((x1 - 1.0, (YR + Y1) / 2, (z0 + z1) / 2), P.DOOR_PULL_DIA, "finger pull")],
        note="inset, on two cup hinges plated to the left side",
        fabricated_elsewhere=True,
    )


def _front() -> Panel:
    g = P.DOOR_GAP
    bz0, _ = band()
    x0, x1 = XI0 + g, XI1 - g
    zs = (Z0 + P.FRONT_BOLT_FROM_END, bz0 - P.FRONT_BOLT_FROM_END)
    return Panel(
        name="front", file="ply_front", stock="3/4", box=(x0, x1, Y0, TA, Z0, bz0),
        normal="y", up=-1, finish_face="front",
        holes=[Hole((x, TA / 2, z), P.FRONT_BOLT_DIA, "M5 knock-down")
               for x in (XI0 + TA / 2, XI1 - TA / 2) for z in zs],
        note="removable: four M5 bolts into threaded inserts in the cleats",
    )


def _cleat(left: bool) -> Panel:
    bz0, _ = band()
    x0, x1 = (XI0, XI0 + TA) if left else (XI1 - TA, XI1)
    y0, y1 = TA, TA + P.FRONT_CLEAT_W
    xm = (x0 + x1) / 2
    return Panel(
        name=f"cleat_{'left' if left else 'right'}", file="ply_front_cleat", stock="3/4",
        box=(x0, x1, y0, y1, FLOOR_TOP, bz0), normal="x", up=+1 if left else -1,
        finish_face="none", qty=1,
        holes=[Hole((xm, (y0 + y1) / 2, z), P.CLEAT_SCREW_DIA, "screw into the side")
               for z in (FLOOR_TOP + 2.0, bz0 - 2.0)],
        note="face-glued and screwed to the side; drill the M5 insert into its front edge "
             "through the front panel's holes",
    )


def _shelf() -> Panel:
    return Panel(name="shelf", file="ply_shelf", stock="3/4", box=shelf_box(),
                 normal="z", up=+1, finish_face="top", note="loose, on four pins")


def panels() -> list[Panel]:
    return [_side(True), _side(False), _rear(), _floor(), _deck(), _apron(), _ledge(),
            _partition(), _divider(), _front(), _cleat(True), _cleat(False), _shelf(),
            _door()]


def by_name() -> dict[str, Panel]:
    return {p.name: p for p in panels()}


# ---------------------------------------------------------------------------
# The grammar, checked
# ---------------------------------------------------------------------------

def problems() -> list[str]:
    """Every grammar violation in the carcass. Empty is good."""
    out = []
    for p in panels():
        a = "xyz".index(p.normal)
        face = p.up_face()
        pocketed = bool(p.pockets or p.bores)
        if pocketed and p.pocket_face == "none":
            out.append(f"{p.name}: pockets but no declared pocket face (rule 1)")
        if pocketed and p.pocket_face == p.finish_face:
            out.append(f"{p.name}: pockets on the finished face (rule 2)")
        for pk in p.pockets:
            # Rule 1: it opens on the up face.
            lo, hi = pk.box[2 * a], pk.box[2 * a + 1]
            on_face = abs((hi if p.up > 0 else lo) - face) < 1e-6
            if not on_face:
                out.append(f"{p.name}: {pk.note} is not cut from the pocketed face (rule 1)")
            # Rule 3: measured stock plus clearance.
            want = sum(pk.mates) + CLR
            if abs(p.across(pk) - want) > 1e-6:
                out.append(f"{p.name}: {pk.note} is {p.across(pk):.4f} wide, wants {want:.4f} (rule 3)")
            # Rule 4.
            d = p.depth_of(pk)
            frac = 1 / 3 if pk.kind == "dado" else 1 / 2
            if abs(d - p.nominal_t * frac) > 1e-6:
                out.append(f"{p.name}: {pk.kind} for {pk.note} is {d:.4f} deep (rule 4)")
            # Rule 5.
            if not p.through(pk):
                out.append(f"{p.name}: {pk.note} is stopped (rule 5)")
    return out
