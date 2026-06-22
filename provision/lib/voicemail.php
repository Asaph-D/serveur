<?php
declare(strict_types=1);

/**
 * Initialise une boîte vocale FreePBX (sans tutoriel « nouvel utilisateur »).
 * Appelé à l’attribution d’extension Asaphone.
 */
function provision_init_voicemail_mailbox(string $extension, ?string $email = null): void {
	if (!file_exists('/etc/freepbx.conf')) {
		return;
	}

	// bootstrap FreePBX lit global $amp_conf — inclure freepbx.conf hors portée locale
	global $amp_conf;
	if (!isset($amp_conf['AMPDBUSER'])) {
		include_once '/etc/freepbx.conf';
	}

	$ext = preg_replace('/\D/', '', $extension);
	if ($ext === '' || (int) $ext < 1001 || (int) $ext > 1010) {
		return;
	}

	try {
		provision_init_voicemail_mailbox_freepbx($ext, $email);
	} catch (Throwable $e) {
		error_log('provision: voicemail init ' . $ext . ' ignoré — ' . $e->getMessage());
	}
}

function provision_init_voicemail_mailbox_freepbx(string $ext, ?string $email): void {
	$vm = \FreePBX::Voicemail();
	$db = \FreePBX::Database();
	$vmpwd = provision_vm_pin($ext);
	$vmCode = provision_vm_access_code($ext);

	$settings = [
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
	];

	$vm->addMailbox($ext, $settings);
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
	provision_voicemail_ensure_default_greeting($spool);

	@exec('chown -R asterisk:asterisk ' . escapeshellarg($spool));
	@exec('asterisk -rx "voicemail reload" 2>/dev/null');

	error_log("provision: voicemail init $ext (code $vmCode, email=" . ($email ?? '') . ')');
}

function provision_voicemail_ensure_default_greeting(string $spool): void {
	if (file_exists("$spool/greet.gsm")) {
		return;
	}
	$templates = [
		'greet'   => '/var/lib/asterisk/sounds/en/vm-theperson.gsm',
		'unavail' => '/var/lib/asterisk/sounds/en/vm-isunavail.gsm',
		'busy'    => '/var/lib/asterisk/sounds/en/vm-rec-busy.gsm',
	];
	foreach ($templates as $name => $src) {
		if (is_file($src)) {
			@copy($src, "$spool/$name.gsm");
			@chmod("$spool/$name.gsm", 0644);
		}
	}
}
