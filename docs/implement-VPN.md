# Implémentation VPN — télétravail vers le PBX

Guide opérationnel pour permettre à un softphone distant (ex. `192.168.137.20`) d’atteindre un PBX fixe sur `192.168.1.61`, sans exposer SIP sur Internet.

**Contexte théorique** : `docs/vpn.md`

**Prérequis serveur** : FreePBX opérationnel, `network/site.env` configuré, `scripts/net-apply-site.sh` déjà exécuté au moins une fois.

---

## 1. Objectif et principe

```text
PC distant (192.168.137.20)          PBX fixe (site)
        │                                   │
        │  tunnel chiffré (WireGuard)       │
        └──────────────► 10.200.0.2 ──────►│ 192.168.1.61
                                            │ 10.10.10.10 (VLAN 10, inchangé)
```

Le PBX **voit l’IP du tunnel** (`10.200.0.x`), **pas** l’IP du LAN distant (`192.168.137.20`).

Conséquences :
- Il faut autoriser le **sous-réseau VPN** dans `site.env` (pas le LAN chez M. Dupont).
- Le VLAN 10 local **n’est pas modifié** ; les téléphones sur site continuent normalement.

---

## 2. Choix de solution

| Solution | Difficulté | Recommandation |
|----------|----------|----------------|
| **WireGuard** sur le PBX | Moyenne | **Recommandé** — contrôle total, pas de compte tiers |
| **Tailscale** | Faible | Bon pour démarrer vite ; réseau overlay `100.x.x.x` |
| OpenVPN | Élevée | Non documenté ici |

Ce guide détaille **WireGuard** (§3–8) puis **Tailscale** (§9).

---

## 3. Plan d’adressage VPN (WireGuard)

| Élément | Valeur proposée |
|---------|-----------------|
| Interface serveur | `wg0` |
| Sous-réseau VPN | `10.200.0.0/24` |
| IP serveur (PBX) | `10.200.0.1/24` |
| IP client 1 (M. Dupont) | `10.200.0.2/32` |
| Port UDP public | `51820` |
| Réseaux routés vers le client | `192.168.1.0/24`, `10.10.10.0/24` (optionnel) |

> Adapte `10.200.0.0/24` si ce préfixe existe déjà ailleurs.

---

## 4. Installation WireGuard sur le serveur PBX

Exécuter sur le Linux qui héberge FreePBX (`192.168.1.61`).

### 4.1 Paquets

```bash
sudo apt-get update
sudo apt-get install -y wireguard wireguard-tools
```

### 4.2 Clés serveur

```bash
sudo install -d -m 0700 /etc/wireguard
cd /etc/wireguard
sudo wg genkey | sudo tee server.key | sudo wg pubkey | sudo tee server.pub
sudo chmod 600 server.key
```

### 4.3 Configuration serveur `/etc/wireguard/wg0.conf`

Remplacer `ETH_IF` par l’interface vers Internet (souvent `ens33`) et `PUBLIC_IP` par l’IP publique du site (ou IP du routeur si NAT).

```ini
[Interface]
Address = 10.200.0.1/24
ListenPort = 51820
PrivateKey = <contenu de /etc/wireguard/server.key>
# Transmettre le trafic des clients VPN vers le LAN du PBX
PostUp   = sysctl -w net.ipv4.ip_forward=1; iptables -A FORWARD -i wg0 -o ETH_IF -j ACCEPT; iptables -A FORWARD -i ETH_IF -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -o ETH_IF -j ACCEPT; iptables -D FORWARD -i ETH_IF -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# Client : M. Dupont
[Peer]
PublicKey = <clé publique du client>
AllowedIPs = 10.200.0.2/32
```

Rendre le forwarding permanent :

```bash
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-wireguard.conf
sudo sysctl --system
```

### 4.4 Démarrage

```bash
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
sudo wg show
```

### 4.5 Routeur (si PBX derrière NAT)

Sur la box / routeur du site :

- **Port forwarding** : UDP `51820` → `192.168.1.61:51820`
- Vérifier que l’IP publique est stable ou utiliser un DNS dynamique (optionnel)

### 4.6 UFW — autoriser WireGuard

```bash
sudo ufw allow 51820/udp comment "WireGuard VPN"
sudo ufw reload
```

---

## 5. Configuration client (M. Dupont)

### 5.1 Génération des clés (sur le PC distant)

```bash
wg genkey | tee client.key | wg pubkey | tee client.pub
```

Transmettre **`client.pub`** au serveur et ajouter le bloc `[Peer]` dans `/etc/wireguard/wg0.conf`, puis :

```bash
sudo systemctl restart wg-quick@wg0
```

### 5.2 Fichier client `dupont.conf` (Windows / Linux)

Remplacer `PUBLIC_IP` par l’IP publique du site.

