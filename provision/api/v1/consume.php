<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$body = array_merge($_POST, provision_read_json_body());
	$jti = trim((string) ($body['jti'] ?? ''));

	if ($jti === '') {
		provision_error('jti requis');
	}

	$db = provision_pdo();
	$ok = provision_consume_token($db, $jti);

	if (!$ok) {
		provision_error('Token introuvable ou déjà consommé', 404);
	}

	provision_ok(['message' => 'Token révoqué']);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 400);
}
