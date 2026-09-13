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

The dial cut diameter (Ø 2.75, calipered 2026-09-09) and the LM301H +
heatsink modules (each 15.5 × 1.575 × 0.525, calipered 2026-09-10; two
modules side by side → 15.5 × 3.15 × 0.525 combined) are both measured.
The steel shell clears the pair and the head is well under its weight
budget.
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


# ---------------------------------------------------------------------------
# Plinth (cabinet)
# The form is decided (2026-09-04): height 36; the clear fascia over a white
# instrument case (the apparatus on show behind glass, cabling included, the
# way the Transparent speaker shows its amplifier); and the steel base frame
# the cabinet floats on, whose members continue into the mast. Every metal part
# is white (2026-09-05); the ply body is the other register.
# V1_PHYSICAL_BUILD.md § Station geometry
# ---------------------------------------------------------------------------

PLINTH_W = 20.0  # "cabinet 20 x 14 in" — width, viewer's left-right
PLINTH_D = 16.0  # CHOICE: was 14. See DepthBudget — the console bay in front of the pan.
PLINTH_H = _knob("PLINTH_H", 36.0)  # CHOICE: "cabinet to necessary height". The one
                                    # knob that moves the panel, the block and the light
                                    # together; the lift does not change with it. Tray
                                    # floor is at this height. Sweepable: GROWLAB_PLINTH_H.

SHADOW_GAP_H = 6.0  # the cabinet floats this far off the floor on the frame

# The frame: 1 x 1 HSS legs at the corners, inset under the cabinet so it
# overhangs, joined by a ring the cabinet floor sits on. CHOICE throughout.
FRAME_TUBE = 1.0
FRAME_LEG_INSET = 1.0  # from the cabinet's outer faces to the legs' outer faces

# The fascia: a clear band across the whole front, recessed behind the front
# plane, over the open console bay. CHOICE throughout.
CHAMFER = 0.5  # on the four vertical outer corners
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
# ---------------------------------------------------------------------------

# Round tube, not rectangular section. The 2 x 3 HSS it replaces was inherited
# from a spec line and never computed: the head is 12 lb at a 5.75 in offset,
# which put 73 psi into a section good for 21,600 — 0.3% of allowable, roughly
# 300x overbuilt. What actually sized it was the bore, because the counterweight
# lived inside. With the counterweight gone the section answers to the load
# alone: 1.5 x 0.065 carries the head at 3% of allowable and sways 0.16 in under
# a deliberate 10 lb shove, at 1.0 lb/ft against the old 3.9.
MAST_OD = 1.5
MAST_WALL = 0.065  # 16 ga
# Kept as the section's bounding box so every notch, clearance and datum
# downstream still reads the same way. For a round tube they are both the OD.
MAST_W = MAST_D = MAST_OD
MAST_BOTTOM = 0.0  # the mast is one of the frame's legs: it runs to the floor
MAST_SIDE_CLEARANCE = 0.125  # CHOICE: between the shaft and the divider

# --- how it is held to the cabinet ---------------------------------------
# U-bolts round the tube, not bolts through it. A bolt through a closed
# section has to be tightened from inside it, which was never possible with
# the HSS either and is plainly impossible down a 1.37 in bore. A U-bolt is
# the hardware a round tube asks for: two legs either side, through the fixed
# rear panel, nutted in the dry bay where a hand can reach. It also leaves the
# tube unbroken, which the painted finish wants.
MAST_STRAP_COUNT = 3
MAST_STRAP_PITCH = 9.0  # CHOICE: spread along the fixing length
MAST_STRAP_BOLT_DIA = 0.28  # 1/4-20 U-bolt legs, clearance
MAST_STRAP_SPAN = MAST_OD + 0.6  # CHOICE: leg centres, straddling the tube
# --- the head's clamp ----------------------------------------------------
# No counterweight. A 12 lb head is a two-handed lift, and a split clamp collar
# holds it and locks the height in one part. The counterweight was what forced a
# large bore, the bore was what forced the section, and the section was what made
# the mast look like structure for a building. Removing it removes all three.
CARRIAGE_H = 4.0  # CHOICE: collar length; sets how much the head can rack
CARRIAGE_CLEAR = 0.020  # CHOICE: close sliding fit, closed by the split
CARRIAGE_WALL = 0.1875  # CHOICE: enough meat for the split and its pinch bolts

