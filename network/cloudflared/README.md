# Reverse proxy provision — Cloudflare Tunnel

Sans box ni port-forward : **cloudflared** ouvre un tunnel sortant vers Apache local.

## Sans domaine propre (GitHub / Vercel uniquement)

GitHub Pages et Vercel servent des **fichiers statiques** — ils ne peuvent pas exécuter l’API PHP du PBX.

Solution retenue :

| Couche | URL | Rôle |
|--------|-----|------|
| **Découverte** | `https://asaph-d.github.io/Portfolio/provision/bootstrap.json` | Toujours la même |
| **API** | `https://xxxx.trycloudflare.com/provision` | Tunnel sortant vers le PBX |
| **Mise à jour** | Auto au boot | `publish-bootstrap-github.sh` pousse le nouveau `api_remote` |

### Installation

```bash
# 1. Token GitHub (PAT, scope repo) pour le dépôt Portfolio
echo "ghp_xxxx" | sudo tee /etc/provision/github-token
sudo chmod 600 /etc/provision/github-token

# 2. Tunnel quick (défaut dans global-config.env)
sudo bash scripts/install-provision-tunnel.sh
# ou explicitement : sudo bash scripts/install-provision-tunnel.sh --quick
```

Au reboot, `serveur-startup.service` : cloudflared → nouvelle URL → sync → push GitHub.

Les apps Asaphone lisent toujours la **même** `discovery_url` ; le JSON contient la `api_remote` à jour.

### Test

```bash
curl -s 'https://asaph-d.github.io/Portfolio/provision/bootstrap.json' | jq .api_remote
```

---

## Avec domaine propre (production)

Si vous achetez un domaine (≈10 €/an) et l’ajoutez à Cloudflare :

```bash
# global-config.env
CLOUDFLARE_TUNNEL_MODE="named"
PROVISION_PUBLIC_HOST="provision.mondomaine.fr"
GITHUB_BOOTSTRAP_PUBLISH="no"   # plus besoin de republier à chaque boot

sudo bash scripts/install-provision-tunnel.sh
```

---

## Fichiers

| Fichier | Rôle |
|---------|------|
| `network/global-config.env` | Mode tunnel + repo GitHub |
| `/etc/provision/github-token` | PAT publication bootstrap |
| `systemd/cloudflared-provision-quick.service` | Tunnel trycloudflare |
| `systemd/cloudflared-provision.service` | Tunnel nommé (domaine fixe) |

## Commandes

```bash
sudo systemctl status cloudflared-provision
bash scripts/sync-global-config.sh
bash scripts/publish-bootstrap-github.sh   # manuel si besoin
```

VPN WireGuard (UDP 51820) reste séparé.
