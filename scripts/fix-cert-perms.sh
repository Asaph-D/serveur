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
# FreePBX Certman (PKCS) : propriétaire www-data. Groupe asterisk pour que le démon
# (-U asterisk -G asterisk) lise les *.key en 0640 sans dépendre des groupes supplémentaires.
CERT_OWNER="${CERT_OWNER:-www-data}"
CERT_GROUP="${CERT_GROUP:-asterisk}"
AST_USER="${FREEPBX_AST_USER:-asterisk}"
[[ $(id -u) -eq 0 ]] || { echo "Root requis." >&2; exit 1; }

usermod -aG "$CERT_GROUP" "$CERT_OWNER" 2>/dev/null || true
usermod -aG "$CERT_GROUP" "$AST_USER" 2>/dev/null || true

if [[ ! -d "$KEYDIR" ]]; then
  echo "Dossier introuvable: $KEYDIR" >&2
  exit 1
fi

# Ownership attendu (FreePBX / Certman)
chown -R "${CERT_OWNER}:${CERT_GROUP}" "$KEYDIR"

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

