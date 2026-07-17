<?php
declare(strict_types=1);

function provision_conf_default_room(): string {
	return trim(provision_env('PROVISION_CONF_DEFAULT_ROOM', '6000'));
}

function provision_conf_room_prefix(): string {
	return trim(provision_env('PROVISION_CONF_ROOM_PREFIX', 'asaphone-grp-'));
}

function provision_group_room_from_id(string $groupId): string {
	$slug = preg_replace('/[^a-zA-Z0-9]/', '', $groupId) ?: bin2hex(random_bytes(6));
	$slug = substr($slug, 0, 24);
	return provision_conf_room_prefix() . strtolower($slug);
}

function provision_group_format_row(array $row, array $members): array {
	return [
		'id' => $row['group_id'],
		'group_id' => $row['group_id'],
		'title' => $row['title'],
		'owner' => $row['owner_ext'],
		'members' => $members,
		'room' => $row['room'],
		'call_uri' => $row['call_uri'],
		'dial' => $row['call_uri'],
		'updated_at' => $row['updated_at'],
	];
}

function provision_groups_list_for_ext(PDO $db, string $ext): array {
	$sth = $db->prepare(
		'SELECT g.group_id, g.owner_ext, g.title, g.room, g.call_uri, g.updated_at
		 FROM provision_chat_groups g
		 INNER JOIN provision_chat_group_members m ON m.group_id = g.group_id
		 WHERE m.member_ext = ?
		 ORDER BY g.updated_at DESC'
	);
	$sth->execute([$ext]);
	$rows = $sth->fetchAll(PDO::FETCH_ASSOC) ?: [];
	$out = [];
	foreach ($rows as $row) {
		$out[] = provision_group_format_row($row, provision_group_members($db, (string) $row['group_id']));
	}
	return $out;
}

function provision_group_members(PDO $db, string $groupId): array {
	$sth = $db->prepare(
		'SELECT member_ext FROM provision_chat_group_members WHERE group_id = ? ORDER BY member_ext'
	);
	$sth->execute([$groupId]);
	return array_column($sth->fetchAll(PDO::FETCH_ASSOC) ?: [], 'member_ext');
}

function provision_group_get(PDO $db, string $groupId): ?array {
	$sth = $db->prepare(
		'SELECT group_id, owner_ext, title, room, call_uri, updated_at FROM provision_chat_groups WHERE group_id = ?'
	);
	$sth->execute([$groupId]);
	$row = $sth->fetch(PDO::FETCH_ASSOC);
	if (!$row) {
		return null;
	}
	return provision_group_format_row($row, provision_group_members($db, $groupId));
}

function provision_group_get_by_room(PDO $db, string $room): ?array {
	$sth = $db->prepare(
		'SELECT group_id, owner_ext, title, room, call_uri, updated_at FROM provision_chat_groups WHERE room = ? OR call_uri = ?'
	);
	$sth->execute([$room, $room]);
	$row = $sth->fetch(PDO::FETCH_ASSOC);
	if (!$row) {
		return null;
	}
	return provision_group_format_row($row, provision_group_members($db, (string) $row['group_id']));
}

/**
 * @param list<string> $members
 */
function provision_group_upsert(PDO $db, string $ownerExt, string $groupId, string $title, array $members): array {
	$groupId = trim($groupId);
	if ($groupId === '') {
		throw new InvalidArgumentException('group id requis');
	}
	$title = trim($title);
	$members = array_values(array_unique(array_filter(array_map('strval', $members), static fn (string $m): bool => preg_match('/^\d{3,5}$/', $m) === 1)));
	if (!in_array($ownerExt, $members, true)) {
		$members[] = $ownerExt;
	}
	sort($members);

	$sth = $db->prepare('SELECT room, call_uri FROM provision_chat_groups WHERE group_id = ?');
	$sth->execute([$groupId]);
	$existing = $sth->fetch(PDO::FETCH_ASSOC);

	if ($existing) {
		$room = (string) $existing['room'];
		$callUri = (string) $existing['call_uri'];
		$db->prepare(
			'UPDATE provision_chat_groups SET owner_ext = ?, title = ?, updated_at = NOW() WHERE group_id = ?'
		)->execute([$ownerExt, $title, $groupId]);
	} else {
		$room = provision_group_room_from_id($groupId);
		$callUri = $room;
		$db->prepare(
			'INSERT INTO provision_chat_groups (group_id, owner_ext, title, room, call_uri) VALUES (?, ?, ?, ?, ?)'
		)->execute([$groupId, $ownerExt, $title, $room, $callUri]);
	}

	$db->prepare('DELETE FROM provision_chat_group_members WHERE group_id = ?')->execute([$groupId]);
	$ins = $db->prepare('INSERT INTO provision_chat_group_members (group_id, member_ext) VALUES (?, ?)');
	foreach ($members as $m) {
		$ins->execute([$groupId, $m]);
	}

	$row = provision_group_get($db, $groupId);
	if ($row === null) {
		throw new RuntimeException('sync groupe échoué');
	}
	return $row;
}

function provision_conference_payload(): array {
	return [
		'default_call_uri' => provision_conf_default_room(),
		'default_room' => provision_conf_default_room(),
		'room_prefix' => provision_conf_room_prefix(),
		'dial_mode' => 'extension',
		'hint' => 'Appeler call_uri comme extension interne ; le PBX gère ConfBridge et les invitations.',
	];
}
