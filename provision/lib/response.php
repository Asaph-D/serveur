<?php
declare(strict_types=1);

function provision_json(array $data, int $status = 200): void {
	http_response_code($status);
	header('Content-Type: application/json; charset=utf-8');
	header('Cache-Control: no-store');
	echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
	exit;
}

function provision_error(string $message, int $status = 400, array $extra = []): void {
	provision_json(array_merge(['ok' => false, 'error' => $message], $extra), $status);
}

function provision_ok(array $data = []): void {
	provision_json(array_merge(['ok' => true], $data));
}

function provision_read_json_body(): array {
	$raw = file_get_contents('php://input');
	if ($raw === false || trim($raw) === '') {
		return [];
	}
	$data = json_decode($raw, true);
	return is_array($data) ? $data : [];
}

function provision_client_ip(): string {
	foreach (['HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'REMOTE_ADDR'] as $hdr) {
		if (!empty($_SERVER[$hdr])) {
			$ip = trim(explode(',', (string) $_SERVER[$hdr])[0]);
			if (filter_var($ip, FILTER_VALIDATE_IP)) {
				return $ip;
			}
		}
	}
	return '0.0.0.0';
}

function provision_normalize_email(string $email): string {
	return strtolower(trim($email));
}

function provision_normalize_phone(?string $phone): ?string {
	if ($phone === null) {
		return null;
	}
	$p = preg_replace('/[^\d+]/', '', trim($phone));
	return $p !== '' ? $p : null;
}

function provision_valid_email(string $email): bool {
	return (bool) filter_var($email, FILTER_VALIDATE_EMAIL);
}
