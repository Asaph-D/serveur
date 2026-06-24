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
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
