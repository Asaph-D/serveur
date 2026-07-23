<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * Messages chat en attente (SIP instantané non livré, destinataire offline).
 * Auth : ext + jti (QR/reconnect) OU ext + secret SIP (REGISTER manuel).
 * GET  ?ext=1001 — renvoie puis retire de la file
 * POST {"ack":[1,2,3]} — accusé explicite (optionnel)
 */
try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$db = provision_pdo();
	$body = ($_SERVER['REQUEST_METHOD'] === 'POST') ? provision_read_json_body() : [];
	$ext = provision_chat_require_ext($db, $body !== [] ? $body : null);

	if ($_SERVER['REQUEST_METHOD'] === 'POST') {
		$ack = $body['ack'] ?? [];
		if (!is_array($ack)) {
			provision_error('ack doit être un tableau');
		}
		$ids = array_values(array_filter(array_map('intval', $ack), static fn (int $v): bool => $v > 0));
		provision_ok(['acknowledged' => provision_chat_ack($db, $ext, $ids)]);
	}

	$rows = provision_chat_fetch_pending($db, $ext);
	$messages = [];
	foreach ($rows as $row) {
		$messages[] = [
			'id' => (int) $row['id'],
			'from' => $row['from_ext'],
			'body' => $row['body'],
			'client_id' => $row['client_id'] ?? null,
			'sip_delivered' => (bool) $row['sip_delivered'],
			'created_at' => $row['created_at'],
		];
	}

	provision_ok([
		'extension' => $ext,
		'messages' => $messages,
		'count' => count($messages),
		'statuses' => provision_chat_recent_outbound_statuses($db, $ext),
		'poll_hint' => 'Appeler à chaque reconnexion WSS si le SIP MESSAGE instantané a pu échouer',
	]);
} catch (Throwable $e) {
	$msg = $e->getMessage();
	$code = 403;
	if (str_contains($msg, 'Trop de tentatives')) {
		$code = 429;
	} elseif (str_contains($msg, 'Identifiants invalides')) {
		$code = 401;
	} elseif (str_contains($msg, 'Authentification requise') || str_contains($msg, 'ext requis')) {
		$code = 401;
	}
	provision_error($msg, $code);
}
