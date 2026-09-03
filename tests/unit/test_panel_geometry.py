"""Panel geometry — the layouts must be buildable, not just drawable.

The emulator's whole purpose is to catch a bad layout before acrylic is cut,
so a candidate that cannot physically exist must never reach the screen.
"""

from __future__ import annotations

import pytest

from pi.dashboard.panel_geometry import (
    DIAL_BEZEL_OD,
    DIAL_CUT_DIAMETER,
    FACE_HEIGHT,
    FACE_WIDTH,
    LAYOUTS,
    SCHEDULE,
    Element,
    geometry_payload,
    layout_by_id,
)


class TestElement:
    def test_edges(self):
        e = Element("x", "dial", 4.0, 6.0, 3.5, 3.5)
        assert e.left == 2.25
        assert e.right == 5.75
        assert e.bottom == 4.25
        assert e.top == 7.75

    def test_overlap_detection(self):
        a = Element("a", "dial", 2.0, 6.0, 3.5, 3.5)
        b = Element("b", "dial", 4.0, 6.0, 3.5, 3.5)
        assert a.overlaps(b)

    def test_touching_is_not_overlapping(self):
        a = Element("a", "dial", 2.0, 6.0, 2.0, 2.0)  # right edge 3.0
        b = Element("b", "dial", 4.0, 6.0, 2.0, 2.0)  # left edge 3.0
        assert not a.overlaps(b)

    def test_vertical_separation(self):
        a = Element("a", "dial", 4.0, 9.0, 3.5, 3.5)
        b = Element("b", "dial", 4.0, 3.0, 3.5, 3.5)
        assert not a.overlaps(b)


@pytest.mark.parametrize("layout", LAYOUTS, ids=[l.id for l in LAYOUTS])
class TestEveryLayoutIsBuildable:
    def test_no_collisions(self, layout):
        assert layout.collisions() == [], (
            f"{layout.id} has overlapping elements — it cannot be built"
        )

    def test_within_the_face(self, layout):
        assert layout.out_of_bounds() == [], (
            f"{layout.id} places elements off the {FACE_WIDTH} x {FACE_HEIGHT} face"
        )

    def test_has_both_dials_and_a_window(self, layout):
        ids = {e.id for e in layout.elements}
        assert {"dial_ph", "dial_ec", "window"} <= ids

    def test_has_the_full_rail(self, layout):
        ids = {e.id for e in layout.elements}
        assert {"jewel", "amber", "knob1", "knob2"} <= ids

    def test_dials_are_bezel_sized(self, layout):
        for element in layout.elements:
            if element.kind == "dial":
                assert element.width == DIAL_BEZEL_OD
                assert element.height == DIAL_BEZEL_OD


class TestSchedule:
    def test_matches_the_drawings(self):
        """Hole schedule, docs/INSTRUMENT_HEAD_PLANS.md Rev A."""
        assert SCHEDULE.by_id("dial_ph").x == 2.750
        assert SCHEDULE.by_id("dial_ph").y == 9.500
        assert SCHEDULE.by_id("dial_ec").x == 6.750
        assert SCHEDULE.by_id("window").x == 4.750
        assert SCHEDULE.by_id("window").y == 5.360
        assert SCHEDULE.by_id("jewel").x == 1.625

    def test_is_the_only_one_flagged_as_the_drawings(self):
        flagged = [l for l in LAYOUTS if l.is_schedule]
        assert len(flagged) == 1
        assert flagged[0] is SCHEDULE

    def test_rail_sits_on_the_meter_columns(self):
        """Grid logic: nothing is placed by eye."""
        assert SCHEDULE.by_id("amber").x == SCHEDULE.by_id("dial_ph").x
        assert SCHEDULE.by_id("knob1").x == SCHEDULE.by_id("dial_ec").x


class TestCutDiameter:
    def test_is_not_asserted(self):
        """The Weston cut is unmeasured. Inventing one would put a second
        wrong dimension into the drawings alongside the Simpson figures."""
        assert DIAL_CUT_DIAMETER is None

    def test_payload_flags_it_as_pending(self):
        payload = geometry_payload()
        assert payload["dial"]["cut_pending_calipers"] is True
        assert payload["dial"]["cut_diameter"] is None


class TestPayload:
    def test_shape(self):
        payload = geometry_payload()
        assert payload["face"] == {"width": FACE_WIDTH, "height": FACE_HEIGHT}
        assert len(payload["layouts"]) == len(LAYOUTS)
        assert payload["window"]["pixels"] == {"width": 800, "height": 480}
        assert payload["notes"]

    def test_every_layout_reports_clean(self):
        for layout in geometry_payload()["layouts"]:
            assert layout["collisions"] == []
            assert layout["out_of_bounds"] == []

    def test_is_json_serialisable(self):
        import json

        json.dumps(geometry_payload())


class TestLookup:
    def test_by_id(self):
        assert layout_by_id("schedule") is SCHEDULE

    def test_unknown_is_none(self):
        assert layout_by_id("nope") is None


def test_stacked_dials_really_do_not_fit():
    """The discarded fifth layout, asserted rather than asserted in prose."""
    window_height = 3.78
    rail = 1.5
    needed = DIAL_BEZEL_OD * 2 + window_height + rail
    assert needed > FACE_HEIGHT
