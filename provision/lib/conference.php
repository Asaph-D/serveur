<?php
declare(strict_types=1);

function provision_conf_normalize_ext(string $ext): ?string {
	$ext = preg_replace('/\D/', '', $ext) ?? '';
	return preg_match('/^\d{3,5}$/', $ext) ? $ext : null;
}

function provision_conf_normalize_room(string $room): string {
	$room = trim($room);
	if ($room === '') {
		return provision_conf_default_room();
	}
	if (preg_match('/^\d{4}$/', $room)) {
		return $room;
	}
	if (str_starts_with($room, provision_conf_room_prefix())) {
		return $room;
	}
	return provision_conf_room_prefix() . preg_replace('/[^a-zA-Z0-9]/', '', $room);
}

/**
 * @param list<string> $extensions
 * @return array{invited: list<string>, skipped: list<string>, errors: list<string>}
 */
function provision_conf_invite_extensions(
	PDO $db,
	string $room,
	string $callerExt,
	array $extensions,
	bool $skipCaller = true
): array {
	$room = provision_conf_normalize_room($room);
	$callerExt = provision_conf_normalize_ext($callerExt) ?? '';
	$invited = [];
	$skipped = [];
	$errors = [];

	foreach ($extensions as $raw) {
		$ext = provision_conf_normalize_ext((string) $raw);
		if ($ext === null) {
			$skipped[] = (string) $raw;
			continue;
		}
		if ($skipCaller && $ext === $callerExt) {
			$skipped[] = $ext;
			continue;
		}
		if (!provision_extension_exists($db, $ext)) {
			$errors[] = "extension inconnue: {$ext}";
			continue;
		}
		if (provision_conf_originate_join($room, $ext, $callerExt)) {
			$invited[] = $ext;
		} else {
			$errors[] = "originate échoué: {$ext}";
		}
	}

	return ['invited' => $invited, 'skipped' => $skipped, 'errors' => $errors];
}

function provision_conf_invite_group_auto(PDO $db, string $room, string $callerExt): array {
	$group = provision_group_get_by_room($db, $room);
	if ($group === null) {
		return ['invited' => [], 'skipped' => [], 'errors' => [], 'group' => null];
	}
	$result = provision_conf_invite_extensions($db, $room, $callerExt, $group['members'], true);
	$result['group'] = $group['id'];
	return $result;
}

function provision_conf_originate_join(string $room, string $targetExt, string $callerExt): bool {
	$room = escapeshellarg(provision_conf_normalize_room($room));
	$target = escapeshellarg($targetExt);
	$caller = escapeshellarg($callerExt !== '' ? $callerExt : 'pbx');
	$cmd = sprintf(
		'sudo -n /usr/local/bin/asaphone-conf-invite %s %s %s 2>&1',
		$room,
		$target,
		$caller
	);
	exec($cmd, $output, $code);
	if ($code !== 0) {
		error_log('conf-invite: ' . implode("\n", $output));
		return false;
	}
	return true;
}
