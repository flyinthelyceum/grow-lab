#!/usr/bin/env python3
"""Build the V1 station and write STEP files for Fusion.

    python cad/build.py            # everything into cad/out/
    python cad/build.py --check    # build and report, write nothing

Outputs
-------
cad/out/growlab_v1_station.step   the full assembly, parts labelled
cad/out/parts/<name>.step         each fabricated part on its own
cad/out/report.json               bounding boxes in inches, interference
                                  check, and the params that were used

STEP is unit-tagged in millimetres; the model is built in mm from inch
parameters, so Fusion imports it at true size. Set Fusion's document units to
inches after import if you want to read the dimensions as the docs give them.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from build123d import export_step  # noqa: E402

from cad.growlab_cad import assembly, params  # noqa: E402
from cad.growlab_cad._shapes import bbox_in  # noqa: E402

OUT = REPO / "cad" / "out"


def _params_snapshot() -> dict:
    """Every public numeric parameter, so the report records what built it."""
    return {
        k: v for k, v in vars(params).items()
        if k.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="build and report; write no files")
    args = ap.parse_args(argv)

    t0 = time.monotonic()
    fab = assembly.fabricated()
    ref = assembly.reference()
    print(f"built {len(fab)} fabricated + {len(ref)} reference parts in {time.monotonic() - t0:.1f}s")

    report = {
        "units": "inches",
        "fabricated": {n: bbox_in(p) for n, p in fab.items()},
        "reference": {n: bbox_in(p) for n, p in ref.items()},
        "interferences": assembly.interferences(fab),
        "reference_clashes": assembly.reference_clashes(fab, ref),
        "depth_budget": {**vars(params.DEPTH), "required": params.DEPTH.required, "slack": params.DEPTH.slack},
        "mast_rotated": params.MAST_ROTATED,
        "heights": vars(params.HEIGHTS),
        "static_lift_in": params.HEIGHTS.static_lift,
        "fixture_cantilever_in": params.FIXTURE_CANTILEVER,
        "dial_cut_diameter": params.DIAL_CUT_DIAMETER,
        "params": _params_snapshot(),
    }

    print()
    print(f"{'part':10} {'x':>16} {'y':>16} {'z':>16}")
    for n, bb in {**report["fabricated"], **report["reference"]}.items():
        print(f"{n:10} {bb['x0']:7.2f}..{bb['x1']:<7.2f} {bb['y0']:7.2f}..{bb['y1']:<7.2f} {bb['z0']:7.2f}..{bb['z1']:<7.2f}")

    print()
    if report["interferences"]:
        print("INTERFERENCE between fabricated parts:")
        for a, b, v in report["interferences"]:
            print(f"  {a} ∩ {b} = {v} in³")
    else:
        print("no interference between fabricated parts")

    if report["reference_clashes"]:
        print("DESIGN CONFLICT — reference envelope meets a fabricated part:")
        for r, f, v in report["reference_clashes"]:
            print(f"  {r} ∩ {f} = {v} in³")

    d = params.DEPTH
    verdict = "fits" if d.slack >= 0 else "DOES NOT FIT"
    print(f"depth budget at the mast: {d.required:.2f} in required of {d.available:.2f} available "
          f"→ {d.slack:+.2f} in ({verdict}); mast {'3 across × 2 deep' if params.MAST_ROTATED else '2 across × 3 deep'}")

    if params.DIAL_CUT_DIAMETER is None:
        print("dials: NOT CUT — witness rings at bezel OD; set DIAL_CUT_DIAMETER after calipers")

    if args.check:
        return 1 if report["interferences"] else 0

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "parts").mkdir(exist_ok=True)

    station = assembly.build()
    path = OUT / "growlab_v1_station.step"
    export_step(station, str(path))
    print(f"\nwrote {path.relative_to(REPO)}  ({path.stat().st_size // 1024} KB)")

    for n, p in fab.items():
        pp = OUT / "parts" / f"{n}.step"
        export_step(p, str(pp))
        print(f"wrote {pp.relative_to(REPO)}  ({pp.stat().st_size // 1024} KB)")

    (OUT / "report.json").write_text(json.dumps(report, indent=2))
    print(f"wrote {(OUT / 'report.json').relative_to(REPO)}")

    return 1 if report["interferences"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
