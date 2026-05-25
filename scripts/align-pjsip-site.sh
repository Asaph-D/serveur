#!/bin/bash
# Applique align-pjsip-endpoint.sh à toutes les extensions listées dans network/pjsip-align.env
# Un seul fwconsole reload à la fin.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV="$ROOT/network/pjsip-align.env"

[[ $(id -u) -eq 0 ]] || { echo "Root requis : sudo bash $0"; exit 1; }
[[ -f "$ENV" ]] || { echo "Fichier introuvable: $ENV"; exit 1; }

# shellcheck disable=SC1090
source "$ENV"

ALIGN="$ROOT/scripts/align-pjsip-endpoint.sh"
[[ -x "$ALIGN" ]] || chmod +x "$ALIGN"

echo "=== PJSIP align site (depuis $ENV) ==="

for ext in ${WEBRTC_EXTENSIONS:-}; do
  [[ -z "$ext" ]] && continue
  echo "--- WebRTC: $ext ---"
  bash "$ALIGN" --webrtc --no-reload "$ext" "${WEBRTC_CODEC_ALLOW:-opus,g722,ulaw,alaw}"
done

for ext in ${CLASSIC_EXTENSIONS:-}; do
  [[ -z "$ext" ]] && continue
  echo "--- Classique: $ext ---"
  bash "$ALIGN" --no-reload "$ext" "${CLASSIC_CODEC_ALLOW:-g722,ulaw,alaw}"
done

echo "=== fwconsole reload ==="
if [[ -x /usr/sbin/fwconsole ]]; then
  /usr/sbin/fwconsole reload
elif [[ -x /var/lib/asterisk/bin/fwconsole ]]; then
  /var/lib/asterisk/bin/fwconsole reload
else
  fwconsole reload
fi

echo "=== Vérification rapide ==="
for ext in ${WEBRTC_EXTENSIONS:-}; do
  [[ -z "$ext" ]] && continue
  echo "--- pjsip show endpoint $ext (webrtc) ---"
  asterisk -rx "pjsip show endpoint $ext" 2>&1 | grep -iE 'webrtc|allow|media_encryption|ice|use_avpf|rtcp_mux' || true
done
for ext in ${CLASSIC_EXTENSIONS:-}; do
  [[ -z "$ext" ]] && continue
  echo "--- pjsip show endpoint $ext (classique) ---"
  asterisk -rx "pjsip show endpoint $ext" 2>&1 | grep -iE 'allow|media_encryption|rtcp_mux|webrtc' || true
done

echo "OK. Pour ajouter une extension plus tard : édite $ENV puis relance ce script."
