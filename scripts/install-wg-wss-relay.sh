#!/usr/bin/env bash
# Relais WireGuard UDP → WebSocket (sortant via Cloudflare, Starlink CGNAT OK).
# Usage : sudo bash scripts/install-wg-wss-relay.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS="/etc/provision/wg-relay.env"
WG_PORT="${PROVISION_VPN_PORT:-51820}"
RELAY_PORT="8081"

[[ $(id -u) -eq 0 ]] || { echo "Root requis : sudo bash $0" >&2; exit 1; }

install_wstunnel() {
	if command -v wstunnel >/dev/null 2>&1; then
		return
	fi
	echo "==> Installation wstunnel"
	local arch ver url
	arch="$(uname -m)"
	case "$arch" in
		x86_64) arch="amd64" ;;
		aarch64) arch="arm64" ;;
		*) echo "Arch non supportée: $arch" >&2; exit 1 ;;
	esac
	ver="$(curl -fsSL https://api.github.com/repos/erebe/wstunnel/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')"
	url="https://github.com/erebe/wstunnel/releases/download/${ver}/wstunnel_${ver#v}_linux_${arch}.tar.gz"
	curl -fsSL "$url" | tar -xz -C /tmp wstunnel
	install -m 755 /tmp/wstunnel /usr/local/bin/wstunnel
}

mkdir -p /etc/provision
if [[ ! -f "$SECRETS" ]]; then
	PREFIX="$(openssl rand -hex 12)"
	cat >"$SECRETS" <<EOF
PROVISION_WG_RELAY_PATH_PREFIX="${PREFIX}"
PROVISION_WG_RELAY_PORT="${RELAY_PORT}"
EOF
	chmod 640 "$SECRETS"
	chown root:www-data "$SECRETS"
fi
# shellcheck disable=SC1090
source "$SECRETS"
PREFIX="${PROVISION_WG_RELAY_PATH_PREFIX:?}"

install_wstunnel

install -m 644 "$ROOT/systemd/cloudflared-wg-relay-quick.service" \
	/etc/systemd/system/cloudflared-wg-relay.service
systemctl daemon-reload
systemctl enable --now cloudflared-wg-relay.service
sleep 8
bash "$ROOT/scripts/refresh-wg-relay-tunnel-url.sh" || true

install -m 644 "$ROOT/systemd/wg-wss-relay.service" /etc/systemd/system/wg-wss-relay.service
sed -i "s|@WG_PORT@|${WG_PORT}|g; s|@RELAY_PORT@|${RELAY_PORT}|g; s|@PATH_PREFIX@|${PREFIX}|g" \
	/etc/systemd/system/wg-wss-relay.service

install -m 644 "$ROOT/apache/wg-wss-relay.conf" /etc/apache2/conf-available/wg-wss-relay.conf
sed -i "s|@RELAY_PORT@|${RELAY_PORT}|g" /etc/apache2/conf-available/wg-wss-relay.conf

a2enmod proxy proxy_http proxy_wstunnel 2>/dev/null || true
a2enconf wg-wss-relay 2>/dev/null || true

systemctl daemon-reload
systemctl enable --now wg-wss-relay.service
systemctl reload apache2 2>/dev/null || systemctl restart apache2

echo ""
echo "OK — relais WG/WebSocket actif"
echo "  Préfixe path : ${PREFIX}"
echo "  wstunnel     : 127.0.0.1:${RELAY_PORT} → UDP 127.0.0.1:${WG_PORT}"
echo "  URL publique WG : voir /etc/provision/wg-relay-tunnel.env (tunnel Cloudflare dédié)"
echo "  (≠ api_remote — pas de /wg-relay sur l’URL API provision)"
