<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$db = provision_pdo();
	$auth = provision_vm_auth_from_request($db);
	$ext = $auth['extension'];
	$messages = provision_vm_list_inbox($ext);
	$token = $auth['token'];
	$baseListen = provision_base_url() . '/api/v1/voicemail/listen.php';

	$outMessages = [];
	foreach ($messages as $msg) {
		$item = [
			'id' => $msg['id'],
			'caller_id' => $msg['caller_id'],
			'duration' => $msg['duration'],
		];
		if ($token !== null) {
			$item['listen_url'] = $baseListen . '?t=' . rawurlencode($token) . '&msg=' . rawurlencode($msg['id']);
		} else {
			$jti = trim((string) ($_SERVER['HTTP_X_PROVISION_JTI'] ?? $_GET['jti'] ?? ''));
			$item['listen_url'] = $baseListen . '?ext=' . rawurlencode($ext)
				. '&jti=' . rawurlencode($jti) . '&msg=' . rawurlencode($msg['id']);
		}
		$outMessages[] = $item;
	}

	provision_ok([
		'extension' => $ext,
		'vm_code' => provision_vm_access_code($ext),
		'deeplink_scheme' => provision_env('PROVISION_QR_SCHEME', 'asaphone') . '://voicemail',
		'messages' => $outMessages,
		'count' => count($outMessages),
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 403);
}
