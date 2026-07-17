#!/bin/bash
# Démarrage PBX — résilient hors ligne (Internet optionnel pour tunnel / GitHub / VPN distant).
# Usage : sudo systemctl start serveur-startup.service
set -uo pipefail

LOG_FILE="${LOG_FILE:-/var/log/serveur-startup.log}"
ROOT_SRV="${ROOT_SRV:-/home/asaph/Documents/serveur}"

if [[ $(id -u) -ne 0 ]]; then
  echo "ERREUR: ce script doit être exécuté en root (ex. via systemd)." >&2
  exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
chmod 0644 "$LOG_FILE" || true

# Miroir terminal + fichier log (systemd = log seul ; terminal interactif = les deux)
if [[ -t 1 ]]; then
	export STARTUP_FORCE_TTY=1
	exec > >(tee -a "$LOG_FILE" | tee /dev/tty) 2>&1
else
	exec > >(tee -a "$LOG_FILE") 2>&1
fi

# shellcheck source=scripts/lib/startup-console.sh
source "${ROOT_SRV}/scripts/lib/startup-console.sh"

startup_progress_init 10
startup_banner

# ── Cœur PBX (local, sans Internet) ─────────────────────────────────────

if command -v fwconsole >/dev/null 2>&1; then
  startup_run_optional "FreePBX chown.conf (VM + clés TLS + run)" \
    bash "${ROOT_SRV}/scripts/install-freepbx-chown-conf.sh"
  startup_run_optional "Permissions GUI FreePBX" \
    bash "${ROOT_SRV}/scripts/fix-freepbx-dashboard-perms.sh"
  startup_run_optional "Permissions certificats TLS (pre-start)" \
    bash "${ROOT_SRV}/scripts/fix-cert-perms.sh"
  startup_run_optional "FreePBX (fwconsole start)" fwconsole start
  startup_run_optional "WSS TLS 8089 (certs + reload)" \
    bash "${ROOT_SRV}/scripts/fix-wss-tls.sh"
  startup_run_optional "Permissions /var/run/asterisk (reload.lock + ctl)" \
    bash "${ROOT_SRV}/scripts/fix-asterisk-run-perms.sh"
  startup_run_optional "Permissions spool messagerie" \
    bash "${ROOT_SRV}/scripts/fix-voicemail-spool-perms.sh"
else
  startup_skip "FreePBX (fwconsole introuvable)"
fi

startup_step "Sessions PHP"
rm -f /var/lib/php/sessions/sess_* 2>/dev/null || true
chown root:root /var/lib/php/sessions 2>/dev/null || true
chmod 1733 /var/lib/php/sessions 2>/dev/null || true
startup_ok "Sessions PHP"

startup_run_critical "Apache (restart)" systemctl restart apache2

startup_step "Profil réseau site (UFW, mDNS, localnets)"
# shellcheck disable=SC1091
source "${ROOT_SRV}/network/global-config.env" 2>/dev/null || true
OFFLINE_HINT=0
if bash "${ROOT_SRV}/scripts/net-apply-site.sh"; then
  startup_ok "Profil réseau site"
else
  startup_warn "Profil réseau site — erreurs partielles"
  OFFLINE_HINT=1
fi

if command -v fwconsole >/dev/null 2>&1; then
  startup_run_optional "Permissions /var/run/asterisk (post-réseau)" \
    bash "${ROOT_SRV}/scripts/fix-asterisk-run-perms.sh"
fi

	if command -v tailscale >/dev/null 2>&1 && systemctl is-enabled tailscaled &>/dev/null; then
  startup_skip "Tailscale (désactivé — utiliser wg-wss-relay)"
fi

if [[ -x "${ROOT_SRV}/scripts/install-wg-wss-relay.sh" ]]; then
  startup_run_optional "Relais WG/WebSocket (Starlink 4G)" \
    bash "${ROOT_SRV}/scripts/install-wg-wss-relay.sh"
  startup_run_optional "URL tunnel WG relay (trycloudflare)" \
    bash "${ROOT_SRV}/scripts/refresh-wg-relay-tunnel-url.sh" --restart
fi

# ── Internet optionnel ───────────────────────────────────────────────────

if systemctl is-enabled cloudflared-provision.service &>/dev/null; then
  startup_step "Cloudflare tunnel (provision API distante)"
  systemctl start cloudflared-provision.service 2>/dev/null \
    || systemctl restart cloudflared-provision.service 2>/dev/null \
    || startup_skip "cloudflared ne démarre pas"
  if [[ "${CLOUDFLARE_TUNNEL_MODE:-quick}" == "quick" ]]; then
    startup_run_optional "URL trycloudflare (refresh-tunnel-url)" \
      bash "${ROOT_SRV}/scripts/refresh-tunnel-url.sh" --restart
  else
    startup_info "Tunnel nommé — pas de refresh trycloudflare"
  fi
else
  startup_skip "Cloudflare tunnel (service non activé)"
fi

# bootstrap.json doit être régénéré APRÈS les refresh tunnel (sinon api_remote périmé sur GitHub).
startup_run_optional "Sync bootstrap (api_remote + relay WSS)" \
  bash "${ROOT_SRV}/scripts/sync-global-config.sh" --deploy

if [[ "${GITHUB_BOOTSTRAP_PUBLISH:-no}" == "yes" ]]; then
  startup_run_optional "Publication bootstrap → GitHub Pages" \
    bash "${ROOT_SRV}/scripts/publish-bootstrap-github.sh"
else
  startup_skip "Publication GitHub (GITHUB_BOOTSTRAP_PUBLISH≠yes)"
fi

# ── HTTPS local (Apache 443 — certs déjà fixés avant fwconsole) ──────────

startup_run_optional "Apache HTTPS (443)" \
  bash "${ROOT_SRV}/scripts/enable-apache-https.sh"

# ── Résumé ───────────────────────────────────────────────────────────────

# shellcheck disable=SC1091
source "${ROOT_SRV}/network/global-config.env" 2>/dev/null || true
PBX_IP="${PBX_LAN_IP:-?}"
PBX_H="${PBX_HOST:-pbx.local}"
API_REM=""
if [[ -r /etc/provision/tunnel.env ]]; then
  # shellcheck disable=SC1091
  source /etc/provision/tunnel.env 2>/dev/null || true
  API_REM="${PROVISION_PUBLIC_BASE_URL:-}"
fi
[[ -z "$API_REM" && -n "${PROVISION_PUBLIC_BASE_URL:-}" ]] && API_REM="$PROVISION_PUBLIC_BASE_URL"

startup_summary "$PBX_IP" "$PBX_H" "$API_REM" "$OFFLINE_HINT"

echo "serveur-startup: OK $(date -Is)"
