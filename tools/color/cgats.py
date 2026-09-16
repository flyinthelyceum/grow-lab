"""A small reader for CGATS/IT8 data files and for plain CSV patch lists.

ArgyllCMS writes CGATS: ``scanin`` produces a ``.ti3`` of what the scanner saw,
and a chart's reference data arrives as a ``.cie`` or ``.txt`` in the same
shape. Both are the same ASCII table — a header of ``KEYWORD "value"`` lines,
then a column list between ``BEGIN_DATA_FORMAT`` and ``END_DATA_FORMAT``, then
rows between ``BEGIN_DATA`` and ``END_DATA``.

This reads enough of that to pull patches out. It is deliberately not a full
CGATS implementation: no sub-tables, no type coercion beyond float-or-string.

CSV is accepted too, for charts measured by hand or pasted out of a
spreadsheet: a header row naming the columns, then one row per patch. Column
names are matched case-insensitively against the same set of aliases.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .colorimetry import D50, Triple, xyz_to_lab

# Column aliases, lower-cased. CGATS spells things several ways depending on
# which program wrote the file; Argyll, i1Profiler and hand-rolled CSV all
# turn up in practice.
_ID_KEYS = ("sample_id", "sampleid", "sample_name", "samplename", "id", "patch", "name")
_XYZ_KEYS = (("xyz_x", "x"), ("xyz_y", "y"), ("xyz_z", "z"))
_LAB_KEYS = (("lab_l", "l"), ("lab_a", "a"), ("lab_b", "b"))
_RGB_KEYS = (("rgb_r", "r"), ("rgb_g", "g"), ("rgb_b", "b"))


@dataclass(frozen=True)
class Patch:
    """One measured or reference patch.

    ``lab`` comes from LAB columns when the file has them, or is computed from
    XYZ under the file's illuminant when it does not. It is ``None`` for a file
    that carries only device RGB — which is what a freshly sampled chart is,
    before anything has told it what those numbers mean. ``rgb`` is the device
    value as the file wrote it, on whatever scale the file used.
    """

    ident: str
    lab: Optional[Triple]
    xyz: Optional[Triple] = None
    rgb: Optional[Triple] = None


@dataclass(frozen=True)
class PatchSet:
    """A named list of patches, with an index by identifier."""

    source: str
    patches: List[Patch]

    def has_colorimetry(self) -> bool:
        """True when every patch carries a Lab value, not only device RGB."""
        return all(p.lab is not None for p in self.patches)

    def by_id(self) -> Dict[str, Patch]:
        return {p.ident: p for p in self.patches}

    def __len__(self) -> int:
        return len(self.patches)


class CgatsError(ValueError):
    """The file is not a CGATS table this reader can use."""


def _pick(columns: Sequence[str], names: Sequence[str]) -> Optional[int]:
    lowered = [c.lower() for c in columns]
    for name in names:
        if name in lowered:
            return lowered.index(name)
    return None


def _triple(row: Sequence[str], idx: Sequence[int]) -> Triple:
    return (float(row[idx[0]]), float(row[idx[1]]), float(row[idx[2]]))


def _rows_to_patches(
    source: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    white: Triple,
) -> PatchSet:
    id_idx = _pick(columns, _ID_KEYS)
    lab_idx = [_pick(columns, keys) for keys in _LAB_KEYS]
    xyz_idx = [_pick(columns, keys) for keys in _XYZ_KEYS]
    rgb_idx = [_pick(columns, keys) for keys in _RGB_KEYS]

    have_lab = all(i is not None for i in lab_idx)
    have_xyz = all(i is not None for i in xyz_idx)
    have_rgb = all(i is not None for i in rgb_idx)
    if not (have_lab or have_xyz or have_rgb):
        raise CgatsError(
            f"{source}: no LAB_L/A/B, XYZ_X/Y/Z or RGB_R/G/B columns; "
            f"found {list(columns)}"
        )

    patches: List[Patch] = []
    for n, row in enumerate(rows, start=1):
        if len(row) < len(columns):
            raise CgatsError(f"{source}: data row {n} has {len(row)} of {len(columns)} fields")
        ident = row[id_idx] if id_idx is not None else str(n)
        # CGATS writes XYZ on a 0..100 scale; the conversions here want Y = 1.
        xyz = tuple(c / 100.0 for c in _triple(row, xyz_idx)) if have_xyz else None
        if have_lab:
            lab = _triple(row, lab_idx)
        elif have_xyz:
            lab = xyz_to_lab(xyz, white)
        else:
            lab = None
        rgb = _triple(row, rgb_idx) if have_rgb else None
        patches.append(Patch(ident=ident, lab=lab, xyz=xyz, rgb=rgb))
    return PatchSet(source=source, patches=patches)


def parse_cgats(text: str, source: str = "<string>", white: Triple = D50) -> PatchSet:
    """Read a CGATS table out of ``text``.

    ``white`` is used only when the file carries XYZ and no Lab. Argyll's
    profile connection space is D50, which is why that is the default; a file
    that states its own illuminant in the header is not second-guessed here,
    because CGATS has no reliable keyword for it across writers.
    """
    columns: List[str] = []
    rows: List[List[str]] = []
    mode = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        upper = line.upper()
        if upper == "BEGIN_DATA_FORMAT":
            mode = "format"
            continue
        if upper == "END_DATA_FORMAT":
            mode = None
            continue
        if upper == "BEGIN_DATA":
            mode = "data"
            continue
        if upper == "END_DATA":
            mode = None
            continue
        if mode == "format":
            columns.extend(line.split())
        elif mode == "data":
            rows.append(line.split())

    if not columns:
        raise CgatsError(f"{source}: no BEGIN_DATA_FORMAT block")
    if not rows:
        raise CgatsError(f"{source}: no data rows")
    return _rows_to_patches(source, columns, rows, white)


def parse_csv(text: str, source: str = "<string>", white: Triple = D50) -> PatchSet:
    """Read a header-row CSV of patches."""
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if r and any(c.strip() for c in r)]
    if not rows:
        raise CgatsError(f"{source}: empty")
    columns = [c.strip() for c in rows[0]]
    body = [[c.strip() for c in r] for r in rows[1:]]
    if not body:
        raise CgatsError(f"{source}: header row only")
    return _rows_to_patches(source, columns, body, white)


def load(path: str | Path, white: Triple = D50) -> PatchSet:
    """Read a patch file, choosing the reader by content rather than suffix.

    A ``.txt`` may be either shape and a ``.cie`` written by hand may be a CSV,
    so the presence of a ``BEGIN_DATA`` block decides it.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    if "BEGIN_DATA" in text.upper():
        return parse_cgats(text, source=str(p), white=white)
    return parse_csv(text, source=str(p), white=white)
