<?php
declare(strict_types=1);

/**
 * Gmail : AUTH + enveloppe SMTP (MAIL FROM) via EMAIL_USER.
 * EMAIL_FROM sert de Reply-To ; affichage From = EMAIL_USER sans alias Google configuré.
 */
function provision_smtp_identity(): array {
	$user = provision_env('EMAIL_USER', '');
	$display = provision_env('EMAIL_FROM', provision_env('PROVISION_MAIL_FROM', $user));
	$host = provision_env('EMAIL_HOST', 'smtp.gmail.com');

	if ($user === '') {
		throw new RuntimeException('EMAIL_USER manquant dans provision-secrets.env');
	}

	$headerFrom = $display;
	if (str_contains($host, 'gmail.com') && strcasecmp($display, $user) !== 0) {
		$headerFrom = $user;
	}

	return [
		'user' => $user,
		'envelope' => $user,
		'header_from' => 'Asaphone <' . $headerFrom . '>',
		'reply_to' => $display,
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
	$headers = [
		'MIME-Version: 1.0',
		'Content-Type: multipart/alternative; boundary="' . $boundary . '"',
		'From: ' . $id['header_from'],
		'Reply-To: ' . $id['reply_to'],
		'To: ' . $to,
		'Subject: ' . $subject,
	];

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

	$headers = [
		'MIME-Version: 1.0',
		'Content-Type: multipart/mixed; boundary="' . $mixedBoundary . '"',
		'From: ' . $id['header_from'],
		'Reply-To: ' . $id['reply_to'],
		'To: ' . $to,
		'Subject: ' . $subject,
	];

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
	$subject = provision_env('PROVISION_MAIL_VERIFY_SUBJECT', 'Code de vérification Asaphone');
	$verifyUrl = provision_base_url() . '/verify/?email=' . rawurlencode($to) . '&code=' . rawurlencode($code);

	$html = '<p>Bonjour,</p>';
	$html .= '<p>Votre code de vérification Asaphone : <strong style="font-size:24px;letter-spacing:4px;">'
		. htmlspecialchars($code, ENT_QUOTES, 'UTF-8') . '</strong></p>';
	$html .= '<p>Ce code expire dans ' . $ttlMinutes . ' minutes.</p>';
	$html .= '<p>Ou cliquez sur ce lien : <a href="' . htmlspecialchars($verifyUrl, ENT_QUOTES, 'UTF-8') . '">'
		. htmlspecialchars($verifyUrl, ENT_QUOTES, 'UTF-8') . '</a></p>';
	$html .= '<p>Si vous n\'avez pas demandé cette inscription, ignorez ce message.</p>';

	provision_smtp_send($to, $subject, $html);
}

function provision_mail_credentials(string $to, string $extension, string $qrPath, string $claimUrl): void {
	$subject = provision_env('PROVISION_MAIL_SUBJECT', 'Vos identifiants Asaphone');
	$server = provision_env('PROVISION_PBX_HOST', 'pbx.local');
	$ttlHours = (int) ceil(provision_qr_ttl() / 3600);

	$html = '<p>Bonjour,</p>';
	$html .= '<p>Votre compte téléphonique est prêt.</p>';
	$html .= '<ol>';
	$html .= '<li>Ouvrez <strong>Asaphone</strong> sur votre appareil</li>';
	$html .= '<li>Choisissez « Scanner un QR » ou « J\'ai déjà mes identifiants »</li>';
	$html .= '<li>Scannez le QR ci-dessous (valable ' . $ttlHours . ' h)</li>';
	$html .= '</ol>';
	$html .= '<p><img src="cid:qr-code" alt="QR provisionnement" style="max-width:280px;" /></p>';
	$html .= '<p>Extension : <strong>' . htmlspecialchars($extension, ENT_QUOTES, 'UTF-8') . '</strong><br>';
	$html .= 'Serveur : <strong>' . htmlspecialchars($server, ENT_QUOTES, 'UTF-8') . '</strong></p>';
	$html .= '<p>Lien direct (si scan impossible) :<br><a href="'
		. htmlspecialchars($claimUrl, ENT_QUOTES, 'UTF-8') . '">'
		. htmlspecialchars($claimUrl, ENT_QUOTES, 'UTF-8') . '</a></p>';
	$html .= '<p><em>Ce QR est personnel et à usage unique. Ne partagez pas ce message.</em></p>';

	provision_smtp_send_with_image($to, $subject, $html, $qrPath, 'qr-code');
}
