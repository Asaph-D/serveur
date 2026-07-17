#!/usr/bin/env bash
# Détecte le LAN actuel (MGMT_IFACE) et propage vers global-config, bootstrap.json, provision.
# Usage : bash scripts/sync-global-config.sh [--deploy]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GCFG="$ROOT/network/global-config.env"
BOOTSTRAP="$ROOT/network/github-pages/provision/bootstrap.json"

DEPLOY=0
[[ "${1:-}" == "--deploy" ]] && DEPLOY=1

# shellcheck disable=SC1091
source "$GCFG"
PROV="$ROOT/network/provision.env"
[[ -f "$PROV" ]] && source "$PROV"
# shellcheck source=scripts/lib/detect-mgmt-network.sh
source "$ROOT/scripts/lib/detect-mgmt-network.sh"

LAN_DETECTED=1
if ! detect_mgmt_network "${MGMT_IFACE:?MGMT_IFACE requis dans global-config.env}"; then
	echo "WARN: pas d'IP sur ${MGMT_IFACE} — conservation config AUTO existante (démarrage hors ligne ?)" >&2
	# shellcheck disable=SC1091
	source "$GCFG"
	LAN_DETECTED=0
fi
# IP de communication SIP/WSS = DHCP sur l'interface VPN/LAN (souvent la même que MGMT)
if [[ "$LAN_DETECTED" -eq 1 ]]; then
	COMM_IFACE="${VPN_LAN_IFACE:-$MGMT_IFACE}"
	if [[ "$COMM_IFACE" != "$MGMT_IFACE" ]]; then
		_saved_cidr="$MGMT_CIDR"
		_saved_gw="$MGMT_GW"
		if detect_mgmt_network "$COMM_IFACE"; then
			PBX_COMM_IP="$PBX_LAN_IP"
			PBX_COMM_GW="$MGMT_GW"
			MGMT_CIDR="$_saved_cidr"
			MGMT_GW="$_saved_gw"
			PBX_LAN_IP="$PBX_COMM_IP"
			PROVISION_VPN_DNS_HINT="$PBX_COMM_GW"
		else
			PROVISION_VPN_DNS_HINT="$MGMT_GW"
		fi
	else
		PROVISION_VPN_DNS_HINT="$MGMT_GW"
	fi
else
	PROVISION_VPN_DNS_HINT="${MGMT_GW:-}"
fi
detect_public_ip || true

# API distante : domaine fixe (named) ou trycloudflare (quick)
# shellcheck source=scripts/lib/detect-tunnel-url.sh
source "$ROOT/scripts/lib/detect-tunnel-url.sh"
resolve_provision_public_urls 0 || true
detect_wg_relay_tunnel_url 0 || true
detect_wg_relay_tunnel_url 0 || true

VPN_PORT="${PROVISION_VPN_PORT:-51820}"
VPN_TUNNEL="${VPN_TUNNEL_CIDR:-10.200.0.0/24}"

EXTRA_LAN_CIDRS="${MGMT_CIDR} ${VPN_TUNNEL}"
PROVISION_VPN_LAN_IP="$PBX_LAN_IP"
PROVISION_VPN_LAN_ENDPOINT="${PBX_LAN_IP}:${VPN_PORT}"
PROVISION_VPN_DNS="${PROVISION_VPN_DNS_HINT:-$MGMT_GW}"

ALLOWED="${MGMT_CIDR},${VOICE_CIDR},${VPN_TUNNEL}"
if [[ -n "${EXTRA_VOICE_CIDRS:-}" ]]; then
	for c in $EXTRA_VOICE_CIDRS; do
		[[ -z "$c" ]] && continue
		ALLOWED="${ALLOWED},${c}"
	done
fi
PROVISION_VPN_ALLOWED_IPS="$ALLOWED"

if [[ -n "${PUBLIC_IP:-}" ]]; then
	PROVISION_VPN_PUBLIC_ENDPOINT="${PUBLIC_IP}:${VPN_PORT}"
