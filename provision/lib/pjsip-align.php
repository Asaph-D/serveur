<?php
declare(strict_types=1);

/**
 * Garantit le profil PJSIP (WebRTC ou classique) avant envoi QR / reconnect.
 * Nécessite /etc/sudoers.d/asaphone-pjsip-align (provision-install.sh).
 */
function provision_ensure_pjsip_profile(string $extension): void {
	if (!preg_match('/^\d{4}$/', $extension)) {
		return;
	}
	$script = '/home/asaph/Documents/serveur/scripts/ensure-pjsip-extension.sh';
	if (!is_executable($script)) {
		$script = dirname(__DIR__, 2) . '/scripts/ensure-pjsip-extension.sh';
	}
	if (!is_readable($script)) {
		error_log("provision: ensure-pjsip-extension.sh introuvable — profil $extension non aligné");
		return;
	}
	$cmd = sprintf(
		'sudo -n %s %s --reload 2>/dev/null',
		escapeshellarg($script),
		escapeshellarg($extension)
	);
	exec($cmd, $out, $code);
	if ($code !== 0) {
		error_log("provision: align PJSIP $extension échoué (code $code): " . implode(' ', $out));
	}
}