```ini
[Interface]
PrivateKey = <contenu client.key>
Address = 10.200.0.2/32
DNS = 192.168.1.1

[Peer]
PublicKey = <contenu /etc/wireguard/server.pub>
Endpoint = PUBLIC_IP:51820
# Seuls les réseaux du PBX passent dans le tunnel (split tunnel)
AllowedIPs = 192.168.1.0/24, 10.10.10.0/24, 10.200.0.0/24
PersistentKeepalive = 25
```

**Windows** : installer [WireGuard](https://www.wireguard.com/install/), importer `dupont.conf`, activer le tunnel.

**Linux** :

```bash
sudo cp dupont.conf /etc/wireguard/wg0.conf
sudo wg-quick up wg0
```

### 5.3 Vérification connectivité

Depuis le PC distant, **tunnel actif** :

```bash
ping -c 3 192.168.1.61
ping -c 3 10.10.10.10
```

Si le ping échoue : vérifier forwarding, `PostUp` iptables, port forwarding routeur, `sudo wg show` côté serveur.

---

## 6. Intégration avec `site.env` et `net-apply-site.sh`

### 6.1 Mettre à jour `network/site.env`

Ajouter le sous-réseau **VPN** (pas le LAN distant `192.168.137.0/24`) :

```env
# Sous-réseau des clients WireGuard
EXTRA_LAN_CIDRS="192.168.1.0/24 10.200.0.0/24"
```

`net-apply-site.sh` injecte `EXTRA_LAN_CIDRS` dans les **localnets PJSIP** d’Asterisk → le PBX fait confiance aux IP `10.200.0.x`.

### 6.2 Appliquer le profil site

```bash
sudo bash /chemin/vers/serveur/scripts/net-apply-site.sh
```

### 6.3 Règles UFW SIP pour le VPN (important)

Aujourd’hui, `EXTRA_LAN_CIDRS` ouvre **RTP + WebRTC** (8088/8089), mais **pas** SIP 5060/5061.

Pour un softphone **Zoiper / Linphone** (SIP classique ou TLS), ajouter manuellement :

```bash
VPN_CIDR="10.200.0.0/24"

sudo ufw allow from ${VPN_CIDR} to any port 5060 proto udp comment "PJSIP UDP VPN"
sudo ufw allow from ${VPN_CIDR} to any port 5060 proto tcp comment "PJSIP TCP VPN"
sudo ufw allow from ${VPN_CIDR} to any port 5061 proto tcp comment "PJSIP TLS VPN"
sudo ufw allow from ${VPN_CIDR} to any port 5160 proto udp comment "PJSIP 5160 UDP VPN"
sudo ufw allow from ${VPN_CIDR} to any port 5161 proto tcp comment "PJSIP 5161 TLS VPN"
sudo ufw allow from ${VPN_CIDR} to any port 80,443 proto tcp comment "FreePBX UI VPN"
sudo ufw reload
```

**Alternative** (ouvre tout le profil « voix » pour le VPN) : mettre `10.200.0.0/24` dans `EXTRA_VOICE_CIDRS` au lieu des règles manuelles — fonctionne, mais le nommage est moins clair.

Vérifier :

```bash
sudo ufw status numbered
```

---

## 7. Configuration softphone distant

Une fois le VPN actif :

| Paramètre | Valeur |
|-----------|--------|
| **Serveur / domaine** | `192.168.1.61` ou `pbx.local` (si hosts Windows) |
| **Port** | `5061` (TLS recommandé, Phase 4) ou `5060` (UDP) |
| **Transport** | TLS ou UDP selon profil |
| **Utilisateur** | Extension (ex. `1001`) |
| **Mot de passe** | Secret PJSIP de l’extension |

**Ne pas** configurer le softphone sur `10.200.0.1` sauf test ; l’IP cible reste **`192.168.1.61`** (interface gestion du PBX).

### Fichier hosts Windows (optionnel)

Sur le PC distant, en admin — `C:\Windows\System32\drivers\etc\hosts` :

```text
192.168.1.61  pbx.local  pbx
```

(même ligne que `network/windows-hosts.txt` généré par `net-apply-site.sh`)

### WebRTC via VPN

Si WebRTC (navigateur) : URL `wss://pbx.local:8089/ws` — fonctionne si `10.200.0.0/24` est dans `EXTRA_LAN_CIDRS` (ports 8088/8089 déjà gérés par le script).

---

## 8. Vérifications finales

### 8.1 Réseau

```bash
# Côté serveur
sudo wg show
ip addr show wg0

# Côté client (tunnel up)
ping 192.168.1.61
```

### 8.2 SIP / Asterisk

```bash
# Sur le PBX
sudo asterisk -rx "pjsip show contacts"
sudo asterisk -rx "pjsip show endpoint 1001"
```

Le contact enregistré doit montrer une IP **`10.200.0.2`** (IP tunnel), pas `192.168.137.20`.

### 8.3 Test d’appel

1. Activer le VPN
2. Lancer Zoiper / Linphone
3. Vérifier statut **Enregistré**
4. Appeler une extension interne (ex. `1002`)

### 8.4 Checklist

| Étape | OK ? |
|-------|------|
| Tunnel WireGuard actif | ☐ |
| Ping `192.168.1.61` depuis le client | ☐ |
| `10.200.0.0/24` dans `EXTRA_LAN_CIDRS` | ☐ |
| `net-apply-site.sh` exécuté | ☐ |
| Règles UFW SIP pour `10.200.0.0/24` | ☐ |
| Softphone enregistré (`pjsip show contacts`) | ☐ |
| Appel test réussi | ☐ |

---

## 9. Option B — Tailscale (plus simple)

Si WireGuard manuel est trop lourd :

### 9.1 Installation

```bash
# Serveur PBX
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# PC distant
# Installer Tailscale depuis https://tailscale.com/download
# Se connecter au même « tailnet »
```

### 9.2 Adresses

Tailscale attribue des IP `100.x.x.x` (ex. PBX `100.64.0.1`, client `100.64.0.2`).

### 9.3 `site.env`

```env
EXTRA_LAN_CIDRS="192.168.1.0/24 100.64.0.0/10"
```

> Utiliser le préfixe Tailscale de ton tailnet (voir `tailscale ip -4` et la doc admin).

### 9.4 UFW

Même limitation que WireGuard : ajouter les règles SIP manuelles pour le CIDR Tailscale, ou utiliser `EXTRA_VOICE_CIDRS`.

### 9.5 Softphone

Configurer le serveur SIP sur l’**IP Tailscale du PBX** (`100.x.x.x`), pas sur `192.168.1.61`, sauf si tu actives **subnet routing** Tailscale pour annoncer `192.168.1.0/24`.

Subnet routing (option avancée) :

```bash
# Sur le PBX
sudo tailscale up --advertise-routes=192.168.1.0/24,10.10.10.0/24
# Approuver les routes dans l’admin Tailscale
```

Avec subnet routing, le softphone peut garder `192.168.1.61` comme serveur.

---

## 10. Dépannage

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| Tunnel up, pas de ping PBX | Forwarding / iptables / route | `sysctl net.ipv4.ip_forward`, `PostUp`, `wg show` |
| Ping OK, softphone hors ligne | UFW bloque SIP | Règles §6.3 pour `10.200.0.0/24` |
| REGISTER OK, pas d’audio | RTP bloqué | Vérifier UFW `10000:20000/udp` depuis VPN CIDR |
| Contact avec IP `192.168.137.x` | Trafic **hors** tunnel | Vérifier `AllowedIPs` client WireGuard |
| TLS échoue | Certificat / port 5061 | `S4-Phase4-Securite-complete.md`, certificat PJSIP |
| `pbx.local` ne résout pas | mDNS absent sur VPN | Fichier `hosts` §7 |

### Logs utiles

```bash
sudo journalctl -u wg-quick@wg0 -b --no-pager
sudo tail -f /var/log/asterisk/full
sudo ufw status verbose
```

---

## 11. Sécurité

- **Ne pas** exposer le port SIP `5060` sur Internet sans VPN — préférer le tunnel.
- Conserver **Fail2Ban** actif (`S4-Phase4-Securite-complete.md`) : une IP VPN compromise peut déclencher un ban.
- Limiter les peers WireGuard : un bloc `[Peer]` par utilisateur, révoquer en supprimant le peer.
- Préférer **TLS 5061 + SRTP** pour les softphones distants.
- Sauvegarder `/etc/wireguard/` (chmod 600 sur les clés privées).

---

## 12. Résumé des fichiers touchés

| Fichier / service | Rôle |
|-------------------|------|
| `/etc/wireguard/wg0.conf` | Config serveur WireGuard |
| `dupont.conf` (client) | Config PC distant |
| `network/site.env` | `EXTRA_LAN_CIDRS` + VPN CIDR |
| `scripts/net-apply-site.sh` | localnets + UFW partiel |
| Règles UFW manuelles §6.3 | SIP complet depuis VPN |
| Routeur | Forward UDP 51820 |

---

## Documents liés

- `docs/vpn.md` — concepts VLAN 10, VPN vs trunk
- `network/site.env` — profil réseau site
- `scripts/net-apply-site.sh` — application UFW + localnets
- `S4-Phase4-Securite-complete.md` — TLS, SRTP, Fail2Ban
- `S2-Phase2-Utilisateurs-Extensions.md` — paramètres softphone Zoiper/Linphone
- `webrtc/README.md` — WebRTC / WSS via VPN
