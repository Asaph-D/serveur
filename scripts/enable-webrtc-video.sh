#!/usr/bin/env bash
# Active la vidéo WebRTC côté serveur : codecs VP8/H.264, Opus, coturn, ICE.
#
# Usage : sudo bash scripts/enable-webrtc-video.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/network/global-config.env"

[[ $(id -u) -eq 0 ]] || { echo "Root requis : sudo bash $0" >&2; exit 1; }

echo "=== 1) WSS Asterisk (si pas déjà fait) ==="
bash "$ROOT/scripts/enable-webrtc-websocket.sh"

echo "=== 2) coturn STUN/TURN ==="
if [[ "${PROVISION_TURN_ENABLE:-yes}" == "yes" ]]; then
	bash "$ROOT/scripts/install-coturn.sh"
else
	echo "PROVISION_TURN_ENABLE≠yes — coturn ignoré"
fi

echo "=== 3) Codecs + profil WebRTC (opus, vp8, h264) ==="
bash "$ROOT/scripts/align-pjsip-site.sh"

echo "=== 4) Réseau + UFW + externip ==="
bash "$ROOT/scripts/net-apply-site.sh"

echo "=== 5) Sync bootstrap (ice_servers, video_codecs) ==="
bash "$ROOT/scripts/sync-global-config.sh" --deploy

echo "=== 6) Déploiement API provision ==="
if [[ -x "$ROOT/scripts/provision-install.sh" ]]; then
	bash "$ROOT/scripts/provision-install.sh" 2>/dev/null | tail -5 || rsync -a "$ROOT/provision/" /var/www/provision/
else
	rsync -a "$ROOT/provision/" /var/www/provision/
fi

echo ""
echo "Vérifications :"
asterisk -rx "pjsip show endpoint 1003" 2>&1 | grep -iE 'allow|max_video' || true
curl -sk "https://${PBX_LAN_IP:-127.0.0.1}/provision/" 2>/dev/null | head -c 300 || true
echo ""
echo "OK — vidéo WebRTC activée côté PBX."
echo "L'app doit : getUserMedia(caméra) + m-line video dans SDP + ice_servers du claim/reconnect."
