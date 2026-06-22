<?php
declare(strict_types=1);

require_once __DIR__ . '/lib/bootstrap.php';

$t = trim((string) ($_GET['t'] ?? ''));
if ($t === '') {
	http_response_code(400);
	echo 'Lien invalide';
	exit;
}

try {
	$db = provision_pdo();
	$row = provision_vm_get_notification($db, $t);
	if (!$row) {
		http_response_code(410);
		echo 'Lien expiré';
		exit;
	}

	$deeplink = provision_build_voicemail_deeplink($t);
	$openUrl = provision_build_voicemail_open_url($t);
	$vmCode = provision_vm_access_code((string) $row['extension']);
	$deeplinkEsc = htmlspecialchars($deeplink, ENT_QUOTES, 'UTF-8');
	$openEsc = htmlspecialchars($openUrl, ENT_QUOTES, 'UTF-8');
	$codeEsc = htmlspecialchars($vmCode, ENT_QUOTES, 'UTF-8');
	$callerEsc = htmlspecialchars((string) ($row['caller_id'] ?? ''), ENT_QUOTES, 'UTF-8');
} catch (Throwable $e) {
	http_response_code(500);
	echo 'Erreur';
	exit;
}
?><!DOCTYPE html>
<html lang="fr">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>Message vocal — Asaphone</title>
	<style>
		body { font-family: system-ui, sans-serif; max-width: 420px; margin: 2rem auto; padding: 0 1rem; color: #1f2937; }
		a.btn { display: block; text-align: center; background: #1a56db; color: #fff; padding: 14px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 1rem 0; }
		p.meta { color: #6b7280; font-size: 14px; }
		code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }
	</style>
</head>
<body>
	<h1>Nouveau message vocal</h1>
	<?php if ($callerEsc !== ''): ?>
	<p class="meta">De : <?= $callerEsc ?> · <?= (int) $row['duration'] ?> s</p>
	<?php endif; ?>
	<p>Ouvrez <strong>Asaphone</strong> pour écouter le message dans l’application.</p>
	<a class="btn" href="<?= $deeplinkEsc ?>">Ouvrir dans Asaphone</a>
	<p class="meta">Ou composez <code><?= $codeEsc ?></code> depuis votre poste.</p>
	<p class="meta">API : <a href="<?= $openEsc ?>"><?= $openEsc ?></a></p>
</body>
</html>
