# VPN, trunks SIP et connectivité réseau — guide VoIP

Document de synthèse : rôle du **VLAN 10**, comportement des softphones distants, et comparaison **VPN** vs **trunk SIP** (matériel, logiciel, niveau d’implémentation).

Aligné sur `network/site.env` et `scripts/net-apply-site.sh`.

---

## 1. Architecture de référence

```text
                    Site du PBX (état actuel)
    ┌─────────────────────────────────────────────────────┐
    │  MGMT 192.168.1.0/24                                │
    │    PBX gestion .......... 192.168.1.104  (ens33)    │
    │    Softphone local ...... 192.168.1.101             │
    │                                                     │
    │  VLAN 10 — 10.10.10.0/24 (stable, switch local)   │
    │    PBX voix ............. 10.10.10.10  (ens33.10)   │
    │    Téléphone bureau ..... 10.10.10.50               │
    │                                                     │
    │  VPN WireGuard — 10.200.0.0/24 (wg0)              │
    │    PBX tunnel ............ 10.200.0.1               │
    │    Client distant ........ 10.200.0.2               │
    └─────────────────────────────────────────────────────┘
```

| Réseau | Variable `site.env` | Rôle |
|--------|---------------------|------|
| **MGMT** | `MGMT_CIDR="192.168.1.0/24"` | Admin, UI FreePBX, softphones sur le LAN |
| **VLAN 10 voix** | `VOICE_CIDR="10.10.10.0/24"` | Téléphonie dédiée sur le site (téléphones IP) |
| **Autres LAN clients** | `EXTRA_LAN_CIDRS` | PC Windows, softphones sur d’autres préfixes autorisés |

Le serveur a **trois pattes IP** (état actuel) :
- **gestion** : `192.168.1.104` sur `ens33`
- **voix** : `10.10.10.10` sur `ens33.10` (VLAN 10)
- **VPN** : `10.200.0.1` sur `wg0` (WireGuard, port UDP `51820`)

> Guide d’installation : `docs/implement-VPN.md` — config client : `network/vpn/client-distant.conf`

---

## 2. À quoi sert le VLAN 10 (`10.10.10.10`) ?

### Ce qu’il fait

Le VLAN 10 **isole la téléphonie** du LAN bureautique **sur le site du PBX** :

- QoS prioritaire sur le RTP (DSCP EF)
- Pare-feu : le VLAN voix n’accède pas librement au MGMT
- IP stable pour les téléphones (`10.10.10.10`, `pbx.local`)
- Règles UFW et `localnets` Asterisk pour `10.10.10.0/24`

### Ce qu’il ne fait pas

**Le VLAN 10 ne couvre pas tous les LAN `192.168.x.x`.**

Ce n’est **pas** un réseau universel qui regroupe `192.168.1.0/24`, `192.168.137.0/24`, etc.

| Idée (fausse) | Réalité |
|---------------|---------|
| VLAN 10 = overlay sur tous les `192.168.x.x` | Non — c’est un `/24` local `10.10.10.0/24` |
| `VOICE_CIDR` étend le VLAN à distance | Non — ça **autorise** le trafic **si** la source est sur ce réseau (ou routée vers lui) |
| Un softphone distant est « sur » le VLAN 10 | Non — sans VPN/trunk, il n’y a pas de lien |

```text
                    PBX (deux pattes)
         ┌────────────────────────────────┐
         │ ens33      → 192.168.1.104    │  ← MGMT
         │ ens33.10   → 10.10.10.10      │  ← VLAN 10 (local)
         │ wg0        → 10.200.0.1       │  ← VPN WireGuard
         └────────────────────────────────┘
                    ▲           ▲
         192.168.1.101      10.10.10.50
         (1001 UDP +        (téléphone IP
          1003 WSS)          sur VLAN 10)

    192.168.137.20  ──✗──  n'est sur AUCUN de ces réseaux
    (chez soi)             sans VPN (10.200.0.2) ou lien dédié
```

Le VLAN 10 est une **clôture** autour des téléphones du site, pas un **pont** vers tous les réseaux `192.168.x.x`.

---

## 3. Scénario : softphone qui change de réseau (serveur fixe)

### État initial (tout fonctionne)

