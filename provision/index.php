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
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
