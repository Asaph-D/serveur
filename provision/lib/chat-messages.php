<?php
declare(strict_types=1);

function provision_chat_parse_from_ext(string $fromSip): string {
	if (preg_match('/(\d{4,5})/', $fromSip, $m)) {
		return $m[1];
	}
	return preg_replace('/[^0-9]/', '', $fromSip) ?: 'unknown';
}

/** Accusés / contrôle — ne pas stocker comme messages chat. */
function provision_chat_is_control_payload(string $body): bool {
	$trimmed = trim($body);
	if ($trimmed === '' || ($trimmed[0] ?? '') !== '{') {
		return false;
	}
	$json = json_decode($trimmed, true);
	if (!is_array($json)) {
		return false;
	}
	$type = (string) ($json['type'] ?? '');
	return in_array($type, ['chat_delivered', 'chat_read', 'chat_outbound_status', 'vm_notify'], true);
}

/**
 * Persiste un MESSAGE entrant.
 * Réutilise la ligne outbound (même from/to/body + client_id) pour unifier les ticks.
 * Retourne 0 si payload de contrôle (accusé) — ne pas traiter comme chat.
 */
function provision_chat_store(PDO $db, string $toExt, string $fromExt, string $body, ?string $clientId = null): int {
	if (provision_chat_is_control_payload($body)) {
		return 0;
	}

	$clientId = $clientId !== null ? trim($clientId) : '';
	if ($clientId === '') {
		$decoded = json_decode(trim($body), true);
		if (is_array($decoded) && !empty($decoded['client_id'])) {
			$clientId = trim((string) $decoded['client_id']);
			if (isset($decoded['body']) && is_string($decoded['body'])) {
				$body = $decoded['body'];
			} elseif (isset($decoded['text']) && is_string($decoded['text'])) {
				$body = $decoded['text'];
			}
		}
	}

	// Ligne créée par outbound.php (émetteur) — même conversation
	if ($clientId !== '') {
		$sth = $db->prepare(
			'SELECT id FROM provision_chat_messages
			 WHERE from_ext = ? AND client_id = ? LIMIT 1'
		);
		$sth->execute([$fromExt, $clientId]);
		$existing = $sth->fetchColumn();
		if ($existing !== false) {
			$id = (int) $existing;
			$upd = $db->prepare(
				'UPDATE provision_chat_messages
				 SET to_ext = ?, body = ?
				 WHERE id = ? AND from_ext = ?'
			);
			$upd->execute([$toExt, $body, $id, $fromExt]);
			return $id;
		}
	}

	// Match outbound récent (même texte, pas encore livré)
	$sth = $db->prepare(
		'SELECT id, client_id FROM provision_chat_messages
		 WHERE from_ext = ? AND to_ext = ? AND body = ?
		   AND sip_delivered = 0 AND read_at IS NULL
		   AND created_at >= (NOW() - INTERVAL 1 DAY)
		 ORDER BY id DESC LIMIT 1'
	);
	$sth->execute([$fromExt, $toExt, $body]);
	$row = $sth->fetch(PDO::FETCH_ASSOC);
	if ($row) {
		return (int) $row['id'];
	}

	$sth = $db->prepare(
		'INSERT INTO provision_chat_messages (from_ext, to_ext, body, client_id) VALUES (?, ?, ?, ?)'
	);
	$sth->execute([$fromExt, $toExt, $body, $clientId !== '' ? $clientId : null]);
	return (int) $db->lastInsertId();
}

/**
 * Enregistre un message sortant (ticks sent/delivered/read).
 * Réutilise la ligne existante si même (from_ext, client_id).
 */
function provision_chat_outbound(PDO $db, string $fromExt, string $toExt, string $body, string $clientId, ?int $atMs = null): int {
	$clientId = trim($clientId);
	if ($clientId === '' || !preg_match('/^\d{4,5}$/', $toExt)) {
		throw new InvalidArgumentException('to / client_id invalides');
	}

	$sth = $db->prepare(
		'SELECT id FROM provision_chat_messages WHERE from_ext = ? AND client_id = ? LIMIT 1'
	);
	$sth->execute([$fromExt, $clientId]);
	$existing = $sth->fetchColumn();
	if ($existing !== false) {
		$id = (int) $existing;
		$upd = $db->prepare(
			'UPDATE provision_chat_messages
			 SET to_ext = ?, body = ?
			 WHERE id = ? AND from_ext = ?'
		);
		$upd->execute([$toExt, $body, $id, $fromExt]);
		return $id;
	}

	$created = $atMs !== null && $atMs > 0
		? date('Y-m-d H:i:s', (int) floor($atMs / 1000))
		: null;

	if ($created !== null) {
		$ins = $db->prepare(
			'INSERT INTO provision_chat_messages (from_ext, to_ext, body, client_id, created_at)
			 VALUES (?, ?, ?, ?, ?)'
		);
		$ins->execute([$fromExt, $toExt, $body, $clientId, $created]);
	} else {
		$ins = $db->prepare(
			'INSERT INTO provision_chat_messages (from_ext, to_ext, body, client_id)
			 VALUES (?, ?, ?, ?)'
		);
		$ins->execute([$fromExt, $toExt, $body, $clientId]);
	}
	return (int) $db->lastInsertId();
}

