#!/usr/bin/env bash
# Résout l'URL API distante (domaine fixe ou trycloudflare legacy).
# Usage : source scripts/lib/detect-tunnel-url.sh && resolve_provision_public_urls

resolve_provision_public_urls() {
	PROVISION_TUNNEL_URL=""
	PROVISION_PUBLIC_BASE_URL=""
	PROVISION_PUBLIC_HOST="${PROVISION_PUBLIC_HOST:-}"

	local mode="${CLOUDFLARE_TUNNEL_MODE:-named}"

	if [[ "$mode" == "named" && -n "${PROVISION_PUBLIC_HOST:-}" ]]; then
		PROVISION_TUNNEL_URL="https://${PROVISION_PUBLIC_HOST}"
		PROVISION_PUBLIC_BASE_URL="https://${PROVISION_PUBLIC_HOST}/provision"
		export PROVISION_TUNNEL_URL PROVISION_PUBLIC_BASE_URL PROVISION_PUBLIC_HOST
		return 0
	fi

	detect_tunnel_url_quick "${1:-0}"
}

# Extrait la dernière URL trycloudflare d'un flux texte (ignore api.trycloudflare.com).
_extract_trycloudflare_url() {
	grep -a 'trycloudflare.com' 2>/dev/null \
		| grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' \
		| grep -v 'api\.trycloudflare\.com' \
		| tail -1 || true
}

# Dernière URL trycloudflare dans le journal.
# Si after_bytes > 0 : ne lit que le contenu écrit APRÈS cet offset (évite l'URL d'un run précédent).
detect_trycloudflare_url_from_log() {
	local log_file="$1"
	local wait_secs="${2:-0}"
	local after_bytes="${3:-0}"
	local url="" i size

	for ((i = 0; i <= wait_secs; i++)); do
		url=""
		if [[ -r "$log_file" ]] || { [[ -f "$log_file" ]] && command -v sudo >/dev/null 2>&1; }; then
			size="$(stat -c%s "$log_file" 2>/dev/null || echo 0)"
			if [[ "$after_bytes" -gt 0 ]]; then
				# Attendre du contenu neuf après le restart
				if [[ "$size" -gt "$after_bytes" ]]; then
					if [[ -r "$log_file" ]]; then
						url="$(tail -c +"$((after_bytes + 1))" "$log_file" | _extract_trycloudflare_url)"
					else
						url="$(sudo tail -c +"$((after_bytes + 1))" "$log_file" 2>/dev/null | _extract_trycloudflare_url)"
					fi
				fi
			else
				if [[ -r "$log_file" ]]; then
					url="$(cat "$log_file" | _extract_trycloudflare_url)"
				else
					url="$(sudo cat "$log_file" 2>/dev/null | _extract_trycloudflare_url)"
				fi
			fi
		fi
		if [[ -n "$url" ]]; then
			printf '%s' "$url"
			return 0
		fi
		[[ "$i" -lt "$wait_secs" ]] && sleep 1
	done
	return 1
}

# Mode dev : URL éphémère trycloudflare (change à chaque redémarrage)
# $1 = wait_secs, $2 = after_bytes (optionnel)
detect_tunnel_url_quick() {
	local wait_secs="${1:-0}"
	local after_bytes="${2:-0}"
	PROVISION_TUNNEL_URL=""
	PROVISION_PUBLIC_BASE_URL=""
	PROVISION_PUBLIC_HOST=""

	local log_file="/var/log/provision/cloudflared.log"
	local url=""
	url="$(detect_trycloudflare_url_from_log "$log_file" "$wait_secs" "$after_bytes" || true)"

	# Secours hors ligne : tunnel.env (jamais prioritaire sur le journal cloudflared)
	if [[ -z "$url" && "$after_bytes" -eq 0 ]]; then
		local env_file="/etc/provision/tunnel.env"
		if [[ -r "$env_file" ]]; then
			# shellcheck disable=SC1090
			source "$env_file"
		elif [[ -f "$env_file" ]] && command -v sudo >/dev/null 2>&1; then
			# shellcheck disable=SC1090
			source <(sudo cat "$env_file" 2>/dev/null || true)
		fi
		url="${PROVISION_TUNNEL_URL:-}"
	fi

	if [[ -z "$url" ]]; then
		return 1
	fi

	PROVISION_TUNNEL_URL="$url"
	PROVISION_PUBLIC_BASE_URL="${url}/provision"
	PROVISION_PUBLIC_HOST="${url#https://}"
	export PROVISION_TUNNEL_URL PROVISION_PUBLIC_BASE_URL PROVISION_PUBLIC_HOST
	return 0
}

# Alias rétrocompat
detect_tunnel_url() {
	resolve_provision_public_urls "${1:-0}"
}

# Attendre qu'une URL trycloudflare réponde (≠ 530 / timeout).
# Cloudflare met parfois quelques secondes avant que l'edge route vers le connecteur.
wait_trycloudflare_ready() {
	local base_url="$1"
	local wait_secs="${2:-45}"
	local i code
	for ((i = 0; i < wait_secs; i += 2)); do
		code="$(curl -sk -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 8 \
			"${base_url%/}/" 2>/dev/null || true)"
		[[ -z "$code" ]] && code="000"
		# 200/301/302/401/403/404 = edge joint l'origin (403 Host Apache OK)
		case "$code" in
			200|301|302|401|403|404) return 0 ;;
		esac
		sleep 2
	done
	echo "WARN: ${base_url} pas prêt (dernier HTTP ${code:-?}) — publication quand même" >&2
	return 1
}

# Tunnel Cloudflare dédié au relais WG (wstunnel :8081) — URL racine, sans /wg-relay
# $1 = wait_secs, $2 = after_bytes (optionnel)
detect_wg_relay_tunnel_url() {
	local wait_secs="${1:-0}"
	local after_bytes="${2:-0}"
	PROVISION_WG_RELAY_TUNNEL_URL=""
	PROVISION_WG_RELAY_WSS_URL=""

	local env_file="/etc/provision/wg-relay-tunnel.env"
	local cached_url=""
	if [[ "$after_bytes" -eq 0 ]]; then
		if [[ -r "$env_file" ]]; then
			# shellcheck disable=SC1090
			source "$env_file"
			cached_url="${PROVISION_WG_RELAY_TUNNEL_URL:-}"
		elif [[ -f "$env_file" ]] && command -v sudo >/dev/null 2>&1; then
			# shellcheck disable=SC1090
			source <(sudo cat "$env_file" 2>/dev/null || true)
			cached_url="${PROVISION_WG_RELAY_TUNNEL_URL:-}"
		fi
	fi

	local log_file="/var/log/provision/cloudflared-wg-relay.log"
	local url=""
	url="$(detect_trycloudflare_url_from_log "$log_file" "$wait_secs" "$after_bytes" || true)"

	if [[ -z "$url" ]]; then
		url="$cached_url"
	fi

	if [[ -z "$url" ]]; then
		return 1
	fi

	PROVISION_WG_RELAY_TUNNEL_URL="$url"
	PROVISION_WG_RELAY_WSS_URL="wss://${url#https://}"
	export PROVISION_WG_RELAY_TUNNEL_URL PROVISION_WG_RELAY_WSS_URL
	return 0
}
