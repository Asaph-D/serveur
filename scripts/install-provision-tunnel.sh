#!/usr/bin/env bash
# Tunnel Cloudflare pour l'API provision (reverse proxy sortant, sans port-forward).
#
# Mode nommé (défaut) : domaine fixe via global-config.env
#   sudo bash scripts/install-provision-tunnel.sh
#
# Mode dev éphémère (trycloudflare) :
#   sudo bash scripts/install-provision-tunnel.sh --quick
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GCFG="$ROOT/network/global-config.env"
QUICK=0
[[ "${1:-}" == "--quick" ]] && QUICK=1

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

install_quick_tunnel() {
	echo "==> Mode quick (trycloudflare — URL change à chaque reboot)"
	cp "$ROOT/systemd/cloudflared-provision-quick.service" \
		/etc/systemd/system/cloudflared-provision.service
	systemctl daemon-reload
	systemctl enable cloudflared-provision.service
	systemctl restart cloudflared-provision.service
	bash "$ROOT/scripts/refresh-tunnel-url.sh"
	bash "$ROOT/scripts/sync-global-config.sh" --deploy
	# shellcheck source=scripts/lib/detect-tunnel-url.sh
	source "$ROOT/scripts/lib/detect-tunnel-url.sh"
	resolve_provision_public_urls 0
	echo ""
	echo "API provision (éphémère) : ${PROVISION_PUBLIC_BASE_URL}"
	echo "Préférer le mode nommé : sudo bash $0 (sans --quick)"
}

cloudflared_cert_path() {
	if [[ -f /root/.cloudflared/cert.pem ]]; then
		echo /root/.cloudflared/cert.pem
	elif [[ -n "${SUDO_USER:-}" && -f "/home/${SUDO_USER}/.cloudflared/cert.pem" ]]; then
		echo "/home/${SUDO_USER}/.cloudflared/cert.pem"
	elif [[ -f "${HOME}/.cloudflared/cert.pem" ]]; then
		echo "${HOME}/.cloudflared/cert.pem"
	fi
}

cloudflared_home() {
	local cert
	cert="$(cloudflared_cert_path || true)"
	[[ -n "$cert" ]] && dirname "$cert"
	echo /root/.cloudflared
}

tunnel_id_by_name() {
	local name="$1"
	cloudflared tunnel list -o json 2>/dev/null | python3 -c "
import json, sys
name = sys.argv[1]
for t in json.load(sys.stdin):
    if t.get('name') == name:
        print(t.get('id', ''))
        break
" "$name" 2>/dev/null || true
}

