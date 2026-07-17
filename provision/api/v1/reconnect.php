<?php
declare(strict_types=1);

/**
 * Reconnexion Asaphone — ext + secret → jti + credentials (sans rescan QR).
 * Réponse identique à session.php (alias historique).
 */
require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$body = array_merge($_POST, provision_read_json_body());
	$ext = trim((string) ($body['ext'] ?? $body['extension'] ?? ''));
	$secret = (string) ($body['secret'] ?? $body['password'] ?? '');

	if ($ext === '' || $secret === '') {
		provision_error('ext et secret (mot de passe SIP) requis');
	}

	$ip = provision_client_ip();
	$max = (int) provision_env('PROVISION_RATE_LIMIT_VERIFY', '10');
	provision_rate_limit('reconnect_ip', $ip, $max);
	provision_rate_limit('reconnect_ext', $ext, $max);

	$db = provision_pdo();
	$session = provision_open_session($db, $ext, $secret);

	provision_ok([
		'message' => $session['reconnect']
			? 'Reconnexion — identifiants redélivrés'
			: 'Première connexion — identifiants redélivrés',
		'session' => $session,
		'reconnect' => $session['reconnect'],
		'jti' => $session['jti'],
		'credentials' => $session['credentials'],
		'expires' => $session['expires'],
	]);
} catch (Throwable $e) {
	$msg = $e->getMessage();
	if (str_contains($msg, 'Trop de tentatives')) {
		provision_error($msg, 429);
	}
	if ($msg === 'Identifiants invalides') {
		provision_error($msg, 401);
	}
	provision_error($msg, 400);
}
