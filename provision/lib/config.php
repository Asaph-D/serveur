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
	$globalPath = is_readable('/etc/provision/global-config.env')
		? '/etc/provision/global-config.env'
		: $repo . '/network/global-config.env';
	$envPath = is_readable('/etc/provision/provision.env')
		? '/etc/provision/provision.env'
		: $repo . '/network/provision.env';

	$global = provision_load_env_file($globalPath);
	$base = provision_load_env_file($envPath);
	$secretsPath = $base['PROVISION_SECRETS_FILE'] ?? '/root/provision-secrets.env';
	$secrets = provision_load_env_file($secretsPath);
	$relay = provision_load_env_file('/etc/provision/wg-relay.env');
	$relayTunnel = provision_load_env_file('/etc/provision/wg-relay-tunnel.env');

	$cfg = array_merge($global, $base, $secrets, $relay, $relayTunnel);
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

function provision_pbx_lan_ip(): string {
	$ip = trim(provision_env('PBX_LAN_IP', ''));
	if ($ip !== '') {
		return $ip;
	}
	return trim(provision_env('PROVISION_VPN_LAN_IP', ''));
}

/** Serveur SIP/WSS : IP DHCP LAN (joignable après VPN ou sur le même réseau). */
function provision_sip_server(): string {
	$ip = provision_pbx_lan_ip();
	if ($ip !== '') {
		return $ip;
	}
	return provision_env('PROVISION_PBX_HOST', 'pbx.local');
}

function provision_wss_url(): string {
	$port = provision_env('PROVISION_WSS_PORT', '8089');
	return 'wss://' . provision_sip_server() . ':' . $port . '/ws';
}

function provision_remote_access_mode(): string {
	return provision_env('PROVISION_REMOTE_ACCESS_MODE', 'auto');
}

function provision_wg_remote_available(): bool {
	return provision_env('PROVISION_WG_REMOTE_ENABLE', 'yes') === 'yes';
}

function provision_vpn_relay_path_prefix(): string {
	return trim(provision_env('PROVISION_WG_RELAY_PATH_PREFIX', ''));
}

/** WebSocket public pour relayer UDP WireGuard (tunnel Cloudflare dédié → wstunnel). */
function provision_vpn_tunnel_wss_url(): string {
	$wss = trim(provision_env('PROVISION_WG_RELAY_WSS_URL', ''));
	if ($wss !== '') {
		return $wss;
	}
	$pub = provision_public_base_url();
	if (!preg_match('#^https?://([^/]+)#', $pub, $m)) {
		return '';
	}
	$scheme = str_starts_with($pub, 'https') ? 'wss' : 'ws';
	return $scheme . '://' . $m[1] . '/wg-relay';
}

function provision_vpn_uses_wss_relay(): bool {
	return provision_remote_access_mode() === 'wss-relay' && !provision_wg_remote_available();
}

function provision_vpn_tunnel_payload(): array {
	if (!provision_vpn_uses_wss_relay()) {
		return [];
	}
	$wss = provision_vpn_tunnel_wss_url();
	if ($wss === '') {
		return [];
	}
	$localPort = (int) provision_env('PROVISION_VPN_PORT', '51820');
	if ($localPort <= 0) {
		$localPort = 51820;
	}
	return [
		'mode' => 'wss-udp-relay',
		'wss_url' => $wss,
		'path_prefix' => provision_vpn_relay_path_prefix(),
		'wireguard_endpoint' => '127.0.0.1:' . $localPort,
		'hint' => 'Démarrer le relay WSS intégré puis WireGuard vers 127.0.0.1 (Asaphone uniquement)',
	];
}

function provision_base_url(): string {
	return rtrim(provision_env('PROVISION_BASE_URL', 'https://pbx.local/provision'), '/');
}

/** URL discovery statique (GitHub Pages) — joignable avant tout contact PBX. */
function provision_discovery_url(): string {
	return trim(provision_env('PROVISION_DISCOVERY_URL', ''));
}

/** API HTTPS joignable depuis Internet (claim / QR / enroll avant tunnel VPN). */
function provision_public_base_url(): string {
	$pub = trim(provision_env('PROVISION_PUBLIC_BASE_URL', ''));
	if ($pub !== '') {
		return rtrim($pub, '/');
	}
	$host = trim(provision_env('PROVISION_PUBLIC_HOST', ''));
	if ($host !== '') {
		return 'https://' . $host . '/provision';
	}
	return provision_base_url();
}

function provision_public_host(): string {
	$host = trim(provision_env('PROVISION_PUBLIC_HOST', ''));
	if ($host !== '') {
		return $host;
	}
	$url = provision_public_base_url();
	if (preg_match('#^https?://([^/:]+)#', $url, $m)) {
		return $m[1];
	}
	return '';
}

/** Liens one-shot envoyés aux apps distantes (toujours via IP/domaine public). */
function provision_bootstrap_url(): string {
	return provision_public_base_url();
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
	$raw = provision_env('PROVISION_CODECS', 'opus,g722,ulaw,alaw');
	$out = [];
	foreach (explode(',', $raw) as $c) {
		$c = trim($c);
		if ($c !== '') {
			$out[] = $c;
		}
	}
	return $out;
}

function provision_video_codecs(): array {
	$raw = provision_env('PROVISION_VIDEO_CODECS', 'vp8,h264');
	$out = [];
	foreach (explode(',', $raw) as $c) {
		$c = trim($c);
		if ($c !== '') {
			$out[] = $c;
		}
	}
	return $out;
}

function provision_turn_enabled(): bool {
	return provision_env('PROVISION_TURN_ENABLE', 'yes') === 'yes';
}

function provision_turn_port(): int {
	return (int) provision_env('PROVISION_TURN_PORT', '3478');
}

/** Secret coturn (use-auth-secret) — provision-secrets.env */
function provision_turn_secret(): string {
	return trim(provision_env('PROVISION_TURN_SECRET', ''));
}

/** Credentials TURN éphémères (RFC coturn REST) pour RTCPeerConnection. */
function provision_turn_credentials(): array {
	$secret = provision_turn_secret();
	if ($secret === '') {
		return [];
	}
	$ttl = (int) provision_env('PROVISION_TURN_TTL', '86400');
	$expiry = (string) (time() + $ttl);
	$credential = base64_encode(hash_hmac('sha1', $expiry, $secret, true));
	return ['username' => $expiry, 'credential' => $credential, 'ttl' => $ttl];
}

/** Serveurs ICE pour clients WebRTC (STUN toujours ; TURN si coturn actif). */
function provision_ice_servers(): array {
	$ip = provision_pbx_lan_ip();
	if ($ip === '') {
		return [];
	}
	$port = provision_turn_port();
	$servers = [
		['urls' => ["stun:{$ip}:{$port}"]],
	];
	if (!provision_turn_enabled() || provision_turn_secret() === '') {
		return $servers;
	}
	$turn = provision_turn_credentials();
	if ($turn === []) {
		return $servers;
	}
	$servers[] = [
		'urls' => [
			"turn:{$ip}:{$port}?transport=udp",
			"turn:{$ip}:{$port}?transport=tcp",
		],
		'username' => $turn['username'],
		'credential' => $turn['credential'],
	];
	return $servers;
}

function provision_master_key(): string {
	$path = provision_env('PROVISION_MASTER_KEY_FILE', '/root/provision-master.key');
	if (is_readable($path)) {
		return trim((string) file_get_contents($path));
	}
	$key = provision_env('PROVISION_MASTER_KEY', '');
	return $key;
}
