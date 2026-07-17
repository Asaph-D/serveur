#!/usr/bin/env bash
# Permissions FreePBX GUI : évite chown(): Operation not permitted (WriteConfig.class.php).
# Apache = www-data ; Asterisk = asterisk ; fichiers config = www-data:asterisk (groupe partagé).
# Usage : sudo bash scripts/fix-freepbx-dashboard-perms.sh
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

WEB_USER="${FREEPBX_WEB_USER:-www-data}"
WEB_GROUP="${FREEPBX_WEB_GROUP:-asterisk}"
AST_USER="${FREEPBX_AST_USER:-asterisk}"
AST_GROUP="${FREEPBX_AST_GROUP:-asterisk}"

echo "FreePBX GUI perms : web=${WEB_USER}:${WEB_GROUP} ast=${AST_USER}:${AST_GROUP}"

# Groupe partagé (écriture GUI + lecture Asterisk)
if ! getent group "$AST_GROUP" >/dev/null; then
	groupadd "$AST_GROUP"
fi
usermod -aG "$AST_GROUP" "$WEB_USER" 2>/dev/null || true
usermod -aG "$AST_GROUP" "$AST_USER" 2>/dev/null || true
# Groupe asterisk : lecture des clés par le démon (-G asterisk, sans groupes supplémentaires).
usermod -aG asterisk "$WEB_USER" 2>/dev/null || true
usermod -aG asterisk "$AST_USER" 2>/dev/null || true

fix_tree() {
	local path="$1"
	local dirmode="${2:-2775}"
	local filemode="${3:-664}"
	[[ -e "$path" ]] || return 0
	echo "  $path"
	chown -R "${WEB_USER}:${AST_GROUP}" "$path"
	find "$path" -type d -exec chmod "$dirmode" {} +
	find "$path" -type f -exec chmod "$filemode" {} +
}

# Réglages FreePBX (Advanced Settings) — source de WriteConfig chown()
if [[ -r /etc/freepbx.conf ]]; then
	export FREEPBX_WEB_USER FREEPBX_WEB_GROUP FREEPBX_AST_USER FREEPBX_AST_GROUP
	php <<'PHP'
<?php
include '/etc/freepbx.conf';
$db = FreePBX::Database();
$web = getenv('FREEPBX_WEB_USER') ?: 'www-data';
$webg = getenv('FREEPBX_WEB_GROUP') ?: 'asterisk';
$ast = getenv('FREEPBX_AST_USER') ?: 'asterisk';
$astg = getenv('FREEPBX_AST_GROUP') ?: 'asterisk';
$upd = $db->prepare('UPDATE freepbx_settings SET value = ? WHERE keyword = ?');
foreach ([
	['AMPASTERISKWEBUSER', $web],
	['AMPASTERISKWEBGROUP', $webg],
	['AMPASTERISKUSER', $ast],
	['AMPASTERISKGROUP', $astg],
] as [$k, $v]) {
	$upd->execute([$v, $k]);
	echo "  DB $k=$v\n";
}
PHP
fi

echo "Arborescences GUI (écriture www-data) :"
fix_tree /etc/asterisk
fix_tree /var/www/html/admin

# /var/lib/asterisk : binaires fwconsole — NE PAS passer en 664 (casse le démarrage)
if [[ -d /var/lib/asterisk ]]; then
	echo "  /var/lib/asterisk (asterisk:${AST_GROUP}, bin exécutable)"
	chown -R "${AST_USER}:${AST_GROUP}" /var/lib/asterisk
	find /var/lib/asterisk -type d -exec chmod 2775 {} +
	find /var/lib/asterisk -type f -exec chmod 664 {} +
	if [[ -d /var/lib/asterisk/bin ]]; then
		find /var/lib/asterisk/bin -type f ! -type l -exec chmod 755 {} +
	fi
fi

if [[ -d /var/www/cgi-bin ]]; then
	echo "  /var/www/cgi-bin"
	chown -R "${WEB_USER}:${AST_GROUP}" /var/www/cgi-bin
	find /var/www/cgi-bin -type d -exec chmod 2775 {} +
	find /var/www/cgi-bin -type f -exec chmod 775 {} +
fi

# Spool voicemail : doit rester writable par asterisk (lockfiles)
if [[ -d /var/spool/asterisk/voicemail ]]; then
	echo "  /var/spool/asterisk/voicemail (asterisk:${AST_GROUP})"
	chown -R "${AST_USER}:${AST_GROUP}" /var/spool/asterisk/voicemail
	find /var/spool/asterisk/voicemail -type d -exec chmod 2775 {} +
	find /var/spool/asterisk/voicemail -type f -exec chmod 664 {} + 2>/dev/null || true
fi

# /var/run/asterisk : géré par fix-asterisk-run-perms.sh (après fwconsole start).

# Sessions PHP (GUI)
if [[ -d /var/lib/php/sessions ]]; then
	chmod 1733 /var/lib/php/sessions
fi

# Vérif rapide : www-data peut chown vers lui-même après écriture
sudo -u "$WEB_USER" php -r "
\$f = '/etc/asterisk/.perm-test';
file_put_contents(\$f, ';test');
if (!@chown(\$f, '$WEB_USER')) { fwrite(STDERR, 'chown web user FAIL\n'); unlink(\$f); exit(1); }
if (!@chgrp(\$f, '$AST_GROUP')) { fwrite(STDERR, 'chgrp asterisk FAIL\n'); unlink(\$f); exit(1); }
unlink(\$f);
echo '  test WriteConfig OK';
"

echo "Terminé. Rechargez la page Extensions (Ctrl+F5) puis réessayez."
