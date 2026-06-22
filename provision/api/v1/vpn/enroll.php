<?php
declare(strict_types=1);

require_once dirname(__DIR__, 3) . '/lib/bootstrap.php';

/**
 * Enrôlement VPN rapide pour compte SIP déjà provisionné.
 * POST ?ext=1003&jti=<uuid>  + header X-Provision-Jti
 * ou JSON {"ext":"1003","jti":"..."}
 */
try {
	if (!provision_vpn_enabled()) {
		provision_error('VPN auto-provisionnement désactivé', 503);
	}

	if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
		provision_error('Méthode non autorisée', 405);
	}

	$body = provision_read_json_body();
	$ext = trim((string) ($body['ext'] ?? $_GET['ext'] ?? ''));
	$jti = trim((string) ($body['jti'] ?? $_SERVER['HTTP_X_PROVISION_JTI'] ?? $_GET['jti'] ?? ''));

	if ($ext === '' || $jti === '') {
		provision_error('ext et jti requis');
	}

	$db = provision_pdo();
	$token = provision_get_token_by_jti($db, $jti);
	if (!$token) {
		provision_error('Token SIP introuvable', 404);
	}
	$email = (string) $token['email'];

	$result = provision_vpn_enroll_provisioned($db, $ext, $jti);

	if (empty($result['resent'])) {
		provision_mail_vpn_claim($email, $result['claim_url'], (string) $result['tunnel_ip']);
	}

	provision_ok([
		'message' => 'VPN prêt. Récupérez la configuration via claim.',
		'tunnel_ip' => $result['tunnel_ip'],
		'claim_url' => $result['claim_url'],
		'deeplink' => $result['deeplink'],
		'expires' => $result['expires'],
	]);
} catch (Throwable $e) {
	$msg = $e->getMessage();
	$status = 400;
	if (str_contains($msg, 'Accès refusé')) {
		$status = 403;
	} elseif (str_contains($msg, 'déjà actif')) {
		$status = 409;
	}
	provision_error($msg, $status);
}
