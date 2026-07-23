<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * Enregistre un message sortant pour les accusés (sent / delivered / read).
 * Auth : jti OU secret SIP (REGISTER manuel).
 * POST /provision/api/v1/chat/outbound.php?ext=1005
 * Body: {"body":"…","client_id":"m-…","to":"1003","at_ms":1732…}
 * Headers optionnels : X-Provision-Jti | X-Provision-Secret
 */
try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}
	if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
		provision_error('Méthode non autorisée', 405);
	}

	$db = provision_pdo();
	$body = provision_read_json_body();
	$ext = provision_chat_require_ext($db, $body);

	$text = trim((string) ($body['body'] ?? ''));
	$clientId = trim((string) ($body['client_id'] ?? ''));
	$to = trim((string) ($body['to'] ?? ''));
	$atMs = isset($body['at_ms']) ? (int) $body['at_ms'] : null;
	if ($text === '' || $clientId === '' || $to === '') {
		provision_error('body, client_id et to requis');
	}
	if (!empty($body['is_group'])) {
		provision_error('is_group non supporté sur outbound pour l’instant', 501);
	}

	$id = provision_chat_outbound($db, $ext, $to, $text, $clientId, $atMs);
	provision_ok(['id' => $id]);
} catch (Throwable $e) {
	$msg = $e->getMessage();
	$code = 400;
	if (str_contains($msg, 'Trop de tentatives')) {
		$code = 429;
	} elseif (str_contains($msg, 'Identifiants invalides') || str_contains($msg, 'Authentification')) {
		$code = 401;
	}
	provision_error($msg, $code);
}
