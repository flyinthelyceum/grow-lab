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

    RUNNER_VERSION="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest \
        | grep -m1 '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/')"
    if [ -z "${RUNNER_VERSION}" ]; then
        echo "ERROR: could not determine the latest runner version." >&2
        exit 1
    fi
    echo "    version ${RUNNER_VERSION}"

    TARBALL="actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"
    curl -fsSL -o "${TARBALL}" \
        "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${TARBALL}"
    tar xzf "${TARBALL}"
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
