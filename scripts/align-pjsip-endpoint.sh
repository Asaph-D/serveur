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
  upsert($db, $ext, "webrtc", "yes");
  upsert($db, $ext, "ice_support", "yes");
  upsert($db, $ext, "use_avpf", "yes");
  upsert($db, $ext, "rtcp_mux", "yes");
  upsert($db, $ext, "media_encryption", "dtls");
  upsert($db, $ext, "media_encryption_optimistic", "no");
  upsert($db, $ext, "dtls_verify", "fingerprint");
  upsert($db, $ext, "dtls_auto_generate_cert", "yes");
} else {
  upsert($db, $ext, "webrtc", "no");
  upsert($db, $ext, "ice_support", "no");
  upsert($db, $ext, "use_avpf", "no");
  upsert($db, $ext, "rtcp_mux", "no");
  upsert($db, $ext, "media_encryption", "no");
  upsert($db, $ext, "media_encryption_optimistic", "no");
}

echo "DB OK\n";
' "$EXT" "$ALLOW_LIST" "$WFLAG" 2>&1

if [[ "$NO_RELOAD" -eq 0 ]]; then
  sudo "$FWCONSOLE" reload 2>&1 | sed -n '1,60p'
  echo
  echo "Résumé runtime (Asterisk):"
  sudo asterisk -rx "pjsip show endpoint $EXT" 2>&1 | grep -iE 'allow|disallow|dtmf_mode|direct_media|rtcp_mux|rewrite_contact|force_rport|rtp_symmetric|media_encryption|webrtc|ice|use_avpf|message_context' || true
fi
