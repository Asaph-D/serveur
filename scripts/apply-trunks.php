#!/usr/bin/env php
<?php
/**
 * Crée/active les trunks PJSIP, routes sortantes et entrantes FreePBX.
 * Exécuter : sudo php /home/asaph/Documents/serveur/scripts/apply-trunks.php
 */
declare(strict_types=1);

if (!is_readable('/etc/freepbx.conf')) {
	fwrite(STDERR, "Fichier /etc/freepbx.conf introuvable.\n");
	exit(1);
}
if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Exécuter en root : sudo php ...\n");
	exit(1);
}

$root = dirname(__DIR__);
$cfg = $root . '/network/trunks.env';
$secrets = '/root/trunks-secrets.env';

if (!is_readable($cfg)) {
	fwrite(STDERR, "Config introuvable: $cfg\n");
	exit(1);
}

function load_env_file(string $path): array {
	$out = [];
	foreach (file($path, FILE_IGNORE_NEW_LINES) as $line) {
		$line = trim($line);
		if ($line === '' || $line[0] === '#') {
			continue;
		}
		if (!str_contains($line, '=')) {
			continue;
		}
		[$k, $v] = explode('=', $line, 2);
		$out[trim($k)] = trim($v, " \t\"'");
	}
	return $out;
}

function env_val(array $env, string $key, string $default = ''): string {
	return $env[$key] ?? $default;
}

function is_placeholder_secret(string $v): bool {
	$v = trim($v);
	return $v === '' || preg_match('/^(CHANGE|VOTRE|XXX|TODO|placeholder)/i', $v);
}

function trunk_by_name(PDO $db, string $name): ?array {
	$sth = $db->prepare('SELECT * FROM trunks WHERE name = ? LIMIT 1');
	$sth->execute([$name]);
	$row = $sth->fetch(PDO::FETCH_ASSOC);
	return $row ?: null;
}

function route_by_name(PDO $db, string $name): ?array {
	$sth = $db->prepare('SELECT * FROM outbound_routes WHERE name = ? LIMIT 1');
	$sth->execute([$name]);
	$row = $sth->fetch(PDO::FETCH_ASSOC);
	return $row ?: null;
}

function did_exists(PDO $db, string $extension, string $cidnum): bool {
	$sth = $db->prepare('SELECT 1 FROM incoming WHERE extension = ? AND cidnum = ? LIMIT 1');
	$sth->execute([$extension, $cidnum]);
	return (bool) $sth->fetchColumn();
}

