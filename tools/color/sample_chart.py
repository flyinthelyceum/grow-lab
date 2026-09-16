#!/usr/bin/env python3
"""Pull device RGB out of a scan: chart patches, or named spots on a subject.

Two subcommands.

``grid`` reads a chart. Give it the pixel centres of the four corner patches —
read them off any image viewer — and it interpolates the rest, samples a box
inside each patch and writes a CSV the fitter can use. Four corners rather
than an outline because a scan is never square on the platen, and because the
corner patch centres are unambiguous to click while a chart's outer edge is
a bevel.

``points`` reads named spots on a subject scanned in the same pass, and, given
a fitted model, reports each one as Lab and as a hex sRGB approximation.

    python tools/color/sample_chart.py grid scan.tif \\
        --corners 412,388 1596,392 1600,1180 408,1176 \\
        --rows 4 --cols 6 --ids-from ColorChecker.cie -o measured.csv

    python tools/color/sample_chart.py points scan.tif \\
        --point cream:2040,910 --point ring:2105,880 --model v600.json

Each patch is reduced by an interquartile mean, not a plain average: a dust
speck, a platen scratch or a specular glint on a varnished surface is a small
number of extreme pixels, and throwing away the outer quartiles removes them
without the quantisation a median would bring.

On bit depth: Pillow delivers 8 bits per channel for ordinary RGB images, so
that is what a sample reads even from a 48-bit scan. It matters less than it
sounds — a patch box is thousands of pixels and the scanner's own noise
dithers the low bits, so the interquartile mean lands well inside a count.
Scan at 48 bits anyway: the depth earns its keep in the driver's own
processing, before anything is written to a file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.color.cgats import CgatsError, load
    from tools.color.fit_profile import Model
else:
    from .cgats import CgatsError, load
    from .fit_profile import Model

Point = Tuple[float, float]

# CHOICE — how much of each patch to sample. Half the patch pitch keeps the
# box clear of the printed gap between patches and of the chart's own slight
# keystone, while still averaging thousands of pixels at 600 dpi.
DEFAULT_PATCH_FRAC = 0.5


class SampleError(ValueError):
    """The image cannot be sampled as asked."""


def _open(path: str | Path):
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - Pillow is a hard dependency
        raise SampleError("Pillow is not installed; pip install -e '.[dev]'") from exc
    try:
        im = Image.open(path)
    except OSError as exc:
        raise SampleError(f"{path}: {exc}") from exc
    return im.convert("RGB") if im.mode != "RGB" else im


def interquartile_mean(values: Sequence[float]) -> float:
    """Mean of the middle half. Falls back to the plain mean under 4 values."""
    xs = sorted(values)
    n = len(xs)
    if n == 0:
        raise SampleError("empty sample region")
    if n < 4:
        return sum(xs) / n
    lo, hi = n // 4, n - n // 4
    mid = xs[lo:hi]
    return sum(mid) / len(mid)


def sample_box(image, centre: Point, half_w: float, half_h: float) -> Tuple[float, float, float]:
    """Interquartile-mean RGB of the box around ``centre``, in 0..255."""
    w, h = image.size
    x0 = max(0, int(round(centre[0] - half_w)))
    x1 = min(w, int(round(centre[0] + half_w)) + 1)
    y0 = max(0, int(round(centre[1] - half_h)))
    y1 = min(h, int(round(centre[1] + half_h)) + 1)
    if x0 >= x1 or y0 >= y1:
        raise SampleError(
            f"sample box at {centre[0]:.0f},{centre[1]:.0f} falls outside the "
            f"{w}x{h} image — check the corner coordinates"
        )
    raw = image.crop((x0, y0, x1, y1)).tobytes()
    return tuple(interquartile_mean(raw[ch::3]) for ch in range(3))


def grid_centres(corners: Sequence[Point], rows: int, cols: int) -> List[Point]:
    """Bilinearly interpolate patch centres from the four corner centres.

    ``corners`` is top-left, top-right, bottom-right, bottom-left, in the
    image's own orientation. Bilinear handles the rotation and the mild
    keystone a hinged lid puts on a chart; it cannot handle a lens, which a
    flatbed does not have.
    """
    if len(corners) != 4:
        raise SampleError("need exactly four corner centres: TL TR BR BL")
    if rows < 2 or cols < 2:
        raise SampleError("a grid needs at least 2 rows and 2 columns")
    tl, tr, br, bl = corners
    out: List[Point] = []
    for r in range(rows):
        v = r / (rows - 1)
        for c in range(cols):
            u = c / (cols - 1)
            top = ((1 - u) * tl[0] + u * tr[0], (1 - u) * tl[1] + u * tr[1])
            bot = ((1 - u) * bl[0] + u * br[0], (1 - u) * bl[1] + u * br[1])
            out.append(((1 - v) * top[0] + v * bot[0], (1 - v) * top[1] + v * bot[1]))
    return out


def _pitch(corners: Sequence[Point], rows: int, cols: int) -> Tuple[float, float]:
    tl, tr, br, bl = corners
    dx = ((tr[0] - tl[0]) ** 2 + (tr[1] - tl[1]) ** 2) ** 0.5 / (cols - 1)
    dy = ((bl[0] - tl[0]) ** 2 + (bl[1] - tl[1]) ** 2) ** 0.5 / (rows - 1)
    return dx, dy


def default_ids(rows: int, cols: int) -> List[str]:
    """``A1`` .. row letter plus column number, the way charts are labelled."""
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if rows > len(letters):
        raise SampleError("more rows than letters; pass --ids-from instead")
    return [f"{letters[r]}{c + 1}" for r in range(rows) for c in range(cols)]


def _parse_point(text: str) -> Point:
    try:
        x, y = text.split(",")
        return (float(x), float(y))
    except ValueError as exc:
        raise SampleError(f"not an x,y pair: {text!r}") from exc


def _parse_named_point(text: str) -> Tuple[str, Point]:
    if ":" not in text:
        raise SampleError(f"not a name:x,y point: {text!r}")
    name, coords = text.split(":", 1)
    return name.strip(), _parse_point(coords)


def cmd_grid(args) -> int:
    image = _open(args.image)
    corners = [_parse_point(c) for c in args.corners]
    centres = grid_centres(corners, args.rows, args.cols)
    dx, dy = _pitch(corners, args.rows, args.cols)
    half_w = dx * args.patch_frac / 2.0
    half_h = dy * args.patch_frac / 2.0

    if args.ids_from:
        ids = [p.ident for p in load(args.ids_from).patches]
        if len(ids) < len(centres):
            raise SampleError(
                f"{args.ids_from} names {len(ids)} patches but the grid has {len(centres)}"
            )
        ids = ids[: len(centres)]
    else:
        ids = default_ids(args.rows, args.cols)

    lines = ["SAMPLE_ID,RGB_R,RGB_G,RGB_B"]
    for ident, centre in zip(ids, centres):
        r, g, b = sample_box(image, centre, half_w, half_h)
        lines.append(f"{ident},{r:.4f},{g:.4f},{b:.4f}")
    text = "\n".join(lines) + "\n"

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(
            f"sampled {len(centres)} patches, box {2 * half_w:.0f}x{2 * half_h:.0f} px "
            f"-> {args.out}"
        )
    else:
        sys.stdout.write(text)
    return 0


def cmd_points(args) -> int:
    image = _open(args.image)
    model: Optional[Model] = Model.load(args.model) if args.model else None
    half = args.radius

    if model is not None:
        print(f"{'spot':<16}{'L*':>8}{'a*':>8}{'b*':>8}  {'sRGB':<9} device RGB")
    else:
        print(f"{'spot':<16}{'R':>9}{'G':>9}{'B':>9}")

    for spec in args.point:
        name, centre = _parse_named_point(spec)
        rgb = sample_box(image, centre, half, half)
        if model is None:
            print(f"{name:<16}{rgb[0]:9.2f}{rgb[1]:9.2f}{rgb[2]:9.2f}")
            continue
        # Pillow hands back 0..255 whatever the file's depth, and the model's
        # own scale was normalised away when it was fitted, so this is the
        # one conversion needed.
        norm = tuple(c / 255.0 for c in rgb)
        lab = model.to_lab(norm)
        print(
            f"{name:<16}{lab[0]:8.2f}{lab[1]:8.2f}{lab[2]:8.2f}  "
            f"{model.to_hex(norm):<9} {rgb[0]:6.1f} {rgb[1]:6.1f} {rgb[2]:6.1f}"
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="sample_chart", description="Sample device RGB out of a scan."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("grid", help="sample a chart's patches")
    g.add_argument("image")
    g.add_argument(
        "--corners",
        nargs=4,
        required=True,
        metavar=("TL", "TR", "BR", "BL"),
        help="pixel centres of the four corner patches, each as x,y",
    )
    g.add_argument("--rows", type=int, required=True)
    g.add_argument("--cols", type=int, required=True)
    g.add_argument(
        "--patch-frac",
        type=float,
        default=DEFAULT_PATCH_FRAC,
        help=f"fraction of the patch pitch to sample (default {DEFAULT_PATCH_FRAC})",
    )
    g.add_argument("--ids-from", help="take patch identifiers, in order, from this reference file")
    g.add_argument("-o", "--out", help="write CSV here instead of stdout")
    g.set_defaults(func=cmd_grid)

    p = sub.add_parser("points", help="sample named spots on a subject")
    p.add_argument("image")
    p.add_argument("--point", action="append", required=True, metavar="NAME:X,Y")
    p.add_argument("--radius", type=float, default=8.0, help="half-size of the sample box, px")
    p.add_argument("--model", help="a fit_profile model; adds Lab and hex columns")
    p.set_defaults(func=cmd_points)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (SampleError, CgatsError, OSError, ValueError) as exc:
        print(f"sample_chart: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
