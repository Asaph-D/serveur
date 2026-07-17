#!/usr/bin/env bash
# coturn STUN/TURN pour WebRTC (vidéo + audio derrière NAT).
# Usage : sudo bash scripts/install-coturn.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GCFG="$ROOT/network/global-config.env"
SECRETS="/etc/provision/provision-secrets.env"

[[ $(id -u) -eq 0 ]] || { echo "Root requis." >&2; exit 1; }
# shellcheck disable=SC1091
source "$GCFG"

LAN_IP="${PBX_LAN_IP:?PBX_LAN_IP requis}"
TURN_PORT="${PROVISION_TURN_PORT:-3478}"
RELAY_MIN="${PROVISION_TURN_RELAY_MIN:-49160}"
RELAY_MAX="${PROVISION_TURN_RELAY_MAX:-49200}"
PUBLIC="${PUBLIC_IP:-}"

if ! command -v turnserver >/dev/null 2>&1; then
	echo "==> Installation coturn"
	DEBIAN_FRONTEND=noninteractive apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y coturn
fi

mkdir -p /etc/provision
if [[ ! -f "$SECRETS" ]]; then
	touch "$SECRETS"
	chmod 640 "$SECRETS"
	chown root:www-data "$SECRETS"
fi

if ! grep -q '^PROVISION_TURN_SECRET=' "$SECRETS" 2>/dev/null; then
	secret="$(openssl rand -hex 32)"
	echo "PROVISION_TURN_SECRET=${secret}" >>"$SECRETS"
	chmod 640 "$SECRETS"
	chown root:www-data "$SECRETS"
	echo "Secret TURN généré dans $SECRETS"
fi
# shellcheck disable=SC1090
source "$SECRETS"
TURN_SECRET="${PROVISION_TURN_SECRET:?PROVISION_TURN_SECRET manquant}"

EXTERNAL_LINE=""
if [[ -n "$PUBLIC" && "$PUBLIC" != "$LAN_IP" ]]; then
	EXTERNAL_LINE="external-ip=${PUBLIC}/${LAN_IP}"
fi

cat >/etc/turnserver.conf <<EOF
# Généré par install-coturn.sh — Asaphone WebRTC
listening-port=${TURN_PORT}
listening-ip=0.0.0.0
relay-ip=${LAN_IP}
${EXTERNAL_LINE}
min-port=${RELAY_MIN}
max-port=${RELAY_MAX}
realm=${PBX_HOST:-pbx.local}
server-name=${PBX_HOST:-pbx.local}
use-auth-secret
static-auth-secret=${TURN_SECRET}
no-multicast-peers
no-cli
fingerprint
EOF

sed -i 's/^#\?TURNSERVER_ENABLED=.*/TURNSERVER_ENABLED=1/' /etc/default/coturn 2>/dev/null || true
systemctl enable coturn >/dev/null 2>&1 || true
systemctl restart coturn
systemctl is-active coturn

echo "OK coturn — STUN/TURN ${LAN_IP}:${TURN_PORT} (relay ${RELAY_MIN}-${RELAY_MAX})"
