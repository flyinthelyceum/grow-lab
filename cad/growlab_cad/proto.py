"""P1: the first-install prototype. Two blocks, a conduit, a light.

Branched from V1 on 2026-10-27 to get an elegant working piece built and
photographed without the station's cabinet, mast, steel case and tray. The V1
design is parked, not deleted; everything here is its own module and borrows
from V1 only what is already measured or already built: the block, the sensor
case, the heatsink bars, the dials, the e-ink.

The composition, in the order the eye reads it
----------------------------------------------
* **The planter.** A CMU lying on the floor as it was made, media straight in
  its cores, in a full-size steam pan that takes the runoff. The sensor case
  sits on its top, between the plants.
* **The instrument.** A second CMU **stood on end**, a solid face shell to the
  viewer. The two Weston dials and the e-ink are **cored into that face**: two
  holes and a window, cut into the block itself, no faceplate. Stood on end,
  its cores become two horizontal tunnels behind the face, open only at the
  sides, and the whole hardware stack lives in them behind laser-cut caps.
* **The crook.** One stick of 3/4 EMT, bent with a standard hand bender: a stub
  into the instrument's lower tunnel, up its side, a back-to-back 90 over its
  top and across to the planter, and a second down to the light. Three bends,
  a stub and two back-to-backs, in one plane -- an electrician's object, and
  the LED cable's raceway. ``bend_sheet()`` is the marks.
* **The light.** A white oak beam, the two aluminium heatsink bars set flush
  into its top so they shed heat to the room exactly as they do bare, the LEDs
  recessed 1.7 in up inside it so no one standing beside it sees a die. Its
  +X end is the camera's bay, tilted at the plants.
* **The telescope.** The drop's straight is long, and a 1/2 EMT inner tube
  carrying the beam slides inside it: 12 in of travel, 12 to 24 in over the
  media. A 3/4 set-screw coupling on the drop's end locks it through a slot in
  a printed sleeve; a printed bushing on the inner tube's top is the second
  guide. The 1/2 lands in the beam's printed hub through a set-screw connector.
* **The ground plate.** 1/4 steel under both blocks, set back from every
  visible edge. Without it the crook tips the instrument over at under two
  pounds of side load; with it the light hangs over the plate's own footprint
  and the planter's wet weight holds it down. ``stability()`` is the sum.

Coordinates: inches, the floor at z = 0, +X to the viewer's right, +Y away
from the viewer -- V1's frame, with its own origin at the planter's centre.

Every number that is a guess says so. The block, the pan, the bender and the
conduit are ESTIMATES until calipered; the coring is the one step that cannot
be undone, so it waits for the block in hand to be measured.
"""

from __future__ import annotations

import math

from components import lm301h_heatsink_module as HS
from components import weston_301
from pi.dashboard.panel_geometry import WINDOW_HEIGHT, WINDOW_WIDTH

from . import params as P

# ---------------------------------------------------------------------------
# Parameters. Prototype-only; V1's live in params.py and are not touched.
# ---------------------------------------------------------------------------

# The block, as params.py has it (both blocks are the same stretcher).
CMU_L, CMU_W, CMU_H = P.CMU_L, P.CMU_W, P.CMU_H
FACE_SHELL, END_SHELL, WEB = P.CMU_FACE_SHELL, P.CMU_END_SHELL, P.CMU_WEB
CMU_WEIGHT = 35.0  # ESTIMATE: lb, a normal-weight 8x8x16 stretcher -- weigh one

# The ground plate.
PLATE_T = 0.25  # CHOICE: 1/4 steel, plasma
PLATE_SETBACK = 0.5  # CHOICE: inside every visible edge, so it reads as a shadow
PLATE_BRIDGE_W = 3.0  # CHOICE: the strip that joins the two footprints
GAP = 1.5  # CHOICE: steam pan rim to the instrument block

# The pan: a full-size 2-1/2 in steam table pan, bought.
PAN_TOP_L, PAN_TOP_W = 20.75, 12.75  # ESTIMATE: over the rolled rim -- measure
PAN_BOTTOM_L, PAN_BOTTOM_W = 19.5, 11.5  # ESTIMATE: the flat of the floor -- measure
PAN_DEPTH = 2.5  # ESTIMATE: sold as 2-1/2 in
PAD_H = 0.5  # CHOICE: four printed pads lift the block clear of its own runoff
PAD_SIZE = 1.5  # CHOICE

