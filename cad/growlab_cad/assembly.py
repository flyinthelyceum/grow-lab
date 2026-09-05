"""The whole station, as one compound of labelled parts.

Every part is built in world coordinates from ``params.py``, so assembly is
composition, not positioning. The labels survive STEP export and become the
component names in Fusion.

Two kinds of part:

* **Fabricated** — plinth, base frame, rear door, tray, pads, mast, and the
  instrument case, fascia and backplate. These must not interfere.
  ``interferences()`` checks every pair and is what the test suite asserts on.
* **Reference** — the CMU, the reservoir, the LED heatsink. Bought or
  undimensioned; present so the composition reads and clearances can be
  judged, and excluded from the interference check. Being here is a claim that
  a part is not ours to cut, and it is worth re-reading occasionally: the
  fixture sat in this list for months on the strength of nobody having decided
  what it was, and the fixture arm was here once too, which meant a fabricated
  steel part went unchecked.
"""

from __future__ import annotations

from itertools import combinations

from build123d import Compound, Part

from . import canopy, case, cmu, fixture, mast, plinth, tray
from .params import IN


def fabricated() -> dict[str, Part]:
    return {
        "plinth": plinth.build(),
        "base_frame": plinth.build_frame(),
        "rear_door": plinth.build_rear_door(),
        "tray": tray.build(),
        "pads": tray.build_pads(),
        "mast": mast.build(),
        "case": case.build(),
        "fascia": plinth.build_fascia(),
        "backplate": plinth.build_backplate(),
        "canopy_carriage": canopy.build_carriage(),
        # The lightbox is fabricated, not bought. It spent the whole project
        # filed as reference — a box of plausible size, excluded from the
        # interference check — because nobody had decided what it was made of.
        # Now that it is a folded steel channel it is checked like anything
        # else we cut.
        "lightbox": fixture.build(),
    }


def reference() -> dict[str, Part]:
    return {
        "cmu": cmu.build(),
        "reservoir": plinth.build_reservoir(),
        "led_heatsink": fixture.build_heatsink(),
    }


def _shared_in3(a: Part, b: Part) -> float:
    """Shared volume of two solids, in in³.

    A kernel failure here is not "no overlap" — it is a check that did not
    run. Raise with the pair named rather than report a clean result.
    """
    try:
        return (a & b).volume / IN**3
    except Exception as exc:  # noqa: BLE001 — re-raised with context
        raise RuntimeError(f"intersection check failed for {a.label!r} ∩ {b.label!r}: {exc}") from exc


def interferences(parts: dict[str, Part], *, tolerance_in3: float = 0.001) -> list[tuple[str, str, float]]:
    """Pairs of parts whose solids overlap by more than ``tolerance_in3``.

    Touching faces (a door in its opening, a mast standing on the floor) have
    zero shared volume and do not count. Returns volumes in in³.
    """
    found = []
    for (na, a), (nb, b) in combinations(parts.items(), 2):
        shared = _shared_in3(a, b)
        if shared > tolerance_in3:
            found.append((na, nb, round(shared, 4)))
    return found


def build() -> Compound:
    parts = {**fabricated(), **reference()}
    children = list(parts.values())
    return Compound(label="growlab_v1_station", children=children)