function build_pjsip_post(array $env, array $secrets, string $kind): array {
	$codecs = [];
	foreach (explode(',', env_val($env, $kind === 'pstn' ? 'PSTN_CODECS' : 'PSTN_CODECS', 'ulaw,alaw,g722')) as $c) {
		$c = trim($c);
		if ($c !== '') {
			$codecs[$c] = '1';
		}
	}

	$defaults = [
		'retry_interval' => '60',
		'max_retries' => '10000',
		'expiration' => '3600',
		'qualify_frequency' => '60',
		'auth_rejection_permanent' => 'off',
		'pjsip_line' => 'false',
		'send_connected_line' => 'yes',
	];

	if ($kind === 'pstn') {
		$server = env_val($env, 'PSTN_SIP_SERVER');
		$port = env_val($env, 'PSTN_SIP_PORT', '5060');
		$user = env_val($secrets, 'PSTN_USERNAME');
		$secret = env_val($secrets, 'PSTN_SECRET');
		$channel = env_val($env, 'PSTN_TRUNK_CHANNELID', 'trunk-operateur-pstn');
		return array_merge($defaults, [
			'channelid' => $channel,
			'trunk_name' => $channel,
			'username' => $user,
			'auth_username' => $user,
			'secret' => $secret,
			'sip_server' => $server,
			'sip_server_port' => $port,
			'transport' => env_val($env, 'PSTN_TRANSPORT', '0.0.0.0-udp'),
			'registration' => env_val($env, 'PSTN_REGISTRATION', 'send'),
			'authentication' => env_val($env, 'PSTN_AUTHENTICATION', 'outbound'),
			'context' => env_val($env, 'PSTN_CONTEXT', 'from-pstn'),
			'codec' => $codecs,
			'dtmfmode' => 'rfc4733',
			'direct_media' => 'no',
			'disabletrunk' => (is_placeholder_secret($user) || is_placeholder_secret($secret)) ? 'on' : 'off',
		]);
	}

	$host = env_val($env, 'INTERPBX_REMOTE_HOST');
	$match = env_val($env, 'INTERPBX_MATCH_IP');
	$user = env_val($secrets, 'INTERPBX_USERNAME');
	$secret = env_val($secrets, 'INTERPBX_SECRET');
	$port = env_val($env, 'INTERPBX_SIP_PORT', '5060');
	$ready = ($match !== '' || $host !== '');
	$channel = env_val($env, 'INTERPBX_CHANNELID', 'trunk-interpbx-site-b');

	return array_merge($defaults, [
		'channelid' => $channel,
		'trunk_name' => $channel,
		'username' => $user,
		'auth_username' => $user,
		'secret' => $secret,
		'sip_server' => $host !== '' ? $host : '0.0.0.0',
		'sip_server_port' => $port,
		'transport' => env_val($env, 'INTERPBX_TRANSPORT', '0.0.0.0-udp'),
		'registration' => env_val($env, 'INTERPBX_REGISTRATION', 'receive'),
		'authentication' => env_val($env, 'INTERPBX_AUTHENTICATION', 'inbound'),
		'context' => env_val($env, 'INTERPBX_CONTEXT', 'from-pstn'),
		'match' => trim(preg_replace('/\s+/', ',', $match)),
		'codec' => $codecs,
		'dtmfmode' => 'rfc4733',
		'direct_media' => 'no',
		'disabletrunk' => $ready ? 'off' : 'on',
	]);
}

function create_or_update_trunk(\FreePBX\modules\Core $core, PDO $db, string $name, string $tech, array $settings, array $post): int {
	$existing = trunk_by_name($db, $name);
	$_POST = array_merge($_POST, $post);
	$settings = array_merge($settings, [
		'name' => $name,
		'tech' => $tech,
		'outcid' => $settings['outcid'] ?? '',
		'keepcid' => 'off',
		'maxchans' => '',
		'failtrunk' => '',
		'dialoutprefix' => '',
		'usercontext' => '',
		'provider' => '',
		'continue' => 'off',
		'dialopts' => false,
		'disabletrunk' => $post['disabletrunk'] ?? 'off',
	]);

	if ($existing) {
		$settings['trunknum'] = (string) $existing['trunkid'];
		$core->deleteTrunk((int) $existing['trunkid'], $tech, true);
		$id = (int) $core->addTrunk($name, $tech, $settings, true);
		echo "MAJ trunk $name (id=$id)\n";
	} else {
		$id = (int) $core->addTrunk($name, $tech, $settings, false);
		echo "OK trunk $name (id=$id)\n";
	}

	$disabled = ($post['disabletrunk'] ?? 'off') === 'on' ? 'on' : 'off';
	$fix = $db->prepare('UPDATE trunks SET disabled = ? WHERE trunkid = ?');
	$fix->execute([$disabled, $id]);

	return $id;
}

function ensure_outbound_route($routing, PDO $db, string $name, array $patterns, array $trunkIds, int $seq = 0): int {
	$existing = route_by_name($db, $name);
	if ($existing) {
		$routeId = (int) $existing['route_id'];
		$routing->updatePatterns($routeId, $patterns, true);
		$routing->updateTrunks($routeId, $trunkIds, true);
		$routing->setOrder($routeId, (string) $seq);
		echo "MAJ route sortante $name (id=$routeId)\n";
		return $routeId;
	}

	$routeId = (int) $routing->add(
		$name,
		'',
		'',
		'',
		'NO',
		'NO',
		'default',
		'',
		$patterns,
		$trunkIds,
		(string) $seq
	);
	echo "OK route sortante $name (id=$routeId)\n";
	return $routeId;
}

