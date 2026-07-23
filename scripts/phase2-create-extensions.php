#!/usr/bin/env php
<?php
/**
 * Crée les extensions PJSIP 1001-1010 (FreePBX Core::processQuickCreate).
 * Exécuter : sudo php /home/asaph/Documents/serveur/scripts/phase2-create-extensions.php
 */
// freepbx.conf définit $amp_conf et charge bootstrap.php
if (!is_readable('/etc/freepbx.conf')) {
	fwrite(STDERR, "Fichier /etc/freepbx.conf introuvable.\n");
	exit(1);
}
if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Exécuter en root : sudo php ...\n");
	exit(1);
}
include '/etc/freepbx.conf';

$core = \FreePBX::Core();
$secretsPath = '/root/phase2-pjsip-secrets.txt';
$lines = [];
$lines[] = "# Phase 2 — secrets SIP PJSIP (1001-1010) — " . date('c');
$lines[] = "# Conserver ce fichier hors sauvegardes publiques ; chmod 600.";

for ($ext = 1001; $ext <= 1010; $ext++) {
	$secret = bin2hex(random_bytes(16));
	$data = [
		'name'         => "Poste $ext",
		'outboundcid'  => '',
		'secret'       => $secret,
		'max_contacts' => 1,
	];
	$r = $core->processQuickCreate('pjsip', (string) $ext, $data);
	if (empty($r['status'])) {
		fwrite(STDERR, "Echec extension $ext: " . ($r['message'] ?? json_encode($r)) . "\n");
		exit(1);
	}
	$lines[] = "$ext\t$secret";
	echo "OK extension $ext\n";
}

file_put_contents($secretsPath, implode("\n", $lines) . "\n");
chmod($secretsPath, 0600);
chown($secretsPath, 0);
chgrp($secretsPath, 0);
echo "Secrets enregistrés : $secretsPath\n";
