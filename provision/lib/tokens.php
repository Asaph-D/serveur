<?php
declare(strict_types=1);

function provision_create_token(PDO $db, string $email, string $extension): array {
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
	}
	return true;
}

function provision_send_qr_email(PDO $db, string $email, string $extension): array {
	$tokenData = provision_create_token($db, $email, $extension);
	$qrDir = '/var/lib/provision/qr';
	$qrPath = $qrDir . '/' . $tokenData['jti'] . '.png';
	provision_generate_qr_png($tokenData['qr_content'], $qrPath);
	provision_mail_credentials($email, $extension, $qrPath, $tokenData['claim_url']);
	@unlink($qrPath);

	return $tokenData;
}
