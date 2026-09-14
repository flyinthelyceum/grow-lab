# CLAUDE.md: grow-lab

## Component measurements: one writer

Physical component dimensions live only in `flyinthelyceum/components` (the `components` package,
https://github.com/flyinthelyceum/components). Never type a CALIPER or DATASHEET value into this
repo; import it (`from components import <part>`). To record a measurement, from a clone of that repo
with the package installed in this repo's `.venv`:
`python -m components measure <part> <CONST> <value> --by XX` (`--datasheet URL` for a drawing).
The pre-commit lint refuses any measured constant here; `scripts/install-hooks.sh` installs it and the
SessionStart hook runs that on every session. Mark a rare non-measurement `# lint: not-a-measurement`.
