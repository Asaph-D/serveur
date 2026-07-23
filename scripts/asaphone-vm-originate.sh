#!/bin/bash
# Originate vm-notify-out (root / asterisk socket)
# Usage: asaphone-vm-originate <ext> <caller> [token]
# token = fichier unique vm-notify-<ext>-<token>.json (évite course concurrente)
set -euo pipefail
EXT="${1:?extension}"
CALLER="${2:-pbx}"
TOKEN="${3:-}"
CALLER="$(printf '%s' "$CALLER" | tr -cd 'A-Za-z0-9._+-')"
[[ -n "$CALLER" ]] || CALLER=pbx
EXT="$(printf '%s' "$EXT" | tr -cd '0-9')"
[[ -n "$EXT" ]] || { echo "extension invalide" >&2; exit 2; }
TOKEN="$(printf '%s' "$TOKEN" | tr -cd 'A-Za-z0-9')"

TMPDIR="${ASAPHONE_VM_NOTIFY_TMP:-/var/lib/provision/tmp}"
mkdir -p "$TMPDIR"

if [[ -n "$TOKEN" ]]; then
	printf '%s' "$CALLER" >"${TMPDIR}/vm-notify-${EXT}-${TOKEN}.caller"
	chmod 666 "${TMPDIR}/vm-notify-${EXT}-${TOKEN}.caller" 2>/dev/null || true
	# Local/1005.token@vm-notify-out — dialplan parse EXTEN
	asterisk -rx "channel originate Local/${EXT}.${TOKEN}@vm-notify-out/n application NoOp notify"
else
	printf '%s' "$CALLER" >"${TMPDIR}/vm-notify-${EXT}.caller"
	chmod 666 "${TMPDIR}/vm-notify-${EXT}.caller" 2>/dev/null || true
	asterisk -rx "channel originate Local/${EXT}@vm-notify-out/n application NoOp notify"
fi
