# DEPLOYMENT.md

How code gets from `main` onto the Pi.

## The problem this solves

The Pi is reachable — `ssh jared@100.77.46.126` over Tailscale, from Jared's
Mac or iPhone on the same mesh. What it is not reachable by is anyone else: the
Cloudflare tunnel publishes HTTP to the dashboard and nothing else, no SSH,
deliberately. So deploying by hand means one person, holding a key, at a
keyboard with a working tailnet.

Before this, every merge needed someone to walk over and type:

```bash
cd ~/grow-lab && git pull && sudo systemctl restart growlab growlab-dashboard
```

That is still the manual fallback, and it still works. The runner means nobody
has to hold a key or be at a keyboard: a deploy becomes a fixed, reviewed set of
steps, gated on tests and recorded in the Actions history.

## How it works

A **GitHub Actions self-hosted runner** runs on the Pi as a systemd service. It
polls GitHub outbound — GitHub never connects inbound, so nothing new is
exposed to the internet.

`.github/workflows/deploy.yml` has two jobs:

| Job | Runs on | Does |
|---|---|---|
| `test` | GitHub-hosted `ubuntu-latest` | Installs `.[dev]`, runs the full suite |
| `deploy` | The Pi (`self-hosted`, `growlab`) | Advances the live clone, restarts, verifies |

`deploy` has `needs: [test]`, so **the Pi only ever runs code whose tests
passed**. That gate is the main reason to run tests off-Pi rather than on it.

Triggers: every push to `main` (so a merged PR deploys itself), and manual
dispatch from the Actions tab for a specific ref.

### It advances the live clone, not a fresh checkout

The deploy job deliberately does **not** `actions/checkout`. The runner's
workspace is a scratch directory; the installation lives at
`/home/jared/grow-lab`, which is what the systemd units run from and where the
gitignored `config.toml` and `.venv` live. Deploying a fresh checkout would
ship a tree with no configuration.

So the job does `git fetch` and `git merge --ff-only` against the existing
clone. Fast-forward only: a diverged local branch fails loudly rather than
being merged or clobbered.

### It refuses to clobber hand edits

If the working tree at `/home/jared/grow-lab` is dirty, the deploy stops and
tells you. `config.toml` and `.venv` are gitignored so they never trip this —
anything that does show up is a hand edit made on the box, and silently
discarding it — in an automated run with nobody watching — is how you lose a fix
made at 2am during a bring-up.

Fix it on the Pi (commit, stash or discard), then re-run the workflow.

### It verifies, and rolls back

After restarting both units it polls `http://127.0.0.1:8000/api/system/status`
for up to a minute. That endpoint opens the database and reports migration
state, so it exercises the thing most likely to break on a schema change.

`429` counts as alive: the API is rate limited, and a rejected request still
proves the server is up. Treating it as failure would roll back a healthy
deploy.

If it never comes up, the job resets the clone to the previous SHA, reinstalls,
restarts, and fails loudly — so a bad deploy leaves the Pi on the last known
good revision rather than dark.

### Dependencies

`pip install -e .` runs only when `pyproject.toml` changed between the old and
new SHA. Most deploys skip it, which matters because resolving wheels on a Pi
is slow.

The `pi` extra (`RPi.GPIO`, `picamera2`, `luma.oled`, `seesaw`) is **not**
installed in CI — those do not build off-Pi. Every driver that needs them
imports lazily inside `connect()` for exactly this reason, which is what lets
the whole suite run on a machine with no GPIO.

## Setting it up

Once, on the Pi:

```bash
cd ~/grow-lab && ./deploy/github-runner/setup.sh
```

It will ask for a registration token from
`https://github.com/flyinthelyceum/grow-lab/settings/actions/runners/new`
(the value after `--token`; it expires in about an hour).

The script also installs a sudoers rule at `/etc/sudoers.d/growlab-runner`,
validated with `visudo -c` before install.

**Re-running is safe.** Each step checks for its own prior work: the sudoers
rule is rewritten in place, an existing download is reused, and an
already-registered runner is left alone.

**If the releases API refuses you** — it rate-limits unauthenticated requests —
pin a version instead:

```bash
RUNNER_VERSION=2.330.0 ./deploy/github-runner/setup.sh
```

Versions are at <https://github.com/actions/runner/releases>.

## Security

A self-hosted runner executes whatever a workflow on this repo says. Its
privileges are the blast radius if the repo is ever compromised, so:

