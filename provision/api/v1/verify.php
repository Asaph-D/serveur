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
	$req = provision_get_request_by_email($db, $email);
	if (!$req || empty($req['verify_code_hash'])) {
		provision_error('Demande introuvable ou déjà vérifiée', 404);
	}

	if (!empty($req['verify_expires'])) {
		$exp = new DateTimeImmutable($req['verify_expires']);
		if ($exp < new DateTimeImmutable('now')) {
			provision_error('Code expiré', 410);
		}
	}

	if (!provision_verify_code_match($code, $req['verify_code_hash'])) {
		provision_error('Code incorrect', 401);
	}

	$resolved = provision_resolve_extension_after_verify($db, $email);
	provision_mark_verified($db, $email, $resolved['extension'], $resolved['status']);

	$response = [
		'message' => 'E-mail vérifié',
		'status' => $resolved['status'],
		'policy' => provision_policy(),
	];

	if ($resolved['send_qr'] && $resolved['extension'] !== null) {
		$tokenData = provision_send_qr_email($db, $email, $resolved['extension']);
		$response['message'] = 'E-mail vérifié. Vos identifiants ont été envoyés.';
		$response['extension'] = $resolved['extension'];
		$response['qr_sent'] = true;
		$response['expires'] = $tokenData['expires'];
	} elseif ($resolved['status'] === 'pending_admin') {
		$response['message'] = 'E-mail vérifié. Un administrateur validera votre extension.';
		$response['qr_sent'] = false;
	}

	provision_ok($response);
} catch (Throwable $e) {
	provision_log_error('verify', $e);
	provision_error($e->getMessage(), 400);
}

function provision_log_error(string $endpoint, Throwable $e): void {
	$dir = '/var/log/provision';
	if (!is_dir($dir)) {
		@mkdir($dir, 0750, true);
	}
	$line = date('c') . " [$endpoint] " . $e->getMessage() . "\n";
	@file_put_contents($dir . '/api.log', $line, FILE_APPEND | LOCK_EX);
}
