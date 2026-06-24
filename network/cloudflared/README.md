# Reverse proxy provision — Cloudflare Tunnel

Sans box ni port-forward : **cloudflared** ouvre un tunnel sortant vers Apache local.

## Installation

```bash
sudo bash scripts/install-provision-tunnel.sh
```

Résultat : URL publique du type `https://xxxx.trycloudflare.com/provision/`

## Fichiers

| Fichier | Rôle |
|---------|------|
| `systemd/cloudflared-provision.service` | Service tunnel → `http://127.0.0.1:80` (Host: pbx.local) |
| `/etc/provision/tunnel.env` | URL générée automatiquement |
| `network/github-pages/provision/bootstrap.json` | `api_remote` doit pointer vers cette URL |

## Commandes

```bash
sudo systemctl status cloudflared-provision
sudo journalctl -u cloudflared-provision -f
curl -sk "$(grep PROVISION_PUBLIC_BASE_URL /etc/provision/tunnel.env | cut -d= -f2 | tr -d '\"')/"
```

## Production stable

L’URL **trycloudflare** change à chaque redémarrage. Pour une URL fixe :

1. Compte [Cloudflare](https://dash.cloudflare.com/)
2. `cloudflared tunnel login`
3. `cloudflared tunnel create asaphone-provision`
4. Configurer ingress vers `http://127.0.0.1:80` + `httpHostHeader: pbx.local`
5. DNS CNAME vers le tunnel (ex. `provision.tondomaine.com`)

VPN WireGuard (UDP 51820) reste séparé — le tunnel ne remplace pas WireGuard pour SIP/RTP.
