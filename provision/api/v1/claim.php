<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$token = trim((string) ($_GET['token'] ?? ''));
	if ($token === '') {
		$body = provision_read_json_body();
		$token = trim((string) ($body['token'] ?? ''));
	}
	if ($token === '') {
		provision_error('Token requis');
	}

	$db = provision_pdo();
	$result = provision_claim_credentials($db, $token);

	provision_ok([
		'credentials' => $result['credentials'],
		'jti' => $result['jti'],
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 404);
}
