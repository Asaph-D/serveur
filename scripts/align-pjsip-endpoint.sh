#!/usr/bin/env bash
# Aligne les paramètres PJSIP (table sip FreePBX) pour une extension.
# Mode classique (téléphone / Zoiper UDP) : SRTP off, rtcp_mux off.
# Mode --webrtc (navigateur) : webrtc/ICE/AVPF/DTLS + codecs incl. opus.
#
# Usage:
#   sudo bash align-pjsip-endpoint.sh [--webrtc] [--no-reload] <extension> [allow_list]
# Ex:
#   sudo bash align-pjsip-endpoint.sh 1001 'g722,ulaw,alaw'
#   sudo bash align-pjsip-endpoint.sh --webrtc 1002 'opus,g722,ulaw,alaw'
set -euo pipefail

WEBRTC=0
NO_RELOAD=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --webrtc) WEBRTC=1; shift ;;
    --no-reload) NO_RELOAD=1; shift ;;
    -*) echo "Option inconnue: $1" >&2; exit 2 ;;
    *) break ;;
  esac
done

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 [--webrtc] [--no-reload] <extension> [allow_list]" >&2
  echo "  classique: $0 1001 'g722,ulaw,alaw'" >&2
  echo "  WebRTC:    $0 --webrtc 1002 'opus,g722,ulaw,alaw'" >&2
  exit 2
fi

EXT="$1"
if [[ "$WEBRTC" -eq 1 ]]; then
  ALLOW_LIST="${2:-opus,g722,ulaw,alaw}"
else
  ALLOW_LIST="${2:-g722,ulaw,alaw}"
fi

if ! [[ "$EXT" =~ ^[0-9]{2,6}$ ]]; then
  echo "Erreur: extension invalide: '$EXT' (attendu: chiffres)" >&2
  exit 2
fi

if ! command -v php >/dev/null 2>&1; then
  echo "Erreur: php introuvable" >&2
  exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
  echo "Erreur: sudo introuvable" >&2
  exit 1
fi

FWCONSOLE="$(command -v fwconsole 2>/dev/null || true)"
if [[ -z "$FWCONSOLE" ]]; then
  if [[ -x /usr/sbin/fwconsole ]]; then
    FWCONSOLE="/usr/sbin/fwconsole"
  elif sudo test -x /var/lib/asterisk/bin/fwconsole 2>/dev/null; then
    FWCONSOLE="/var/lib/asterisk/bin/fwconsole"
  fi
fi
if [[ -z "${FWCONSOLE:-}" ]]; then
  echo "Erreur: fwconsole introuvable" >&2
  exit 1
fi

if ! sudo -n true 2>/dev/null; then
  echo "Erreur: sudo nécessite un mot de passe (lance: sudo -v puis relance)" >&2
  exit 1
fi

MODE_LABEL="classique (UDP / téléphone)"
[[ "$WEBRTC" -eq 1 ]] && MODE_LABEL="WebRTC (navigateur / WSS)"

echo "Alignement PJSIP extension $EXT — $MODE_LABEL"
echo "  allow=$ALLOW_LIST"
if [[ "$WEBRTC" -eq 1 ]]; then
  echo "  webrtc=yes, ice, avpf, rtcp_mux, media_encryption=dtls"
else
  echo "  SRTP=off (media_encryption=no), direct_media=off, rtcp_mux=off, dtmf=rfc4733"
fi
echo

WFLAG="classic"
[[ "$WEBRTC" -eq 1 ]] && WFLAG="webrtc"

sudo php -r '
include "/etc/freepbx.conf";
$db = \FreePBX::Database();

$ext = $argv[1];
$allow = $argv[2];
$webrtc = ($argv[3] ?? "") === "webrtc";

function upsert($db, $id, $keyword, $data) {
  $id = addslashes($id);
  $keyword = addslashes($keyword);
  $data = addslashes($data);
  $db->exec("REPLACE INTO sip (id,keyword,data,flags) VALUES (\"$id\",\"$keyword\",\"$data\",0)");
}

upsert($db, $ext, "disallow", "all");
upsert($db, $ext, "allow", str_replace(",", "&", $allow));

upsert($db, $ext, "dtmfmode", "rfc4733");
upsert($db, $ext, "direct_media", "no");
upsert($db, $ext, "rewrite_contact", "yes");
upsert($db, $ext, "force_rport", "yes");
upsert($db, $ext, "rtp_symmetric", "yes");