# The crook: 3/4 EMT and the hand bender it is bent with.
EMT_OD = 0.92  # ESTIMATE: caliper the stick
TAKE_UP = 6.0  # ESTIMATE: read it off the bender's shoe; 3/4 EMT shoes are stamped 6
STICK = 120.0  # CHOICE: one 10 ft stick
STUB_BACK = 7.0  # CHOICE: the leg into the lower tunnel, end to back of bend.
                 # A hand bender cannot make a stub shorter than its take-up
STANDOFF = 0.25  # CHOICE: the riser rides on clamp backs, off the block's side. It
                 # is also what keeps the first bend's arc clear of the web's edge
                 # where it sweeps out of the lower tunnel
CRAWL = 0.6  # CHOICE: the crook's plane, in from the tunnel's back wall, so the
             # stub lies along the back of the lower tunnel out of the hardware's way

# The light.
# The light's height: a telescope at the end of the drop. A 1/2 EMT inner tube
# carries the beam and slides inside the 3/4 drop; a 3/4 set-screw coupling on
# the drop's end locks it, through a slot in a printed sleeve that centres the
# 1/2 in the coupling's free half. Loosen, slide, tighten.
GAP_MIN = 12.0  # CHOICE: V1's closest useful working distance, for seedlings
GAP_MAX = 24.0  # CHOICE: a grown ranunculus, about 18 in, with 6 to spare
DRAWN_GAP = GAP_MIN  # CHOICE: where the model and the renders hang it
INNER_OD = 0.706  # ESTIMATE: 1/2 EMT -- caliper it
INNER_ID = 0.622  # ESTIMATE: 1/2 EMT's bore; every cable to the beam goes through it
EMT_ID = 0.824  # ESTIMATE: 3/4 EMT's bore
COUPLING_L = 1.75  # ESTIMATE: a 3/4 set-screw coupling, end to end
COUPLING_OD = 1.1  # ESTIMATE
HALF_STOP = 0.5  # ESTIMATE: hub top to the stop in a 1/2 set-screw connector
OVERLAP_MIN = 2.5  # CHOICE: inner tube inside the drop proper, at the lowest light
SHOW_MIN = 1.0  # CHOICE: hub top to coupling, at the highest light
TANGENT_CLEAR = 0.25  # CHOICE: the inner tube stops short of the last bend
SLEEVE_LIP = 0.125  # CHOICE: the printed sleeve's stop, under the coupling
SLEEVE_SLOT = 0.3  # CHOICE: the window the set screw bears through
BUSHING_L = 1.0  # CHOICE: printed, on the inner tube's top end -- the second guide
MICRO_HDMI = (0.44, 0.27)  # ESTIMATE: the micro-HDMI plug's overmold, w x t -- measure
BEAM_END = 2.25  # CHOICE: oak beyond the bars at each end; the +X end is the camera bay
BEAM_RAIL = 0.625  # CHOICE: oak beside the bars
BEAM_SPINE = 0.5  # CHOICE: oak between the two bars, full height -- two channels of light.
                  # 1/2 so the camera cable's groove in its top keeps 1/8 walls
BEAM_H = 2.25  # CHOICE: the bars' 0.525 plus 1.725 of regress below them
BAR_CLEAR = 0.02  # CHOICE: a side, bar in its pocket
LEDGE = 0.125  # CHOICE: oak the bar rests on, all round, outside the LED board
HUB_L = 2.75  # CHOICE: printed PETG, along the beam
HUB_H = 0.875  # CHOICE: tall enough for the connector's locknut inside it
WIRE_HOLE = 0.25  # CHOICE: through the spine under the hub, leads to the boards
KNOCKOUT = 0.875  # ESTIMATE: the trade knockout for 1/2 conduit -- check the connector

# The camera: Camera Module 3, in a bay in the beam's +X end block, tilted
# toward the plants, its cable in a groove along the top of the spine to the hub
# and down the telescope as a micro-HDMI pull (a standard HDMI plug will not
# pass a 1/2 EMT bore; the micro end is the one pulled, then adapted).
CAM_BAY = (1.5, 1.5)  # CHOICE: x by y, blind from the top
CAM_FLOOR = 0.25  # CHOICE: oak left under the bay
CAM_LENS = 0.75  # CHOICE: the window through the floor
CAM_LID = 0.125  # CHOICE: a printed lid, flush in a rebate round the bay
CAM_TILT = 30.0  # CHOICE: degrees off straight down, toward the plants
CAM_HFOV = 66.0  # ESTIMATE: Camera Module 3 standard, horizontal -- the wide is 102
GROOVE = 0.25  # CHOICE: width and depth, in the spine's top

