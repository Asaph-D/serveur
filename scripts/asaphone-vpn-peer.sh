#!/bin/bash
# Gestion peers WireGuard (root) — appelé par www-data via sudo
set -euo pipefail

WG_CONF="${WG_CONF:-/etc/wireguard/wg0.conf}"
IFACE="${WG_IFACE:-wg0}"

usage() {
	echo "Usage: $0 server-pubkey | add <pubkey> <tunnel_ip> | remove <pubkey>" >&2
	exit 1
}

ensure_iface() {
	if ! ip link show "$IFACE" &>/dev/null; then
		echo "Interface $IFACE absente" >&2
		exit 1
	fi
}

server_pubkey() {
	ensure_iface
	wg show "$IFACE" public-key
}

peer_in_conf() {
	local pubkey="$1"
	grep -qF "$pubkey" "$WG_CONF" 2>/dev/null
}

add_peer() {
	local pubkey="$1"
	local ip="$2"
	ensure_iface
	wg set "$IFACE" peer "$pubkey" allowed-ips "${ip}/32"
	if [[ -r "$WG_CONF" ]] && ! peer_in_conf "$pubkey"; then
		cat >>"$WG_CONF" <<EOF

[Peer]
# provision-vpn $(date -Iseconds)
PublicKey = ${pubkey}
AllowedIPs = ${ip}/32
EOF
		chmod 600 "$WG_CONF"
	fi
	echo "ok"
}

remove_peer() {
	local pubkey="$1"
	ensure_iface
	wg set "$IFACE" peer "$pubkey" remove 2>/dev/null || true
	if [[ -r "$WG_CONF" ]]; then
		local tmp
		tmp="$(mktemp)"
		awk -v pk="$pubkey" '
			/^\[Peer\]/ { block=1; buf=$0 ORS; next }
			block {
				buf = buf $0 ORS
				if ($0 ~ /^PublicKey = / && index($0, pk)) { skip=1 }
				if ($0 == "" || $0 ~ /^\[/ ) {
					if (!skip) printf "%s", buf
					block=($0 ~ /^\[Peer\]/) ? 1 : 0
					skip=0
					buf=($0 ~ /^\[Peer\]/) ? $0 ORS : ""
					if ($0 != "" && $0 !~ /^\[Peer\]/) print $0
					next
				}
				next
			}
			{ print }
		' "$WG_CONF" >"$tmp"
		mv "$tmp" "$WG_CONF"
		chmod 600 "$WG_CONF"
	fi
	echo "ok"
}

case "${1:-}" in
	server-pubkey) server_pubkey ;;
	add)
		[[ $# -eq 3 ]] || usage
		add_peer "$2" "$3"
		;;
	remove)
		[[ $# -eq 2 ]] || usage
		remove_peer "$2"
		;;
	*) usage ;;
esac