- **The sudoers rule is narrow.** Restart, start, stop and `journalctl` on
  `growlab` and `growlab-dashboard`. Not `ALL`. Do not widen it — a deploy
  needs nothing else.
- **No fork-PR trigger.** The workflow runs only on push to `main` and manual
  dispatch. Never add `pull_request` to a self-hosted workflow on a repo that
  accepts outside contributions: a fork PR would run attacker-authored code on
  the Pi, on your LAN, before any review.
- **`permissions: contents: read`** on the workflow, so the job token cannot
  write to the repo.
- The runner holds a GitHub token scoped to this repo. Rotate it by
  re-registering if the Pi is ever compromised.

## Operating it

**Deploy on merge** — automatic. Merging a PR to `main` deploys it.

**Deploy by hand** — Actions tab → *Deploy to Pi* → *Run workflow*. Optionally
name a ref to deploy something other than `main`.

**Emergency deploy without tests** — the `skip_tests` input on manual dispatch.
For when the box is down and the fix is obvious. Not a habit.

**Roll back** — dispatch with `ref` set to the last good SHA.

**Check what is deployed** — the run summary reports the before and after SHA
and the commit subject.

## Running things on the Pi: `Pi Inspect`

`.github/workflows/pi-inspect.yml` exposes a fixed menu of thirteen operations
on the box. Actions tab → *Pi Inspect* → *Run workflow* → pick one.

- `git-status` — branch and head, the last 25 commits, the diff of modified
  tracked files, and untracked files. One operation, because in practice you
  want all four at once.
- `git-unpushed` — commits made on the box that `origin` has never seen, with
  their patches. The runner is read-only and the Pi holds no key that can push,
  so work committed there is stranded until someone reads it out.
- `services` — `growlab`, `growlab-dashboard` and the runner unit.
- `logs-orchestrator`, `logs-dashboard` — the last 200 journal lines of each.
- `disk` — filesystems, the largest things under `$HOME`, the databases.
- `sensor-scan`, `sensor-status`, `ph-slope`, `meter-status` — the CLI.
- `control-state` — the live `/api/control` and `/api/meters/status` payloads.
- `pytest` — the suite, against the deployed tree.
- `restart-services` — restart both units and report health. The only operation
  that acts on the machine rather than reporting on it.

It exists because it is a bounded, audited path onto the box. The Pi *is*
reachable — `ssh jared@100.77.46.126` over Tailscale — but that wants a key and
a working tailnet on whatever is in your hand. The Actions tab wants a browser,
and it records who asked for what.

**It is a `choice` input, not a command string, and that is the whole design.**
A workflow taking an arbitrary command would be remote code execution on a
machine inside a home network, available to anyone who can dispatch workflows
here. Every command that can run is written out in the file; nothing else can,
whatever is passed in. Adding an operation is a small pull request — reviewable,
and the menu stays the boundary.

The rest of the posture is the same as the deploy job: `workflow_dispatch`
only so a merge never triggers it, running as `jared` rather than root with
sudo still limited to the two units by `/etc/sudoers.d/growlab-runner`,
`contents: read` so the token cannot write, and every dispatch recorded in the
Actions history with the operation and who asked for it.

## Concurrency is scoped to the deploy job, deliberately

Only one deploy runs at a time — two racing on one Pi would interleave a git
reset with a service restart. That guard lives on the **`deploy` job**, not on
the workflow.

At workflow level it gates the entire run. A deploy stuck in the queue — the
runner offline, the Pi unplugged — then blocks every subsequent run outright,
tests included. That is not theoretical: when the workflow first merged, its
deploy job sat waiting for a runner that had not been registered yet, and the
next push produced a run that stayed `pending` with zero jobs created. CI had
silently stopped, and nothing said so.

Scoped to the job, tests always run and only deploys serialize. Do not move it
back up.

## If the runner goes offline

It is a systemd service on the Pi:

```bash
cd ~/actions-runner
sudo ./svc.sh status
sudo ./svc.sh start
```

Deploys queue while it is down and run when it returns; tests keep running in
the meantime (see the concurrency note above). If the Pi has been rebuilt,
re-run `setup.sh` with a fresh token.

A queued self-hosted job waits about 24 hours before GitHub abandons it, so a
long outage leaves stale deploys in the queue. They are harmless — each is a
fast-forward that no-ops on an already-current clone — but cancel them from the
Actions tab if you would rather not have them fire all at once.
