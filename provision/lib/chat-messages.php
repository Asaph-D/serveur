<?php
declare(strict_types=1);

function provision_chat_parse_from_ext(string $fromSip): string {
	if (preg_match('/(\d{4,5})/', $fromSip, $m)) {
		return $m[1];
	}
	return preg_replace('/[^0-9]/', '', $fromSip) ?: 'unknown';
}

function provision_chat_store(PDO $db, string $toExt, string $fromExt, string $body): int {
	$sth = $db->prepare(
		'INSERT INTO provision_chat_messages (from_ext, to_ext, body) VALUES (?, ?, ?)'
	);
	$sth->execute([$fromExt, $toExt, $body]);
	return (int) $db->lastInsertId();
}

function provision_chat_mark_sip_delivered(PDO $db, int $id): void {
	$sth = $db->prepare(
		'UPDATE provision_chat_messages SET sip_delivered = 1, delivered_at = NOW() WHERE id = ?'
	);
	$sth->execute([$id]);
}

function provision_chat_list_pending(PDO $db, string $toExt): array {
	$sth = $db->prepare(
		'SELECT id, from_ext, body, sip_delivered, created_at
		 FROM provision_chat_messages
		 WHERE to_ext = ? AND consumed = 0
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
		"UPDATE provision_chat_messages SET consumed = 1 WHERE id IN ($placeholders) AND to_ext = ?"
	);
	$sth->execute($params);
	return $sth->rowCount();
}

/** Marque des messages pending comme lus (même persistance que ack). */
function provision_chat_mark_read(PDO $db, string $toExt, array $ids): int {
	return provision_chat_ack($db, $toExt, $ids);
}

/** Accusé de lecture SIP vers un correspondant (messages live sans id serveur). */
function provision_chat_notify_peer_read(string $readerExt, string $peerExt): bool {
	$payload = json_encode([
		'type' => 'chat_read',
		'reader' => $readerExt,
		'from' => $readerExt,
		'peer' => $peerExt,
	], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

	return provision_vm_send_sip_message($peerExt, $readerExt, $payload);
}

function provision_chat_validate_jti(PDO $db, string $jti, string $extension): bool {
	return provision_vm_validate_jti($db, $jti, $extension);
}
