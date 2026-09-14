#!/bin/bash
# SessionStart hook for Claude Code (local and on the web).
# 1. Installs the components pre-commit lint (.git/hooks is not versioned).
# 2. Makes the `components` package importable in .venv (created if absent):
#    editable from a local clone of flyinthelyceum/components when there is one,
#    otherwise the pinned git dependency.
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
LIB_STATE="no venv, lib not installed"
if [ -n "$PY" ]; then
  LIB_STATE="lib $("$PY" -c 'import components; print(components.version())' 2>/dev/null || echo unavailable)"
fi
echo "session-start: components lint hook installed; $LIB_STATE"
