#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/jared/grow-lab}"
QUICK_MODE=0

usage() {
    cat <<EOF
Usage: $(basename "$0") [--quick]

Recover the dashboard stack on the Pi:
  1. verify repo + venv
  2. reinstall editable package (unless --quick)
  3. restart growlab-dashboard
  4. restart cloudflared
  5. print health checks
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick)
            QUICK_MODE=1
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

if [[ ! -d "${REPO_ROOT}" ]]; then
    echo "[!!] Repo root not found: ${REPO_ROOT}" >&2
    exit 1
fi

if [[ ! -f "${REPO_ROOT}/.venv/bin/activate" ]]; then
    echo "[!!] Virtualenv missing at ${REPO_ROOT}/.venv" >&2
    exit 1
fi

cd "${REPO_ROOT}"
source "${REPO_ROOT}/.venv/bin/activate"

echo "[*] Repo: ${REPO_ROOT}"
echo "[*] Host: $(hostname)"
echo "[*] Time: $(date '+%Y-%m-%d %H:%M:%S %Z')"

if [[ "${QUICK_MODE}" -eq 0 ]]; then
    echo "[*] Refreshing editable install"
    pip install -e .
else
    echo "[*] Quick mode: skipping pip install -e ."
fi

echo "[*] Restarting dashboard"
sudo systemctl restart growlab-dashboard

echo "[*] Restarting Cloudflare tunnel"
sudo systemctl restart cloudflared

echo "[*] Waiting for services to settle"
sleep 3

echo ""
echo "=== Service Health ==="
systemctl is-active growlab-dashboard
systemctl is-active cloudflared

echo ""
echo "=== Dashboard Status ==="
sudo systemctl --no-pager --full status growlab-dashboard | sed -n '1,18p'

echo ""
echo "=== Tunnel Status ==="
sudo systemctl --no-pager --full status cloudflared | sed -n '1,18p'

echo ""
echo "=== Local Origin Checks ==="
curl -fsS http://127.0.0.1:8000/art | rg -n "art-live-ph|ph-ring|ec-ring|ENVIRONMENTAL \+ RESERVOIR|\?v=" || true
curl -fsSI http://127.0.0.1:8000/static/art/ph-ring.js | sed -n '1,8p'

echo ""
echo "=== Tailnet Snapshot ==="
tailscale status | sed -n '1,10p' || true

