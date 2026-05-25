#!/bin/bash
# Orchestration Phase 4 : Fail2Ban → certificat PJSIP TLS → SRTP (1001–1010).
# Exécuter : sudo bash scripts/phase4-apply-all.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ $(id -u) -eq 0 ]] || { echo "Root requis." >&2; exit 1; }

echo "=== Fail2Ban (jail asterisk) ==="
bash "$ROOT/scripts/phase4-apply-fail2ban.sh"

echo "=== PJSIP TLS — certificat default (kvstore pjsipcertid) ==="
php "$ROOT/scripts/phase4-assign-pjsip-tls-cert.php"

echo "=== SRTP SDES — extensions 1001–1010 (attente fin reload précédent) ==="
sleep 20
php "$ROOT/scripts/phase4-enable-srtp-extensions.php"

echo "=== Terminé. Contrôles : ==="
echo "  sudo fail2ban-client status asterisk"
echo "  sudo asterisk -rx 'pjsip show transport 0.0.0.0-tls' | grep -E 'cert_file|priv_key'"
echo "  sudo ufw status numbered"
