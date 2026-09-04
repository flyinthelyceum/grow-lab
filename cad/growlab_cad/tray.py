"""The drip tray: a formed stainless pan that nests into the carcass top.

"304 stainless … 16 ga … The tray carries water, never weight. Pads rise from
the cabinet rail through cutouts in the tray floor so the block bears on the
carcass."  — V1_PHYSICAL_BUILD.md § Tray and block interface

Modelled as a shell: floor plate plus four upstands, with the four pad cutouts
and the notch at the back for the mast to pass through. The bend radius is
left to the fabricator; the sheet here is square-cornered so the cutouts are
unambiguous.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, labelled


def plan_centre() -> tuple[float, float]:
    return 0.0, P.PLINTH_D / 2


def pad_centres() -> list[tuple[float, float]]:
    """Under the block's four corners, where it is solid all the way down."""
    return [
        (P.CMU_X - P.PAD_X, P.CMU_Y - P.PAD_Y_OFFSET),
        (P.CMU_X + P.PAD_X, P.CMU_Y - P.PAD_Y_OFFSET),
        (P.CMU_X - P.PAD_X, P.CMU_Y + P.PAD_Y_OFFSET),
        (P.CMU_X + P.PAD_X, P.CMU_Y + P.PAD_Y_OFFSET),
    ]


def mast_notch() -> tuple[float, float, float, float]:
    """(x_len, y_len, x_centre, y_centre) of the notch in the tray's back edge."""
    c = P.MAST_NOTCH_CLEARANCE
    x_len = P.MAST_W + 2 * c
    # From the mast's front face (with clearance) to the tray's back wall,
    # plus a little past it so the cut clears the wall entirely.
    y_front = P.MAST_Y - P.MAST_D / 2 - c
    y_back = P.PLINTH_D - P.CARCASS_T + 0.5
    return x_len, y_back - y_front, P.MAST_X, (y_front + y_back) / 2


def build() -> Part:
    cx, cy = plan_centre()
    # Floor sheet plus upstand: the rim must land at TRAY_RIM_Z, flush with the sides.
    outer = box(P.TRAY_W, P.TRAY_D, P.TRAY_UPSTAND + P.TRAY_T, at=(cx, cy, P.TRAY_FLOOR_Z - P.TRAY_T))
    inner = box(
        P.TRAY_W - 2 * P.TRAY_T,
        P.TRAY_D - 2 * P.TRAY_T,
        P.TRAY_UPSTAND + 1.0,
        at=(cx, cy, P.TRAY_FLOOR_Z),
    )
    pan = outer - inner

    # Pad cutouts: the block bears on the carcass, not on this sheet.
    cut = P.PAD_SIZE + 2 * P.PAD_CUTOUT_CLEARANCE
    for px, py in pad_centres():
        pan -= box(cut, cut, P.TRAY_T * 4, at=(px, py, P.TRAY_FLOOR_Z - P.TRAY_T * 2))

    # Notch for the mast, through the floor and the back upstand.
    nx, ny, ncx, ncy = mast_notch()
    pan -= box(nx, ny, P.TRAY_UPSTAND + 2.0, at=(ncx, ncy, P.TRAY_FLOOR_Z - 1.0))

    return labelled(pan, "tray_304_16ga")


def build_pads() -> Part:
    """The four standoffs. They belong to the carcass structurally, but are
    built here because their positions are the tray's cutouts."""
    pads = None
    rail_top = P.TRAY_FLOOR_Z - P.TRAY_T  # the tray floor rests on the rail
    height = P.CMU_UNDERSIDE_Z - rail_top
    for px, py in pad_centres():
        pad = box(P.PAD_SIZE, P.PAD_SIZE, height, at=(px, py, rail_top))
        pads = pad if pads is None else pads + pad
    return labelled(pads, "cmu_pads")
