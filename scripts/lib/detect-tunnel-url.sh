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

# Dernière URL trycloudflare émise par cloudflared (ignore api.trycloudflare.com).
detect_trycloudflare_url_from_log() {
	local log_file="$1"
	local wait_secs="${2:-0}"
	local url="" i

	for ((i = 0; i <= wait_secs; i++)); do
		if [[ -r "$log_file" ]]; then
			url="$(grep -a 'trycloudflare.com' "$log_file" 2>/dev/null \
				| grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' \
				| grep -v 'api\.trycloudflare\.com' \
				| tail -1 || true)"
		elif [[ -f "$log_file" ]] && command -v sudo >/dev/null 2>&1; then
			url="$(sudo grep -a 'trycloudflare.com' "$log_file" 2>/dev/null \
				| grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' \
				| grep -v 'api\.trycloudflare\.com' \
				| tail -1 || true)"
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
detect_tunnel_url_quick() {
	local wait_secs="${1:-0}"
	PROVISION_TUNNEL_URL=""
	PROVISION_PUBLIC_BASE_URL=""
	PROVISION_PUBLIC_HOST=""

	local log_file="/var/log/provision/cloudflared.log"
	local url=""
	url="$(detect_trycloudflare_url_from_log "$log_file" "$wait_secs" || true)"

	# Secours hors ligne : tunnel.env (jamais prioritaire sur le journal cloudflared)
	if [[ -z "$url" ]]; then
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

# Tunnel Cloudflare dédié au relais WG (wstunnel :8081) — URL racine, sans /wg-relay
detect_wg_relay_tunnel_url() {
	local wait_secs="${1:-0}"
	PROVISION_WG_RELAY_TUNNEL_URL=""
	PROVISION_WG_RELAY_WSS_URL=""

	local env_file="/etc/provision/wg-relay-tunnel.env"
	local cached_url=""
	if [[ -r "$env_file" ]]; then
		# shellcheck disable=SC1090
		source "$env_file"
		cached_url="${PROVISION_WG_RELAY_TUNNEL_URL:-}"
	elif [[ -f "$env_file" ]] && command -v sudo >/dev/null 2>&1; then
		# shellcheck disable=SC1090
		source <(sudo cat "$env_file" 2>/dev/null || true)
		cached_url="${PROVISION_WG_RELAY_TUNNEL_URL:-}"
	fi

	local log_file="/var/log/provision/cloudflared-wg-relay.log"
	local url=""
	url="$(detect_trycloudflare_url_from_log "$log_file" "$wait_secs" || true)"

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
