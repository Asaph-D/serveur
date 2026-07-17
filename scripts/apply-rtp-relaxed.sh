#!/usr/bin/env bash
# Ajuste RTP Asterisk (custom) pour WebRTC/NAT.
# Usage: sudo bash scripts/apply-rtp-relaxed.sh
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "Root requis : sudo bash $0" >&2
  exit 1
fi

cat > /etc/asterisk/rtp_custom.conf <<'EOF'
[general]
; WebRTC / NAT : accepter source RTP qui change (évite "No audio available")
strictrtp=no
EOF

chown www-data:asterisk /etc/asterisk/rtp_custom.conf 2>/dev/null || chown asterisk:asterisk /etc/asterisk/rtp_custom.conf 2>/dev/null || true
chmod 664 /etc/asterisk/rtp_custom.conf 2>/dev/null || true

asterisk -rx "module reload res_rtp_asterisk.so" >/dev/null 2>&1 || true
asterisk -rx "rtp show settings" 2>/dev/null | sed -n '1,40p' || true
