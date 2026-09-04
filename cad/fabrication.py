#!/usr/bin/env python3
"""The fabrication pack: DXFs to cut from, and a list of what to buy.

    python cad/fabrication.py          # writes cad/out/fab/

Outputs
-------
fab/plate.dxf          the instrument plate, 1/8 aluminium, full hole schedule
fab/case_body.dxf      the case's flat development, 16 ga, with bend lines
fab/fascia.dxf         the clear acrylic band
fab/backplate.dxf      the console backplate
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

from cad.growlab_cad import case, params as P, plinth  # noqa: E402
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
# The instrument plate — 1/8 in aluminium, black.
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


def backplate_flat() -> Sketch:
    bz0, bz1 = plinth._fascia_band()
    return rect(P.INSIDE_X1 - P.INSIDE_X0, bz1 - bz0, (0, 0))


# ---------------------------------------------------------------------------
# The cut list — what to buy and saw, from the same parameters.
# ---------------------------------------------------------------------------

def cutlist() -> dict:
    m = case_metrics()
    fm = fascia_metrics()
    bay_h = P.RAIL_BOTTOM_Z - P.FLOOR_TOP_Z
    frame_leg = P.SHADOW_GAP_H - P.FRAME_TUBE
    ring_x = P.PLINTH_W - 2 * P.FRAME_LEG_INSET
    ring_y = P.PLINTH_D - 2 * P.FRAME_LEG_INSET
    carcass_h = P.TRAY_RIM_Z - P.SHADOW_GAP_H

    return {
        "units": "inches",
        "ply": {
            "stock": f"{P.CARCASS_T} in birch ply",
            "parts": [
                {"part": "Side", "qty": 2, "w": P.PLINTH_D, "h": carcass_h,
                 "note": "chamfer the front vertical corner 0.5; rebate the front "
                         f"{P.FASCIA_POCKET} deep over the band"},
                {"part": "Rear panel", "qty": 1, "w": P.INSIDE_X1 - P.INSIDE_X0, "h": carcass_h,
                 "note": "door opening cut out of it; mast bolt holes"},
                {"part": "Rear door", "qty": 1,
                 "w": (P.DIVIDER_X - P.DIVIDER_T / 2) - P.INSIDE_X0 - 2 * P.DOOR_GAP,
                 "h": bay_h - 2 * P.DOOR_GAP, "note": "wet bay; hinge and catch TBD"},
                {"part": "Floor", "qty": 1, "w": P.INSIDE_X1 - P.INSIDE_X0,
                 "h": P.REAR_INSIDE_Y - P.CARCASS_T, "note": "mast passes through to the frame"},
                {"part": "Front panel", "qty": 1, "w": P.INSIDE_X1 - P.INSIDE_X0,
                 "h": P.RAIL_BOTTOM_Z - P.SHADOW_GAP_H,
                 "note": f"rebate {P.FASCIA_POCKET} deep over the band; through-opening "
                         f"below the {P.FASCIA_TOP_LIP} header"},
                {"part": "Console partition", "qty": 1,
                 "w": (P.DIVIDER_X - P.DIVIDER_T / 2) - P.INSIDE_X0, "h": bay_h,
                 "note": f"{P.CONSOLE_PARTITION_T} stock"},
                {"part": "Bay divider", "qty": 1, "w": P.REAR_INSIDE_Y - P.PARTITION_Y0,
                 "h": bay_h, "note": f"{P.DIVIDER_T} stock; grommeted line pass"},
                {"part": "Console ledge", "qty": 1, "w": P.INSIDE_X1 - P.INSIDE_X0,
                 "h": P.CONSOLE_Y1 - P.LEDGE_CHASE - P.FASCIA_POCKET,
                 "note": "carries the case; fascia's bottom row screws into it"},
                {"part": "Reservoir shelf", "qty": 1,
                 "w": (P.DIVIDER_X - P.DIVIDER_T / 2) - P.INSIDE_X0,
                 "h": P.REAR_INSIDE_Y - P.PARTITION_Y1, "note": "on slotted cleats"},
                {"part": "Top rail, front/back", "qty": 2, "w": P.INSIDE_X1 - P.INSIDE_X0,
                 "h": P.CARCASS_T, "note": "back member notched for the mast"},
                {"part": "Top rail, sides", "qty": 2, "w": P.REAR_INSIDE_Y - P.CARCASS_T,
                 "h": P.CARCASS_T, "note": ""},
                {"part": "Top rail, cross", "qty": 2, "w": P.REAR_INSIDE_Y - P.CARCASS_T,
                 "h": P.CARCASS_T, "note": "under the block's pads"},
            ],
        },
        "steel": {
            "stock": f"{P.FRAME_TUBE} x {P.FRAME_TUBE} HSS or solid bar; "
                     f"{P.MAST_W} x {P.MAST_D} HSS for the mast",
            "parts": [
                {"part": "Frame leg", "qty": 4, "length": frame_leg,
                 "note": "levelling feet in the ends"},
                {"part": "Frame ring, left/right", "qty": 2, "length": ring_y, "note": ""},
                {"part": "Frame ring, front/back", "qty": 2, "length": ring_x,
                 "note": "back member notched for the mast"},
                {"part": "Mast", "qty": 1, "length": P.MAST_TOP,
                 "note": "floor to cap; side line pass; 4 rear bolt holes"},
                {"part": "Mast cap", "qty": 1, "length": P.MAST_D,
                 "note": f"{P.MAST_CAP_T} plate, {P.MAST_W} x {P.MAST_D}, welded"},
                {"part": "Fixture arm, forward", "qty": 1,
                 "length": (P.MAST_Y + P.MAST_D / 2) - (P.FIXTURE_Y + P.FIXTURE_D / 2 - P.FIXTURE_BAR_D),
                 "note": f"{P.FIXTURE_ARM_W} x {P.FIXTURE_ARM_T} flat, welded to the cap"},
                {"part": "Fixture arm, cross bar", "qty": 1, "length": P.FIXTURE_W,
                 "note": "along the fixture's back edge; spans the mast's offset"},
            ],
        },
        "sheet": [
            {"part": "Instrument plate", "material": f"{P.PLATE_T} aluminium, black",
             "blank": [FACE_WIDTH, FACE_HEIGHT], "file": "plate.dxf"},
            {"part": "Instrument case body", "material": "16 ga aluminium, black",
             "blank": [m["blank_w"], m["blank_h"]], "file": "case_body.dxf",
             "note": "6 bends; see the drawing"},
            {"part": "Console backplate", "material": f"{P.BACKPLATE_T} sheet, black",
             "blank": [P.INSIDE_X1 - P.INSIDE_X0, plinth._fascia_band()[1] - plinth._fascia_band()[0]],
             "file": "backplate.dxf"},
            {"part": "Fascia", "material": f"{P.FASCIA_T} clear cast acrylic",
             "blank": [fm["w"], fm["h"]], "file": "fascia.dxf",
             "note": "cast, not extruded"},
            {"part": "Tray", "material": "304 stainless, 16 ga",
             "blank": [P.TRAY_W - 2 * P.TRAY_T + 2 * P.TRAY_UPSTAND,
                       P.TRAY_D - 2 * P.TRAY_T + 2 * P.TRAY_UPSTAND],
             "file": "(from the STEP)",
             "note": "formed pan; blank is nominal, the shop develops it. Pad cutouts "
                     "and the mast notch are in the STEP."},
        ],
        "pending": [
            "Dial cut diameter — the plate ships with scribe rings only until the "
            "Weston 301 bezels are calipered.",
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
            "| Part | Qty | W | H | Note |", "|---|---:|---:|---:|---|"]
    for r in data["ply"]["parts"]:
        out.append(f"| {r['part']} | {r['qty']} | {r['w']:.3f} | {r['h']:.3f} | {r['note']} |")

    out += ["", "## Steel — " + data["steel"]["stock"], "",
            "| Part | Qty | Length | Note |", "|---|---:|---:|---|"]
    for r in data["steel"]["parts"]:
        out.append(f"| {r['part']} | {r['qty']} | {r['length']:.3f} | {r['note']} |")

    out += ["", "## Sheet and glazing", "",
            "| Part | Material | Blank | File | Note |", "|---|---|---|---|---|"]
    for r in data["sheet"]:
        out.append(f"| {r['part']} | {r['material']} | {r['blank'][0]:.3f} × {r['blank'][1]:.3f} "
                   f"| {r['file']} | {r.get('note', '')} |")

    out += ["", "## Not on this list — measure first", ""]
    out += [f"- {p}" for p in data["pending"]]
    return "\n".join(out) + "\n"


PACK_README = """# fab/ — the pack you cut from

