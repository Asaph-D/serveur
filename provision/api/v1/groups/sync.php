<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

/**
 * Sync groupes messagerie → salles ConfBridge.
 * POST { "groups": [ { "id", "title", "members": ["1001","1002"] } ] }
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
	$groupsIn = $body['groups'] ?? null;
	if (!is_array($groupsIn)) {
		$single = $body;
		if (!empty($body['id']) || !empty($body['group_id'])) {
			$groupsIn = [$single];
		} else {
			provision_error('groups[] requis');
		}
	}

	$synced = [];
	foreach ($groupsIn as $g) {
		if (!is_array($g)) {
			continue;
		}
		$gid = trim((string) ($g['id'] ?? $g['group_id'] ?? ''));
		$title = trim((string) ($g['title'] ?? $g['name'] ?? ''));
		$members = $g['members'] ?? [];
		if ($gid === '' || !is_array($members)) {
			continue;
		}
		$synced[] = provision_group_upsert($db, $ext, $gid, $title, $members);
	}

	if ($synced === []) {
		provision_error('aucun groupe valide');
	}

	provision_ok([
		'extension' => $ext,
		'groups' => $synced,
		'conference' => provision_conference_payload(),
		'hint' => 'Utiliser call_uri (ou dial) pour lancer l\'appel groupe — le PBX invite les membres.',
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 400);
}
