#!/usr/bin/env php
<?php
/**
 * Corrige les fichiers greet/unavail/busy (gsm) pour 1001-1010.
 * sudo php scripts/fix-voicemail-greetings.php
 */
if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Exécuter en root.\n");
	exit(1);
}

$sounds = '/var/lib/asterisk/sounds/en';
$map = [
	'greet'   => "$sounds/vm-theperson.gsm",
	'unavail' => "$sounds/vm-isunavail.gsm",
	'busy'    => "$sounds/vm-rec-busy.gsm",
];

foreach ($map as $name => $src) {
	if (!is_file($src)) {
		fwrite(STDERR, "Son manquant : $src\n");
		exit(1);
	}
}

for ($e = 1001; $e <= 1010; $e++) {
	$ext = (string) $e;
	$spool = "/var/spool/asterisk/voicemail/default/$ext";
	if (!is_dir($spool)) {
		mkdir($spool, 0755, true);
	}
	foreach ($map as $name => $src) {
		copy($src, "$spool/$name.gsm");
		chmod("$spool/$name.gsm", 0644);
		foreach (['wav', 'WAV', 'g722', 'ulaw', 'alaw'] as $bad) {
			@unlink("$spool/$name.$bad");
		}
	}
	exec('chown -R asterisk:asterisk ' . escapeshellarg($spool));
	echo "Greetings GSM OK : $ext\n";
}

echo "Terminé. Test : appeler un poste offline → messagerie doit répondre.\n";
