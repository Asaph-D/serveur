#!/usr/bin/env php
<?php
declare(strict_types=1);

/**
 * Invite une extension dans une salle ConfBridge (CLI / dialplan).
 * Usage: conf-invite.php <room> <target_ext> [caller_ext]
 *        conf-invite.php auto <room> <caller_ext>
 */
if (PHP_SAPI !== 'cli') {
	fwrite(STDERR, "CLI uniquement\n");
	exit(1);
}

require_once dirname(__DIR__) . '/lib/bootstrap.php';

$mode = $argv[1] ?? '';
if ($mode === 'auto') {
	$room = (string) ($argv[2] ?? '');
	$caller = (string) ($argv[3] ?? '');
	if ($room === '' || $caller === '') {
		fwrite(STDERR, "usage: auto <room> <caller_ext>\n");
		exit(1);
	}
	$db = provision_pdo();
	$result = provision_conf_invite_group_auto($db, $room, $caller);
	echo json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . "\n";
	exit($result['errors'] !== [] && $result['invited'] === [] ? 1 : 0);
}

$room = (string) ($argv[1] ?? '');
$target = (string) ($argv[2] ?? '');
$caller = (string) ($argv[3] ?? 'pbx');
if ($room === '' || $target === '') {
	fwrite(STDERR, "usage: <room> <target_ext> [caller_ext]\n");
	exit(1);
}

$roomEsc = provision_conf_normalize_room($room);
$targetEsc = provision_conf_normalize_ext($target);
if ($targetEsc === null) {
	exit(1);
}

$cmd = sprintf(
	'asterisk -rx %s',
	escapeshellarg(
		"channel originate {ASAPHONE_CONF_ROOM={$roomEsc}}PJSIP/{$targetEsc} extension s@asaphone-conf-join"
	)
);
exec($cmd, $out, $code);
if ($code !== 0) {
	fwrite(STDERR, implode("\n", $out));
	exit(1);
}
echo "OK {$targetEsc} -> {$roomEsc}\n";
