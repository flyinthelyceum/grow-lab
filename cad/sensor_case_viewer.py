#!/usr/bin/env python3
"""Turn the canopy sensor case into a self-contained 3D viewer page.

    python cad/sensor_case_viewer.py

One HTML file: both printed halves and the three boards tessellated and
embedded, three.js inlined, no server and no network. The station viewer
(``cad/viewer.py``) answers "how does this read from where a person stands".
This one answers the three questions this part actually raises, which are
different, so it is a different page rather than another variant of that one:

**Assembled** — does the thing look like a small piece of refined geometry on
a coarse block, or like a lump? That is the whole brief for this object.

**Exploded** — where does every board sit, and what holds it? The case is
mostly its contents; an empty box shows nothing. The boards come from
``sensor_case.boards()``, which puts them where the layout functions say, so
this is the model's own answer rather than a drawing of one.

**On the bed** — both halves in print orientation, on a bed plane. Rev D had
four features that were not attached to the part and its tests could not see
it. The tests can now, but "one solid" is a thing you should also be able to
look at: turn the body over and the collar, the bosses and the webs are either
columns standing on the face or they are floating, and the eye catches that
in a second.

Everything the page shows is computed here from the same parameters the
geometry is, so the viewer cannot drift from the part.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from array import array
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT = REPO / "cad" / "out"

# Printed PETG, the boards, and the disc. The two halves are the same material
# and are deliberately a shade apart: they are one object in the hand and two
# things on the bed, and the render has to say which it is showing.
PARTS = {
    "sensor_case_body": dict(label="Body (printed PETG)", colour="#F2F4F1",
                             opacity=1.0, explode=(0, 0, 1.0)),
    # The plate does not move. Everything is assembled onto it, and exploding it
    # downward only buries it in the block it is standing on.
    "sensor_case_base": dict(label="Base plate + lip", colour="#E2E5DE",
                             opacity=1.0, explode=(0, 0, 0.0)),
    "diffuser": dict(label="PTFE diffuser, Ø12 × 1", colour="#CBD9E2",
                     opacity=0.75, explode=(0, 0, 1.35), roughness=0.55),
    # The two hanging boards travel with the body, because that is what holds
    # them, and a little less far, so they come out from under it rather than
    # with it. The ADS1115 barely moves: it is taped to the plate, and the only
    # thing worth showing is that there is tape under it.
    # 0.35 is not a look: the boards hang 11.5 mm above the body's bottom edge,
    # so they only clear it once the body has risen that much further than they
    # have — d(1 - f) > 11.5. At 0.35 they are out in the open by the time the
    # slider is a third across; at 0.55 they stay hidden until the very end.
    "as7341": dict(label="AS7341 (screwed)", colour="#2E5C7A",
                   opacity=1.0, explode=(0, 0, 0.35), roughness=0.6),
    "bme280": dict(label="BME280 (two bosses)", colour="#3D6B4A",
                   opacity=1.0, explode=(0, 0, 0.35), roughness=0.6),
    "ads1115": dict(label="ADS1115 (taped to the plate)", colour="#A3402B",
                    opacity=1.0, explode=(0, 0, 0.12), roughness=0.6),
}

EXPLODE_SPAN = 34.0  # mm at the slider's far end, per unit of a part's vector


def _mesh(part, tolerance_mm: float, angular: float, origin) -> dict:
    """Tessellate one part into the little-endian Float32/Uint32 the page reads.

    Shifted onto the case's own datum — plan centre, block top — rather than
    left in station coordinates. The case sits 288 mm off the station's origin
    in Y and 1127 up in Z, and a viewer that inherits that has to carry the
    offset through its camera, its section planes and its bed. Moving it once,
    here, means every number the page handles afterwards is the number on the
    drawing: X and Y from the middle of the case, Z as height above the block.
    """
    verts, tris = part.tessellate(tolerance_mm, angular)
    # tessellate hands back the kernel's millimetres, which is what this page
    # wants; the parameters are inches, so the datum is converted on the way in.
    ox, oy, oz = origin
    pos = array("f", (c for v in verts
                      for c in (v.X - ox, v.Y - oy, v.Z - oz)))
    idx = array("I", (i for t in tris for i in t))
    if sys.byteorder == "big":
        pos.byteswap()
        idx.byteswap()
    return {
        "positions": base64.b64encode(pos.tobytes()).decode(),
        "indices": base64.b64encode(idx.tobytes()).decode(),
        "triangles": len(tris),
    }


def _payload(tolerance_mm: float, angular: float) -> dict:
    from cad.growlab_cad import params as P
    from cad.growlab_cad import sensor_case as SC

    mm = lambda v: v / P.MM  # noqa: E731 — inches to millimetres, everywhere below

    parts = {"sensor_case_body": SC.build_body(), "sensor_case_base": SC.build_base()}
    parts.update(SC.boards())
    origin = (P.SC_X * P.IN, P.SC_Y * P.IN, P.SC_Z0 * P.IN)
    meshes = {name: _mesh(part, tolerance_mm, angular, origin)
              for name, part in parts.items()}

    def rel(part) -> dict[str, float]:
        """A part's box on the case's datum, in millimetres."""
        from cad.growlab_cad._shapes import bbox_in

        bb = bbox_in(part)
        return {"x0": mm(bb["x0"] - P.SC_X), "x1": mm(bb["x1"] - P.SC_X),
                "y0": mm(bb["y0"] - P.SC_Y), "y1": mm(bb["y1"] - P.SC_Y),
                "z0": mm(bb["z0"] - P.SC_Z0), "z1": mm(bb["z1"] - P.SC_Z0)}

    # Where each part sits, per mode. The assembled placement is the model's own
    # — the meshes are already in world coordinates, so the offset is zero and
    # the only interesting entry is the print one.
    zero = {"at": [0, 0, 0]}
    at_origin = {}
    for name in ("sensor_case_body", "sensor_case_base"):
        # for_print() rotates 180 about X and drops the part on Z=0. Rather than
        # ship a second copy of every mesh, ship the transform and let the page
        # apply it: a rotation, and the offset that lands the part on the bed.
        # Turning about X negates Y and Z, so a part centred at (cx, cy) with
        # its top at z1 comes to rest by moving (-cx, +cy, +z1).
        bb = rel(parts[name])
        at_origin[name] = {
            "flip": True,
            "at": [-(bb["x0"] + bb["x1"]) / 2,
                   (bb["y0"] + bb["y1"]) / 2,
                   bb["z1"]],
        }

    # Side by side on the bed, not overlapping.
    side = mm(P.SC_LEN) * 0.62
    at_origin["sensor_case_body"]["at"][0] -= side
    at_origin["sensor_case_base"]["at"][0] += side

    assembled_frame = {"cx": 0, "cy": 0, "cz": mm(P.SC_HGT) / 2,
                       "r": mm(P.SC_LEN) * 2.1}
    modes = {
        "assembled": {
            "label": "Assembled, on the block",
            "note": "Refined geometry on a coarse thing, or a lump",
            "place": {n: zero for n in parts},
            "block": True, "bed": False, "explodes": False,
            "frame": assembled_frame,
            "view": {"theta": -0.62, "phi": 1.06},
        },
        "exploded": {
            "label": "Exploded",
            "note": "Every board, and what holds it",
            "place": {n: zero for n in parts},
            "block": True, "bed": False, "explodes": True,
            # Two frames, and the page reads between them as the slider moves:
            # a stack that grows to four times the height of the case cannot be
            # watched through a camera framed on the case.
            "frame": {**assembled_frame, "r": mm(P.SC_LEN) * 2.4},
            # Low, almost level with the seam. An exploded stack separated only
            # in Z is invisible from above: the body's own footprint hides
            # everything under it, and at 29 degrees of elevation a 12 mm gap
            # is covered for 22 mm in every direction. From 13 degrees you see
            # between the layers, which is the whole point of the mode.
            "view": {"theta": -0.62, "phi": 1.36},
            "frameFull": {
                "cx": 0, "cy": 0,
                "cz": (mm(P.SC_HGT) + 1.35 * EXPLODE_SPAN - mm(P.SC_LIP_DROP)) / 2,
                "r": mm(P.SC_LEN) * 3.3,
            },
        },
        "print": {
            "label": "On the bed",
            "note": "Both halves top-face-down, no supports",
            "place": at_origin,
            "shows": ["sensor_case_body", "sensor_case_base"],
            "block": False, "bed": True, "explodes": False,
            # Wide enough for both halves side by side, which is 130 mm across.
            "frame": {"cx": 0, "cy": 0, "cz": mm(P.SC_HGT) / 2, "r": mm(P.SC_LEN) * 3.3},
            "view": {"theta": -0.55, "phi": 1.0},
        },
    }

    # The section ranges are the part's own extents, so the slider cannot leave
    # the object.
    cut = {
        "x": [-mm(P.SC_LEN) / 2, mm(P.SC_LEN) / 2],
        "y": [-mm(P.SC_WID) / 2, mm(P.SC_Y1 - P.SC_Y)],
        "z": [-mm(P.SC_LIP_DROP), mm(P.SC_HGT)],
    }

    tube = mm(SC.recess_floor() - SC.board_top())
    import math

    half_angle = math.degrees(math.atan((mm(P.SC_BAFFLE_ID) / 2) / tube))
    readout = [
        ("Envelope", f"{mm(P.SC_LEN):.0f} × {mm(P.SC_WID):.0f} × {mm(P.SC_HGT):.0f}", False),
        ("Wall / plate", f"{mm(P.SC_WALL):.1f} / {mm(P.SC_BASE_T):.1f}", False),
        ("Bore, and its field", f"Ø{mm(P.SC_BAFFLE_ID):.1f} · {half_angle:.0f}°", False),
        ("Wall under the collar",
         f"{mm((P.SC_BAFFLE_OD - P.SC_APERTURE_DIA) / 2):.1f}", False),
        ("Skin under the disc",
         f"{mm(SC.recess_floor() - SC.pilot_top()):.2f}", True),
        ("Plate under a screw head",
         f"{mm(P.SC_BASE_T - P.SC_SCREW_CSK_DEPTH):.1f}", False),
        ("Headroom over the ADS1115",
         f"{mm(SC.board_top() - P.SC_BOARD_T - SC.ads1115_stack_top()):.1f}", True),
        ("Longest bridge", f"{mm(P.SC_VENT_L):.1f}", False),
        ("Triangles", f"{sum(m['triangles'] for m in meshes.values()):,}", False),
    ]

    return {
        "sha": _git_sha(),
        "parts": PARTS,
        "meshes": meshes,
        "modes": modes,
        "cut": cut,
        "explodeSpan": EXPLODE_SPAN,
        "block": {
            "len": mm(P.CMU_L), "wid": mm(P.CMU_W),
            "x": mm(P.CMU_X - P.SC_X), "y": mm(P.CMU_Y - P.SC_Y),
        },
        "meta": (f"{mm(P.SC_LEN):.0f} × {mm(P.SC_WID):.0f} × {mm(P.SC_HGT):.0f} mm, matte white "
                 "PETG, on the block's centre-rear. Rev E — what five adversarial reviews left "
                 "standing."),
        "readout": [{"label": a, "value": b, "tight": t} for a, b, t in readout],
        "foot": ("Built from <code>cad/growlab_cad/sensor_case.py</code> at "
                 f"<code>{_git_sha()}</code>, so the render cannot drift from the part. "
                 "Millimetres throughout."),
    }


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:  # noqa: BLE001 — a viewer built outside a checkout still works
        return "unknown"


# The document head a file opened from disk needs, and a published page does
# not: an artifact host supplies its own skeleton and its own charset, and a
# second doctype inside that is a parse error rather than a preference.
STANDALONE_HEAD = (
    '<!doctype html>\n'
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
)


def render_html(payload: dict, *, standalone: bool = True) -> str:
    """The template with the data and three.js poured in."""
    from cad.viewer import THREE_TAG, _three_js

    template = (REPO / "cad" / "sensor_case_viewer_template.html").read_text()
    assert "/*__CASE_DATA__*/null" in template, "the data placeholder moved"
    assert template.startswith(STANDALONE_HEAD), "the template's head moved"
    if not standalone:
        template = template[len(STANDALONE_HEAD):]
    html = template.replace("/*__CASE_DATA__*/null", json.dumps(payload))
    src = _three_js()
    if src is not None:
        assert THREE_TAG in html, "the three.js script tag moved; inlining would no-op"
        html = html.replace(THREE_TAG, f"<script>{src}</script>")
    return html


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tolerance", type=float, default=0.06,
                    help="tessellation tolerance, mm. Tighter than the station's: this part "
                         "is 58 mm long and its bore is 6.5, so the station's 0.6 would "
                         "render the collar as a hexagon")
    ap.add_argument("--angular", type=float, default=0.2, help="angular tolerance, radians")
    ap.add_argument("--artifact", action="store_true",
                    help="emit the page without its own document head, for a host that "
                         "supplies one")
    ap.add_argument("--out", type=Path, default=OUT / "sensor_case_viewer.html")
    args = ap.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    payload = _payload(args.tolerance, args.angular)
    html = render_html(payload, standalone=not args.artifact)
    args.out.write_text(html)
    tris = sum(m["triangles"] for m in payload["meshes"].values())
    rel = args.out.relative_to(REPO) if args.out.is_relative_to(REPO) else args.out
    print(f"wrote {rel}  ({len(html) // 1024} KB, {tris} triangles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
