#!/usr/bin/env bash
# Ajuste RTP Asterisk pour WebRTC/NAT via FreePBX Sipsettings (persistant).
# Suit l'IP DHCP actuelle (LAN maison ou hotspot) — ne pas figer 192.168.1.80.
#
# Usage:
#   sudo bash scripts/apply-rtp-relaxed.sh           # Sipsettings + fwconsole reload
#   sudo bash scripts/apply-rtp-relaxed.sh --quick   # sans fwconsole (boot / sync IP)
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "Root requis : sudo bash $0" >&2
  exit 1
fi

QUICK=0
[[ "${1:-}" == "--quick" ]] && QUICK=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/network/global-config.env" 2>/dev/null || true
# shellcheck source=scripts/lib/detect-mgmt-network.sh
source "$ROOT/scripts/lib/detect-mgmt-network.sh"

LAN_IP=""
if [[ -n "${MGMT_IFACE:-}" ]] && detect_mgmt_network "$MGMT_IFACE"; then
  LAN_IP="$PBX_LAN_IP"
fi
if [[ -z "$LAN_IP" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/network/global-config.env" 2>/dev/null || true
  LAN_IP="${PBX_LAN_IP:-}"
fi
if [[ -z "$LAN_IP" ]]; then
  LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi
if [[ -z "$LAN_IP" || ! "$LAN_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "ERREUR: IP LAN introuvable (MGMT_IFACE=${MGMT_IFACE:-?})" >&2
  exit 1
fi

echo "apply-rtp-relaxed: ice_host + media pin → ${LAN_IP} (quick=${QUICK})"

# LAN host-only ICE : pas de stunaddr Asterisk (checks ICE peer = STUN binding).
# Les clients gardent stun:PBX_LAN_IP:3478 via bootstrap.
php -r "
include '/etc/freepbx.conf';
\$ss = FreePBX::Sipsettings();
\$ss->setConfig('stunaddr', '');
\$ss->setConfig('webrtcstunaddr', '');
\$ss->setConfig('strictrtp', 'No');
\$ss->setConfig('ice-blacklist', [
  ['address' => '10.10.10.0', 'subnet' => '24'],
  ['address' => '10.200.0.0', 'subnet' => '24'],
  ['address' => '172.16.0.0', 'subnet' => '12'],
  ['address' => '192.168.58.0', 'subnet' => '24'],
  ['address' => '192.168.67.0', 'subnet' => '24'],
  ['address' => '127.0.0.0', 'subnet' => '8'],
  ['address' => 'fe80::', 'subnet' => '10'],
]);
\$ss->setConfig('ice-host-candidates', [
  ['local' => '${LAN_IP}', 'advertised' => '${LAN_IP}'],
]);
echo 'ice-host=' . '${LAN_IP}' . '=>' . '${LAN_IP}' . PHP_EOL;
echo 'stunaddr=[' . \$ss->getConfig('stunaddr') . ']' . PHP_EOL;
"

# Ne PAS rouvrir [general] dans rtp_custom (Asterisk 20 → STUN 0.0.0.0)
cat > /etc/asterisk/rtp_custom.conf <<'EOF'
; Asaphone — stunaddr / strictrtp via FreePBX Sipsettings → rtp_additional.conf
; Ne pas rouvrir [general] ici (bug Asterisk : STUN → 0.0.0.0).
EOF
chown www-data:asterisk /etc/asterisk/rtp_custom.conf 2>/dev/null || true
chmod 664 /etc/asterisk/rtp_custom.conf 2>/dev/null || true

# Patch immediat ice_host (fwconsole reload peut arriver plus tard / autre hook)
RTP_ADD="/etc/asterisk/rtp_additional.conf"
if [[ -f "$RTP_ADD" ]]; then
  tmp="$(mktemp)"
  awk -v ip="$LAN_IP" '
    BEGIN { in_ice=0; done=0 }
    /^\[ice_host_candidates\]/ {
      print
      print ip " => " ip
      in_ice=1
      done=1
      next
    }
    in_ice && /^\[/ { in_ice=0 }
    in_ice && /^[0-9]/ { next }
    in_ice && /^[[:space:]]*$/ { next }
    { print }
    END {
      if (!done) {
        print ""
        print "[ice_host_candidates]"
        print ip " => " ip
      }
    }
  ' "$RTP_ADD" >"$tmp"
  mv -f "$tmp" "$RTP_ADD"
  chown www-data:asterisk "$RTP_ADD" 2>/dev/null || true
  chmod 664 "$RTP_ADD" 2>/dev/null || true
fi

# media_address endpoints WebRTC (meme IP DHCP)
CUSTOM_POST="/etc/asterisk/pjsip.endpoint_custom_post.conf"
# shellcheck disable=SC1091
source "$ROOT/network/pjsip-align.env" 2>/dev/null || true
[[ -f /etc/provision/provision.env ]] && source /etc/provision/provision.env 2>/dev/null || true
{
  echo "; Asaphone — apply-rtp-relaxed.sh ($(date -Is)) IP=${LAN_IP}"
  echo "; media_address + prefs : ne PAS union-ajouter la video sur un offre audio-only"
  declare -A _seen=()
  for e in ${WEBRTC_EXTENSIONS:-1003 1004 1005 1006 1007 1008 1009 1010} ${PROVISION_EXT_POOL:-}; do
    [[ -z "$e" || -n "${_seen[$e]:-}" ]] && continue
    _seen[$e]=1
    echo "[${e}](+)"
    echo "media_address=${LAN_IP}"
    # bind_rtp=yes + socket piné → EPERM si ICE teste 127.0.0.1 / autre iface
    echo "bind_rtp_to_media_address=no"
    # Defaut FreePBX/Asterisk = operation:union → ajoute vp8/h264 (m-line video)
    # meme si l appelant n a envoye que de l audio → pas d audio + TOS video apres bridge.
    echo "codec_prefs_outgoing_offer=prefer:pending, operation:intersect, keep:all, transcode:allow"
    echo "codec_prefs_incoming_offer=prefer:pending, operation:intersect, keep:all, transcode:allow"
    echo "codec_prefs_outgoing_answer=prefer:pending, operation:intersect, keep:all, transcode:allow"
    echo "codec_prefs_incoming_answer=prefer:pending, operation:intersect, keep:all, transcode:allow"
    echo
  done
} >"${CUSTOM_POST}.tmp" && mv -f "${CUSTOM_POST}.tmp" "$CUSTOM_POST"
chown www-data:asterisk "$CUSTOM_POST" 2>/dev/null || true
chmod 664 "$CUSTOM_POST" 2>/dev/null || true

if [[ "$QUICK" -eq 1 ]]; then
  asterisk -rx "module unload res_rtp_asterisk.so" >/dev/null 2>&1 || true
  asterisk -rx "module load res_rtp_asterisk.so" >/dev/null 2>&1 || true
  asterisk -rx "module reload res_pjsip.so" >/dev/null 2>&1 || true
else
  fwconsole reload
  asterisk -rx "module unload res_rtp_asterisk.so" >/dev/null 2>&1 || true
  asterisk -rx "module load res_rtp_asterisk.so" >/dev/null 2>&1 || true
fi

asterisk -rx "rtp show settings" 2>/dev/null | sed -n '1,30p' || true
grep -A3 '\[ice_host_candidates\]' "$RTP_ADD" || true
asterisk -rx "pjsip show endpoint 1005" 2>/dev/null | grep -iE 'media_address|bind_rtp|codec_prefs_outgoing_offer' || true
