#!/usr/bin/env bash
# URL trycloudflare du tunnel WG relay (cloudflared → wstunnel :8081).
# Usage : sudo bash scripts/refresh-wg-relay-tunnel-url.sh [--restart]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/detect-tunnel-url.sh
source "$ROOT/scripts/lib/detect-tunnel-url.sh"

if [[ "$(id -u)" -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

if [[ "${1:-}" == "--restart" ]]; then
	systemctl restart cloudflared-wg-relay.service 2>/dev/null || true
fi

mkdir -p /var/log/provision
chmod 750 /var/log/provision

if ! detect_wg_relay_tunnel_url 45; then
	echo "WARN: URL tunnel WG relay introuvable — journalctl -u cloudflared-wg-relay" >&2
	exit 1
fi

TUNNEL_ENV="/etc/provision/wg-relay-tunnel.env"
cat >"$TUNNEL_ENV" <<EOF
# Généré par refresh-wg-relay-tunnel-url.sh — tunnel dédié wstunnel (≠ API provision)
PROVISION_WG_RELAY_TUNNEL_URL=${PROVISION_WG_RELAY_TUNNEL_URL}
PROVISION_WG_RELAY_WSS_URL=${PROVISION_WG_RELAY_WSS_URL}
EOF
chmod 640 "$TUNNEL_ENV"
chown root:www-data "$TUNNEL_ENV" 2>/dev/null || chmod 600 "$TUNNEL_ENV"

echo "WG relay WSS : ${PROVISION_WG_RELAY_WSS_URL}"
