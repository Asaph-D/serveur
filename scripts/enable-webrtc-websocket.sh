#!/bin/bash
# Active HTTP(S) Asterisk + transport PJSIP WSS pour clients WebRTC (navigateur).
# Idempotent : remplace le bloc marqué entre BEGIN/END dans les fichiers cibles.
# Exécuter : sudo bash /home/asaph/Documents/serveur/scripts/enable-webrtc-websocket.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ $(id -u) -eq 0 ]] || { echo "Root requis."; exit 1; }

HTTP_SNIP="$ROOT/webrtc/asterisk/http_custom-webrtc.conf"
PJSIP_SNIP="$ROOT/webrtc/asterisk/pjsip.transports_custom_post-webrtc.conf"
HTTP_DST="/etc/asterisk/http_custom.conf"
PJSIP_DST="/etc/asterisk/pjsip.transports_custom_post.conf"

for f in "$HTTP_SNIP" "$PJSIP_SNIP"; do
  [[ -f "$f" ]] || { echo "Snippet introuvable: $f"; exit 1; }
done

merge_marked_block() {
  local dst="$1"
  local begin="$2"
  local end="$3"
  local snippet="$4"
  mkdir -p "$(dirname "$dst")"
  [[ -f "$dst" ]] || touch "$dst"
  cp -a "$dst" "${dst}.bak.$(date +%Y%m%d%H%M%S)"
  awk -v b="$begin" -v e="$end" '
    { gsub(/\r$/, "") }
    $0 == b { skip = 1; next }
    $0 == e { skip = 0; next }
    !skip { print }
  ' "$dst" > "${dst}.new"
  mv "${dst}.new" "$dst"
  {
    echo "$begin"
    cat "$snippet"
    echo "$end"
    echo ""
  } >> "$dst"
  if id asterisk &>/dev/null; then
    chown asterisk:asterisk "$dst" 2>/dev/null || true
  fi
}

echo "=== Fusion http_custom.conf (HTTP 8088 + TLS 8089) ==="
merge_marked_block "$HTTP_DST" "; BEGIN serveur-webrtc-http" "; END serveur-webrtc-http" "$HTTP_SNIP"

echo "=== Fusion pjsip.transports_custom_post.conf (transport-wss) ==="
merge_marked_block "$PJSIP_DST" "; BEGIN serveur-webrtc-pjsip-transport" "; END serveur-webrtc-pjsip-transport" "$PJSIP_SNIP"

CRT="/etc/asterisk/keys/default.crt"
KEY="/etc/asterisk/keys/default.key"
INT_CRT="/etc/asterisk/keys/integration/certificate.pem"
INT_KEY="/etc/asterisk/keys/integration/webserver.key"
if [[ ! -f "$CRT" || ! -f "$KEY" ]]; then
  echo "AVERTISSEMENT : certificat ou clé absent ($CRT / $KEY)." >&2
  echo "  FreePBX utilise souvent /etc/asterisk/keys/integration/ — sinon Certificate Manager." >&2
fi

echo "=== Permissions TLS (Certman PKCS = www-data:www-data, asterisk ∈ www-data) ==="
bash "$ROOT/scripts/fix-cert-perms.sh"

echo "=== FreePBX : activer HTTP et écouter sur le réseau ==="
echo "    (sinon http_additional.conf laisse enabled=no et 127.0.0.1, WSS injoignable du LAN)"
if command -v fwconsole >/dev/null 2>&1; then
  fwconsole setting HTTPENABLED 1
  fwconsole setting HTTPBINDADDRESS 0.0.0.0
  fwconsole setting HTTPTLSBINDADDRESS 0.0.0.0
fi

echo "=== Modules WebSocket (info) ==="
if command -v asterisk >/dev/null 2>&1; then
  asterisk -rx "module show like res_http_websocket" 2>/dev/null || true
  asterisk -rx "module show like res_pjsip_transport_websocket" 2>/dev/null || true
fi

echo "=== Rechargement FreePBX / Asterisk ==="
if command -v fwconsole >/dev/null 2>&1; then
  fwconsole reload
else
  asterisk -rx "module reload http.so" 2>/dev/null || true
  asterisk -rx "module reload res_pjsip.so" 2>/dev/null || true
fi

echo "OK. Vérifications :"
echo "  sudo asterisk -rx \"http show status\""
echo "  sudo asterisk -rx \"pjsip show transports\""
echo "  sudo asterisk -rx \"pjsip show contacts\""
AST_COUNT="$(pgrep -c -x asterisk 2>/dev/null || echo 0)"
if [[ "${AST_COUNT}" -gt 1 ]]; then
  echo "AVERTISSEMENT : ${AST_COUNT} processus asterisk détectés." >&2
  echo "  Ne pas lancer 'asterisk -rvvv' en parallèle de fwconsole (instance fantôme, CLI ≠ WebSocket)." >&2
  echo "  Console : sudo asterisk -r   ou   sudo fwconsole console" >&2
fi
echo "Pare-feu : WEBRTC_ENABLE=yes dans network/site.env puis sudo bash scripts/net-apply-site.sh"
