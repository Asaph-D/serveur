<?php
declare(strict_types=1);

function provision_build_voicemail_open_url(string $notifyToken): string {
	return provision_base_url() . '/api/v1/voicemail/open.php?t=' . rawurlencode($notifyToken);
}

function provision_build_voicemail_deeplink(string $notifyToken): string {
	$scheme = provision_env('PROVISION_QR_SCHEME', 'asaphone');
	$openUrl = provision_build_voicemail_open_url($notifyToken);
	return $scheme . '://voicemail?url=' . rawurlencode($openUrl);
}

function provision_build_voicemail_deeplink_for_extension(string $extension): string {
	$scheme = provision_env('PROVISION_QR_SCHEME', 'asaphone');
	$code = provision_vm_access_code($extension);
	return $scheme . '://voicemail?code=' . rawurlencode($code) . '&ext=' . rawurlencode($extension);
}

function provision_vm_notify_ttl(): int {
	return (int) provision_env('PROVISION_VM_NOTIFY_TTL', '604800');
}

function provision_vm_spool_dir(string $extension, string $context = 'default'): string {
	return '/var/spool/asterisk/voicemail/' . $context . '/' . $extension;
}

function provision_vm_resolve_msg_path(string $extension, string $msgId, string $context = 'default'): ?string {
	$base = provision_vm_spool_dir($extension, $context) . '/INBOX';
	foreach (['wav', 'WAV', 'gsm', 'g722'] as $ext) {
		$path = "$base/$msgId.$ext";
		if (is_readable($path)) {
			return $path;
		}
	}
	return null;
}

function provision_vm_extract_caller_extension(string $callerId): string {
	if (preg_match('/(\d{4,5})/', $callerId, $m)) {
		return $m[1];
	}
	return 'pbx';
}

function provision_vm_build_sip_payload(
	string $extension,
	string $msgId,
	string $callerId,
	int $duration
): string {
	$vmCode = provision_vm_access_code($extension);
	$caller = provision_vm_extract_caller_extension($callerId);
	$text = sprintf(
		'Nouveau message vocal de %s (%ds). Composez %s pour ecouter.',
		$caller,
		$duration,
		$vmCode
	);

	return json_encode([
		'type' => 'voicemail',
		'ext' => $extension,
		'vm_code' => $vmCode,
		'caller' => $caller,
		'caller_id' => $callerId,
		'duration' => $duration,
		'msg_id' => $msgId,
		'text' => $text,
		'deeplink' => provision_build_voicemail_deeplink_for_extension($extension),
		'open_api' => provision_base_url() . '/api/v1/voicemail/open.php?ext=' . rawurlencode($extension),
	], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}

/**
 * Notification messagerie via SIP MESSAGE (même flux que le chat Asaphone).
 */
function provision_vm_send_sip_message(string $extension, string $callerId, string $body): bool {
	$caller = provision_vm_extract_caller_extension($callerId);
	$tmpDir = '/var/lib/provision/tmp';
	if (!is_dir($tmpDir)) {
		@mkdir($tmpDir, 01777, true);
	}

	$payloadFile = "$tmpDir/vm-notify-$extension.json";
	if (@file_put_contents($payloadFile, $body) === false) {
		error_log("vm-notify: impossible d'écrire $payloadFile");
		return false;
	}
	@chmod($payloadFile, 0666);

	$cmd = sprintf(
		'sudo -n /usr/local/bin/asaphone-vm-originate %s %s 2>&1',
		escapeshellarg($extension),
		escapeshellarg($caller)
	);
	exec($cmd, $output, $code);

	if ($code !== 0) {
		error_log('vm-notify originate: ' . implode("\n", $output));
		return false;
	}

	return true;
}

function provision_vm_list_pending_notifications(PDO $db, string $extension): array {
	$sth = $db->prepare(
		'SELECT id, caller_id, duration, msg_id, notify_token, created_at
		 FROM provision_vm_notifications
		 WHERE extension = ? AND consumed = 0 AND expires > NOW()
		 ORDER BY id ASC'
	);
	$sth->execute([$extension]);
	$rows = $sth->fetchAll(PDO::FETCH_ASSOC) ?: [];
	$jti = trim((string) ($_SERVER['HTTP_X_PROVISION_JTI'] ?? $_GET['jti'] ?? ''));
	$baseListen = provision_base_url() . '/api/v1/voicemail/listen.php';

	$out = [];
	foreach ($rows as $row) {
		$item = [
			'id' => (int) $row['id'],
			'msg_id' => $row['msg_id'],
			'caller_id' => $row['caller_id'],
			'duration' => (int) $row['duration'],
			'created_at' => $row['created_at'],
			'vm_code' => provision_vm_access_code($extension),
			'deeplink' => provision_build_voicemail_deeplink_for_extension($extension),
			'text' => sprintf(
				'Nouveau message vocal%s (%ds). Composez %s.',
				$row['caller_id'] !== '' ? ' de ' . $row['caller_id'] : '',
				(int) $row['duration'],
				provision_vm_access_code($extension)
			),
		];
		if ($jti !== '') {
			$item['listen_url'] = $baseListen . '?ext=' . rawurlencode($extension)
				. '&jti=' . rawurlencode($jti) . '&msg=' . rawurlencode((string) $row['msg_id']);
		}
		$out[] = $item;
	}
	return $out;
}

function provision_vm_ack_notifications(PDO $db, string $extension, array $ids): int {
	if ($ids === []) {
		return 0;
	}
	$placeholders = implode(',', array_fill(0, count($ids), '?'));
	$params = array_merge($ids, [$extension]);
	$sth = $db->prepare(
		"UPDATE provision_vm_notifications SET consumed = 1
		 WHERE id IN ($placeholders) AND extension = ?"
	);
	$sth->execute($params);
	return $sth->rowCount();
}

function provision_vm_create_notification(
	PDO $db,
	string $extension,
	string $msgId,
	string $context,
	string $callerId,
	int $duration,
	?string $msgPath
): array {
	$token = provision_random_token(24);
	$expires = (new DateTimeImmutable('now'))->modify('+' . provision_vm_notify_ttl() . ' seconds');

	$sth = $db->prepare(
		'INSERT INTO provision_vm_notifications
		 (extension, email, phone, caller_id, duration, msg_id, msg_path, notify_token, expires)
		 VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, ?)'
	);
	$sth->execute([
		$extension,
		$callerId,
		$duration,
		$msgId,
		$msgPath,
		$token,
		$expires->format('Y-m-d H:i:s'),
	]);

	$vmCode = provision_vm_access_code($extension);
	$sipBody = provision_vm_build_sip_payload($extension, $msgId, $callerId, $duration);

	return [
		'extension' => $extension,
		'vm_code' => $vmCode,
		'caller_id' => $callerId,
		'sip_body' => $sipBody,
		'deeplink' => provision_build_voicemail_deeplink_for_extension($extension),
		'notify_token' => $token,
	];
}

