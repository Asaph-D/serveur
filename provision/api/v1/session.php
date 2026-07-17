<?php
declare(strict_types=1);

/**
 * Handshake final Asaphone — ouverture session SIP (jti + WSS IP + ICE).
 *
 * Contexte VPN / 4G (recommandé) — token one-shot, sans ext+secret :
 *   GET  /api/v1/session.php?token=<session_token>
 *   POST { "token": "…" }  ou  { "session_token": "…" }
 *
 * Contexte manuel (admin / debug) :
 *   POST { "ext": "1003", "secret": "…" }
 */
require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$body = array_merge($_POST, provision_read_json_body());
	$token = trim((string) ($_GET['token'] ?? $body['token'] ?? $body['session_token'] ?? ''));
	$ext = trim((string) ($body['ext'] ?? $body['extension'] ?? ''));
	$secret = (string) ($body['secret'] ?? $body['password'] ?? '');

	$ip = provision_client_ip();
	$max = (int) provision_env('PROVISION_RATE_LIMIT_VERIFY', '10');

	$db = provision_pdo();

	if ($token !== '') {
		provision_rate_limit('session_token_ip', $ip, $max);
		$session = provision_open_session_from_claim($db, $token);
		provision_ok([
			'message' => 'Session ouverte via token — configurez SIP puis POST /consume',
			'session' => $session,
			'jti' => $session['jti'],
			'credentials' => $session['credentials'],
		]);
	}

	if ($ext === '' || $secret === '') {
		provision_error('token requis (VPN/4G) ou ext+secret (manuel)');
	}

	provision_rate_limit('session_ip', $ip, $max);
	provision_rate_limit('session_ext', $ext, $max);

	$session = provision_open_session($db, $ext, $secret);

	provision_ok([
		'message' => $session['reconnect']
			? 'Session ouverte — reconnexion'
			: 'Session ouverte — première connexion',
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
	if (str_contains($msg, 'Token') || str_contains($msg, 'expiré')) {
		provision_error($msg, 404);
	}
	provision_error($msg, 400);
}
