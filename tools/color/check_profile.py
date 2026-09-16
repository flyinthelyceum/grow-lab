#!/usr/bin/env python3
"""Score a set of measured patches against a reference chart.

This is the step that tells you whether a scanner profile actually worked.
``scanin`` reads the chart, ``colprof`` fits a profile, and then nothing in
that toolchain says in plain terms how close the result came. This does: it
pairs patches by identifier, computes CIEDE2000 per patch, and reports the
mean, the 95th percentile and the worst offenders, with the error split into
lightness, chroma and hue so a systematic miss is visible as one.

    python tools/color/check_profile.py measured.ti3 reference.cie
    python -m tools.color.check_profile measured.ti3 reference.cie --json

Exit status is 0 when every threshold holds, 1 when one does not, 2 on a
usage or file error — so it can gate a profiling run in a script.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

if __package__ in (None, ""):  # run as a plain script, not as a module
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.color.cgats import CgatsError, PatchSet, load
    from tools.color.colorimetry import delta_e_2000, delta_e_76, percentile
else:
    from .cgats import CgatsError, PatchSet, load
    from .colorimetry import delta_e_2000, delta_e_76, percentile

# CHOICE — the bar this project holds a scanner profile to. A mean around 1
# is what a well-lit flatbed and a fresh chart give; 2 is still usable for
# sampling a colour off a scan, and anything past 5 on a single patch means a
# patch was misread rather than mis-profiled, so look at that patch first.
DEFAULT_MEAN = 2.0
DEFAULT_P95 = 4.0
DEFAULT_MAX = 5.0


@dataclass(frozen=True)
class Comparison:
    ident: str
    de: float
    dL: float
    dC: float
    dH: float

    def as_dict(self) -> dict:
        return {
            "id": self.ident,
            "de2000": round(self.de, 4),
            "dL": round(self.dL, 4),
            "dC": round(self.dC, 4),
            "dH": round(self.dH, 4),
        }


def compare(
    measured: PatchSet, reference: PatchSet, kL: float = 1.0
) -> tuple[List[Comparison], List[str]]:
    """Pair patches by identifier and score each pair.

    Returns the comparisons and the identifiers present in the reference but
    missing from the measurement — a chart read with a corner clipped shows up
    there rather than as a suspiciously good score over ten patches.
    """
    for side, ps in (("measurement", measured), ("reference", reference)):
        if not ps.has_colorimetry():
            raise CgatsError(
                f"{ps.source}: the {side} carries device RGB only. This scores "
                "colour against colour; convert the device values first with "
                "fit_profile and sample_chart, or point this at a file that has "
                "Lab or XYZ."
            )

    m = measured.by_id()
    rows: List[Comparison] = []
    missing: List[str] = []
    for ref in reference.patches:
        got = m.get(ref.ident)
        if got is None:
            missing.append(ref.ident)
            continue
        de = delta_e_2000(ref.lab, got.lab, kL=kL)
        dL = got.lab[0] - ref.lab[0]
        c_ref = math.hypot(ref.lab[1], ref.lab[2])
        c_got = math.hypot(got.lab[1], got.lab[2])
        dC = c_got - c_ref
        # The hue term is whatever the Euclidean difference has left after
        # lightness and chroma; signed by which way the hue turned.
        residual = delta_e_76(ref.lab, got.lab) ** 2 - dL * dL - dC * dC
        dH = math.sqrt(max(0.0, residual))
        cross = ref.lab[1] * got.lab[2] - ref.lab[2] * got.lab[1]
        if cross < 0:
            dH = -dH
        rows.append(Comparison(ident=ref.ident, de=de, dL=dL, dC=dC, dH=dH))
    return rows, missing


def summarise(rows: Sequence[Comparison]) -> dict:
    des = [r.de for r in rows]
    if not des:
        return {"n": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "n": len(des),
        "mean": sum(des) / len(des),
        "median": percentile(des, 50.0),
        "p95": percentile(des, 95.0),
        "max": max(des),
    }


def _report(
    rows: Sequence[Comparison],
    missing: Sequence[str],
    stats: dict,
    limits: dict,
    worst: int,
    out=sys.stdout,
) -> None:
    print(f"{stats['n']} patches paired", file=out)
    if missing:
        shown = ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else "")
        print(f"{len(missing)} reference patches not found in the measurement: {shown}", file=out)
    print("", file=out)
    print(f"  mean dE00    {stats['mean']:6.2f}   (limit {limits['mean']:.2f})", file=out)
    print(f"  median dE00  {stats['median']:6.2f}", file=out)
    print(f"  95th dE00    {stats['p95']:6.2f}   (limit {limits['p95']:.2f})", file=out)
    print(f"  max dE00     {stats['max']:6.2f}   (limit {limits['max']:.2f})", file=out)

    if rows and worst:
        print("", file=out)
        print(f"worst {min(worst, len(rows))} patches", file=out)
        print(f"  {'patch':<12} {'dE00':>7} {'dL':>7} {'dC':>7} {'dH':>7}", file=out)
        for r in sorted(rows, key=lambda x: -x.de)[:worst]:
            print(
                f"  {r.ident:<12} {r.de:7.2f} {r.dL:7.2f} {r.dC:7.2f} {r.dH:7.2f}",
                file=out,
            )
        # A whole-chart bias is worth naming; it usually means the white point
        # or the exposure moved, not that the profile is bad everywhere.
        n = len(rows)
        bias_L = sum(r.dL for r in rows) / n
        bias_C = sum(r.dC for r in rows) / n
        if abs(bias_L) > 1.0 or abs(bias_C) > 1.0:
            print("", file=out)
            print(
                f"systematic bias: mean dL {bias_L:+.2f}, mean dC {bias_C:+.2f} "
                "— check the white point and that every automatic adjustment is off",
                file=out,
            )


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="check_profile",
        description="Score measured patches against a reference chart in CIEDE2000.",
    )
    ap.add_argument("measured", help="CGATS .ti3/.txt or CSV of what was measured")
    ap.add_argument("reference", help="CGATS .cie/.txt or CSV of the chart's reference values")
    ap.add_argument("--kl", type=float, default=1.0, help="CIEDE2000 kL weight (default 1.0)")
    ap.add_argument("--mean", type=float, default=DEFAULT_MEAN, help="mean dE00 limit")
    ap.add_argument("--p95", type=float, default=DEFAULT_P95, help="95th percentile dE00 limit")
    ap.add_argument("--max", dest="max_de", type=float, default=DEFAULT_MAX, help="max dE00 limit")
    ap.add_argument("--worst", type=int, default=8, help="how many worst patches to list")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args(argv)

    try:
        measured = load(args.measured)
        reference = load(args.reference)
    except (OSError, CgatsError) as exc:
        print(f"check_profile: {exc}", file=sys.stderr)
        return 2

    try:
        rows, missing = compare(measured, reference, kL=args.kl)
    except CgatsError as exc:
        print(f"check_profile: {exc}", file=sys.stderr)
        return 2
    if not rows:
        print(
            "check_profile: no patches paired — the two files share no identifiers. "
            "scanin's .ti3 uses the chart's own patch names; make sure the reference "
            "is the chart that was actually scanned.",
            file=sys.stderr,
        )
        return 2

    stats = summarise(rows)
    limits = {"mean": args.mean, "p95": args.p95, "max": args.max_de}
    failures = [
        name
        for name in ("mean", "p95", "max")
        for limit in (limits[name],)
        if stats[name] > limit
    ]

    if args.json:
        print(
            json.dumps(
                {
                    "measured": measured.source,
                    "reference": reference.source,
                    "stats": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in stats.items()},
                    "limits": limits,
                    "failed": failures,
                    "missing": list(missing),
                    "patches": [r.as_dict() for r in sorted(rows, key=lambda x: -x.de)],
                },
                indent=2,
            )
        )
    else:
        _report(rows, missing, stats, limits, args.worst)
        print("", file=sys.stdout)
        print("PASS" if not failures else "FAIL: over limit on " + ", ".join(failures))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
