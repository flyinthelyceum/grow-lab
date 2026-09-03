"""pH probe health from the EZO-pH `Slope,?` command.

Thresholds come from the EZO-pH datasheet V6.1, "Understanding pH slope"
(pages 68-70), not from judgement: new probe slope >95%, zero offset within
+/-5 mV, and beyond 10 mV the datasheet says "noticeable performance issues".
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pi.drivers.ezo_ph import (
    OFFSET_DEGRADED_MV,
    SLOPE_HEALTHY_PERCENT,
    EZOPhDriver,
    ProbeSlope,
    parse_slope,
)


class TestParseSlope:
    def test_datasheet_example(self):
        """The exact response printed in the datasheet."""
        slope = parse_slope("?Slope,99.7,100.3,-0.89")
        assert slope == ProbeSlope(99.7, 100.3, -0.89)

    def test_tolerates_missing_leading_question_mark(self):
        assert parse_slope("Slope,99.7,100.3,-0.89") is not None

    def test_tolerates_trailing_whitespace_and_nulls(self):
        assert parse_slope("  ?Slope,98.2,97.8,-1.2  \n") == ProbeSlope(
            98.2, 97.8, -1.2
        )

    def test_integer_fields(self):
        assert parse_slope("?Slope,100,100,0") == ProbeSlope(100.0, 100.0, 0.0)

    @pytest.mark.parametrize(
        "response",
        [
            "",
            "garbage",
            "?Slope,",
            "?Slope,1,2",          # too few fields
            "?Slope,a,b,c",        # not numbers
            "6.42",                # a pH reading, not a slope
            "*OK",
        ],
    )
    def test_rejects_anything_else(self, response):
        """A garbled read must never become a health verdict."""
        assert parse_slope(response) is None


class TestVerdict:
    def test_uncalibrated_default_is_recognised(self):
        """100/100/0 is the pre-calibration default, not a perfect probe."""
        slope = ProbeSlope(100.0, 100.0, 0.0)
        assert slope.is_uncalibrated
        assert slope.verdict == "uncalibrated"

    def test_healthy(self):
        assert ProbeSlope(99.7, 100.3, -0.89).verdict == "healthy"

    def test_healthy_at_the_datasheet_boundary(self):
        assert ProbeSlope(95.0, 95.0, 5.0).verdict == "healthy"
        assert ProbeSlope(95.0, 95.0, -5.0).verdict == "healthy"

    def test_marginal_when_only_the_offset_has_drifted(self):
        assert ProbeSlope(98.0, 99.0, 8.0).verdict == "marginal"

    def test_failing_on_low_slope(self):
        assert ProbeSlope(61.2, 88.4, -1.0).verdict == "failing"

    def test_failing_on_excessive_offset(self):
        assert ProbeSlope(99.0, 99.0, 14.0).verdict == "failing"

    def test_one_bad_half_fails_the_probe(self):
        """Acid and base are evaluated separately; the worse one governs."""
        assert ProbeSlope(99.9, 71.0, 0.0).verdict == "failing"
        assert ProbeSlope(71.0, 99.9, 0.0).verdict == "failing"

    def test_worst_slope(self):
        assert ProbeSlope(99.9, 71.0, 0.0).worst_slope == 71.0

    def test_offset_sign_does_not_matter(self):
        assert (
            ProbeSlope(99.0, 99.0, OFFSET_DEGRADED_MV + 1).verdict
            == ProbeSlope(99.0, 99.0, -(OFFSET_DEGRADED_MV + 1)).verdict
        )

    def test_a_probe_reading_its_isopotential_point_fails(self):
        """The observed failure: near-zero slope, needle parked at pH 7."""
        assert ProbeSlope(2.0, 3.0, 0.5).verdict == "failing"


class TestReadSlope:
    async def test_parses_a_good_response(self):
        driver = EZOPhDriver()
        driver.query = AsyncMock(return_value="?Slope,99.7,100.3,-0.89")
        slope = await driver.read_slope()
        assert slope.verdict == "healthy"
        driver.query.assert_awaited_once_with("Slope,?")

    async def test_none_when_the_circuit_does_not_answer(self):
        driver = EZOPhDriver()
        driver.query = AsyncMock(return_value=None)
        assert await driver.read_slope() is None

    async def test_none_on_a_garbled_response(self):
        driver = EZOPhDriver()
        driver.query = AsyncMock(return_value="\x02\xff junk")
        assert await driver.read_slope() is None


class TestThresholdsMatchTheDatasheet:
    def test_slope_threshold(self):
        assert SLOPE_HEALTHY_PERCENT == 95.0

    def test_degraded_offset_threshold(self):
        assert OFFSET_DEGRADED_MV == 10.0