MAST_CAP_T = 0.25  # CHOICE: a disc welded over the top. Nothing lands on it any
                   # more — the arm is on the collar — but an open pipe end
                   # reads unfinished, more so in white.
MAST_LINE_PASS_DIA = 0.50  # was 0.75, which is half the diameter of this tube
                           # and would have been a gash rather than a hole. The
                           # drip line and the LED cable both pass 0.50.
MAST_LINE_PASS_H = 0.85  # The entry is an **obround**, 0.50 wide x 0.85 tall, not
                         # a bigger circle. The camera moved into the lightbox on
                         # 2026-09-12 and its HDMI connector will not pass a half
                         # inch — but opening the hole to Ø1.00 would wrap 84° of
                         # this tube's circumference and break out tangentially,
                         # the exact gash Ø0.75 was rejected for. Wrap is set by
                         # the width across the circumference, so stretching the
                         # hole *along the tube's axis* costs nothing: same 0.50
                         # width, same ±19.5° of wrap, and the connector passes
                         # lengthwise.
                         #
                         # 0.85 rather than 1.00 because the pass lives in a
                         # 1.29 in window — pan rim below, rail above — and the
                         # obround grows *upward only* so the bottom edge keeps
                         # the clearance over the rim the old hole had. See
                         # ``plinth.LINE_PASS_Z``. It passes a slim HDMI
                         # connector (~0.60 x 0.30); the booted kind on a thick
                         # cable will not go, and that cable is wrong for the
                         # bore's slack anyway.

# The cable slot (2026-09-12). The LED pair, the camera's HDMI and the fixture
# fans' lead run up the bore and out to the moving collar through a longitudinal
# slot in the *rear* face, so no cable is ever visible on the mast. It spans the
# collar's travel and nothing more: the tube stays closed for 3.75 in below the
# cap and for 56 in below the slot's lower end, so neither end of the section is
# opened and the welded cap keeps its job as an end closure.
#
# **The cost is torsion, and it is real.** An open section is ~365x less stiff in
# torsion than a closed one (J 0.151 -> 0.00041 in^4), so a sideways shove at the
# fixture twists the mast elastically where it used to be rigid — about 6 deg
# under a casual bump, 20 deg under a hard one, worst at full lift where the
# whole slot lies between the collar and closed tube. It returns; nothing yields.
# Bending is untouched in any way that matters: 3.1% of allowable against 2.7%.
# This buys the invisibility the piece is built on, and it is the reason the
# coiled external lead `canopy.py` used to describe is gone.
MAST_SLOT_W = 0.25  # CHOICE: passes the cable, not its connector
MAST_SLOT_MARGIN = 0.375  # CHOICE: slot beyond the collar's travel at each end so
                          # the lead is never pinched at either extreme
MAST_SLOT_KEYHOLE_DIA = 0.625  # CHOICE: at the top end. Passes an HDMI connector at
                               # assembly so the cap is never unwelded, and is a
                               # far better crack arrest than the slot's own width.
MAST_SLOT_END_DIA = 0.25  # the bottom end, drilled round. An undrilled slot end is
                          # a crack starter; this is not optional.


# ---------------------------------------------------------------------------
# Instrument face
# INSTRUMENT_HEAD_PLANS.md § Face — the hole schedule comes from
# pi/dashboard/panel_geometry.py, the same source the emulator draws from.
# The box around it (sides, top, bottom, back, flange) is superseded: the
# cabinet is the box now.
# ---------------------------------------------------------------------------

FACE_SCREW_DIA = 0.135  # "F1–4 … Ø 0.135 c'sunk x4 | M3 flat-head"

