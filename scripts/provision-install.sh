#!/usr/bin/env bash
# Installe la mini-API provisionnement Asaphone sur le PBX.
# Usage : sudo bash provision-install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS="/etc/provision/provision-secrets.env"
LEGACY_SECRETS="/root/provision-secrets.env"
MASTER_KEY="/root/provision-master.key"
WWW="/var/www/provision"
ETC="/etc/provision"
LOG="/var/log/provision"
LIB="/var/lib/provision"

if [[ "$(id -u)" -ne 0 ]]; then
	echo "Exécuter en root : sudo bash $0" >&2
	exit 1
fi

echo "==> Paquets (qrencode, PHP)"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y qrencode php-cli php-mysql php-json 2>/dev/null || {
	apt-get install -y qrencode php-cli php-mysql php-json
}

echo "==> Répertoires"
mkdir -p "$WWW" "$ETC" "$LOG" "$LIB/qr"
chown www-data:www-data "$LIB" "$LIB/qr" 2>/dev/null || true
chmod 775 "$LIB" "$LIB/qr"
chmod 750 "$LOG"
chown www-data:www-data "$LOG" 2>/dev/null || true

echo "==> Secrets SMTP"
if [[ ! -f "$SECRETS" ]]; then
	if [[ -f "$LEGACY_SECRETS" ]]; then
		cp "$LEGACY_SECRETS" "$SECRETS"
	elif [[ -f "$ROOT/network/provision.secrets.env" ]]; then
		cp "$ROOT/network/provision.secrets.env" "$SECRETS"
	else
		cp "$ROOT/network/provision.secrets.env.example" "$SECRETS"
		echo "ATTENTION : éditez $SECRETS avec vos identifiants Gmail" >&2
	fi
fi
chown root:www-data "$SECRETS"
chmod 640 "$SECRETS"

echo "==> Clé maître provisionnement"
if [[ ! -f "$MASTER_KEY" ]]; then
	openssl rand -hex 32 > "$MASTER_KEY"
	chmod 600 "$MASTER_KEY"
fi

echo "==> Config provision.env"
cp "$ROOT/network/provision.env" "$ETC/provision.env"
chown root:www-data "$ETC/provision.env"
chmod 640 "$ETC/provision.env"

echo "==> Déploiement /var/www/provision"
rsync -a --delete \
	--exclude='*.swp' \
	"$ROOT/provision/" "$WWW/"
chown -R www-data:www-data "$WWW"
find "$WWW" -type f -name '*.php' -exec chmod 640 {} \;
find "$WWW" -type d -exec chmod 750 {} \;

echo "==> Schéma MariaDB"
if [[ -r /etc/freepbx.conf ]]; then
	readarray -t _db < <(php -r '
		include "/etc/freepbx.conf";
		echo ($amp_conf["AMPDBHOST"] ?? "localhost") . "\n";
		echo ($amp_conf["AMPDBUSER"] ?? "asteriskuser") . "\n";
		echo ($amp_conf["AMPDBPASS"] ?? "") . "\n";
		echo ($amp_conf["AMPDBNAME"] ?? "asterisk") . "\n";
	')
	DB_HOST="${_db[0]}"
	DB_USER="${_db[1]}"
	DB_PASS="${_db[2]}"
	DB_NAME="${_db[3]}"
	mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$ROOT/scripts/provision-schema.sql"
	mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$ROOT/scripts/provision-schema-voicemail.sql" 2>/dev/null || {
		mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$ROOT/scripts/provision-schema-voicemail.sql" || true
	}
	mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$ROOT/scripts/provision-schema-chat.sql" 2>/dev/null || true
else
	mysql asterisk < "$ROOT/scripts/provision-schema.sql"
fi

echo "==> Apache alias /provision"
APACHE_SNIP="/etc/apache2/conf-available/provision.conf"
cat > "$APACHE_SNIP" <<'APACHE'
# Mini-API provisionnement Asaphone
Alias /provision /var/www/provision

<Directory /var/www/provision>
    Options -Indexes +FollowSymLinks
    AllowOverride None
    Require all granted
    <FilesMatch "\.php$">
        SetHandler application/x-httpd-php
    </FilesMatch>
</Directory>
APACHE

a2enconf provision 2>/dev/null || true

if command -v apache2ctl >/dev/null 2>&1; then
	apache2ctl configtest
	systemctl reload apache2 || systemctl restart apache2
fi

echo "==> HTTPS (port 443)"
bash "$ROOT/scripts/enable-apache-https.sh"

echo "==> Wrapper externnotify messagerie"
install -m 0755 "$ROOT/scripts/asaphone-vm-notify.sh" /usr/local/bin/asaphone-vm-notify
install -m 0755 "$ROOT/scripts/asaphone-vm-originate.sh" /usr/local/bin/asaphone-vm-originate
install -m 0755 "$ROOT/scripts/asaphone-chat-ingest.sh" /usr/local/bin/asaphone-chat-ingest
install -m 0440 "$ROOT/scripts/asaphone-chat-ingest.sudoers" /etc/sudoers.d/asaphone-chat-ingest
visudo -c -f /etc/sudoers.d/asaphone-chat-ingest
install -m 0440 "$ROOT/scripts/asaphone-vm-notify.sudoers" /etc/sudoers.d/asaphone-vm-notify
visudo -c -f /etc/sudoers.d/asaphone-vm-notify

echo "==> Scripts CLI exécutables"
chmod +x "$ROOT/scripts/provision-assign-ext.php"
chmod +x "$ROOT/scripts/provision-send-mail.php"
chmod +x "$ROOT/scripts/provision-generate-qr.php"
chmod +x "$WWW/bin/vm-notify.php" 2>/dev/null || true
chmod +x "$WWW/bin/chat-ingest.php" 2>/dev/null || true

echo ""
echo "Installation terminée."
echo "  Config     : $ETC/provision.env"
echo "  Secrets    : $SECRETS (chmod 600)"
echo "  API        : $(grep PROVISION_BASE_URL "$ROOT/network/provision.env" | cut -d= -f2- | tr -d '\"')"
echo ""
echo "Tests :"
echo "  sudo php $ROOT/scripts/provision-send-mail.php --to VOTRE_EMAIL"
echo "  curl -sk -X POST https://pbx.local/provision/api/v1/register.php -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\"}'"
echo ""
echo "Admin (policy=admin) :"
echo "  sudo php $ROOT/scripts/provision-assign-ext.php --list-pending"
echo "  sudo php $ROOT/scripts/provision-assign-ext.php --approve user@mail.com --extension 1007"
