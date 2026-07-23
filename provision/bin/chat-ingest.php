<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/lib/bootstrap.php';

if (PHP_SAPI !== 'cli') {
	exit(1);
}

$cmd = $argv[1] ?? '';
$db = provision_pdo();

if ($cmd === 'store') {
	$toExt = $argv[2] ?? '';
	$bodyFile = $argv[3] ?? '';
	$fromSip = $argv[4] ?? '';
	if ($toExt === '' || !is_readable($bodyFile)) {
		exit(1);
	}
	$fromFile = $bodyFile . '.from';
	if (is_readable($fromFile)) {
		$fromSip = trim((string) file_get_contents($fromFile));
	}
	$body = (string) file_get_contents($bodyFile);
	$fromExt = provision_chat_parse_from_ext($fromSip);
	// 0 = payload contrôle (chat_delivered/read) — dialplan n’appelle pas « delivered »
	echo provision_chat_store($db, $toExt, $fromExt, $body);
	exit(0);
}

if ($cmd === 'delivered') {
	$id = (int) ($argv[2] ?? 0);
	if ($id > 0) {
		// MessageSend SUCCESS → DB + SIP chat_delivered vers l’émetteur
		provision_chat_mark_sip_delivered($db, $id, true);
	}
	exit(0);
}

exit(1);
