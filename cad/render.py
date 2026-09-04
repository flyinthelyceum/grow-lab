#!/usr/bin/env python3
"""Elevations of the station as SVG — front, side and plan.

    python cad/render.py          # writes cad/out/elevation_*.svg

Hidden lines are dashed and grey, visible lines solid. The front elevation
also carries the height stack from ``params.HEIGHTS`` as labelled datum lines,
so the drawing states the numbers the docs state and a reader can check one
against the other by eye.

These are for looking at, not for fabricating from: the STEP is the
fabrication source. But a plan view is the fastest way to see that the
pan, the console bay and the rear door all fit in the depth.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from build123d import Compound, ExportSVG, LineType, Unit  # noqa: E402

from cad.growlab_cad import assembly, params as P  # noqa: E402
from cad.growlab_cad.params import IN  # noqa: E402

OUT = REPO / "cad" / "out"

# Each view: name, where the camera sits (mm), which way is up, what it looks at.
# Distances are large so the projection is effectively orthographic.
FAR = 5000.0
_ZC = P.MAST_TOP / 2 * IN
_YC = P.PLINTH_D / 2 * IN
VIEWS = {
    "front": dict(viewport_origin=(0, -FAR, _ZC), viewport_up=(0, 0, 1), look_at=(0, 0, _ZC)),
    "side": dict(viewport_origin=(FAR, _YC, _ZC), viewport_up=(0, 0, 1), look_at=(0, _YC, _ZC)),
    "plan": dict(viewport_origin=(0, _YC, FAR), viewport_up=(0, 1, 0), look_at=(0, _YC, 0)),
}

# Datum lines on the front elevation, in inches. Labelled as the docs label them.
DATUMS = [
    ("floor", 0.0),
    ("shadow gap", P.HEIGHTS.shadow_gap),
    ("face bottom", P.HEIGHTS.face_bottom),
    ("reservoir shelf", P.HEIGHTS.reservoir_shelf),
    ("panel centre", P.HEIGHTS.panel_centre),
    ("water low", P.HEIGHTS.water_low),
    ("face top", P.HEIGHTS.face_top),
    ("tray floor", P.HEIGHTS.tray_floor),
    ("tray rim", P.HEIGHTS.tray_rim),
    ("emitters", P.HEIGHTS.emitter),
    ("CMU top", P.HEIGHTS.cmu_top),
    ("fixture", P.HEIGHTS.fixture),
    ("mast top", P.HEIGHTS.mast_top),
]


def _compound() -> Compound:
    parts = {**assembly.fabricated(), **assembly.reference()}
    return Compound(children=list(parts.values()))


def _export(comp: Compound, name: str, path: Path) -> None:
    visible, hidden = comp.project_to_viewport(**VIEWS[name])
    # The geometry is in mm; ExportSVG labels the document, it does not convert.
    svg = ExportSVG(unit=Unit.MM, scale=1.0, line_weight=0.35)
    svg.add_layer("hidden", line_type=LineType.ISO_DASH, line_weight=0.15, line_color=(160, 160, 160))
    svg.add_layer("visible", line_weight=0.5, line_color=(25, 25, 25))
    svg.add_shape(hidden, layer="hidden")
    svg.add_shape(visible, layer="visible")
    svg.write(str(path))


def _add_datums(path: Path) -> None:
    """Inject labelled datum lines into the front elevation.

    ExportSVG writes the drawing in inches, Y down, with a viewBox that fits
    the geometry. Read the viewBox back, then draw each datum as a full-width
    line at its height with a small label at the left margin.
    """
    text = path.read_text()
    import re

    m = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', text)
    if not m:
        return
    vx, vy, vw, vh = map(float, m.groups())

    # Coordinates are mm. The projection centres the view on its look_at
    # point and the drawing group is Y-flipped, so in viewBox space the floor
    # (world Z = 0) is the bottom edge of the box and heights go up from there.
    floor_y = vy + vh
    margin = 82.0  # mm, room for the labels at the left
    pad = 15.0
    new_vb = f'viewBox="{vx - margin} {vy - pad} {vw + margin} {vh + 2 * pad}"'
    text = text.replace(m.group(0), new_vb, 1)
    # Keep the page the same physical size as the box.
    text = re.sub(r'width="[^"]*" height="[^"]*"',
                  f'width="{vw + margin:.1f}mm" height="{vh + 2 * pad:.1f}mm"', text, count=1)

    lines = ['<g id="datums" font-family="ui-monospace, Menlo, monospace" font-size="7.5">']
    prev_z = None
    for label, z in sorted(DATUMS, key=lambda d: d[1]):
        y = floor_y - z * IN
        lines.append(
            f'<line x1="{vx - margin + 2:.1f}" y1="{y:.1f}" x2="{vx + vw:.1f}" y2="{y:.1f}" '
            f'stroke="#c8871f" stroke-width="0.9" stroke-dasharray="6 4" opacity="0.85"/>'
        )
        # Two datums within half an inch of each other: label the upper one
        # above its line and the lower one below, so neither hides the other.
        below = prev_z is not None and z - prev_z < 0.5
        ty = y + 8.5 if below else y - 2.2
        lines.append(
            f'<text x="{vx - margin + 3:.1f}" y="{ty:.1f}" fill="#8a5a10">{label} · {z:g} in</text>'
        )
        prev_z = z
    lines.append("</g>")
    text = text.replace("</svg>", "\n".join(lines) + "\n</svg>", 1)
    path.write_text(text)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    comp = _compound()
    for name in VIEWS:
        path = OUT / f"elevation_{name}.svg"
        _export(comp, name, path)
        if name == "front":
            _add_datums(path)
        print(f"wrote {path.relative_to(REPO)}  ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
