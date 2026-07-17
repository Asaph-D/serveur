#!/usr/bin/env bash
# Spool messagerie vocale : propriétaire asterisk (lockfiles INBOX).
# FreePBX / startup peuvent remettre www-data — relancer après fwconsole start.
# Usage : sudo bash scripts/fix-voicemail-spool-perms.sh
set -euo pipefail

AST_USER="${FREEPBX_AST_USER:-asterisk}"
AST_GROUP="${FREEPBX_AST_GROUP:-asterisk}"
VM_SPOOL="/var/spool/asterisk/voicemail"

if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

[[ -d "$VM_SPOOL" ]] || { echo "Absent : $VM_SPOOL" >&2; exit 1; }

echo "Voicemail spool → ${AST_USER}:${AST_GROUP}"
chown -R "${AST_USER}:${AST_GROUP}" "$VM_SPOOL"
find "$VM_SPOOL" -type d -exec chmod 2775 {} +
find "$VM_SPOOL" -type f -exec chmod 664 {} + 2>/dev/null || true

# Parent spool : traversable par asterisk
if [[ -d /var/spool/asterisk ]]; then
	chown "${AST_USER}:${AST_GROUP}" /var/spool/asterisk
	chmod 2775 /var/spool/asterisk
fi

# Test écriture
sudo -u "$AST_USER" touch "${VM_SPOOL}/default/.perm-test"
rm -f "${VM_SPOOL}/default/.perm-test"
echo "OK — asterisk peut écrire dans ${VM_SPOOL}"
