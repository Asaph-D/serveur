#!/usr/bin/env php
<?php
/**
 * Attribution / validation admin d'une extension puis envoi QR.
 *
 * Pré-provisionnement :
 *   sudo php provision-assign-ext.php --email user@example.com --extension 1007
 *
 * Validation admin (après verify) :
 *   sudo php provision-assign-ext.php --approve user@example.com --extension 1007
 *
 * Liste en attente :
 *   sudo php provision-assign-ext.php --list-pending
 *
 * Vérifier une extension (libre / associée) :
 *   sudo php provision-assign-ext.php --check 1007
 *   sudo php provision-assign-ext.php --pool
 */
declare(strict_types=1);

if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Exécuter en root : sudo php ...\n");
	exit(1);
}

require_once dirname(__DIR__) . '/provision/lib/bootstrap.php';

$opts = getopt('', ['email:', 'extension:', 'approve:', 'list-pending', 'check:', 'pool', 'help']);

if (isset($opts['help'])) {
	echo "Usage:\n";
	echo "  --list-pending\n";
	echo "  --pool                          (état du pool onboarding)\n";
	echo "  --check EXT                     (extension libre / associée ?)\n";
	echo "  --approve EMAIL --extension EXT\n";
	echo "  --email EMAIL --extension EXT   (pré-provisionnement)\n";
	exit(0);
}

$db = provision_pdo();

if (isset($opts['pool'])) {
	$pool = provision_pool_status($db);
	printf("Pool : %d extensions, %d libres, %d authentifiées\n", $pool['total'], $pool['free_count'], $pool['taken_count']);
	foreach ($pool['pool'] as $st) {
		printf(
			"  %s  free=%s  taken=%s  owner=%s  pending=%s  reason=%s\n",
			$st['extension'],
			$st['free'] ? 'yes' : 'no',
			$st['taken'] ? 'yes' : 'no',
			$st['associated_email'] ?? '-',
			$st['pending_email'] ?? '-',
			$st['reason']
		);
	}
	exit(0);
}

if (isset($opts['check'])) {
	$ext = trim((string) $opts['check']);
	echo json_encode(provision_extension_status($db, $ext), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n";
	exit(0);
}

if (isset($opts['list-pending'])) {
	$sth = $db->query(
		"SELECT email, status, extension, created_at FROM provision_requests
		 WHERE status IN ('pending_admin', 'pending')
		 ORDER BY created_at ASC"
	);
	foreach ($sth->fetchAll() as $row) {
		printf(
			"%s\t%s\text=%s\t%s\n",
			$row['email'],
			$row['status'],
			$row['extension'] ?? '-',
			$row['created_at']
		);
	}
	exit(0);
}

$email = provision_normalize_email((string) ($opts['approve'] ?? $opts['email'] ?? ''));
$extension = trim((string) ($opts['extension'] ?? ''));

if (!provision_valid_email($email)) {
	fwrite(STDERR, "E-mail invalide\n");
	exit(1);
}
if ($extension === '' || !preg_match('/^\d+$/', $extension)) {
	fwrite(STDERR, "Extension invalide\n");
	exit(1);
}

if (!provision_extension_exists($db, $extension)) {
	fwrite(STDERR, "Extension $extension inexistante dans FreePBX\n");
	exit(1);
}

$req = provision_get_request_by_email($db, $email);

if (isset($opts['approve'])) {
	if (!$req || $req['status'] !== 'pending_admin') {
		fwrite(STDERR, "Aucune demande en attente admin pour $email\n");
		exit(1);
	}
	if (!provision_is_extension_available($db, $extension)) {
		fwrite(STDERR, "Extension $extension déjà attribuée\n");
		exit(1);
	}
	provision_set_extension($db, $email, $extension, 'verified');
	$tokenData = provision_send_qr_email($db, $email, $extension);
	echo "QR envoyé à $email (extension $extension, jti={$tokenData['jti']})\n";
	exit(0);
}

// pré-provisionnement
if ($req) {
	provision_set_extension($db, $email, $extension, 'pending');
} else {
	$sth = $db->prepare(
		'INSERT INTO provision_requests (email, extension, status) VALUES (?, ?, "pending")'
	);
	$sth->execute([$email, $extension]);
}
echo "Pré-provisionné : $email → extension $extension\n";
