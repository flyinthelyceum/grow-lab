"""Templates must stay compatible with the dashboard's CSP.

script-src is 'self' plus the Cloudflare Insights beacon, with no
'unsafe-inline' and no 'unsafe-hashes'. That blocks inline event handler
attributes outright. The failure is silent: the browser logs a CSP
violation and simply never runs the handler.

This bit the Google Fonts links, which used the async-CSS trick
    <link rel="stylesheet" media="print" onload="this.media='all'">
so the blocked handler left every page stuck on media="print" and the
Space Mono / Inter faces never applied on screen.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "pi" / "dashboard" / "templates"

# macOS writes AppleDouble sidecars next to real files on exFAT volumes.
TEMPLATES = sorted(
    p for p in TEMPLATE_DIR.glob("*.html") if not p.name.startswith("._")
)

INLINE_HANDLER = re.compile(r"\son[a-z]+\s*=\s*[\"']", re.IGNORECASE)


def test_templates_were_found():
    assert TEMPLATES, f"no templates discovered under {TEMPLATE_DIR}"


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_no_inline_event_handlers(template: Path):
    offenders = [
        line.strip()
        for line in template.read_text(encoding="utf-8").splitlines()
        if INLINE_HANDLER.search(line)
    ]
    assert not offenders, (
        f"{template.name} uses inline event handlers, which the CSP blocks "
        f"silently. Move the behaviour into a served .js file. Offending "
        f"lines: {offenders}"
    )


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_stylesheets_are_not_stranded_on_print_media(template: Path):
    """A stylesheet left at media="print" never applies to the screen."""
    for line in template.read_text(encoding="utf-8").splitlines():
        if "rel=\"stylesheet\"" in line and 'media="print"' in line:
            pytest.fail(
                f"{template.name} loads a stylesheet with media=\"print\": "
                f"{line.strip()}"
            )
