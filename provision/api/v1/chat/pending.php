<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * Messages chat en attente (SIP instantané non livré, destinataire offline).
 * Exclut les messages déjà reçus en live (sip_delivered=1), même si non lus côté app.
 * GET  ?ext=1001 + X-Provision-Jti — renvoie puis retire de la file (pas de re-envoi)
 * POST {"ack":[1,2,3]} — accusé explicite (optionnel)
 */
try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$db = provision_pdo();
	$ext = trim((string) ($_GET['ext'] ?? ''));
	$jti = trim((string) ($_SERVER['HTTP_X_PROVISION_JTI'] ?? $_GET['jti'] ?? ''));
	if ($ext === '' || $jti === '') {
		provision_error('ext et jti requis');
	}
	if (!provision_chat_validate_jti($db, $jti, $ext)) {
		provision_error('Accès refusé', 403);
	}

	if ($_SERVER['REQUEST_METHOD'] === 'POST') {
		$body = provision_read_json_body();
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
			'sip_delivered' => (bool) $row['sip_delivered'],
			'created_at' => $row['created_at'],
		];
	}

	provision_ok([
		'extension' => $ext,
		'messages' => $messages,
		'count' => count($messages),
		'poll_hint' => 'Appeler à chaque reconnexion WSS si le SIP MESSAGE instantané a pu échouer',
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 403);
}
