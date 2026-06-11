#!/usr/bin/env php
<?php
/**
 * Génère un QR de test pour une extension (admin).
 *   sudo php provision-generate-qr.php --extension 1007 --email admin@test.com
 */
declare(strict_types=1);

if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Exécuter en root : sudo php ...\n");
	exit(1);
}

require_once dirname(__DIR__) . '/provision/lib/bootstrap.php';

$opts = getopt('', ['extension:', 'email:', 'out:', 'help']);
if (isset($opts['help']) || empty($opts['extension']) || empty($opts['email'])) {
	echo "Usage: sudo php provision-generate-qr.php --extension 1007 --email user@test.com [--out /tmp/qr.png]\n";
	exit(empty($opts['extension']) || empty($opts['email']) ? 1 : 0);
}

$extension = trim((string) $opts['extension']);
$email = provision_normalize_email((string) $opts['email']);
$out = $opts['out'] ?? '/tmp/asaphone-qr-' . $extension . '.png';

$db = provision_pdo();
$tokenData = provision_create_token($db, $email, $extension);
provision_generate_qr_png($tokenData['qr_content'], $out);

echo "QR : $out\n";
echo "Claim URL : {$tokenData['claim_url']}\n";
echo "JTI : {$tokenData['jti']}\n";
