<?php
declare(strict_types=1);

function provision_uuid(): string {
	$data = random_bytes(16);
	$data[6] = chr((ord($data[6]) & 0x0f) | 0x40);
	$data[8] = chr((ord($data[8]) & 0x3f) | 0x80);
	return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($data), 4));
}

function provision_random_token(int $bytes = 32): string {
	return bin2hex(random_bytes($bytes));
}

function provision_verify_code(): string {
	return str_pad((string) random_int(0, 999999), 6, '0', STR_PAD_LEFT);
}

function provision_hash_code(string $code): string {
	return password_hash($code, PASSWORD_BCRYPT);
}

function provision_verify_code_match(string $code, string $hash): bool {
	return password_verify($code, $hash);
}

function provision_encrypt_payload(array $payload): ?string {
	$keyHex = provision_master_key();
	if ($keyHex === '' || strlen($keyHex) !== 64) {
		return null;
	}
	$key = hex2bin($keyHex);
	$iv = random_bytes(12);
	$plaintext = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
	$tag = '';
	$ciphertext = openssl_encrypt($plaintext, 'aes-256-gcm', $key, OPENSSL_RAW_DATA, $iv, $tag, '', 16);
	if ($ciphertext === false) {
		return null;
	}
	return rtrim(strtr(base64_encode($iv . $tag . $ciphertext), '+/', '-_'), '=');
}

function provision_decrypt_payload(string $encoded): ?array {
	$keyHex = provision_master_key();
	if ($keyHex === '' || strlen($keyHex) !== 64) {
		return null;
	}
	$key = hex2bin($keyHex);
	$pad = strlen($encoded) % 4;
	if ($pad > 0) {
		$encoded .= str_repeat('=', 4 - $pad);
	}
	$raw = base64_decode(strtr($encoded, '-_', '+/'), true);
	if ($raw === false || strlen($raw) < 28) {
		return null;
	}
	$iv = substr($raw, 0, 12);
	$tag = substr($raw, 12, 16);
	$ciphertext = substr($raw, 28);
	$plaintext = openssl_decrypt($ciphertext, 'aes-256-gcm', $key, OPENSSL_RAW_DATA, $iv, $tag);
	if ($plaintext === false) {
		return null;
	}
	$data = json_decode($plaintext, true);
	return is_array($data) ? $data : null;
}

function provision_encrypt_secret(string $secret): ?string {
	return provision_encrypt_payload(['secret' => $secret]);
}

function provision_decrypt_secret(?string $encoded): ?string {
	if ($encoded === null || $encoded === '') {
		return null;
	}
	$data = provision_decrypt_payload($encoded);
	$val = $data['secret'] ?? null;
	return is_string($val) && $val !== '' ? $val : null;
}

function provision_build_claim_url(string $claimToken): string {
	return provision_bootstrap_url() . '/api/v1/claim.php?token=' . rawurlencode($claimToken);
}

function provision_build_qr_content(string $claimToken): string {
	$scheme = provision_env('PROVISION_QR_SCHEME', 'asaphone');
	$claimUrl = provision_build_claim_url($claimToken);
	return $scheme . '://provision?url=' . rawurlencode($claimUrl);
}

function provision_generate_qr_png(string $content, string $outPath): void {
	$tmpIn = tempnam(sys_get_temp_dir(), 'qrin_');
	$tmpOut = tempnam(sys_get_temp_dir(), 'qrout_') . '.png';
	file_put_contents($tmpIn, $content);

	$cmd = sprintf(
		'qrencode -o %s -s 8 -m 2 < %s 2>&1',
		escapeshellarg($tmpOut),
		escapeshellarg($tmpIn)
	);
	exec($cmd, $output, $code);
	@unlink($tmpIn);

	if ($code !== 0 || !is_readable($tmpOut)) {
		@unlink($tmpOut);
		throw new RuntimeException('Génération QR échouée (qrencode): ' . implode("\n", $output));
	}

	if (!rename($tmpOut, $outPath)) {
		@unlink($tmpOut);
		throw new RuntimeException("Impossible d'écrire $outPath");
	}
	chmod($outPath, 0600);
}
