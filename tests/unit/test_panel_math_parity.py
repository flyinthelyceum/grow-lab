"""The emulator's JS must agree with the hardware's Python, exactly.

The panel emulator at /panel is only useful if the needles move the way the
real movements move. If the JS drifts from `pi/services/meters.py`, the screen
reads plausibly while the mast reads differently — and nobody finds out until
the meters are mounted.

So this is not a comment asking future readers to keep two files in sync. It
runs the actual JS module under node and compares every output to the actual
Python, across a sweep that includes the endpoints and the exact-half cases
where rounding rules diverge.

Skipped cleanly when node is unavailable, the same way the browser tests skip
without Playwright.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from pi.drivers.mcp4728 import clamp_code, differential_codes
from pi.services.meters import apply_calibration, ease_alpha, normalise

MATH_JS = (
    Path(__file__).resolve().parents[2]
    / "pi"
    / "dashboard"
    / "static"
    / "panel"
    / "meter-math.js"
)

_NODE = shutil.which("node") or shutil.which("nodejs")

pytestmark = pytest.mark.skipif(
    _NODE is None, reason="JS/Python parity check requires node"
)

# Tolerance for float round-tripping through JSON. Anything looser would let a
# real mapping difference hide; anything tighter trips on decimal printing.
TOL = 1e-12


def _run_js(cases: dict, tmp_dir: Path) -> dict:
    """Evaluate the shared module against `cases` and return its answers."""
    cases_path = tmp_dir / "cases.json"
    cases_path.write_text(json.dumps(cases))

    script = f"""
import {{ readFileSync }} from "node:fs";
import {{
  normalise, applyCalibration, easeAlpha, clampCode, differentialCodes
}} from {json.dumps(MATH_JS.as_uri())};

const cases = JSON.parse(readFileSync({json.dumps(str(cases_path))}, "utf8"));
const out = {{
  normalise: cases.normalise.map(([v, c, s]) => normalise(v, c, s)),
  calibration: cases.calibration.map(([x, pts]) => applyCalibration(x, pts)),
  ease: cases.ease.map(([dt, tau]) => easeAlpha(dt, tau)),
  clamp: cases.clamp.map((c) => clampCode(c)),
  differential: cases.differential.map(([x, m, s]) => differentialCodes(x, m, s)),
}};
process.stdout.write(JSON.stringify(out));
"""
    result = subprocess.run(
        [_NODE, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"node failed:\n{result.stderr}")
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def cases() -> dict:
    """A sweep wide enough that a mapping difference cannot hide in it."""
    # normalise: on target, either side, both endpoints, well past them, and a
    # zero span (the divide-by-zero guard).
    normalise_cases = []
    for centre, span in ((6.0, 1.0), (1.0, 1.0), (7.2, 0.4), (0.0, 2.5)):
        for offset in (-4.0, -1.0, -0.5, -0.001, 0.0, 0.001, 0.5, 1.0, 4.0):
            normalise_cases.append([centre + offset * span, centre, span])
    normalise_cases += [[6.5, 6.0, 0.0], [6.5, 6.0, -1.0]]

    five_point = [[-1.0, -0.94], [-0.5, -0.47], [0.0, 0.02], [0.5, 0.53], [1.0, 0.97]]
    calibration_cases = [[x / 20.0, five_point] for x in range(-25, 26)]
    calibration_cases += [
        [0.0, []],                        # no table — passes through
        [0.3, [[0.0, 0.0]]],              # one point — passes through
        [0.5, [[0.5, 0.5], [0.5, 0.9]]],  # duplicated commanded value
        [-2.0, five_point],               # below the table
        [2.0, five_point],                # above the table
    ]

    ease_cases = [
        [1 / 30.0, 2.0], [1 / 30.0, 0.5], [0.1, 5.0], [1.0, 1.0],
        [1 / 30.0, 0.0], [1 / 30.0, -1.0], [0.0, 2.0], [10.0, 0.25],
    ]

    clamp_cases = [-5000, -1, 0, 1, 2047, 2048, 4095, 4096, 99999]

    differential_cases = []
    for span_counts in (2048, 1024, 1000, 333):
        for x in (-1.0, -0.75, -0.5, -0.25, -0.001, 0.0, 0.001, 0.25, 0.5, 0.75, 1.0):
            differential_cases.append([x, 2048, span_counts])
    # Deliberate exact-half deltas, where Python rounds to even and
    # Math.round would not.
    differential_cases += [
        [0.5, 2048, 1001], [-0.5, 2048, 1001],
        [0.5, 2048, 1003], [-0.5, 2048, 1003],
        [0.25, 2048, 2],   [-0.25, 2048, 2],
    ]

    return {
        "normalise": normalise_cases,
        "calibration": calibration_cases,
        "ease": ease_cases,
        "clamp": clamp_cases,
        "differential": differential_cases,
    }


@pytest.fixture(scope="module")
def js(cases, tmp_path_factory) -> dict:
    return _run_js(cases, tmp_path_factory.mktemp("parity"))


def test_module_exists():
    assert MATH_JS.is_file(), f"missing shared maths module at {MATH_JS}"


def test_normalise_matches(cases, js):
    for (args, actual) in zip(cases["normalise"], js["normalise"]):
        expected = normalise(*args)
        assert abs(expected - actual) < TOL, f"normalise{tuple(args)}"


def test_calibration_matches(cases, js):
    for ((x, points), actual) in zip(cases["calibration"], js["calibration"]):
        expected = apply_calibration(x, tuple(tuple(p) for p in points))
        assert abs(expected - actual) < TOL, f"apply_calibration({x}, {points})"


def test_ease_matches(cases, js):
    for ((dt, tau), actual) in zip(cases["ease"], js["ease"]):
        expected = ease_alpha(dt, tau)
        assert abs(expected - actual) < TOL, f"ease_alpha({dt}, {tau})"


def test_clamp_matches(cases, js):
    for (code, actual) in zip(cases["clamp"], js["clamp"]):
        assert clamp_code(code) == actual, f"clamp_code({code})"


def test_differential_codes_match(cases, js):
    """Includes the exact-half deltas where JS Math.round would disagree."""
    for ((x, midpoint, span_counts), actual) in zip(
        cases["differential"], js["differential"]
    ):
        expected = differential_codes(
            x, midpoint=midpoint, span_counts=span_counts
        )
        assert list(expected) == actual, (
            f"differential_codes({x}, midpoint={midpoint}, "
            f"span_counts={span_counts})"
        )


def test_easing_reaches_the_target(cases, js):
    """A sanity property, not a parity check: repeated easing converges."""
    alpha = ease_alpha(1 / 30.0, 2.0)
    displayed = 0.0
    for _ in range(30 * 20):  # 20 seconds at 30 Hz
        displayed += (1.0 - displayed) * alpha
    assert math.isclose(displayed, 1.0, abs_tol=1e-4)
