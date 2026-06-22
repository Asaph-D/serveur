<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

try {
	if (!provision_vpn_enabled()) {
		provision_error('VPN auto-provisionnement désactivé', 503);
	}

	$body = array_merge($_POST, provision_read_json_body());
	$email = provision_normalize_email((string) ($body['email'] ?? ''));

	if (!provision_valid_email($email)) {
		provision_error('Adresse e-mail invalide');
	}

	$ip = provision_client_ip();
	provision_rate_limit('vpn_register_ip', $ip, (int) provision_env('PROVISION_RATE_LIMIT_REGISTER', '5'));
	provision_rate_limit('vpn_register_email', $email, (int) provision_env('PROVISION_RATE_LIMIT_VERIFY', '10'));

	$db = provision_pdo();
	$code = provision_verify_code();
	$hash = provision_hash_code($code);
	$expires = (new DateTimeImmutable('now'))->modify('+' . provision_verify_ttl() . ' seconds');

	provision_vpn_upsert_register($db, $email, $hash, $expires);

	$ttlMin = (int) ceil(provision_verify_ttl() / 60);
	provision_mail_verify_code($email, $code, $ttlMin);

	provision_ok([
		'message' => 'Si cette adresse est valide, un code de vérification VPN a été envoyé.',
		'expires_in' => provision_verify_ttl(),
	]);
} catch (Throwable $e) {
	provision_vpn_log_error('register', $e);
	$msg = $e->getMessage();
	if (str_contains($msg, 'Trop de tentatives')) {
		provision_error($msg, 429);
	}
	if (str_contains($msg, 'déjà actif')) {
		provision_error($msg, 409);
	}
	provision_error('Impossible d\'envoyer le code VPN', 500);
}

function provision_vpn_log_error(string $endpoint, Throwable $e): void {
	$dir = '/var/log/provision';
	if (!is_dir($dir)) {
		@mkdir($dir, 0750, true);
	}
	$line = date('c') . " [vpn:$endpoint] " . $e->getMessage() . "\n";
	@file_put_contents($dir . '/api.log', $line, FILE_APPEND | LOCK_EX);
}