# The face of the instrument block.
DIAL_GAP = 0.125  # CHOICE: between the two dial flanges
DIAL_FLANGE = weston_301.FLANGE_OD  # LIB: 3.51, calipered 2026-10-27
DIAL_HOLE = P.DIAL_CUT_DIAMETER  # LIB: what passes the body, 2.75
WINDOW_W, WINDOW_H = WINDOW_WIDTH, WINDOW_HEIGHT  # the plate's: the Inky's active area
WINDOW_CORNER = 0.25  # CHOICE: a 1/2 in masonry bit at each corner first, so the
                      # window has round inside corners and no grinder overcut
MIN_LIGAMENT = 0.5  # CHOICE: concrete left between a cut and a free edge
INKY_BOARD = (6.85, 4.84)  # ESTIMATE: 174 x 123 mm as published -- measure

# Densities, for the stability sum only.
OAK = 0.027  # ESTIMATE: lb/in3, white oak
ALUMINIUM = 0.0975  # ESTIMATE: lb/in3
EMT_LB_PER_IN = 0.035  # ESTIMATE: 3/4 EMT, about 0.42 lb/ft
HUB_AND_HARDWARE = 0.5  # ESTIMATE: lb, hub, connector, locknut, leads


# ---------------------------------------------------------------------------
# Where things are. Arithmetic only -- the tests run it without a kernel.
# ---------------------------------------------------------------------------

def plate_top() -> float:
    return PLATE_T


def planter_box() -> tuple[float, float, float, float, float, float]:
    """The planter block: lying as made, cores up, on its pads in the pan."""
    y0 = crook_y() - CMU_W / 2
    z0 = plate_top() + PAD_H
    return (-CMU_L / 2, CMU_L / 2, y0, y0 + CMU_W, z0, z0 + CMU_H)


def media_top() -> float:
    return planter_box()[5]


def pan_box() -> tuple[float, float, float, float, float, float]:
    cy = crook_y()
    return (-PAN_TOP_L / 2, PAN_TOP_L / 2, cy - PAN_TOP_W / 2, cy + PAN_TOP_W / 2,
            plate_top(), plate_top() + PAN_DEPTH)


def instrument_box() -> tuple[float, float, float, float, float, float]:
    """The instrument block, stood on end, front face flush with y = 0."""
    x0 = PAN_TOP_L / 2 + GAP
    return (x0, x0 + CMU_W, 0.0, CMU_W, plate_top(), plate_top() + CMU_L)


def tunnels() -> dict[str, tuple[float, float]]:
    """z extents of the instrument block's two cores, now horizontal tunnels
    running left to right behind the face, open at both sides."""
    z0 = instrument_box()[4]
    core = (CMU_L - 2 * END_SHELL - WEB) / 2
    lo = (z0 + END_SHELL, z0 + END_SHELL + core)
    hi = (lo[1] + WEB, lo[1] + WEB + core)
    return {"lower": lo, "upper": hi}


def tunnel_y() -> tuple[float, float]:
    """Front to back inside a tunnel: between the two face shells."""
    return FACE_SHELL, CMU_W - FACE_SHELL


def crook_y() -> float:
    """The plane the whole crook is bent in. Near the back of the tunnels, so
    the stub lies along the lower tunnel's back wall; the planter is centred on
    it, so the drop lands over the planter's middle."""
    return tunnel_y()[1] - CRAWL


def dial_centres() -> list[tuple[float, float]]:
    """(x, z) of the two dial holes, side by side across the upper tunnel."""
    x0, x1, *_ = instrument_box()
    cx = (x0 + x1) / 2
    zc = sum(tunnels()["upper"]) / 2
    dx = DIAL_FLANGE / 2 + DIAL_GAP / 2
    return [(cx - dx, zc), (cx + dx, zc)]


def window_rect() -> tuple[float, float, float, float]:
    """(x0, x1, z0, z1) of the e-ink window, centred on the lower tunnel."""
    x0, x1, *_ = instrument_box()
    cx = (x0 + x1) / 2
    zc = sum(tunnels()["lower"]) / 2
    return cx - WINDOW_W / 2, cx + WINDOW_W / 2, zc - WINDOW_H / 2, zc + WINDOW_H / 2


# ---------------------------------------------------------------------------
# The crook, as a centreline and as the marks a bender makes it from.
# ---------------------------------------------------------------------------

def bend_radius() -> float:
    """Centreline radius, from the take-up the bender is stamped with: a stub's
    take-up is the arrow to the back of the bend, which is the radius plus
    half the pipe."""
    return TAKE_UP - EMT_OD / 2


