<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

try {
	if (!provision_vpn_enabled()) {
		provision_error('VPN auto-provisionnement désactivé', 503);
	}

	$email = provision_normalize_email((string) ($_GET['email'] ?? ''));
	if (!provision_valid_email($email)) {
		provision_error('Adresse e-mail invalide');
	}

	$db = provision_pdo();
	provision_ok(provision_vpn_status($db, $email));
} catch (Throwable $e) {
	provision_error($e->getMessage(), 400);
}
