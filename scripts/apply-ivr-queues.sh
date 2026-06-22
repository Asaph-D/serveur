#!/usr/bin/env bash
# Files d'attente IVR — une queue par extension 1001-1010 + dialplan 7101-7110 / 7010.
# Usage : sudo bash scripts/apply-ivr-queues.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUEUES_SRC="$REPO/phase3/asterisk/queues-ivr.conf"
QUEUES_DST="/etc/asterisk/queues_custom.conf"
EXT_CUSTOM="/etc/asterisk/extensions_custom.conf"
MARK_BEGIN=";>>>BEGIN_IVR_QUEUES"
MARK_END=";<<<END_IVR_QUEUES"
PHASE3_END=";<<<END_PHASE3"

if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

if [[ ! -f "$QUEUES_SRC" ]]; then
	echo "Fichier introuvable : $QUEUES_SRC" >&2
	exit 1
fi

echo "==> Queues IVR (1001-1010 + phase3-support)"
echo "==> Enregistrement FreePBX (UI Applications → Queues)"
php "$REPO/scripts/apply-ivr-queues-freepbx.php"

echo "==> Dialplan IVR queues (contexte from-internal-custom)"
IVR_BLOCK=$(cat <<'DIAL'

;>>>BEGIN_IVR_QUEUES
; Files par extension — composer 7101 (→1001) … 7110 (→1010)

exten => 7010,1,NoOp(Phase3 IVR AGI + queue)
 same => n,AGI(phase3_intelligent_ivr.py,fr)
 same => n,Read(QEXT,beep,4,,,5)
 same => n,GotoIf($[${LEN(${QEXT})} >= 4]?ivr-q,hang7010)
 same => n(ivr-q),Queue(ivr-ext-${QEXT},t,,,90)
 same => n,Hangup()
 same => n(hang7010),Hangup()

exten => _71XX,1,NoOp(IVR queue shortcut ${EXTEN})
 same => n,Set(IVR_EXT=$[1000 + ${EXTEN} - 7100])
 same => n,GotoIf($[${IVR_EXT} >= 1001 & ${IVR_EXT} <= 1010]?go,invalid)
 same => n(go),Queue(ivr-ext-${IVR_EXT},t,,,90)
 same => n,Hangup()
 same => n(invalid),Playback(invalid)
 same => n,Hangup()
;<<<END_IVR_QUEUES
DIAL
)

# Retirer tout ancien bloc IVR (mauvais contexte possible)
if grep -qF "$MARK_BEGIN" "$EXT_CUSTOM" 2>/dev/null; then
	sed -i "/$(printf '%s' "$MARK_BEGIN" | sed 's/[;]/\\&/g')/,/$(printf '%s' "$MARK_END" | sed 's/[;]/\\&/g')/d" "$EXT_CUSTOM"
fi

# Retirer commentaire IVR AGI orphelin laissé par une appli précédente
sed -i '/^; IVR intelligent (AGI Python)$/d' "$EXT_CUSTOM"

if grep -qF "$MARK_BEGIN" "$EXT_CUSTOM" 2>/dev/null; then
	echo "Bloc IVR queues déjà présent dans from-internal-custom"
else
	if grep -qF "$PHASE3_END" "$EXT_CUSTOM" 2>/dev/null; then
		# Insérer avant la fin du bloc Phase 3 (contexte from-internal-custom)
		awk -v block="$IVR_BLOCK" '
			index($0, ";<<<END_PHASE3") { print block }
			{ print }
		' "$EXT_CUSTOM" > "${EXT_CUSTOM}.tmp"
		mv "${EXT_CUSTOM}.tmp" "$EXT_CUSTOM"
		echo "Bloc IVR queues inséré avant END_PHASE3"
	else
		{
			echo ""
			echo "[from-internal-custom]"
			printf '%s\n' "$IVR_BLOCK"
		} >> "$EXT_CUSTOM"
		echo "Bloc IVR queues ajouté (fin de fichier)"
	fi
fi

chown asterisk:asterisk "$EXT_CUSTOM" 2>/dev/null || true

echo "==> Reload FreePBX"
if command -v fwconsole >/dev/null 2>&1; then
	fwconsole reload
else
	/usr/sbin/asterisk -rx "dialplan reload"
	/usr/sbin/asterisk -rx "module reload app_queue.so"
fi
echo "  phase3-support  → 7020 (postes 1001-1010)"
echo "  ivr-ext-100X    → 710X ou saisie extension sur 7010"
echo ""
echo "Vérifications :"
echo "  sudo asterisk -rx \"queue show ivr-ext-1007\""
echo "  sudo asterisk -rx \"dialplan show from-internal-custom\" | grep 7107"