include '/etc/freepbx.conf';

$env = load_env_file($cfg);
if (env_val($env, 'TRUNKS_ENABLE', 'yes') !== 'yes') {
	echo "TRUNKS_ENABLE != yes — rien à faire.\n";
	exit(0);
}

$secretEnv = is_readable($secrets) ? load_env_file($secrets) : [];
$core = \FreePBX::Core();
$db = \FreePBX::Database();
$routing = new \FreePBX\modules\Core\Components\Outboundrouting();

$pstnPost = build_pjsip_post($env, $secretEnv, 'pstn');
$interpbxPost = build_pjsip_post($env, $secretEnv, 'interpbx');

$pstnId = create_or_update_trunk(
	$core,
	$db,
	env_val($env, 'PSTN_TRUNK_NAME', 'trunk-operateur-pstn'),
	'pjsip',
	['outcid' => env_val($env, 'PSTN_OUTCID')],
	$pstnPost
);

$interpbxId = create_or_update_trunk(
	$core,
	$db,
	env_val($env, 'INTERPBX_TRUNK_NAME', 'trunk-interpbx-site-b'),
	'pjsip',
	['outcid' => ''],
	$interpbxPost
);

$prefix = preg_replace('/[^0-9]/', '', env_val($env, 'INTERPBX_PREFIX', '8'));
$interpbxPattern = $prefix . 'X.';

ensure_outbound_route($routing, $db, env_val($env, 'ROUTE_FRANCE_NAME', 'France-metropole'), [
	['match_pattern_prefix' => '', 'match_pattern_pass' => '0XXXXXXXXX', 'match_cid' => '', 'prepend_digits' => ''],
], [$pstnId], 0);

ensure_outbound_route($routing, $db, env_val($env, 'ROUTE_INTERNATIONAL_NAME', 'International'), [
	['match_pattern_prefix' => '', 'match_pattern_pass' => '00.', 'match_cid' => '', 'prepend_digits' => ''],
], [$pstnId], 1);

ensure_outbound_route($routing, $db, env_val($env, 'ROUTE_INTERPBX_NAME', 'Inter-PBX-site-B'), [
	['match_pattern_prefix' => '', 'match_pattern_pass' => $interpbxPattern, 'match_cid' => '', 'prepend_digits' => ''],
], [$interpbxId], 2);

$inboundDest = env_val($env, 'INBOUND_DEFAULT_DEST', 'from-internal,7000,1');
$did = env_val($env, 'INBOUND_DID');

if ($did !== '' && !did_exists($db, $did, '')) {
	$core->addDID([
		'extension' => $did,
		'cidnum' => '',
		'description' => env_val($env, 'INBOUND_DID_DESCRIPTION', 'DID opérateur principal'),
		'destination' => $inboundDest,
	]);
	echo "OK route entrante DID $did\n";
} elseif ($did !== '') {
	echo "Route entrante DID $did déjà présente\n";
}

if (!did_exists($db, '', '')) {
	$core->addDID([
		'extension' => '',
		'cidnum' => '',
		'description' => env_val($env, 'INBOUND_CATCHALL_DESCRIPTION', 'Appels entrants trunk (catch-all)'),
		'destination' => $inboundDest,
	]);
	echo "OK route entrante catch-all (tous DID)\n";
} else {
	echo "Route entrante catch-all déjà présente\n";
}

if ($pstnPost['disabletrunk'] === 'on') {
	echo "INFO: trunk PSTN créé mais DÉSACTIVÉ — renseigner PSTN_USERNAME/PSTN_SECRET dans /root/trunks-secrets.env\n";
}
if ($interpbxPost['disabletrunk'] === 'on') {
	echo "INFO: trunk inter-PBX créé mais DÉSACTIVÉ — renseigner INTERPBX_MATCH_IP ou INTERPBX_REMOTE_HOST dans network/trunks.env\n";
}

echo "Terminé. Exécuter : sudo fwconsole reload\n";
