#!/usr/bin/env bash
# Affichage console au démarrage (serveur-startup.service + mode interactif)

STARTUP_WARN_COUNT=0
STARTUP_SKIP_COUNT=0
STARTUP_STEP=0
STARTUP_TOTAL=10
STARTUP_PROGRESS_WIDTH=36

# Détecte un terminal réel (même si stdout est redirigé vers tee)
startup_is_tty() {
	[[ -n "${STARTUP_FORCE_TTY:-}" ]] && return 0
	[[ -t 1 ]] || [[ -t 2 ]] || [[ -w /dev/tty ]]
}

startup_c() {
	local code="$1"
	shift
	if startup_is_tty; then
		printf '\033[%sm' "$code"
	fi
	printf '%s' "$*"
	if startup_is_tty; then
		printf '\033[0m'
	fi
}

startup_echo() {
	printf '%s\n' "$*"
}

startup_rule() {
	startup_echo "╔══════════════════════════════════════════════════════════════════════════╗"
}

startup_rule_bottom() {
	startup_echo "╚══════════════════════════════════════════════════════════════════════════╝"
}

startup_banner() {
	echo ""
	startup_rule
	startup_echo "║                                                                          ║"
	startup_c "1;35" "║"
	printf '%s' "     █▀▀█ █▀▀█ ▄▀▄ ▀▄▀ █▀▀█   ░   █▀▄▀█ █▀▀█ █▀▀█ █▀▀█                    "
	if startup_is_tty; then printf '\033[0m'; fi
	echo " ║"
	startup_c "1;35" "║"
	printf '%s' "     ▀▄▀█ █▄▄█ █▀█ ░░█ █▄▄█   ░   █ ▀ █ █▄▄█ █▄▄█ ░░░                    "
	if startup_is_tty; then printf '\033[0m'; fi
	echo " ║"
	startup_echo "║                                                                          ║"
	startup_c "1;33" "║"
	printf '%s' "                          ▀▄▀  A S A P H O N E  ▄▀▀                        "
	if startup_is_tty; then printf '\033[0m'; fi
	echo " ║"
	startup_echo "║                                                                          ║"
	startup_c "0;36" "║"
	printf '%s' "              FreePBX  ·  Provision  ·  VoIP  ·  VPN WireGuard              "
	if startup_is_tty; then printf '\033[0m'; fi
	startup_echo " ║"
	startup_echo "║                                                                          ║"
	startup_rule_bottom
	echo ""
	startup_c "1;37" "  $(date '+%A %d %B %Y — %H:%M:%S')"
	echo ""
	startup_info "LAN / FreePBX / Apache  → démarrent sans Internet"
	startup_info "Cloudflare · GitHub · VPN distant  → nécessitent Internet"
	startup_info "Journal complet  → /var/log/serveur-startup.log"
	echo ""
}

startup_progress_init() {
	STARTUP_TOTAL="${1:-10}"
	STARTUP_STEP=0
}

startup_progress_render() {
	local current="$1"
	local total="$2"
	local label="${3:-}"
	local width="$STARTUP_PROGRESS_WIDTH"
	local filled empty pct bar i

	[[ "$total" -lt 1 ]] && total=1
	[[ "$current" -gt "$total" ]] && current="$total"
	filled=$(( current * width / total ))
	empty=$(( width - filled ))
	pct=$(( current * 100 / total ))

	bar=""
	for ((i = 0; i < filled; i++)); do bar+="█"; done
	for ((i = 0; i < empty; i++)); do bar+="░"; done

	echo ""
	startup_c "0;36" "  ┌─ Lancement ─────────────────────────────────────────────────────────┐"
	echo ""
	startup_c "1;36" "  │ [${bar}] ${pct}%"
	echo ""
	startup_c "0;90" "  │ étape ${current}/${total}"
	echo ""
	if [[ -n "$label" ]]; then
		startup_c "0;36" "  │ "
		printf '▸ %s\n' "$label"
	fi
	startup_c "0;36" "  └──────────────────────────────────────────────────────────────────────┘"
	echo ""
}

startup_step() {
	STARTUP_STEP=$((STARTUP_STEP + 1))
	startup_progress_render "$STARTUP_STEP" "$STARTUP_TOTAL" "$*"
	startup_c "1;36" "▶ $*"
	echo ""
}

startup_ok() {
	startup_c "1;32" "  ✓ $*"
	echo ""
}

startup_warn() {
	STARTUP_WARN_COUNT=$((STARTUP_WARN_COUNT + 1))
	startup_c "1;33" "  ⚠ $*"
	echo ""
}

startup_skip() {
	STARTUP_SKIP_COUNT=$((STARTUP_SKIP_COUNT + 1))
	startup_c "0;90" "  ○ $*"
	echo ""
}

startup_info() {
	startup_c "0;90" "  │ $*"
	echo ""
}

startup_run_critical() {
	local label="$1"
	shift
	startup_step "$label"
	if "$@"; then
		startup_ok "$label"
		return 0
	fi
	startup_warn "$label — échec"
	return 1
}

startup_run_optional() {
	local label="$1"
	shift
	startup_step "$label (optionnel — Internet ou réseau)"
	if "$@"; then
		startup_ok "$label"
		return 0
	fi
	startup_skip "$label — poursuite sans bloquer le démarrage"
	return 0
}

startup_summary() {
	local pbx_ip="${1:-?}"
	local pbx_host="${2:-pbx.local}"
	local api_remote="${3:-}"
	local offline="${4:-0}"

	echo ""
	startup_rule
	startup_c "1;32" "  DÉMARRAGE TERMINÉ"
	echo ""
	startup_rule_bottom
	echo ""
	startup_info "Interface LAN   : ${pbx_ip}  (${pbx_host})"
	startup_info "FreePBX         : https://${pbx_host}"
	startup_info "Provision API   : https://${pbx_host}/provision"
	startup_info "Asaphone login  : POST …/api/v1/reconnect.php"
	if [[ -n "$api_remote" ]]; then
		startup_info "API distante    : ${api_remote}"
	else
		startup_info "API distante    : (indisponible — hors ligne ou tunnel arrêté)"
	fi
	if [[ "$offline" -eq 1 ]]; then
		startup_info "Mode            : hors ligne — relancer sync quand Internet revient"
	fi
	if [[ "$STARTUP_WARN_COUNT" -gt 0 || "$STARTUP_SKIP_COUNT" -gt 0 ]]; then
		startup_info "Alertes         : ${STARTUP_WARN_COUNT} avertissement(s), ${STARTUP_SKIP_COUNT} étape(s) ignorée(s)"
	fi
	startup_info "Astuce dev      : asterisk -rx \"pjsip show contacts\""
	startup_info "                 sudo bash scripts/sync-global-config.sh"
	echo ""
	startup_progress_render "$STARTUP_TOTAL" "$STARTUP_TOTAL" "terminé"
	echo ""
}
