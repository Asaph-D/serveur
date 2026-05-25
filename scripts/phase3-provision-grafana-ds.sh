#!/bin/bash
# Enregistre la datasource InfluxDB (Flux) dans Grafana via l’API REST.
set -euo pipefail
cd "$(dirname "$0")/../monitoring"
if [[ ! -f .env ]]; then
	echo "Créez monitoring/.env (scripts/phase3-gen-monitoring-env.sh)." >&2
	exit 1
fi
set -a && source ./.env && set +a
BODY=$(python3 -c "
import json, os
print(json.dumps({
  'name': 'InfluxDB-VoIP',
  'type': 'influxdb',
  'access': 'proxy',
  'url': 'http://127.0.0.1:8086',
  'isDefault': True,
  'jsonData': {
    'version': 'Flux',
    'organization': os.environ.get('INFLUX_ORG', 'voip'),
    'defaultBucket': os.environ.get('INFLUX_BUCKET', 'asterisk'),
    'tlsSkipVerify': False
  },
  'secureJsonData': { 'token': os.environ['INFLUX_ADMIN_TOKEN'] }
}))
")
CODE=$(curl -sS -o /tmp/grafana-ds.out -w "%{http_code}" \
	-u "${GRAFANA_ADMIN_USER:-admin}:${GRAFANA_ADMIN_PASSWORD}" \
	-H "Content-Type: application/json" \
	-X POST "http://127.0.0.1:3000/api/datasources" \
	-d "$BODY")
cat /tmp/grafana-ds.out
echo ""
if [[ "$CODE" != "200" && "$CODE" != "409" ]]; then
	echo "Erreur HTTP $CODE (409 = datasource déjà présente, OK)." >&2
	[[ "$CODE" == "409" ]] || exit 1
fi
echo "Grafana : http://127.0.0.1:3000 — datasource InfluxDB-VoIP prête."
