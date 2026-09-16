#!/usr/bin/env python3
"""Fit a scanner's device RGB to CIE XYZ, and score the fit honestly.

A matrix-and-curves ICC profile is, underneath, exactly two things: a per
channel tone curve that linearises the device, and a 3x3 that rotates the
linearised device primaries onto CIE XYZ. This fits both from a scanned
chart, in about a hundred lines and with no colour-management stack
installed, and writes the result as JSON that the sampler can apply.

    python tools/color/fit_profile.py measured.csv reference.cie -o v600.json

Two numbers come back. The **fit** error is how well the model reproduces the
chart it was fitted to — always flattering, because the chart is both the
question and the answer. The **cross-validated** error refits the matrix with
each patch held out and scores that patch against a model that never saw it;
that is the number that predicts what happens to a colour the chart does not
contain, and it is the one to quote.

This does not replace ArgyllCMS. A cLUT profile fitted by ``colprof`` will
beat a 3x3 on a chart with saturated patches, and only an ICC profile can be
handed to other software. What this gives is a self-contained, tested,
inspectable path from a scan to a defensible Lab number.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.color.cgats import CgatsError, PatchSet, load
    from tools.color.colorimetry import (
        D50,
        Triple,
        _apply,
        _invert,
        delta_e_2000,
        lab_to_xyz,
        percentile,
        srgb_to_hex,
        xyz_to_lab,
        xyz_to_srgb,
    )
else:
    from .cgats import CgatsError, PatchSet, load
    from .colorimetry import (
        D50,
        Triple,
        _apply,
        _invert,
        delta_e_2000,
        lab_to_xyz,
        percentile,
        srgb_to_hex,
        xyz_to_lab,
        xyz_to_srgb,
    )

MODEL_KIND = "growlab-color-model/1"

# CHOICE — the gamma search range and resolution. Flatbed scanners land
# between about 1.6 and 2.4; the range is wider than that so an odd driver
# setting is found rather than pinned to an endpoint. The refinement step is
# finer than the fit error can resolve, which costs nothing at 24 patches.
GAMMA_LO = 1.0
GAMMA_HI = 3.2
GAMMA_COARSE = 0.05
GAMMA_FINE = 0.002


@dataclass
class Model:
    """A fitted device-RGB to XYZ transform."""

    kind: str
    gamma: float
    matrix: List[List[float]]
    white: List[float]
    rgb_scale: float
    source: str = ""
    fit: Optional[dict] = None

    def to_xyz(self, rgb: Sequence[float]) -> Triple:
        """Device RGB, already normalised to 0..1, to XYZ under ``white``."""
        lin = [max(0.0, min(1.0, c)) ** self.gamma for c in rgb]
        return _apply(self.matrix, lin)

    def to_lab(self, rgb: Sequence[float]) -> Triple:
        return xyz_to_lab(self.to_xyz(rgb), tuple(self.white))

    def to_hex(self, rgb: Sequence[float]) -> str:
        return srgb_to_hex(xyz_to_srgb(self.to_xyz(rgb), tuple(self.white)))

    def dump(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def load(path: str | Path) -> "Model":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("kind") != MODEL_KIND:
            raise ValueError(f"{path}: not a {MODEL_KIND} file")
        return Model(**data)


class FitError(ValueError):
    """The chart cannot be fitted."""


def detect_scale(values: Sequence[float]) -> float:
    """Guess the scale device RGB arrived on.

    CGATS writes 0..100, hand-made CSV tends to be 0..1, and anything sampled
    straight out of an image is 0..255 or 0..65535. The bands do not overlap,
    so the maximum decides. Pass ``--rgb-scale`` when the chart is dark enough
    that its own maximum is misleading.
    """
    top = max(values) if values else 0.0
    if top <= 1.5:
        return 1.0
    if top <= 100.5:
        return 100.0
    if top <= 255.5:
        return 255.0
    return 65535.0


def _solve3(a: Sequence[Sequence[float]], b: Sequence[float]) -> Triple:
    return _apply(_invert(a), b)


def _fit_matrix(lin: Sequence[Triple], xyz: Sequence[Triple]) -> List[List[float]]:
    """Least-squares 3x3 taking linearised RGB to XYZ, by normal equations.

    Three patches would make this exactly determined and worthless; a real
    chart over-determines it, which is the point. The normal equations are
    ill-conditioned in general, but a scanner's three channels are far from
    collinear and 24 patches is a benign problem.
    """
    ata = [[sum(p[i] * p[j] for p in lin) for j in range(3)] for i in range(3)]
    rows = []
    for k in range(3):
        atb = [sum(p[i] * t[k] for p, t in zip(lin, xyz)) for i in range(3)]
        try:
            rows.append(list(_solve3(ata, atb)))
        except ValueError as exc:  # singular
            raise FitError(
                "the chart's linearised RGB is degenerate — patches are "
                "collinear or all one colour"
            ) from exc
    return rows


def _errors(
    matrix: Sequence[Sequence[float]],
    lin: Sequence[Triple],
    labs: Sequence[Triple],
    white: Triple,
) -> List[float]:
    return [
        delta_e_2000(lab, xyz_to_lab(_apply(matrix, p), white))
        for p, lab in zip(lin, labs)
    ]


def _mean_error(gamma: float, rgb: Sequence[Triple], labs, xyz, white) -> Tuple[float, list]:
    lin = [tuple(c ** gamma for c in p) for p in rgb]
    matrix = _fit_matrix(lin, xyz)
    errs = _errors(matrix, lin, labs, white)
    return sum(errs) / len(errs), matrix


def fit(
    rgb: Sequence[Triple],
    labs: Sequence[Triple],
    white: Triple = D50,
    gamma: Optional[float] = None,
) -> Tuple[float, List[List[float]]]:
    """Fit gamma and matrix. ``rgb`` is normalised 0..1; ``labs`` is reference.

    Gamma is found by a coarse sweep then a fine one around the winner rather
    than by a gradient method: the objective is a mean of CIEDE2000 values,
    which is not smooth, and a sweep over a bounded range cannot walk off a
    cliff the way a solver can.
    """
    if len(rgb) < 4:
        raise FitError(f"need at least 4 patches to fit a 3x3, got {len(rgb)}")
    xyz = [lab_to_xyz(lab, white) for lab in labs]

    if gamma is not None:
        return gamma, _mean_error(gamma, rgb, labs, xyz, white)[1]

    def sweep(lo: float, hi: float, step: float) -> Tuple[float, float]:
        best_g, best_e = lo, float("inf")
        g = lo
        while g <= hi + 1e-12:
            e, _ = _mean_error(g, rgb, labs, xyz, white)
            if e < best_e:
                best_g, best_e = g, e
            g += step
        return best_g, best_e

    coarse, _ = sweep(GAMMA_LO, GAMMA_HI, GAMMA_COARSE)
    best, _ = sweep(
        max(GAMMA_LO, coarse - GAMMA_COARSE),
        min(GAMMA_HI, coarse + GAMMA_COARSE),
        GAMMA_FINE,
    )
    return best, _mean_error(best, rgb, labs, xyz, white)[1]


def cross_validate(
    rgb: Sequence[Triple], labs: Sequence[Triple], gamma: float, white: Triple = D50
) -> List[float]:
    """Leave-one-out CIEDE2000, at fixed gamma.

    Gamma is held at the full-chart value rather than refitted per fold. It is
    one parameter against the matrix's nine and it barely moves when a single
    patch leaves; refitting it per fold changes the reported number by less
    than the number's own precision and multiplies the work by the patch count.
    """
    xyz = [lab_to_xyz(lab, white) for lab in labs]
    lin = [tuple(c ** gamma for c in p) for p in rgb]
    out: List[float] = []
    for i in range(len(lin)):
        rest_lin = lin[:i] + lin[i + 1 :]
        rest_xyz = xyz[:i] + xyz[i + 1 :]
        matrix = _fit_matrix(rest_lin, rest_xyz)
        out.append(delta_e_2000(labs[i], xyz_to_lab(_apply(matrix, lin[i]), white)))
    return out


def _stats(errs: Sequence[float]) -> dict:
    return {
        "n": len(errs),
        "mean": round(sum(errs) / len(errs), 4) if errs else 0.0,
        "median": round(percentile(errs, 50.0), 4),
        "p95": round(percentile(errs, 95.0), 4),
        "max": round(max(errs), 4) if errs else 0.0,
    }


def build(
    measured: PatchSet,
    reference: PatchSet,
    white: Triple = D50,
    gamma: Optional[float] = None,
    rgb_scale: Optional[float] = None,
) -> Tuple[Model, List[str]]:
    """Pair the two sets by identifier and fit a model to the pairs."""
    ref_by_id = reference.by_id()
    rgb: List[Triple] = []
    labs: List[Triple] = []
    missing: List[str] = []
    for p in measured.patches:
        if p.rgb is None:
            raise FitError(
                f"{measured.source}: patch {p.ident} has no device RGB — the measured "
                "file must carry RGB_R/RGB_G/RGB_B, not just Lab"
            )
        ref = ref_by_id.get(p.ident)
        if ref is None:
            missing.append(p.ident)
            continue
        rgb.append(p.rgb)
        labs.append(ref.lab)
    if not rgb:
        raise FitError(
            "no patches paired — the measured file and the reference share no "
            "identifiers"
        )

    scale = rgb_scale or detect_scale([c for p in rgb for c in p])
    norm = [tuple(min(1.0, max(0.0, c / scale)) for c in p) for p in rgb]

    g, matrix = fit(norm, labs, white=white, gamma=gamma)
    lin = [tuple(c ** g for c in p) for p in norm]
    fit_errs = _errors(matrix, lin, labs, white)
    cv_errs = cross_validate(norm, labs, g, white)

    model = Model(
        kind=MODEL_KIND,
        gamma=round(g, 5),
        matrix=[[round(v, 8) for v in row] for row in matrix],
        white=list(white),
        rgb_scale=scale,
        source=f"{measured.source} against {reference.source}",
        fit={"fit": _stats(fit_errs), "cross_validated": _stats(cv_errs)},
    )
    return model, missing


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="fit_profile",
        description="Fit device RGB to XYZ from a scanned chart and report the error.",
    )
    ap.add_argument("measured", help="CSV or CGATS of sampled patches, with device RGB")
    ap.add_argument("reference", help="the chart's reference values")
    ap.add_argument("-o", "--out", help="write the fitted model here as JSON")
    ap.add_argument("--gamma", type=float, help="fix gamma instead of searching for it")
    ap.add_argument(
        "--rgb-scale",
        type=float,
        help="the full-scale device value (1, 100, 255, 65535); guessed if omitted",
    )
    ap.add_argument("--json", action="store_true", help="emit the model to stdout as JSON")
    args = ap.parse_args(argv)

    try:
        measured = load(args.measured)
        reference = load(args.reference)
        model, missing = build(
            measured, reference, gamma=args.gamma, rgb_scale=args.rgb_scale
        )
    except (OSError, CgatsError, FitError) as exc:
        print(f"fit_profile: {exc}", file=sys.stderr)
        return 2

    if args.out:
        model.dump(args.out)

    if args.json:
        print(json.dumps(asdict(model), indent=2))
        return 0

    f, cv = model.fit["fit"], model.fit["cross_validated"]
    print(f"fitted {f['n']} patches, gamma {model.gamma:.3f}, device full scale {model.rgb_scale:g}")
    if missing:
        shown = ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else "")
        print(f"{len(missing)} measured patches had no reference and were dropped: {shown}")
    print("")
    print(f"  {'':<16}{'mean':>8}{'median':>8}{'p95':>8}{'max':>8}")
    print(f"  {'fit':<16}{f['mean']:8.2f}{f['median']:8.2f}{f['p95']:8.2f}{f['max']:8.2f}")
    print(f"  {'cross-validated':<16}{cv['mean']:8.2f}{cv['median']:8.2f}{cv['p95']:8.2f}{cv['max']:8.2f}")
    print("")
    print("Quote the cross-validated mean. The fit row is the chart marking its own work.")
    if args.out:
        print(f"model written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
