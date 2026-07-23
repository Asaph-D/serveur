#!/bin/bash
# Applique align-pjsip-endpoint.sh à toutes les extensions listées dans network/pjsip-align.env
# + pool provision (PROVISION_EXT_POOL) — source unique pour les postes Asaphone WebRTC.
#
# Usage :
#   sudo bash align-pjsip-site.sh           # DB + fwconsole reload
#   sudo bash align-pjsip-site.sh --db-only # DB seulement (hook PRE_RELOAD FreePBX)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV="$ROOT/network/pjsip-align.env"
PROV="$ROOT/network/provision.env"
[[ -f /etc/provision/provision.env ]] && PROV="/etc/provision/provision.env"

DB_ONLY=0
[[ "${1:-}" == "--db-only" ]] && DB_ONLY=1

[[ $(id -u) -eq 0 ]] || { echo "Root requis : sudo bash $0"; exit 1; }
[[ -f "$ENV" ]] || { echo "Fichier introuvable: $ENV"; exit 1; }

# shellcheck disable=SC1090
source "$ENV"
[[ -f "$PROV" ]] && source "$PROV"

ENSURE="$ROOT/scripts/ensure-pjsip-extension.sh"
[[ -x "$ENSURE" ]] || chmod +x "$ENSURE"

echo "=== PJSIP align site (depuis $ENV + pool provision)${DB_ONLY:+ — DB only} ==="

declare -A SEEN=()
ALIGN_LIST=()
for ext in ${WEBRTC_EXTENSIONS:-} ${PROVISION_EXT_POOL:-}; do
	[[ -z "$ext" ]] && continue
	[[ -n "${SEEN[$ext]:-}" ]] && continue
	SEEN[$ext]=1
	if [[ " ${CLASSIC_EXTENSIONS:-} " == *" $ext "* ]]; then
		continue
	fi
	ALIGN_LIST+=("$ext")
done

for ext in "${ALIGN_LIST[@]}"; do
	echo "--- WebRTC (pool): $ext ---"
	bash "$ENSURE" "$ext"
done

for ext in ${CLASSIC_EXTENSIONS:-}; do
	[[ -z "$ext" ]] && continue
	echo "--- Classique: $ext ---"
	bash "$ENSURE" "$ext"
done

if [[ "$DB_ONLY" -eq 1 ]]; then
	echo "OK (DB only — pas de fwconsole reload)."
	exit 0
fi

echo "=== fwconsole reload ==="
if [[ -x /usr/sbin/fwconsole ]]; then
	/usr/sbin/fwconsole reload
elif [[ -x /var/lib/asterisk/bin/fwconsole ]]; then
	/var/lib/asterisk/bin/fwconsole reload
else
	fwconsole reload
fi

echo "=== Vérification rapide ==="
for ext in "${ALIGN_LIST[@]}"; do
	echo "--- pjsip show endpoint $ext (webrtc) ---"
	asterisk -rx "pjsip show endpoint $ext" 2>&1 | grep -iE 'webrtc|allow|media_encryption|ice|use_avpf|rtcp_mux' || true
done
for ext in ${CLASSIC_EXTENSIONS:-}; do
	[[ -z "$ext" ]] && continue
	echo "--- pjsip show endpoint $ext (classique) ---"
	asterisk -rx "pjsip show endpoint $ext" 2>&1 | grep -iE 'allow|media_encryption|rtcp_mux|webrtc' || true
done

echo "OK. Pour ajouter une extension plus tard : édite $ENV puis relance ce script."
