#!/usr/bin/env bash
# Aligne le profil PJSIP d'une extension (WebRTC ou classique) — idempotent.
# Usage : ensure-pjsip-extension.sh <ext> [--reload]
# Appelé par align-pjsip-site.sh, server-startup, provision (sudo www-data).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_ALIGN="$ROOT/network/pjsip-align.env"
ENV_PROV="$ROOT/network/provision.env"
[[ -f /etc/provision/provision.env ]] && ENV_PROV="/etc/provision/provision.env"

[[ $# -ge 1 ]] || { echo "Usage: $0 <extension> [--reload]" >&2; exit 2; }
EXT="$1"
DO_RELOAD=0
[[ "${2:-}" == "--reload" ]] && DO_RELOAD=1

if ! [[ "$EXT" =~ ^[0-9]{2,6}$ ]]; then
	echo "Extension invalide: $EXT" >&2
	exit 2
fi

# shellcheck disable=SC1090
source "$ENV_ALIGN"
[[ -f "$ENV_PROV" ]] && source "$ENV_PROV"

CLASSIC_SET=" ${CLASSIC_EXTENSIONS:-1001 1002} "
WEBRTC_SET=" ${WEBRTC_EXTENSIONS:-} "
POOL_SET=" ${PROVISION_EXT_POOL:-1003 1004 1005 1006 1007 1008 1009 1010} "

WEBRTC=0
if [[ "$CLASSIC_SET" == *" $EXT "* ]]; then
	WEBRTC=0
elif [[ "$WEBRTC_SET" == *" $EXT "* ]] || [[ "$POOL_SET" == *" $EXT "* ]]; then
	WEBRTC=1
else
	# Extension hors pool : profil classique par défaut (téléphone UDP)
	WEBRTC=0
fi

ALIGN="$ROOT/scripts/align-pjsip-endpoint.sh"
[[ -x "$ALIGN" ]] || chmod +x "$ALIGN"

if [[ "$WEBRTC" -eq 1 ]]; then
	bash "$ALIGN" --webrtc --no-reload "$EXT" "${WEBRTC_CODEC_ALLOW:-g722,ulaw,alaw,opus,vp8,h264}"
else
	bash "$ALIGN" --no-reload "$EXT" "${CLASSIC_CODEC_ALLOW:-g722,ulaw,alaw}"
fi

if [[ "$DO_RELOAD" -eq 1 ]]; then
	if [[ -x /usr/sbin/fwconsole ]]; then
		/usr/sbin/fwconsole reload >/dev/null
	elif command -v fwconsole >/dev/null 2>&1; then
		fwconsole reload >/dev/null
	fi
fi