M. Dupont, softphone `192.168.1.101` sur `192.168.1.0/24`, PBX `192.168.1.104` :

1. Résout `pbx.local` → mDNS → `192.168.1.104`
2. REGISTER SIP vers `192.168.1.104:5060` (ou TLS `5061`, ou WSS `8089`)
3. UFW : source ∈ `192.168.1.0/24` → **autorisé**
4. Asterisk : source ∈ `localnets` → **OK**
5. RTP UDP `10000–20000` → **autorisé**

Les téléphones VLAN 10 (`10.10.10.50`) continuent via `10.10.10.10`, indépendamment du MGMT.

### M. Dupont part sur `192.168.137.0/24` (`192.168.137.20`)

Le serveur **ne bouge pas** (`192.168.1.104` + `10.10.10.10` + `10.200.0.1`). `site.env` reste `MGMT_CIDR="192.168.1.0/24"`.

```text
    Site PBX (fixe)                      Nouveau lieu
    ┌────────────────────────┐           ┌────────────────────────┐
    │ MGMT 192.168.1.0/24    │    ???    │ LAN 192.168.137.0/24   │
    │  PBX .. 192.168.1.104  │  ◄────►   │  PC .. 192.168.137.20  │
    │  VLAN10 .. 10.10.10.10 │  route ?  │                        │
    └────────────────────────┘           └────────────────────────┘
```

#### Étape 1 — Résolution `pbx.local`

| Action | Résultat |
|--------|----------|
| mDNS `pbx.local` | **Échec** (mDNS ne traverse pas Internet / autre LAN) |
| Fichier `hosts` avec `192.168.1.104` | IP privée **inaccessible** depuis `192.168.137.0/24` |
| Ping `192.168.1.104` | **Échec** (sauf VPN WireGuard actif) |

#### Étape 2 — Routage (couche 3)

Par défaut : **aucun chemin** entre `192.168.137.0/24` et `192.168.1.0/24`. Le VLAN 10 n’entre pas en jeu pour M. Dupont.

#### Étape 3 — Si une route existait (VPN)

| Couche | Comportement serveur |
|--------|----------------------|
| **UFW** | Source `192.168.137.20` ∉ `192.168.1.0/24` → **bloqué** |
| **localnets** | `192.168.137.0/24` absent → SIP/NAT incorrect ou refus |
| **UI FreePBX** | Bloquée aussi |

#### Étape 4 — Côté softphone

```text
T+0   Déconnexion du LAN 192.168.1.0/24 → REGISTER expire (~60–120 s)
T+1   Connexion 192.168.137.0/24 → IP = 192.168.137.20
T+2   Tentative REGISTER vers pbx.local / 192.168.1.61 → échec
T+3   Statut : « Hors ligne » / « Registration failed »
```

#### Étape 5 — Ce qui continue sur le site PBX

| Élément | Statut |
|---------|--------|
| PBX `192.168.1.104` | Inchangé, actif |
| VLAN 10 `10.10.10.10` | Stable, téléphones OK |
| Autres softphones sur `192.168.1.0/24` | OK |

### Correction pour le télétravail

**A. Connectivité** (obligatoire) : VPN utilisateur ou site-à-site (WireGuard, Tailscale, etc.)

**B. `site.env`** (si le VPN donne accès au PBX) :

```env
MGMT_CIDR="192.168.1.0/24"
EXTRA_LAN_CIDRS="192.168.1.0/24 10.200.0.0/24"
```

> **Important** : autoriser le **sous-réseau VPN** (`10.200.0.0/24`), pas le LAN distant (`192.168.137.0/24`). Le PBX voit l’IP tunnel (`10.200.0.2`), pas l’IP du réseau chez M. Dupont.

Puis :

```bash
sudo bash /home/asaph/Documents/serveur/scripts/net-apply-site.sh
```

Configurer le softphone sur **`192.168.1.104`** ou `pbx.local` (fichier `hosts` si mDNS ne traverse pas le VPN). Voir `docs/implement-VPN.md` §6.3 pour les règles UFW SIP complètes.

---

## 4. Qui change quoi quand on bouge de réseau ?

