# Installation & lancement (système vierge)

Ce dépôt contient des scripts et services systemd pour automatiser le démarrage et quelques tâches “post-boot” d’un serveur VoIP (FreePBX/Asterisk), ainsi que l’application d’un profil réseau “site”.

> Important : dans ton usage, la commande correcte n’est pas `sudo start ...` mais **`sudo systemctl start ...`** (systemd).

## Prérequis

- Accès **root** (sudo).
- **systemd** (les scripts utilisent `systemctl`).
- Si FreePBX/Asterisk n’est pas installé, installe d’abord la pile PBX (voir § Versions ci-dessous). Ce dépôt **ne fournit pas** l’installateur officiel FreePBX ; il automatise le post-install (réseau, démarrage, monitoring, sécurité).

### Versions des outils (alignement projet)

Les versions ci-dessous sont celles **documentées ou épinglées** dans ce dépôt (`Architecture-VoIP-communication-composants.md`, `monitoring/docker-compose.yml`, `scripts/install-asterisk-res-srtp.sh`, phases S3/S4). Sur une machine vierge, vise ces versions (ou plus récentes **mineures** compatibles FreePBX 17).

| Composant | Version cible | Rôle / remarque |
|-----------|---------------|-----------------|
| **OS** | **Debian 12** (Bookworm) **ou** **Ubuntu 22.04 LTS** | Recommandé pour FreePBX 17 ; les scripts utilisent `apt-get`. Ubuntu 24.04 fonctionne aussi (Fail2Ban en backend **nftables**, voir `S4-Phase4-Securite-complete.md`). |
| **FreePBX** | **17.x** (dernière 17 stable) | Interface + modules ; commande `fwconsole`. [Installation officielle](https://wiki.freepbx.org/display/FOH/Installing+FreePBX). |
| **Asterisk** | **20.x LTS** — référence projet **`20.18.2`** | Cœur VoIP (PJSIP, ConfBridge, WebRTC). Vérifier : `asterisk -V`. |
| **MariaDB** | **10.6+** (souvent **10.11** sur Debian 12) | Base FreePBX / CDR. Vérifier : `mariadb --version`. |
| **PHP** | **8.2** (fourni avec FreePBX 17) | UI FreePBX + scripts PHP du dépôt. Vérifier : `php -v`. |
| **Apache** | **2.4.x** (paquet `apache2`) | Héberge l’UI FreePBX. Vérifier : `apache2 -v`. |
| **UFW** | paquet `ufw` (dernière du dépôt OS) | Pare-feu ; règles via `net-apply-site.sh`. |
| **Avahi** | paquet `avahi-daemon` | mDNS (`pbx.local`). |
| **Fail2Ban** | **≥ 0.11** | Jail Asterisk (Phase 4). Vérifier : `fail2ban-client --version`. |
| **libsrtp2** | paquet **`libsrtp2-dev`** | Requis si compilation du module **`res_srtp`** (WebRTC). |
| **Python** | **3.10+** (Python 3 système) | AGI Phase 3 (`phase3_intelligent_ivr.py`). |
| **Docker Engine** | **24+** (ou équivalent récent) | Uniquement si `MONITORING_ENABLE="yes"`. |
| **Docker Compose** | **v2** (`docker compose`, plugin) | Stack `serveur/monitoring/`. |
| **InfluxDB** | image **`influxdb:2.7-alpine`** | Séries temporelles (bucket `asterisk`). |
| **Grafana** | image **`grafana/grafana:11.4.0`** | Dashboards (port **3000**). |
| **Telegraf** | image de base **`telegraf:1.33`** → build **`voip-telegraf:1.33-ami`** | Collecte AMI + logs → Influx. |

**Ports réseau utilisés par la stack** (à ouvrir selon `network/site.env`) :

| Service | Port(s) |
|---------|---------|
| SIP UDP/TCP | 5060, 5160 |
| SIP TLS | 5061, 5161 |
| RTP | 10000–20000/udp |
| HTTP Asterisk (WebRTC lab) | 8088/tcp |
| WSS Asterisk (WebRTC) | 8089/tcp |
| UI FreePBX (Apache) | 80/tcp, 443/tcp |
| Grafana / InfluxDB (optionnel) | 3000/tcp, 8086/tcp |

### Installation des paquets système (hors FreePBX)

Sur Debian 12 / Ubuntu 22.04, avant ou après FreePBX :

```bash
sudo apt-get update
sudo apt-get install -y \
  apache2 mariadb-server \
  ufw avahi-daemon \
  fail2ban \
  libsrtp2-dev \
  python3 \
  git curl
```

Puis installer **FreePBX 17** + **Asterisk 20** selon le guide officiel (script Sangoma ou ISO Distro). Après install, contrôler :

```bash
fwconsole -V          # FreePBX
asterisk -V           # doit afficher Asterisk 20.x
php -v                # PHP 8.2.x
apache2 -v            # Apache/2.4.x
```

### Monitoring Docker (versions figées dans le dépôt)

Si tu actives le monitoring :

```bash
sudo apt-get install -y docker.io docker-compose-plugin
# ou paquets équivalents selon ta distro
docker --version
docker compose version
cd serveur/monitoring
docker compose pull   # télécharge influxdb:2.7-alpine, grafana:11.4.0, telegraf:1.33
docker compose build  # construit voip-telegraf:1.33-ami
```

Les tags exacts sont dans `serveur/monitoring/docker-compose.yml`.

### WebRTC / SRTP (si compilation Asterisk)

Le script `serveur/scripts/install-asterisk-res-srtp.sh` suppose les sources Asterisk dans :

- `/usr/src/asterisk-20.18.2` (variable `AST_SRC` modifiable)

```bash
sudo bash serveur/scripts/install-asterisk-res-srtp.sh
asterisk -rx "module show like res_srtp"
```

## 1) Récupérer le projet sur le serveur

Place le dossier `serveur/` sur la machine Linux.

Recommandation : copier ce dépôt dans un chemin stable, par exemple :

- `/opt/serveur-asterisk/serveur`

Les scripts fonctionnent quel que soit l’emplacement **tant que tu adaptes le service systemd** (voir plus bas), car `serveur/systemd/serveur-startup.service` référence actuellement un chemin codé en dur.

## 2) Vérifier/adapter les chemins (IMPORTANT)

Le service `serveur/systemd/serveur-startup.service` contient :

- `ExecStart=/bin/bash /home/asaph/Documents/serveur/scripts/server-startup.sh`

Sur une machine vierge, ce chemin a de grandes chances d’être faux.

Deux options :

- **Option A (recommandée)** : édite `serveur/systemd/serveur-startup.service` et remplace le chemin par l’emplacement réel du script sur ta machine.
- **Option B** : installe le projet exactement dans `/home/asaph/Documents/serveur/` (peu pratique, mais ça évite de modifier le fichier).

## 3) Configurer le profil réseau “site”

Le script `serveur/scripts/net-apply-site.sh` lit la configuration :

- `serveur/network/site.env`

Édite `serveur/network/site.env` et adapte au site :

- `MGMT_CIDR` : réseau de gestion (UI FreePBX)
- `VOICE_CIDR` : réseau VoIP/VLAN voix
- `EXTRA_VOICE_CIDRS` / `EXTRA_LAN_CIDRS` : autres réseaux routés
- `PBX_MDNS_NAME` : nom mDNS (ex. `pbx` -> `pbx.local`)
- options WebRTC/monitoring si utilisées

Puis applique le profil :

```bash
sudo bash serveur/scripts/net-apply-site.sh
```

Ce que fait ce script (résumé) :

- Installe/active **avahi-daemon** (mDNS) si manquant
- Met à jour **FreePBX localnets (PJSIP)** via PHP/DB
- Configure **UFW** (SIP/RTP/WebRTC/monitoring selon `site.env`)
- (Optionnel) démarre `docker compose` dans `serveur/monitoring/`
- `fwconsole reload`
- Génère `serveur/network/windows-hosts.txt` (utile si Windows ne résout pas `.local`)

## 4) Installer le service systemd “startup”

### Méthode simple (copie du unit)

1) Copier le unit :

