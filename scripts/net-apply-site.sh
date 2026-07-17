#!/bin/bash
# Applique le “profil site” : FreePBX localnets + UFW + mDNS (pbx.local).
# Exécuter : sudo bash /home/asaph/Documents/serveur/scripts/net-apply-site.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/network/site.env"

[[ $(id -u) -eq 0 ]] || { echo "Root requis."; exit 1; }
[[ -f "$CFG" ]] || { echo "Config introuvable: $CFG"; exit 1; }

echo "=== 0) Détection réseau LAN (global-config) ==="
SYNC_ARGS=()
[[ $(id -u) -eq 0 ]] && SYNC_ARGS+=(--deploy)
if ! bash "$ROOT/scripts/sync-global-config.sh" "${SYNC_ARGS[@]}"; then
  echo "WARN: sync-global-config partiel — config précédente conservée (hors ligne ?)" >&2
fi

# shellcheck disable=SC1090
source "$CFG"

if [[ -z "${MGMT_CIDR:-}" || -z "${VOICE_CIDR:-}" ]]; then
  echo "MGMT_CIDR et VOICE_CIDR doivent être définis dans $CFG" >&2
  exit 1
fi

echo "=== 1) mDNS / hostname : ${PBX_MDNS_NAME}.local ==="
if ! command -v avahi-daemon >/dev/null 2>&1; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y avahi-daemon
fi
if [[ -n "${PBX_MDNS_NAME:-}" ]]; then
  hostnamectl set-hostname "${PBX_MDNS_NAME}"
fi
systemctl enable --now avahi-daemon

echo "=== 2) FreePBX localnets (PJSIP) ==="
export EXTRA_LAN_CIDRS EXTRA_VOICE_CIDRS
php -r '
include "/etc/freepbx.conf";
$db = \FreePBX::Database();
$mgmt = getenv("MGMT_CIDR");
$voice = getenv("VOICE_CIDR");
$lines = array_values(array_unique(array_filter([$mgmt, $voice])));
$extra_voice = trim((string) getenv("EXTRA_VOICE_CIDRS"));
if ($extra_voice !== "") {
  foreach (preg_split("/\s+/", $extra_voice) as $c) {
    if ($c !== "" && !in_array($c, $lines, true)) { $lines[] = $c; }
  }
}
$extra = trim((string) getenv("EXTRA_LAN_CIDRS"));
if ($extra !== "") {
  foreach (preg_split("/\s+/", $extra) as $c) {
    if ($c !== "" && !in_array($c, $lines, true)) { $lines[] = $c; }
  }
}
$val = implode("\n", $lines);
$stmt = $db->prepare("UPDATE kvstore_Sipsettings SET val = :val WHERE `key` = \"localnets\"");
$stmt->execute([":val" => $val]);
echo "kvstore_Sipsettings.localnets mis à jour:\n$val\n";
' >/dev/null

echo "=== 2b) FreePBX externip (ICE / RTP WebRTC) ==="
if [[ -n "${PBX_LAN_IP:-}" ]]; then
  php -r '
include "/etc/freepbx.conf";
$db = \FreePBX::Database();
$ip = getenv("PBX_LAN_IP");
$stmt = $db->prepare("UPDATE kvstore_Sipsettings SET val = :val WHERE `key` = \"externip\"");
$stmt->execute([":val" => $ip]);
$stmt = $db->prepare("UPDATE kvstore_Sipsettings SET val = :val WHERE `key` = \"externhost\"");
$stmt->execute([":val" => $ip]);
echo "externip/externhost = $ip\n";
' >/dev/null
fi

echo "=== 3) UFW (SIP/RTP selon site.env) ==="
ufw --force enable >/dev/null || true

allow_voice_cidr() {
  local cidr="$1"
  local label="$2"

  ufw allow from "${cidr}" to any port 5060 proto udp comment "PJSIP UDP ${label}" >/dev/null || true
  ufw allow from "${cidr}" to any port 5060 proto tcp comment "PJSIP TCP ${label}" >/dev/null || true
  ufw allow from "${cidr}" to any port 5061 proto tcp comment "PJSIP TLS ${label}" >/dev/null || true
  ufw allow from "${cidr}" to any port 5160 proto udp comment "PJSIP 5160 UDP ${label}" >/dev/null || true
  ufw allow from "${cidr}" to any port 5161 proto tcp comment "PJSIP 5161 TLS ${label}" >/dev/null || true
  ufw allow from "${cidr}" to any port 10000:20000 proto udp comment "RTP ${label}" >/dev/null || true

  if [[ "${WEBRTC_ENABLE:-no}" == "yes" ]]; then
    local whp="${WEBRTC_HTTP_PORT:-8088}"
    local wwp="${WEBRTC_WSS_PORT:-8089}"
    ufw allow from "${cidr}" to any port "${whp}" proto tcp comment "Asterisk HTTP WebRTC ${label}" >/dev/null || true
    ufw allow from "${cidr}" to any port "${wwp}" proto tcp comment "Asterisk WSS WebRTC ${label}" >/dev/null || true
  fi
  if [[ "${PROVISION_TURN_ENABLE:-no}" == "yes" ]]; then
    local tp="${PROVISION_TURN_PORT:-3478}"
    ufw allow from "${cidr}" to any port "${tp}" proto udp comment "STUN/TURN ${label}" >/dev/null || true
    ufw allow from "${cidr}" to any port "${tp}" proto tcp comment "STUN/TURN TCP ${label}" >/dev/null || true
    local rmin="${PROVISION_TURN_RELAY_MIN:-49160}"
    local rmax="${PROVISION_TURN_RELAY_MAX:-49200}"
    ufw allow from "${cidr}" to any port "${rmin}:${rmax}" proto udp comment "TURN relay ${label}" >/dev/null || true
  fi
}

