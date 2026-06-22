<?php
declare(strict_types=1);

function provision_vpn_enabled(): bool {
	return provision_enabled()
		&& provision_env('PROVISION_VPN_ENABLE', 'yes') === 'yes';
}

function provision_vpn_server_public_key(): string {
	$file = provision_env('PROVISION_VPN_SERVER_PUBKEY_FILE', '/etc/wireguard/server.pub');
	if (is_readable($file)) {
		$key = trim((string) file_get_contents($file));
		if ($key !== '') {
			return $key;
		}
	}
	$out = [];
	$code = 0;
	exec('sudo -n /usr/local/bin/asaphone-vpn-peer server-pubkey 2>&1', $out, $code);
	if ($code !== 0) {
		throw new RuntimeException('Clé publique WireGuard serveur introuvable');
	}
	$key = trim(implode("\n", $out));
	if ($key === '') {
		throw new RuntimeException('Clé publique WireGuard vide');
	}
	return $key;
}

function provision_vpn_allowed_ips(): string {
	return provision_env(
		'PROVISION_VPN_ALLOWED_IPS',
		'192.168.137.0/24,10.10.10.0/24,10.200.0.0/24'
	);
}

function provision_vpn_endpoint_remote(): string {
	return provision_env('PROVISION_VPN_PUBLIC_ENDPOINT', '102.244.125.13:51820');
}

function provision_vpn_endpoint_lan(): string {
	$host = provision_env('PROVISION_PBX_HOST', 'pbx.local');
	$lanIp = provision_env('PROVISION_VPN_LAN_IP', '192.168.137.240');
	$port = provision_env('PROVISION_VPN_PORT', '51820');
	if (provision_env('PROVISION_VPN_LAN_ENDPOINT', '') !== '') {
		return provision_env('PROVISION_VPN_LAN_ENDPOINT');
	}
	return $lanIp . ':' . $port;
}

function provision_vpn_claim_ttl(): int {
	return (int) provision_env('PROVISION_VPN_CLAIM_TTL', '86400');
}

function provision_vpn_generate_keypair(): array {
	$priv = trim((string) shell_exec('wg genkey 2>/dev/null'));
	if ($priv === '') {
		throw new RuntimeException('wg genkey indisponible');
	}
	$pub = trim((string) shell_exec('echo ' . escapeshellarg($priv) . ' | wg pubkey 2>/dev/null'));
	if ($pub === '') {
		throw new RuntimeException('wg pubkey indisponible');
	}
	return ['private' => $priv, 'public' => $pub];
}

function provision_vpn_get_peer_by_email(PDO $db, string $email): ?array {
	$sth = $db->prepare('SELECT * FROM provision_vpn_peers WHERE email = ? LIMIT 1');
	$sth->execute([$email]);
	$row = $sth->fetch();
	return $row ?: null;
}

function provision_vpn_get_peer_by_claim(PDO $db, string $claimToken): ?array {
	$sth = $db->prepare('SELECT * FROM provision_vpn_peers WHERE claim_token = ? LIMIT 1');
	$sth->execute([$claimToken]);
	$row = $sth->fetch();
	return $row ?: null;
}

function provision_vpn_allocate_tunnel_ip(PDO $db): string {
	$start = (int) provision_env('PROVISION_VPN_POOL_START', '10');
	$end = (int) provision_env('PROVISION_VPN_POOL_END', '254');
	$prefix = provision_env('PROVISION_VPN_TUNNEL_PREFIX', '10.200.0');

	for ($host = $start; $host <= $end; $host++) {
		$ip = $prefix . '.' . $host;
		$sth = $db->prepare('SELECT 1 FROM provision_vpn_peers WHERE tunnel_ip = ? LIMIT 1');
		$sth->execute([$ip]);
		if (!$sth->fetchColumn()) {
			return $ip;
		}
	}
	throw new RuntimeException('Pool VPN épuisé');
}

