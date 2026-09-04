#!/usr/bin/env python3
"""Turn the station into a self-contained 3D viewer page.

    python cad/viewer.py                       # the form candidates at 36
    python cad/viewer.py --heights 36 40 44    # a height sweep instead
    python cad/viewer.py --variant "Tall frame=PLINTH_H:44,FRAME:1"

The page is one HTML file: every part tessellated and embedded, three.js from
cdnjs, no server. It exists so a layout decision can be looked at from the
positions a person will actually occupy — standing in front of the panel,
leaning over the block — before anyone commits stock to it. Part toggles, a
section cut, the height stack as datums, and the PLINTH_H variants side by
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
    "base_recess": dict(label="Recessed base", colour="#9C7B4E", opacity=1.0, group="fabricated"),
    "base_frame": dict(label="Steel base frame", colour="#3E4247", opacity=1.0, group="fabricated"),
    "fascia": dict(label="Instrument fascia", colour="#2E2C29", opacity=1.0, group="fabricated"),
    "rear_door": dict(label="Rear door (wet bay)", colour="#B8925A", opacity=1.0, group="fabricated"),
    "tray": dict(label="Tray, 304 16 ga", colour="#C4C9CC", opacity=1.0, group="fabricated"),
    "pads": dict(label="Block pads", colour="#8F7A55", opacity=1.0, group="fabricated"),
    "mast": dict(label="Mast, 2 × 3 HSS", colour="#4A4F55", opacity=1.0, group="fabricated"),
    "face": dict(label="Instrument face, acrylic", colour="#9CC3D8", opacity=0.55, group="fabricated"),
    "cmu": dict(label="CMU vessel", colour="#9A9590", opacity=1.0, group="reference"),
    "media": dict(label="Media", colour="#5E4A38", opacity=1.0, group="reference"),
    "reservoir": dict(label="Reservoir pan", colour="#5C8DB3", opacity=0.5, group="reference"),
    "fixture": dict(label="LED fixture + arm", colour="#D9A83E", opacity=0.9, group="reference"),
    "console": dict(label="Console electronics envelope", colour="#6FAE7B", opacity=0.35, group="reference"),
}


# The design pass: the four combinations of the two form knobs, at the
# decided height. Both off is the box as first modelled.
DEFAULT_VARIANTS = [
    ("Box", {}),
    ("Fascia", {"GROWLAB_FASCIA": "1"}),
    ("Frame", {"GROWLAB_FRAME": "1"}),
    ("Fascia + frame", {"GROWLAB_FASCIA": "1", "GROWLAB_FRAME": "1"}),
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
        "label": os.environ.get("GROWLAB_VARIANT_LABEL", f"{P.PLINTH_H:g} in"),
        "form": ("fascia " if P.FASCIA else "") + ("frame" if P.FRAME else "") or "box",
        "plinth_h": P.PLINTH_H,
        "plinth_w": P.PLINTH_W,
        "plinth_d": P.PLINTH_D,
        "panel_centre": P.PANEL_CENTRE_Z,
        "static_lift": P.HEIGHTS.static_lift,
        "top": P.MAST_TOP + P.FIXTURE_ARM_T,
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


def render_html(variants: list[dict]) -> str:
    template = (REPO / "cad" / "viewer_template.html").read_text()
    payload = json.dumps({
        "sha": _git_sha(),
        "materials": MATERIALS,
        "variants": variants,
    })
    return template.replace("/*__STATION_DATA__*/null", payload)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--heights", type=float, nargs="+", help="build a PLINTH_H sweep instead of the form candidates")
    ap.add_argument("--variant", action="append", default=[], metavar="LABEL=KEY:VAL,...",
                    help="an explicit variant, e.g. 'Tall frame=PLINTH_H:44,FRAME:1'; repeatable")
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