function provision_chat_row_status(array $row): string {
	if (!empty($row['read_at'])) {
		return 'read';
	}
	if (!empty($row['sip_delivered']) || !empty($row['delivered_at']) || !empty($row['consumed'])) {
		return 'delivered';
	}
	return 'sent';
}

function provision_chat_status_payload(array $row): array {
	return [
		'id' => (int) $row['id'],
		'client_id' => $row['client_id'] !== null && $row['client_id'] !== '' ? (string) $row['client_id'] : null,
		'status' => provision_chat_row_status($row),
		'peer' => (string) $row['to_ext'],
	];
}

/** Statuts des messages envoyés par $fromExt (poll ticks). */
function provision_chat_statuses(PDO $db, string $fromExt, array $ids = [], array $clientIds = []): array {
	$ids = array_values(array_filter(array_map('intval', $ids), static fn (int $v): bool => $v > 0));
	$clientIds = array_values(array_filter(array_map(
		static fn ($v): string => trim((string) $v),
		$clientIds
	), static fn (string $v): bool => $v !== ''));

	if ($ids === [] && $clientIds === []) {
		return [];
	}

	$clauses = [];
	$params = [$fromExt];
	if ($ids !== []) {
		$ph = implode(',', array_fill(0, count($ids), '?'));
		$clauses[] = "id IN ($ph)";
		array_push($params, ...$ids);
	}
	if ($clientIds !== []) {
		$ph = implode(',', array_fill(0, count($clientIds), '?'));
		$clauses[] = "client_id IN ($ph)";
		array_push($params, ...$clientIds);
	}

	$sql = 'SELECT id, client_id, to_ext, sip_delivered, consumed, delivered_at, read_at
		FROM provision_chat_messages
		WHERE from_ext = ? AND (' . implode(' OR ', $clauses) . ')
		ORDER BY id ASC';
	$sth = $db->prepare($sql);
	$sth->execute($params);
	$rows = $sth->fetchAll(PDO::FETCH_ASSOC) ?: [];
	return array_map('provision_chat_status_payload', $rows);
}

/** Statuts récents des messages sortants (enrichissement pending). */
function provision_chat_recent_outbound_statuses(PDO $db, string $fromExt, int $limit = 50): array {
	$sth = $db->prepare(
		'SELECT id, client_id, to_ext, sip_delivered, consumed, delivered_at, read_at
		 FROM provision_chat_messages
		 WHERE from_ext = ? AND (client_id IS NOT NULL OR sip_delivered = 1 OR read_at IS NOT NULL)
		 ORDER BY id DESC
		 LIMIT ?'
	);
	$sth->bindValue(1, $fromExt, PDO::PARAM_STR);
	$sth->bindValue(2, $limit, PDO::PARAM_INT);
	$sth->execute();
	$rows = array_reverse($sth->fetchAll(PDO::FETCH_ASSOC) ?: []);
	return array_map('provision_chat_status_payload', $rows);
}

/**
 * Marque livré device + pousse SIP chat_delivered à l’émetteur (style WhatsApp ✓✓).
 */
