<?php
declare(strict_types=1);

/**
 * Onboarding VPN autonome (e-mail + code) — hors flux connexion Asaphone.
 * L’app utilise : register/verify SIP → session_token → vpn/enroll → vpn/claim.
 */
require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

try {
	if (!provision_vpn_enabled()) {
		provision_error('VPN auto-provisionnement désactivé', 503);
	}

	$body = array_merge($_POST, provision_read_json_body());
	$email = provision_normalize_email((string) ($body['email'] ?? ''));
	$code = trim((string) ($body['code'] ?? ''));

	if (!provision_valid_email($email)) {
		provision_error('Adresse e-mail invalide');
	}
	if (!preg_match('/^\d{6}$/', $code)) {
		provision_error('Code invalide');
	}

	provision_rate_limit('vpn_verify_ip', provision_client_ip(), (int) provision_env('PROVISION_RATE_LIMIT_VERIFY', '10'));

	$db = provision_pdo();
	$result = provision_vpn_execute_verify($db, $email, $code);

	if (empty($result['resent'])) {
		provision_mail_vpn_claim($email, $result['claim_url'], (string) $result['tunnel_ip']);
	}

	$response = [
		'message' => empty($result['resent'])
			? 'VPN prêt. Configuration envoyée par e-mail.'
			: 'Lien VPN encore valide renvoyé.',
		'tunnel_ip' => $result['tunnel_ip'],
		'claim_url' => $result['claim_url'],
		'deeplink' => $result['deeplink'],
		'expires' => $result['expires'],
	];

	if (!empty($result['resent'])) {
		$response['resent'] = true;
	}

	$sessionLinks = provision_issue_session_links_for_email($db, $email);
	$response = array_merge($response, provision_session_links_payload($sessionLinks));

	provision_ok($response);
} catch (Throwable $e) {
	provision_vpn_log_error('verify', $e);
	$msg = $e->getMessage();
	$status = 400;
	if ($msg === 'Code incorrect') {
		$status = 401;
	} elseif ($msg === 'Code expiré') {
		$status = 410;
	} elseif (str_contains($msg, 'introuvable')) {
		$status = 404;
	}
	provision_error($msg, $status);
}

function provision_vpn_log_error(string $endpoint, Throwable $e): void {
	$dir = '/var/log/provision';
	if (!is_dir($dir)) {
		@mkdir($dir, 0750, true);
	}
	$line = date('c') . " [vpn:$endpoint] " . $e->getMessage() . "\n";
	@file_put_contents($dir . '/api.log', $line, FILE_APPEND | LOCK_EX);
}
