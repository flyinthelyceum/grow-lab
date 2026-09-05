#!/usr/bin/env python3
"""Turn the station into a self-contained 3D viewer page.

    python cad/viewer.py                       # the design at 36
    python cad/viewer.py --heights 36 40 44    # a height sweep instead
    python cad/viewer.py --variant "Tall=PLINTH_H:44"

The page is one HTML file: every part tessellated and embedded, three.js from
cdnjs, no server. It exists so a layout decision can be looked at from the
positions a person will actually occupy — standing in front of the panel,
leaning over the block — before anyone commits stock to it. Part toggles, a
section cut, the height stack as datums, and any PLINTH_H variants side by
side.

Each variant is built in a subprocess with its ``GROWLAB_*`` knobs set, so
the kernel sees a clean ``params`` module every time.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from array import array
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT = REPO / "cad" / "out"

# Material and role for each part, keyed by the assembly's part names.
# Colours are the materials': ply, stainless, steel, acrylic, concrete.
MATERIALS = {
    "plinth": dict(label="Cabinet carcass", colour="#C9A46A", opacity=1.0, group="fabricated"),
    "base_frame": dict(label="Steel base frame, white DTM", colour="#D8DBD7", opacity=1.0, group="fabricated"),
    "fascia": dict(label="Fascia, clear acrylic", colour="#BFD9E8", opacity=0.28, group="fabricated"),
    "case": dict(label="Instrument case, white aluminium", colour="#E9EBE8", opacity=1.0, group="fabricated"),
    "backplate": dict(label="Console backplate, white", colour="#DCDFDB", opacity=1.0, group="fabricated"),
    "rear_door": dict(label="Rear door (wet bay)", colour="#B8925A", opacity=1.0, group="fabricated"),
    "tray": dict(label="Tray, 304 16 ga", colour="#C4C9CC", opacity=1.0, group="fabricated"),
    "pads": dict(label="Block pads", colour="#8F7A55", opacity=1.0, group="fabricated"),
    # Every steel and aluminium part in the piece is white now — the frame, the
    # mast, the head, the case and the backplate. Not paper white: painted metal
    # under room light reads a shade cooler and darker than paper, and the five
    # are separated by a few points of value so a flat-shaded render still tells
    # them apart. The ply body is the other register and is unchanged.
    "mast": dict(label="Mast, Ø1.5 tube, white DTM", colour="#EDEEEC", opacity=1.0, group="fabricated"),
    "canopy_carriage": dict(label="Canopy carriage + arm, white DTM", colour="#E4E6E3", opacity=1.0, group="fabricated"),
    "cmu": dict(label="CMU vessel", colour="#9A9590", opacity=1.0, group="reference"),
    "reservoir": dict(label="Reservoir pan", colour="#5C8DB3", opacity=0.5, group="reference"),
    "fixture": dict(label="LED fixture", colour="#D9A83E", opacity=0.9, group="reference"),
}


# What is worth flipping between. This used to be the form candidates — fascia
# vs box, frame vs plinth — and the subtract pass removed those flags once the
# design was decided, leaving the toggle with one entry and nothing to do. The
# canopy travel replaced them: the head rides a clamp collar now, so the
# interesting question is what the piece looks like at each end of its 21 in.
DEFAULT_VARIANTS = [
    ("Parked — light 12 in over the media", {"GROWLAB_FIXTURE_ABOVE_MEDIA": "12"}),
    ("Mid travel — 22.5 in", {"GROWLAB_FIXTURE_ABOVE_MEDIA": "22.5"}),
    ("Full lift — 33 in, clears a mature plant", {"GROWLAB_FIXTURE_ABOVE_MEDIA": "33"}),
]


def _dump(out_path: Path, tolerance_mm: float, angular: float) -> None:
    """Child process: build the station at the current params and write meshes."""
    from cad.growlab_cad import assembly, params as P
    from cad.growlab_cad.params import IN

    parts = {**assembly.fabricated(), **assembly.reference()}
    meshes = {}
    for name, part in parts.items():
        verts, tris = part.tessellate(tolerance_mm, angular)
        # array() streams from the generators; no intermediate tuple of every
        # coordinate. The page reads little-endian Float32 / Uint32.
        pos = array("f", (c / IN for v in verts for c in (v.X, v.Y, v.Z)))
        idx = array("I", (i for t in tris for i in t))
        if sys.byteorder == "big":
            pos.byteswap()
            idx.byteswap()
        meshes[name] = {
            "positions": base64.b64encode(pos.tobytes()).decode(),
            "indices": base64.b64encode(idx.tobytes()).decode(),
            "triangles": len(tris),
        }

    heights = vars(P.HEIGHTS)
    variant = {
        "label": os.environ.get("GROWLAB_VARIANT_LABEL", f"light {P.FIXTURE_ABOVE_MEDIA:g} in over media"),
        "plinth_h": P.PLINTH_H,
        "plinth_w": P.PLINTH_W,
        "plinth_d": P.PLINTH_D,
        "panel_centre": P.PANEL_CENTRE_Z,
        "static_lift": P.HEIGHTS.static_lift,
        "top": P.MAST_TOP,  # the cap is the highest thing; the arm rides below it
        "heights": heights,
        "face": {"x0": P.FACE_X0, "z0": P.FACE_Z0, "z1": P.FACE_Z1},
        "meshes": meshes,
    }
    out_path.write_text(json.dumps(variant))


def build_variants(specs: list[tuple[str, dict]], tolerance_mm: float, angular: float) -> list[dict]:
    variants = []
    for n, (label, knobs) in enumerate(specs):
        tmp = OUT / f"_variant_{n}.json"
        env = {**os.environ, **knobs, "GROWLAB_VARIANT_LABEL": label}
        subprocess.run(
            [sys.executable, __file__, "--dump", str(tmp), "--tolerance", str(tolerance_mm), "--angular", str(angular)],
            env=env, check=True, cwd=str(REPO),
        )
        variants.append(json.loads(tmp.read_text()))
        tmp.unlink()
        tris = sum(m["triangles"] for m in variants[-1]["meshes"].values())
        print(f"{label} ({' '.join(f'{k}={v}' for k, v in knobs.items()) or 'defaults'}): {tris} triangles")
    return variants


def _parse_variant(spec: str) -> tuple[str, dict]:
    """'Label=KEY:VAL,KEY:VAL' → (label, {GROWLAB_KEY: VAL, …})."""
    label, _, knobs = spec.partition("=")
    env = {}
    for kv in filter(None, knobs.split(",")):
        k, _, v = kv.partition(":")
        env[f"GROWLAB_{k.strip().upper()}"] = v.strip()
    return label.strip(), env


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:
        return "unknown"


THREE_URL = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
THREE_CACHE = OUT / "_three.min.js"
THREE_TAG = f'<script src="{THREE_URL}"></script>'


def _three_js() -> str | None:
    """three.js source, cached beside the output. None if it cannot be had.

    The viewer is advertised as one file you can open in a browser with nothing
    installed. It was not: it pulled three.js from a CDN, so offline — on a
    plane, at a bench with no wifi, from the CI artifact — it opened as a blank
    page with two console errors and no canvas. Inlining it costs ~600 KB and
    makes the claim true.
    """
    if THREE_CACHE.exists():
        return THREE_CACHE.read_text()
    try:
        import urllib.request

        with urllib.request.urlopen(THREE_URL, timeout=30) as r:
            src = r.read().decode()
        THREE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        THREE_CACHE.write_text(src)
        return src
    except Exception as exc:  # noqa: BLE001 — falling back is the point
        print(f"could not fetch three.js ({exc}); falling back to the CDN tag, "
              "which means this file needs a network to open")
        return None


def render_html(variants: list[dict]) -> str:
    template = (REPO / "cad" / "viewer_template.html").read_text()
    payload = json.dumps({
        "sha": _git_sha(),
        "materials": MATERIALS,
        "variants": variants,
    })
    html = template.replace("/*__STATION_DATA__*/null", payload)
    src = _three_js()
    if src is not None:
        assert THREE_TAG in html, "the three.js script tag moved; inlining would silently no-op"
        html = html.replace(THREE_TAG, f"<script>{src}</script>")
    return html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--heights", type=float, nargs="+", help="build a PLINTH_H sweep instead of the single design")
    ap.add_argument("--variant", action="append", default=[], metavar="LABEL=KEY:VAL,...",
                    help="an explicit variant, e.g. 'Tall=PLINTH_H:44'; repeatable")
    ap.add_argument("--tolerance", type=float, default=0.6, help="tessellation tolerance, mm")
    ap.add_argument("--angular", type=float, default=0.35, help="angular tolerance, radians")
    ap.add_argument("--dump", type=Path, help=argparse.SUPPRESS)
    ap.add_argument("--out", type=Path, default=OUT / "viewer.html")
    args = ap.parse_args(argv)

    if args.dump:
        _dump(args.dump, args.tolerance, args.angular)
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    if args.variant:
        specs = [_parse_variant(v) for v in args.variant]
    elif args.heights:
        specs = [(f"{h:g} in", {"GROWLAB_PLINTH_H": f"{h:g}"}) for h in args.heights]
    else:
        specs = DEFAULT_VARIANTS
    variants = build_variants(specs, args.tolerance, args.angular)
    html = render_html(variants)
    args.out.write_text(html)
    print(f"wrote {args.out.relative_to(REPO) if args.out.is_relative_to(REPO) else args.out}  ({len(html) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