# The instrument case (fascia form): a white metal box the meters, Inky, i3,
# Pi and meter driver live in, its front plate carrying the hole schedule.
# Removable forward as a unit once the fascia is off and the knob caps are
# pulled. Mild steel sheet in white DTM acrylic, as every metal part is —
# no aluminium anywhere in V1. CHOICE throughout.
#
# The thicknesses below are unchanged from the aluminium version, which makes
# the plate STIFFER, not weaker: steel's modulus is 29 Msi against 10, so
# 1/8 in steel is about 2.9x the bending stiffness of the 1/8 in aluminium it
# replaces. It is also 2.9x the weight (4.05 lb against 1.40). If that ever
# matters, 13 ga (0.090) steel still matches the original aluminium plate's
# stiffness; it is not the reason to change anything today.
# 0.0625 is nominal for the folded box: 16 ga steel is 0.0598, and 0.003 in is
# well inside the bend allowance the shop owns anyway.
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

# Weston 301 bezel OD, calipered 2026-09-09 — both meters identical.
DIAL_CUT_DIAMETER: float | None = 2.75
DIAL_BODY_DEPTH = 0.975   # bezel rear face to body rear face, calipered 2026-09-09
DIAL_TERMINAL_DEPTH = 1.735  # bezel rear face to terminal bolt rear, calipered 2026-09-09
WITNESS_DEPTH = 0.02  # CHOICE: engraving depth for reference marks


# ---------------------------------------------------------------------------
# LED fixture — the envelope, and (below) the lightbox that fills it
# V1_PHYSICAL_BUILD.md § Mast: "hangs … at 46 in, cantilevered forward to
# centre over the block". 46 was 15.1 above the media; that distance is kept.
# ---------------------------------------------------------------------------

# --- canopy travel ---------------------------------------------------------
# LIGHTING_SYSTEM.md has always said "Height should remain adjustable" — to
# accommodate plant growth, allow intensity tuning and prevent light stress —
# and named a pulley or sliding mount. It was never specced. A fixed head at
# 15 in above the media has a mature ranunculus (12–18 in) growing into the
# light: at 15 in tall the canopy touches it, at 18 in it is 3 in inside it.
#
# These two numbers set the whole armature. The mast height and the carriage
# travel both derive from them, so dialling the top of travel down shortens
# the mast with it.
FIXTURE_ABOVE_MEDIA_MIN = 12.0  # CHOICE: closest useful working distance
FIXTURE_ABOVE_MEDIA_MAX = 33.0  # CHOICE: 15 in of clearance over an 18 in plant

# Where the head is drawn. Honoured as a knob so the viewer can show the
# armature at any point in its travel; the model is drawn parked at the bottom.
FIXTURE_ABOVE_MEDIA = _knob("FIXTURE_ABOVE_MEDIA", FIXTURE_ABOVE_MEDIA_MIN)
FIXTURE_W = 16.0  # CHOICE: spans the 15.625 block, per the section drawing
FIXTURE_D = 6.0  # CHOICE: envelope for two boards on a heatsink
FIXTURE_H = 1.5  # CHOICE

# --- the lightbox ----------------------------------------------------------
# A folded steel channel, open at the bottom, over the on-hand aluminium
# heatsink bar. Decided 2026-09-05 after the fixture had gone the whole project
# with no material at all: every lighting document specified the electronics and
# none of them said what the body was.
#
# Steel is what is shown and specified; the aluminium stays because physics
# wants it and it is already bought. Steel conducts at roughly a quarter of
# aluminium's rate, so an all-steel heatsink would need several times the area
# — a bigger object hanging over the plant, which is the mistake the fan
# taught. The bar does the conducting inside a shell that does the looking.
#
# Open at the bottom because that is the light aperture; slotted along the top
# and open at the ends so the channel is a chimney rather than an oven.
#
# Each LM301H board has its own heatsink bar — two modules, each calipered
# 2026-09-10 at 15.5 x 1.575 x 0.525. Arranged side by side (parallel, LEDs
# down), the combined envelope is 15.5 x 3.15 x 0.525. The original guesses
# (14 x 4 x 1) overestimated the height and underestimated the width.
LIGHTBOX_T = 0.0625  # CHOICE: 16 ga, as the instrument case
LIGHTBOX_VENT_N = 9  # CHOICE: slots along the top, over the heatsink's fins
LIGHTBOX_VENT_W = 0.375  # CHOICE
LIGHTBOX_VENT_L = 3.5  # CHOICE: along the depth, inside the cross bar's landing
LIGHTBOX_END_INSET = 0.75  # CHOICE: the end slots' inset from each end

