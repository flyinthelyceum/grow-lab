#!/usr/bin/env bash
#
# Install the GitHub Actions self-hosted runner on the Pi.
#
# Why this exists: nobody can shell into the Pi from a Claude Code session --
# no route to the LAN, and the Cloudflare tunnel publishes only HTTP to the
# dashboard. This runner is the path by which merged work reaches the hardware
# without someone walking over to the box.
#
# Run it on the Pi:
#
#   cd ~/grow-lab && ./deploy/github-runner/setup.sh
#
# You will need a runner registration token, which expires after about an hour:
#   https://github.com/flyinthelyceum/grow-lab/settings/actions/runners/new
# Copy the value after `--token` from the command GitHub shows you.
#
# The runner version is resolved from the GitHub releases API. That API
# rate-limits unauthenticated requests, so if it refuses you can pin one:
#
#   RUNNER_VERSION=2.330.0 ./deploy/github-runner/setup.sh
#
# Re-running this script is safe. Every step checks for its own prior work:
# the sudoers rule is rewritten in place, an existing download is reused, and
# an already-registered runner is left alone.

set -euo pipefail

REPO_URL="https://github.com/flyinthelyceum/grow-lab"
RUNNER_DIR="${HOME}/actions-runner"
RUNNER_USER="$(whoami)"
GROWLAB_DIR="${HOME}/grow-lab"
LABELS="growlab,pi"
UNITS="growlab growlab-dashboard"

echo "==> GROWLAB self-hosted runner setup"
echo "    repo:    ${REPO_URL}"
echo "    runner:  ${RUNNER_DIR}"
echo "    user:    ${RUNNER_USER}"
echo "    labels:  ${LABELS}"
echo

# --- 0. Sanity ---------------------------------------------------------------

if [ ! -d "${GROWLAB_DIR}/.git" ]; then
    echo "ERROR: no git clone at ${GROWLAB_DIR}." >&2
    echo "The deploy workflow advances that clone in place -- it is what the" >&2
    echo "systemd units run from, and where config.toml and .venv live." >&2
    exit 1
fi

if [ ! -d "${GROWLAB_DIR}/.venv" ]; then
    echo "ERROR: no virtualenv at ${GROWLAB_DIR}/.venv." >&2
    exit 1
fi

SYSTEMCTL="$(command -v systemctl)"
JOURNALCTL="$(command -v journalctl)"

# --- 1. Sudoers: exactly the verbs needed, on exactly these two units ---------
#
# NOT blanket NOPASSWD. A self-hosted runner executes whatever a workflow on
# this repo says, so its sudo rights are the blast radius if the repo is ever
# compromised. Restarting two services is all a deploy needs, so that is all it
# gets.

SUDOERS_FILE="/etc/sudoers.d/growlab-runner"
echo "==> Installing narrow sudoers rule at ${SUDOERS_FILE}"

TMP_SUDOERS="$(mktemp)"
{
    echo "# Installed by deploy/github-runner/setup.sh for the GROWLAB deploy workflow."
    echo "# Deliberately narrow: the runner may restart and inspect these two units"
    echo "# and nothing else. Do not widen this to ALL."
    for unit in ${UNITS}; do
        echo "${RUNNER_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL} restart ${unit}"
        echo "${RUNNER_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL} start ${unit}"
        echo "${RUNNER_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL} stop ${unit}"
        echo "${RUNNER_USER} ALL=(root) NOPASSWD: ${JOURNALCTL} -u ${unit} *"
    done
    # The restart step passes both units in a single call.
    echo "${RUNNER_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL} restart ${UNITS}"
} > "${TMP_SUDOERS}"

# visudo -c refuses to install a file that would break sudo entirely.
if sudo visudo -c -f "${TMP_SUDOERS}"; then
    sudo install -m 0440 -o root -g root "${TMP_SUDOERS}" "${SUDOERS_FILE}"
    echo "    installed and validated"
else
    echo "ERROR: generated sudoers file did not validate; nothing was installed." >&2
    rm -f "${TMP_SUDOERS}"
    exit 1
fi
rm -f "${TMP_SUDOERS}"

# --- 2. Download the runner --------------------------------------------------

case "$(uname -m)" in
    aarch64|arm64) RUNNER_ARCH="arm64" ;;
    armv7l)        RUNNER_ARCH="arm" ;;
    x86_64)        RUNNER_ARCH="x64" ;;
    *) echo "ERROR: unsupported architecture $(uname -m)" >&2; exit 1 ;;
esac