function provision_chat_mark_sip_delivered(PDO $db, int $id, bool $notifySender = true): void {
	$sth = $db->prepare(
		'SELECT id, from_ext, to_ext, client_id, sip_delivered
		 FROM provision_chat_messages WHERE id = ? LIMIT 1'
	);
	$sth->execute([$id]);
	$row = $sth->fetch(PDO::FETCH_ASSOC);
	if (!$row) {
		return;
	}

	$upd = $db->prepare(
		'UPDATE provision_chat_messages
		 SET sip_delivered = 1, delivered_at = COALESCE(delivered_at, NOW()), consumed = 1
		 WHERE id = ?'
	);
	$upd->execute([$id]);

	if (!$notifySender) {
		return;
	}
	// Éviter double push si déjà livré
	if (!empty($row['sip_delivered'])) {
		return;
	}

	$fromExt = (string) $row['from_ext'];
	$toExt = (string) $row['to_ext'];
	if ($fromExt === '' || $toExt === '' || $fromExt === $toExt) {
		return;
	}

	provision_chat_notify_senders_delivered($db, $toExt, [[
		'id' => (int) $row['id'],
		'from_ext' => $fromExt,
		'client_id' => $row['client_id'] ?? null,
	]]);
}

/** Messages jamais reçus en live (SIP MESSAGE échoué / offline). */
function provision_chat_list_pending(PDO $db, string $toExt): array {
	$sth = $db->prepare(
		'SELECT id, from_ext, body, client_id, sip_delivered, created_at
		 FROM provision_chat_messages
		 WHERE to_ext = ? AND consumed = 0 AND sip_delivered = 0
		 ORDER BY id ASC'
	);
	$sth->execute([$toExt]);
	return $sth->fetchAll(PDO::FETCH_ASSOC) ?: [];
}

function provision_chat_ack(PDO $db, string $toExt, array $ids): int {
	if ($ids === []) {
		return 0;
	}
	$placeholders = implode(',', array_fill(0, count($ids), '?'));
	$params = array_merge($ids, [$toExt]);
	$sth = $db->prepare(
		"UPDATE provision_chat_messages
		 SET consumed = 1, sip_delivered = 1, delivered_at = COALESCE(delivered_at, NOW())
		 WHERE id IN ($placeholders) AND to_ext = ?"
	);
	$sth->execute($params);
	return $sth->rowCount();
}

/**
 * Récupère la file pending puis la vide (un seul envoi HTTP par message).
 * Notifie les émetteurs (chat_delivered) pour les ticks.
 */
function provision_chat_fetch_pending(PDO $db, string $toExt): array {
	$rows = provision_chat_list_pending($db, $toExt);
	if ($rows === []) {
		return [];
	}
	$ids = array_values(array_filter(
		array_map(static fn (array $row): int => (int) $row['id'], $rows),
		static fn (int $id): bool => $id > 0
	));
	if ($ids !== []) {
		provision_chat_ack($db, $toExt, $ids);
		provision_chat_notify_senders_delivered($db, $toExt, $rows);
	}
	return $rows;
}