function provision_vpn_upsert_register(PDO $db, string $email, string $codeHash, DateTimeInterface $expires): void {
	$existing = provision_vpn_get_peer_by_email($db, $email);
	if ($existing && $existing['status'] === 'active') {
		throw new RuntimeException('VPN déjà actif pour cet e-mail');
	}

	if ($existing) {
		$sth = $db->prepare(
			'UPDATE provision_vpn_peers
			 SET verify_code_hash = ?, verify_expires = ?, status = "pending",
			     claim_token = NULL, claim_expires = NULL, updated_at = NOW()
			 WHERE email = ?'
		);
		$sth->execute([$codeHash, $expires->format('Y-m-d H:i:s'), $email]);
		return;
	}

	$ip = provision_vpn_allocate_tunnel_ip($db);
	$sth = $db->prepare(
		'INSERT INTO provision_vpn_peers
		 (email, tunnel_ip, client_public_key, verify_code_hash, verify_expires, status)
		 VALUES (?, ?, NULL, ?, ?, "pending")'
	);
	$sth->execute([$email, $ip, $codeHash, $expires->format('Y-m-d H:i:s')]);
}

function provision_vpn_apply_peer(string $publicKey, string $tunnelIp): void {
	$cmd = sprintf(
		'sudo -n /usr/local/bin/asaphone-vpn-peer add %s %s 2>&1',
		escapeshellarg($publicKey),
		escapeshellarg($tunnelIp)
	);
	exec($cmd, $out, $code);
	if ($code !== 0) {
		throw new RuntimeException('Application peer WireGuard échouée: ' . implode("\n", $out));
	}
}

function provision_vpn_build_client_conf(string $privateKey, string $tunnelIp, ?string $endpoint = null): string {
	$endpoint ??= provision_vpn_endpoint_remote();
	$serverPub = provision_vpn_server_public_key();
	$allowed = provision_vpn_allowed_ips();
	$dns = provision_env('PROVISION_VPN_DNS', '192.168.137.1');

	return implode("\n", [
		'[Interface]',
		'PrivateKey = ' . $privateKey,
		'Address = ' . $tunnelIp . '/32',
		'DNS = ' . $dns,
		'',
		'[Peer]',
		'PublicKey = ' . $serverPub,
		'Endpoint = ' . $endpoint,
		'AllowedIPs = ' . $allowed,
		'PersistentKeepalive = 25',
		'',
	]);
}

function provision_vpn_build_claim_url(string $claimToken): string {
	return provision_base_url() . '/api/v1/vpn/claim.php?token=' . rawurlencode($claimToken);
}

function provision_vpn_build_deeplink(string $claimToken): string {
	$scheme = provision_env('PROVISION_QR_SCHEME', 'asaphone');
	$url = provision_vpn_build_claim_url($claimToken);
	return $scheme . '://vpn?url=' . rawurlencode($url);
}

function provision_vpn_config_payload(array $peer, string $privateKey, ?string $endpoint = null): array {
	$endpointRemote = provision_vpn_endpoint_remote();
	$endpointLan = provision_vpn_endpoint_lan();
	$useEndpoint = $endpoint ?? $endpointRemote;
	$conf = provision_vpn_build_client_conf($privateKey, (string) $peer['tunnel_ip'], $useEndpoint);

	return [
		'tunnel_ip' => $peer['tunnel_ip'],
		'email' => $peer['email'],
		'extension' => $peer['extension'],
		'endpoint_remote' => $endpointRemote,
		'endpoint_lan' => $endpointLan,
		'endpoint' => $useEndpoint,
		'allowed_ips' => provision_vpn_allowed_ips(),
		'dns' => provision_env('PROVISION_VPN_DNS', '192.168.137.1'),
		'server_public_key' => provision_vpn_server_public_key(),
		'config' => $conf,
		'interface' => [
			'private_key' => $privateKey,
			'address' => $peer['tunnel_ip'] . '/32',
			'dns' => provision_env('PROVISION_VPN_DNS', '192.168.137.1'),
		],
		'peer' => [
			'public_key' => provision_vpn_server_public_key(),
			'endpoint' => $useEndpoint,
			'allowed_ips' => provision_vpn_allowed_ips(),
			'persistent_keepalive' => 25,
		],
	];
}

