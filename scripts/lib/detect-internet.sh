#!/usr/bin/env bash
# Détection rapide d'un accès Internet (WAN), pas seulement LAN.
# Usage : source scripts/lib/detect-internet.sh && has_internet && echo OK

has_internet() {
	local url timeout="${STARTUP_INTERNET_PROBE_SECS:-3}"
	for url in \
		"https://cloudflare.com/cdn-cgi/trace" \
		"https://api.github.com/zen" \
		"https://1.1.1.1/cdn-cgi/trace"
	do
		if curl -fsS --connect-timeout 2 --max-time "$timeout" -o /dev/null "$url" 2>/dev/null; then
			return 0
		fi
	done
	return 1
}
