#!/usr/bin/env bash
# Hook FreePBX PRE_RELOAD — reecrit le profil WebRTC en base AVANT retrieve_conf.
# Compatible root / www-data (Apply Config dashboard).
# Ne JAMAIS appeler fwconsole reload ici (boucle).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# /tmp : ecrivible root et www-data (Apply Config)
LOG="${ASAPHONE_PRE_RELOAD_LOG:-/tmp/asaphone-freepbx-pre-reload.log}"
ALIGN="$ROOT/scripts/align-pjsip-endpoint.sh"
ENSURE="$ROOT/scripts/ensure-pjsip-extension.sh"
ENV="$ROOT/network/pjsip-align.env"
PROV="$ROOT/network/provision.env"
[[ -f /etc/provision/provision.env ]] && PROV="/etc/provision/provision.env"

log() { echo "$*" >>"$LOG" 2>/dev/null || true; }

log "=== $(date -Is) PRE_RELOAD uid=$(id -u) user=$(id -un) ==="

# shellcheck disable=SC1090
source "$ENV" 2>/dev/null || true
[[ -f "$PROV" ]] && source "$PROV" 2>/dev/null || true

run_align() {
	local mode="$1" ext="$2" codecs="$3"
	if [[ $(id -u) -eq 0 ]]; then
		if [[ "$mode" == "webrtc" ]]; then
			bash "$ALIGN" --webrtc --no-reload "$ext" "$codecs" >>"$LOG" 2>&1 || log "WARN align $ext failed"
		else
			bash "$ALIGN" --no-reload "$ext" "$codecs" >>"$LOG" 2>&1 || log "WARN align $ext failed"
		fi
	else
		# www-data : ensure via sudo (script dans /home inaccessible en lecture directe)
		sudo -n "$ENSURE" "$ext" >>"$LOG" 2>&1 || log "WARN ensure $ext failed (sudoers?)"
	fi
}

declare -A SEEN=()
for ext in ${WEBRTC_EXTENSIONS:-} ${PROVISION_EXT_POOL:-1003 1004 1005 1006 1007 1008 1009 1010}; do
	[[ -z "$ext" ]] && continue
	[[ -n "${SEEN[$ext]:-}" ]] && continue
	SEEN[$ext]=1
	[[ " ${CLASSIC_EXTENSIONS:-1001 1002} " == *" $ext "* ]] && continue
	log "--- WebRTC $ext ---"
	run_align webrtc "$ext" "${WEBRTC_CODEC_ALLOW:-g722,ulaw,alaw,opus,vp8,h264}"
done
for ext in ${CLASSIC_EXTENSIONS:-1001 1002}; do
	[[ -z "$ext" ]] && continue
	log "--- Classique $ext ---"
	run_align classic "$ext" "${CLASSIC_CODEC_ALLOW:-g722,ulaw,alaw}"
done
log "OK PRE_RELOAD"
exit 0
