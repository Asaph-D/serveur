#!/usr/bin/env bash
# Reverse proxy provision via Cloudflare Tunnel (pas de box / port-forward).
# Usage : sudo bash scripts/install-provision-tunnel.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

if ! command -v cloudflared >/dev/null 2>&1; then
	echo "==> Installation cloudflared"
	curl -fsSL -o /tmp/cloudflared \
		"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
	install -m 755 /tmp/cloudflared /usr/local/bin/cloudflared
fi

mkdir -p /var/log/provision
chmod 750 /var/log/provision
chown www-data:www-data /var/log/provision 2>/dev/null || true

echo "==> Service systemd cloudflared-provision"
cp "$ROOT/systemd/cloudflared-provision.service" /etc/systemd/system/cloudflared-provision.service
systemctl daemon-reload
systemctl enable cloudflared-provision.service
systemctl restart cloudflared-provision.service

echo "==> Attente URL publique trycloudflare.com"
TUNNEL_URL=""
for _ in $(seq 1 30); do
	TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /var/log/provision/cloudflared.log 2>/dev/null | tail -1 || true)
	if [[ -n "$TUNNEL_URL" ]]; then
		break
	fi
	sleep 1
done

if [[ -z "$TUNNEL_URL" ]]; then
	echo "URL tunnel introuvable — voir : journalctl -u cloudflared-provision -f" >&2
	exit 1
fi

API_BASE="${TUNNEL_URL}/provision"
TUNNEL_ENV="/etc/provision/tunnel.env"
cat >"$TUNNEL_ENV" <<EOF
# Généré par install-provision-tunnel.sh — URL Cloudflare Tunnel (reverse proxy)
PROVISION_TUNNEL_URL=${TUNNEL_URL}
PROVISION_PUBLIC_BASE_URL=${API_BASE}
EOF
chmod 640 "$TUNNEL_ENV"
chown root:www-data "$TUNNEL_ENV" 2>/dev/null || chmod 600 "$TUNNEL_ENV"

# Mettre à jour provision.env si les clés existent
PROV_ENV="/etc/provision/provision.env"
if [[ -f "$PROV_ENV" ]]; then
	if grep -q '^PROVISION_PUBLIC_BASE_URL=' "$PROV_ENV"; then
		sed -i "s|^PROVISION_PUBLIC_BASE_URL=.*|PROVISION_PUBLIC_BASE_URL=\"${API_BASE}\"|" "$PROV_ENV"
	else
		echo "PROVISION_PUBLIC_BASE_URL=\"${API_BASE}\"" >>"$PROV_ENV"
	fi
	# Host public = hostname tunnel (sans https)
	TUNNEL_HOST="${TUNNEL_URL#https://}"
	if grep -q '^PROVISION_PUBLIC_HOST=' "$PROV_ENV"; then
		sed -i "s|^PROVISION_PUBLIC_HOST=.*|PROVISION_PUBLIC_HOST=\"${TUNNEL_HOST}\"|" "$PROV_ENV"
	fi
fi

echo ""
echo "Tunnel actif : ${TUNNEL_URL}"
echo "API provision : ${API_BASE}"
echo ""
echo "Test :"
echo "  curl -sk '${API_BASE}/'"
echo ""
echo "Mettre à jour bootstrap.json (GitHub Pages) :"
echo "  api_remote : \"${API_BASE}\""
echo ""
echo "Note : URL trycloudflare change si le service redémarre."
echo "Production stable : compte Cloudflare + tunnel nommé (voir network/cloudflared/README.md)."
