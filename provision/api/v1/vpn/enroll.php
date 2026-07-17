<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * Connexion VPN — sans compte, sans e-mail, sans verify.
 *
 * Mode open (PROVISION_VPN_CONNECT_MODE=open) :
 *   POST api_remote/vpn/enroll  { "device_id": "<uuid app stable>" }
 *   ou POST {}  → device_id généré côté serveur (à persister côté app)
 *   → claim_url → GET vpn/claim → tunnel
 *
 * Pas de register / verify / session_token dans ce flux.
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
	provision_rate_limit('vpn_connect_ip', $ip, 30);

	$db = provision_pdo();
	$mode = provision_env('PROVISION_VPN_CONNECT_MODE', 'open');

	if ($mode === 'open') {
		$deviceId = trim((string) ($body['device_id'] ?? ''));
		$result = provision_vpn_enroll_connect($db, $deviceId);
		provision_ok(array_merge([
			'message' => 'VPN prêt — GET claim_url puis activez le tunnel.',
			'flow' => [
				'step' => 1,
				'next' => 'GET claim_url (api_remote, avant tunnel)',
				'then' => 'Activer WireGuard → accès LAN virtuel',
			],
		], $result));
	}

	// Modes futurs (compte SIP) — désactivés tant que PROVISION_VPN_CONNECT_MODE ≠ open
	provision_error('Connexion VPN par compte désactivée — utiliser enroll avec device_id (mode open)', 501);
} catch (Throwable $e) {
	$msg = $e->getMessage();
	$status = 400;
	if (str_contains($msg, 'Trop de tentatives')) {
		$status = 429;
	} elseif (str_contains($msg, 'déjà actif')) {
		$status = 409;
	}
	provision_error($msg, $status);
}
