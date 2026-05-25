# Phase 3 — IVR intelligent, services avancés, monitoring Grafana + InfluxDB

Document d’exploitation aligné sur le cahier Phase 3 (AGI Python, horaires, file ACD, ConfBridge, trunk modèle, MixMonitor) et sur l’architecture **Grafana + InfluxDB**.

---

## 1. Monitoring (Docker)

| Composant | Rôle | Port hôte |
|-----------|------|-----------|
| **InfluxDB 2** | Séries temporelles (bucket `asterisk`, org `voip`) | **8086** |
| **Grafana** | Tableaux de bord | **3000** |
| **Telegraf** (image maison `voip-telegraf:1.33-ami`) | Exécute `ami_metrics.py` (AMI → métriques) et pousse vers Influx | `network_mode: host` |

**Démarrage**

```bash
cd /home/asaph/Documents/serveur/monitoring
# Si pas encore de secrets :
#   bash ../scripts/phase3-gen-monitoring-env.sh
docker compose up -d
```

**Grafana — datasource + tableau de bord** : provisionnés automatiquement au démarrage du conteneur (`grafana/provisioning/`, dossier **VoIP**). Tableau **« VoIP / Asterisk — monitoring »** : stats *Canaux / Appels actifs* + série temporelle (mesure Influx **`asterisk_core`**). URL type : `http://IP:3000/d/voip-asterisk-pbx/voip-asterisk-monitoring` (titre affiché selon l’UI).

**Prometheus** : **non utilisé** dans cette stack. Les métriques vont **Telegraf → InfluxDB 2 → Grafana (langage Flux)**. Ajouter Prometheus serait un **choix parallèle** (ex. `node_exporter` + datasource Prometheus) sans lien obligatoire avec le flux AMI actuel.

L’ancien script `scripts/phase3-provision-grafana-ds.sh` reste optionnel si la datasource était créée à la main avant le provisioning fichier.

**Pourquoi une image Telegraf custom** : les images officielles n’incluent pas le plugin `[[inputs.asterisk]]`. Le collecteur est un script Python AMI (`telegraf/ami_metrics.py`) invoqué par `[[inputs.exec]]`.

**AMI utilisateur `telegraf`** (`/etc/asterisk/manager_custom.conf`) :

- `permit=127.0.0.1` (conteneur en réseau host → même pile que Asterisk).
- **`write = command`** requis pour l’action AMI `Command: core show channels` (sinon `Permission denied`).
- Mot de passe : identique à `AMI_TELEGRAF_PASSWORD` dans `monitoring/.env` (généré par `phase3-gen-monitoring-env.sh`).

**Grafana — requête Flux exemple** (Explore, datasource InfluxDB-VoIP) :

```flux
from(bucket: "asterisk")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "asterisk_core")
```

**Pare-feu** : ouvrir **3000/tcp** et **8086/tcp** au besoin depuis les LAN autorisés (ex. `192.168.147.0/24`, `10.10.10.0/24`).

---

## 2. Dialplan et services Phase 3

Appliqué par `sudo bash scripts/phase3-apply-asterisk.sh` (idempotent : bloc marqué `BEGIN_PHASE3` / `END_PHASE3`).

| Numéro | Fonction |
|--------|----------|
| **7000** | Routage horaire **GotoIfTime** (lun–ven 09:00–17:59 → **7010**, sinon message fermeture) |
| **7010** | **IVR AGI** : `/var/lib/asterisk/agi-bin/phase3_intelligent_ivr.py` (VIP via `/etc/asterisk/phase3-vip.txt`, logique horaire / langue) |
| **7020** | **Queue** `phase3-support` (**leastrecent**), **MixMonitor** vers `/var/spool/asterisk/monitor/` |
| **8001** | **ConfBridge** — salle `phase3-<PIN>` ; PIN test **1234** (à changer) |
| **8100** | Test **MixMonitor** + renvoi messagerie 1001 |
| **8000** | Inchangé (Phase 2 — sonnerie groupe) |

**File d’attente** : `/etc/asterisk/queues_custom.conf`, section `[phase3-support]` (membres **PJSIP/1001–1005** par défaut — adapter).

**Trunk SIP** : modèle **wizard** commenté dans `/etc/asterisk/pjsip_custom_post.conf` ; en production, préférer **Connectivité → Trunks** FreePBX quand les modules réseau Sangoma sont stables.

**NFS** pour enregistrements : non monté automatiquement — monter un export sur `/var/spool/asterisk/monitor` (ou chemin dédié) côté infra, puis redémarrer Asterisk.

---

## 3. Modules FreePBX (queues, conferences, …)

L’installation `fwconsole ma downloadinstall …` peut **échouer** sur le téléchargement des **gros packs de sons** (timeout). La file d’attente et le dialplan ci-dessus s’appuient sur **`app_queue` / ConfBridge** au niveau Asterisk et sur les fichiers `*_custom.conf`, sans obliger le module GUI **queues** pour une file minimale.

Pour retenter plus tard : `sudo fwconsole ma downloadinstall queues` (ou nuit / miroir plus rapide).

---

## 4. Fichiers utiles

| Fichier |
|---------|
| `monitoring/docker-compose.yml` |
| `monitoring/telegraf/Dockerfile` |
| `monitoring/telegraf/telegraf.conf` |
| `monitoring/telegraf/ami_metrics.py` |
| `scripts/phase3-gen-monitoring-env.sh` |
| `scripts/phase3-provision-grafana-ds.sh` |
| `scripts/phase3-apply-asterisk.sh` |
| `phase3/agi/phase3_intelligent_ivr.py` |
| `phase3/asterisk/phase3-vip.txt` |

---

*Mis à jour lors du déploiement Phase 3 (monitoring AMI + dialplan custom).*
