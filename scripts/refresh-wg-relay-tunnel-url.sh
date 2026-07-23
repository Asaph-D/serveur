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

mkdir -p /var/log/provision
chmod 750 /var/log/provision
LOG="/var/log/provision/cloudflared-wg-relay.log"
touch "$LOG"
chmod 640 "$LOG"

# shellcheck source=scripts/lib/detect-internet.sh
source "$ROOT/scripts/lib/detect-internet.sh"

AFTER_BYTES=0
if [[ "${1:-}" == "--restart" ]]; then
	if ! has_internet; then
		echo "Hors ligne — pas de restart cloudflared WG relay (URL conservée)" >&2
		if detect_wg_relay_tunnel_url 0; then
			echo "Repli wg-relay-tunnel.env : ${PROVISION_WG_RELAY_WSS_URL}"
			exit 0
		fi
		echo "WARN: URL WG relay introuvable (hors ligne, pas de cache)" >&2
		exit 1
	fi
	AFTER_BYTES="$(stat -c%s "$LOG" 2>/dev/null || echo 0)"
	systemctl restart cloudflared-wg-relay.service 2>/dev/null \
		|| systemctl start cloudflared-wg-relay.service 2>/dev/null \
		|| true
fi

WAIT_SECS=20
has_internet || WAIT_SECS=3
if ! detect_wg_relay_tunnel_url "$WAIT_SECS" "$AFTER_BYTES"; then
	if [[ "$AFTER_BYTES" -gt 0 ]] && detect_wg_relay_tunnel_url 5 0; then
		echo "WARN: URL WG relay post-restart introuvable — repli journal" >&2
	else
		echo "WARN: URL tunnel WG relay introuvable — journalctl -u cloudflared-wg-relay" >&2
		exit 1
	fi
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
