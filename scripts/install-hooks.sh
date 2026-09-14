#!/bin/sh
# Install the components pre-commit lint into this clone's hooks dir.
# .git/hooks is not versioned, so a consumer's SessionStart hook runs this and
# anyone can run it by hand. Idempotent. Refuses to overwrite a pre-commit it
# did not write (looks for its own marker line).
# The lint refuses any caliper/datasheet-tagged constant in the INDEX (what the
# commit would contain); measurements are written with `components measure`.
set -e
root="$(git rev-parse --show-toplevel)"
hooks="$(git -C "$root" rev-parse --git-path hooks)"
case "$hooks" in /*) ;; *) hooks="$root/$hooks" ;; esac
marker="# Installed by scripts/install-hooks.sh (components-lib)."
if [ -f "$hooks/pre-commit" ] && ! grep -qF "$marker" "$hooks/pre-commit"; then
  echo "install-hooks: $hooks/pre-commit exists and is not ours; leaving it alone." >&2
  echo "  Merge this into it by hand: python -m components lint --staged \"\$(git rev-parse --show-toplevel)\"" >&2
  exit 1
fi
mkdir -p "$hooks"
cat > "$hooks/pre-commit" <<'HOOK'
#!/bin/sh
# Installed by scripts/install-hooks.sh (components-lib). Do not edit here.
root="$(git rev-parse --show-toplevel)"
if [ -x "$root/.venv/bin/python" ] && "$root/.venv/bin/python" -c "import components" >/dev/null 2>&1; then
  exec "$root/.venv/bin/python" -m components lint --staged "$root"
fi
if python3 -c "import components" >/dev/null 2>&1; then
  exec python3 -m components lint --staged "$root"
fi
lint="${COMPONENTS_REPO:-$HOME/projects/components}/components/lint_consumer.py"
if [ -f "$root/components/lint_consumer.py" ]; then lint="$root/components/lint_consumer.py"; fi
if [ -f "$lint" ]; then
  exec python3 "$lint" --staged "$root"
fi
echo "pre-commit: the components lint is not installed; refusing to commit unchecked." >&2
echo "  pip install 'components @ git+https://github.com/flyinthelyceum/components.git@components-v1'" >&2
echo "  or set COMPONENTS_REPO to a clone of flyinthelyceum/components." >&2
exit 1
HOOK
chmod +x "$hooks/pre-commit"
echo "install-hooks: components pre-commit lint installed at $hooks/pre-commit"
