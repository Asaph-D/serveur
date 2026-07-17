<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

/**
 * Inviter des extensions dans une salle ConfBridge (appel en cours ou pré-invite).
 * POST { "room": "6000"|"asaphone-grp-xxx", "extensions": ["1004","1005"], "auto": false }
 * Header X-Provision-Jti + ?ext=
 */
try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}
	if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
		provision_error('Méthode non autorisée', 405);
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

	$body = provision_read_json_body();
	$room = trim((string) ($body['room'] ?? $body['call_uri'] ?? $body['conference'] ?? ''));
	if ($room === '') {
		$room = provision_conf_default_room();
	}

	$auto = (bool) ($body['auto'] ?? false);
	if ($auto || empty($body['extensions'])) {
		$result = provision_conf_invite_group_auto($db, $room, $ext);
	} else {
		$extensions = is_array($body['extensions']) ? $body['extensions'] : [];
		$result = provision_conf_invite_extensions($db, $room, $ext, $extensions, true);
	}

	provision_ok([
		'extension' => $ext,
		'room' => provision_conf_normalize_room($room),
		'invited' => $result['invited'],
		'skipped' => $result['skipped'],
		'errors' => $result['errors'],
		'group_id' => $result['group'] ?? null,
		'hint' => 'Le client reste sur un seul appel SIP vers la salle ; le PBX origine les participants.',
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 400);
}
