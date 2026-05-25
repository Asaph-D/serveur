#!/usr/bin/env php
<?php
/**
 * Active le chiffrement média SDES (SRTP) sur les extensions PJSIP 1001–1010.
 * Cahier Phase 4 — aligné « encryption=yes » / SDES côté endpoint.
 *
 * Exécuter : sudo php scripts/phase4-enable-srtp-extensions.php
 */
if (!is_readable('/etc/freepbx.conf')) {
	fwrite(STDERR, "/etc/freepbx.conf introuvable.\n");
	exit(1);
}
if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Root requis : sudo php ...\n");
	exit(1);
}
include '/etc/freepbx.conf';

$db = \FreePBX::Database();
$sql = "UPDATE sip SET data = 'sdes' WHERE keyword = 'media_encryption' AND id >= '1001' AND id <= '1010'";
$n = $db->exec($sql);
if ($n === false) {
	fwrite(STDERR, "Échec SQL.\n");
	exit(1);
}
echo "Lignes mises à jour (media_encryption=sdes) : $n\n";
passthru('/usr/sbin/fwconsole reload', $code);
exit($code ?: 0);
