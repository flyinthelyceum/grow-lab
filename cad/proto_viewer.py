#!/usr/bin/env python3
"""Turn the P1 prototype into a self-contained 3D viewer page.

    python cad/proto_viewer.py            # → cad/out/proto_viewer.html

One HTML file: every P1 part tessellated and embedded, three.js inlined, no
server and no network. The station viewer (``cad/viewer.py``) and the sensor
case viewer each answer their own object's questions; P1's are different again,
so it is its own page rather than a variant of either:

**Where does the light hang?** The telescope is the one moving part. The page's
height slider moves everything that rides on the 1/2 EMT -- beam, bars, hub,
lid, inner tube, bushing -- through the 12 in of travel, and reads out what the
model holds it to at every height: the tube still in the drop, the hub clear of
the coupling.

**What does the camera see?** One view puts the eye where the Camera Module 3
sits in the beam's end, tilted as it is, at its horizontal field of view. Move
the light and look again.

**How does it photograph?** The portfolio view is a standing three-quarter
from the front, and the crook can be shown in a few DTM colours, because the
paint is the decision nobody can make from a STEP file.

Everything the page shows is computed here from ``proto.py``, so the viewer
cannot drift from the part. Inches throughout.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import subprocess
import sys
from array import array
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT = REPO / "cad" / "out"

# Every part ``proto.build()`` makes, and nothing else: the test holds the two
# to each other, so a part added to the model cannot quietly go missing here.
# ``rides`` is the telescope: the parts that move when the light is raised.
PARTS = {
    "planter": dict(label="Planter block", colour="#A6A39C", roughness=0.95),
    "media": dict(label="Coir, in the cores", colour="#6B4A33", roughness=1.0),
    "pan": dict(label="Steam pan (stainless)", colour="#C4C9CC", metalness=0.55,
                roughness=0.35),
    "pads": dict(label="Pads (printed)", colour="#F2F4F1"),
    "instrument": dict(label="Instrument block, cored", colour="#9C9A94", roughness=0.95),
    "plate": dict(label="Ground plate (1/4 steel)", colour="#3A3D3E", metalness=0.4,
                  roughness=0.6),
    "crook": dict(label="Crook, 3/4 EMT", colour="#1E2124", paint=True, metalness=0.15,
                  roughness=0.55),
    "coupling": dict(label="Set-screw coupling", colour="#B8BCBE", metalness=0.6,
                     roughness=0.35),
    "sleeve": dict(label="Sleeve (printed)", colour="#F2F4F1"),
    "inner": dict(label="Inner tube, 1/2 EMT", colour="#B8BCBE", metalness=0.6,
                  roughness=0.35, rides=True),
    "bushing": dict(label="Bushing (printed)", colour="#F2F4F1", rides=True),
    "beam": dict(label="Beam, white oak", colour="#C9A97A", roughness=0.7, rides=True),
    "bars": dict(label="Heatsink bars", colour="#8E9499", metalness=0.6, roughness=0.4,
                 rides=True),
    "hub": dict(label="Hub (printed)", colour="#F2F4F1", rides=True),
    "lid": dict(label="Camera lid (printed)", colour="#F2F4F1", rides=True),
}

# The crook's paint, as candidates. DTM enamels come in a short list of solid
# colours; these are the ones that read against concrete and oak.
PAINTS = {
    "Black": "#1E2124",
    "Signal white": "#ECECE7",
    "Safety orange": "#D9622B",
    "Oxide red": "#7A2E22",
}

GAP_STEP = 0.5  # in: the readout's table, which the page snaps the slider to


def _mesh(part, tolerance_mm: float, angular: float) -> dict:
    """Tessellate one part into the little-endian Float32/Uint32 the page reads,
    converted from the kernel's millimetres to the model's inches."""
    from cad.growlab_cad.params import IN

    verts, tris = part.tessellate(tolerance_mm, angular)
    pos = array("f", (c / IN for v in verts for c in (v.X, v.Y, v.Z)))
    idx = array("I", (i for t in tris for i in t))
    if sys.byteorder == "big":
        pos.byteswap()
        idx.byteswap()
    return {
        "positions": base64.b64encode(pos.tobytes()).decode(),
        "indices": base64.b64encode(idx.tobytes()).decode(),
        "triangles": len(tris),
    }


def heights() -> list[dict]:
    """The telescope at every step of its travel: what the model holds it to."""
    from cad.growlab_cad import proto as Q

    tip = Q.crook_points()["tip"][1]
    n = round(Q.travel() / GAP_STEP)
    out = []
    for i in range(n + 1):
        gap = Q.GAP_MIN + i * GAP_STEP
        far, near = Q.camera_sees(gap)
        out.append({
            "gap": gap,
            "rise": gap - Q.DRAWN_GAP,
            "beam_bottom": Q.beam_box(gap)[4],
            "held": Q.inner_tube(gap)[1] - tip,
            "hub_clear": Q.coupling_bottom() - Q.hub_top(gap),
            "far": far, "near": near,
        })
    return out


def _payload(tolerance_mm: float, angular: float) -> dict:
    from cad.growlab_cad import proto as Q

    parts = Q.build()
    missing = set(parts) ^ set(PARTS)
    assert not missing, f"PARTS and proto.build() disagree: {missing}"
    meshes = {name: _mesh(parts[name], tolerance_mm, angular) for name in PARTS}

    c = Q.crook_points()
    ib, pb = Q.instrument_box(), Q.planter_box()
    bx0, bx1, *_ = Q.cam_bay()
    x0 = min(Q.pan_box()[0], pb[0])
    x1 = c["p1"][0] + Q.EMT_OD / 2
    top = c["p2"][1] + Q.EMT_OD / 2

    # The camera: the eye at the lens window under the bay, at the drawn height,
    # its axis tilted off straight down toward the planter (-X). The page moves
    # it with the beam.
    tilt = math.radians(Q.CAM_TILT)
    camera = {
        "eye": [(bx0 + bx1) / 2, Q.crook_y(), Q.beam_box()[4] - 0.05],
        "dir": [-math.sin(tilt), 0.0, -math.cos(tilt)],
        "hfov": Q.CAM_HFOV,
    }

    s = Q.stability()
    dx = Q.dial_centres()[0][0] - Q.DIAL_HOLE / 2 - ib[0]
    readout = [
        ("Crook, floor to top", f"{top:.1f} in", True),
        ("Developed length", f"{Q.developed_length():.1f} of {Q.STICK:.0f} in", False),
        ("Bends", f"{Q.total_bend():.0f}° in three 90s", False),
        ("Light, all in", f"{Q.light_weight():.1f} lb", False),
        ("Shove to tip it, free-standing", f"{s['shove_lb']:.1f} lb", True),
        ("Concrete beside a dial hole", f"{dx:.2f} in", True),
        ("Window reveal", f"{Q.FACE_SHELL:.2f} in deep", False),
        ("Triangles", f"{sum(m['triangles'] for m in meshes.values()):,}", False),
    ]

    sha = _git_sha()
    return {
        "sha": sha,
        "parts": PARTS,
        "paints": PAINTS,
        "meshes": meshes,
        "heights": heights(),
        "drawnGap": Q.DRAWN_GAP,
        "camera": camera,
        "frame": {"x0": x0, "x1": x1, "y0": Q.pan_box()[2], "y1": max(ib[3], pb[3]),
                  "z1": top},
        "mediaTop": Q.media_top(),
        "cut": {"x": [x0, x1], "y": [Q.pan_box()[2], max(ib[3], pb[3])], "z": [0.0, top]},
        "meta": ("Two blocks, a conduit, a light. The planter on the floor in its pan; "
                 "the instrument stood on end with the dials and the e-ink cored into its "
                 "face; one stick of 3/4 EMT bent on a hand bender, and a white oak beam "
                 "on a telescope, 12 to 24 in over the media."),
        "readout": [{"label": a, "value": b, "tight": t} for a, b, t in readout],
        "foot": ("Built from <code>cad/growlab_cad/proto.py</code> at "
                 f"<code>{sha}</code>, so the render cannot drift from the part. "
                 "Inches throughout. The block, the pan and the conduit are estimates "
                 "until calipered: see <code>docs/P1_PROTOTYPE.md</code>."),
    }


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:  # noqa: BLE001 — a viewer built outside a checkout still works
        return "unknown"


def render_html(payload: dict, *, standalone: bool = True) -> str:
    """The template with the data and three.js poured in."""
    from cad.sensor_case_viewer import STANDALONE_HEAD
    from cad.viewer import THREE_TAG, _three_js

    template = (REPO / "cad" / "proto_viewer_template.html").read_text()
    assert "/*__P1_DATA__*/null" in template, "the data placeholder moved"
    assert template.startswith(STANDALONE_HEAD), "the template's head moved"
    if not standalone:
        template = template[len(STANDALONE_HEAD):]
    html = template.replace("/*__P1_DATA__*/null", json.dumps(payload))
    src = _three_js()
    if src is not None:
        assert THREE_TAG in html, "the three.js script tag moved; inlining would no-op"
        html = html.replace(THREE_TAG, f"<script>{src}</script>")
    return html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tolerance", type=float, default=0.3,
                    help="tessellation tolerance, mm. Between the station's 0.6 and the "
                         "case's 0.06: the tubes are under an inch across")
    ap.add_argument("--angular", type=float, default=0.3, help="angular tolerance, radians")
    ap.add_argument("--artifact", action="store_true",
                    help="emit the page without its own document head, for a host that "
                         "supplies one")
    ap.add_argument("--out", type=Path, default=OUT / "proto_viewer.html")
    args = ap.parse_args(argv)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = _payload(args.tolerance, args.angular)
    html = render_html(payload, standalone=not args.artifact)
    args.out.write_text(html)
    tris = sum(m["triangles"] for m in payload["meshes"].values())
    rel = args.out.relative_to(REPO) if args.out.is_relative_to(REPO) else args.out
    print(f"wrote {rel}  ({len(html) // 1024} KB, {tris} triangles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