# Two LM301H + heatsink modules side by side, calipered 2026-09-10.
# Each module: 15.5 x 1.575 x 0.525; combined envelope below.
HEATSINK_W = 15.5        # along the fixture width (one module's length)
HEATSINK_D = 2 * 1.575   # two modules side by side, front to back
HEATSINK_H = 0.525       # height/thickness of one module
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
FIXTURE_Z = MEDIA_SURFACE_Z + FIXTURE_ABOVE_MEDIA  # underside of the fixture, as drawn
FIXTURE_Z_MIN = MEDIA_SURFACE_Z + FIXTURE_ABOVE_MEDIA_MIN  # 54.875
FIXTURE_Z_MAX = MEDIA_SURFACE_Z + FIXTURE_ABOVE_MEDIA_MAX  # 75.875
FIXTURE_TRAVEL = FIXTURE_Z_MAX - FIXTURE_Z_MIN  # 21.0

# The arm's top face, which is where the carriage is centred.
CARRIAGE_Z = FIXTURE_Z + FIXTURE_H
CARRIAGE_Z_MIN = FIXTURE_Z_MIN + FIXTURE_H  # 56.375
CARRIAGE_Z_MAX = FIXTURE_Z_MAX + FIXTURE_H  # 77.375

# The cable slot spans the collar's travel, plus a margin at each end. The cable
# leaves the bore at the collar's mid-height, so it is the *carriage* band the
# slot has to cover, not the fixture's.
MAST_SLOT_Z0 = CARRIAGE_Z_MIN - MAST_SLOT_MARGIN  # 56.0
MAST_SLOT_Z1 = CARRIAGE_Z_MAX + MAST_SLOT_MARGIN  # 77.75
MAST_SLOT_LEN = MAST_SLOT_Z1 - MAST_SLOT_Z0  # 21.75

# The mast is now as tall as the travel needs, not as tall as one fixed head
# position. It stops a little above the collar at full lift — enough that the
# tube reads as continuing past the head rather than stopping at it.
MAST_HEAD = 2.0  # CHOICE: tube above the collar at full lift, plus the cap
MAST_TOP = CARRIAGE_Z_MAX + CARRIAGE_H / 2 + MAST_HEAD

# Reservoir shelf: as high as the rail allows, rounded down to a whole inch so
# the slotted supports read as a sensible range. The pan must clear the rail
# by RESERVOIR_LIFT_CLEARANCE to be lifted off the shelf and slid out.
SHELF_H = float(math.floor(RAIL_BOTTOM_Z - RESERVOIR_LIFT_CLEARANCE - RESERVOIR_H))  # 28

# Where the mast's line pass sits, in the 1.29 in window between the pan's rim
# and the rail. The obround grows **upward only** from where the old Ø0.50
# hole's bottom edge was, because that edge's 0.15 in clearance over the rim is
# what keeps the loom above the water line. Growing it symmetrically put the
# lower edge below the rim.
MAST_LINE_PASS_BOTTOM_Z = SHELF_H + RESERVOIR_H + 0.4 - MAST_LINE_PASS_DIA / 2  # 34.05
MAST_LINE_PASS_Z = MAST_LINE_PASS_BOTTOM_Z + MAST_LINE_PASS_H / 2  # 34.475
WATER_LOW = SHELF_H + WATER_LOW_ABOVE_SHELF  # 30.0
WATER_FULL = SHELF_H + WATER_FULL_ABOVE_SHELF  # 32.1

