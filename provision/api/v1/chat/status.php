<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * Poll des accusés sent|delivered|read pour les messages sortants.
 * Auth : jti OU secret SIP.
 * GET  ?ext=1005&ids=1,2&client_ids=m-a,m-b
 * POST body: {"ids":[1,2],"client_ids":["m-a"]}
 */
try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$db = provision_pdo();
	$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
	$body = ($method === 'POST') ? provision_read_json_body() : [];
	$ext = provision_chat_require_ext($db, $body !== [] ? $body : null);

	$ids = [];
	$clientIds = [];
	if ($method === 'POST') {
		$ids = $body['ids'] ?? [];
		$clientIds = $body['client_ids'] ?? [];
		if (!is_array($ids)) {
			provision_error('ids doit être un tableau');
		}
		if (!is_array($clientIds)) {
			provision_error('client_ids doit être un tableau');
		}
	} else {
		if (isset($_GET['ids']) && (string) $_GET['ids'] !== '') {
			$ids = preg_split('/\s*,\s*/', (string) $_GET['ids']) ?: [];
		}
		if (isset($_GET['client_ids']) && (string) $_GET['client_ids'] !== '') {
			$clientIds = preg_split('/\s*,\s*/', (string) $_GET['client_ids']) ?: [];
		}
	}

	$statuses = provision_chat_statuses($db, $ext, $ids, $clientIds);
	provision_ok(['statuses' => $statuses]);
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
