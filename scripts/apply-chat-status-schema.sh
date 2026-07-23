#!/usr/bin/env bash
# Applique colonnes client_id / read_at pour les accusés chat.
set -euo pipefail
[[ $(id -u) -eq 0 ]] || { echo "Root requis"; exit 1; }
php -r '
include "/etc/freepbx.conf";
$db = \FreePBX::Database();
$stmts = [
	"ALTER TABLE provision_chat_messages ADD COLUMN client_id VARCHAR(64) NULL DEFAULT NULL AFTER body",
	"ALTER TABLE provision_chat_messages ADD COLUMN read_at DATETIME NULL DEFAULT NULL AFTER delivered_at",
	"ALTER TABLE provision_chat_messages ADD INDEX idx_chat_from_client (from_ext, client_id)",
	"ALTER TABLE provision_chat_messages ADD INDEX idx_chat_from_id (from_ext, id)",
];
foreach ($stmts as $s) {
	try {
		$db->exec($s);
		echo "OK: $s\n";
	} catch (Throwable $e) {
		echo "SKIP: " . $e->getMessage() . "\n";
	}
}
'
echo "Schema chat status OK."
