"""Every dimension of the V1 station, as data.

This is the physical sibling of ``pi/dashboard/panel_geometry.py``: one place
the numbers live, so the CAD, the emulator, and the fabrication docs cannot
drift apart. Everything downstream (``plinth.py``, ``mast.py``, ``head.py`` …)
reads from here and computes nothing of its own.

Conventions
-----------
* **Inches.** Every document for this build is in inches and so is this file.
  build123d's kernel works in millimetres, so geometry code multiplies by
  ``IN`` at construction. Tests assert in inches.
* **Origin** is on the floor, at the centre of the plinth's width, on the
  plinth's front face. ``+X`` is the viewer's right, ``+Y`` runs from the front
  face toward the back, ``+Z`` is up. So the mast — "at the back" — sits at
  high Y, and the instrument face the viewer reads is at low Y.
* **Provenance.** Each value carries the document and section it came from.
  Values that appear in no document are marked ``CHOICE`` — they are design
  decisions made here to produce a buildable model, and the person finishing
  this in Fusion should treat them as proposals, not canon.

Two things are deliberately *not* asserted:

* **The dial cut diameter.** The Weston 301 bezels are pending calipers; the
  drawings' Ø 2.79 is a Simpson figure that does not apply. ``head.py`` engraves
  a witness circle at the bezel OD unless a measured cut is supplied.
* **The LED fixture.** Two LM301H boards on a heatsink, cantilevered forward of
  the mast. No dimensions exist for the heatsink; the fixture here is an
  envelope so the assembly reads correctly, not a part to fabricate.
"""

from __future__ import annotations

from dataclasses import dataclass

IN = 25.4  # millimetres per inch — the only unit conversion in the package


# ---------------------------------------------------------------------------
# Plinth (cabinet)
# V1_PHYSICAL_BUILD.md § Station geometry (resolved 2026-09-03)
# ---------------------------------------------------------------------------

PLINTH_W = 20.0  # "cabinet 20 x 14 in" — width, viewer's left-right
PLINTH_D = 14.0  # depth, "set by the reservoir, not the block"
PLINTH_H = 24.0  # "Cabinet top / tray floor — 24 in"

SHADOW_GAP_H = 2.0  # "Recessed base / shadow gap — 0–2 in"
SHADOW_GAP_INSET = 1.0  # CHOICE: how far the kick steps back under the sides

CARCASS_T = 0.75  # CHOICE: 3/4 in sheet stock for sides, top frame and floor
REAR_PANEL_T = 0.75  # "full-height rear panel in the carcass" — the mast fixes here

SHELF_H = 12.0  # "Reservoir shelf — 12 in"
SHELF_T = 0.75  # CHOICE: same stock as the carcass
SHELF_SLOT_PITCH = 1.0  # "slotted supports … moving the shelf an inch afterwards"
SHELF_SLOT_COUNT = 5  # CHOICE: ±2 in of adjustment around the design height

# Wet bay (reservoir) and dry bay (electronics), "hard-divided".
# "The reservoir pan at 12.8 x 10.4 leaves ~7 in of cabinet width for the dry bay."
DIVIDER_T = 0.5  # CHOICE
WET_BAY_W = 13.0  # pan 12.8 + working clearance; dry bay gets the rest (~6.5)

# Reservoir: "stainless half-size steam table pan, 6 in deep (12.8 x 10.4 x 5.9)"
# V1_PHYSICAL_BUILD.md § Water loop item 1. Modelled as a reference envelope.
RESERVOIR_L = 12.8  # X, across the wet bay
RESERVOIR_W = 10.4  # Y, front to back
RESERVOIR_H = 5.9
RESERVOIR_FRONT_CLEARANCE = 0.25  # CHOICE: behind the front panel
WATER_LOW = 14.0  # "Water surface — low (design case) — 14.0 in"
WATER_FULL = 16.1  # "Water surface — full — 16.1 in"


# ---------------------------------------------------------------------------
# Tray
# V1_PHYSICAL_BUILD.md § Station geometry, § Tray and block interface
# ---------------------------------------------------------------------------

# "Tray is a flush rebate … drops into the cabinet's top frame and becomes the
# top surface, flush with the sides." Read as: the carcass sides rise to the
# tray rim (26), the tray nests inside them on a rail, and its rim finishes
# flush with the top of the sides. So the pan's plan is the carcass INSIDE.
TRAY_W = PLINTH_W - 2 * CARCASS_T  # 18.5
TRAY_D = PLINTH_D - 2 * CARCASS_T  # 12.5
TRAY_UPSTAND = 2.0  # "Tray upstand — 26 in", i.e. 24 → 26
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

