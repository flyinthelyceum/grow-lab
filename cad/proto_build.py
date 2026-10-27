#!/usr/bin/env python3
"""The P1 prototype's pack: what to cut, print, bend and buy.

    python cad/proto_build.py          # writes cad/out/proto/

Outputs
-------
proto/p1.step              every part in place, for Fusion and for looking at
proto/beam_top.dxf         the oak beam, setup 1, top up: the two bar pockets
proto/beam_bottom.dxf      setup 2, flipped end for end: the two light channels
proto/beam.step            the beam on its own, top face up, for CAM
proto/hub.stl              printed PETG, matte white, printed top face down
proto/pads.stl             four printed pads under the planter
proto/face_template.dxf    laser-cut: lay it on the instrument block's face to
                           mark the coring -- pilot holes cut, circles scribed
proto/plate.dxf            plasma: the ground plate
proto/cap_*.dxf            laser-cut: the four tunnel caps
proto/bend_sheet.md        the marks for the crook
proto/README.md            what each file is

DXFs are inches 1:1, layers ``cut``, ``pocket_<depth>`` (from the up face) and
``mark`` (scribe or etch, never through), as in the V1 pack.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from build123d import Circle, Line, Pos, Rectangle, RectangleRounded, Sketch, Unit  # noqa: E402
from build123d.exporters import ExportDXF, LineType  # noqa: E402

from cad.growlab_cad import proto as Q  # noqa: E402
from components import lm301h_heatsink_module as HS  # noqa: E402

OUT = REPO / "cad" / "out" / "proto"


def rect(w: float, h: float, at: tuple[float, float]) -> Sketch:
    """A rectangle by its bottom-left corner."""
    return Pos(at[0] + w / 2, at[1] + h / 2) * Rectangle(w, h)


def write(path: Path, layers: dict[str, list]) -> None:
    ex = ExportDXF(unit=Unit.IN, line_weight=0.35)
    for name, shapes in layers.items():
        if name == "mark":
            ex.add_layer(name, line_type=LineType.ISO_DOT, line_weight=0.18)
        else:
            ex.add_layer(name, line_weight=0.5 if name == "cut" else 0.25)
        for sh in shapes:
            ex.add_shape(sh, layer=name)
    ex.write(str(path))


# ---------------------------------------------------------------------------
# The beam, from a 17 x 4.9 x 2.25 white oak blank (10/4 stock, or two 5/4
# glued). Origin at the blank's corner; the bars run along x.
# ---------------------------------------------------------------------------

def beam_blank() -> tuple[float, float, float]:
    x0, x1, y0, y1, z0, z1 = Q.beam_box()
    return x1 - x0, y1 - y0, z1 - z0


def bar_pockets() -> list[tuple[float, float, float, float]]:
    """(x0, x1, y0, y1) of each bar's pocket, blank coordinates."""
    bl, bw, _ = beam_blank()
    pl = HS.LENGTH + 2 * Q.BAR_CLEAR
    pw = HS.WIDTH + 2 * Q.BAR_CLEAR
    out = []
    for s in (-1, 1):
        yc = bw / 2 + s * (Q.BEAM_SPINE / 2 + pw / 2)
        out.append(((bl - pl) / 2, (bl + pl) / 2, yc - pw / 2, yc + pw / 2))
    return out


def beam_top() -> dict[str, list]:
    """Setup 1, top face up: the bar pockets, the bars' own depth, and the
    hub's four screw pilots in the rails."""
    bl, bw, _ = beam_blank()
    body = rect(bl, bw, (0, 0))
    pockets = [rect(x1 - x0, y1 - y0, (x0, y0)) for x0, x1, y0, y1 in bar_pockets()]
    x0, _, y0, *_ = Q.beam_box()
    pilots = [Pos(x - x0, y - y0) * Circle(0.1) for x, y in Q.hub_screws()]
    body -= Pos(bl / 2, bw / 2) * Circle(Q.WIRE_HOLE / 2)
    return {"cut": [body], f"pocket_{HS.HEIGHT:.3f}": pockets, f"pocket_{0.5:.3f}": pilots}