def beam_box(gap: float = DRAWN_GAP) -> tuple[float, float, float, float, float, float]:
    l = HS.LENGTH + 2 * BAR_CLEAR + 2 * BEAM_END
    w = beam_width()
    z0 = media_top() + gap
    cy = crook_y()
    return (-l / 2, l / 2, cy - w / 2, cy + w / 2, z0, z0 + BEAM_H)


def beam_width() -> float:
    return 2 * (HS.WIDTH + 2 * BAR_CLEAR) + BEAM_SPINE + 2 * BEAM_RAIL


def hub_top(gap: float = DRAWN_GAP) -> float:
    return beam_box(gap)[5] + HUB_H


def coupling_bottom() -> float:
    """Fixed on the drop's end: set by the highest light, plus a little tube."""
    return hub_top(GAP_MAX) + SHOW_MIN


def inner_tube(gap: float = DRAWN_GAP) -> tuple[float, float]:
    """(z_bottom, z_top) of the 1/2 inner tube with the light at ``gap``.

    Its length is what keeps OVERLAP_MIN inside the drop at the lowest light,
    and its top short of the bend at the highest.
    """
    z_tip = coupling_bottom() + COUPLING_L / 2  # the 3/4 drop's end
    length = (z_tip + OVERLAP_MIN) - (hub_top(GAP_MIN) + HALF_STOP)
    z0 = hub_top(gap) + HALF_STOP
    return z0, z0 + length


def travel() -> float:
    return GAP_MAX - GAP_MIN


def crook_points() -> dict[str, tuple[float, float]]:
    """The centreline corners, (x, z) in the crook's plane, and its two ends.

    end   -- inside the lower tunnel, the stub's end
    p1    -- stub meets riser, against the block's +X side
    p2    -- riser meets run, over the block's top
    p3    -- run meets drop, over the planter's centre
    tip   -- the drop's end, at the stop inside the telescope's coupling

    The drop's straight is the telescope's: the inner tube at the highest
    light has to fit inside it, short of the bend, which is what sets how high
    the run goes.
    """
    d = EMT_OD
    x_r = instrument_box()[1] + STANDOFF + d / 2  # on clamp backs, under its straps
    z_low = tunnels()["lower"][0] + d / 2  # the stub lies on the tunnel floor
    x_end = x_r + d / 2 - STUB_BACK
    z_tip = coupling_bottom() + COUPLING_L / 2
    z_tangent = inner_tube(GAP_MAX)[1] + TANGENT_CLEAR
    z_run = z_tangent + bend_radius()
    return {"end": (x_end, z_low), "p1": (x_r, z_low), "p2": (x_r, z_run),
            "p3": (0.0, z_run), "tip": (0.0, z_tip)}


def developed_length() -> float:
    """Pipe used: the straights between tangent points plus three quarter arcs."""
    r = bend_radius()
    c = crook_points()
    stub = c["p1"][0] - c["end"][0] - r
    riser = c["p2"][1] - c["p1"][1] - 2 * r
    run = c["p2"][0] - c["p3"][0] - 2 * r
    drop = c["p3"][1] - c["tip"][1] - r
    return stub + riser + run + drop + 3 * math.pi * r / 2


def bend_sheet() -> list[dict]:
    """The marks, the way a hand bender takes them. Every distance is to the
    BACK of a bend -- the outside of the pipe -- which is what a tape reads.

    1. Stub: from the end, mark STUB_BACK less the take-up, arrow on the mark.
    2. Back-to-back: from the back of bend 1, the outer height to the top of
       the run; star (back-of-bend) mark on it, same plane, same direction.
    3. Back-to-back: from the back of bend 2 (the riser's outside), the outer
       length to the drop's far side; star on the mark.
    4. Cut: from the back of bend 3 (the top of the run), the drop.
    """
    d = EMT_OD
    c = crook_points()
    rise_back = c["p2"][1] - c["p1"][1] + d  # bottom of stub to top of run
    run_back = c["p2"][0] - c["p3"][0] + d  # outside of riser to outside of drop
    drop_back = c["p2"][1] + d / 2 - c["tip"][1]
    return [
        {"step": 1, "bend": "90° stub", "from": "the end",
         "mark": STUB_BACK - TAKE_UP, "use": "arrow", "back_of_bend": STUB_BACK},
        {"step": 2, "bend": "90° back-to-back", "from": "back of bend 1 (underside of the stub)",
         "mark": rise_back, "use": "star", "back_of_bend": rise_back},
        {"step": 3, "bend": "90° back-to-back", "from": "back of bend 2 (outside of the riser)",
         "mark": run_back, "use": "star", "back_of_bend": run_back},
        {"step": 4, "bend": "cut", "from": "back of bend 3 (top of the run)",
         "mark": drop_back, "use": "hacksaw, ream", "back_of_bend": drop_back},
        {"step": 5, "bend": "cut 1/2 EMT", "from": "end to end, the inner tube",
         "mark": inner_tube()[1] - inner_tube()[0], "use": "hacksaw, ream both ends",
         "back_of_bend": inner_tube()[1] - inner_tube()[0]},
    ]