# Media: "fill both cores to 1–2 in below the rim" → the doc's 30.9 surface
# against a 32.4 top is 1.5 in down.
MEDIA_BELOW_RIM = 1.5


# ---------------------------------------------------------------------------
# Mast (vertical armature)
# V1_PHYSICAL_BUILD.md § Mast — thin shaft, instrument head
# ---------------------------------------------------------------------------

# "2 x 3 in hollow section". The doc does not say which way round. Default:
# the 2 in face toward the viewer (X), 3 in deep (Y) — the thinner reading of
# "thin shaft". Rotating it is one flag, and it matters: see depth_budget().
MAST_ROTATED = False  # CHOICE — True puts 3 in across and 2 in deep
MAST_W, MAST_D = (3.0, 2.0) if MAST_ROTATED else (2.0, 3.0)
MAST_WALL = 0.120  # CHOICE: 11 ga, the common wall for 2x3 HSS
MAST_TOP = 46.0  # "plinth top to 46 in"

# The doc says "plinth top to 46 in" for the shaft and, separately, that it
# "bolts to the cabinet carcass … a full-height rear panel". The section
# drawing draws it running the full height of the cabinet. Both are honoured:
# the visible shaft rises from the plinth top, and it continues down the inside
# of the rear panel to the cabinet floor for its fixing.
MAST_BOTTOM = SHADOW_GAP_H + CARCASS_T  # CHOICE: stands on the carcass floor, inside
MAST_BOLT_DIA = 0.3125  # CHOICE: 5/16 in through-bolts into the rear panel
MAST_BOLT_COUNT = 4
MAST_BOLT_PITCH = 6.0  # CHOICE: spread along the fixing length

# Flange — INSTRUMENT_HEAD_PLANS.md § Panel schedule:
# "Flange | 6.00 x 4.00 | 1/4 steel. Shaft welded on; 4 x M6 tapped; arm boss"
FLANGE_W = 6.0
FLANGE_D = 4.0
FLANGE_T = 0.25
# Head bottom panel: "4 x Ø 0.257 on 2.00 x 1.50 for flange bolts"
FLANGE_BOLT_PATTERN_X = 2.0
FLANGE_BOLT_PATTERN_Y = 1.5
FLANGE_BOLT_CLEARANCE_DIA = 0.257


# ---------------------------------------------------------------------------
# Instrument head
# INSTRUMENT_HEAD_PLANS.md — face dimensions and hole schedule come from
# pi/dashboard/panel_geometry.py, the same source the emulator draws from.
# ---------------------------------------------------------------------------

HEAD_D = 3.5  # "Head external: 9.50 W x 12.00 H x 3.50 D"
HEAD_BOTTOM = 46.0  # "head bottom at 46 in (fixture level), top at 58 in"
HEAD_TOP = 58.0
ACRYLIC_T = 0.25  # "1/4 in cast acrylic throughout"

# "Vent: 8 slots 2.00 x 0.125 at 0.75 pitch, centred" — top and bottom panels
VENT_SLOT_COUNT = 8
VENT_SLOT_L = 2.0
VENT_SLOT_W = 0.125
VENT_SLOT_PITCH = 0.75

LOOM_PASS_DIA = 0.75  # "Ø 0.75 loom pass, grommeted" — bottom panel
CORNER_BLOCK = 0.75  # "Corner block | 4 | 0.75 | 0.75"
FACE_SCREW_DIA = 0.135  # "F1–4 … Ø 0.135 c'sunk x4 | M3 flat-head"

# The dial cut diameter is pending calipers. None means: engrave a witness
# circle at the bezel OD and do not cut. Supply a measured value to cut.
DIAL_CUT_DIAMETER: float | None = None
WITNESS_DEPTH = 0.02  # CHOICE: engraving depth for reference marks


# ---------------------------------------------------------------------------
# LED fixture — envelope only
# V1_PHYSICAL_BUILD.md § Mast: "hangs from the head's underside at 46 in,
# cantilevered ~10 in forward to centre over the block"
# ---------------------------------------------------------------------------

