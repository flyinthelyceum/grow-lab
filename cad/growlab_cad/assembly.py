"""The whole station, as one compound of labelled parts.

Every part is built in world coordinates from ``params.py``, so assembly is
composition, not positioning. The labels survive STEP export and become the
component names in Fusion.

Two kinds of part:

* **Fabricated** — plinth, rear door, tray, pads, mast, face. These must not
  interfere. ``interferences()`` checks every pair and is what the test suite
  asserts on.
* **Reference** — the CMU, its media, the reservoir, the LED fixture, the
  console electronics. Bought or undimensioned; present so the composition
  reads and clearances can be judged, excluded from the interference check
  but checked against the fabricated parts as design conflicts.
"""

from __future__ import annotations

from itertools import combinations

from build123d import Compound, Part

from . import cmu, face, fixture, mast, plinth, tray
from .params import IN


def fabricated() -> dict[str, Part]:
    return {
        "plinth": plinth.build(),
        "rear_door": plinth.build_rear_door(),
        "tray": tray.build(),
        "pads": tray.build_pads(),
        "mast": mast.build(),
        "face": face.build(),
    }


def reference() -> dict[str, Part]:
    return {
        "cmu": cmu.build(),
        "media": cmu.media(),
        "reservoir": plinth.build_reservoir(),
        "fixture": fixture.build(),
        "console": plinth.build_console_electronics(),
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


def reference_clashes(fab: dict[str, Part], ref: dict[str, Part], *, tolerance_in3: float = 0.001) -> list[tuple[str, str, float]]:
    """Reference envelopes overlapping fabricated parts.

    Not a build error — the envelopes are bought parts and placeholders — but
    a design conflict worth surfacing: a reservoir that runs into a partition
    is a cabinet that is too shallow, not a modelling mistake.
    """
    found = []
    for nr, r in ref.items():
        for nf, f in fab.items():
            shared = _shared_in3(r, f)
            if shared > tolerance_in3:
                found.append((nr, nf, round(shared, 4)))
    return found


def build() -> Compound:
    parts = {**fabricated(), **reference()}
    children = list(parts.values())
    return Compound(label="growlab_v1_station", children=children)
