<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * À la reconnexion Asaphone : liste les notifications VM non lues (consumed=0).
 * GET  ?ext=1003  + header X-Provision-Jti
 * POST {"ack":[1,2,3]}  — marque comme lues après affichage
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
	if (!provision_vm_validate_jti($db, $jti, $ext)) {
		provision_error('Accès refusé', 403);
	}

	if ($_SERVER['REQUEST_METHOD'] === 'POST') {
		$body = provision_read_json_body();
		$ack = $body['ack'] ?? [];
		if (!is_array($ack)) {
			provision_error('ack doit être un tableau');
		}
		$ids = array_values(array_filter(array_map('intval', $ack), static fn (int $v): bool => $v > 0));
		$count = provision_vm_ack_notifications($db, $ext, $ids);
		provision_ok(['acknowledged' => $count]);
	}

	$pending = provision_vm_list_pending_notifications($db, $ext);
	$inbox = provision_vm_list_inbox($ext);

	provision_ok([
		'extension' => $ext,
		'vm_code' => provision_vm_access_code($ext),
		'pending' => $pending,
		'pending_count' => count($pending),
		'inbox_count' => count($inbox),
		'poll_hint' => 'Appeler ce endpoint à chaque REGISTER / reconnexion WSS',
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 403);
}
