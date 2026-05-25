#!/usr/bin/env php
<?php
/**
 * Associe le certificat Certificate Manager « default » (cid=1) au transport PJSIP TLS.
 * Corrige pjsipcertid=0 où cert_file restait vide dans Asterisk.
 *
 * Exécuter : sudo php scripts/phase4-assign-pjsip-tls-cert.php
 */
if (!is_readable('/etc/freepbx.conf')) {
	fwrite(STDERR, "/etc/freepbx.conf introuvable.\n");
	exit(1);
}
if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Root requis.\n");
	exit(1);
}
include '/etc/freepbx.conf';

$db = \FreePBX::Database();
$row = $db->query("SELECT cid FROM certman_certs WHERE basename = 'default' ORDER BY cid LIMIT 1")->fetch(PDO::FETCH_ASSOC);
if (!$row) {
	fwrite(STDERR, "Aucun certificat « default » dans certman_certs.\n");
	exit(1);
}
$cid = (int) $row['cid'];
$db->exec('UPDATE kvstore_Sipsettings SET val=' . $db->quote((string) $cid) . " WHERE `key` = 'pjsipcertid'");
echo "pjsipcertid = $cid (default). Puis : sudo fwconsole reload\n";
passthru('/usr/sbin/fwconsole reload', $code);
exit($code ?: 0);
