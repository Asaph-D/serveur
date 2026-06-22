#!/usr/bin/env php
<?php
/**
 * Politique messagerie : pas d’e-mail WAV, notification Asaphone (externnotify).
 * sudo php scripts/apply-voicemail-policy.php
 */
if (posix_geteuid() !== 0) {
	fwrite(STDERR, "Exécuter en root.\n");
	exit(1);
}
include '/etc/freepbx.conf';

$vm = \FreePBX::Voicemail();
$vmconf = $vm->getVoicemail(false);

$notifyScript = '/usr/local/bin/asaphone-vm-notify';

$vmconf['general']['forcename'] = 'no';
$vmconf['general']['forcegreetings'] = 'no';
$vmconf['general']['externnotify'] = $notifyScript;
$vmconf['general']['attach'] = 'no';
unset($vmconf['general']['emailbody'], $vmconf['general']['emailsubject']);

foreach ($vmconf['default'] ?? [] as $ext => $data) {
	if (!is_numeric($ext)) {
		continue;
	}
	$vmconf['default'][$ext]['email'] = '';
	$vmconf['default'][$ext]['pager'] = '';
	$opts = $vmconf['default'][$ext]['options'] ?? [];
	$opts['attach'] = 'no';
	$opts['forcename'] = 'no';
	$opts['forcegreetings'] = 'no';
	$vmconf['default'][$ext]['options'] = $opts;
}

$vm->saveVoicemail($vmconf);

if (is_file($notifyScript)) {
	chmod($notifyScript, 0755);
	chown($notifyScript, 'www-data');
}

echo "Politique VM : pas d'e-mail WAV, externnotify → $notifyScript\n";
echo "fwconsole reload requis.\n";
