<?php
declare(strict_types=1);

require_once dirname(__DIR__, 2) . '/lib/bootstrap.php';

try {
	if (!provision_enabled()) {
		provision_error('Provisionnement désactivé', 503);
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

	$ip = provision_client_ip();
	$maxVerify = (int) provision_env('PROVISION_RATE_LIMIT_VERIFY', '10');
	provision_rate_limit('verify_ip', $ip, $maxVerify);

	$db = provision_pdo();
	$resolved = provision_execute_verify($db, $email, $code);

	$response = [
		'message' => 'E-mail vérifié',
		'status' => $resolved['status'],
		'policy' => provision_policy(),
	];

	if (!empty($resolved['qr_resent'])) {
		$response['message'] = 'Vos identifiants ont été renvoyés par e-mail.';
		$response['extension'] = $resolved['extension'];
		$response['qr_sent'] = true;
		$response['qr_resent'] = true;
		$response['expires'] = $resolved['token']['expires'] ?? null;
	} elseif ($resolved['send_qr'] && $resolved['extension'] !== null) {
		$response['message'] = 'E-mail vérifié. Vos identifiants ont été envoyés.';
		$response['extension'] = $resolved['extension'];
		$response['qr_sent'] = true;
		$response['expires'] = $resolved['token']['expires'] ?? null;
	} elseif ($resolved['status'] === 'pending_admin') {
		$response['message'] = 'E-mail vérifié. Un administrateur validera votre extension.';
		$response['qr_sent'] = false;
	}

	provision_ok($response);
} catch (Throwable $e) {
	provision_log_error('verify', $e);
	$msg = $e->getMessage();
	$code = 400;
	if ($msg === 'Code incorrect') {
		$code = 401;
	} elseif ($msg === 'Code expiré') {
		$code = 410;
	} elseif (str_contains($msg, 'introuvable') || str_contains($msg, 'déjà vérifiée')) {
		$code = 404;
	}
	provision_error($msg, $code);
}

function provision_log_error(string $endpoint, Throwable $e): void {
	$dir = '/var/log/provision';
	if (!is_dir($dir)) {
		@mkdir($dir, 0750, true);
	}
	$line = date('c') . " [$endpoint] " . $e->getMessage() . "\n";
	@file_put_contents($dir . '/api.log', $line, FILE_APPEND | LOCK_EX);
}