def beam_bottom() -> dict[str, list]:
    """Setup 2, flipped end for end about x (so y is mirrored): the two light
    channels, inside a ledge all round, up to the pockets' floor. The spine
    and the rails stay full height."""
    bl, bw, bh = beam_blank()
    body = rect(bl, bw, (0, 0))
    chans = []
    for x0, x1, y0, y1 in bar_pockets():
        y0m, y1m = bw - y1, bw - y0
        chans.append(rect(x1 - x0 - 2 * Q.LEDGE, y1m - y0m - 2 * Q.LEDGE,
                          (x0 + Q.LEDGE, y0m + Q.LEDGE)))
    body -= Pos(bl / 2, bw / 2) * Circle(Q.WIRE_HOLE / 2)
    return {"cut": [body], f"pocket_{bh - HS.HEIGHT:.3f}": chans}


def beam_step():
    """The beam on its own, top face up, corner at the origin, millimetres."""
    from cad.growlab_cad._shapes import bbox_in, location_in

    beam = Q.build_beam()
    bb = bbox_in(beam)
    return location_in(-bb["x0"], -bb["y0"], -bb["z0"]) * beam


# ---------------------------------------------------------------------------
# The coring template: the instrument block's face, 1:1. Lay it on the face,
# square to the edges, and drill the pilots through it.
# ---------------------------------------------------------------------------

def face_template() -> dict[str, list]:
    x0, x1, _, _, z0, z1 = Q.instrument_box()
    w, h = x1 - x0, z1 - z0
    body = rect(w, h, (0, 0))
    marks = []
    # The dials: a 1/4 pilot for the core bit's centre drill, the hole scribed.
    for x, z in Q.dial_centres():
        body -= Pos(x - x0, z - z0) * Circle(0.125)
        marks.extend((Pos(x - x0, z - z0) * Circle(Q.DIAL_HOLE / 2)).edges())
        marks.extend((Pos(x - x0, z - z0) * Circle(Q.DIAL_FLANGE / 2)).edges())
    # The window: cut out, so it can be traced, with a pilot for the 1/2 bit
    # at each corner, which is what rounds them.
    wx0, wx1, wz0, wz1 = Q.window_rect()
    body -= Pos((wx0 + wx1) / 2 - x0, (wz0 + wz1) / 2 - z0) * RectangleRounded(
        wx1 - wx0, wz1 - wz0, Q.WINDOW_CORNER)
    # Where the tunnels and the web are, so the template can be checked
    # against the block's own side before anything is drilled.
    for name, (t0, t1) in Q.tunnels().items():
        for zz in (t0, t1):
            marks.append(Line((0, zz - z0), (w, zz - z0)))
    return {"cut": [body], "mark": marks}


# ---------------------------------------------------------------------------
# The ground plate, plasma. Origin at the plate's own bottom-left.
# ---------------------------------------------------------------------------

def plate() -> dict[str, list]:
    rects = Q.plate_outline()
    xs = [r[0] for r in rects]
    ys = [r[2] for r in rects]
    ox, oy = min(xs), min(ys)
    body = None
    for x0, x1, y0, y1 in rects:
        r = rect(x1 - x0, y1 - y0, (x0 - ox, y0 - oy))
        body = r if body is None else body + r
    bx, by = Q.plate_bolt()
    body -= Pos(bx - ox, by - oy) * Circle(0.40 / 2)
    return {"cut": [body]}


# ---------------------------------------------------------------------------
# The four tunnel caps, 3 mm matte white acrylic, laser. Each fills one end of
# one tunnel; drawn as seen from outside the block.
# ---------------------------------------------------------------------------

CAP_CLEAR = 0.03  # a side: real cores are tapered and rough -- fit, then re-cut
VENT_W, VENT_L = 0.125, 2.5


def caps() -> dict[str, dict[str, list]]:
    y0, y1 = Q.tunnel_y()
    out = {}
    for tunnel, (z0, z1) in Q.tunnels().items():
        w, h = (y1 - y0) - 2 * CAP_CLEAR, (z1 - z0) - 2 * CAP_CLEAR
        for side in ("left", "right"):
            body = rect(w, h, (0, 0))
            # Vents: a column of slots, so the stack breathes side to side.
            n = 6
            for i in range(n):
                vz = h * (i + 1) / (n + 1)
                body -= Pos(w / 2, vz) * RectangleRounded(VENT_L, VENT_W, VENT_W / 2 - 1e-3)
            if side == "right" and tunnel == "lower":
                # The crook's first bend sweeps out through this opening; the
                # notch is where the arc crosses the cap's plane. Drawn from
                # outside, the block's front is on the left.
                zb, zt = Q.stub_exit()
                u = (Q.crook_y() - y0) - CAP_CLEAR
                body -= rect(Q.EMT_OD + 0.1, (zt - zb) + 0.1,
                             (u - (Q.EMT_OD + 0.1) / 2, zb - z0 - CAP_CLEAR - 0.05))
            if side == "left" and tunnel == "lower":
                # The power cord and the floor-run leads leave here.
                body -= Pos(w - 0.75, 0.75) * Circle(0.4)
            out[f"cap_{tunnel}_{side}"] = {"cut": [body]}
    return out


