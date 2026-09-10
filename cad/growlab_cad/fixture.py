"""The lightbox: a folded steel channel over the on-hand aluminium heatsink.

For most of this project the fixture was an *envelope* — a box of plausible
size, filed as a reference part, excluded from the interference check. That was
a fair description of a bought component and a poor one of this: every lighting
document specified the electronics (which boards, which driver, that they need a
heatsink) and none of them ever said what the **body** was. No material, no
finish, no construction, for the second most visible object in the piece.

Decided 2026-09-05: **a white steel channel over the aluminium bar.**

* **Steel is what is specified, shown and painted**, with the rest of the metal
  register. No aluminium is fabricated for V1.
* **The aluminium heatsink stays, inside, unseen.** Steel conducts at roughly a
  quarter of aluminium's rate, so an all-steel heatsink would want several times
  the area to shed the same watts — a physically bigger object hanging over the
  plant, which is precisely the mistake the fan taught. The bar does the
  conducting; the shell does the looking.
* **Open at the bottom.** That face is the light aperture, so there is nothing
  to fabricate there and nothing to obstruct.
* **Slotted along the top, open at the ends.** `LIGHTING_SYSTEM.md` asks for
  free airflow round the heatsink. An open-bottomed channel with a row of slots
  above the fins is a chimney: air in at the aperture, out at the top. A closed
  box would be an oven, and LED life is the thing thermal management is for.

It hangs from the cross bar that runs along its back edge — see ``canopy.py``,
where the arm and bar are welded to the collar as one weldment.

Each LM301H + heatsink module was calipered 2026-09-10: 15.5 × 1.575 ×
0.525 in. Two modules sit side by side (15.5 × 3.15 × 0.525 combined).
Much smaller than the original guesses (14 × 4 × 1); the shell clears the
pair with wide margin and the head is well under its weight budget.
"""

from __future__ import annotations

from build123d import Part

from . import params as P
from ._shapes import box, labelled


def shell_z0() -> float:
    """The channel's bottom edge — the light aperture's plane."""
    return P.FIXTURE_Z


def heatsink_z0() -> float:
    """The bar sits up under the channel's top, where the fins meet the slots."""
    return P.FIXTURE_Z + P.FIXTURE_H - P.LIGHTBOX_T - P.HEATSINK_H


def vent_xs() -> list[float]:
    """Slot centres along the top, spread over the heatsink's own width."""
    span = P.HEATSINK_W - P.LIGHTBOX_VENT_W
    step = span / (P.LIGHTBOX_VENT_N - 1)
    return [P.FIXTURE_X - span / 2 + i * step for i in range(P.LIGHTBOX_VENT_N)]


def build_shell() -> Part:
    """The folded channel: top, two sides, two ends, open bottom, vented."""
    t = P.LIGHTBOX_T
    outer = box(P.FIXTURE_W, P.FIXTURE_D, P.FIXTURE_H,
                at=(P.FIXTURE_X, P.FIXTURE_Y, shell_z0()))
    # Hollow it from below: the bottom stays open, so the cutter runs out
    # through the aperture rather than leaving a floor.
    outer -= box(P.FIXTURE_W - 2 * t, P.FIXTURE_D - 2 * t, P.FIXTURE_H - t + 0.5,
                 at=(P.FIXTURE_X, P.FIXTURE_Y, shell_z0() - 0.5))

    # Vent slots through the top, over the fins.
    for x in vent_xs():
        outer -= box(P.LIGHTBOX_VENT_W, P.LIGHTBOX_VENT_L, t * 3,
                     at=(x, P.FIXTURE_Y, shell_z0() + P.FIXTURE_H - t * 1.5))

    # End slots: the chimney's outlets, and what stops the ends reading as a
    # closed box from the side — the view a person gets standing beside it.
    for sx in (-1, 1):
        x = P.FIXTURE_X + sx * (P.FIXTURE_W / 2 - P.LIGHTBOX_END_INSET)
        outer -= box(t * 3, P.LIGHTBOX_VENT_L, P.FIXTURE_H - 2 * t,
                     at=(x, P.FIXTURE_Y, shell_z0() + t))

    return labelled(outer, "lightbox_shell")


def build_heatsink() -> Part:
    """Reference: the aluminium bar already on hand, calipered 2026-09-10."""
    return labelled(
        box(P.HEATSINK_W, P.HEATSINK_D, P.HEATSINK_H,
            at=(P.FIXTURE_X, P.FIXTURE_Y, heatsink_z0())),
        "led_heatsink",
    )


def build() -> Part:
    """The fabricated part. The heatsink is reference and is not included."""
    return build_shell()