def stub_exit() -> tuple[float, float]:
    """(z_bottom, z_top) where the stub's bend crosses the plane of the block's
    +X side, which is where the lower right cap is notched.

    The first bend is a quarter circle of the bender's radius, centred inside
    the tunnel; at this radius it does not leave along the floor but sweeps up
    and out through the opening, so the notch is where the arc says, not where
    the stub lies.
    """
    r, d = bend_radius(), EMT_OD
    c = crook_points()
    xc, zc = c["p1"][0] - r, c["p1"][1] + r  # the arc's centre
    dx = instrument_box()[1] - xc

    def z_at(radius: float) -> float:
        return zc - math.sqrt(max(radius ** 2 - dx ** 2, 0.0))

    return z_at(r + d / 2), z_at(r - d / 2) if dx < r - d / 2 else zc


def total_bend() -> float:
    """Degrees between pull points. NEC 358.26 allows 360; three 90s is 270."""
    return 270.0


# ---------------------------------------------------------------------------
# Will it stand.
# ---------------------------------------------------------------------------

def light_weight() -> float:
    """The beam, bars and hub, in pounds."""
    x0, x1, y0, y1, z0, z1 = beam_box()
    hl, hw, hh = HS.LENGTH, HS.WIDTH, HS.HEIGHT
    oak = (x1 - x0) * (y1 - y0) * (z1 - z0) - 2 * (hl * hw * (z1 - z0))  # bars' channels
    return oak * OAK + 2 * hl * hw * hh * ALUMINIUM + HUB_AND_HARDWARE


def stability() -> dict[str, float]:
    """Tipping of the instrument block about its edge nearest the planter.

    Free-standing, the light's moment against the block's weight. On the plate
    the block is bolted down and the light hangs inside the plate's footprint,
    so what tips would be the whole plate -- planter, pan and all -- and its
    pivot is outside everything that hangs off the crook.
    """
    c = crook_points()
    xi0 = instrument_box()[0]
    run = c["p2"][0] - c["p3"][0]
    tipping = light_weight() * (xi0 - c["p3"][0]) + run * EMT_LB_PER_IN * (xi0 - (c["p2"][0] + c["p3"][0]) / 2)
    resisting = CMU_WEIGHT * CMU_W / 2
    # Horizontal shove at the beam's height that tips it, free-standing.
    shove = (resisting - tipping) / (beam_box()[4] - plate_top())
    return {"tipping": tipping, "resisting": resisting, "factor": resisting / tipping,
            "shove_lb": shove}


# ---------------------------------------------------------------------------
# Geometry. The kernel is imported here and not above, so the layout and the
# bend sheet test anywhere.
# ---------------------------------------------------------------------------

def _wbox(b):
    from ._shapes import MIN, box

    x0, x1, y0, y1, z0, z1 = b
    return box(x1 - x0, y1 - y0, z1 - z0, at=(x0, y0, z0), align=MIN)


def build_planter():
    """Reference: the block as bought, cores open, on its pads."""
    from ._shapes import labelled

    b = planter_box()
    block = _wbox(b)
    core_l = (CMU_L - 2 * END_SHELL - WEB) / 2
    for sx in (-1, 1):
        cx = sx * (WEB / 2 + core_l / 2)
        block -= _wbox((cx - core_l / 2, cx + core_l / 2, b[2] + FACE_SHELL, b[3] - FACE_SHELL,
                        b[4] - 0.1, b[5] + 0.1))
    return labelled(block, "p1_planter")


def build_media():
    """Coir to the block's top, in both cores. Reference."""
    from ._shapes import labelled

    b = planter_box()
    core_l = (CMU_L - 2 * END_SHELL - WEB) / 2
    media = None
    for sx in (-1, 1):
        cx = sx * (WEB / 2 + core_l / 2)
        m = _wbox((cx - core_l / 2, cx + core_l / 2, b[2] + FACE_SHELL, b[3] - FACE_SHELL,
                   b[4], b[5] - 0.25))
        media = m if media is None else media + m
    return labelled(media, "p1_media")