install_named_tunnel() {
	# shellcheck disable=SC1091
	source "$GCFG"

	local tunnel_name="${CLOUDFLARE_TUNNEL_NAME:-asaphone-provision}"
	local hostname="${PROVISION_PUBLIC_HOST:-}"

	if [[ -z "$hostname" ]]; then
		echo "PROVISION_PUBLIC_HOST vide — utilisez le mode quick (sans domaine) :" >&2
		echo "  CLOUDFLARE_TUNNEL_MODE=\"quick\" dans network/global-config.env" >&2
		echo "  sudo bash scripts/install-provision-tunnel.sh --quick" >&2
		exit 1
	fi
	if [[ "$hostname" == *"tondomaine"* || "$hostname" == *"example.com"* ]]; then
		echo "Éditez network/global-config.env :" >&2
		echo "  PROVISION_PUBLIC_HOST=\"provision.votredomaine.com\"" >&2
		echo "  (zone DNS gérée par Cloudflare)" >&2
		exit 1
	fi

	local cert
	cert="$(cloudflared_cert_path || true)"
	if [[ -z "$cert" ]]; then
		echo "==> Connexion compte Cloudflare (navigateur)"
		echo "    Choisissez la zone DNS qui hébergera ${hostname}"
		cloudflared tunnel login
		cert="$(cloudflared_cert_path || true)"
	fi
	if [[ -z "$cert" ]]; then
		echo "cert.pem introuvable après login — relancez : cloudflared tunnel login" >&2
		exit 1
	fi

	local cf_home
	cf_home="$(cloudflared_home)"

	echo "==> Tunnel nommé : ${tunnel_name}"
	local tunnel_id
	tunnel_id="$(tunnel_id_by_name "$tunnel_name")"
	if [[ -z "$tunnel_id" ]]; then
		echo "    Création du tunnel…"
		cloudflared tunnel create "$tunnel_name"
		tunnel_id="$(tunnel_id_by_name "$tunnel_name")"
	fi
	if [[ -z "$tunnel_id" ]]; then
		echo "Impossible de récupérer l'ID du tunnel ${tunnel_name}" >&2
		exit 1
	fi
	echo "    ID : ${tunnel_id}"

	local src_creds="${cf_home}/${tunnel_id}.json"
	local etc_dir="/etc/cloudflared/provision"
	mkdir -p "$etc_dir"
	if [[ ! -f "$src_creds" ]]; then
		echo "Credentials introuvables : ${src_creds}" >&2
		exit 1
	fi
	install -m 600 "$src_creds" "${etc_dir}/credentials.json"

	echo "==> Config ${etc_dir}/config.yml"
	sed -e "s|\${CLOUDFLARE_TUNNEL_NAME}|${tunnel_name}|g" \
		-e "s|\${PROVISION_PUBLIC_HOST}|${hostname}|g" \
		"$ROOT/network/cloudflared/config.yml.template" >"${etc_dir}/config.yml"
	chmod 640 "${etc_dir}/config.yml"

	echo "==> DNS CNAME : ${hostname}"
	if ! cloudflared tunnel route dns "$tunnel_name" "$hostname" 2>&1; then
		echo "WARN: route DNS automatique échouée." >&2
		echo "      Créez manuellement un CNAME ${hostname} → ${tunnel_id}.cfargotunnel.com" >&2
	fi

	# tunnel.env (URL fixe — plus de parsing de logs)
	cat >/etc/provision/tunnel.env <<EOF
# Tunnel Cloudflare nommé — domaine fixe (ne change pas au reboot)
CLOUDFLARE_TUNNEL_MODE=named
PROVISION_TUNNEL_URL=https://${hostname}
PROVISION_PUBLIC_BASE_URL=https://${hostname}/provision
EOF
	chmod 640 /etc/provision/tunnel.env
	chown root:www-data /etc/provision/tunnel.env 2>/dev/null || chmod 600 /etc/provision/tunnel.env

	cp "$ROOT/systemd/cloudflared-provision.service" \
		/etc/systemd/system/cloudflared-provision.service
	systemctl daemon-reload
	systemctl enable cloudflared-provision.service
	systemctl restart cloudflared-provision.service

	sleep 2
	bash "$ROOT/scripts/sync-global-config.sh" --deploy

	# shellcheck source=scripts/lib/detect-tunnel-url.sh
	source "$ROOT/scripts/lib/detect-tunnel-url.sh"
	resolve_provision_public_urls 0

	echo ""
	echo "Tunnel nommé actif : https://${hostname}"
	echo "API provision      : ${PROVISION_PUBLIC_BASE_URL}"
	echo ""
	echo "Test :"
	echo "  curl -sk '${PROVISION_PUBLIC_BASE_URL}/'"
	echo ""
	echo "Publier une fois sur GitHub Pages : network/github-pages/provision/bootstrap.json"
	echo "  api_remote : \"${PROVISION_PUBLIC_BASE_URL}\""
}

if [[ "$QUICK" -eq 1 ]]; then
	install_quick_tunnel
elif [[ "${CLOUDFLARE_TUNNEL_MODE:-quick}" == "quick" ]]; then
	install_quick_tunnel
else
	install_named_tunnel
fi
