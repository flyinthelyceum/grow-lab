"""Every form candidate must build clean, not just the default.

The form knobs (``GROWLAB_FASCIA``, ``GROWLAB_FRAME``) change the geometry at
import time, so each candidate is built in its own process through the real
entry point, exactly as the viewer builds it. Slow (a kernel build each), and
worth it: a candidate that interferes is not a candidate.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("build123d")

REPO = Path(__file__).resolve().parents[2]


def _clean_env(**knobs: str) -> dict:
    """The caller's shell may carry GROWLAB_* knobs; a candidate must not inherit them."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GROWLAB_")}
    env.update(knobs)
    return env

# Both knobs are set explicitly in every entry, never left to the default.
# They were once left to it, and the suite quietly tested half of what it named:
# with FASCIA and FRAME both defaulting True, "design" and "design+frame"
# resolved to the same build, as did "box" and "box+frame", and no entry ever
# set GROWLAB_FRAME=0 — so the plinth form was never built at all.
FORMS = {
    "design":             {"GROWLAB_FASCIA": "1", "GROWLAB_FRAME": "1"},
    "design on a plinth": {"GROWLAB_FASCIA": "1", "GROWLAB_FRAME": "0"},
    "box on a frame":     {"GROWLAB_FASCIA": "0", "GROWLAB_FRAME": "1"},
    "box":                {"GROWLAB_FASCIA": "0", "GROWLAB_FRAME": "0"},
}


def test_the_named_forms_are_four_distinct_builds():
    """Four names must mean four builds, whatever the knobs default to.

    This is the guard the collapse got past: it is cheap, needs no kernel, and
    fails loudly if anyone reintroduces an entry that relies on a default.
    """
    resolved = {frozenset(knobs.items()) for knobs in FORMS.values()}
    assert len(resolved) == len(FORMS), "two named forms resolve to the same build"

    for name, knobs in FORMS.items():
        assert set(knobs) == {"GROWLAB_FASCIA", "GROWLAB_FRAME"}, (
            f"{name!r} leaves a knob to its default; set both explicitly"
        )

    assert {k["GROWLAB_FASCIA"] for k in FORMS.values()} == {"0", "1"}
    assert {k["GROWLAB_FRAME"] for k in FORMS.values()} == {"0", "1"}


@pytest.mark.parametrize("form", FORMS, ids=list(FORMS))
def test_form_builds_without_interference_or_conflict(form):
    env = _clean_env(**FORMS[form])
    r = subprocess.run(
        [sys.executable, str(REPO / "cad" / "build.py"), "--check"],
        env=env, cwd=str(REPO), capture_output=True, text=True, timeout=600,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no interference between fabricated parts" in r.stdout, r.stdout
    assert "no design conflicts" in r.stdout, r.stdout
    assert "static lift, low water → emitters: 13.0 in" in r.stdout, "a form must not move the lift"


def test_bad_flag_names_itself():
    env = _clean_env(GROWLAB_FRAME="maybe")
    r = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); import cad.growlab_cad.params"],
        env=env, cwd=str(REPO), capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "GROWLAB_FRAME='maybe'" in r.stderr
