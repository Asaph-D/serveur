---
name: provision
description: >-
  Configures and debugs Asaphone PBX provisioning (SIP QR, VPN WireGuard, GitHub
  Pages bootstrap). Use when working on provision API, onboarding, claim tokens,
  VPN enroll, bootstrap.json, pbx.local, or network/github-pages/provision.
---

# Provision Asaphone

## Architecture

| Couche | URL | Rôle |
|--------|-----|------|
| Discovery | `https://asaph-d.github.io/Portfolio/provision/bootstrap.json` | Toujours joignable ; indique où est l’API |
| API LAN | `https://pbx.local/provision` | Register, verify, claim, VPN |
| API remote | Cloudflare Tunnel `https://*.trycloudflare.com/provision` | Même API PBX via reverse proxy sortant (pas de box) |
| VPN | UDP `143.105.152.123:51820` | Tunnel WG après réception du `.conf` |

GitHub Pages = **fichier JSON statique** uniquement. L’API PHP reste sur le PBX.

## Publier / mettre à jour bootstrap (utilisateur)

1. Copier `network/github-pages/provision/bootstrap.json` → dépôt Portfolio :
   `Portfolio/provision/bootstrap.json`
2. `git add provision/bootstrap.json && git commit && git push`
3. Vérifier :
   ```bash
   curl -s 'https://asaph-d.github.io/Portfolio/provision/bootstrap.json' | jq .
   ```
4. Si IP publique change : éditer `api_remote` et `vpn.endpoint_remote` dans ce JSON.

## Flux Asaphone (app)

1. `GET discovery_url` → lire `api_lan` / `api_remote`
2. Sur LAN : utiliser `api_lan` ; hors LAN : `api_remote` (si 443 forward OK)
3. SIP : register → verify → claim
4. VPN (optionnel, hors LAN) : vpn_register → vpn_verify → vpn_claim **ou** vpn_enroll (ext+jti)
5. Activer tunnel WG → puis WSS `wss://pbx.local:8089/ws`

## Endpoints PBX (`provision/api/v1/`)

| Fichier | Méthode | Corps |
|---------|---------|-------|
| `register.php` | POST | `{"email":"..."}` |
| `verify.php` | POST | `{"email":"...","code":"123456"}` |
| `claim.php` | POST | `{"token":"..."}` |
| `vpn/register.php` | POST | `{"email":"..."}` |
| `vpn/verify.php` | POST | `{"email":"...","code":"..."}` |
| `vpn/claim.php` | POST | `{"token":"..."}` |
| `vpn/enroll.php` | POST | `ext` + `jti` + header `X-Provision-Jti` |
| `vpn/status.php` | GET | `?email=...` |

## curl de test

```bash
# Discovery (GitHub — doit passer partout)
curl -s 'https://asaph-d.github.io/Portfolio/provision/bootstrap.json'

# API sur LAN
curl -sk 'https://pbx.local/provision/'

# API distante (forward 443 requis)
curl -sk --max-time 15 'https://143.105.152.123/provision/'
```

## Config serveur

- `network/provision.env` — `PROVISION_DISCOVERY_URL`, `PROVISION_PUBLIC_*`, VPN
- Déployer : `sudo bash scripts/provision-install.sh`
- Schéma VPN : `scripts/provision-schema-vpn.sql`

## Reverse proxy (sans box)

```bash
sudo bash scripts/install-provision-tunnel.sh
```

Cloudflare Tunnel → Apache local. URL dans `/etc/provision/tunnel.env`.

## Port forward box

**Non requis** pour l’API provision (tunnel Cloudflare).  
VPN WireGuard UDP **51820** reste nécessaire pour le tunnel WG (sauf si autre solution).

## Modifier le dépôt serveur

- Claim URLs distantes : `provision_bootstrap_url()` dans `provision/lib/config.php`
- Ne pas pointer `PROVISION_PUBLIC_BASE_URL` vers GitHub Pages (pas de PHP).