fi

PROVISION_REMOTE_ACCESS_MODE="${PROVISION_REMOTE_ACCESS_MODE:-auto}"
PROVISION_WG_REMOTE_ENABLE="yes"
if [[ "$PROVISION_REMOTE_ACCESS_MODE" == "tailscale" ]]; then
	PROVISION_REMOTE_ACCESS_MODE="auto"
fi
if [[ "$PROVISION_REMOTE_ACCESS_MODE" == "auto" || "$PROVISION_REMOTE_ACCESS_MODE" == "wss-relay" ]] && [[ -n "${MGMT_GW:-}" ]]; then
	if curl -sf -m 3 "http://${MGMT_GW}/" 2>/dev/null | grep -qi '<title>Starlink</title>'; then
		PROVISION_REMOTE_ACCESS_MODE="wss-relay"
		PROVISION_WG_REMOTE_ENABLE="no"
	fi
elif [[ "$PROVISION_REMOTE_ACCESS_MODE" == "wss-relay" ]]; then
	PROVISION_WG_REMOTE_ENABLE="no"
fi

AUTO_BLOCK="# >>> AUTO-GENERATED — ne pas éditer (sync-global-config.sh / serveur-startup)
PBX_LAN_IP=\"${PBX_LAN_IP}\"
MGMT_CIDR=\"${MGMT_CIDR}\"
MGMT_GW=\"${MGMT_GW:-}\"
PUBLIC_IP=\"${PUBLIC_IP:-}\"
PROVISION_VPN_PUBLIC_ENDPOINT=\"${PROVISION_VPN_PUBLIC_ENDPOINT:-}\"
EXTRA_LAN_CIDRS=\"${EXTRA_LAN_CIDRS}\"
PROVISION_VPN_LAN_IP=\"${PROVISION_VPN_LAN_IP}\"
PROVISION_VPN_LAN_ENDPOINT=\"${PROVISION_VPN_LAN_ENDPOINT}\"
PROVISION_VPN_DNS=\"${PROVISION_VPN_DNS}\"
PROVISION_VPN_ALLOWED_IPS=\"${PROVISION_VPN_ALLOWED_IPS}\"
PROVISION_REMOTE_ACCESS_MODE=\"${PROVISION_REMOTE_ACCESS_MODE}\"
PROVISION_WG_REMOTE_ENABLE=\"${PROVISION_WG_REMOTE_ENABLE}\"
# <<< AUTO-GENERATED"

tmp="$(mktemp)"
awk -v repl="$AUTO_BLOCK" '
  /^# >>> AUTO-GENERATED/ { print repl; skip=1; next }
  /^# <<< AUTO-GENERATED/ { skip=0; next }
  !skip { print }
' "$GCFG" >"$tmp"
mv "$tmp" "$GCFG"

# bootstrap.json (découverte GitHub Pages)
mkdir -p "$(dirname "$BOOTSTRAP")"
DISC="${PROVISION_DISCOVERY_URL}"
API_LAN="https://${PBX_HOST}/provision"
API_LAN_IP="https://${PBX_LAN_IP}/provision"
API_REMOTE="${PROVISION_PUBLIC_BASE_URL}"
SIP_SERVER="${PBX_LAN_IP}"
WSS_URL="wss://${PBX_LAN_IP}:${PROVISION_WSS_PORT:-8089}/ws"
WSS_LAN="$WSS_URL"
VPN_REMOTE="${PROVISION_VPN_PUBLIC_ENDPOINT:-}"
TURN_PORT="${PROVISION_TURN_PORT:-3478}"
VIDEO_CODECS="${PROVISION_VIDEO_CODECS:-vp8,h264}"
ICE_STUN="stun:${PBX_LAN_IP}:${TURN_PORT}"
if [[ "$PROVISION_REMOTE_ACCESS_MODE" == "tailscale" ]]; then
	BOOTSTRAP_NOTES="4G/Starlink : relay WSS intégré Asaphone (pas UDP direct). Wi-Fi site : endpoint_lan ou LAN direct."
