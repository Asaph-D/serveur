#!/usr/bin/env bash
# /var/run/asterisk : reload.lock (Apply Config GUI) + socket asterisk.ctl (asterisk -rx).
# À exécuter après fwconsole start/reload — Asterisk peut recréer le dossier en 755 asterisk:asterisk.
# Usage : sudo bash scripts/fix-asterisk-run-perms.sh
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

WEB_USER="${FREEPBX_WEB_USER:-www-data}"
AST_USER="${FREEPBX_AST_USER:-asterisk}"
AST_GROUP="${FREEPBX_AST_GROUP:-asterisk}"

usermod -aG "$AST_GROUP" "$WEB_USER" 2>/dev/null || true

mkdir -p /var/run/asterisk
# GUI (www-data) doit pouvoir créer reload.lock ; groupe asterisk pour le socket ctl.
chown "${WEB_USER}:${AST_GROUP}" /var/run/asterisk
chmod 2775 /var/run/asterisk

CTL=/var/run/asterisk/asterisk.ctl
if [[ -S "$CTL" ]]; then
	chown "${AST_USER}:${AST_GROUP}" "$CTL"
	chmod 770 "$CTL"
fi

PIDF=/var/run/asterisk/asterisk.pid
if [[ -f "$PIDF" ]]; then
	chown "${AST_USER}:${AST_GROUP}" "$PIDF"
	chmod 664 "$PIDF"
fi

# Lock orphelin : évite erreurs fwconsole reload si le PID n'existe plus.
LOCK=/var/run/asterisk/reload.lock
if [[ -f "$LOCK" ]]; then
	pid="$(tr -dc '0-9' < "$LOCK" | head -c 16 || true)"
	if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
		rm -f "$LOCK"
	fi
fi
