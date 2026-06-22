<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/lib/bootstrap.php';

/**
 * Appelé par Asterisk externnotify :
 *   vm-notify.php <mailbox> <msgid> <context> <callerid> <duration>
 */
if (PHP_SAPI !== 'cli') {
	fwrite(STDERR, "CLI uniquement\n");
	exit(1);
}

$mailbox = $argv[1] ?? '';
$msgId = $argv[2] ?? '';
$context = $argv[3] ?? 'default';
$callerId = $argv[4] ?? '';
$duration = (int) ($argv[5] ?? 0);

if ($mailbox === '') {
	exit(0);
}

try {
	provision_vm_handle_extern_notify($mailbox, $msgId, $context, $callerId, $duration);
	exit(0);
} catch (Throwable $e) {
	error_log('vm-notify: ' . $e->getMessage());
	exit(1);
}
