#!/usr/bin/env bash
# Hook FreePBX POST_RELOAD — permissions + bind RTP LAN + verif WebRTC apres Apply Config.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# /tmp : ecrivible root et www-data (Apply Config)
LOG="${ASAPHONE_POST_RELOAD_LOG:-/tmp/asaphone-freepbx-post-reload.log}"
# shellcheck disable=SC1091
source "${ROOT}/network/global-config.env" 2>/dev/null || true
source "${ROOT}/network/pjsip-align.env" 2>/dev/null || true
[[ -f /etc/provision/provision.env ]] && source /etc/provision/provision.env 2>/dev/null || true
# Preferer l IP DHCP live (hotspot variable), sinon global-config.
# shellcheck source=scripts/lib/detect-mgmt-network.sh
source "${ROOT}/scripts/lib/detect-mgmt-network.sh" 2>/dev/null || true
LAN_IP=""
if [[ -n "${MGMT_IFACE:-}" ]] && detect_mgmt_network "$MGMT_IFACE" 2>/dev/null; then
	LAN_IP="$PBX_LAN_IP"
fi
LAN_IP="${LAN_IP:-${PBX_LAN_IP:-}}"

{
	echo "=== $(date -Is) POST_RELOAD uid=$(id -u) ==="
	if [[ $(id -u) -eq 0 ]]; then
		bash "${ROOT}/scripts/fix-cert-perms.sh" 2>/dev/null || true
		bash "${ROOT}/scripts/fix-asterisk-run-perms.sh" 2>/dev/null || true
		# ice_host_candidates doit suivre le DHCP (sinon reste sur ancienne IP LAN)
		if [[ -n "$LAN_IP" ]]; then
			bash "${ROOT}/scripts/apply-rtp-relaxed.sh" --quick 2>/dev/null || true
		fi
	fi

	for e in 1003 1004 1005 1006 1007 1008 1009 1010; do
		w=$(asterisk -rx "pjsip show endpoint $e" 2>/dev/null | awk -F: '/^[[:space:]]*webrtc[[:space:]]+:/{print $NF; exit}' | tr -d ' ')
		i=$(asterisk -rx "pjsip show endpoint $e" 2>/dev/null | awk -F: '/^[[:space:]]*ice_support[[:space:]]+:/{print $NF; exit}' | tr -d ' ')
		b=$(asterisk -rx "pjsip show endpoint $e" 2>/dev/null | awk -F: '/^[[:space:]]*bind_rtp_to_media_address[[:space:]]+:/{print $NF; exit}' | tr -d ' ')
		m=$(asterisk -rx "pjsip show endpoint $e" 2>/dev/null | awk -F: '/^[[:space:]]*media_address[[:space:]]+:/{print $NF; exit}' | tr -d ' ')
		echo "  $e webrtc=${w:-?} ice=${i:-?} bind_rtp=${b:-?} media=${m:-?}"
	done
	echo "OK POST_RELOAD (LAN_IP=${LAN_IP:-?})"
} >>"$LOG" 2>&1 || true
exit 0
