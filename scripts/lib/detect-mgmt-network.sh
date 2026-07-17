#!/usr/bin/env bash
# Détecte IP / CIDR / passerelle sur l'interface de gestion (DHCP selon point d'accès).
# Usage : source scripts/lib/detect-mgmt-network.sh && detect_mgmt_network ens33

detect_mgmt_network() {
	local iface="${1:?interface requise}"

	PBX_LAN_IP=""
	MGMT_CIDR=""
	MGMT_GW=""

	if ! ip link show "$iface" >/dev/null 2>&1; then
		echo "Interface introuvable : $iface" >&2
		return 1
	fi

	local cidr
	cidr="$(ip -4 -o addr show dev "$iface" scope global 2>/dev/null | awk '{print $4}' | head -1 || true)"
	if [[ -z "$cidr" ]]; then
		echo "Pas d'IPv4 sur $iface (hors ligne ou DHCP en attente ?)" >&2
		return 1
	fi

	PBX_LAN_IP="${cidr%%/*}"
	MGMT_CIDR="$(ip -4 route show dev "$iface" proto kernel scope link 2>/dev/null | awk '{print $1}' | head -1 || true)"
	if [[ -z "$MGMT_CIDR" ]]; then
		# repli : masque /24 si route kernel absente
		local prefix="${cidr#*/}"
		if [[ "$prefix" == "24" ]]; then
			local o1 o2 o3 _rest
			IFS=. read -r o1 o2 o3 _rest <<<"$PBX_LAN_IP"
			MGMT_CIDR="${o1}.${o2}.${o3}.0/24"
		else
			MGMT_CIDR="$cidr"
		fi
	fi

	MGMT_GW="$(ip -4 route show dev "$iface" 2>/dev/null | awk '/^default / { print $3; exit }')"
	if [[ -z "$MGMT_GW" ]]; then
		MGMT_GW="$(ip -4 route show default 2>/dev/null | awk '{ print $3; exit }')"
	fi

	export PBX_LAN_IP MGMT_CIDR MGMT_GW
	return 0
}

detect_public_ip() {
	PUBLIC_IP=""
	if command -v curl >/dev/null 2>&1; then
		PUBLIC_IP="$(curl -fsS --max-time 8 https://ifconfig.me 2>/dev/null || curl -fsS --max-time 8 https://api.ipify.org 2>/dev/null || true)"
	fi
	export PUBLIC_IP
}
