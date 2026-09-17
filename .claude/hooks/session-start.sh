#!/bin/bash
# SessionStart hook for Claude Code (local and on the web).
# 1. Installs the components pre-commit lint (.git/hooks is not versioned).
# 2. Makes the `components` package importable in .venv (created if absent):
#    editable from a local clone of flyinthelyceum/components when there is one,
#    otherwise the pinned git dependency.
# 3. Keeps that dependency CURRENT, not merely present. See below.
# Idempotent and quiet. Never fails the session: offline pip warns and continues.
set -uo pipefail
cd "$CLAUDE_PROJECT_DIR"

sh scripts/install-hooks.sh >/dev/null 2>&1 || echo "session-start: warning: install-hooks.sh failed" >&2

if [ ! -x .venv/bin/python ]; then
  # The package needs Python 3.11+; /usr/bin/python3 on macOS is older.
  for cand in python3.14 python3.13 python3.12 python3.11 python3; do
    command -v "$cand" >/dev/null 2>&1 || continue
    "$cand" -m venv .venv >/dev/null 2>&1 && break
  done
  [ -x .venv/bin/python ] || echo "session-start: warning: could not create .venv" >&2
fi
PY=""
[ -x .venv/bin/python ] && PY=.venv/bin/python
if [ -n "$PY" ] && ! "$PY" -c "import components" >/dev/null 2>&1; then
  LIB_SRC="${COMPONENTS_REPO:-$HOME/projects/components}"
  if [ -f "$LIB_SRC/components/__init__.py" ]; then
    "$PY" -m pip install --quiet -e "$LIB_SRC" >/dev/null 2>&1 \
      || echo "session-start: warning: pip install -e $LIB_SRC failed (offline?); continuing" >&2
  else
    "$PY" -m pip install --quiet \
      "components @ git+https://github.com/flyinthelyceum/components.git@components-v1" >/dev/null 2>&1 \
      || echo "session-start: warning: pip install of components failed (offline?); continuing" >&2
  fi
fi
if [ -n "$PY" ] && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"$CLAUDE_PROJECT_DIR/.venv/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi
# --- Freshness -------------------------------------------------------------
# `components-v1` is a MOVING tag, so "already importable" says nothing about
# which version is importable. The block above only installs when the import
# FAILS, which means a stale copy is invisible: one session here ran the whole
# suite green on v1.16 while the library was at v1.32. Every AS7341 constant
# read None, params.py silently kept its ESTIMATEs, and the case was drawn to a
# socket height that had already been measured and disagreed by 1.8 mm.
#
# So compare commits, not presence. pip records the exact commit a VCS install
# came from in direct_url.json; git ls-remote says where the tag points now.
#
# An editable install needs the same treatment, not a pass. "It tracks the
# clone" is only reassuring if the clone is current, and the first run of this
# check found a clone 41 commits behind quietly shadowing a newer copy. A clean
# clone is fast-forwarded; a dirty one is left alone and said out loud, because
# someone is mid-measurement in it and their work outranks this.
if [ -z "${PY:-}" ] && command -v python3 >/dev/null 2>&1 \
   && python3 -c "import components" >/dev/null 2>&1; then
  # No .venv, but the library is importable from the ambient interpreter —
  # which is how the hosted sessions are set up. Check the copy actually in use.
  PY=python3
fi
if [ -n "${PY:-}" ] && "$PY" -c "import components" >/dev/null 2>&1; then
  HAVE=$("$PY" - <<'EOF' 2>/dev/null
import json, importlib.metadata as md
try:
    raw = md.distribution("components").read_text("direct_url.json")
except Exception:
    raw = None
info = json.loads(raw) if raw else {}
if info.get("dir_info", {}).get("editable"):
    print("editable")
else:
    print(info.get("vcs_info", {}).get("commit_id", ""))
EOF
)
  if [ "$HAVE" = "editable" ]; then
    CLONE=$("$PY" - <<'EOF' 2>/dev/null
import json, importlib.metadata as md
from urllib.parse import urlparse, unquote
try:
    info = json.loads(md.distribution("components").read_text("direct_url.json"))
    print(unquote(urlparse(info.get("url", "")).path))
except Exception:
    pass
EOF
)
    if [ -n "$CLONE" ] && [ -d "$CLONE/.git" ]; then
      if [ -n "$(git -C "$CLONE" status --porcelain 2>/dev/null)" ]; then
        LIB_NOTE=" (editable from a clone with uncommitted changes; left alone)"
      elif git -C "$CLONE" fetch --quiet origin >/dev/null 2>&1 \
           && ! git -C "$CLONE" merge --ff-only --quiet '@{u}' >/dev/null 2>&1; then
        LIB_NOTE=" (editable clone has diverged from its upstream; fix it by hand)"
      fi
    fi
  elif [ -n "$HAVE" ]; then
    WANT=$(git ls-remote https://github.com/flyinthelyceum/components.git \
             refs/tags/components-v1 2>/dev/null | awk 'NR==1{print $1}')
    # Empty WANT means offline or the remote is unreachable: say nothing, do
    # nothing. A freshness check must never be the reason a session cannot start.
    if [ -n "$WANT" ] && [ "$WANT" != "$HAVE" ]; then
      echo "session-start: components is behind the pin; updating" >&2
      "$PY" -m pip install --quiet --force-reinstall --no-deps \
        "components @ git+https://github.com/flyinthelyceum/components.git@components-v1" \
        >/dev/null 2>&1 \
        || echo "session-start: warning: could not update components; continuing on the stale copy" >&2
    fi
  fi
fi

LIB_STATE="no venv, lib not installed"
if [ -n "${PY:-}" ]; then
  LIB_STATE="lib $("$PY" -c 'import components; print(components.version())' 2>/dev/null || echo unavailable)${LIB_NOTE:-}"
fi
echo "session-start: components lint hook installed; $LIB_STATE"