# The face: centred on width, top edge FACE_MARGIN under the rail.
FACE_X0 = -FACE_WIDTH / 2
FACE_Z1 = RAIL_BOTTOM_Z - FACE_MARGIN
FACE_Z0 = FACE_Z1 - FACE_HEIGHT  # 22.19
PANEL_CENTRE_Z = (FACE_Z0 + FACE_Z1) / 2  # 28.19 — read standing, looking down
# The plate sits behind the fascia by CASE_GAP.
FACE_Y0 = FASCIA_POCKET + CASE_GAP  # 0.50 behind the front plane
FACE_T = PLATE_T
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


# ---------------------------------------------------------------------------
# Canopy sensor case (2026-09-13)
#
# A printed block on the CMU's centre-rear carrying the AS7341, BME280 and
# ADS1115. The two plants grow from the cores at either end, so the block's
# centre is the one place that stays open — and stays unshaded.
#
# **This section is in millimetres.** Every constraint on this part is metric:
# the boards, the M2 screws and heat-set inserts, the nozzle, the layer height.
# Inches are the right unit for a cabinet and the wrong one here, so the values
# below are given in mm and multiplied by MM to reach the inches the geometry
# helpers take. The comment on each line is the figure you would read on a
# caliper.
# ---------------------------------------------------------------------------

MM = 1.0 / IN  # inches per millimetre

# --- The boards, as bought. Generic modules, not Adafruit. -----------------
# AS7341: the small square generic, photographed 2026-09-13 — NOT the T-shaped
# Ewellite board the first cut was drawn to. Scaled off the photo by its own
# 0.1 in header-pad pitch, so figures are good to about half a millimetre.
# CALIPER THE FOUR MARKED ONES BEFORE PRINTING. The header edge is -X, and the
# edge with the regulator (the photo's top) is +Y.
SC_AS7341_L = 21.0 * MM  # CALIPER — along X
SC_AS7341_W = 16.0 * MM  # CALIPER — along Y
SC_AS7341_SENSOR_X = 18.0 * MM  # CALIPER — the sensor ring, from the header edge
SC_AS7341_SENSOR_Y = 7.9 * MM  # CALIPER — from the +Y edge. Mid-height, near +X
# The board's own Ø3 mounting hole sits on the sensor's row, 6.7 mm inboard of
# it. That is the fixing: one M2.5 up through the hole into a boss hanging from
# the top wall, with the baffle as the second contact. The one board whose
# position matters gets a screw, not tape.
SC_AS7341_HOLE_X = 11.3 * MM
SC_AS7341_HOLE_Y = 7.9 * MM
SC_AS7341_HOLE_DIA = 3.0 * MM
SC_AS7341_BOSS_DIA = 6.0 * MM
SC_AS7341_PILOT = 2.1 * MM  # M2.5 self-tapping in PETG
SC_AS7341_PILOT_DEPTH = 3.0 * MM  # 2.0 of boss + 1.0 into the top wall, leaving
                                  # 1.0 of show face over it
# What is almost certainly a white LED, 5.2 mm below the sensor — the light
# square at bottom right of the photo. Advisory: the baffle test uses it.
SC_AS7341_LED_DX = -0.7 * MM
SC_AS7341_LED_DY = -5.2 * MM
# Tallest part on the sensor face (the big capacitor, top centre). Sets the
# minimum baffle drop, because the board hangs component-side up. CHECK IT.
SC_AS7341_PART_H = 1.6 * MM
SC_ADS1115_L = 28.0 * MM  # 28 x 18 published for the GY-ADS1115
SC_ADS1115_W = 18.0 * MM
SC_BME280_L = 15.4 * MM  # 15.4 x 11.6 published for the GY-BME280-3.3
SC_BME280_W = 11.6 * MM
SC_BOARD_T = 1.6 * MM
SC_BOARD_CLEAR = 0.4 * MM  # per side, around a board in its fence

