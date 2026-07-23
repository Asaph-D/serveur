<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * Accusés de lecture chat Asaphone.
 * Auth : jti OU secret SIP (REGISTER manuel).
 * POST ?ext=1003
 * Body: {"read":[4,5,6],"peer":"1004","client_ids":["m-…"]}
 */
try {
	if (!provision_enabled()) {
		provision_chat_read_error('Provisionnement désactivé', 503);
	}

	if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
		provision_chat_read_error('Méthode non autorisée', 405);
	}

	$db = provision_pdo();
	$body = provision_read_json_body();
	$ext = provision_chat_require_ext($db, $body);

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

	$clientIds = $body['client_ids'] ?? [];
	if (!is_array($clientIds)) {
		provision_chat_read_error('client_ids doit être un tableau');
	}
	$clientIds = array_values(array_filter(array_map(
		static fn ($v): string => trim((string) $v),
		$clientIds
	), static fn (string $v): bool => $v !== ''));

	$marked = 0;
	if ($ids !== []) {
		$marked = provision_chat_mark_read($db, $ext, $ids);
		provision_chat_notify_senders_read($db, $ext, $ids, $clientIds);
	} elseif ($peer !== '' && $clientIds !== []) {
		// peer + client_ids sans ids serveur
		provision_chat_notify_peer_read($ext, $peer, [], $clientIds);
	}

	provision_ok(['marked' => $marked]);
} catch (Throwable $e) {
	$msg = $e->getMessage();
	$code = 400;
	if (str_contains($msg, 'Trop de tentatives')) {
		$code = 429;
	} elseif (str_contains($msg, 'Identifiants invalides') || str_contains($msg, 'Authentification')) {
		$code = 401;
	}
	provision_chat_read_error($msg, $code);
}

function provision_chat_read_error(string $message, int $status = 400): void {
	http_response_code($status);
	header('Content-Type: application/json; charset=utf-8');
	header('Cache-Control: no-store');
	echo json_encode(['ok' => false, 'message' => $message], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
	exit;
}
