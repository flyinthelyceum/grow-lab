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

FORMS = {
    "design": {},
    "design+frame": {"GROWLAB_FRAME": "1"},
    "box": {"GROWLAB_FASCIA": "0"},
    "box+frame": {"GROWLAB_FASCIA": "0", "GROWLAB_FRAME": "1"},
}


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
