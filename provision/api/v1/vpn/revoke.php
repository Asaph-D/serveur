<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * Révoque le VPN d'un appareil (mode open).
 *
 * POST api_remote/vpn/revoke  { "device_id": "<uuid app stable>" }
 * → retire le peer WireGuard + supprime l'enregistrement (ré-enroll possible).
 */
try {
	if (!provision_vpn_enabled()) {
		provision_error('VPN auto-provisionnement désactivé', 503);
	}

	if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
		provision_error('Méthode non autorisée', 405);
	}

	$body = provision_read_json_body();
	$ip = provision_client_ip();
	provision_rate_limit('vpn_revoke_ip', $ip, 20);

	$db = provision_pdo();
	$mode = provision_env('PROVISION_VPN_CONNECT_MODE', 'open');

	if ($mode !== 'open') {
		provision_error('Révocation VPN par device_id désactivée (mode open requis)', 501);
	}

	$deviceId = trim((string) ($body['device_id'] ?? ''));
	$result = provision_vpn_revoke_connect($db, $deviceId);
	provision_ok(array_merge([
		'message' => 'VPN révoqué — vous pouvez rappeler enroll avec le même device_id.',
	], $result));
} catch (Throwable $e) {
	$msg = $e->getMessage();
	$status = 400;
	if (str_contains($msg, 'Trop de tentatives')) {
		$status = 429;
	} elseif (str_contains($msg, 'introuvable')) {
		$status = 404;
	}
	provision_error($msg, $status);
}
