<?php
declare(strict_types=1);

function provision_get_request_by_email(PDO $db, string $email): ?array {
	$sth = $db->prepare('SELECT * FROM provision_requests WHERE email = ? LIMIT 1');
	$sth->execute([$email]);
	$row = $sth->fetch();
	return $row ?: null;
}

function provision_upsert_register(PDO $db, string $email, string $codeHash, DateTimeInterface $expires, ?string $phone = null): void {
	$existing = provision_get_request_by_email($db, $email);
	if ($existing && in_array($existing['status'], ['provisioned'], true)) {
		throw new RuntimeException('Cet e-mail est déjà provisionné');
	}

	if ($existing) {
		$sql = 'UPDATE provision_requests
			 SET verify_code_hash = ?, verify_expires = ?, email_verified = 0,
			     status = "pending", updated_at = NOW()';
		$params = [$codeHash, $expires->format('Y-m-d H:i:s')];
		if ($phone !== null) {
			$sql .= ', phone = ?';
			$params[] = $phone;
		}
		$sql .= ' WHERE email = ?';
		$params[] = $email;
		$sth = $db->prepare($sql);
		$sth->execute($params);
		return;
	}

	$sth = $db->prepare(
		'INSERT INTO provision_requests (email, phone, verify_code_hash, verify_expires, status)
		 VALUES (?, ?, ?, ?, "pending")'
	);
	$sth->execute([$email, $phone, $codeHash, $expires->format('Y-m-d H:i:s')]);
}

function provision_mark_verified(PDO $db, string $email, ?string $extension, string $status): void {
	$sth = $db->prepare(
		'UPDATE provision_requests
		 SET email_verified = 1, verify_code_hash = NULL, verify_expires = NULL,
		     extension = ?, status = ?, updated_at = NOW()
		 WHERE email = ?'
	);
	$sth->execute([$extension, $status, $email]);
}

function provision_set_extension(PDO $db, string $email, string $extension, string $status): void {
	$sth = $db->prepare(
		'UPDATE provision_requests
		 SET extension = ?, status = ?, updated_at = NOW()
		 WHERE email = ?'
	);
	$sth->execute([$extension, $status, $email]);
}

function provision_resolve_extension_after_verify(PDO $db, string $email): array {
	$policy = provision_policy();
	$req = provision_get_request_by_email($db, $email);
	if (!$req) {
		throw new RuntimeException('Demande introuvable');
	}

	if ($policy === 'preprovisioned') {
		$ext = provision_find_preprovisioned_extension($db, $email);
		if ($ext === null) {
			$ext = $req['extension'] ?? null;
		}
		if ($ext === null || $ext === '') {
			throw new RuntimeException('Aucune extension pré-provisionnée pour cet e-mail');
		}
		if (!provision_extension_exists($db, $ext)) {
			throw new RuntimeException("Extension $ext inexistante");
		}
		return ['extension' => $ext, 'status' => 'verified', 'send_qr' => true];
	}

	if ($policy === 'admin') {
		return ['extension' => null, 'status' => 'pending_admin', 'send_qr' => false];
	}

	// auto — réutiliser l’extension en attente d’auth pour ce compte (QR déjà envoyé)
	$pending = provision_find_email_pending_extension($db, $email);
	if ($pending !== null && provision_is_extension_available($db, $pending, $email)) {
		return ['extension' => $pending, 'status' => 'verified', 'send_qr' => true];
	}

	$ext = provision_assign_next_extension($db, $email);
	if ($ext === null) {
		throw new RuntimeException('Pool d\'extensions épuisé');
	}
	return ['extension' => $ext, 'status' => 'verified', 'send_qr' => true];
}

function provision_execute_verify(PDO $db, string $email, string $code): array {
	$req = provision_get_request_by_email($db, $email);

	if (!$req || empty($req['verify_code_hash'])) {
		if ($req && in_array($req['status'], ['verified', 'pending_admin'], true) && !empty($req['extension'])) {
			if (provision_has_active_token($db, $email)) {
				throw new RuntimeException(
					'Compte déjà vérifié. Consultez votre boîte mail pour le QR ou relancez une inscription.'
				);
			}
			$tokenData = provision_resend_qr_email($db, $email);
			return [
				'extension' => $req['extension'],
				'status' => $req['status'],
				'send_qr' => true,
				'qr_resent' => true,
				'token' => $tokenData,
			];
		}
		throw new RuntimeException('Demande introuvable ou déjà vérifiée');
	}

	if (!empty($req['verify_expires'])) {
		$exp = new DateTimeImmutable($req['verify_expires']);
		if ($exp < new DateTimeImmutable('now')) {
			throw new RuntimeException('Code expiré');
		}
	}

	if (!provision_verify_code_match($code, $req['verify_code_hash'])) {
		throw new RuntimeException('Code incorrect');
	}

	$resolved = provision_resolve_extension_after_verify($db, $email);

	// Envoyer le QR avant de marquer vérifié (évite état bloqué si l'envoi échoue)
	if ($resolved['send_qr'] && $resolved['extension'] !== null) {
		$tokenData = provision_send_qr_email($db, $email, $resolved['extension']);
		$resolved['token'] = $tokenData;
	}

	provision_mark_verified($db, $email, $resolved['extension'], $resolved['status']);

	return $resolved;
}
