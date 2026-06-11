<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
	}

	$body = array_merge($_POST, provision_read_json_body());
	$email = provision_normalize_email((string) ($body['email'] ?? ''));

	if (!provision_valid_email($email)) {
		provision_error('Adresse e-mail invalide');
	}

	$ip = provision_client_ip();
	$maxRegister = (int) provision_env('PROVISION_RATE_LIMIT_REGISTER', '5');
	$maxVerify = (int) provision_env('PROVISION_RATE_LIMIT_VERIFY', '10');

	provision_rate_limit('register_ip', $ip, $maxRegister);
	provision_rate_limit('register_email', $email, $maxVerify);

	$db = provision_pdo();
	$code = provision_verify_code();
	$hash = provision_hash_code($code);
	$expires = (new DateTimeImmutable('now'))->modify('+' . provision_verify_ttl() . ' seconds');

	provision_upsert_register($db, $email, $hash, $expires);

	$ttlMin = (int) ceil(provision_verify_ttl() / 60);
	provision_mail_verify_code($email, $code, $ttlMin);

	provision_ok([
		'message' => 'Si cette adresse est valide, un code de vérification a été envoyé.',
		'expires_in' => provision_verify_ttl(),
	]);
} catch (Throwable $e) {
	provision_log_error('register', $e);
	$msg = $e->getMessage();
	if (str_contains($msg, 'Trop de tentatives')) {
		provision_error($msg, 429);
	}
	provision_error('Impossible d\'envoyer le code de vérification', 500);
}

function provision_log_error(string $endpoint, Throwable $e): void {
	$dir = '/var/log/provision';
	if (!is_dir($dir)) {
		@mkdir($dir, 0750, true);
	}
	$line = date('c') . " [$endpoint] " . $e->getMessage() . "\n";
	@file_put_contents($dir . '/api.log', $line, FILE_APPEND | LOCK_EX);
}
