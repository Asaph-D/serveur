<?php
declare(strict_types=1);

/** Expéditeur réel = EMAIL_USER (Gmail). EMAIL_FROM est un placeholder futur, non utilisé pour l’envoi. */
function provision_smtp_identity(): array {
	$user = provision_env('EMAIL_USER', '');
	if ($user === '') {
		throw new RuntimeException('EMAIL_USER manquant dans provision-secrets.env');
	}

	return [
		'user' => $user,
		'envelope' => $user,
		'header_from' => 'Asaphone <' . $user . '>',
		'reply_to' => $user,
		'brand' => 'Asaphone',
	];
}

function provision_mail_layout(string $title, string $bodyHtml, ?string $footerNote = null): string {
	$brand = 'Asaphone';
	$year = date('Y');
	$footer = $footerNote ?? 'Ce message a été envoyé automatiquement. Merci de ne pas y répondre directement.';

	return '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
		. '<title>' . htmlspecialchars($title, ENT_QUOTES, 'UTF-8') . '</title></head>'
		. '<body style="margin:0;padding:0;background:#f4f6f8;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1a1a2e;">'
		. '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:32px 16px;">'
		. '<tr><td align="center">'
		. '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">'
		. '<tr><td style="background:#1a56db;padding:24px 32px;">'
		. '<p style="margin:0;font-size:20px;font-weight:600;color:#ffffff;letter-spacing:.5px;">' . htmlspecialchars($brand, ENT_QUOTES, 'UTF-8') . '</p>'
		. '<p style="margin:4px 0 0;font-size:13px;color:#c3dafe;">Téléphonie professionnelle</p>'
		. '</td></tr>'
		. '<tr><td style="padding:32px;">'
		. '<h1 style="margin:0 0 16px;font-size:22px;font-weight:600;color:#1a1a2e;">' . htmlspecialchars($title, ENT_QUOTES, 'UTF-8') . '</h1>'
		. $bodyHtml
		. '</td></tr>'
		. '<tr><td style="padding:20px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;">'
		. '<p style="margin:0;font-size:12px;color:#6b7280;line-height:1.5;">' . htmlspecialchars($footer, ENT_QUOTES, 'UTF-8') . '</p>'
		. '<p style="margin:8px 0 0;font-size:11px;color:#9ca3af;">&copy; ' . $year . ' ' . htmlspecialchars($brand, ENT_QUOTES, 'UTF-8') . '</p>'
		. '</td></tr></table></td></tr></table></body></html>';
}

function provision_mail_headers(array $id, string $to, string $subject): array {
	return [
		'MIME-Version: 1.0',
		'From: ' . $id['header_from'],
		'Reply-To: ' . $id['reply_to'],
		'To: ' . $to,
		'Subject: ' . $subject,
		'X-Mailer: Asaphone-Provision/1.0',
		'X-Priority: 3',
	];
}

function provision_smtp_send(string $to, string $subject, string $html, ?string $text = null): void {
	if (provision_env('EMAIL_ENABLED', 'false') !== 'true') {
		throw new RuntimeException('Envoi e-mail désactivé (EMAIL_ENABLED)');
	}

	$host = provision_env('EMAIL_HOST', 'smtp.gmail.com');
	$port = (int) provision_env('EMAIL_PORT', '587');
	$pass = provision_env('EMAIL_PASSWORD', '');
	$id = provision_smtp_identity();

	if ($pass === '') {
		throw new RuntimeException('EMAIL_PASSWORD manquant dans provision-secrets.env');
	}

	$text ??= strip_tags(str_replace(['<br>', '<br/>', '<br />'], "\n", $html));

	$boundary = 'b_' . bin2hex(random_bytes(8));
	$headers = provision_mail_headers($id, $to, $subject);
	$headers[] = 'Content-Type: multipart/alternative; boundary="' . $boundary . '"';

	$body = "--{$boundary}\r\n";
	$body .= "Content-Type: text/plain; charset=UTF-8\r\n\r\n";
	$body .= $text . "\r\n";
	$body .= "--{$boundary}\r\n";
	$body .= "Content-Type: text/html; charset=UTF-8\r\n\r\n";
	$body .= $html . "\r\n";
	$body .= "--{$boundary}--\r\n";

	provision_smtp_dialog($host, $port, $id['user'], $pass, $id['envelope'], $to, $headers, $body);
}

