#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_HOST="jared@100.77.46.126"
TARGET_HOST="${TARGET_HOST:-$DEFAULT_HOST}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/jared/grow-lab}"
RESTART_REMOTE=1

usage() {
    cat <<EOF
Usage: $(basename "$0") [--host user@host] [--remote-root /path] [--no-restart]

Push the dashboard files needed for the current art/dashboard deploy to the Pi.

Options:
  --host         SSH target (default: ${DEFAULT_HOST})
  --remote-root  Remote repo root (default: ${REMOTE_ROOT})
  --no-restart   Only copy files; do not trigger remote recovery
  -h, --help     Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)
            TARGET_HOST="$2"
            shift 2
            ;;
        --remote-root)
            REMOTE_ROOT="$2"
            shift 2
            ;;
        --no-restart)
            RESTART_REMOTE=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

FILES=(
    "deploy/recover-dashboard.sh"
    "pi/dashboard/app.py"
    "pi/dashboard/templates/art.html"
    "pi/dashboard/templates/observatory.html"
    "pi/dashboard/templates/dream.html"
    "pi/dashboard/static/art.js"
    "pi/dashboard/static/art/art-core.js"
    "pi/dashboard/static/art/ph-ring.js"
    "pi/dashboard/static/art/ec-ring.js"
)

echo "[*] Checking SSH connectivity to ${TARGET_HOST}"
ssh -o BatchMode=yes -o ConnectTimeout=10 "${TARGET_HOST}" "echo connected >/dev/null"

echo "[*] Ensuring remote directories exist"
ssh "${TARGET_HOST}" "mkdir -p \
    '${REMOTE_ROOT}/deploy' \
    '${REMOTE_ROOT}/pi/dashboard/templates' \
    '${REMOTE_ROOT}/pi/dashboard/static/art'"

for rel_path in "${FILES[@]}"; do
    local_path="${ROOT_DIR}/${rel_path}"
    remote_path="${REMOTE_ROOT}/${rel_path}"
    echo "[*] Copying ${rel_path}"
    scp "${local_path}" "${TARGET_HOST}:${remote_path}"
done

ssh "${TARGET_HOST}" "chmod +x \
    '${REMOTE_ROOT}/deploy/recover-dashboard.sh'"

if [[ "${RESTART_REMOTE}" -eq 1 ]]; then
    echo "[*] Running remote recovery"
    ssh "${TARGET_HOST}" "'${REMOTE_ROOT}/deploy/recover-dashboard.sh' --quick"
else
    echo "[ok] Files copied without restart"
fi
