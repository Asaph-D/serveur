<?php
declare(strict_types=1);

function provision_repo_root(): string {
	return dirname(__DIR__, 2);
}

function provision_load_env_file(string $path): array {
	if (!is_readable($path)) {
		return [];
	}
	$out = [];
	foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
		$line = trim($line);
		if ($line === '' || $line[0] === '#') {
			continue;
		}
		if (!str_contains($line, '=')) {
			continue;
		}
		[$k, $v] = explode('=', $line, 2);
		$out[trim($k)] = trim($v, " \t\"'");
	}
	return $out;
}

function provision_config(): array {
	static $cfg = null;
	if ($cfg !== null) {
		return $cfg;
	}

	$repo = provision_repo_root();
	$envPath = is_readable('/etc/provision/provision.env')
		? '/etc/provision/provision.env'
		: $repo . '/network/provision.env';

	$base = provision_load_env_file($envPath);
	$secretsPath = $base['PROVISION_SECRETS_FILE'] ?? '/root/provision-secrets.env';
	$secrets = provision_load_env_file($secretsPath);

	$cfg = array_merge($base, $secrets);
	return $cfg;
}

function provision_env(string $key, string $default = ''): string {
	$cfg = provision_config();
	return $cfg[$key] ?? $default;
}

function provision_enabled(): bool {
	return provision_env('PROVISION_ENABLE', 'yes') === 'yes'
		&& provision_env('EMAIL_ENABLED', 'false') === 'true';
}

function provision_base_url(): string {
	return rtrim(provision_env('PROVISION_BASE_URL', 'https://pbx.local/provision'), '/');
}

function provision_verify_ttl(): int {
	return (int) provision_env('PROVISION_VERIFY_TTL', '900');
}

function provision_qr_ttl(): int {
	return (int) provision_env('PROVISION_QR_TTL', '86400');
}

function provision_policy(): string {
	return provision_env('PROVISION_POLICY', 'admin');
}

function provision_ext_pool(): array {
	$raw = provision_env('PROVISION_EXT_POOL', '1003 1004 1005 1006 1007 1008 1009 1010');
	$parts = preg_split('/\s+/', trim($raw)) ?: [];
	return array_values(array_filter($parts, static function (string $v): bool {
		return $v !== '';
	}));
}

function provision_codecs(): array {
	$raw = provision_env('PROVISION_CODECS', 'g722,ulaw,alaw');
	$out = [];
	foreach (explode(',', $raw) as $c) {
		$c = trim($c);
		if ($c !== '') {
			$out[] = $c;
		}
	}
	return $out;
}

function provision_master_key(): string {
	$path = provision_env('PROVISION_MASTER_KEY_FILE', '/root/provision-master.key');
	if (is_readable($path)) {
		return trim((string) file_get_contents($path));
	}
	$key = provision_env('PROVISION_MASTER_KEY', '');
	return $key;
}
