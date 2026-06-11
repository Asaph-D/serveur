<?php
declare(strict_types=1);

function provision_load_pjsip_secrets_file(): array {
	$path = provision_env('PROVISION_PJSIP_SECRETS', '/root/phase2-pjsip-secrets.txt');
	if (!is_readable($path)) {
		return [];
	}
	$out = [];
	foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
		$line = trim($line);
		if ($line === '' || $line[0] === '#') {
			continue;
		}
		$parts = preg_split('/\s+/', $line, 2);
		if (count($parts) === 2) {
			$out[$parts[0]] = $parts[1];
		}
	}
	return $out;
}

function provision_get_extension_secret(PDO $db, string $extension): ?string {
	$fromFile = provision_load_pjsip_secrets_file();
	if (isset($fromFile[$extension])) {
		return $fromFile[$extension];
	}

	$queries = [
		['SELECT data FROM pjsip WHERE id = ? AND keyword = ? LIMIT 1', [$extension, 'secret']],
		['SELECT data FROM pjsip WHERE id = ? AND keyword = ? LIMIT 1', ['auth' . $extension, 'password']],
		['SELECT data FROM sip WHERE id = ? AND keyword = ? LIMIT 1', [$extension, 'secret']],
	];

	foreach ($queries as [$sql, $params]) {
		try {
			$sth = $db->prepare($sql);
			$sth->execute($params);
			$val = $sth->fetchColumn();
			if (is_string($val) && $val !== '') {
				return $val;
			}
		} catch (Throwable $e) {
			// table absente selon version FreePBX
		}
	}

	return null;
}

function provision_extension_exists(PDO $db, string $extension): bool {
	$sth = $db->prepare('SELECT 1 FROM users WHERE extension = ? LIMIT 1');
	$sth->execute([$extension]);
	return (bool) $sth->fetchColumn();
}

/** Extension garantie : authentification SIP confirmée (consume → provisioned). */
function provision_get_extension_owner(PDO $db, string $extension): ?array {
	$sth = $db->prepare(
		"SELECT email, status, email_verified, updated_at FROM provision_requests
		 WHERE extension = ? AND extension IS NOT NULL AND extension != ''
		 AND status = 'provisioned'
		 LIMIT 1"
	);
	$sth->execute([$extension]);
	$row = $sth->fetch();
	return $row ?: null;
}

/** QR envoyé mais pas encore authentifié — n'empêche pas la réattribution du pool. */
function provision_get_extension_pending(PDO $db, string $extension): ?array {
	$sth = $db->prepare(
		"SELECT email, status, email_verified, updated_at FROM provision_requests
		 WHERE extension = ? AND extension IS NOT NULL AND extension != ''
		 AND status IN ('verified', 'pending_admin')
		 ORDER BY updated_at DESC LIMIT 1"
	);
	$sth->execute([$extension]);
	$row = $sth->fetch();
	return $row ?: null;
}

function provision_find_email_pending_extension(PDO $db, string $email): ?string {
	$sth = $db->prepare(
		"SELECT extension FROM provision_requests
		 WHERE email = ? AND extension IS NOT NULL AND extension != ''
		 AND status IN ('verified', 'pending_admin')
		 LIMIT 1"
	);
	$sth->execute([$email]);
	$ext = $sth->fetchColumn();
	return is_string($ext) && $ext !== '' ? $ext : null;
}

function provision_is_extension_available(PDO $db, string $extension): bool {
	if (!provision_extension_exists($db, $extension)) {
		return false;
	}

	return provision_get_extension_owner($db, $extension) === null;
}

function provision_extension_status(PDO $db, string $extension, ?string $forEmail = null): array {
	$inPool = in_array($extension, provision_ext_pool(), true);
	$exists = provision_extension_exists($db, $extension);
	$owner = provision_get_extension_owner($db, $extension);
	$pending = provision_get_extension_pending($db, $extension);

	$free = $exists && $inPool && $owner === null;
	$available = false;
	$reason = 'unknown';

	if (!$exists) {
		$reason = 'not_in_freepbx';
	} elseif (!$inPool) {
		$reason = 'outside_pool';
	} elseif ($owner === null) {
		$available = true;
		$reason = 'free';
	} elseif ($forEmail !== null && $owner['email'] === $forEmail) {
		$available = false;
		$reason = 'authenticated_as_you';
	} else {
		$available = false;
		$reason = 'authenticated';
	}

	return [
		'extension' => $extension,
		'exists' => $exists,
		'in_pool' => $inPool,
		'free' => $free,
		'available' => $available,
		'taken' => $owner !== null,
		'associated_email' => $owner['email'] ?? null,
		'associated_status' => $owner['status'] ?? null,
		'pending_email' => $pending['email'] ?? null,
		'pending_status' => $pending['status'] ?? null,
		'reason' => $reason,
	];
}

function provision_pool_status(PDO $db, ?string $forEmail = null): array {
	$items = [];
	$freeCount = 0;
	$takenCount = 0;
	foreach (provision_ext_pool() as $ext) {
		$st = provision_extension_status($db, $ext, $forEmail);
		$items[] = $st;
		if ($st['free']) {
			$freeCount++;
		}
		if ($st['taken']) {
			$takenCount++;
		}
	}

	return [
		'pool' => $items,
		'total' => count($items),
		'free_count' => $freeCount,
		'taken_count' => $takenCount,
	];
}

function provision_assign_next_extension(PDO $db): ?string {
	foreach (provision_ext_pool() as $ext) {
		if (provision_is_extension_available($db, $ext)) {
			return $ext;
		}
	}
	return null;
}

function provision_find_preprovisioned_extension(PDO $db, string $email): ?string {
	$sth = $db->prepare(
		"SELECT extension FROM provision_requests
		 WHERE email = ? AND extension IS NOT NULL AND extension != ''
		 AND status IN ('pending', 'verified', 'pending_admin')
		 LIMIT 1"
	);
	$sth->execute([$email]);
	$ext = $sth->fetchColumn();
	return is_string($ext) && $ext !== '' ? $ext : null;
}

function provision_credentials_payload(PDO $db, string $extension, string $jti): array {
	$secret = provision_get_extension_secret($db, $extension);
	if ($secret === null) {
		throw new RuntimeException("Secret SIP introuvable pour l'extension $extension");
	}

	$now = time();
	return [
		'ext' => $extension,
		'server' => provision_env('PROVISION_PBX_HOST', 'pbx.local'),
		'transport' => provision_env('PROVISION_TRANSPORT', 'wss'),
		'port' => (int) provision_env('PROVISION_WSS_PORT', '8089'),
		'secret' => $secret,
		'codecs' => provision_codecs(),
		'webrtc' => true,
		'iat' => $now,
		'exp' => $now + provision_qr_ttl(),
		'jti' => $jti,
	];
}