function provision_smtp_send_with_image(
	string $to,
	string $subject,
	string $html,
	string $imagePath,
	string $cid = 'qr-code'
): void {
	if (provision_env('EMAIL_ENABLED', 'false') !== 'true') {
		throw new RuntimeException('Envoi e-mail désactivé (EMAIL_ENABLED)');
	}

	$host = provision_env('EMAIL_HOST', 'smtp.gmail.com');
	$port = (int) provision_env('EMAIL_PORT', '587');
	$pass = provision_env('EMAIL_PASSWORD', '');
	$id = provision_smtp_identity();

	if (!is_readable($imagePath)) {
		throw new RuntimeException("Image QR introuvable: $imagePath");
	}

	$imgData = file_get_contents($imagePath);
	$imgB64 = chunk_split(base64_encode($imgData), 76, "\r\n");

	$altBoundary = 'alt_' . bin2hex(random_bytes(6));
	$mixedBoundary = 'mix_' . bin2hex(random_bytes(6));

	$headers = provision_mail_headers($id, $to, $subject);
	$headers[] = 'Content-Type: multipart/mixed; boundary="' . $mixedBoundary . '"';

	$text = strip_tags(str_replace(['<br>', '<br/>', '<br />'], "\n", $html));

	$body = "--{$mixedBoundary}\r\n";
	$body .= "Content-Type: multipart/alternative; boundary=\"{$altBoundary}\"\r\n\r\n";

	$body .= "--{$altBoundary}\r\n";
	$body .= "Content-Type: text/plain; charset=UTF-8\r\n\r\n";
	$body .= $text . "\r\n";

	$body .= "--{$altBoundary}\r\n";
	$body .= "Content-Type: text/html; charset=UTF-8\r\n\r\n";
	$body .= $html . "\r\n";
	$body .= "--{$altBoundary}--\r\n";

	$body .= "--{$mixedBoundary}\r\n";
	$body .= "Content-Type: image/png; name=\"qr.png\"\r\n";
	$body .= "Content-Transfer-Encoding: base64\r\n";
	$body .= "Content-ID: <{$cid}>\r\n";
	$body .= "Content-Disposition: inline; filename=\"qr.png\"\r\n\r\n";
	$body .= $imgB64 . "\r\n";
	$body .= "--{$mixedBoundary}--\r\n";

	provision_smtp_dialog($host, $port, $id['user'], $pass, $id['envelope'], $to, $headers, $body);
}

function provision_smtp_dialog(
	string $host,
	int $port,
	string $user,
	string $pass,
	string $envelopeFrom,
	string $to,
	array $headers,
	string $body
): void {
	$errno = 0;
	$errstr = '';
	$fp = @stream_socket_client("tcp://{$host}:{$port}", $errno, $errstr, 30);
	if (!$fp) {
		throw new RuntimeException("Connexion SMTP échouée: $errstr ($errno)");
	}
	stream_set_timeout($fp, 30);

	provision_smtp_expect($fp, [220]);
	$ehlo = provision_smtp_cmd($fp, 'EHLO ' . gethostname());

	if (!str_contains($ehlo, 'STARTTLS')) {
		fclose($fp);
		throw new RuntimeException('STARTTLS non supporté par le serveur SMTP');
	}

	provision_smtp_cmd($fp, 'STARTTLS');
	$cryptoMethod = STREAM_CRYPTO_METHOD_TLS_CLIENT;
	if (defined('STREAM_CRYPTO_METHOD_TLSv1_2_CLIENT')) {
		$cryptoMethod = STREAM_CRYPTO_METHOD_TLSv1_2_CLIENT;
	}
	if (!stream_socket_enable_crypto($fp, true, $cryptoMethod)) {
		fclose($fp);
		throw new RuntimeException('Échec négociation STARTTLS');
	}

	provision_smtp_cmd($fp, 'EHLO ' . gethostname());
	provision_smtp_cmd($fp, 'AUTH LOGIN');
	provision_smtp_cmd($fp, base64_encode($user));
	provision_smtp_cmd($fp, base64_encode($pass));
	provision_smtp_cmd($fp, 'MAIL FROM:<' . $envelopeFrom . '>');
	provision_smtp_cmd($fp, 'RCPT TO:<' . $to . '>');
	provision_smtp_cmd($fp, 'DATA');

	$msg = implode("\r\n", $headers) . "\r\n\r\n" . $body . "\r\n.";
	fwrite($fp, $msg . "\r\n");
	provision_smtp_expect($fp, [250]);

	provision_smtp_cmd($fp, 'QUIT');
	fclose($fp);
}

function provision_smtp_cmd($fp, string $cmd): string {
	fwrite($fp, $cmd . "\r\n");
	return provision_smtp_read($fp);
}

function provision_smtp_read($fp): string {
	$out = '';
	while ($line = fgets($fp, 515)) {
		$out .= $line;
		if (isset($line[3]) && $line[3] === ' ') {
			break;
		}
	}
	return $out;
}

function provision_smtp_expect($fp, array $codes): void {
	$resp = provision_smtp_read($fp);
	$code = (int) substr($resp, 0, 3);
	if (!in_array($code, $codes, true)) {
		throw new RuntimeException("Réponse SMTP inattendue ($code): $resp");
	}
}