```bash
sudo install -m 0644 serveur/systemd/serveur-startup.service /etc/systemd/system/serveur-startup.service
```

2) Recharger systemd et activer :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now serveur-startup.service
```

3) Vérifier :

```bash
systemctl status serveur-startup.service --no-pager -l
```

### Méthode via le script d’installation (à utiliser seulement si le chemin correspond)

Un script existe : `serveur/scripts/install-startup-service.sh`.

Attention : il pointe actuellement vers :

- `UNIT_SRC="/home/asaph/Documents/serveur/systemd/serveur-startup.service"`

Si ton dépôt n’est pas installé dans ce chemin, **ce script échouera**. Dans ce cas, utilise la “méthode simple” ci-dessus ou adapte `UNIT_SRC`.

## 5) (Recommandé) Installer le service de permissions certificats FreePBX

Pour normaliser les permissions dans `/etc/asterisk/keys`, tu peux installer :

```bash
sudo bash serveur/scripts/install-cert-perms-service.sh
```

Ce script :

- installe `fix-cert-perms.sh` dans `/usr/local/sbin/fix-cert-perms.sh`
- crée le service `freepbx-cert-perms.service`
- active et démarre le service

## 6) Lancer / relancer le serveur

### Démarrer manuellement le service

```bash
sudo systemctl start serveur-startup.service
```

### Relancer

```bash
sudo systemctl restart serveur-startup.service
```

### Activer au boot (si pas déjà fait)

```bash
sudo systemctl enable serveur-startup.service
```

## 7) Logs & diagnostic

### Logs systemd

```bash
journalctl -u serveur-startup.service -b --no-pager
```

### Log fichier

Le script écrit aussi dans :

- `/var/log/serveur-startup.log`

(Défini par `LOG_FILE` dans `serveur/scripts/server-startup.sh`.)

## 8) Ce que fait exactement `serveur-startup` au boot

Le script `serveur/scripts/server-startup.sh` :

- démarre FreePBX si `fwconsole` est présent : `fwconsole start`
- nettoie les sessions PHP : `/var/lib/php/sessions`
- redémarre Apache2 : `systemctl restart apache2`
- applique le profil réseau : `serveur/scripts/net-apply-site.sh`
- fixe les permissions certificats : `serveur/scripts/fix-cert-perms.sh`

## 9) Dépannage rapide

- `fwconsole introuvable` :
  - FreePBX n’est pas installé ou pas dans le PATH. Installe FreePBX ou adapte le script.
- `Failed to restart apache2` :
  - Apache2 absent ou en erreur. Voir `systemctl status apache2 -l` et `journalctl -u apache2 -b`.
- `Config introuvable: .../serveur/network/site.env` :
  - Le script `net-apply-site.sh` ne trouve pas `site.env` (chemin dépôt incorrect). Vérifie l’emplacement du dossier `serveur/`.
- Problème `.local` sous Windows :
  - utilise la ligne générée dans `serveur/network/windows-hosts.txt` et copie-la dans
    `C:\Windows\System32\drivers\etc\hosts` (en admin).

## Documents complémentaires

- WebRTC : `serveur/webrtc/README.md`
- Monitoring : `serveur/monitoring/README.md`
- Phases et docs réseau/VoIP : fichiers `serveur/S*-Phase*.md` et `serveur/docs/*.md`