function provision_vpn_issue_peer(PDO $db, string $email, ?string $extension = null): array {
	$peer = provision_vpn_get_peer_by_email($db, $email);
	if (!$peer) {
		throw new RuntimeException('Demande VPN introuvable');
	}
	if ($peer['status'] === 'active' && empty($peer['claim_token'])) {
		throw new RuntimeException('VPN déjà actif — révoquer avant réémission');
	}

	$keys = provision_vpn_generate_keypair();
	$privEnc = provision_encrypt_secret($keys['private']);
	if ($privEnc === null) {
		throw new RuntimeException('Chiffrement clé VPN échoué');
	}

	provision_vpn_apply_peer($keys['public'], (string) $peer['tunnel_ip']);

	$claimToken = provision_random_token(24);
	$expires = (new DateTimeImmutable('now'))->modify('+' . provision_vpn_claim_ttl() . ' seconds');

	$sth = $db->prepare(
		'UPDATE provision_vpn_peers
		 SET client_public_key = ?, client_private_key_enc = ?, claim_token = ?, claim_expires = ?,
		     extension = COALESCE(?, extension), status = "ready", verify_code_hash = NULL,
		     verify_expires = NULL, updated_at = NOW()
		 WHERE email = ?'
	);
	$sth->execute([
		$keys['public'],
		$privEnc,
		$claimToken,
		$expires->format('Y-m-d H:i:s'),
		$extension,
		$email,
	]);

	$peer = provision_vpn_get_peer_by_email($db, $email);
	if (!$peer) {
		throw new RuntimeException('Peer VPN introuvable après émission');
	}

	return [
		'claim_token' => $claimToken,
		'claim_url' => provision_vpn_build_claim_url($claimToken),
		'deeplink' => provision_vpn_build_deeplink($claimToken),
		'tunnel_ip' => $peer['tunnel_ip'],
		'expires' => $expires->format(DateTimeInterface::ATOM),
	];
}

function provision_vpn_execute_verify(PDO $db, string $email, string $code): array {
	$peer = provision_vpn_get_peer_by_email($db, $email);
	if (!$peer || empty($peer['verify_code_hash'])) {
		if ($peer && $peer['status'] === 'ready' && !empty($peer['claim_token'])) {
			$exp = new DateTimeImmutable($peer['claim_expires']);
			if ($exp > new DateTimeImmutable('now')) {
				return [
					'claim_token' => $peer['claim_token'],
					'claim_url' => provision_vpn_build_claim_url($peer['claim_token']),
					'deeplink' => provision_vpn_build_deeplink($peer['claim_token']),
					'tunnel_ip' => $peer['tunnel_ip'],
					'expires' => $exp->format(DateTimeInterface::ATOM),
					'resent' => true,
				];
			}
		}
		throw new RuntimeException('Demande VPN introuvable ou déjà vérifiée');
	}

	if (!empty($peer['verify_expires'])) {
		$exp = new DateTimeImmutable($peer['verify_expires']);
		if ($exp < new DateTimeImmutable('now')) {
			throw new RuntimeException('Code expiré');
		}
	}

	if (!provision_verify_code_match($code, $peer['verify_code_hash'])) {
		throw new RuntimeException('Code incorrect');
	}

	$req = provision_get_request_by_email($db, $email);
	$extension = is_array($req) ? ($req['extension'] ?? null) : null;

	return provision_vpn_issue_peer($db, $email, is_string($extension) ? $extension : null);
}

function provision_vpn_claim_config(PDO $db, string $claimToken, ?string $endpoint = null): array {
	$peer = provision_vpn_get_peer_by_claim($db, $claimToken);
	if (!$peer) {
		throw new RuntimeException('Token VPN invalide');
	}
	if (!in_array($peer['status'], ['ready', 'active'], true)) {
		throw new RuntimeException('Token VPN invalide');
	}
	if (!empty($peer['claim_expires'])) {
		$exp = new DateTimeImmutable($peer['claim_expires']);
		if ($exp < new DateTimeImmutable('now')) {
			throw new RuntimeException('Token VPN expiré');
		}
	}

	$privateKey = provision_decrypt_secret($peer['client_private_key_enc'] ?? null);
	if ($privateKey === null) {
		throw new RuntimeException('Configuration VPN indisponible');
	}

	$config = provision_vpn_config_payload($peer, $privateKey, $endpoint);

	$db->prepare(
		'UPDATE provision_vpn_peers
		 SET status = "active", claimed_at = NOW(), claim_token = NULL, claim_expires = NULL,
		     client_private_key_enc = NULL, updated_at = NOW()
		 WHERE id = ?'
	)->execute([(int) $peer['id']]);

	return $config;
}

