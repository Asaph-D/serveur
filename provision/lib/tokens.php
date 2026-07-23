<?php
declare(strict_types=1);

function provision_revoke_tokens_for_email(PDO $db, string $email): void {
	$db->prepare(
		'UPDATE provision_tokens SET used = 1, used_at = NOW() WHERE used = 0 AND email = ?'
	)->execute([$email]);
}

function provision_revoke_tokens_for_extension_except(PDO $db, string $extension, string $keepEmail): void {
	$db->prepare(
		'UPDATE provision_tokens SET used = 1, used_at = NOW()
		 WHERE used = 0 AND extension = ? AND email != ?'
	)->execute([$extension, $keepEmail]);
}

function provision_validate_token_claim(PDO $db, array $token): void {
	$req = provision_get_request_by_email($db, $token['email']);
	if (!$req || empty($req['extension'])) {
		throw new RuntimeException('Token révoqué');
	}
	if ((string) $req['extension'] !== (string) $token['extension']) {
		throw new RuntimeException('Token révoqué');
	}
	if (!in_array($req['status'], ['verified', 'pending_admin', 'provisioned'], true)) {
		throw new RuntimeException('Token révoqué');
	}
}

function provision_create_token(PDO $db, string $email, string $extension): array {
	provision_revoke_tokens_for_email($db, $email);
	provision_revoke_tokens_for_extension_except($db, $extension, $email);

	$jti = provision_uuid();
	$claimToken = provision_random_token(24);
	$expires = (new DateTimeImmutable('now'))->modify('+' . provision_qr_ttl() . ' seconds');

	$payload = provision_credentials_payload($db, $extension, $jti);
	$payloadEnc = provision_encrypt_payload($payload);

	$sth = $db->prepare(
		'INSERT INTO provision_tokens (jti, extension, email, claim_token, payload_enc, expires)
		 VALUES (?, ?, ?, ?, ?, ?)'
	);
	$sth->execute([
		$jti,
		$extension,
		$email,
		$claimToken,
		$payloadEnc,
		$expires->format('Y-m-d H:i:s'),
	]);

	return [
		'jti' => $jti,
		'claim_token' => $claimToken,
		'claim_url' => provision_build_claim_url($claimToken),
		'qr_content' => provision_build_qr_content($claimToken),
		'expires' => $expires->format(DateTimeInterface::ATOM),
	];
}

function provision_get_token_by_claim(PDO $db, string $claimToken): ?array {
	$sth = $db->prepare('SELECT * FROM provision_tokens WHERE claim_token = ? LIMIT 1');
	$sth->execute([$claimToken]);
	$row = $sth->fetch();
	return $row ?: null;
}

function provision_get_token_by_jti(PDO $db, string $jti): ?array {
	$sth = $db->prepare('SELECT * FROM provision_tokens WHERE jti = ? LIMIT 1');
	$sth->execute([$jti]);
	$row = $sth->fetch();
	return $row ?: null;
}

function provision_token_valid(array $token): bool {
	if ((int) $token['used'] === 1) {
		return false;
	}
	$expires = new DateTimeImmutable($token['expires']);
	return $expires > new DateTimeImmutable('now');
}

function provision_claim_credentials(PDO $db, string $claimToken): array {
	$token = provision_get_token_by_claim($db, $claimToken);
	if (!$token) {
		throw new RuntimeException('Token invalide');
	}
	if (!provision_token_valid($token)) {
		throw new RuntimeException('Token expiré ou déjà utilisé');
	}
	provision_validate_token_claim($db, $token);

	$credentials = provision_credentials_payload($db, $token['extension'], $token['jti']);

	return [
		'jti' => $token['jti'],
		'credentials' => $credentials,
	];
}

function provision_consume_token(PDO $db, string $jti): bool {
	$sth = $db->prepare(
		'UPDATE provision_tokens
		 SET used = 1, used_at = NOW()
		 WHERE jti = ? AND used = 0'
	);
	$sth->execute([$jti]);
	if ($sth->rowCount() === 0) {
		return false;
	}

	$token = provision_get_token_by_jti($db, $jti);
	if ($token) {
		$upd = $db->prepare(
			'UPDATE provision_requests SET status = "provisioned", updated_at = NOW() WHERE email = ?'
		);
		$upd->execute([$token['email']]);
		provision_revoke_tokens_for_extension_except($db, (string) $token['extension'], (string) $token['email']);
	}
	return true;
}

function provision_has_active_token(PDO $db, string $email): bool {
	$sth = $db->prepare(
		'SELECT 1 FROM provision_tokens
		 WHERE email = ? AND used = 0 AND expires > NOW() LIMIT 1'
	);
	$sth->execute([$email]);
	return (bool) $sth->fetchColumn();
}

