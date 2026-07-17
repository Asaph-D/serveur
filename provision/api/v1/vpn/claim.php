<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

try {
	if (!provision_vpn_enabled()) {
		provision_error('VPN auto-provisionnement désactivé', 503);
	}

	$token = trim((string) ($_GET['token'] ?? ''));
	if ($token === '') {
		$body = provision_read_json_body();
		$token = trim((string) ($body['token'] ?? ''));
	}
	if ($token === '') {
		provision_error('Token requis');
	}

	$endpoint = trim((string) ($_GET['endpoint'] ?? $_GET['mode'] ?? ''));
	if ($endpoint === 'lan') {
		$useEndpoint = provision_vpn_endpoint_lan();
	} elseif ($endpoint === 'remote' || $endpoint === '') {
		$useEndpoint = provision_vpn_uses_wss_relay()
			? null
			: provision_vpn_endpoint_remote();
	} else {
		$useEndpoint = $endpoint;
	}

	$db = provision_pdo();
	$config = provision_vpn_claim_config($db, $token, $useEndpoint);

	$next = provision_vpn_uses_wss_relay()
		? 'Démarrer relay WSS intégré puis WireGuard (127.0.0.1:51820)'
		: 'Activer vpn.config (WireGuard) — endpoint UDP public';

	provision_ok([
		'vpn' => $config,
		'flow' => [
			'step' => 2,
			'next' => $next,
			'then' => 'Tunnel UP → joindre ' . ($config['pbx_lan_ip'] ?? provision_pbx_lan_ip()),
		],
	]);
} catch (Throwable $e) {
	provision_error($e->getMessage(), 404);
}
