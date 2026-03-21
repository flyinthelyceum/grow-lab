#!/usr/bin/env bash
# GROWLAB Cloudflare Tunnel setup script
# Run on the Pi as user jared
set -euo pipefail

TUNNEL_NAME="growlab"
HOSTNAME="grow.aaand.space"

echo "=== GROWLAB Cloudflare Tunnel Setup ==="
echo ""

# --- Install cloudflared ---
if command -v cloudflared &>/dev/null; then
    echo "[ok] cloudflared already installed: $(cloudflared --version)"
else
    echo "[*] Installing cloudflared..."
    ARCH=$(dpkg --print-architecture)
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb" -o /tmp/cloudflared.deb
    sudo dpkg -i /tmp/cloudflared.deb
    rm /tmp/cloudflared.deb
    echo "[ok] Installed: $(cloudflared --version)"
fi

echo ""

# --- Authenticate ---
if [ -f "$HOME/.cloudflared/cert.pem" ]; then
    echo "[ok] Already authenticated with Cloudflare"
else
    echo "[*] Opening browser to authenticate with Cloudflare..."
    echo "    (If headless, copy the URL it prints and open on your Mac)"
    cloudflared tunnel login
fi

echo ""

# --- Create tunnel ---
EXISTING=$(cloudflared tunnel list --output json 2>/dev/null | python3 -c "
import json, sys
tunnels = json.load(sys.stdin)
for t in tunnels:
    if t['name'] == '$TUNNEL_NAME':
        print(t['id'])
        break
" 2>/dev/null || true)

if [ -n "$EXISTING" ]; then
    TUNNEL_UUID="$EXISTING"
    echo "[ok] Tunnel '$TUNNEL_NAME' already exists: $TUNNEL_UUID"
else
    echo "[*] Creating tunnel '$TUNNEL_NAME'..."
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_UUID=$(cloudflared tunnel list --output json | python3 -c "
import json, sys
tunnels = json.load(sys.stdin)
for t in tunnels:
    if t['name'] == '$TUNNEL_NAME':
        print(t['id'])
        break
")
    echo "[ok] Created tunnel: $TUNNEL_UUID"
fi

echo ""

# --- Write config ---
CONFIG_PATH="$HOME/.cloudflared/config.yml"
echo "[*] Writing config to $CONFIG_PATH"

cat > "$CONFIG_PATH" <<YAML
tunnel: ${TUNNEL_UUID}
credentials-file: /home/jared/.cloudflared/${TUNNEL_UUID}.json

ingress:
  - hostname: ${HOSTNAME}
    service: http://localhost:8000
  - service: http_status:404
YAML

echo "[ok] Config written"
echo ""

# --- Route DNS ---
echo "[*] Routing DNS: $HOSTNAME -> tunnel"
cloudflared tunnel route dns "$TUNNEL_NAME" "$HOSTNAME" 2>/dev/null || echo "    (DNS route may already exist — check Cloudflare dashboard)"
echo ""

# --- Install systemd service ---
echo "[*] Installing systemd service..."
sudo cp "$(dirname "$0")/../systemd/cloudflared.service" /etc/systemd/system/cloudflared.service
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
echo ""

# --- Verify ---
echo "[*] Checking tunnel status..."
sleep 2
if systemctl is-active --quiet cloudflared; then
    echo "[ok] cloudflared is running"
    echo ""
    echo "=== Setup Complete ==="
    echo "Dashboard will be live at: https://$HOSTNAME"
    echo ""
    echo "Useful commands:"
    echo "  sudo systemctl status cloudflared    # check status"
    echo "  sudo journalctl -u cloudflared -f    # stream logs"
    echo "  cloudflared tunnel info $TUNNEL_NAME # tunnel details"
else
    echo "[!!] cloudflared failed to start. Check logs:"
    echo "  sudo journalctl -u cloudflared --no-pager -n 20"
    exit 1
fi