| Question | Réponse |
|----------|---------|
| L’IP utilisateur change-t-elle ? | **Oui**, à chaque nouveau réseau (DHCP). |
| Le serveur s’adapte-t-il seul ? | **Non** — mettre à jour `site.env` + `net-apply-site.sh`. |
| Le VLAN 10 est-il impacté ? | **Non**, tant que l’infra locale reste en place. |
| Que reste stable ? | Nom `pbx.local`, IP voix `10.10.10.10`, extensions SIP. |

---

## 5. Qu’est-ce qui crée un « pont » entre LAN distants ?

### Deux familles à ne pas confondre

| Famille | Ce que ça fait | Exemple |
|---------|----------------|---------|
| **Pont réseau (L3)** | Router des paquets entre sous-réseaux | VPN, routes statiques, MPLS |
| **Pont téléphonie (SIP)** | Relier deux **PBX** ou un PBX à l’**opérateur** | Trunk SIP |
| **Traversée NAT** | Un client derrière une box, sans relier les LAN | STUN/TURN + IP publique |

### Mécanismes détaillés

| Mécanisme | Relie des LAN privés ? | Niveau | Dispositif dédié ? |
|-----------|------------------------|--------|-------------------|
| **VPN site-à-site** | Oui | OS / routeur | Non (souvent) |
| **VPN utilisateur** | Oui (1 PC) | OS serveur + client | Non |
| **Tailscale / ZeroTier** | Oui (overlay) | Agent sur chaque machine | Non |
| **Routes statiques / MPLS / SD-WAN** | Oui | Routeur / opérateur | Parfois (CPE) |
| **Tunnels GRE / IPIP / WireGuard** | Oui | Kernel Linux | Non |
| **Trunk VLAN 802.1Q** | Non (L2 local) | Switch | **Switch** |
| **Trunk SIP** | Non (couche SIP) | FreePBX / Asterisk | Non |
| **NAT + IP publique** | Non (via Internet) | Routeur + FreePBX | Non |
| **STUN / TURN / ICE** | Non | Client + serveur | Non |
| **SBC** | Non (frontal SIP) | Logiciel ou appliance | Optionnel |

### Trunk réseau (802.1Q) vs trunk SIP

- **Trunk VLAN** : étend des VLANs entre switchs **du même site** (ou bâtiments reliés par fibre). Ne joint pas `192.168.137.20` sur Internet.
- **Trunk SIP** : connexion logique **PBX ↔ opérateur** ou **PBX ↔ PBX**. Pas un pont entre PC sur des LAN différents.

---

## 6. VPN vs trunk SIP — comparaison pratique

| | **VPN** | **Trunk SIP** |
|---|---------|----------------|
| **Dispositif dédié obligatoire ?** | Non (souvent) | Non |
| **Implémentable en logiciel ?** | Oui | Oui |
| **Où configurer ?** | OS Linux / routeur / agent (Tailscale) | **FreePBX** (UI + PJSIP) |
| **Couche** | Réseau IP (L3) | Applicatif SIP (L7) |
| **Relie quoi ?** | Réseaux IP / PC distant → LAN PBX | PBX ↔ opérateur ou autre PBX |
| **Pour softphone distant ?** | **Oui** | Non (sauf scénario opérateur) |
| **Pour appels PSTN ?** | Non | **Oui** |
| **Pour VLAN 10 local ?** | Indépendant | Indépendant |

```text
                    TRUNK SIP                    VPN
                    ─────────                    ───
Quoi est relié ?    PBX ↔ opérateur/PBX         LAN ↔ LAN ou PC ↔ LAN
Couche              SIP (couche 7)              IP (couche 3)
Où configurer ?     FreePBX (UI)                 Linux / routeur / agent
Matériel extra ?    Non                          Non (sauf VPN sur firewall dédié)
Pour softphone      Non (sauf via opérateur)      Oui (télétravail)
```

---

## 7. Niveaux d’implémentation

