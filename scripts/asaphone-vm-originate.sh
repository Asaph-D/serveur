#!/bin/bash
# Originate vm-notify-out (root / asterisk socket)
# Asterisk 20 : pas de prefixe {VAR=val} sur channel originate (→ WARNING tech invalide).
set -euo pipefail
EXT="${1:?extension}"
CALLER="${2:-pbx}"
# Sanitiser (chiffres / court id)
CALLER="$(printf '%s' "$CALLER" | tr -cd 'A-Za-z0-9._+-')"
[[ -n "$CALLER" ]] || CALLER=pbx
EXT="$(printf '%s' "$EXT" | tr -cd '0-9')"
[[ -n "$EXT" ]] || { echo "extension invalide" >&2; exit 2; }

TMPDIR="${ASAPHONE_VM_NOTIFY_TMP:-/var/lib/provision/tmp}"
mkdir -p "$TMPDIR"
# Dialplan vm-notify-out lit ce fichier pour MESSAGE(from)
printf '%s' "$CALLER" >"${TMPDIR}/vm-notify-${EXT}.caller"
chmod 666 "${TMPDIR}/vm-notify-${EXT}.caller" 2>/dev/null || true

asterisk -rx "channel originate Local/${EXT}@vm-notify-out/n application NoOp notify"
