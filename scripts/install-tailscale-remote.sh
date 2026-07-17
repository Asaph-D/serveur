#!/usr/bin/env bash
# Accès distant sans port forward — Tailscale subnet router (Starlink CGNAT).
# Usage : sudo bash scripts/install-tailscale-remote.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GCFG="$ROOT/network/global-config.env"

[[ $(id -u) -eq 0 ]] || { echo "Exécuter en root : sudo bash $0" >&2; exit 1; }

# shellcheck disable=SC1091
source "$GCFG"

ROUTES="${MGMT_CIDR}"
if [[ -n "${VOICE_CIDR:-}" ]]; then
	ROUTES="${ROUTES},${VOICE_CIDR}"
fi

echo "==> Tailscale — routes annoncées : ${ROUTES}"
echo "    PBX LAN : ${PBX_LAN_IP} | Passerelle : ${MGMT_GW:-?}"

if ! command -v tailscale >/dev/null 2>&1; then
	echo "==> Installation Tailscale"
	curl -fsSL https://tailscale.com/install.sh | sh
fi

sysctl -w net.ipv4.ip_forward=1 >/dev/null
grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.d/99-wireguard.conf 2>/dev/null \
	|| echo 'net.ipv4.ip_forward=1' >>/etc/sysctl.d/99-wireguard.conf

systemctl enable --now tailscaled

if command -v ufw >/dev/null 2>&1; then
	ufw allow in on tailscale0 comment 'Tailscale mesh' 2>/dev/null || true
fi

HOSTNAME="asaphone-pbx"
if tailscale status --json 2>/dev/null | grep -q '"BackendState":"Running"'; then
	echo "==> Tailscale déjà connecté — mise à jour des routes"
	tailscale set --hostname="$HOSTNAME" --advertise-routes="$ROUTES" --accept-routes
else
	echo "==> Connexion Tailscale (ouvrir l’URL ci-dessous dans un navigateur)"
	tailscale up \
		--hostname="$HOSTNAME" \
		--advertise-routes="$ROUTES" \
		--accept-routes \
		--ssh=false
fi

echo ""
echo "=== Étape admin Tailscale (une fois) ==="
echo "1. https://login.tailscale.com/admin/machines"
echo "2. Machine « ${HOSTNAME} » → Edit route settings → approuver : ${ROUTES}"
echo ""
echo "=== Sur le téléphone (4G) ==="
echo "1. Installer Tailscale (Play Store / App Store)"
echo "2. Même compte Tailscale que le PBX"
echo "3. Paramètres → activer « Use Tailscale subnets » / routes subnet"
echo "4. Ouvrir Asaphone — ${PBX_LAN_IP} doit répondre sans WireGuard"
echo ""
tailscale status 2>/dev/null || true
IP_TS=$(tailscale ip -4 2>/dev/null || true)
[[ -n "$IP_TS" ]] && echo "IP Tailscale PBX : ${IP_TS}"
