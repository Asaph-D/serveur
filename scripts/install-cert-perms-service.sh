#!/bin/bash
# Installe un service systemd qui exécute fix-cert-perms.sh au démarrage.
# Usage :
#   sudo bash /home/asaph/Documents/serveur/scripts/install-cert-perms-service.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/scripts/fix-cert-perms.sh"
DST="/usr/local/sbin/fix-cert-perms.sh"

[[ $(id -u) -eq 0 ]] || { echo "Root requis." >&2; exit 1; }
[[ -f "$SRC" ]] || { echo "Script introuvable: $SRC" >&2; exit 1; }

install -m 0755 "$SRC" "$DST"

cat > /etc/systemd/system/freepbx-cert-perms.service <<'UNIT'
[Unit]
Description=Normalise permissions FreePBX Certman (/etc/asterisk/keys)
After=network.target

[Service]
Type=oneshot
Environment=KEY_MODE=0640
Environment=CERT_GROUP=asterisk
ExecStart=/usr/local/sbin/fix-cert-perms.sh

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now freepbx-cert-perms.service
systemctl status freepbx-cert-perms.service --no-pager -l || true
echo "OK: service freepbx-cert-perms.service activé."