function provision_send_qr_email(PDO $db, string $email, string $extension): array {
	provision_init_voicemail_mailbox($extension, $email);
	require_once __DIR__ . '/pjsip-align.php';
	provision_ensure_pjsip_profile($extension);
	$tokenData = provision_create_token($db, $email, $extension);
	$qrPath = tempnam(sys_get_temp_dir(), 'asaphone_qr_') . '.png';
	try {
		provision_generate_qr_png($tokenData['qr_content'], $qrPath);
		provision_mail_credentials($email, $extension, $qrPath, $tokenData['claim_url']);
	} finally {
		@unlink($qrPath);
	}

	return $tokenData;
}

function provision_resend_qr_email(PDO $db, string $email): array {
	$req = provision_get_request_by_email($db, $email);
	if (!$req || empty($req['extension'])) {
		throw new RuntimeException('Aucune extension attribuée pour cet e-mail');
	}
	if (!in_array($req['status'], ['verified', 'pending_admin'], true)) {
		throw new RuntimeException('Compte non éligible au renvoi du QR');
	}
	return provision_send_qr_email($db, $email, (string) $req['extension']);
}

function provision_get_active_token(PDO $db, string $email, string $extension): ?array {
	$sth = $db->prepare(
		'SELECT * FROM provision_tokens
		 WHERE email = ? AND extension = ? AND used = 0 AND expires > NOW()
		 ORDER BY id DESC LIMIT 1'
	);
	$sth->execute([$email, $extension]);
	$row = $sth->fetch();
	return $row ?: null;
}

function provision_verify_extension_secret(PDO $db, string $extension, string $secret): void {
	if (!preg_match('/^\d{4}$/', $extension)) {
		throw new RuntimeException('Identifiants invalides');
	}
	if (!provision_extension_exists($db, $extension)) {
		throw new RuntimeException('Identifiants invalides');
	}
	$stored = provision_get_extension_secret($db, $extension);
	if ($stored === null || $stored === '' || !hash_equals($stored, $secret)) {
		throw new RuntimeException('Identifiants invalides');
	}
}

function provision_resolve_email_for_extension(PDO $db, string $extension): ?string {
	$owner = provision_get_extension_owner($db, $extension);
	if ($owner && !empty($owner['email'])) {
		return (string) $owner['email'];
	}
	$holder = provision_get_extension_holder($db, $extension);
	if ($holder && !empty($holder['email'])
		&& in_array($holder['status'], ['verified', 'pending_admin', 'provisioned'], true)) {
		return (string) $holder['email'];
	}
	return null;
}

/**
 * Redélivre le contenu du QR (jti + credentials) sans rescanner.
 * - Première fois : jeton actif existant ou nouveau (comme claim).
 * - Reconnexion (déjà provisioned) : nouveau jti consommé pour chat / messagerie.
 */
function provision_redeliver_session(PDO $db, string $extension, string $secret): array {
	provision_verify_extension_secret($db, $extension, $secret);

	$email = provision_resolve_email_for_extension($db, $extension);
	if ($email === null) {
		throw new RuntimeException('Extension non liée à un compte Asaphone — inscrivez-vous par e-mail');
	}

	$alreadyProvisioned = provision_get_extension_owner($db, $extension) !== null;

	if ($alreadyProvisioned) {
		$tokenData = provision_create_token($db, $email, $extension);
		provision_consume_token($db, $tokenData['jti']);
		$credentials = provision_credentials_payload($db, $extension, $tokenData['jti']);
		return [
			'reconnect' => true,
			'jti' => $tokenData['jti'],
			'credentials' => $credentials,
			'expires' => $tokenData['expires'],
		];
	}

	$active = provision_get_active_token($db, $email, $extension);
	if ($active !== null) {
		provision_validate_token_claim($db, $active);
		$credentials = provision_credentials_payload($db, $extension, $active['jti']);
		return [
			'reconnect' => false,
			'jti' => $active['jti'],
			'credentials' => $credentials,
			'claim_token' => $active['claim_token'],
			'claim_url' => provision_build_claim_url($active['claim_token']),
			'expires' => (new DateTimeImmutable($active['expires']))->format(DateTimeInterface::ATOM),
		];
	}

	$tokenData = provision_create_token($db, $email, $extension);
	$credentials = provision_credentials_payload($db, $extension, $tokenData['jti']);
	return [
		'reconnect' => false,
		'jti' => $tokenData['jti'],
		'credentials' => $credentials,
		'claim_token' => $tokenData['claim_token'],
		'claim_url' => $tokenData['claim_url'],
		'expires' => $tokenData['expires'],
	];
}