```text
┌─────────────────────────────────────────────────────────────┐
│  INTERNET                                                    │
│     ▲                    ▲                                   │
│     │ trunk SIP          │ VPN (optionnel)                   │
│     │ (FreePBX)          │ (WireGuard / Tailscale)           │
└─────┼────────────────────┼───────────────────────────────────┘
      │                    │
┌─────▼────────────────────▼───────────────────────────────────┐
│  SERVEUR FreePBX / Asterisk (192.168.1.104 + 10.10.10.10 + wg0) │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │ Trunks SIP  │  │ Extensions │  │ VPN serveur (opt.)  │  │
│  │ (FreePBX)   │  │ PJSIP      │  │ wg0 / tailscale     │  │
│  └─────────────┘  └──────────────┘  └─────────────────────┘  │
│         ▲ OS Linux + UFW + net-apply-site.sh                 │
└─────────┼────────────────────────────────────────────────────┘
          │
    ┌─────┴──────┐
    │ SWITCH     │  ← infra locale pour VLAN 10
    │ VLAN 10    │
    └────────────┘
```

### Trunk SIP — niveau application

- Configuration : FreePBX → *Connectivité → Trunks*
- Fichiers : PJSIP généré par FreePBX
- Le PBX doit joindre l’IP/FQDN du fournisseur (souvent Internet)
- **Aucun équipement supplémentaire**

### VPN — niveau réseau (OS)

**Option A — sur le serveur PBX** (petit site) :

```bash
sudo apt install wireguard
# Interface wg0, clients distants se connectent
# Puis : UFW + EXTRA_LAN_CIDRS dans site.env
sudo bash serveur/scripts/net-apply-site.sh
```

**Option B — VM dédiée** : même principe, charge isolée du PBX.

**Option C — Tailscale** : agent sur PBX + PC, peu de config routeur.

| Niveau | Exemple |
|--------|---------|
| Kernel / OS | WireGuard (`wg0`), IPsec |
| Service systemd | `wg-quick@wg0`, `openvpn@server` |
| Overlay | Tailscale, ZeroTier |
| Routeur pro | VPN site-à-site (logiciel dans le boîtier) |

---

## 8. Recommandations par cas d’usage

| Besoin | Solution | Dispositif ? | Niveau |
|--------|----------|--------------|--------|
| Téléphones sur site | **VLAN 10** | Switch (ou hyperviseur) | Couche 2 |
| Softphone sur LAN bureau (`192.168.1.x`) | Accès direct | Non | Client → `192.168.1.104` |
| M. Dupont chez lui (`192.168.137.x`) | **VPN WireGuard** + `10.200.0.0/24` dans `EXTRA_LAN_CIDRS` | Non | `wg0` + `network/vpn/client-distant.conf` |
| Appels internes UDP ↔ WSS (1001 ↔ 1003) | **Extensions PJSIP** (pas de trunk) | Non | Asterisk fait le pont media |
| Appels vers l’extérieur (PSTN) | **Trunk SIP** opérateur | Non | FreePBX |
| Exposition sans VPN | NAT + TLS 5061 + SRTP + Fail2Ban | Non | Routeur + FreePBX (risqué) |
| Deux sites avec chacun un PBX | **Trunk SIP** inter-PBX | Non | FreePBX des deux côtés |

---

## 9. Rôle de `net-apply-site.sh` et `site.env`

Le script `scripts/net-apply-site.sh` applique le profil réseau :

1. **mDNS** (`pbx.local`) via Avahi
2. **localnets PJSIP** : `MGMT_CIDR`, `VOICE_CIDR`, `EXTRA_LAN_CIDRS`, `EXTRA_VOICE_CIDRS`
3. **UFW** : ouverture SIP/RTP/WebRTC/monitoring selon les CIDR configurés
4. **Monitoring Docker** (si `MONITORING_ENABLE="yes"`)
5. **`windows-hosts.txt`** pour Windows sans mDNS

**Important** : ajouter un réseau dans `site.env` **autorise** le trafic depuis ce CIDR ; cela ne **crée pas** la route réseau vers ce CIDR. Il faut d’abord un **chemin IP** (VPN, routage, etc.).

---

## 10. Synthèse

- **VLAN 10** : segmentation voix **locale**, IP stable `10.10.10.10`, indépendant du MGMT.
- **Changement de réseau utilisateur** : nouvelle IP DHCP ; le serveur ne s’adapte pas seul.
- **Pont réseau** : VPN, routage, MPLS, overlays (Tailscale) — **logiciel** dans la majorité des cas.
- **Pont téléphonie** : trunk SIP — **logiciel** dans FreePBX, pour opérateur ou autre PBX.
- **Seul élément « matériel » structurant** pour la voix sur site : le **switch** (VLAN 10).

