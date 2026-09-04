"""Instrument head panel geometry — the face, as data.

One source of truth for what sits where on the 9.50 x 12.00 acrylic face in
the cabinet's front, so the emulator at `/panel`, the hole schedule in
docs/INSTRUMENT_HEAD_PLANS.md, and the CAD (`cad/face.py`, which cuts the
acrylic, and `cad/plinth.py`, which cuts the opening for it) all read the
same numbers instead of drifting apart.

Coordinates follow the fabrication drawings: **inches, origin at the panel's
bottom-left, X right, Y up.** Elements are positioned by centre, which is how
a hole schedule is written and how a drill press is set.

A note on dial dimensions
-------------------------
The head plans were written for Simpson Wide-Vue 1327 movements and specify a
2.79 in cut. The build uses **Weston 301** movements instead, and their cut
diameter is not known — it has to come off a caliper when the meters arrive.

So this module carries the bezel outside diameter (3.50 in, which is what
"3-1/2 inch meter" means and is safe to draw) and deliberately does *not*
carry a cut diameter. The emulator judges a layout by what the eye sees, which
is the bezel; the hole behind it is a fabrication number, and inventing one
would put a second wrong dimension into the drawings.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Face stock, from the panel schedule.
FACE_WIDTH = 9.50
FACE_HEIGHT = 12.00

# Weston 301, 3-1/2 in: nominal bezel outside diameter. Definitional for the
# size class, so safe to draw. The panel cut is pending calipers.
DIAL_BEZEL_OD = 3.50
DIAL_CUT_DIAMETER: float | None = None

# Inky Impression 7.3 in: stated active area 160 x 96 mm, and its pixel grid.
WINDOW_WIDTH = 6.30
WINDOW_HEIGHT = 3.78
INKY_PIXELS = (800, 480)

# Rail hardware, from the hole schedule.
JEWEL_DIAMETER = 1.00  # NOS Dialco 1 in jewel pilot
AMBER_DIAMETER = 0.50  # VCC 1092 amber, tend-me
KNOB_DIAMETER = 0.375  # pot bushing; the knob body is larger
CORNER_SCREW_INSET = 0.375


@dataclass(frozen=True)
class Element:
    """One thing on the face, positioned by its centre."""

    id: str
    kind: str  # dial | window | jewel | amber | knob
    x: float
    y: float
    width: float
    height: float
    label: str = ""

    @property
    def left(self) -> float:
        return self.x - self.width / 2

    @property
    def right(self) -> float:
        return self.x + self.width / 2

    @property
    def bottom(self) -> float:
        return self.y - self.height / 2

    @property
    def top(self) -> float:
        return self.y + self.height / 2

    def overlaps(self, other: Element) -> bool:
        return not (
            self.right <= other.left
            or other.right <= self.left
            or self.top <= other.bottom
            or other.top <= self.bottom
        )


@dataclass(frozen=True)
class Layout:
    """A candidate arrangement of the face."""

    id: str
    name: str
    rationale: str
    elements: tuple[Element, ...]
    is_schedule: bool = False  # True for the one the drawings currently specify

    def by_id(self, element_id: str) -> Element | None:
        for element in self.elements:
            if element.id == element_id:
                return element
        return None

    def collisions(self) -> list[tuple[str, str]]:
        """Overlapping element pairs. A layout that reports any is unbuildable."""
        found = []
        items = list(self.elements)
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                if a.overlaps(b):
                    found.append((a.id, b.id))
        return found

    def out_of_bounds(self) -> list[str]:
        """Elements that run off the face."""
        return [
            e.id
            for e in self.elements
            if e.left < 0
            or e.bottom < 0
            or e.right > FACE_WIDTH
            or e.top > FACE_HEIGHT
        ]


def _dial(element_id: str, x: float, y: float, label: str) -> Element:
    return Element(
        id=element_id,
        kind="dial",
        x=x,
        y=y,
        width=DIAL_BEZEL_OD,
        height=DIAL_BEZEL_OD,
        label=label,
    )


def _window(x: float, y: float) -> Element:
    return Element(
        id="window",
        kind="window",
        x=x,
        y=y,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        label="Inky Impression 7.3",
    )


def _rail(jewel_x: float, amber_x: float, k1_x: float, k2_x: float, y: float):
    return (
        Element("jewel", "jewel", jewel_x, y, JEWEL_DIAMETER, JEWEL_DIAMETER, "power"),
        Element("amber", "amber", amber_x, y, AMBER_DIAMETER, AMBER_DIAMETER, "tend me"),
        Element("knob1", "knob", k1_x, y, KNOB_DIAMETER, KNOB_DIAMETER, "K1"),
        Element("knob2", "knob", k2_x, y, KNOB_DIAMETER, KNOB_DIAMETER, "K2"),
    )


# -- Candidate layouts -------------------------------------------------------
#
# Four arrangements that fit the stock. A fifth was drawn and discarded: a
# stacked column of both dials needs 3.50 + 3.50 for the movements plus 3.78
# for the window plus roughly 1.5 of rail, which is 12.28 in against 12.00 of
# face. It does not fit, at any spacing. See LAYOUT_NOTES.

SCHEDULE = Layout(
    id="schedule",
    name="Schedule",
    rationale=(
        "Exactly what the drawings specify. Dials high and close — centres 4.00 "
        "apart, so 0.50 between bezels and 1.00 to each edge. The pair reads as "
        "one instrument rather than two gauges, and every rail element lands on a "
        "column derived from the meter mounting holes. Nothing is placed by eye."
    ),
    is_schedule=True,
    elements=(
        _dial("dial_ph", 2.750, 9.500, "pH"),
        _dial("dial_ec", 6.750, 9.500, "EC"),
        _window(4.750, 5.360),
        *_rail(1.625, 2.750, 6.750, 7.875, 1.625),
    ),
)

WIDE = Layout(
    id="wide",
    name="Wide pair",
    rationale=(
        "The same grid logic with the dials pushed out to 2.375 / 7.125 — 1.25 "
        "between bezels, 0.625 to each edge. Air between the movements and less at "
        "the margins. Tests whether the tight pair in the schedule reads as "
        "deliberate or as crowded; the trade is that separated dials start to read "
        "as two instruments rather than one."
    ),
    elements=(
        _dial("dial_ph", 2.375, 9.500, "pH"),
        _dial("dial_ec", 7.125, 9.500, "EC"),
        _window(4.750, 5.360),
        *_rail(1.375, 2.375, 7.125, 8.375, 1.625),
    ),
)

OFFSET = Layout(
    id="offset",
    name="Offset pair",
    rationale=(
        "Dials at different heights — pH at 10.00, EC at 9.00 — keeping the pair "
        "but breaking its symmetry. Argues that a face read as apparatus rather "
        "than as a product should show the asymmetry of what it measures. The risk "
        "is that it reads as an error rather than as intent, which is exactly what "
        "an emulator is for."
    ),
    elements=(
        _dial("dial_ph", 2.750, 10.000, "pH"),
        _dial("dial_ec", 6.750, 9.000, "EC"),
        _window(4.750, 5.100),
        *_rail(1.625, 2.750, 6.750, 7.875, 1.625),
    ),
)

INVERTED = Layout(
    id="inverted",
    name="Inverted",
    rationale=(
        "Window on top, dials beneath it. Inverts the hierarchy: the slow "
        "e-ink face reads first and the instantaneous needles second, which is the "
        "opposite of what the schedule asserts. Worth seeing, because the whole "
        "argument for centre-zero dials is that deviation should be legible at a "
        "glance — and a glance lands at the top of the panel."
    ),
    elements=(
        _window(4.750, 9.100),
        _dial("dial_ph", 2.750, 4.400, "pH"),
        _dial("dial_ec", 6.750, 4.400, "EC"),
        *_rail(1.625, 2.750, 6.750, 7.875, 1.100),
    ),
)

LAYOUTS: tuple[Layout, ...] = (SCHEDULE, WIDE, OFFSET, INVERTED)

LAYOUT_NOTES = (
    "A stacked-dial column does not fit the stock: two 3.50 in movements plus the "
    "3.78 in window plus roughly 1.5 in of rail is 12.28 in against 12.00 in of "
    "face. Drawn and discarded rather than shown at an impossible spacing.",
    "Dial cut diameter is pending calipers on the Weston 301 bezels. The drawings "
    "still carry Simpson Wide-Vue 1327 numbers (2.79 in cut, 2.25 in square stud "
    "pattern), which do not apply to these movements. Bezel OD of 3.50 in is "
    "nominal for the size class and is what these drawings show.",
)


def layout_by_id(layout_id: str) -> Layout | None:
    for layout in LAYOUTS:
        if layout.id == layout_id:
            return layout
    return None


def _element_payload(element: Element) -> dict:
    return {
        "id": element.id,
        "kind": element.kind,
        "x": element.x,
        "y": element.y,
        "width": element.width,
        "height": element.height,
        "label": element.label,
    }


def geometry_payload() -> dict:
    """Every candidate layout plus the face constants, for the emulator."""
    return {
        "face": {"width": FACE_WIDTH, "height": FACE_HEIGHT},
        "dial": {
            "bezel_od": DIAL_BEZEL_OD,
            "cut_diameter": DIAL_CUT_DIAMETER,
            "cut_pending_calipers": DIAL_CUT_DIAMETER is None,
        },
        "window": {
            "width": WINDOW_WIDTH,
            "height": WINDOW_HEIGHT,
            "pixels": {"width": INKY_PIXELS[0], "height": INKY_PIXELS[1]},
        },
        "corner_screw_inset": CORNER_SCREW_INSET,
        "notes": list(LAYOUT_NOTES),
        "layouts": [
            {
                "id": layout.id,
                "name": layout.name,
                "rationale": layout.rationale,
                "is_schedule": layout.is_schedule,
                "collisions": layout.collisions(),
                "out_of_bounds": layout.out_of_bounds(),
                "elements": [_element_payload(e) for e in layout.elements],
            }
            for layout in LAYOUTS
        ],
    }
