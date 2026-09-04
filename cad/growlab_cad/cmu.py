"""The vessel: a standard two-core CMU, as reference geometry.

Not a fabricated part — it is bought — but it is the thing everything else is
sized around, so it is modelled at actual dimensions with its two cores open
top and bottom, sitting on its pads at the documented height.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, labelled


def core_size() -> tuple[float, float]:
    """Plan size of one core, from the block's shell and web thicknesses."""
    core_l = (P.CMU_L - 2 * P.CMU_END_SHELL - P.CMU_WEB) / 2
    core_w = P.CMU_W - 2 * P.CMU_FACE_SHELL
    return core_l, core_w


def core_centres() -> tuple[tuple[float, float], tuple[float, float]]:
    """Plan centres of the two cores, either side of the centre web."""
    core_l, _ = core_size()
    offset = P.CMU_WEB / 2 + core_l / 2
    return (P.CMU_X - offset, P.CMU_Y), (P.CMU_X + offset, P.CMU_Y)


def build() -> Part:
    block = box(P.CMU_L, P.CMU_W, P.CMU_H, at=(P.CMU_X, P.CMU_Y, P.CMU_UNDERSIDE_Z))
    core_l, core_w = core_size()
    for cx, cy in core_centres():
        # Through both faces, so the cutter is taller than the block.
        block -= box(core_l, core_w, P.CMU_H + 1.0, at=(cx, cy, P.CMU_UNDERSIDE_Z - 0.5))
    return labelled(block, "cmu_vessel")


def media() -> Part:
    """The coco/perlite fill, to the documented surface — reference only."""
    core_l, core_w = core_size()
    height = P.MEDIA_SURFACE_Z - P.CMU_UNDERSIDE_Z
    fill = None
    for cx, cy in core_centres():
        m = box(core_l, core_w, height, at=(cx, cy, P.CMU_UNDERSIDE_Z))
        fill = m if fill is None else fill + m
    return labelled(fill, "media_reference")
