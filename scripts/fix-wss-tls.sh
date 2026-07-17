#!/usr/bin/env bash
# Permissions certificats TLS + rechargement HTTP/PJSIP pour WSS (port 8089).
# fwconsole start remet parfois les clés en 0600 ; ce script corrige puis recharge TLS.
# Usage : sudo bash scripts/fix-wss-tls.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $(id -u) -eq 0 ]] || { echo "Root requis." >&2; exit 1; }

bash "${ROOT}/scripts/fix-cert-perms.sh"

# Groupe asterisk : le démon lit les *.key en 0640 (owner www-data, group asterisk).
usermod -aG asterisk asterisk 2>/dev/null || true

if command -v fwconsole >/dev/null 2>&1; then
	# Applique freepbx_chown.conf (clés 0640) sans redémarrer tout le PBX.
	fwconsole chown 2>/dev/null || true
fi

bash "${ROOT}/scripts/fix-cert-perms.sh"

if command -v asterisk >/dev/null 2>&1; then
	asterisk -rx "module reload http.so" 2>/dev/null || true
	asterisk -rx "module reload res_pjsip.so" 2>/dev/null || true
	sleep 1
	if ! ss -tln | grep -q ':8089 '; then
		echo "Port 8089 absent — redémarrage Asterisk pour initialiser TLS WSS..."
		if command -v fwconsole >/dev/null 2>&1; then
			fwconsole stop
			bash "${ROOT}/scripts/fix-cert-perms.sh"
			fwconsole start
			bash "${ROOT}/scripts/fix-cert-perms.sh"
			bash "${ROOT}/scripts/fix-asterisk-run-perms.sh" 2>/dev/null || true
		fi
	fi
fi

if ss -tln | grep -q ':8089 '; then
	echo "OK: WSS actif sur le port 8089"
	asterisk -rx "http show status" 2>/dev/null | grep -E '8088|8089|HTTPS|TLS' || true
else
	echo "ERREUR: port 8089 toujours fermé — vérifier /var/log/asterisk/full (tcptls, certificate.pem)" >&2
	exit 1
fi
