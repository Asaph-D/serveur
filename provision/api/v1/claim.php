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
	$session = provision_open_session_from_claim($db, $token);

	provision_ok([
		'message' => 'Identifiants récupérés — configurez SIP puis POST /consume avec le jti',
		'session' => $session,
		'jti' => $session['jti'],
		'credentials' => $session['credentials'],
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 404);
}