Pour le télétravail vers un PBX fixe sur `192.168.1.0/24` : **VPN utilisateur WireGuard** (`wg0`, `10.200.0.0/24`) + mise à jour de `EXTRA_LAN_CIDRS` + `net-apply-site.sh`.

---

## 11. Faut-il implémenter les trunks ?

### Ce qui fonctionne déjà sans trunk

D’après les tests actuels sur le PBX :

| Scénario | Mécanisme | Trunk nécessaire ? |
|----------|-----------|-------------------|
| `1001` (UDP) → `1003` (WSS/WebRTC) | Extensions PJSIP + Asterisk B2BUA | **Non** |
| Appels entre extensions internes (1001–1010) | Dialplan FreePBX `from-internal` | **Non** |
| Appels de groupe / conférence | ConfBridge côté Asterisk | **Non** |
| Télétravail (softphone distant) | VPN WireGuard + extension PJSIP | **Non** (trunk ≠ VPN) |
| Téléphones VLAN 10 (`10.10.10.x`) | Extension PJSIP vers `10.10.10.10` | **Non** |

Les trunks SIP et les extensions PJSIP sont **complémentaires**, pas interchangeables.

### Quand implémenter un trunk

| Besoin | Solution | Quand le faire |
|--------|----------|----------------|
| Appeler un **mobile ou fixe externe** (PSTN) | Trunk opérateur (OVH, Twilio…) | Dès que tu veux des appels hors réseau interne |
| Recevoir des appels **depuis l’extérieur** (numéro DID) | Trunk opérateur + routes entrantes | Dès qu’un numéro public est requis |
| Relier **deux PBX** sur deux sites distincts | Trunk inter-PBX | Uniquement si chaque site a son propre PBX |
| Connecter un PC distant au PBX | **VPN** (déjà en place) | Pas un trunk |

### Conclusion

**Non, les trunks ne sont pas nécessaires** tant que tu restes sur de la **téléphonie interne** (extensions, conférences, mix UDP/WebRTC). La VoIP interne passe par les **extensions PJSIP**, pas par un trunk.

**Oui, implémente un trunk** uniquement si tu as besoin d’appels **vers ou depuis le réseau téléphonique public** (PSTN), ou de relier **un autre PBX**. Voir `docs/trunk.md`.

**État actuel** : trunks et routes préconfigurés via `scripts/apply-trunks.sh` :
- trunk PSTN (`trunk-operateur-pstn`) — actif après renseignement de `/root/trunks-secrets.env`
- trunk inter-PBX (`trunk-interpbx-site-b`) — réception depuis `192.168.1.0/24` et `10.200.0.0/24`
- routes sortantes France / International / Inter-PBX
- route entrante catch-all → IVR `7000`

### Point de vigilance (logs actuels)

L’appel `1001 → 1003` fonctionne (sonnerie, décrochage, bridge), mais un avertissement DTLS apparaît :

```text
DTLS packet from 192.168.1.101 dropped. ICE not completed yet.
```

Ce n’est **pas** un problème de trunk — c’est un souci **media WebRTC/ICE** côté client `1003`. Si l’audio est instable, vérifier ICE/STUN, les ports RTP `10000–20000/udp` et la config WebRTC de l’extension.

---

## Documents liés

- `network/site.env` — configuration site
- `scripts/net-apply-site.sh` — application UFW + localnets
- `docs/implement-VPN.md` — installation WireGuard (opérationnel)
- `network/vpn/client-distant.conf` — config client VPN
- `docs/trunk.md` — trunks SIP (PSTN, inter-PBX)
- `docs/Configuration-VLAN-VoIP-production.md` — architecture VLAN production
- `Plan-adressage-reseau-VoIP-QoS.md` — VLAN 10 et QoS RTP
- `S4-Phase4-Securite-complete.md` — TLS, SRTP, Fail2Ban (exposition Internet)
- `webrtc/README.md` — WebRTC / WSS (`pbx.local:8089`)
