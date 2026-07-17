<?php
declare(strict_types=1);

/** Chemins API relatifs à la base /provision. */
function provision_api_paths(): array {
	return [
		'register' => '/api/v1/register.php',
		'verify' => '/api/v1/verify.php',
		'claim' => '/api/v1/claim.php',
		'reconnect' => '/api/v1/reconnect.php',
		'session' => '/api/v1/session.php',
		'consume' => '/api/v1/consume.php',
		'voicemail_pending' => '/api/v1/voicemail/pending.php',
		'voicemail_listen' => '/api/v1/voicemail/listen.php',
		'chat_pending' => '/api/v1/chat/pending.php',
		'chat_read' => '/api/v1/chat/read.php',
		'groups_sync' => '/api/v1/groups/sync.php',
		'groups_list' => '/api/v1/groups/list.php',
		'conference_invite' => '/api/v1/conference/invite.php',
		'vpn_enroll' => '/api/v1/vpn/enroll.php',
		'vpn_status' => '/api/v1/vpn/status.php',
	];
}

/** Base URL API joignable par le client (Host de la requête ou IP LAN). */
function provision_request_api_base(): string {
	$host = $_SERVER['HTTP_HOST'] ?? '';
	if ($host !== '' && !str_contains($host, 'pbx.local')) {
		$scheme = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
		return rtrim("{$scheme}://{$host}/provision", '/');
	}
	$ip = provision_pbx_lan_ip();
	if ($ip !== '') {
		return "https://{$ip}/provision";
	}
	return provision_public_base_url();
}

function provision_session_sip_block(string $extension, array $credentials): array {
	$host = (string) ($credentials['server'] ?? provision_sip_server());
	return [
		'ext' => $extension,
		'secret' => $credentials['secret'],
		'host' => $host,
		'domain' => $host,
		'transport' => $credentials['transport'] ?? 'wss',
		'port' => (int) ($credentials['port'] ?? provision_env('PROVISION_WSS_PORT', '8089')),
		'wss_url' => $credentials['wss_url'] ?? provision_wss_url(),
		'sip_uri' => "sip:{$extension}@{$host}",
		'registrar_uri' => "sip:{$host}",
		'pbx_host' => provision_env('PROVISION_PBX_HOST', 'pbx.local'),
		'pbx_lan_ip' => provision_pbx_lan_ip(),
	];
}

/**
 * Bundle final pour Asaphone : token jti + SIP/WSS (IP LAN) + ICE + URLs API.
 * À appeler après register/verify/claim ou en login ext+secret (reconnect).
 */
function provision_format_session(array $redeliver): array {
	$credentials = $redeliver['credentials'];
	$ext = (string) $credentials['ext'];
	$apiBase = provision_request_api_base();
	$paths = provision_api_paths();

	$endpoints = [];
	foreach ($paths as $name => $path) {
		$endpoints[$name] = $apiBase . $path;
	}

	$db = provision_pdo();
	$groups = provision_groups_list_for_ext($db, $ext);
	$conference = provision_conference_payload();

	return [
		'reconnect' => (bool) ($redeliver['reconnect'] ?? false),
		'jti' => $redeliver['jti'],
		'expires' => $redeliver['expires'] ?? null,
		'credentials' => $credentials,
		'sip' => provision_session_sip_block($ext, $credentials),
		'media' => [
			'webrtc' => (bool) ($credentials['webrtc'] ?? true),
			'video' => (bool) ($credentials['video'] ?? true),
			'codecs' => $credentials['codecs'] ?? provision_codecs(),
			'video_codecs' => $credentials['video_codecs'] ?? provision_video_codecs(),
			'ice_servers' => $credentials['ice_servers'] ?? provision_ice_servers(),
			'wss_url' => $credentials['wss_url'] ?? provision_wss_url(),
		],
		'voicemail' => [
			'vm_code' => $credentials['vm_code'] ?? null,
			'vm_pin' => $credentials['vm_pin'] ?? null,
			'jti_header' => 'X-Provision-Jti',
		],
		'conference' => $conference,
		'groups' => $groups,
		'item_maps' => [
			'group_id' => 'id',
			'group_call_uri' => 'call_uri',
			'group_dial' => 'dial',
		],
		'api' => [
			'base_url' => $apiBase,
			'discovery_url' => provision_discovery_url(),
			'public_base_url' => provision_public_base_url(),
			'endpoints' => $endpoints,
			'group_call' => $conference['default_call_uri'],
		],
		'claim_token' => $redeliver['claim_token'] ?? null,
		'claim_url' => $redeliver['claim_url'] ?? null,
	];
}

function provision_open_session(PDO $db, string $extension, string $secret): array {
	$redeliver = provision_redeliver_session($db, $extension, $secret);
	return provision_format_session($redeliver);
}

function provision_open_session_from_claim(PDO $db, string $claimToken): array {
	$result = provision_claim_credentials($db, $claimToken);
	$redeliver = [
		'reconnect' => false,
		'jti' => $result['jti'],
		'credentials' => $result['credentials'],
		'expires' => null,
		'claim_token' => $claimToken,
		'claim_url' => provision_build_claim_url($claimToken),
	];
	return provision_format_session($redeliver);
}

/** URL HTTPS one-shot → handshake SIP (contexte VPN / public, sans ext+secret). */
function provision_build_session_url(string $claimToken): string {
	return provision_request_api_base() . '/api/v1/session.php?token=' . rawurlencode($claimToken);
}

function provision_build_session_deeplink(string $claimToken): string {
	$scheme = provision_env('PROVISION_QR_SCHEME', 'asaphone');
	return $scheme . '://session?url=' . rawurlencode(provision_build_session_url($claimToken));
}

/**
 * Émet (ou réutilise) un token claim SIP pour l’e-mail — lien d’auth comme register/verify.
 * Utilisé après vpn/verify (4G) ou dans la réponse verify SIP pour l’app.
 */
function provision_issue_session_links_for_email(PDO $db, string $email): ?array {
	$req = provision_get_request_by_email($db, $email);
	if (!$req || empty($req['extension'])) {
		return null;
	}
	if (!in_array($req['status'], ['verified', 'pending_admin', 'provisioned'], true)) {
		return null;
	}

	$ext = (string) $req['extension'];
	$active = provision_get_active_token($db, $email, $ext);
	if ($active !== null) {
		provision_validate_token_claim($db, $active);
		$claimToken = (string) $active['claim_token'];
		$expires = (new DateTimeImmutable($active['expires']))->format(DateTimeInterface::ATOM);
	} else {
		$tokenData = provision_create_token($db, $email, $ext);
		$claimToken = (string) $tokenData['claim_token'];
		$expires = (string) $tokenData['expires'];
	}

	return [
		'session_token' => $claimToken,
		'session_url' => provision_build_session_url($claimToken),
		'session_deeplink' => provision_build_session_deeplink($claimToken),
		'claim_url' => provision_build_claim_url($claimToken),
		'qr_content' => provision_build_qr_content($claimToken),
		'extension' => $ext,
		'expires' => $expires,
	];
}

/** Champs session_* à fusionner dans les réponses verify / vpn. */
function provision_session_links_payload(?array $links): array {
	if ($links === null) {
		return [];
	}
	return [
		'session_token' => $links['session_token'],
		'session_url' => $links['session_url'],
		'session_deeplink' => $links['session_deeplink'],
		'claim_url' => $links['claim_url'],
		'extension' => $links['extension'],
		'session_expires' => $links['expires'],
	];
}
