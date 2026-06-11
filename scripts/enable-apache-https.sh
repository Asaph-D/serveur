#!/usr/bin/env bash
# Active HTTPS Apache (port 443) avec le certificat FreePBX /etc/asterisk/keys/default.*
# Usage : sudo bash scripts/enable-apache-https.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSL_SITE="freepbx-ssl"
CERT_CRT="/etc/asterisk/keys/default.crt"
CERT_KEY="/etc/asterisk/keys/default.key"

if [[ "$(id -u)" -ne 0 ]]; then
	echo "Exécuter en root : sudo bash $0" >&2
	exit 1
fi

echo "==> Module Apache ssl"
if [[ ! -f /etc/apache2/mods-available/ssl.load ]]; then
	export DEBIAN_FRONTEND=noninteractive
	apt-get install -y libapache2-mod-ssl || apt-get install -y apache2
fi

echo "==> Permissions certificats"
bash "$ROOT/scripts/fix-cert-perms.sh"

if [[ ! -r "$CERT_CRT" || ! -r "$CERT_KEY" ]]; then
	echo "Certificats introuvables : $CERT_CRT / $CERT_KEY" >&2
	echo "Générer via FreePBX → Admin → Certificats (Certman), ou :" >&2
	echo "  fwconsole certificates --generate --type self-signed --hostname pbx.local" >&2
	exit 1
fi

echo "==> Vhost SSL"
cp "$ROOT/apache/freepbx-ssl.conf" "/etc/apache2/sites-available/${SSL_SITE}.conf"
a2enmod ssl 2>/dev/null || true
a2ensite "${SSL_SITE}.conf" 2>/dev/null || true

# Éviter conflit avec default-ssl (snakeoil) si présent
a2dissite default-ssl.conf 2>/dev/null || true

echo "==> Alias /provision (conf-enabled)"
a2enconf provision 2>/dev/null || true

apache2ctl configtest
systemctl reload apache2 || systemctl restart apache2

if ss -tlnp | grep -q ':443 '; then
	echo ""
	echo "HTTPS actif sur le port 443."
	echo "  Certificat : $CERT_CRT"
	openssl x509 -in "$CERT_CRT" -noout -subject -dates 2>/dev/null || true
	echo ""
	echo "Test :"
	echo "  curl -sk https://pbx.local/provision/"
	echo "  curl -sk -X POST https://pbx.local/provision/api/v1/register.php \\"
	echo "    -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\"}'"
else
	echo "ERREUR : le port 443 n'écoute pas." >&2
	exit 1
fi