# ---------------------------------------------------------------------------

def bend_sheet_md() -> str:
    rows = Q.bend_sheet()
    s = Q.stability()
    lines = [
        "# P1 crook: bend sheet", "",
        f"3/4 EMT, one 10 ft stick. Bender take-up **{Q.TAKE_UP} in** (read your shoe; "
        f"if it differs, change `TAKE_UP` and re-run). Centreline radius "
        f"{Q.bend_radius():.2f}. All three bends in **one plane, the same direction** "
        "-- lay it on the floor between bends to check it does not dog-leg.", "",
        "Every distance is to the **back** of a bend: the outside of the pipe, which is "
        "what a tape reads.", "",
        "| Step | Bend | Measure from | Mark at | Bender |",
        "|---:|---|---|---:|---|",
    ]
    for r in rows:
        lines.append(f"| {r['step']} | {r['bend']} | {r['from']} | **{r['mark']:.2f}** | {r['use']} |")
    lines += [
        "",
        f"Pipe used: {Q.developed_length():.1f} in of the {Q.STICK:.0f}. Bend the crook from one "
        f"end; the {Q.STICK - Q.developed_length():.0f} in left is enough to practise the stub "
        "and a back-to-back first, on the same stick. Ream the cut end.",
        f"Total bend {Q.total_bend():.0f}° between pull points (NEC allows 360).",
        "",
        "## What it holds up",
        f"Light: about {Q.light_weight():.1f} lb. Free-standing, the instrument block tips at "
        f"**{s['shove_lb']:.1f} lb** of side push at the beam (safety factor {s['factor']:.1f} "
        "at rest). On the ground plate, bolted, it does not: the light hangs inside the "
        "plate's footprint.",
    ]
    return "\n".join(lines) + "\n"


README = """# proto/ -- the P1 pack

Generated by `python cad/proto_build.py` from `cad/growlab_cad/proto.py`. See
`docs/P1_PROTOTYPE.md` for the design and the build order.

| File | Make it on | What |
|---|---|---|
| `bend_sheet.md` | hand bender | the crook's three bends and its cut |
| `beam_top.dxf`, `beam_bottom.dxf`, `beam.step` | CNC router | white oak beam, two setups |
| `hub.stl`, `pads.stl` | printer | matte white PETG, no supports |
| `face_template.dxf` | CO2 laser, 1/8 ply or acrylic | marks the coring on the block |
| `cap_*.dxf` | CO2 laser, 3 mm white acrylic | the four tunnel caps |
| `plate.dxf` | CNC plasma, 1/4 steel | the ground plate; countersink the bolt hole underneath |
| `p1.step` | -- | everything in place |

**Measure before coring.** The block's shells and web are typical figures, not
this block's. Hold the template against the block's side and check its
tunnel lines land on the real web before a single hole is drilled.
"""


def main(argv: list[str] | None = None) -> int:
    from build123d import Compound, export_step, export_stl

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    parts = Q.build()
    export_step(Compound(label="growlab_p1", children=list(parts.values())), str(out / "p1.step"))
    export_step(beam_step(), str(out / "beam.step"))
    write(out / "beam_top.dxf", beam_top())
    write(out / "beam_bottom.dxf", beam_bottom())

    from build123d import Rot

    from cad.growlab_cad._shapes import bbox_in, location_in

    for name, part in (("hub", parts["hub"]), ("pads", parts["pads"])):
        if name == "hub":
            part = Rot(180, 0, 0) * part  # top face down: the cavity opens upward
        bb = bbox_in(part)
        part = location_in(-(bb["x0"] + bb["x1"]) / 2, -(bb["y0"] + bb["y1"]) / 2, -bb["z0"]) * part
        export_stl(part, str(out / f"{name}.stl"))

    write(out / "face_template.dxf", face_template())
    write(out / "plate.dxf", plate())
    for name, layers in caps().items():
        write(out / f"{name}.dxf", layers)
    (out / "bend_sheet.md").write_text(bend_sheet_md())
    (out / "README.md").write_text(README)

    for f in sorted(out.iterdir()):
        print(f"wrote {f.relative_to(REPO) if f.is_relative_to(REPO) else f}")
    print()
    print(bend_sheet_md())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
