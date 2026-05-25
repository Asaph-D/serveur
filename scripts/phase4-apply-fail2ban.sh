#!/bin/bash
# Installe la jail Asterisk Fail2Ban Phase 4 (FreePBX).
# Exécuter : sudo bash scripts/phase4-apply-fail2ban.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi
if ! command -v fail2ban-client >/dev/null; then
	apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban
fi
install -d /etc/fail2ban/jail.d
install -m 0644 "$ROOT/phase4/fail2ban/jail.d/asterisk-freepbx.local" /etc/fail2ban/jail.d/asterisk-freepbx.local
systemctl enable --now fail2ban
fail2ban-client reload
fail2ban-client status asterisk
echo "OK — vérifier : sudo fail2ban-client status asterisk"
