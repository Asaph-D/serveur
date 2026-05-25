#!/bin/bash
# Génère monitoring/.env avec mots de passe aléatoires (à exécuter depuis le dossier serveur).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENVF="$ROOT/monitoring/.env"
if [[ -f "$ENVF" ]]; then
	echo "Existe déjà : $ENVF — supprimez-le pour régénérer." >&2
	exit 1
fi
INFLUX_PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
GRAFANA_PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
AMI_PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
# Token InfluxDB v2 (doit être une chaîne fournie par l’admin au setup docker ; format aléatoire OK)
INFLUX_TOKEN=$(openssl rand -hex 32)

cat > "$ENVF" <<EOF
INFLUX_ADMIN_USER=admin
INFLUX_ADMIN_PASSWORD=${INFLUX_PASS}
INFLUX_ORG=voip
INFLUX_BUCKET=asterisk
INFLUX_ADMIN_TOKEN=${INFLUX_TOKEN}

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=${GRAFANA_PASS}

AMI_TELEGRAF_USER=telegraf
AMI_TELEGRAF_PASSWORD=${AMI_PASS}
EOF
chmod 600 "$ENVF"
echo "Créé $ENVF (permissions 600). Conservez ce fichier confidentiel."
