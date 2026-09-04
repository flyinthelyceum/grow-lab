"""Every dimension of the V1 station, as data.

This is the physical sibling of ``pi/dashboard/panel_geometry.py``: one place
the numbers live, so the CAD, the emulator, and the fabrication docs cannot
drift apart. Everything downstream (``plinth.py``, ``mast.py``, ``face.py`` …)
reads from here and computes nothing of its own.

The layout (decided 2026-09-04, superseding the mast-and-head scheme)
---------------------------------------------------------------------
The instrument panel is in the **front face of the cabinet**, not in a head on
top of the mast. Behind the face, a shallow dry **console bay** runs the full
width; behind that, the **reservoir** in the wet bay and the **mast** in the
dry bay, side by side. Access is from the **rear**: a door behind the wet bay
for the reservoir, and the mast bolts to the fixed rear panel behind the dry
bay. The cabinet is as tall as that stack needs. The mast is the 2 × 3 hollow
section as drawn, carrying only the LED fixture, the drip line and the LED
cable — the sensor loom never leaves the cabinet.

Why it is arranged this way
~~~~~~~~~~~~~~~~~~~~~~~~~~~
* **Depth.** The reservoir pan and the mast no longer share an X, so the old
  conflict (pan 10.4 + mast 3.0 in a 14 in cabinet) is gone. The cabinet is
  16 in deep because the console bay needs 3 in clear in front of the pan.
* **Lift.** With the pan *behind* the console rather than under it, the
  reservoir shelf can rise almost to the top rail. Static lift falls from the
  docs' 17 in to ~13 in, on the same pump. Putting the pan under a console
  deck instead would have pushed the lift to ~28 in — "fragile, avoid" on the
  SICCE's curve — so that arrangement was not built.
* **Access.** A steam-table pan slides out of a rear door at working height
  rather than a stoop. The mast sits in the dry bay so the door is clear.

Conventions
-----------
* **Inches.** Every document for this build is in inches and so is this file.
  build123d's kernel works in millimetres, so geometry code multiplies by
  ``IN`` at construction. Tests assert in inches.
* **Origin** is on the floor, at the centre of the plinth's width, on the
  plinth's front face. ``+X`` is the viewer's right, ``+Y`` runs from the front
  face toward the back, ``+Z`` is up.
* **Provenance.** Each value carries the document and section it came from.
  Values that appear in no document are marked ``CHOICE`` — design decisions
  made here to produce a buildable model; the person finishing this in Fusion
  should treat them as proposals, not canon.

Two things are deliberately *not* asserted:

* **The dial cut diameter.** The Weston 301 bezels are pending calipers; the
  drawings' Ø 2.79 is a Simpson figure that does not apply. ``face.py``
  engraves a witness circle at the bezel OD unless a measured cut is supplied.
* **The LED fixture.** Two LM301H boards on a heatsink, cantilevered forward of
  the mast. No dimensions exist for the heatsink; the fixture here is an
  envelope so the assembly reads correctly, not a part to fabricate.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

from pi.dashboard.panel_geometry import FACE_HEIGHT, FACE_WIDTH

IN = 25.4  # millimetres per inch — the only unit conversion in the package


def _knob(name: str, default: float) -> float:
    """A parameter that a sweep may override from the environment.

    ``GROWLAB_PLINTH_H=40 python cad/build.py`` builds the station four inches
    taller without editing this file. Only the knobs that are genuinely open
    decisions are exposed this way; everything else is a number with a
    provenance. The value in the file is the design as documented.
    """
    var = f"GROWLAB_{name}"
    raw = os.environ.get(var)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{var}={raw!r} is not a number (inches expected, e.g. {var}={default:g})") from None


def _flag(name: str, default: bool = False) -> bool:
    """A yes/no design candidate, switchable from the environment the same way."""
    var = f"GROWLAB_{name}"
    raw = os.environ.get(var)
    if not raw:
        return default
    if raw.lower() in ("1", "true", "yes", "on"):
        return True
    if raw.lower() in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"{var}={raw!r} is not a yes/no (use 1 or 0)")


# ---------------------------------------------------------------------------
# Form (design pass, 2026-09-04)
# Decided: height 36; the clear fascia over a black instrument case (the
# apparatus on show behind glass, cabling included, the way the Transparent
# speaker shows its amplifier); and the steel base frame the cabinet floats
# on, whose members continue into the mast. Both flags default on and both
# can be turned off — GROWLAB_FASCIA=0, GROWLAB_FRAME=0 — to rebuild the
# earlier forms for the record.
# ---------------------------------------------------------------------------

FASCIA = _flag("FASCIA", True)  # decided. A full-width clear band recessed into the
                                # front over an open console bay; the instrument
                                # case behind it; the four vertical corners
                                # chamfered so the sides read as planes meeting.
FRAME = _flag("FRAME", True)    # decided. The cabinet floats on a welded 1 x 1 steel
                                # frame rather than a recessed plinth, and the mast
                                # runs to the floor as one of its members: legs,
                                # ring, mast, fixture arm and the instrument case
                                # are then one black register, the ply another.


# ---------------------------------------------------------------------------
# Plinth (cabinet)
# V1_PHYSICAL_BUILD.md § Station geometry
# ---------------------------------------------------------------------------

PLINTH_W = 20.0  # "cabinet 20 x 14 in" — width, viewer's left-right
PLINTH_D = 16.0  # CHOICE: was 14. See DepthBudget — the console bay in front of the pan.
PLINTH_H = _knob("PLINTH_H", 36.0)  # CHOICE: "cabinet to necessary height". The one
                                    # knob that moves the panel, the block and the light
                                    # together; the lift does not change with it. Tray
                                    # floor is at this height. Sweepable: GROWLAB_PLINTH_H.

SHADOW_GAP_H = 6.0 if FRAME else 2.0  # "Recessed base / shadow gap — 0–2 in";
                                      # on the frame the cabinet floats at 6.
SHADOW_GAP_INSET = 1.0  # CHOICE: how far the kick steps back under the sides

# Frame candidate: 1 x 1 HSS legs at the corners, inset under the cabinet so it
# overhangs, joined by a ring the cabinet floor sits on. CHOICE throughout.
FRAME_TUBE = 1.0
FRAME_LEG_INSET = 1.0  # from the cabinet's outer faces to the legs' outer faces

# The fascia: a clear band across the whole front, recessed behind the front
# plane, over the open console bay. CHOICE throughout.
CHAMFER = 0.5 if FASCIA else 0.0  # on the four vertical outer corners
FASCIA_T = 0.25  # "1/4 in cast acrylic" — clear
FASCIA_RECESS = 0.15  # the band's face behind the cabinet's front plane
FASCIA_POCKET = FASCIA_RECESS + FASCIA_T  # 0.40 cut out of the front for it
FASCIA_MARGIN = 1.0  # the band runs this far above and below the instrument plate
FASCIA_TOP_LIP = 0.75  # CHOICE: ply left behind the band's top edge — the header the
                       # fascia's top row of screws lands in. Below it the bay is open.
FASCIA_SCREW_DIA = 0.135  # clearance for M3 c'sunk, as the plate's F1-4
FASCIA_SCREW_COLUMNS = 5  # CHOICE: across each of the two rows
PILOT_DIA = 2.5 / 25.4  # pilot in ply for an M3 screw or a threaded insert
KNOB_HOLE_CLEARANCE = 0.0625  # the knob shafts pass through the acrylic; the
                              # dials and the e-ink are read through it

# What shows through the band besides the case: a dark sheet on the partition
# and a ply ledge the case sits on. The ledge stops short of the partition so
# the cables drop behind the case to the PSU below. CHOICE throughout.
BACKPLATE_T = 0.0625
LEDGE_T = 0.75
LEDGE_CHASE = 0.75  # gap behind the ledge, the cable route down

CARCASS_T = 0.75  # CHOICE: 3/4 in sheet stock for sides, top frame and floor
REAR_PANEL_T = 0.75  # "full-height rear panel in the carcass" — the mast fixes here
DOOR_GAP = 0.0625  # CHOICE: clearance around the rear door

# Console bay: the dry slice directly behind the front face, full width.
# INSTRUMENT_HEAD_PLANS.md § Depth stack: meters, Inky, i3 and Pi "both fit
# inside 3.00 clear".
CONSOLE_D = 3.0  # clear depth behind the face
CONSOLE_PARTITION_T = 0.5  # CHOICE: the wall between the console bay and the wet bay

# The acrylic face sits in a rebated opening in the front panel, centred on
# the cabinet's width and as high as the rail allows. FACE_WIDTH/HEIGHT come
# from panel_geometry so the opening and the face cannot disagree.
FACE_MARGIN = 1.0  # CHOICE: from the plate's top edge up to the rail
FACE_LIP = 0.5  # box form only: the ply lip behind the face's edge that F1–4 screw into

# Wet bay (reservoir) and dry bay (mast, PSU, driver), behind the console
# partition, "hard-divided".
DIVIDER_T = 0.5  # CHOICE
WET_BAY_W = 13.0  # pan 12.8 + working clearance; dry bay gets the rest (~5)

# Reservoir: "stainless half-size steam table pan, 6 in deep (12.8 x 10.4 x 5.9)"
# V1_PHYSICAL_BUILD.md § Water loop item 1. Modelled as a reference envelope.
RESERVOIR_L = 12.8  # X, across the wet bay
RESERVOIR_W = 10.4  # Y, front to back
RESERVOIR_H = 5.9
RESERVOIR_FRONT_CLEARANCE = 0.25  # CHOICE: behind the console partition
RESERVOIR_LIFT_CLEARANCE = 0.5  # CHOICE: above the pan rim, to lift it off the shelf
WATER_LOW_ABOVE_SHELF = 2.0  # the docs' low line was 2 in above the shelf (12 → 14)
WATER_FULL_ABOVE_SHELF = 4.1  # and the full line 4.1 above (12 → 16.1)

SHELF_T = 0.75  # CHOICE: same stock as the carcass
SHELF_SLOT_PITCH = 1.0  # "slotted supports … moving the shelf an inch afterwards"
SHELF_SLOT_COUNT = 5  # CHOICE: ±2 in of adjustment around the design height


# ---------------------------------------------------------------------------
# Tray
# V1_PHYSICAL_BUILD.md § Station geometry, § Tray and block interface
# ---------------------------------------------------------------------------

# "Tray is a flush rebate … drops into the cabinet's top frame and becomes the
# top surface, flush with the sides." The carcass sides rise to the tray rim,
# the tray nests inside them on a rail, and its rim finishes flush.
TRAY_W = PLINTH_W - 2 * CARCASS_T  # 18.5
TRAY_D = PLINTH_D - 2 * CARCASS_T  # 14.5
TRAY_UPSTAND = 2.0  # "Tray upstand" is 2 in above the tray floor
TRAY_T = 0.0625  # "16 ga" — stainless 16 ga is 0.0625 in (1.59 mm)
TRAY_CORNER_R = 0.25  # CHOICE: inside bend radius for a formed pan

# "The block sits above its own runoff on 0.75 in pads … pads rise from the
# cabinet rail through cutouts in the tray floor so the block bears on the
# carcass."
PAD_H = 0.75
PAD_SIZE = 1.25  # CHOICE: square pad, sized from the section detail
PAD_CUTOUT_CLEARANCE = 0.125  # CHOICE: gap around each pad in the tray floor
PAD_COUNT = 4

# "the tray notched to clear" the mast, which passes behind it.
MAST_NOTCH_CLEARANCE = 0.125  # CHOICE


# ---------------------------------------------------------------------------
# CMU (the vessel)
# V1_PHYSICAL_BUILD.md § Vessel; section drawing footer: "nominal 8 x 8 x 16
# CMU at 15.625 x 7.625 x 7.625 in actual"
# ---------------------------------------------------------------------------

CMU_L = 15.625  # along X, the long face toward the viewer
CMU_W = 7.625  # along Y
CMU_H = 7.625
CMU_FACE_SHELL = 1.25  # CHOICE: typical for a standard two-core block
CMU_END_SHELL = 1.25  # CHOICE
CMU_WEB = 1.0  # CHOICE — "The block's own center web divides the two cores"

# Media: "fill both cores to 1–2 in below the rim"; the docs' 30.9 surface
# against a 32.4 top was 1.5 in down.
MEDIA_BELOW_RIM = 1.5
EMITTER_ABOVE_MEDIA = 0.125  # the docs put discharge 0.1 above the media surface


# ---------------------------------------------------------------------------
# Mast (vertical armature)
# V1_PHYSICAL_BUILD.md § Mast: "2 x 3 in hollow section"
# ---------------------------------------------------------------------------

# 2 in face toward the viewer (X), 3 in deep (Y): the strong axis front-back,
# where the fixture's moment is. "Mast as drawn."
MAST_W, MAST_D = 2.0, 3.0
MAST_WALL = 0.120  # CHOICE: 11 ga, the common wall for 2x3 HSS
MAST_BOTTOM = 0.0 if FRAME else SHADOW_GAP_H + CARCASS_T  # on the frame it IS a
                                                          # leg; otherwise it stands
                                                          # on the carcass floor
MAST_SIDE_CLEARANCE = 0.125  # CHOICE: between the shaft and the divider
MAST_BOLT_DIA = 0.3125  # CHOICE: 5/16 in through-bolts into the rear panel
MAST_BOLT_COUNT = 4
MAST_BOLT_PITCH = 6.0  # CHOICE: spread along the fixing length
MAST_CAP_T = 0.25  # CHOICE: a welded cap plate closes the top; the arm lands on it
MAST_LINE_PASS_DIA = 0.75  # "Ø 0.75 loom pass, grommeted" — now in the shaft's
                           # side wall, where the drip line and LED cable enter


# ---------------------------------------------------------------------------
# Instrument face
# INSTRUMENT_HEAD_PLANS.md § Face — the hole schedule comes from
# pi/dashboard/panel_geometry.py, the same source the emulator draws from.
# The box around it (sides, top, bottom, back, flange) is superseded: the
# cabinet is the box now.
# ---------------------------------------------------------------------------

ACRYLIC_T = 0.25  # "1/4 in cast acrylic throughout" — the box form's face, and the fascia
FACE_SCREW_DIA = 0.135  # "F1–4 … Ø 0.135 c'sunk x4 | M3 flat-head"

# The instrument case (fascia form): a black metal box the meters, Inky, i3,
# Pi and meter driver live in, its front plate carrying the hole schedule.
# Removable forward as a unit once the fascia is off and the knob caps are
# pulled. Sheet aluminium, black. CHOICE throughout.
PLATE_T = 0.125  # 1/8 in front plate — stiff enough to carry two movements
CASE_SHEET_T = 0.0625  # 16 ga folded box behind the plate
CASE_D = 2.75  # plate front to case back; INSTRUMENT_HEAD_PLANS.md: "inside 3.00 clear"
CASE_GAP = 0.1  # fascia back to plate front — the knobs' bushings span it
CASE_LOOM_DIA = 0.75  # grommeted pass in the case's back for the loom
CASE_FLANGE = 0.5  # CHOICE: return flanges folded inward from the LEFT and RIGHT walls'
                   # front edges, full height. The plate's F1-4 screws tap into them;
                   # without them there is nothing in 16 ga to take a screw. No flange on
                   # the top and bottom walls: one would reach 0.5625 in behind the
                   # plate's top edge, and the OFFSET layout puts a dial bezel within
                   # 0.25 of it. Side flanges clear every layout (tightest: WIDE, 0.06).
CASE_TAP_DIA = 2.5 / 25.4  # M3 tap drill in the flanges

# The dial cut diameter is pending calipers. None means: engrave a witness
# circle at the bezel OD and do not cut. Supply a measured value to cut.
DIAL_CUT_DIAMETER: float | None = None
WITNESS_DEPTH = 0.02  # CHOICE: engraving depth for reference marks

# What lives behind the face, as a reference envelope: the face footprint,
# CONSOLE_D deep. If this touches the partition the console is too shallow.
CONSOLE_ELECTRONICS_D = CONSOLE_D  # box form; the fascia form has the case instead


# ---------------------------------------------------------------------------
# LED fixture — envelope only
# V1_PHYSICAL_BUILD.md § Mast: "hangs … at 46 in, cantilevered forward to
# centre over the block". 46 was 15.1 above the media; that distance is kept.
# ---------------------------------------------------------------------------

FIXTURE_ABOVE_MEDIA = 15.0  # CHOICE: the docs' 46 − 30.9, rounded
FIXTURE_W = 16.0  # CHOICE: spans the 15.625 block, per the section drawing
FIXTURE_D = 6.0  # CHOICE: envelope for two boards on a heatsink
FIXTURE_H = 1.5  # CHOICE
FIXTURE_ARM_W = 1.5  # CHOICE: the arm forward from the mast
FIXTURE_ARM_T = 0.5  # CHOICE
FIXTURE_BAR_D = 1.0  # CHOICE: the cross bar along the fixture's back edge


# ---------------------------------------------------------------------------
# Derived positions — the height stack the docs publish, computed rather than
# restated, so a test can hold the two against each other.
# ---------------------------------------------------------------------------

FLOOR_TOP_Z = SHADOW_GAP_H + CARCASS_T  # 2.75
TRAY_FLOOR_Z = PLINTH_H  # 36
TRAY_RIM_Z = PLINTH_H + TRAY_UPSTAND  # 38
RAIL_TOP_Z = TRAY_FLOOR_Z - TRAY_T  # the tray floor rests on the rail
RAIL_BOTTOM_Z = RAIL_TOP_Z - CARCASS_T  # 35.19 — the top of every bay
CMU_UNDERSIDE_Z = TRAY_FLOOR_Z + PAD_H  # 36.75
CMU_TOP_Z = CMU_UNDERSIDE_Z + CMU_H  # 44.375
MEDIA_SURFACE_Z = CMU_TOP_Z - MEDIA_BELOW_RIM  # 42.875
EMITTER_Z = MEDIA_SURFACE_Z + EMITTER_ABOVE_MEDIA  # 43.0
FIXTURE_Z = MEDIA_SURFACE_Z + FIXTURE_ABOVE_MEDIA  # 57.875 — underside of the fixture
MAST_TOP = FIXTURE_Z + FIXTURE_H  # 59.375 — top of the cap; the arm sits on it

# Reservoir shelf: as high as the rail allows, rounded down to a whole inch so
# the slotted supports read as a sensible range. The pan must clear the rail
# by RESERVOIR_LIFT_CLEARANCE to be lifted off the shelf and slid out.
SHELF_H = float(math.floor(RAIL_BOTTOM_Z - RESERVOIR_LIFT_CLEARANCE - RESERVOIR_H))  # 28
WATER_LOW = SHELF_H + WATER_LOW_ABOVE_SHELF  # 30.0
WATER_FULL = SHELF_H + WATER_FULL_ABOVE_SHELF  # 32.1

# The face: centred on width, top edge FACE_MARGIN under the rail.
FACE_X0 = -FACE_WIDTH / 2
FACE_Z1 = RAIL_BOTTOM_Z - FACE_MARGIN
FACE_Z0 = FACE_Z1 - FACE_HEIGHT  # 22.19
PANEL_CENTRE_Z = (FACE_Z0 + FACE_Z1) / 2  # 28.19 — read standing, looking down
# The plate sits behind the fascia by CASE_GAP; the box form's acrylic face is
# flush with the front instead.
FACE_Y0 = FASCIA_POCKET + CASE_GAP if FASCIA else 0.0  # 0.50 behind the front plane
FACE_T = PLATE_T if FASCIA else ACRYLIC_T
CASE_Y0 = FACE_Y0
CASE_Y1 = FACE_Y0 + CASE_D  # 3.25 — the cable gap behind is CONSOLE_Y1 − this

# Plan: console bay, partition, then the wet and dry bays behind.
CONSOLE_Y0 = CARCASS_T  # inside face of the front panel
CONSOLE_Y1 = CONSOLE_Y0 + CONSOLE_D  # 3.75
PARTITION_Y0 = CONSOLE_Y1
PARTITION_Y1 = PARTITION_Y0 + CONSOLE_PARTITION_T  # 4.25
REAR_INSIDE_Y = PLINTH_D - REAR_PANEL_T  # 15.25

# The divider between the wet bay (viewer's left) and the dry bay.
INSIDE_X0 = -PLINTH_W / 2 + CARCASS_T  # −9.25
INSIDE_X1 = PLINTH_W / 2 - CARCASS_T  # 9.25
DIVIDER_X = INSIDE_X0 + WET_BAY_W + DIVIDER_T / 2  # 4.0
DRY_BAY_X0 = DIVIDER_X + DIVIDER_T / 2  # 4.25
DRY_BAY_W = INSIDE_X1 - DRY_BAY_X0  # 5.0

# Mast plan position: in the dry bay, against the rear panel, as close to the
# cabinet's centre as the divider allows — so the fixture's cross bar is short.
MAST_X = DRY_BAY_X0 + MAST_SIDE_CLEARANCE + MAST_W / 2  # 5.375
MAST_Y = REAR_INSIDE_Y - MAST_D / 2  # 13.75

# Reservoir plan position: in the wet bay, from the partition.
RESERVOIR_X = INSIDE_X0 + WET_BAY_W / 2
RESERVOIR_Y0 = PARTITION_Y1 + RESERVOIR_FRONT_CLEARANCE  # 4.5
RESERVOIR_Y1 = RESERVOIR_Y0 + RESERVOIR_W  # 14.9

# CMU plan position: centred in the cabinet. The mast is off to the side now,
# so nothing argues for setting the block forward.
CMU_X = 0.0
CMU_Y = PLINTH_D / 2  # 8.0

# Fixture: centred over the block. The moment arm at the mast is derived.
FIXTURE_X = CMU_X
FIXTURE_Y = CMU_Y
FIXTURE_CANTILEVER = MAST_Y - FIXTURE_Y  # 5.75 — mast centreline to fixture centreline

# Where the pads meet the block: under the four corners, where a face shell
# meets an end shell and the block is solid all the way down.
PAD_X = CMU_L / 2 - CMU_END_SHELL / 2
PAD_Y_OFFSET = CMU_W / 2 - CMU_FACE_SHELL / 2


@dataclass(frozen=True)
class HeightStack:
    """The published height stack, for comparison against the docs' table."""

    shadow_gap: float = SHADOW_GAP_H
    face_bottom: float = FACE_Z0
    panel_centre: float = PANEL_CENTRE_Z
    reservoir_shelf: float = SHELF_H
    water_low: float = WATER_LOW
    water_full: float = WATER_FULL
    face_top: float = FACE_Z1
    tray_floor: float = TRAY_FLOOR_Z
    tray_rim: float = TRAY_RIM_Z
    cmu_underside: float = CMU_UNDERSIDE_Z
    media_surface: float = MEDIA_SURFACE_Z
    emitter: float = EMITTER_Z
    cmu_top: float = CMU_TOP_Z
    fixture: float = FIXTURE_Z
    mast_top: float = MAST_TOP

    @property
    def static_lift(self) -> float:
        """Low water line to emitter discharge — the pump's real job."""
        return self.emitter - self.water_low


HEIGHTS = HeightStack()


@dataclass(frozen=True)
class DepthBudget:
    """What the cabinet's depth has to hold, front to back, through the wet bay.

    The console bay sits in front of the reservoir pan; this is the arithmetic
    that decides whether they fit, and by how much. The mast is in the dry bay
    and no longer competes with the pan.
    """

    front_panel: float = CARCASS_T
    console: float = CONSOLE_D
    partition: float = CONSOLE_PARTITION_T
    front_clearance: float = RESERVOIR_FRONT_CLEARANCE
    reservoir: float = RESERVOIR_W
    rear_panel: float = REAR_PANEL_T
    available: float = PLINTH_D

    @property
    def required(self) -> float:
        return (self.front_panel + self.console + self.partition
                + self.front_clearance + self.reservoir + self.rear_panel)

    @property
    def slack(self) -> float:
        """Positive: they fit with this much to spare. Negative: they collide by this much."""
        return self.available - self.required


DEPTH = DepthBudget()