def build_pan():
    """Reference: the steam pan, as an open tray on its floor dimensions."""
    from ._shapes import labelled

    b = pan_box()
    pan = _wbox(b) - _wbox((b[0] + 0.05, b[1] - 0.05, b[2] + 0.05, b[3] - 0.05,
                            b[4] + 0.05, b[5] + 0.1))
    return labelled(pan, "p1_pan")


def build_pads():
    """Four printed pads under the planter's corners, where it is solid."""
    from ._shapes import labelled

    x0, x1, y0, y1, z0, _ = planter_box()
    out = None
    for x in (x0 + END_SHELL / 2, x1 - END_SHELL / 2):
        for y in (y0 + FACE_SHELL / 2, y1 - FACE_SHELL / 2):
            p = _wbox((x - PAD_SIZE / 2, x + PAD_SIZE / 2, y - PAD_SIZE / 2, y + PAD_SIZE / 2,
                       plate_top() + 0.05, z0))
            out = p if out is None else out + p
    return labelled(out, "p1_pads")


def build_instrument():
    """The instrument block, stood on end: its tunnels, the two dial holes and
    the e-ink window cut through its front face shell."""
    from ._shapes import cyl_y, labelled

    b = instrument_box()
    block = _wbox(b)
    y0, y1 = tunnel_y()
    for z0, z1 in tunnels().values():
        block -= _wbox((b[0] - 0.1, b[1] + 0.1, y0, y1, z0, z1))
    for x, z in dial_centres():
        block -= cyl_y(DIAL_HOLE, FACE_SHELL * 3, at=(x, 0.0, z))
    wx0, wx1, wz0, wz1 = window_rect()
    block -= _wbox((wx0, wx1, -0.1, FACE_SHELL + 0.1, wz0, wz1))
    return labelled(block, "p1_instrument")


def build_plate():
    """The ground plate: both footprints set back, and a bridge between."""
    from ._shapes import labelled

    s = PLATE_SETBACK
    cy = crook_y()
    pan = (-PAN_BOTTOM_L / 2 + s, PAN_BOTTOM_L / 2 - s, cy - PAN_BOTTOM_W / 2 + s,
           cy + PAN_BOTTOM_W / 2 - s)
    ib = instrument_box()
    inst = (ib[0] + s, ib[1] - s, ib[2] + s, ib[3] - s)
    bridge = (pan[1] - 0.5, inst[0] + 0.5, cy - PLATE_BRIDGE_W / 2, cy + PLATE_BRIDGE_W / 2)
    plate = None
    for r in (pan, inst, bridge):
        part = _wbox((*r, 0.0, PLATE_T))
        plate = part if plate is None else plate + part
    return labelled(plate, "p1_plate")


def plate_outline() -> list[tuple[float, float, float, float]]:
    """The plate's three rectangles, (x0, x1, y0, y1), for the DXF."""
    s = PLATE_SETBACK
    cy = crook_y()
    pan = (-PAN_BOTTOM_L / 2 + s, PAN_BOTTOM_L / 2 - s, cy - PAN_BOTTOM_W / 2 + s,
           cy + PAN_BOTTOM_W / 2 - s)
    ib = instrument_box()
    inst = (ib[0] + s, ib[1] - s, ib[2] + s, ib[3] - s)
    bridge = (pan[1] - 0.5, inst[0] + 0.5, cy - PLATE_BRIDGE_W / 2, cy + PLATE_BRIDGE_W / 2)
    return [pan, inst, bridge]


def plate_bolt() -> tuple[float, float]:
    """One 3/8 flat-head up through the plate and the block's bottom end shell,
    nut and fender washer inside the lower tunnel, clear of the stub."""
    x0, x1, *_ = instrument_box()
    return (x0 + x1) / 2, tunnel_y()[0] + 1.25


def build_crook():
    """The bent stick: its corners filleted at the bender's radius, which is
    exactly what a hand bender does to a straight line, then swept."""
    from build123d import Circle, FilletPolyline, Plane, sweep

    from ._shapes import labelled
    from .params import IN

    c = crook_points()
    y = crook_y()
    pts = [(c[k][0] * IN, y * IN, c[k][1] * IN) for k in ("end", "p1", "p2", "p3", "tip")]
    path = FilletPolyline(*pts, radius=bend_radius() * IN)
    start = Plane(origin=pts[0], z_dir=(1, 0, 0))
    outer = sweep(start * Circle(EMT_OD / 2 * IN), path=path)
    bore = sweep(start * Circle((EMT_OD / 2 - 0.05) * IN), path=path)
    return labelled(outer - bore, "p1_crook")


