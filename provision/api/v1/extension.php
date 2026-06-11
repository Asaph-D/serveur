<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$ext = trim((string) ($_GET['ext'] ?? $_GET['extension'] ?? ''));
	$email = provision_normalize_email((string) ($_GET['email'] ?? ''));
	$forEmail = provision_valid_email($email) ? $email : null;

	$db = provision_pdo();

	if ($ext === '') {
		provision_ok(provision_pool_status($db, $forEmail));
	}

	if (!preg_match('/^\d+$/', $ext)) {
		provision_error('Extension invalide');
	}

	provision_ok(provision_extension_status($db, $ext, $forEmail));
} catch (Throwable $e) {
	provision_error($e->getMessage(), 400);
}
