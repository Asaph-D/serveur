# Stack monitoring VoIP

| Service | Rôle |
|---------|------|
| **InfluxDB 2** | Stockage séries (`bucket: asterisk`, `org: voip`) |
| **Telegraf** | `ami_metrics.py` (AMI Asterisk) → Influx |
| **Grafana** | Dashboards Flux (datasource **InfluxDB-VoIP** provisionnée) |

**Prometheus** : absent. Chaîne : **Telegraf → InfluxDB → Grafana**.

```bash
cp .env.example .env   # ou scripts/phase3-gen-monitoring-env.sh
docker compose up -d
```

Dashboard : dossier Grafana **VoIP** → **VoIP / Asterisk — monitoring**.

Fichiers : `grafana/provisioning/`, `grafana/dashboards/voip-asterisk.json`, `telegraf/`.