def build_beam():
    """The oak beam: two bar pockets in the top, two light channels below
    them, a spine between, a wire hole through the spine under the hub."""
    from ._shapes import cyl_z, labelled

    b = beam_box()
    beam = _wbox(b)
    hl, hw, hh = HS.LENGTH, HS.WIDTH, HS.HEIGHT
    cy = crook_y()
    for s in (-1, 1):
        ycen = cy + s * (BEAM_SPINE / 2 + hw / 2 + BAR_CLEAR)
        pw, pl = hw + 2 * BAR_CLEAR, hl + 2 * BAR_CLEAR
        # The bar's pocket, from the top, its own depth.
        beam -= _wbox((-pl / 2, pl / 2, ycen - pw / 2, ycen + pw / 2, b[5] - hh, b[5] + 0.1))
        # The channel below it, inside the ledge, out through the bottom.
        beam -= _wbox((-pl / 2 + LEDGE, pl / 2 - LEDGE, ycen - pw / 2 + LEDGE, ycen + pw / 2 - LEDGE,
                       b[4] - 0.1, b[5] - hh + 0.001))
    beam -= cyl_z(WIRE_HOLE, BEAM_H + 0.2, at=(0.0, cy, b[4] - 0.1))
    # The camera bay in the +X end, its lid's rebate, the lens window through
    # its floor, and the cable's groove in the spine's top back to the hub.
    bx0, bx1, by0, by1 = cam_bay()
    beam -= _wbox((bx0, bx1, by0, by1, b[4] + CAM_FLOOR, b[5] + 0.1))
    beam -= _wbox((bx0 - CAM_LID, bx1 + CAM_LID, by0 - CAM_LID, by1 + CAM_LID,
                   b[5] - CAM_LID, b[5] + 0.1))
    beam -= cyl_z(CAM_LENS, CAM_FLOOR + 0.2, at=((bx0 + bx1) / 2, cy, b[4] - 0.1))
    beam -= _wbox((-HUB_L / 2 + 0.25, bx0 + 0.01, cy - GROOVE / 2, cy + GROOVE / 2,
                   b[5] - GROOVE, b[5] + 0.1))
    return labelled(beam, "p1_beam")


def cam_bay() -> tuple[float, float, float, float]:
    """(x0, x1, y0, y1) of the camera bay, in the +X end block."""
    b = beam_box()
    x0 = HS.LENGTH / 2 + BAR_CLEAR + (BEAM_END - CAM_BAY[0]) / 2
    cy = crook_y()
    return x0, x0 + CAM_BAY[0], cy - CAM_BAY[1] / 2, cy + CAM_BAY[1] / 2


def camera_sees(gap: float) -> tuple[float, float]:
    """The planter's far and near ends, as angles off the camera's tilted
    axis, in degrees, at ``gap``. Both inside half the field of view means it
    frames both plants."""
    bx0, bx1, *_ = cam_bay()
    xc = (bx0 + bx1) / 2
    h = beam_box(gap)[4] + CAM_FLOOR - media_top()
    x0, x1, *_ = planter_box()
    far = math.degrees(math.atan2(xc - x0, h))
    near = math.degrees(math.atan2(xc - x1, h))
    return far - CAM_TILT, near - CAM_TILT


def build_bars():
    """Reference: the two heatsink bars as calipered, flush in the beam's top."""
    from ._shapes import labelled

    b = beam_box()
    hl, hw, hh = HS.LENGTH, HS.WIDTH, HS.HEIGHT
    cy = crook_y()
    out = None
    for s in (-1, 1):
        ycen = cy + s * (BEAM_SPINE / 2 + hw / 2 + BAR_CLEAR)
        bar = _wbox((-hl / 2, hl / 2, ycen - hw / 2, ycen + hw / 2, b[5] - hh, b[5]))
        out = bar if out is None else out + bar
    return labelled(out, "p1_bars")


