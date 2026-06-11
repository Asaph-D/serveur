<?php
declare(strict_types=1);

function provision_freepbx_db_config(): array {
	static $cfg = null;
	if ($cfg !== null) {
		return $cfg;
	}

	$path = '/etc/freepbx.conf';
	if (!is_readable($path)) {
		throw new RuntimeException('FreePBX non configuré (/etc/freepbx.conf)');
	}

	$content = file_get_contents($path);
	if ($content === false) {
		throw new RuntimeException('Impossible de lire /etc/freepbx.conf');
	}

	$out = [
		'host' => 'localhost',
		'db' => 'asterisk',
		'user' => 'freepbxuser',
		'pass' => '',
	];

	if (preg_match_all("/\\['([^']+)'\\]\\s*=\\s*'([^']*)'\\s*;/", $content, $matches, PREG_SET_ORDER)) {
		foreach ($matches as $match) {
			switch ($match[1]) {
				case 'AMPDBHOST':
					$out['host'] = $match[2];
					break;
				case 'AMPDBNAME':
					$out['db'] = $match[2];
					break;
				case 'AMPDBUSER':
					$out['user'] = $match[2];
					break;
				case 'AMPDBPASS':
					$out['pass'] = $match[2];
					break;
			}
		}
	}

	$cfg = $out;
	return $cfg;
}

function provision_pdo(): PDO {
	static $pdo = null;
	if ($pdo instanceof PDO) {
		return $pdo;
	}

	$dbCfg = provision_freepbx_db_config();
	$dsn = "mysql:host={$dbCfg['host']};dbname={$dbCfg['db']};charset=utf8mb4";
	$pdo = new PDO($dsn, $dbCfg['user'], $dbCfg['pass'], [
		PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
		PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
	]);
	return $pdo;
}
