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

function provision_is_extension_available(PDO $db, string $extension): bool {
	if (!provision_extension_exists($db, $extension)) {
		return false;
	}

	$sth = $db->prepare(
		"SELECT 1 FROM provision_requests
		 WHERE extension = ? AND status IN ('verified', 'pending_admin', 'provisioned')
		 LIMIT 1"
	);
	$sth->execute([$extension]);
	return !$sth->fetchColumn();
}

function provision_assign_next_extension(PDO $db, string $email): ?string {
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