def build_hub():
    """Printed PETG, matte white like the sensor case: a bridge over the
    bars at mid-length, screwed to the rails, hollow underneath for the
    connector's locknut, with the 3/4 EMT connector's knockout in its top."""
    from ._shapes import cyl_z, labelled

    b = beam_box()
    cy = crook_y()
    hub = _wbox((-HUB_L / 2, HUB_L / 2, b[2], b[3], b[5], b[5] + HUB_H))
    hub -= _wbox((-HUB_L / 2 + 0.25, HUB_L / 2 - 0.25, b[2] + BEAM_RAIL, b[3] - BEAM_RAIL,
                  b[5] - 0.1, b[5] + HUB_H - 0.1875))
    hub -= cyl_z(KNOCKOUT, 1.0, at=(0.0, cy, b[5] + HUB_H - 0.5))
    # The camera cable's groove carries on under the hub's end wall.
    hub -= _wbox((HUB_L / 2 - 0.3, HUB_L / 2 + 0.1, cy - GROOVE / 2, cy + GROOVE / 2,
                  b[5] - 0.1, b[5] + 0.0625))
    for x, y in hub_screws():
        hub -= cyl_z(HUB_SCREW, HUB_H + 0.2, at=(x, y, b[5] - 0.1))
    return labelled(hub, "p1_hub")


HUB_SCREW = 0.15  # CHOICE: #6 clearance, through the hub into the rails


def hub_screws() -> list[tuple[float, float]]:
    """(x, y) of the hub's four screws: down through its solid ends into the
    middle of the oak rails, clear of the bars."""
    b = beam_box()
    dx = HUB_L / 2 - 0.375
    return [(sx * dx, y) for sx in (-1, 1)
            for y in (b[2] + BEAM_RAIL / 2, b[3] - BEAM_RAIL / 2)]


def _tube(od: float, idia: float, z0: float, z1: float, x: float = 0.0):
    from ._shapes import cyl_z

    y = crook_y()
    return cyl_z(od, z1 - z0, at=(x, y, z0)) - cyl_z(idia, z1 - z0 + 0.2, at=(x, y, z0 - 0.1))


def build_inner():
    """The 1/2 EMT inner tube, at the drawn height."""
    from ._shapes import labelled

    z0, z1 = inner_tube()
    return labelled(_tube(INNER_OD, INNER_ID, z0, z1), "p1_inner_tube")


def build_coupling():
    """Reference: the 3/4 set-screw coupling on the drop's end."""
    from ._shapes import labelled

    zc = coupling_bottom()
    return labelled(_tube(COUPLING_OD, EMT_OD + 0.005, zc, zc + COUPLING_L), "p1_coupling")


def build_sleeve():
    """Printed: centres the 1/2 tube in the coupling's free half, a lip under
    it for a stop, and a slot for the coupling's set screw to bear through."""
    from ._shapes import labelled

    zc = coupling_bottom()
    y = crook_y()
    sleeve = _tube(EMT_OD - 0.01, INNER_OD + 0.02, zc, zc + COUPLING_L / 2 - 0.05)
    sleeve += _tube(COUPLING_OD, INNER_OD + 0.02, zc - SLEEVE_LIP, zc)
    sleeve -= _wbox((-SLEEVE_SLOT / 2, SLEEVE_SLOT / 2, y, y + EMT_OD,
                     zc + 0.15, zc + COUPLING_L / 2 - 0.15))
    return labelled(sleeve, "p1_sleeve")


def build_bushing():
    """Printed: on the inner tube's top end, a slide fit in the 3/4 bore --
    the telescope's second guide, so it cannot rack."""
    from ._shapes import labelled

    z1 = inner_tube()[1]
    return labelled(_tube(EMT_ID - 0.02, INNER_OD, z1 - BUSHING_L, z1), "p1_bushing")


def build_lid():
    """Printed: the camera bay's lid, flush in its rebate."""
    from ._shapes import labelled

    b = beam_box()
    bx0, bx1, by0, by1 = cam_bay()
    c = 0.01
    return labelled(_wbox((bx0 - CAM_LID + c, bx1 + CAM_LID - c, by0 - CAM_LID + c,
                           by1 + CAM_LID - c, b[5] - CAM_LID, b[5])), "p1_cam_lid")


def build() -> dict:
    """Every P1 part, in place: fabricated first, then reference."""
    return {
        "plate": build_plate(), "instrument": build_instrument(), "crook": build_crook(),
        "beam": build_beam(), "hub": build_hub(), "pads": build_pads(),
        "inner": build_inner(), "sleeve": build_sleeve(), "bushing": build_bushing(),
        "lid": build_lid(),
        "planter": build_planter(), "media": build_media(), "pan": build_pan(),
        "bars": build_bars(), "coupling": build_coupling(),
    }
