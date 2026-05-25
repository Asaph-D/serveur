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

for ($e = 1001; $e <= 1010; $e++) {
	$ext = (string) $e;
	$vmpwd = substr(str_pad($ext, 4, '0', STR_PAD_LEFT), -4);
	$vm->addMailbox($ext, [
		'vm'         => 'enabled',
		'name'       => "Poste $ext",
		'vmpwd'      => $vmpwd,
		'email'      => '',
		'passlogin'  => 'passlogin=no',
		'attach'     => 'attach=yes',
		'envelope'   => 'envelope=yes',
		'vmdelete'   => 'vmdelete=no',
		'saycid'     => 'saycid=yes',
	]);
	$sth = $db->prepare('UPDATE users SET voicemail = ? WHERE extension = ?');
	$sth->execute(['default', $ext]);
	$vm->mapMailBox($ext);
	echo "Messagerie $ext (PIN $vmpwd)\n";
}

echo "fwconsole reload requis.\n";
