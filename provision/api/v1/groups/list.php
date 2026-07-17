<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

/**
 * Liste des groupes dont l'extension est membre.
 * GET ?ext=1003 + X-Provision-Jti
 */
try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}
	if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
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

	provision_ok([
		'extension' => $ext,
		'groups' => provision_groups_list_for_ext($db, $ext),
		'conference' => provision_conference_payload(),
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 400);
}
