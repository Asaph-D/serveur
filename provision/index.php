<?php
declare(strict_types=1);

require_once __DIR__ . '/lib/bootstrap.php';

header('Content-Type: application/json; charset=utf-8');
echo json_encode([
	'service' => 'asaphone-provision',
	'version' => '1.0',
	'enabled' => provision_enabled(),
	'policy' => provision_policy(),
	'base_url' => provision_base_url(),
	'bootstrap_url' => provision_bootstrap_url(),
	'discovery_url' => provision_discovery_url(),
	'public_host' => provision_public_host(),
	'pbx_host' => provision_env('PROVISION_PBX_HOST', 'pbx.local'),
	'pbx_lan_ip' => provision_pbx_lan_ip(),
	'sip_server' => provision_sip_server(),
	'wss_url' => provision_wss_url(),
	'video_codecs' => provision_video_codecs(),
	'ice_servers' => provision_ice_servers(),
	'vpn_connect_mode' => provision_env('PROVISION_VPN_CONNECT_MODE', 'open'),
	'vpn_connect_flow' => provision_env('PROVISION_WG_REMOTE_ENABLE', 'yes') === 'yes'
		? [
			'1_enroll' => 'POST /api/v1/vpn/enroll.php {"device_id":"…"} via api_remote',
			'2_claim' => 'GET /api/v1/vpn/claim.php?token=… via api_remote',
			'3_tunnel' => 'Activer WireGuard avec la config claim',
			'4_lan' => 'Accès 192.168.1.x après tunnel UP',
			'revoke' => 'POST /api/v1/vpn/revoke.php {"device_id":"…"} (ré-enroll après 409)',
		]
		: [
			'remote' => 'Relay WSS intégré (tunnel claim.tunnel) puis WireGuard → 127.0.0.1:51820',
			'lan' => 'Wi-Fi site : accès direct ' . provision_pbx_lan_ip() . ' ou WireGuard endpoint_lan',
			'api' => 'Provision HTTPS via api_remote (Cloudflare)',
		],
	'remote_access' => array_merge([
		'mode' => provision_remote_access_mode(),
		'wireguard_remote' => provision_wg_remote_available(),
	], provision_vpn_tunnel_payload() !== []
		? ['wss_relay' => provision_vpn_tunnel_payload()]
		: []),
	'conference' => provision_conference_payload(),
	'endpoints' => array_merge(provision_api_paths(), [
		'vpn_register' => '/api/v1/vpn/register.php',
		'vpn_verify' => '/api/v1/vpn/verify.php',
		'vpn_claim' => '/api/v1/vpn/claim.php',
	]),
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
