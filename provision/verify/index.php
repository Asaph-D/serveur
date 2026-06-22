<?php
declare(strict_types=1);

require_once dirname(__DIR__) . '/lib/bootstrap.php';

$email = provision_normalize_email((string) ($_GET['email'] ?? $_POST['email'] ?? ''));
$code = trim((string) ($_GET['code'] ?? $_POST['code'] ?? ''));
$result = null;
$error = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST' || ($email !== '' && $code !== '')) {
	try {
		if (!provision_enabled()) {
			throw new RuntimeException('Provisionnement désactivé');
		}
		if (!provision_valid_email($email)) {
			throw new RuntimeException('Adresse e-mail invalide');
		}
		if (!preg_match('/^\d{6}$/', $code)) {
			throw new RuntimeException('Code invalide (6 chiffres)');
		}

		$db = provision_pdo();
		$resolved = provision_execute_verify($db, $email, $code);

		if (!empty($resolved['qr_resent'])) {
			$result = 'Vos identifiants Asaphone vous ont été renvoyés par courrier.';
		} elseif ($resolved['send_qr'] && $resolved['extension'] !== null) {
			$result = 'Votre e-mail est vérifié. Vos identifiants Asaphone vous ont été envoyés par courrier.';
		} elseif ($resolved['status'] === 'pending_admin') {
			$result = 'Votre e-mail est vérifié. Un administrateur validera votre extension sous peu.';
		} else {
			$result = 'Votre e-mail est vérifié.';
		}
	} catch (Throwable $e) {
		$error = $e->getMessage();
	}
}

?><!DOCTYPE html>
<html lang="fr">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>Vérification Asaphone</title>
	<style>
		body { font-family: system-ui, sans-serif; max-width: 480px; margin: 2rem auto; padding: 0 1rem; }
		.ok { color: #0a7; }
		.err { color: #c33; }
		label { display: block; margin: 0.75rem 0 0.25rem; }
		input { width: 100%; padding: 0.5rem; box-sizing: border-box; }
		button { margin-top: 1rem; padding: 0.6rem 1.2rem; }
	</style>
</head>
<body>
	<h1>Vérification Asaphone</h1>
	<?php if ($result): ?>
		<p class="ok"><?= htmlspecialchars($result, ENT_QUOTES, 'UTF-8') ?></p>
	<?php elseif ($error): ?>
		<p class="err"><?= htmlspecialchars($error, ENT_QUOTES, 'UTF-8') ?></p>
	<?php endif; ?>
	<form method="post">
		<label for="email">E-mail</label>
		<input type="email" id="email" name="email" required value="<?= htmlspecialchars($email, ENT_QUOTES, 'UTF-8') ?>">
		<label for="code">Code à 6 chiffres</label>
		<input type="text" id="code" name="code" required pattern="\d{6}" maxlength="6" value="<?= htmlspecialchars($code, ENT_QUOTES, 'UTF-8') ?>">
		<button type="submit">Vérifier</button>
	</form>
</body>
</html>
