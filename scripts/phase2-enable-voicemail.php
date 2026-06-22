#!/usr/bin/env php
<?php
/**
 * Active la messagerie (default) pour 1001-1010, pièce jointe WAV, email à renseigner en GUI.
 * sudo php /home/asaph/Documents/serveur/scripts/phase2-enable-voicemail.php
 */
if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Exécuter en root.\n");
	exit(1);
}
include '/etc/freepbx.conf';

$vm = \FreePBX::Voicemail();
$db = \FreePBX::Database();
$sounds = '/var/lib/asterisk/sounds/en';
$greetFiles = [
	'greet'   => "$sounds/vm-theperson.gsm",
	'unavail' => "$sounds/vm-isunavail.gsm",
	'busy'    => "$sounds/vm-rec-busy.gsm",
];

for ($e = 1001; $e <= 1010; $e++) {
	$ext = (string) $e;
	$vmpwd = substr(str_pad($ext, 4, '0', STR_PAD_LEFT), -4);
	$vm->addMailbox($ext, [
		'vm'         => 'enabled',
		'name'       => "Poste $ext",
		'vmpwd'      => $vmpwd,
		'email'      => '',
		'passlogin'  => 'passlogin=no',
		'attach'     => 'attach=no',
		'envelope'   => 'envelope=yes',
		'vmdelete'   => 'vmdelete=no',
		'saycid'     => 'saycid=yes',
		'options'    => 'forcename=no|forcegreetings=no',
	]);
	$sth = $db->prepare('UPDATE users SET voicemail = ? WHERE extension = ?');
	$sth->execute(['default', $ext]);
	$vm->mapMailBox($ext);
	$spool = "/var/spool/asterisk/voicemail/default/$ext";
	foreach (['', 'INBOX', 'Old', 'Work', 'Friends', 'Family', 'Urgent'] as $sub) {
		$dir = $sub === '' ? $spool : "$spool/$sub";
		if (!is_dir($dir)) {
			mkdir($dir, 0755, true);
		}
	}
	if (is_dir($spool)) {
		foreach ($greetFiles as $name => $src) {
			if (is_file($src)) {
				copy($src, "$spool/$name.gsm");
				chmod("$spool/$name.gsm", 0644);
				foreach (['wav', 'WAV', 'g722'] as $bad) {
					@unlink("$spool/$name.$bad");
				}
			}
		}
	}
	exec('chown -R asterisk:asterisk ' . escapeshellarg($spool));
	echo "Messagerie $ext (PIN $vmpwd, code *81" . substr($ext, 1) . ", init OK)\n";
}

echo "fwconsole reload requis.\n";
