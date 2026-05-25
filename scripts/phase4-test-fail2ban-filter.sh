#!/bin/bash
# Test rapide du filtre Fail2Ban asterisk (fichier full souvent énorme → extrait).
set -euo pipefail
LINES="${1:-2000}"
TMP=$(mktemp /tmp/asterisk-f2b-test.XXXXXX.log)
trap 'rm -f "$TMP"' EXIT
sudo tail -n "$LINES" /var/log/asterisk/full > "$TMP"
echo "Extrait : $LINES dernières lignes → $TMP ($(wc -c < "$TMP") octets)"
echo "=== Résumé ==="
sudo fail2ban-regex "$TMP" /etc/fail2ban/filter.d/asterisk.conf
echo ""
echo "Pour le détail des lignes matchées : sudo fail2ban-regex \"$TMP\" /etc/fail2ban/filter.d/asterisk.conf -v"
