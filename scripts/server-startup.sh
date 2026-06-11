#!/bin/bash
set -euo pipefail

LOG_FILE="${LOG_FILE:-/var/log/serveur-startup.log}"

if [[ $(id -u) -ne 0 ]]; then
  echo "ERREUR: ce script doit être exécuté en root (ex. via systemd)." >&2
  exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
chmod 0644 "$LOG_FILE" || true

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== serveur-startup: $(date -Is) ==="

if command -v fwconsole >/dev/null 2>&1; then
  echo "== fwconsole start =="
  fwconsole start
else
  echo "WARN: fwconsole introuvable, étape ignorée." >&2
fi

echo "== nettoyage sessions PHP + perms =="
rm -f /var/lib/php/sessions/sess_* 2>/dev/null || true
chown root:root /var/lib/php/sessions
chmod 1733 /var/lib/php/sessions
ls -ld /var/lib/php/sessions

echo "== restart apache2 + status (60 lignes) =="
systemctl restart apache2 2>&1
systemctl --no-pager --full status apache2 2>&1 | sed -n '1,60p'

echo "== apply site network profile =="
bash /home/asaph/Documents/serveur/scripts/net-apply-site.sh

echo "== fix cert permissions =="
bash /home/asaph/Documents/serveur/scripts/fix-cert-perms.sh

echo "== enable apache HTTPS (443) =="
bash /home/asaph/Documents/serveur/scripts/enable-apache-https.sh

echo "=== serveur-startup: OK $(date -Is) ==="
