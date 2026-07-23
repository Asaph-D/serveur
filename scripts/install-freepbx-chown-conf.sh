#!/usr/bin/env bash
# Installe freepbx_chown.conf pour protéger le spool messagerie de fwconsole chown.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="/etc/asterisk/freepbx_chown.conf"
install -m 0644 "$ROOT/apache/freepbx_chown.conf" "$DST"
chown www-data:asterisk "$DST" 2>/dev/null || true
echo "OK: $DST"
