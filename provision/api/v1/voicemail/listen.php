<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

try {
	$db = provision_pdo();
	$auth = provision_vm_auth_from_request($db);
	$ext = $auth['extension'];
	$msgId = trim((string) ($_GET['msg'] ?? ''));
	if ($msgId === '' || !preg_match('/^msg[0-9]+$/', $msgId)) {
		provision_error('Message invalide');
	}

	$path = provision_vm_resolve_msg_path($ext, $msgId);
	if ($path === null) {
		provision_error('Message introuvable', 404);
	}

	$realBase = realpath(provision_vm_spool_dir($ext) . '/INBOX');
	$realPath = realpath($path);
	if ($realBase === false || $realPath === false || !str_starts_with($realPath, $realBase)) {
		provision_error('Accès refusé', 403);
	}

	$mime = str_ends_with(strtolower($path), '.gsm') ? 'audio/gsm' : 'audio/wav';
	header('Content-Type: ' . $mime);
	header('Content-Length: ' . (string) filesize($path));
	header('Cache-Control: no-store');
	readfile($path);
	exit;
} catch (Throwable $e) {
	provision_error($e->getMessage(), 403);
}