function provision_chat_notify_senders_delivered(PDO $db, string $readerExt, array $rows): void {
	$byFrom = [];
	foreach ($rows as $row) {
		$from = (string) ($row['from_ext'] ?? '');
		if ($from === '' || $from === $readerExt) {
			continue;
		}
		$byFrom[$from][] = $row;
	}
	foreach ($byFrom as $fromExt => $list) {
		// Clés numériques PHP ("1005" → int) — MessageSend exige une string
		$fromExt = (string) $fromExt;
		$ids = [];
		$clientIds = [];
		foreach ($list as $row) {
			$ids[] = (int) $row['id'];
			if (!empty($row['client_id'])) {
				$clientIds[] = (string) $row['client_id'];
			}
		}
		$payload = json_encode([
			'type' => 'chat_delivered',
			'peer' => $readerExt,
			'ids' => $ids,
			'client_ids' => $clientIds,
		], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
		provision_vm_send_sip_message($fromExt, (string) $readerExt, $payload);
	}
}

/** Marque lus (read_at) — distinct de la livraison device. */
function provision_chat_mark_read(PDO $db, string $toExt, array $ids): int {
	if ($ids === []) {
		return 0;
	}
	$placeholders = implode(',', array_fill(0, count($ids), '?'));
	$params = array_merge($ids, [$toExt]);
	$sth = $db->prepare(
		"UPDATE provision_chat_messages
		 SET consumed = 1,
		     sip_delivered = 1,
		     delivered_at = COALESCE(delivered_at, NOW()),
		     read_at = COALESCE(read_at, NOW())
		 WHERE id IN ($placeholders) AND to_ext = ?"
	);
	$sth->execute($params);
	return $sth->rowCount();
}

/**
 * Pousse SIP chat_read vers chaque émetteur des messages lus (style WhatsApp ✓✓ verts).
 * L’app n’émet pas ce MESSAGE — le serveur le fait à POST read.php.
 */
function provision_chat_notify_senders_read(PDO $db, string $readerExt, array $ids, array $clientIds = []): void {
	$ids = array_values(array_filter(array_map('intval', $ids), static fn (int $v): bool => $v > 0));
	if ($ids === []) {
		return;
	}
	$placeholders = implode(',', array_fill(0, count($ids), '?'));
	$sth = $db->prepare(
		"SELECT id, from_ext, client_id FROM provision_chat_messages
		 WHERE id IN ($placeholders) AND to_ext = ?"
	);
	$sth->execute(array_merge($ids, [$readerExt]));
	$rows = $sth->fetchAll(PDO::FETCH_ASSOC) ?: [];
	if ($rows === []) {
		return;
	}

	$byFrom = [];
	foreach ($rows as $row) {
		$from = (string) ($row['from_ext'] ?? '');
		if ($from === '' || $from === $readerExt) {
			continue;
		}
		$byFrom[$from][] = $row;
	}

	$extraClientIds = array_values(array_filter(array_map('strval', $clientIds), static fn (string $v): bool => $v !== ''));

	foreach ($byFrom as $fromExt => $list) {
		$fromExt = (string) $fromExt;
		$msgIds = [];
		$msgClientIds = $extraClientIds;
		foreach ($list as $row) {
			$msgIds[] = (int) $row['id'];
			if (!empty($row['client_id'])) {
				$msgClientIds[] = (string) $row['client_id'];
			}
		}
		$msgClientIds = array_values(array_unique($msgClientIds));
		provision_chat_notify_peer_read($readerExt, $fromExt, $msgIds, $msgClientIds);
	}
}

/** Accusé de lecture SIP vers un correspondant (émetteur original). */
function provision_chat_notify_peer_read(string $readerExt, string $peerExt, array $ids = [], array $clientIds = []): bool {
	$ids = array_values(array_filter(array_map('intval', $ids), static fn (int $v): bool => $v > 0));
	$clientIds = array_values(array_filter(array_map('strval', $clientIds), static fn (string $v): bool => $v !== ''));
	// Sans ids ni client_ids l’app ne peut pas lier les ticks — inutile / bruit
	if ($ids === [] && $clientIds === []) {
		return false;
	}
	$payload = json_encode([
		'type' => 'chat_read',
		'reader' => $readerExt,
		'from' => $readerExt,
		'peer' => $readerExt,
		'ids' => $ids,
		'client_ids' => $clientIds,
	], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

	return provision_vm_send_sip_message((string) $peerExt, (string) $readerExt, $payload);
}

function provision_chat_validate_jti(PDO $db, string $jti, string $extension): bool {
	return provision_vm_validate_jti($db, $jti, $extension);
}

/**
 * Auth chat : jti (QR / reconnect) OU secret SIP (REGISTER manuel).
 * Preuve d’accès = mêmes identifiants que le REGISTER Asterisk.
 *
 * @param array|null $body Corps JSON déjà lu (secret / password optionnels)
 * @return string extension authentifiée
 */
function provision_chat_require_ext(PDO $db, ?array $body = null): string {
	$ext = trim((string) ($_GET['ext'] ?? ($body['ext'] ?? $body['extension'] ?? '')));
	$jti = trim((string) ($_SERVER['HTTP_X_PROVISION_JTI'] ?? $_GET['jti'] ?? ($body['jti'] ?? '')));
	$secret = (string) (
		$_SERVER['HTTP_X_PROVISION_SECRET']
		?? $_GET['secret']
		?? $_GET['password']
		?? ($body['secret'] ?? $body['password'] ?? '')
	);

	if ($ext === '') {
		throw new RuntimeException('ext requis');
	}
	if (!preg_match('/^\d{4,5}$/', $ext)) {
		throw new RuntimeException('ext invalide');
	}

	if ($jti !== '' && provision_chat_validate_jti($db, $jti, $ext)) {
		return $ext;
	}

	if ($secret !== '') {
		$ip = provision_client_ip();
		$max = (int) provision_env('PROVISION_RATE_LIMIT_VERIFY', '10');
		provision_rate_limit('chat_secret_ip', $ip, $max);
		provision_rate_limit('chat_secret_ext', $ext, $max);
		provision_verify_extension_secret($db, $ext, $secret);
		return $ext;
	}

	throw new RuntimeException(
		'Authentification requise : jti (QR/reconnect) ou secret SIP (même mot de passe que le REGISTER)'
	);
}
