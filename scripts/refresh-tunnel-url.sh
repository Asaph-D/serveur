#!/usr/bin/env bash
# Mode dev uniquement (trycloudflare éphémère). Production : install-provision-tunnel.sh sans --quick.
# Usage : sudo bash scripts/refresh-tunnel-url.sh [--restart]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/detect-tunnel-url.sh
source "$ROOT/scripts/lib/detect-tunnel-url.sh"

if [[ "$(id -u)" -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

if [[ "${1:-}" == "--restart" ]]; then
	systemctl restart cloudflared-provision.service 2>/dev/null || true
	sleep 3
fi

mkdir -p /var/log/provision
chmod 750 /var/log/provision

if ! detect_tunnel_url 45; then
	echo "WARN: URL tunnel introuvable (hors ligne ?) — journalctl -u cloudflared-provision" >&2
	exit 1
fi

TUNNEL_ENV="/etc/provision/tunnel.env"
cat >"$TUNNEL_ENV" <<EOF
# Généré par refresh-tunnel-url.sh — URL Cloudflare Tunnel (éphémère trycloudflare)
PROVISION_TUNNEL_URL=${PROVISION_TUNNEL_URL}
PROVISION_PUBLIC_BASE_URL=${PROVISION_PUBLIC_BASE_URL}
EOF
chmod 640 "$TUNNEL_ENV"
chown root:www-data "$TUNNEL_ENV" 2>/dev/null || chmod 600 "$TUNNEL_ENV"

echo "Tunnel : ${PROVISION_TUNNEL_URL}"
echo "API    : ${PROVISION_PUBLIC_BASE_URL}"