# --- Envelope -------------------------------------------------------------
# 56 long. The first cut was 78, forced by a 40 mm T-shaped AS7341 with its
# sensor at one end; the board actually in hand is 21 mm square and the sensor
# is near mid-length, so the port centres with 18 mm of board one side and 3 the
# other. The length is now set by the ADS1115 on the plate (28) between the two
# inlet vents and the corner bosses. Width and height are as tight as the boards
# allow.
SC_LEN = 56.0 * MM
SC_WID = 27.0 * MM  # inside the CMU's 31.75 face shell with 4.75 to spare
SC_HGT = 18.0 * MM  # body 15.5 + base plate 2.5
SC_WALL = 2.0 * MM  # CHOICE: 4 perimeters at 0.50 extrusion width, exactly
SC_BASE_T = 2.5 * MM  # 5 lines. 2.0 looked tidier until the M2 countersink
                      # turned out to be 2.2 deep and came through the back
SC_CHAMFER = 1.5 * MM  # the four vertical corners, 45 deg, cut like the plinth's

# --- The optical stack ----------------------------------------------------
SC_PORT_DIA = 12.3 * MM  # recess for a Ø12.0 PTFE disc, 0.3 for FDM
SC_PORT_DEPTH = 1.0 * MM  # disc thickness, so it finishes flush with the top face
SC_APERTURE_DIA = 10.5 * MM  # through the rest of the top wall; 0.9 ledge holds the disc
SC_BAFFLE_ID = 6.5 * MM  # the sensor's field stop; narrower than the LED's offset
SC_BAFFLE_OD = 8.5 * MM
SC_BAFFLE_DROP = 2.0 * MM  # top wall inner face to the board. Doubles as the standoff
                           # that sets sensor-to-diffuser distance — the one height
                           # in this part that has to be right. It is also the
                           # component clearance: the board hangs sensor-side up, so
                           # every part on that face lives in this gap.
SC_POST_DIA = 3.0 * MM  # the BME280's four standoffs

# --- Closure --------------------------------------------------------------
SC_BOSS_DIA = 6.0 * MM
SC_BOSS_H = 6.0 * MM  # deliberately short: the AS7341 lies above the bosses and
                      # a full-height boss would foul it
SC_INSERT_HOLE = 2.6 * MM  # M2 heat-set insert (Ø3.2 body)
SC_INSERT_DEPTH = 5.0 * MM
SC_SCREW_DIA = 2.2 * MM  # M2 clearance through the base plate
SC_SCREW_CSK = 4.4 * MM  # countersink, so nothing proud sits against the block
SC_SCREW_INSET = 5.0 * MM

# --- Entries, vents, seating ----------------------------------------------
# Both cable entries are notches in the walls' bottom edge rather than holes.
# A hole through a vertical wall needs a teardrop or a bridge; a notch closed by
# the base plate needs neither, and the cable drops in instead of threading.
SC_CABLE_W = 5.3 * MM  # Cat5e (~5.5 OD), a shade under for a friction fit
SC_CABLE_H = 6.0 * MM
SC_PROBE_W = 4.6 * MM  # SEN0308 lead, up from the core
SC_PROBE_H = 5.0 * MM
# No internal tie posts: they chopped the plate's clear run and the ADS1115
# would not fit between them and the corner bosses. The notch is sized a shade
# under the cable for a friction fit, and a zip tie goes on outside the wall.
SC_VENT_L = 10.0 * MM  # slots in the base plate, under the case, facing the block
SC_VENT_W = 2.0 * MM
SC_VENT_X = 17.0 * MM  # one slot each end, between the ADS1115 and the bosses
SC_FOOT_DIA = 8.0 * MM  # recess for a self-adhesive silicone foot
SC_FOOT_DEPTH = 0.6 * MM
SC_LIP_DROP = 12.0 * MM  # the rear wall carries on down past the floor and bears
                         # on the block's rear face. That is the whole fixing:
                         # weight, friction and a face that cannot slide forward.

# --- Where it sits --------------------------------------------------------
SC_X = CMU_X  # centred on the block's length
SC_Y1 = CMU_Y + CMU_W / 2  # rear face flush with the block's rear face
SC_Y = SC_Y1 - SC_WID / 2
SC_Z0 = CMU_TOP_Z  # the base plate's underside, on its silicone feet
