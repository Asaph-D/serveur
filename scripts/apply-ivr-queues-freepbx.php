#!/usr/bin/env php
<?php
/**
 * Enregistre les files IVR dans FreePBX (UI Applications → Queues).
 * Complète queues_custom.conf (Asterisk seul) — visible dans l’admin.
 *
 *   sudo php scripts/apply-ivr-queues-freepbx.php
 */
declare(strict_types=1);

if (!is_readable('/etc/freepbx.conf')) {
	fwrite(STDERR, "FreePBX introuvable.\n");
	exit(1);
}
if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Exécuter en root.\n");
	exit(1);
}

include '/etc/freepbx.conf';

if (!function_exists('queues_del')) {
	\FreePBX::Modules()->loadFunctionsInc('queues');
}

$db = \FreePBX::Database();

function queue_exists(PDO $db, string $name): bool {
	$sth = $db->prepare('SELECT 1 FROM queues_config WHERE extension = ? LIMIT 1');
	$sth->execute([$name]);
	return (bool) $sth->fetchColumn();
}

function delete_queue(PDO $db, string $name): void {
	if (!queue_exists($db, $name)) {
		return;
	}
	if (function_exists('queues_del')) {
		try {
			queues_del($name);
			return;
		} catch (Throwable $e) {
			// repli SQL
		}
	}
	$db->prepare('DELETE FROM queues_details WHERE id = ?')->execute([$name]);
	$db->prepare('DELETE FROM queues_config WHERE extension = ?')->execute([$name]);
}

function insert_queue(PDO $db, string $name, string $descr, array $kv, array $members): void {
	delete_queue($db, $name);

	$db->prepare(
		'INSERT INTO queues_config (
			extension, descr, grppre, alertinfo, ringing, maxwait, password,
			ivr_id, dest, cwignore, callback_id, queuewait, use_queue_context,
			togglehint, qnoanswer, callconfirm
		) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
	)->execute([
		$name, $descr, '', '', 0, '', '', 'none', '', 0, 'none', 0, 0, 0, 0, 0,
	]);

	$ins = $db->prepare(
		'INSERT INTO queues_details (id, keyword, data, flags) VALUES (?,?,?,?)'
	);

	$flag = 0;
	foreach ($kv as $keyword => $data) {
		$ins->execute([$name, $keyword, (string) $data, $flag]);
	}

	foreach ($members as $i => $member) {
		$ins->execute([$name, 'member', $member, $i]);
	}

	echo "OK queue $name ($descr)\n";
}

function default_ringall_kv(int $maxlen = 5): array {
	return [
		'maxlen' => (string) $maxlen,
		'joinempty' => 'yes',
		'leavewhenempty' => 'no',
		'strategy' => 'ringall',
		'timeout' => '25',
		'retry' => '2',
		'wrapuptime' => '5',
		'ringinuse' => 'no',
		'announce-frequency' => '0',
		'announce-holdtime' => 'no',
		'announce-position' => 'no',
		'recording' => 'dontcare',
		'monitor-join' => 'yes',
		'weight' => '0',
		'autofill' => 'no',
		'reportholdtime' => 'no',
		'autopause' => 'no',
		'music' => 'default',
	];
}

function default_leastrecent_kv(): array {
	$kv = default_ringall_kv(0);
	$kv['strategy'] = 'leastrecent';
	$kv['timeout'] = '20';
	return $kv;
}

// phase3-support — tous les postes
insert_queue(
	$db,
	'phase3-support',
	'Support IVR (1001-1010)',
	default_leastrecent_kv(),
	array_map(static fn(int $e): string => "PJSIP/$e,0", range(1001, 1010))
);

// Une file par extension
for ($ext = 1001; $ext <= 1010; $ext++) {
	insert_queue(
		$db,
		"ivr-ext-$ext",
		"IVR extension $ext",
		default_ringall_kv(5),
		["PJSIP/$ext,0"]
	);
}

// Éviter doublon avec queues_custom.conf (FreePBX régénère depuis la base)
$custom = "/etc/asterisk/queues_custom.conf";
file_put_contents($custom, <<<'CONF'
; Géré par FreePBX (queues_config) — scripts/apply-ivr-queues-freepbx.php
; Ne pas redéfinir les queues ici (conflit avec queues_additional.conf).

CONF
);
chown($custom, 'asterisk');
chgrp($custom, 'asterisk');
chmod($custom, 0644);

echo "\nReload FreePBX...\n";
passthru('fwconsole reload', $code);
exit($code === 0 ? 0 : 1);