elif [[ "$PROVISION_REMOTE_ACCESS_MODE" == "wss-relay" ]]; then
	BOOTSTRAP_NOTES="4G/Starlink : relay WSS intégré Asaphone (pas UDP direct). Wi-Fi site : endpoint_lan ou LAN direct."
else
	BOOTSTRAP_NOTES="sip_server / wss_url = IP LAN. ice_servers = STUN ; TURN via claim/reconnect."
fi

TUNNEL_WSS="${PROVISION_WG_RELAY_WSS_URL:-}"
if [[ -z "$TUNNEL_WSS" && "$PROVISION_REMOTE_ACCESS_MODE" == "wss-relay" && "$API_REMOTE" =~ ^https?://([^/]+) ]]; then
	if [[ "$API_REMOTE" == https://* ]]; then
		TUNNEL_WSS="wss://${BASH_REMATCH[1]}/wg-relay"
	else
		TUNNEL_WSS="ws://${BASH_REMATCH[1]}/wg-relay"
	fi
fi

if command -v jq >/dev/null 2>&1; then
	VIDEO_JSON=$(jq -n --arg vc "$VIDEO_CODECS" '$vc | split(",") | map(gsub("^\\s+|\\s+$";"")) | map(select(length>0))')
	ICE_JSON=$(jq -n --arg stun "$ICE_STUN" '[{urls: [$stun]}]')
	jq -n \
		--arg version "1" \
		--arg service "asaphone-provision" \
		--arg discovery_url "$DISC" \
		--arg api_lan "$API_LAN" \
		--arg api_remote "$API_REMOTE" \
		--arg pbx_host "$PBX_HOST" \
		--arg pbx_lan_ip "$PBX_LAN_IP" \
		--arg sip_server "$SIP_SERVER" \
		--arg api_lan_ip "$API_LAN_IP" \
		--argjson wss_port "${PROVISION_WSS_PORT:-8089}" \
		--arg wss_url "$WSS_URL" \
		--arg wss_url_lan "$WSS_LAN" \
		--arg endpoint_remote "$VPN_REMOTE" \
		--arg endpoint_lan "$PROVISION_VPN_LAN_ENDPOINT" \
		--arg allowed_ips "$PROVISION_VPN_ALLOWED_IPS" \
		--arg remote_mode "$PROVISION_REMOTE_ACCESS_MODE" \
		--arg wg_remote "$PROVISION_WG_REMOTE_ENABLE" \
		--arg mgmt_cidr "$MGMT_CIDR" \
		--arg voice_cidr "$VOICE_CIDR" \
		--arg notes "$BOOTSTRAP_NOTES" \
		--arg tunnel_wss "$TUNNEL_WSS" \
		--argjson video_codecs "$VIDEO_JSON" \
		--argjson ice_servers "$ICE_JSON" \
		'{
			version: ($version | tonumber),
			service: $service,
			discovery_url: $discovery_url,
			api_lan: $api_lan,
			api_remote: $api_remote,
			pbx_host: $pbx_host,
			pbx_lan_ip: $pbx_lan_ip,
			sip_server: $sip_server,
			api_lan_ip: $api_lan_ip,
			wss_port: $wss_port,
			wss_url: $wss_url,
			wss_url_lan: $wss_url_lan,
			video_codecs: $video_codecs,
			ice_servers: $ice_servers,
			vpn: {
				enable: true,
				wireguard_remote_available: ($wg_remote == "yes"),
				endpoint_remote: (if $wg_remote == "yes" then $endpoint_remote else "" end),
				endpoint_lan: $endpoint_lan,
				allowed_ips: $allowed_ips
			},
			remote_access: {
				mode: $remote_mode,
				wss_relay: (if $remote_mode == "wss-relay" and ($tunnel_wss | length) > 0 then {
					tunnel_wss: $tunnel_wss,
					wireguard_endpoint: "127.0.0.1:51820",
					hint: "Relay WSS intégré Asaphone — pas d app externe"
				} else null end)
			},
			endpoints: {
				register: "/api/v1/register.php",
				verify: "/api/v1/verify.php",
				claim: "/api/v1/claim.php",
				reconnect: "/api/v1/reconnect.php",
				session: "/api/v1/session.php",
				vpn_register: "/api/v1/vpn/register.php",
				vpn_verify: "/api/v1/vpn/verify.php",
				vpn_claim: "/api/v1/vpn/claim.php",
				vpn_enroll: "/api/v1/vpn/enroll.php",
				vpn_revoke: "/api/v1/vpn/revoke.php",
				vpn_status: "/api/v1/vpn/status.php",
				groups_sync: "/api/v1/groups/sync.php",
				groups_list: "/api/v1/groups/list.php",
				conference_invite: "/api/v1/conference/invite.php"
			},
			conference: {
				default_call_uri: "6000",
				default_room: "6000",
				room_prefix: "asaphone-grp-",
				dial_mode: "extension"
			},
			deeplink_scheme: "asaphone",
			notes: $notes
		}' >"$BOOTSTRAP"
else
	cat >"$BOOTSTRAP" <<EOF
{
  "version": 1,
  "service": "asaphone-provision",
  "discovery_url": "${DISC}",
  "api_lan": "${API_LAN}",
  "api_remote": "${API_REMOTE}",
  "pbx_host": "${PBX_HOST}",
  "pbx_lan_ip": "${PBX_LAN_IP}",
  "sip_server": "${SIP_SERVER}",
  "api_lan_ip": "${API_LAN_IP}",
  "wss_port": ${PROVISION_WSS_PORT:-8089},
  "wss_url": "${WSS_URL}",
  "wss_url_lan": "${WSS_LAN}",
  "video_codecs": ["vp8", "h264"],
  "ice_servers": [{"urls": ["stun:${PBX_LAN_IP}:${TURN_PORT}"]}],
  "vpn": {
    "enable": true,
    "endpoint_remote": "${VPN_REMOTE}",
    "endpoint_lan": "${PROVISION_VPN_LAN_ENDPOINT}",
    "allowed_ips": "${PROVISION_VPN_ALLOWED_IPS}"
  },
  "endpoints": {
    "register": "/api/v1/register.php",
    "verify": "/api/v1/verify.php",
    "claim": "/api/v1/claim.php",
    "reconnect": "/api/v1/reconnect.php",
    "session": "/api/v1/session.php",
    "vpn_register": "/api/v1/vpn/register.php",
    "vpn_verify": "/api/v1/vpn/verify.php",
    "vpn_claim": "/api/v1/vpn/claim.php",
    "vpn_enroll": "/api/v1/vpn/enroll.php",
    "vpn_status": "/api/v1/vpn/status.php",
    "groups_sync": "/api/v1/groups/sync.php",
    "groups_list": "/api/v1/groups/list.php",
    "conference_invite": "/api/v1/conference/invite.php"
  },
  "conference": {
    "default_call_uri": "6000",
    "default_room": "6000",
    "room_prefix": "asaphone-grp-",
    "dial_mode": "extension"
  },
  "deeplink_scheme": "asaphone",
  "notes": "sip_server / wss_url / api_lan_ip = IP DHCP sur VPN_LAN_IFACE. pbx_host = mDNS optionnel."
}
EOF
fi

# Propager les clés VPN dans provision.env (section AUTO)
PROV="$ROOT/network/provision.env"
RELAY_PREFIX=""
[[ -f /etc/provision/wg-relay.env ]] && RELAY_PREFIX="$(grep -E '^PROVISION_WG_RELAY_PATH_PREFIX=' /etc/provision/wg-relay.env | cut -d= -f2- | tr -d '"')"
if [[ -f "$PROV" ]]; then
	prov_auto="# >>> AUTO-GENERATED — sync-global-config.sh
PROVISION_PUBLIC_HOST=\"${PROVISION_PUBLIC_HOST:-}\"
PROVISION_PUBLIC_BASE_URL=\"${PROVISION_PUBLIC_BASE_URL:-}\"
PROVISION_VPN_LAN_IP=\"${PROVISION_VPN_LAN_IP}\"
PROVISION_VPN_LAN_ENDPOINT=\"${PROVISION_VPN_LAN_ENDPOINT}\"
PROVISION_VPN_DNS=\"${PROVISION_VPN_DNS}\"
PROVISION_VPN_ALLOWED_IPS=\"${PROVISION_VPN_ALLOWED_IPS}\"
PROVISION_VPN_PUBLIC_ENDPOINT=\"${PROVISION_VPN_PUBLIC_ENDPOINT:-}\"
PROVISION_REMOTE_ACCESS_MODE=\"${PROVISION_REMOTE_ACCESS_MODE}\"
PROVISION_WG_REMOTE_ENABLE=\"${PROVISION_WG_REMOTE_ENABLE}\"
PROVISION_WG_RELAY_PATH_PREFIX=\"${RELAY_PREFIX}\"
PROVISION_WG_RELAY_WSS_URL=\"${PROVISION_WG_RELAY_WSS_URL:-}\"
# <<< AUTO-GENERATED"
	tmp2="$(mktemp)"
	if grep -q '^# >>> AUTO-GENERATED' "$PROV"; then
		awk -v repl="$prov_auto" '
		  /^# >>> AUTO-GENERATED/ { print repl; skip=1; next }
		  /^# <<< AUTO-GENERATED/ { skip=0; next }
		  !skip { print }
		' "$PROV" >"$tmp2"
	else
		cat "$PROV" >"$tmp2"
		printf '\n%s\n' "$prov_auto" >>"$tmp2"
	fi
	mv "$tmp2" "$PROV"
fi

# windows-hosts.txt
OUT="$ROOT/network/windows-hosts.txt"
{
	echo "# Copier dans C:\\Windows\\System32\\drivers\\etc\\hosts (admin)"
	echo "# Généré par sync-global-config.sh — réseau ${MGMT_CIDR}"
	echo "${PBX_LAN_IP}  ${PBX_MDNS_NAME}.local  ${PBX_MDNS_NAME}"
} >"$OUT"

echo "=== sync-global-config ==="
echo "  Interface   : ${MGMT_IFACE}"
echo "  PBX LAN IP  : ${PBX_LAN_IP}"
echo "  MGMT CIDR   : ${MGMT_CIDR}"
echo "  Passerelle  : ${MGMT_GW:-?}"
echo "  IP publique : ${PUBLIC_IP:-?}"
echo "  Accès dist. : ${PROVISION_REMOTE_ACCESS_MODE} (WG remote=${PROVISION_WG_REMOTE_ENABLE})"
echo "  API remote  : ${PROVISION_PUBLIC_BASE_URL:-?} (${PROVISION_PUBLIC_HOST:-})"
echo "  bootstrap   : ${BOOTSTRAP}"
echo "  hosts Win   : ${OUT}"

if [[ "$DEPLOY" -eq 1 && "$(id -u)" -eq 0 && -f /etc/provision/provision.env ]]; then
	echo "==> Déploiement /etc/provision"
	cp "$GCFG" /etc/provision/global-config.env
	cp "$PROV" /etc/provision/provision.env
	chown root:www-data /etc/provision/global-config.env /etc/provision/provision.env
	chmod 640 /etc/provision/global-config.env /etc/provision/provision.env
	# Garder les fichiers du dépôt modifiables par l'utilisateur du projet
	if [[ -n "${SUDO_USER:-}" ]]; then
		chown "${SUDO_USER}:${SUDO_USER}" "$GCFG" "$PROV" "$BOOTSTRAP" "$OUT" 2>/dev/null || true
	fi
fi

echo "OK — publier bootstrap.json sur GitHub Pages si api_remote ou pbx_lan_ip ont changé."
