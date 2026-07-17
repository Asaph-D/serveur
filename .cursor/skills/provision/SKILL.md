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
| API remote | Cloudflare Tunnel trycloudflare (URL dans bootstrap GitHub) | PHP sur PBX ; bootstrap republié au boot |
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

## Flux Asaphone — connexion VPN (MVP, sans compte)

**Pas de register, verify, e-mail ni session_token** pour la connexion VPN.

```
4G → api_remote
 │
 ├─► POST vpn/enroll  { "device_id": "<uuid stable app>" }
 │       → claim_url, deeplink, tunnel_ip
 │
 ├─► GET  vpn/claim?token=…
 │       → config WireGuard (+ sip_server / wss_url hints)
 │
 ▼
tunnel actif  (= dans le réseau site)
 │
 └─► SIP / session : hors scope MVP connexion VPN
```

`PROVISION_VPN_CONNECT_MODE=open` dans `network/provision.env`.

`vpn/register` et `vpn/verify` : **non utilisés** par l’app (admin / legacy).

Compte SIP (register → verify → session) : **phase ultérieure**, pas mélangée au VPN pour l’instant.

Sur LAN : `api_lan` ; hors LAN : **`api_remote`** (jamais `pbx.local` avant tunnel).

## Endpoints PBX (`provision/api/v1/`)

| Fichier | Méthode | Corps | Flux app |
|---------|---------|-------|----------|
| `vpn/enroll.php` | POST | `{"device_id":"…"}` | **Connexion VPN** |
| `vpn/revoke.php` | POST | `{"device_id":"…"}` | **Révoquer appareil** |
| `vpn/claim.php` | GET | `?token=` | **Connexion VPN** |
| `register.php` | POST | email | Compte (plus tard) |
| `verify.php` | POST | email+code | Compte (plus tard) |
| `session.php` | GET | `?token=` | SIP (plus tard) |
| `groups/sync.php` | POST | `groups[]` | Sync messagerie → `call_uri` |
| `groups/list.php` | GET | `?ext=` + jti | Liste groupes |
| `conference/invite.php` | POST | `room`, `extensions[]` | Inviter en cours d'appel |
| `vpn/register.php` | POST | email | **Hors flux app** |
| `vpn/verify.php` | POST | email+code | **Hors flux app** |

## Appels de groupe (ConfBridge)

Doc complète : `docs/asaphone-group-conference.md`

- Client compose **`call_uri`** (ex. `asaphone-grp-…` ou `6000`) — **un seul appel SIP**
- PBX : ConfBridge + originate vers membres
- Sync : `POST groups/sync` avec `jti` ; session/reconnect inclut `groups[]` + `conference`

## curl de test

```bash
# Discovery (GitHub — doit passer partout)
curl -s 'https://asaph-d.github.io/Portfolio/provision/bootstrap.json'

# API sur LAN
curl -sk 'https://pbx.local/provision/'

# API distante (forward 443 requis)
curl -sk --max-time 15 'https://143.105.152.123/provision/'

# Révoquer un appareil (mode open) puis ré-enrôler
API="$(jq -r .api_remote bootstrap.json)"
DEVICE_ID="f4d4d618-5cca-44a2-9ae1-90498a6a1531"
curl -sk -X POST "$API/api/v1/vpn/revoke.php" \
  -H 'Content-Type: application/json' \
  -d "{\"device_id\":\"$DEVICE_ID\"}"
curl -sk -X POST "$API/api/v1/vpn/enroll.php" \
  -H 'Content-Type: application/json' \
  -d "{\"device_id\":\"$DEVICE_ID\"}"
```

## Config serveur

- `network/global-config.env` — **source unique** ; section `AUTO-GENERATED` = LAN + IP publique + tunnel Cloudflare
- `bash scripts/sync-global-config.sh` — détecte IP sur `MGMT_IFACE` + lit `/etc/provision/tunnel.env`
- Au boot : `serveur-startup.service` → `refresh-tunnel-url.sh` → `sync-global-config.sh --deploy`
- `network/site.env` / `network/provision.env` — incluent global-config
- Déployer : `sudo bash scripts/provision-install.sh`
- Schéma VPN : `scripts/provision-schema-vpn.sql`

## Sans domaine propre

GitHub Pages / Vercel = statique seulement. Tunnel **quick** + `publish-bootstrap-github.sh` au boot.

```bash
echo "ghp_xxx" | sudo tee /etc/provision/github-token && sudo chmod 600 /etc/provision/github-token
sudo bash scripts/install-provision-tunnel.sh
```

## Avec domaine (Cloudflare)

```bash
# PROVISION_PUBLIC_HOST + CLOUDFLARE_TUNNEL_MODE=named dans global-config.env
sudo bash scripts/install-provision-tunnel.sh
```

## Port forward box

**Starlink (CGNAT)** : pas de UDP entrant. Accès distant via **relay WSS intégré Asaphone** (pas d’app externe) :

```bash
sudo bash scripts/install-wg-wss-relay.sh
```

`claim` / bootstrap exposent `tunnel.wss_url` + `path_prefix` ; l’app ouvre le relay puis WireGuard vers `127.0.0.1:51820`.

**Box classique** : forward UDP `51820` → IP LAN du PBX.

## Modifier le dépôt serveur

- Claim URLs distantes : `provision_bootstrap_url()` dans `provision/lib/config.php`
- Ne pas pointer `PROVISION_PUBLIC_BASE_URL` vers GitHub Pages (pas de PHP).