if [ ! -f "${RUNNER_DIR}/config.sh" ]; then
    echo "==> Downloading runner for linux-${RUNNER_ARCH}"
    mkdir -p "${RUNNER_DIR}"
    cd "${RUNNER_DIR}"

    # Resolve the latest release.
    #
    # Deliberately NOT `curl ... | grep -m1`. grep -m1 exits at its first
    # match, closing the pipe while curl still has body in flight; curl then
    # dies with error 23 ("Failure writing output to destination, passed N
    # returned M") and `set -o pipefail` aborts the whole script. That is what
    # happened on the first real run of this script. Same family of bug as
    # piping into `head -n1`.
    #
    # Capture the body first, then parse it. No pipe from curl, nothing that
    # can close early.
    if [ -z "${RUNNER_VERSION:-}" ]; then
        echo "    resolving latest release..."
        RELEASE_JSON=""
        if ! RELEASE_JSON="$(curl -fsSL --retry 3 --retry-delay 2 --max-time 60 \
                https://api.github.com/repos/actions/runner/releases/latest)"; then
            echo "ERROR: could not reach the GitHub releases API." >&2
            echo "The API rate-limits unauthenticated requests. Either retry" >&2
            echo "later, or pin a version explicitly:" >&2
            echo >&2
            echo "  RUNNER_VERSION=2.330.0 $0" >&2
            echo >&2
            echo "Versions are listed at https://github.com/actions/runner/releases" >&2
            exit 1
        fi

        # Parse with python3 -- this is a Python project, so it is present,
        # and a real JSON parser cannot be fooled by a "tag_name" quoted
        # inside the release notes the way a greedy regex can be. sed is the
        # fallback if python3 is somehow missing.
        if command -v python3 >/dev/null 2>&1; then
            RUNNER_VERSION="$(printf '%s' "${RELEASE_JSON}" | python3 -c \
'import json,sys
try:
    print(json.load(sys.stdin)["tag_name"].lstrip("v"))
except Exception:
    pass' 2>/dev/null || true)"
        else
            RUNNER_VERSION="$(printf '%s\n' "${RELEASE_JSON}" \
                | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"v\([^"]*\)".*/\1/p' \
                | sed -n 1p)"
        fi
    fi

    if [ -z "${RUNNER_VERSION}" ]; then
        echo "ERROR: could not determine the runner version from the API response." >&2
        echo "Pin one explicitly:  RUNNER_VERSION=2.330.0 $0" >&2
        exit 1
    fi
    echo "    version ${RUNNER_VERSION}"

    TARBALL="actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"
    URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${TARBALL}"

    echo "    downloading ${TARBALL}"
    if ! curl -fL --retry 3 --retry-delay 2 --progress-bar -o "${TARBALL}" "${URL}"; then
        echo "ERROR: download failed from ${URL}" >&2
        echo "If the disk is full this is where it shows: check \`df -h ~\`." >&2
        rm -f "${TARBALL}"
        exit 1
    fi

    # A truncated download or an HTML error page would still be a file, and
    # tar's failure message for one is not obvious. Check before extracting.
    TARBALL_BYTES="$(stat -c %s "${TARBALL}" 2>/dev/null || echo 0)"
    if [ "${TARBALL_BYTES}" -lt 1000000 ]; then
        echo "ERROR: ${TARBALL} is only ${TARBALL_BYTES} bytes — not a runner tarball." >&2
        echo "Likely a truncated transfer or an error page. First bytes:" >&2
        head -c 200 "${TARBALL}" >&2 || true
        echo >&2
        rm -f "${TARBALL}"
        exit 1
    fi

    if ! tar xzf "${TARBALL}"; then
        echo "ERROR: could not extract ${TARBALL}." >&2
        exit 1
    fi
    rm -f "${TARBALL}"
else
    echo "==> Runner already downloaded at ${RUNNER_DIR}"
fi

cd "${RUNNER_DIR}"

# --- 3. Register -------------------------------------------------------------

if [ ! -f ".runner" ]; then
    echo
    echo "==> Registration token needed."
    echo "    Open: ${REPO_URL}/settings/actions/runners/new"
    echo "    Copy the value after --token from the command shown there."
    echo "    (It expires in about an hour.)"
    echo
    read -r -p "Token: " RUNNER_TOKEN

    ./config.sh \
        --url "${REPO_URL}" \
        --token "${RUNNER_TOKEN}" \
        --name "growlab-pi" \
        --labels "${LABELS}" \
        --work "_work" \
        --unattended \
        --replace
else
    echo "==> Runner already registered"
fi

# --- 4. Run it as a service --------------------------------------------------

echo "==> Installing the runner as a systemd service"
sudo ./svc.sh install "${RUNNER_USER}"
sudo ./svc.sh start

echo
echo "==> Done."
sudo ./svc.sh status || true
echo
echo "Verify at ${REPO_URL}/settings/actions/runners -- 'growlab-pi' should be Idle."
echo
echo "Deploys now run on merge to main, and can be fired by hand from"
echo "${REPO_URL}/actions/workflows/deploy.yml"
