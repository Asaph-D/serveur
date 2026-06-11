<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$email = provision_normalize_email((string) ($_GET['email'] ?? ''));
	if (!provision_valid_email($email)) {
		provision_error('Adresse e-mail invalide');
	}

	$db = provision_pdo();
	$req = provision_get_request_by_email($db, $email);
	if (!$req) {
		provision_ok(['status' => 'unknown', 'email_verified' => false]);
	}

	provision_ok([
		'status' => $req['status'],
		'email_verified' => (bool) $req['email_verified'],
		'extension' => $req['extension'],
		'created_at' => $req['created_at'],
		'updated_at' => $req['updated_at'],
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 400);
}
