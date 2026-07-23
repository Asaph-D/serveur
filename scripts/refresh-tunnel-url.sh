#!/usr/bin/env bash
# Mode dev uniquement (trycloudflare éphémère). Production : install-provision-tunnel.sh sans --quick.
# Usage : sudo bash scripts/refresh-tunnel-url.sh [--restart]
#
# Important : après --restart, on ne lit QUE le journal écrit après le redémarrage
# (sinon on republie une ancienne URL trycloudflare → HTTP 530 / hôte mort côté app).
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
LOG="/var/log/provision/cloudflared.log"
touch "$LOG"
chmod 640 "$LOG"

# shellcheck source=scripts/lib/detect-internet.sh
source "$ROOT/scripts/lib/detect-internet.sh"

AFTER_BYTES=0
if [[ "${1:-}" == "--restart" ]]; then
	if ! has_internet; then
		echo "Hors ligne — pas de restart cloudflared (URL conservée dans tunnel.env)" >&2
		if detect_tunnel_url_quick 0; then
			echo "Repli tunnel.env : ${PROVISION_TUNNEL_URL}"
			exit 0
		fi
		echo "WARN: URL tunnel introuvable (hors ligne, pas de cache)" >&2
		exit 1
	fi
	AFTER_BYTES="$(stat -c%s "$LOG" 2>/dev/null || echo 0)"
	systemctl restart cloudflared-provision.service 2>/dev/null \
		|| systemctl start cloudflared-provision.service 2>/dev/null \
		|| true
fi

# Attendre une URL apparue UNIQUEMENT après le restart (20 s max si online ; cloudflared ~5–15 s)
WAIT_SECS=20
has_internet || WAIT_SECS=3
if ! detect_tunnel_url_quick "$WAIT_SECS" "$AFTER_BYTES"; then
	# Repli : dernière URL du journal complet (démarrage sans --restart)
	if [[ "$AFTER_BYTES" -gt 0 ]] && detect_tunnel_url_quick 5 0; then
		echo "WARN: URL post-restart introuvable — repli sur dernière URL du journal" >&2
	else
		echo "WARN: URL tunnel introuvable (hors ligne ?) — journalctl -u cloudflared-provision" >&2
		exit 1
	fi
fi

# Laisser Cloudflare propager le routage edge → connecteur (court ; skip si hors ligne)
if has_internet; then
	wait_trycloudflare_ready "${PROVISION_PUBLIC_BASE_URL}" 15 || true
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