upsert($db, $ext, "message_context", "from-message");

if ($webrtc) {
  // Cles NATIVE FreePBX (PJSip.class.php) — sinon Apply Config regenere avpf=no / icesupport=no
  // et casse le SDP WebRTC (Could not negotiate stream / nothing).
  upsert($db, $ext, "webrtc", "yes");
  upsert($db, $ext, "avpf", "yes");
  upsert($db, $ext, "icesupport", "yes");
  // BUNDLE obligatoire audio+video WebRTC (sinon DTLS video hors candidats ICE)
  upsert($db, $ext, "bundle", "yes");
  upsert($db, $ext, "rtcp_mux", "yes");
  // Forcer RTP/ICE sur IP LAN (evite docker/WG/IPv6 Network is unreachable)
  // IP DHCP courante (hotspot variable) — ecrite par sync-global-config / startup
  $media = "";
  foreach (["/home/asaph/Documents/serveur/network/global-config.env", "/etc/provision/global-config.env", "/etc/provision/provision.env"] as $envf) {
    if (!is_readable($envf)) { continue; }
    if (preg_match("/^PBX_LAN_IP=(.+)$/m", (string)@file_get_contents($envf), $m)) {
      $media = trim($m[1], " \t\"");
      if ($media !== "") { break; }
    }
  }
  if ($media === "") {
    echo "WARN: PBX_LAN_IP introuvable — media_address non force\n";
  } else {
    upsert($db, $ext, "media_address", $media);
  }
  // no : bind piné provoque STUN EPERM (sendto 127.0.0.1 depuis IP LAN)
  upsert($db, $ext, "bind_rtp_to_media_address", "no");
  upsert($db, $ext, "media_encryption", "dtls");
  upsert($db, $ext, "media_encryption_optimistic", "no");
  upsert($db, $ext, "media_use_received_transport", "yes");
  upsert($db, $ext, "dtls_verify", "fingerprint");
  upsert($db, $ext, "dtls_setup", "actpass");
  upsert($db, $ext, "dtls_auto_generate_cert", "yes");
  upsert($db, $ext, "max_audio_streams", "1");
  upsert($db, $ext, "max_video_streams", "1");
  // FreePBX: empty("0") → fallback 30s → coupe la video si ICE lent. 300 = large.
  upsert($db, $ext, "rtp_timeout", "300");
  upsert($db, $ext, "rtp_timeout_hold", "300");
  // Alias Asterisk (lisibles hors FreePBX)
  upsert($db, $ext, "ice_support", "yes");
  upsert($db, $ext, "use_avpf", "yes");
  upsert($db, $ext, "codec_prefs_incoming_answer", "prefer:ulaw, operation:intersect, keep:all, transcode:allow");
  upsert($db, $ext, "codec_prefs_outgoing_offer", "prefer:ulaw, operation:intersect, keep:all, transcode:allow");
  // WSS : contact sip@IP:port_ws — qualify UDP echoue (surtout avec VPN actif).
  upsert($db, $ext, "qualifyfreq", "0");
} else {
  upsert($db, $ext, "webrtc", "no");
  upsert($db, $ext, "bundle", "no");
  upsert($db, $ext, "avpf", "no");
  upsert($db, $ext, "icesupport", "no");
  upsert($db, $ext, "ice_support", "no");
  upsert($db, $ext, "use_avpf", "no");
  upsert($db, $ext, "rtcp_mux", "no");
  upsert($db, $ext, "media_address", "");
  upsert($db, $ext, "bind_rtp_to_media_address", "no");
  upsert($db, $ext, "media_encryption", "no");
  upsert($db, $ext, "media_encryption_optimistic", "no");
  upsert($db, $ext, "media_use_received_transport", "no");
  upsert($db, $ext, "qualifyfreq", "60");
}

echo "DB OK\n";
' "$EXT" "$ALLOW_LIST" "$WFLAG" 2>&1

if [[ "$NO_RELOAD" -eq 0 ]]; then
  sudo "$FWCONSOLE" reload 2>&1 | sed -n '1,60p'
  echo
  echo "Résumé runtime (Asterisk):"
  sudo asterisk -rx "pjsip show endpoint $EXT" 2>&1 | grep -iE 'allow|disallow|dtmf_mode|direct_media|rtcp_mux|rewrite_contact|force_rport|rtp_symmetric|media_encryption|webrtc|ice|use_avpf|message_context' || true
fi