FIXTURE_Z = HEAD_BOTTOM  # 46
# The doc says "~10 in forward". That figure came from the section drawing,
# which drew the mast BEHIND the cabinet. The doc also says the tray is
# "notched to clear" the mast, which puts it INSIDE the footprint against the
# rear panel — and that is what is modelled, because it is the stiffer mount
# and the one the notch implies. The cantilever is then whatever the geometry
# says: mast centreline to block centreline. See FIXTURE_CANTILEVER below,
# after the plan positions are known.
FIXTURE_W = 16.0  # CHOICE: spans the 15.625 block, per the section drawing
FIXTURE_D = 8.0  # CHOICE: envelope for two boards on a heatsink
FIXTURE_H = 1.5  # CHOICE
FIXTURE_ARM_W = 1.5  # CHOICE: the arm from the flange boss to the fixture
FIXTURE_ARM_T = 0.5  # CHOICE


# ---------------------------------------------------------------------------
# Derived positions — the height stack the docs publish, computed rather than
# restated, so a test can hold the two against each other.
# ---------------------------------------------------------------------------

TRAY_FLOOR_Z = PLINTH_H  # 24
TRAY_RIM_Z = PLINTH_H + TRAY_UPSTAND  # 26
CMU_UNDERSIDE_Z = TRAY_FLOOR_Z + PAD_H  # 24.75
CMU_TOP_Z = CMU_UNDERSIDE_Z + CMU_H  # 32.375 — docs round to 32.4
MEDIA_SURFACE_Z = CMU_TOP_Z - MEDIA_BELOW_RIM  # 30.875 — docs: 30.9
EMITTER_Z = 31.0  # "Emitter discharge — 31.0 in", just above the media
PANEL_CENTRE_Z = (HEAD_BOTTOM + HEAD_TOP) / 2  # 52 — "read standing"

# Mast plan position: centred on width, against the inside of the rear panel.
MAST_X = 0.0
MAST_Y = PLINTH_D - REAR_PANEL_T - MAST_D / 2

# CMU plan position. Centred on width. In depth it sits FORWARD in the tray,
# behind the tray's front wall by CMU_FRONT_SETBACK — not centred. Centred, its
# back face (10.81 in a 14 in cabinet) runs into a mast whose front face is at
# 10.25. Forward, the block is in front of the column, which is also the
# composition the piece wants: vessel, then mast, then head.
CMU_X = 0.0
CMU_FRONT_SETBACK = 1.0  # CHOICE: from the tray's inside front wall
CMU_Y = CARCASS_T + TRAY_T + CMU_FRONT_SETBACK + CMU_W / 2

# Fixture: centred over the block. Cantilever is derived, not asserted.
FIXTURE_Y = CMU_Y
FIXTURE_CANTILEVER = MAST_Y - CMU_Y  # 4.75 with the mast inside; the doc's ~10
                                     # assumed it outside. See the note above.

# Where the pads meet the block: under the four corners, where a face shell
# meets an end shell and the block is solid all the way down.
PAD_X = CMU_L / 2 - CMU_END_SHELL / 2
PAD_Y_OFFSET = CMU_W / 2 - CMU_FACE_SHELL / 2


@dataclass(frozen=True)
class HeightStack:
    """The published height stack, for comparison against the docs' table."""

    shadow_gap: float = SHADOW_GAP_H
    reservoir_shelf: float = SHELF_H
    water_low: float = WATER_LOW
    water_full: float = WATER_FULL
    tray_floor: float = TRAY_FLOOR_Z
    tray_rim: float = TRAY_RIM_Z
    cmu_underside: float = CMU_UNDERSIDE_Z
    media_surface: float = MEDIA_SURFACE_Z
    emitter: float = EMITTER_Z
    cmu_top: float = CMU_TOP_Z
    fixture: float = FIXTURE_Z
    head_bottom: float = HEAD_BOTTOM
    panel_centre: float = PANEL_CENTRE_Z
    head_top: float = HEAD_TOP

    @property
    def static_lift(self) -> float:
        """Low water line to emitter discharge — the pump's real job."""
        return self.emitter - self.water_low


HEIGHTS = HeightStack()


@dataclass(frozen=True)
class DepthBudget:
    """What the cabinet's depth has to hold, front to back, at the mast's X.

    The reservoir pan and the mast both want the back of the wet bay. This is
    the arithmetic that decides whether they fit, and by how much.
    """

    front_panel: float = CARCASS_T
    front_clearance: float = RESERVOIR_FRONT_CLEARANCE
    reservoir: float = RESERVOIR_W
    mast: float = MAST_D
    rear_panel: float = REAR_PANEL_T
    available: float = PLINTH_D

    @property
    def required(self) -> float:
        return self.front_panel + self.front_clearance + self.reservoir + self.mast + self.rear_panel

    @property
    def slack(self) -> float:
        """Positive: they fit with this much to spare. Negative: they collide by this much."""
        return self.available - self.required


DEPTH = DepthBudget()
