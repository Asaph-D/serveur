#!/bin/bash
# Applique trunks SIP + routes + UFW opérateur depuis network/trunks.env
# Exécuter : sudo bash /home/asaph/Documents/serveur/scripts/apply-trunks.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/network/trunks.env"
SECRETS="/root/trunks-secrets.env"
EXAMPLE="$ROOT/network/trunks.secrets.env.example"

[[ $(id -u) -eq 0 ]] || { echo "Root requis."; exit 1; }
[[ -f "$CFG" ]] || { echo "Config introuvable: $CFG"; exit 1; }

# shellcheck disable=SC1090
source "$CFG"

if [[ "${TRUNKS_ENABLE:-yes}" != "yes" ]]; then
	echo "TRUNKS_ENABLE != yes — rien à faire."
	exit 0
fi

if [[ ! -f "$SECRETS" && -f "$EXAMPLE" ]]; then
	install -m 0600 "$EXAMPLE" "$SECRETS"
	echo "Créé $SECRETS — renseigner les identifiants opérateur puis relancer."
fi

echo "=== 1) Trunks + routes FreePBX ==="
php "$ROOT/scripts/apply-trunks.php"

echo "=== 2) UFW — IP opérateur trunk (si définies) ==="
if [[ -n "${PSTN_OPERATOR_CIDRS:-}" ]]; then
	read -r -a _op_cidrs <<< "${PSTN_OPERATOR_CIDRS}"
	for c in "${_op_cidrs[@]}"; do
		[[ -z "${c}" ]] && continue
		ufw allow from "${c}" to any port 5060 proto udp comment "Trunk PSTN SIP UDP ${c}" >/dev/null || true
		ufw allow from "${c}" to any port 5060 proto tcp comment "Trunk PSTN SIP TCP ${c}" >/dev/null || true
		ufw allow from "${c}" to any port 5061 proto tcp comment "Trunk PSTN SIP TLS ${c}" >/dev/null || true
		ufw allow from "${c}" to any port 10000:20000 proto udp comment "Trunk PSTN RTP ${c}" >/dev/null || true
	done
	ufw reload >/dev/null || true
	echo "Règles UFW opérateur appliquées."
else
	echo "PSTN_OPERATOR_CIDRS vide — ajouter les IP/CIDR opérateur dans $CFG quand l'offre est connue."
fi

echo "=== 3) Reload FreePBX / Asterisk ==="
if command -v fwconsole >/dev/null 2>&1; then
	fwconsole reload
else
	asterisk -rx "module reload res_pjsip.so" || true
fi

echo "=== 4) Vérifications ==="
asterisk -rx "pjsip show endpoints" 2>/dev/null | grep -E 'trunk-|Endpoint:' || true
asterisk -rx "pjsip show registrations" 2>/dev/null || true
echo "Routes sortantes :"
asterisk -rx "dialplan show outbound-allroutes" 2>/dev/null | head -20 || true

echo "OK."
echo "- Trunks FreePBX : Connectivité → Trunks"
echo "- Secrets opérateur : $SECRETS"
echo "- Config : $CFG"
