#!/bin/bash
# Normalise les permissions des certificats FreePBX/Certman.
#
# Objectif :
# - Certificats/chaînes (*.crt, *.pem, *.csr) : lisibles (644) si nécessaire
# - Clés privées (*.key) : par défaut strictes (600). Peut être ajusté via KEY_MODE
#
# Usage :
#   sudo bash /home/asaph/Documents/serveur/scripts/fix-cert-perms.sh
#
set -euo pipefail

KEYDIR="/etc/asterisk/keys"
KEY_MODE="${KEY_MODE:-0640}" # 0640 (groupe) recommandé ici. Alternative plus stricte: 0600
[[ $(id -u) -eq 0 ]] || { echo "Root requis." >&2; exit 1; }

if [[ ! -d "$KEYDIR" ]]; then
  echo "Dossier introuvable: $KEYDIR" >&2
  exit 1
fi

# Ownership attendu (Asterisk tourne en user asterisk)
chown -R asterisk:asterisk "$KEYDIR"

# Certificats publics et chaînes : lecture OK
find "$KEYDIR" -type f \( -name "*.crt" -o -name "*.pem" -o -name "*.csr" \) -print0 \
  | xargs -0r chmod 0644

# Clés privées : strictes
find "$KEYDIR" -type f -name "*.key" -print0 \
  | xargs -0r chmod "$KEY_MODE"

# Dossiers : traversables + écriture via groupe (FreePBX web = www-data ∈ groupe asterisk)
# setgid (2) pour conserver le groupe sur les nouveaux fichiers.
find "$KEYDIR" -type d -print0 | xargs -0r chmod 2775

echo "OK: permissions normalisées dans $KEYDIR"
echo "  - *.key mode: $KEY_MODE"