function provision_vm_handle_extern_notify(
	string $mailbox,
	string $msgId,
	string $context,
	string $callerId,
	int $duration
): void {
	$extension = preg_replace('/@.*$/', '', $mailbox);
	if ($extension === '' || (int) $extension < 1001 || (int) $extension > 1010) {
		return;
	}

	$db = provision_pdo();
	$msgPath = provision_vm_resolve_msg_path($extension, $msgId, $context);
	$notification = provision_vm_create_notification(
		$db,
		$extension,
		$msgId,
		$context,
		$callerId,
		$duration,
		$msgPath
	);

	$ok = provision_vm_send_sip_message(
		$extension,
		$callerId,
		$notification['sip_body']
	);

	error_log(sprintf(
		'vm-notify: ext=%s msg=%s sip=%s deeplink=%s',
		$extension,
		$msgId,
		$ok ? 'ok' : 'fail',
		$notification['deeplink']
	));
}

function provision_vm_get_notification(PDO $db, string $token): ?array {
	$sth = $db->prepare(
		'SELECT * FROM provision_vm_notifications
		 WHERE notify_token = ? AND expires > NOW() LIMIT 1'
	);
	$sth->execute([$token]);
	$row = $sth->fetch(PDO::FETCH_ASSOC);
	return $row ?: null;
}

function provision_vm_validate_jti(PDO $db, string $jti, string $extension): bool {
	$sth = $db->prepare(
		'SELECT 1 FROM provision_tokens
		 WHERE jti = ? AND extension = ? AND used = 1 LIMIT 1'
	);
	$sth->execute([$jti, $extension]);
	return (bool) $sth->fetchColumn();
}

function provision_vm_list_inbox(string $extension, string $context = 'default'): array {
	$dir = provision_vm_spool_dir($extension, $context) . '/INBOX';
	if (!is_dir($dir)) {
		return [];
	}

	$messages = [];
	foreach (glob($dir . '/msg*.txt') ?: [] as $metaFile) {
		$msgId = basename($metaFile, '.txt');
		$meta = @file_get_contents($metaFile);
		$caller = '';
		$duration = 0;
		if (is_string($meta)) {
			if (preg_match('/callerid=(.+)/', $meta, $m)) {
				$caller = trim($m[1]);
			}
			if (preg_match('/duration=(\d+)/', $meta, $m)) {
				$duration = (int) $m[1];
			}
		}
		$messages[] = [
			'id' => $msgId,
			'caller_id' => $caller,
			'duration' => $duration,
		];
	}

	usort($messages, static function (array $a, array $b): int {
		return strcmp($b['id'], $a['id']);
	});

	return $messages;
}

function provision_vm_auth_from_request(PDO $db): array {
	$token = trim((string) ($_GET['t'] ?? $_GET['token'] ?? ''));
	if ($token !== '') {
		$row = provision_vm_get_notification($db, $token);
		if (!$row) {
			throw new RuntimeException('Lien expiré ou invalide');
		}
		return ['mode' => 'notify', 'extension' => (string) $row['extension'], 'token' => $token, 'row' => $row];
	}

	$ext = trim((string) ($_GET['ext'] ?? ''));
	$jti = trim((string) ($_SERVER['HTTP_X_PROVISION_JTI'] ?? $_GET['jti'] ?? ''));
	if ($ext === '' || $jti === '') {
		throw new RuntimeException('Authentification requise (token, ou ext+jti)');
	}
	if (!provision_vm_validate_jti($db, $jti, $ext)) {
		throw new RuntimeException('Accès refusé');
	}
	return ['mode' => 'jti', 'extension' => $ext, 'token' => null, 'row' => null];
}
