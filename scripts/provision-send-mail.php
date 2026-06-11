#!/usr/bin/env php
<?php
/**
 * Test envoi SMTP Gmail.
 *   sudo php provision-send-mail.php --to votre@email.com
 */
declare(strict_types=1);

if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Exécuter en root : sudo php ...\n");
	exit(1);
}

require_once dirname(__DIR__) . '/provision/lib/bootstrap.php';

$opts = getopt('', ['to:', 'help']);
if (isset($opts['help']) || empty($opts['to'])) {
	echo "Usage: sudo php provision-send-mail.php --to email@example.com\n";
	exit(empty($opts['to']) ? 1 : 0);
}

$to = provision_normalize_email((string) $opts['to']);
if (!provision_valid_email($to)) {
	fwrite(STDERR, "E-mail invalide\n");
	exit(1);
}

$html = '<p>Test SMTP Asaphone depuis le PBX.</p><p>Si vous lisez ceci, la configuration Gmail fonctionne.</p>';
provision_smtp_send($to, '[Asaphone] Test SMTP PBX', $html);
echo "OK — message envoyé à $to\n";