Generated by `python cad/fabrication.py` from the same parameters as the solid
model. If a number here disagrees with the STEP, the STEP is stale — rebuild.

| File | What |
|---|---|
| `plate.dxf` | Instrument plate, {plate_t} aluminium. Hole schedule from `panel_geometry.py`. |
| `case_body.dxf` | Case body flat, 16 ga. Blank {cbw:.3f} × {cbh:.3f}, six bends. |
| `fascia.dxf` | Clear cast acrylic band, {fascia_t}. Two knob holes, ten fixings. |
| `backplate.dxf` | Console backplate, {bp_t} sheet. |
| `cutlist.md` | Ply, steel, sheet and glazing, with quantities. |

**Units: inches, 1:1.** The exporter tags the unit but does not convert, so
these are authored in inches directly; a test reads the files back and checks
both the tag and a coordinate.

**Layers.** `cut` — profile and holes. `bend` — fold lines, do not cut.
`mark` — scribe only.

**Bends** are drawn at the theoretical fold with no bend allowance; the
K-factor is the shop's. The blank is the sum of the flat faces.

**The dials are not cut.** The plate carries scribe rings at the bezel OD and
nothing else, until the Weston 301s are measured. Set
`params.DIAL_CUT_DIAMETER` and regenerate; the rings become holes.

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

    data = cutlist()
    (args.out / "cutlist.json").write_text(json.dumps(data, indent=2))
    (args.out / "cutlist.md").write_text(cutlist_markdown(data))

    m = case_metrics()
    (args.out / "README.md").write_text(PACK_README.format(
        plate_t=P.PLATE_T, fascia_t=P.FASCIA_T, bp_t=P.BACKPLATE_T,
        cbw=m["blank_w"], cbh=m["blank_h"],
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