# Toujours autoriser depuis le VLAN voix principal et les secteurs voix routés.
allow_voice_cidr "${VOICE_CIDR}" "VOICE"
if [[ -n "${EXTRA_VOICE_CIDRS:-}" ]]; then
  read -r -a _extra_voice_lans <<< "${EXTRA_VOICE_CIDRS}"
  for c in "${_extra_voice_lans[@]}"; do
    [[ -z "${c}" ]] && continue
    allow_voice_cidr "${c}" "VOICE EXTRA"
  done
fi

if [[ "${WEBRTC_ENABLE:-no}" == "yes" ]]; then
  WHP="${WEBRTC_HTTP_PORT:-8088}"
  WWP="${WEBRTC_WSS_PORT:-8089}"
  ufw allow from "${MGMT_CIDR}" to any port "${WHP}" proto tcp comment "Asterisk HTTP WebRTC MGMT" >/dev/null || true
  ufw allow from "${MGMT_CIDR}" to any port "${WWP}" proto tcp comment "Asterisk WSS WebRTC MGMT" >/dev/null || true
  # RTP média WebRTC / softphones depuis les LAN listés dans EXTRA_LAN_CIDRS
  if [[ -n "${EXTRA_LAN_CIDRS:-}" ]]; then
    read -r -a _extra_lans <<< "${EXTRA_LAN_CIDRS}"
    for c in "${_extra_lans[@]}"; do
      [[ -z "${c}" ]] && continue
      ufw allow from "${c}" to any port "${WHP}" proto tcp comment "Asterisk HTTP WebRTC EXTRA" >/dev/null || true
      ufw allow from "${c}" to any port "${WWP}" proto tcp comment "Asterisk WSS WebRTC EXTRA" >/dev/null || true
      ufw allow from "${c}" to any port 10000:20000 proto udp comment "RTP WebRTC/softphone EXTRA" >/dev/null || true
    done
  fi
fi

if [[ "${ALLOW_SIP_FROM_MGMT:-no}" == "yes" ]]; then
  ufw allow from "${MGMT_CIDR}" to any port 5060 proto udp comment "PJSIP UDP MGMT" >/dev/null || true
  ufw allow from "${MGMT_CIDR}" to any port 5060 proto tcp comment "PJSIP TCP MGMT" >/dev/null || true
  ufw allow from "${MGMT_CIDR}" to any port 5160 proto udp comment "PJSIP 5160 UDP MGMT" >/dev/null || true
fi

if [[ "${ALLOW_TLS_FROM_MGMT:-no}" == "yes" ]]; then
  ufw allow from "${MGMT_CIDR}" to any port 5061 proto tcp comment "PJSIP TLS MGMT" >/dev/null || true
  ufw allow from "${MGMT_CIDR}" to any port 5161 proto tcp comment "PJSIP 5161 TLS MGMT" >/dev/null || true
fi

ufw reload >/dev/null

echo "=== 4) Monitoring (Docker) ==="
if [[ "${MONITORING_ALLOW_FROM_MGMT:-no}" == "yes" ]]; then
  ufw allow from "${MGMT_CIDR}" to any port "${GRAFANA_PORT:-3000}" proto tcp comment "Grafana MGMT" >/dev/null || true
  ufw allow from "${MGMT_CIDR}" to any port "${INFLUXDB_PORT:-8086}" proto tcp comment "InfluxDB MGMT" >/dev/null || true
  ufw reload >/dev/null
fi

if [[ "${MONITORING_ENABLE:-no}" == "yes" ]]; then
  if command -v docker >/dev/null 2>&1; then
    (cd "$ROOT/monitoring" && docker compose up -d) >/dev/null
  else
    echo "Docker non trouvé : monitoring non démarré." >&2
  fi
fi

echo "=== 5) Reload FreePBX / Asterisk ==="
fwconsole reload >/dev/null

echo "=== 6) Aide Windows (hosts) ==="
# Windows ne résout pas toujours mDNS (.local) par défaut.
# On génère une ligne prête à coller dans C:\Windows\System32\drivers\etc\hosts
if [[ -n "${PBX_LAN_IP:-}" && -n "${PBX_MDNS_NAME:-}" ]]; then
  echo "Généré : $ROOT/network/windows-hosts.txt (${PBX_LAN_IP} → ${PBX_MDNS_NAME}.local)"
fi

echo "OK."
echo "- Nom à utiliser côté téléphones/softphones: ${PBX_MDNS_NAME}.local"
echo "- Vérifier enregistrements: sudo asterisk -rx \"pjsip show contacts\""
echo "- UFW: sudo ufw status numbered"