function provision_mail_verify_code(string $to, string $code, int $ttlMinutes): void {
	$subject = provision_env('PROVISION_MAIL_VERIFY_SUBJECT', 'Votre code de vérification — Asaphone');
	$verifyUrl = provision_base_url() . '/verify/?email=' . rawurlencode($to) . '&code=' . rawurlencode($code);
	$codeEsc = htmlspecialchars($code, ENT_QUOTES, 'UTF-8');
	$urlEsc = htmlspecialchars($verifyUrl, ENT_QUOTES, 'UTF-8');

	$body = '<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#374151;">Bonjour,</p>';
	$body .= '<p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#374151;">'
		. 'Pour activer votre compte téléphonique, saisissez le code ci-dessous dans l\'application <strong>Asaphone</strong> :</p>';
	$body .= '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:8px 0 24px;">'
		. '<div style="display:inline-block;background:#f0f5ff;border:2px solid #1a56db;border-radius:8px;padding:16px 32px;">'
		. '<span style="font-size:32px;font-weight:700;letter-spacing:8px;color:#1a56db;font-family:Consolas,Monaco,monospace;">'
		. $codeEsc . '</span></div></td></tr></table>';
	$body .= '<p style="margin:0 0 8px;font-size:14px;color:#6b7280;">Ce code expire dans <strong>' . $ttlMinutes . ' minutes</strong>.</p>';
	$body .= '<p style="margin:0 0 16px;font-size:14px;color:#6b7280;">'
		. 'Vous pouvez aussi <a href="' . $urlEsc . '" style="color:#1a56db;">confirmer via le navigateur</a>.</p>';
	$body .= '<p style="margin:0;font-size:13px;color:#9ca3af;">Si vous n\'avez pas demandé cette inscription, ignorez ce message.</p>';

	$html = provision_mail_layout('Vérification de votre adresse e-mail', $body);
	$text = "Bonjour,\n\nVotre code de vérification Asaphone : $code\n\n"
		. "Saisissez ce code dans l'application Asaphone.\n"
		. "Expire dans $ttlMinutes minutes.\n\n"
		. "Lien : $verifyUrl\n";

	provision_smtp_send($to, $subject, $html, $text);
	provision_log_mail_sent('verify_code', $to);
}

function provision_log_mail_sent(string $kind, string $to): void {
	$dir = '/var/log/provision';
	if (!is_dir($dir)) {
		@mkdir($dir, 0750, true);
	}
	$line = date('c') . " [mail:$kind] sent to $to\n";
	@file_put_contents($dir . '/mail.log', $line, FILE_APPEND | LOCK_EX);
}

function provision_mail_credentials(string $to, string $extension, string $qrPath, string $claimUrl): void {
	$subject = provision_env('PROVISION_MAIL_SUBJECT', 'Vos identifiants — Asaphone');
	$server = provision_env('PROVISION_PBX_HOST', 'pbx.local');
	$ttlHours = (int) ceil(provision_qr_ttl() / 3600);
	$extEsc = htmlspecialchars($extension, ENT_QUOTES, 'UTF-8');
	$srvEsc = htmlspecialchars($server, ENT_QUOTES, 'UTF-8');
	$urlEsc = htmlspecialchars($claimUrl, ENT_QUOTES, 'UTF-8');
	$vmCode = provision_vm_access_code($extension);
	$vmPin = provision_vm_pin($extension);
	$vmCodeEsc = htmlspecialchars($vmCode, ENT_QUOTES, 'UTF-8');
	$vmPinEsc = htmlspecialchars($vmPin, ENT_QUOTES, 'UTF-8');

	$body = '<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#374151;">Bonjour,</p>';
	$body .= '<p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#374151;">'
		. 'Votre adresse e-mail est confirmée. Votre compte téléphonique est prêt.</p>';
	$body .= '<ol style="margin:0 0 24px;padding-left:20px;font-size:14px;line-height:1.8;color:#374151;">';
	$body .= '<li>Ouvrez <strong>Asaphone</strong> sur votre appareil</li>';
	$body .= '<li>Choisissez « Scanner un QR »</li>';
	$body .= '<li>Scannez le code ci-dessous (valable ' . $ttlHours . ' h)</li>';
	$body .= '</ol>';
	$body .= '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:0 0 24px;">'
		. '<img src="cid:qr-code" alt="QR provisionnement" style="max-width:240px;border:1px solid #e5e7eb;border-radius:8px;" />'
		. '</td></tr></table>';
	$body .= '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border-radius:6px;margin-bottom:16px;">'
		. '<tr><td style="padding:16px;font-size:14px;color:#374151;">'
		. '<strong>Extension :</strong> ' . $extEsc . '<br>'
		. '<strong>Serveur :</strong> ' . $srvEsc . '<br>'
		. '<strong>Messagerie vocale :</strong> composez <strong>' . $vmCodeEsc . '</strong>'
		. ' (depuis votre poste, sans PIN ; sinon PIN&nbsp;: ' . $vmPinEsc . ')'
		. '</td></tr></table>';
	$body .= '<p style="margin:0;font-size:13px;color:#6b7280;">'
		. 'Lien alternatif : <a href="' . $urlEsc . '" style="color:#1a56db;word-break:break-all;">' . $urlEsc . '</a></p>';
	$body .= '<p style="margin:16px 0 0;font-size:13px;color:#9ca3af;">'
		. 'Ce QR est personnel et à usage unique. Ne partagez pas ce message.</p>';

	$html = provision_mail_layout('Vos identifiants téléphoniques', $body, 'Ne transférez pas ce message — il contient vos accès personnels.');
	provision_smtp_send_with_image($to, $subject, $html, $qrPath, 'qr-code');
	provision_log_mail_sent('credentials', $to);
}
