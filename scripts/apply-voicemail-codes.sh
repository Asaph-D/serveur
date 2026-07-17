#!/usr/bin/env bash
# Codes messagerie vocale directs : *81001 … *81010 → boîte 1001–1010
# Usage : sudo bash scripts/apply-voicemail-codes.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_CUSTOM="/etc/asterisk/extensions_custom.conf"
MARK_BEGIN=";>>>BEGIN_VM_CODES"
MARK_END=";<<<END_VM_CODES"
PHASE3_END=";<<<END_PHASE3"

if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

VM_BLOCK=$(cat <<'DIAL'

;>>>BEGIN_VM_CODES
; Messagerie directe : *81001 (poste 1001) … *81010 (poste 1010)
; Depuis SON propre poste : accès sans PIN (option s). Sinon : PIN = 4 derniers chiffres de l’extension.

exten => _*810XX,1,NoOp(Messagerie directe ext 1${EXTEN:3})
 same => n,Set(VMEXT=1${EXTEN:3})
 same => n,GotoIf($[${VMEXT} < 1001 | ${VMEXT} > 1010]?invalid)
 same => n,GotoIf($["${CALLERID(num)}" = "${VMEXT}"]?vmskip)
 same => n,Set(VMOPTS=)
 same => n,Goto(vmcodecs)
 same => n(vmskip),Set(VMOPTS=s)
 same => n(vmcodecs),NoOp(VM WebRTC ext ${VMEXT})
 same => n,Answer()
 same => n,Wait(0.5)
 same => n,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMailMain(${VMEXT}@default,${VMOPTS})
 same => n,Hangup()
 same => n(invalid),Playback(invalid)
 same => n,Hangup()
;<<<END_VM_CODES
DIAL
)

if grep -qF "$MARK_BEGIN" "$EXT_CUSTOM" 2>/dev/null; then
	sed -i "/$(printf '%s' "$MARK_BEGIN" | sed 's/[;]/\\&/g')/,/$(printf '%s' "$MARK_END" | sed 's/[;]/\\&/g')/d" "$EXT_CUSTOM"
fi

if grep -qF "$PHASE3_END" "$EXT_CUSTOM" 2>/dev/null; then
	awk -v block="$VM_BLOCK" '
		index($0, ";<<<END_PHASE3") { print block }
		{ print }
	' "$EXT_CUSTOM" > "${EXT_CUSTOM}.tmp"
	mv "${EXT_CUSTOM}.tmp" "$EXT_CUSTOM"
else
	printf '%s\n' "$VM_BLOCK" >> "$EXT_CUSTOM"
fi

chown www-data:asterisk "$EXT_CUSTOM" 2>/dev/null || chown asterisk:asterisk "$EXT_CUSTOM" 2>/dev/null || true

echo "Codes messagerie : *81001 … *81010"
if command -v fwconsole >/dev/null 2>&1; then
	fwconsole reload
else
	asterisk -rx "dialplan reload"
fi

echo "PIN par défaut : 4 derniers chiffres (ex. 1003 → 1003)"
echo "Ré-appliquer config VM : sudo php $REPO/scripts/phase2-enable-voicemail.php && fwconsole reload"