function provision_vpn_enroll_provisioned(PDO $db, string $extension, string $jti): array {
	if (!provision_vm_validate_jti($db, $jti, $extension)) {
		throw new RuntimeException('Accès refusé');
	}

	$token = provision_get_token_by_jti($db, $jti);
	if (!$token) {
		throw new RuntimeException('Token SIP introuvable');
	}

	$email = (string) $token['email'];
	$peer = provision_vpn_get_peer_by_email($db, $email);

	if ($peer && $peer['status'] === 'active') {
		throw new RuntimeException('VPN déjà actif pour ce compte');
	}

	if ($peer && $peer['status'] === 'ready' && !empty($peer['claim_token'])) {
		$exp = new DateTimeImmutable($peer['claim_expires']);
		if ($exp > new DateTimeImmutable('now')) {
			return [
				'claim_token' => $peer['claim_token'],
				'claim_url' => provision_vpn_build_claim_url($peer['claim_token']),
				'deeplink' => provision_vpn_build_deeplink($peer['claim_token']),
				'tunnel_ip' => $peer['tunnel_ip'],
				'expires' => $exp->format(DateTimeInterface::ATOM),
			];
		}
	}

	if (!$peer) {
		$ip = provision_vpn_allocate_tunnel_ip($db);
		$db->prepare(
			'INSERT INTO provision_vpn_peers (email, extension, tunnel_ip, client_public_key, status)
			 VALUES (?, ?, ?, NULL, "pending")'
		)->execute([$email, $extension, $ip]);
	}

	return provision_vpn_issue_peer($db, $email, $extension);
}

function provision_vpn_status(PDO $db, string $email): array {
	$peer = provision_vpn_get_peer_by_email($db, $email);
	if (!$peer) {
		return ['email' => $email, 'status' => 'none', 'tunnel_ip' => null];
	}

	return [
		'email' => $email,
		'extension' => $peer['extension'],
		'status' => $peer['status'],
		'tunnel_ip' => $peer['tunnel_ip'],
		'has_pending_claim' => $peer['status'] === 'ready' && !empty($peer['claim_token']),
		'claim_expires' => $peer['claim_expires'],
		'claimed_at' => $peer['claimed_at'],
	];
}

function provision_mail_vpn_claim(string $to, string $claimUrl, string $tunnelIp): void {
	$subject = provision_env('PROVISION_VPN_MAIL_SUBJECT', 'Configuration VPN Asaphone');
	$urlEsc = htmlspecialchars($claimUrl, ENT_QUOTES, 'UTF-8');
	$ipEsc = htmlspecialchars($tunnelIp, ENT_QUOTES, 'UTF-8');

	$body = '<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#374151;">Bonjour,</p>';
	$body .= '<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#374151;">'
		. 'Votre accès VPN distant est prêt (IP tunnel <strong>' . $ipEsc . '</strong>).</p>';
	$body .= '<p style="margin:0 0 16px;font-size:14px;color:#374151;">'
		. 'Dans <strong>Asaphone</strong>, choisissez « Configurer le VPN » ou ouvrez ce lien :</p>';
	$body .= '<p style="margin:0;font-size:14px;"><a href="' . $urlEsc . '" style="color:#1a56db;word-break:break-all;">'
		. $urlEsc . '</a></p>';

	$html = provision_mail_layout('Accès VPN Asaphone', $body);
	$text = "Votre accès VPN est prêt.\nIP tunnel : $tunnelIp\nLien : $claimUrl\n";
	provision_smtp_send($to, $subject, $html, $text);
	provision_log_mail_sent('vpn_claim', $to);
}
