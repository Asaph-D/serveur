<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * Accusés de lecture chat Asaphone.
 * POST /provision/api/v1/chat/read.php?ext=1003&jti=<uuid>
 * Header: X-Provision-Jti: <uuid>
 * Body: {"read":[4,5,6],"peer":"1004"}
 */
try {
	if (!provision_enabled()) {
		provision_chat_read_error('Provisionnement désactivé', 503);
	}

	if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
		provision_chat_read_error('Méthode non autorisée', 405);
	}

	$db = provision_pdo();
	$ext = trim((string) ($_GET['ext'] ?? ''));
	$jti = trim((string) ($_SERVER['HTTP_X_PROVISION_JTI'] ?? $_GET['jti'] ?? ''));
	if ($ext === '' || $jti === '') {
		provision_chat_read_error('ext et jti requis');
	}
	if (!provision_chat_validate_jti($db, $jti, $ext)) {
		provision_chat_read_error('Accès refusé', 403);
	}

	$body = provision_read_json_body();
	$read = $body['read'] ?? [];
	if (!is_array($read)) {
		provision_chat_read_error('read doit être un tableau');
	}

	$ids = array_values(array_filter(array_map('intval', $read), static fn (int $v): bool => $v > 0));
	$peer = trim((string) ($body['peer'] ?? ''));
	if ($peer !== '' && !preg_match('/^\d{4,5}$/', $peer)) {
		provision_chat_read_error('peer invalide');
	}

	if ($ids === [] && $peer === '') {
		provision_chat_read_error('read ou peer requis');
	}

	if ($ids !== []) {
		provision_chat_mark_read($db, $ext, $ids);
	}
	if ($peer !== '') {
		provision_chat_notify_peer_read($ext, $peer);
	}

	provision_ok();
} catch (Throwable $e) {
	provision_chat_read_error($e->getMessage(), 400);
}

function provision_chat_read_error(string $message, int $status = 400): void {
	http_response_code($status);
	header('Content-Type: application/json; charset=utf-8');
	header('Cache-Control: no-store');
	echo json_encode(['ok' => false, 'message' => $message], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
	exit;
}
