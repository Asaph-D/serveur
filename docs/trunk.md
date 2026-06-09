# Trunk SIP — guide VoIP

Document de synthèse : rôle du **trunk SIP** dans l’architecture FreePBX/Asterisk, distinction avec le **trunk VLAN** et le **VPN**, et mise en œuvre via l’UI FreePBX.

**Complément** : `docs/vpn.md` (VPN vs trunk), `S2-Phase2-Utilisateurs-Extensions.md` (numérotation), `S4-Phase4-Securite-complete.md` (TLS, UFW).

---

## 1. Ne pas confondre : trois « trunks » différents

| Terme | Couche | Ce que c’est | Dans ce projet |
|-------|--------|--------------|----------------|
| **Trunk SIP** | Applicatif (SIP) | Lien logique **PBX ↔ opérateur** ou **PBX ↔ PBX** | FreePBX → *Connectivité → Trunks* |
| **Trunk VLAN** (802.1Q) | Réseau (L2) | Port switch qui transporte **plusieurs VLANs** tagués | VLAN 10 voix vers le PBX (`Plan-adressage-reseau-VoIP-QoS.md`) |
| **Trunk opérateur PSTN** | Téléphonie | Offre du FAI pour appels **vers/fixe/mobile** | Même chose qu’un trunk SIP vers `sip.ovh.fr`, etc. |

Ce document parle du **trunk SIP** (téléphonie). Le **trunk VLAN** ne relie pas des réseaux `192.168.x.x` distants — voir `docs/vpn.md`.

---

## 2. À quoi sert un trunk SIP ?

Un trunk est une **connexion SIP permanente** entre votre PBX et un **pair distant** (opérateur, autre PBX, plateforme cloud).

```text
                    INTERNET
                        │
            ┌───────────┴───────────┐
            │   Fournisseur SIP     │
            │   (OVH, Twilio, …)    │
            └───────────┬───────────┘
                        │ trunk SIP
                        ▼
            ┌───────────────────────┐
            │  FreePBX / Asterisk   │
            │  192.168.1.61         │
            │  10.10.10.10 (voix)   │
            └───────────┬───────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   Extensions      Téléphones      Autre PBX
   1001–1010       VLAN 10         (trunk inter-PBX)
```

### Ce qu’un trunk fait

| Fonction | Description |
|----------|-------------|
| **Appels sortants** | Extension `1001` compose `0612345678` → PBX envoie l’appel au trunk → opérateur → PSTN |
| **Appels entrants** | Numéro DID `+33…` chez l’opérateur → trunk → PBX → IVR / extension / file |
| **Inter-PBX** | Site A appelle Site B via trunk SIP entre les deux PBX |

### Ce qu’un trunk ne fait pas

| Idée (fausse) | Réalité |
|---------------|---------|
| Le trunk relie le PC `192.168.137.20` au PBX | **Non** — c’est le rôle du **VPN** ou d’une **extension** enregistrée |
| Le trunk remplace les extensions internes | **Non** — extensions et trunks coexistent |
| Le trunk étend le VLAN 10 | **Non** — couche SIP, pas couche 2 |

---

## 3. Trunk SIP vs extension vs VPN

| | **Extension PJSIP** | **Trunk SIP** | **VPN** |
|---|---------------------|---------------|---------|
| **Qui ?** | Poste utilisateur (1001, softphone) | Serveur distant (opérateur, autre PBX) | PC distant vers le LAN |
| **Auth** | REGISTER + secret extension | Auth sortante (login/mot de passe opérateur) | Clés tunnel |
| **Direction** | Poste ↔ PBX | PBX ↔ opérateur/PBX | Réseau IP |
| **Config** | FreePBX → Extensions | FreePBX → Trunks | OS Linux (`docs/implement-VPN.md`) |
| **Pour M. Dupont chez lui** | Possible **avec VPN** | Non (sauf appels PSTN) | **Oui** |

---

## 4. Types de trunks dans votre architecture

### 4.1 Trunk opérateur (PSTN / SIP trunk)

Connexion vers un **fournisseur SIP** pour joindre le réseau téléphonique public.

```text
Extension 1001  →  Asterisk  →  trunk OVH  →  réseau fixe/mobile
```

- Signalisation : UDP `5060`, TCP `5060`, ou **TLS `5061`** (recommandé Phase 4)
- Authentification : identifiant / mot de passe fournis par l’opérateur
- Numéros entrants (DID) : routés via **Routes entrantes** FreePBX

### 4.2 Trunk inter-PBX (multi-sites)

Deux sites avec chacun un PBX :

```text
PBX Site A (192.168.1.0/24)  ←── trunk SIP ──→  PBX Site B (192.168.50.0/24)
```

- Chaque site garde son **VLAN 10** local
- Les sites communiquent en **SIP** via Internet ou lien dédié
- Pas besoin de fusionner les LAN en un seul réseau

### 4.3 Trunk vs WebRTC / softphone

Un client **WebRTC** (navigateur) ou **Zoiper** est une **extension PJSIP**, pas un trunk.

Le trunk opérateur reste un **chemin séparé** : le média WebRTC ne « traverse » pas le trunk vers le FAI — Asterisk fait le **pont** (B2BUA) entre l’extension et le trunk.

---

## 5. Flux signalisation (FreePBX)

### 5.1 Contextes dialplan

| Contexte | Origine | Usage |
|----------|---------|-------|
| `from-internal` | Extensions internes (1001–1010) | Appels entre postes, vers l’extérieur |
| `from-trunk` / `from-pstn` | Appels **entrants** via trunk | DID → IVR, extension, file |
| Routes sortantes | Appels **sortants** internes | Pattern numéro → trunk choisi |

Sous FreePBX, le cœur du dialplan est **généré** par l’UI ; le custom reste dans `extensions_custom.conf` (Phase 2/3).

### 5.2 Appel sortant (exemple)

```text
1. 1001 compose 0612345678
2. Dialplan from-internal : match route sortante "France 10 chiffres"
3. Normalisation : 0612345678 → format attendu par l’opérateur
4. Asterisk envoie INVITE au trunk (ex. trunk-ovh)
5. Opérateur établit l’appel PSTN
6. RTP : PBX ↔ opérateur (plage 10000–20000)
```

### 5.3 Appel entrant (exemple)

```text
1. Appel vers DID +33… chez l’opérateur
2. Opérateur envoie INVITE vers IP publique / trunk du PBX
3. Contexte from-trunk
4. Route entrante : DID → extension 7000 (IVR Phase 3)
```

---

## 6. Implémentation automatisée (ce projet)

```bash
sudo cp network/trunks.secrets.env.example /root/trunks-secrets.env
sudo chmod 600 /root/trunks-secrets.env
sudo nano /root/trunks-secrets.env
sudo bash /home/asaph/Documents/serveur/scripts/apply-trunks.sh
```

| Fichier | Rôle |
|---------|------|
| `network/trunks.env` | Trunks, routes, DID, UFW opérateur |
| `/root/trunks-secrets.env` | Identifiants opérateur (hors Git) |
| `scripts/apply-trunks.sh` | Application complète |

Trunks : `trunk-operateur-pstn` (PSTN), `trunk-interpbx-site-b` (inter-PBX, préfixe `8`).

---

## 7. Implémentation FreePBX manuelle (alternative UI)

En production, préférer l’**UI FreePBX** plutôt que l’édition manuelle de `pjsip.conf` :

**Connectivité → Trunks → Ajouter un trunk PJSIP**

### 6.1 Paramètres courants (trunk opérateur)

| Champ | Exemple | Remarque |
|-------|---------|----------|
| Nom du trunk | `trunk-ovh` | Identifiant interne |
| PEER Details / Outbound | `sip.ovh.fr` | Hôte opérateur |
| Username | `0033…` ou login FAI | Fourni par l’opérateur |
| Secret | mot de passe trunk | **Ne pas committer** |
| Transport | `transport-udp` ou `transport-tls` | TLS si opérateur le supporte |
| Contexte entrant | `from-pstn` | Défaut FreePBX |

### 6.2 Routes sortantes

**Connectivité → Routes sortantes → Ajouter**

| Champ | Exemple France |
|-------|----------------|
| Nom | `France-metropole` |
| Pattern | `0XXXXXXXXX` (0 + 9 chiffres) |
| Trunk séquence | `trunk-ovh` |
| Préfixe | (vide ou `0` selon opérateur) |

Patterns usuels (à adapter selon l’offre) :

| Usage | Pattern |
|-------|---------|
| Métropole 10 chiffres | `0XXXXXXXXX` |
| International | `00.` ou conversion `+` → `00` |
| Numéros courts | `1[0-9]XX` — **conformité réglementaire** à valider |

### 6.3 Routes entrantes

**Connectivité → Routes entrantes → Ajouter**

| Champ | Exemple |
|-------|---------|
| DID | `+33123456789` |
| Destination | Extension `7000` (IVR) ou `1001` |

### 6.4 Après modification

```bash
sudo fwconsole reload
sudo asterisk -rx "pjsip show endpoints"
sudo asterisk -rx "pjsip show aors"
```

---

## 7. Modèle Phase 3 (fichier custom)

Le script `scripts/phase3-apply-asterisk.sh` ajoute un **modèle commenté** dans `/etc/asterisk/pjsip_custom_post.conf` :

```ini
; BEGIN_PHASE3_TRUNK_TEMPLATE
;[wizard-ovh]
;type = wizard
;transport = transport-udp
;accepts_registrations = no
;sends_auth = yes
;sends_registrations = yes
;endpoint = ovh-endpoint
;identify = ovh-identify
;remote_hosts = sip.ovh.fr
;outbound_auth/username = VOTRE_LOGIN
;outbound_auth/password = VOTRE_SECRET
;aor/contact = sip:VOTRE_LOGIN@sip.ovh.fr
```

**Usage** :
- Décommenter et adapter **ou** configurer via l’UI FreePBX
- **Ne pas dupliquer** : un trunk en UI + le même en custom = conflit PJSIP
- En production : **UI FreePBX** quand les modules Sangoma sont stables (`S3-Phase3-IVR-Monitoring.md`)

---

## 8. Réseau et pare-feu (UFW)

### 8.1 Politique actuelle du projet

`scripts/net-apply-site.sh` ouvre SIP/RTP depuis :
- `VOICE_CIDR` (`10.10.10.0/24`)
- `MGMT_CIDR` (`192.168.1.0/24`) si `ALLOW_SIP_FROM_MGMT=yes`
- `EXTRA_LAN_CIDRS` (RTP + WebRTC partiel)

Les **trunks opérateur** arrivent depuis **Internet** (IP publique du FAI) — **pas** couverts par `site.env`.

### 8.2 Règles UFW pour trunk opérateur

Autoriser **uniquement** les IP du fournisseur (pas `Anywhere` en production) :

```bash
# Exemple : IP de signalisation OVH (à remplacer par la doc opérateur)
OPERATOR_IP="51.xxx.xxx.xxx"

sudo ufw allow from ${OPERATOR_IP} to any port 5060 proto udp comment "Trunk OVH SIP UDP"
sudo ufw allow from ${OPERATOR_IP} to any port 5060 proto tcp comment "Trunk OVH SIP TCP"
sudo ufw allow from ${OPERATOR_IP} to any port 5061 proto tcp comment "Trunk OVH SIP TLS"
# RTP entrant souvent depuis plages opérateur — restreindre selon doc FAI
sudo ufw reload
```

Référence durcissement : `S4-Phase4-Securite-complete.md` §5 — *« ajouter des règles UFW ciblées (`allow from IP_FAI`) plutôt qu’un accès mondial »*.

### 8.3 NAT et IP publique

Si le PBX est derrière une box :

- **Port forwarding** : SIP (`5060` ou `5061`) et parfois RTP vers `192.168.1.61`
- Ou **SBC** (Kamailio, OpenSIPS) en frontal avec IP publique
- Informer l’opérateur de l’**IP publique** pour l’auth entrante (identify par IP)

### 8.4 Fail2Ban

Les IP opérateur légitimes ne doivent **pas** être bannies. Si besoin, ajouter les IP FAI en **ignoreip** Fail2Ban.

---

## 9. Sécurité (Phase 4)

| Mesure | Trunk |
|--------|-------|
| **TLS 5061** | Privilégier si l’opérateur le propose |
| **SRTP** | Selon offre opérateur (souvent RTP classique côté trunk) |
| **Auth sortante** | Login / mot de passe trunk (stockage FreePBX, pas dans Git) |
| **Auth entrante** | IP source (identify) + éventuellement digest |
| **Fail2Ban** | Actif sur `/var/log/asterisk/full` — attention aux faux positifs trunk |
| **Secrets** | Rotation selon politique opérateur |

Certificat TLS local (extensions / softphones) : `scripts/phase4-assign-pjsip-tls-cert.php` — distinct du certificat côté opérateur trunk.

---

## 10. Trunk inter-PBX (multi-sites)

### Architecture

```text
Site A                          Site B
PBX 192.168.1.61                PBX 192.168.50.10
  │                               │
  │ trunk SIP (Internet ou MPLS)  │
  └───────────────┬───────────────┘
                  │
        Appel 1001@A → 2001@B
```

### Configuration (chaque côté)

| Côté A | Côté B |
|--------|--------|
| Trunk vers IP/FQDN PBX B | Trunk vers IP/FQDN PBX A |
| Route sortante : préfixe interne site B → trunk-B | Route sortante : préfixe site A → trunk-A |
| Route entrante : appels du trunk-A → extensions | Route entrante : appels du trunk-B → extensions |

Chaque site conserve son **VLAN 10** (`10.10.10.0/24`) ; seul le **SIP** traverse le trunk.

---

## 11. Vérifications

### 11.1 État PJSIP

```bash
sudo asterisk -rx "pjsip show endpoints" | grep -i trunk
sudo asterisk -rx "pjsip show aors"
sudo asterisk -rx "pjsip show registrations"
```

### 11.2 Test appel sortant

1. Composer un numéro externe depuis `1001`
2. Observer les logs :

```bash
sudo tail -f /var/log/asterisk/full
```

3. Vérifier CDR dans FreePBX ou MariaDB

### 11.3 Test appel entrant

1. Appeler le DID depuis un mobile
2. Vérifier que la route entrante atteint la bonne destination (IVR `7000`, extension, etc.)

### 11.4 Checklist trunk opérateur

| Étape | OK ? |
|-------|------|
| Trunk créé dans FreePBX (ou custom décommenté) | ☐ |
| Auth opérateur validée (`pjsip show registrations` ou logs) | ☐ |
| Route sortante France configurée | ☐ |
| Route entrante DID configurée | ☐ |
| UFW : IP opérateur autorisée (pas Anywhere) | ☐ |
| NAT / IP publique alignée avec l’opérateur | ☐ |
| `fwconsole reload` exécuté | ☐ |
| Appel sortant test réussi | ☐ |
| Appel entrant test réussi | ☐ |

---

## 12. Dépannage rapide

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| Pas d’appel sortant | Route sortante / pattern incorrect | Vérifier *Routes sortantes*, pattern `0XXXXXXXXX` |
| `403 Forbidden` trunk | Auth / IP non autorisée chez FAI | Login, mot de passe, IP publique déclarée |
| Appel sortant, pas d’audio | RTP / NAT / UFW | Ports 10000–20000, `externaddr` / `localnets` |
| Entrant ne sonne pas | Route entrante / DID | *Routes entrantes*, format DID `+33…` |
| Conflit PJSIP | Trunk UI + custom wizard | Un seul endroit de config |
| Fail2Ban bloque trunk | IP FAI bannie | `ignoreip` ou ajuster le filtre |

### Commandes utiles

```bash
sudo asterisk -rx "pjsip set logger on"
sudo asterisk -rx "dialplan show from-internal"
sudo ufw status numbered
sudo fail2ban-client status asterisk
```

---

## 13. Position dans le plan de déploiement

| Phase | Élément trunk |
|-------|---------------|
| **Phase 1** | VLAN 10, UFW local — pas de trunk |
| **Phase 2** | Extensions 1001–1010 — trunks **prévus** (§6 numérotation) |
| **Phase 3** | Modèle trunk commenté dans `pjsip_custom_post.conf` |
| **Phase 4** | UFW ciblé IP opérateur, TLS extensions |
| **Phase suivante** | Trunk opérateur + routes entrantes/sortantes en production |

---

## 14. Synthèse

- **Trunk SIP** = lien **PBX ↔ opérateur** ou **PBX ↔ PBX**, couche **applicative**, **100 % logiciel** dans FreePBX.
- **Pas un pont réseau** : ne remplace pas VPN ni VLAN 10.
- **Extensions** = postes internes ; **trunks** = sortie/entrée vers l’extérieur ou autre PBX.
- **Config** : UI FreePBX (*Trunks*, *Routes sortantes*, *Routes entrantes*) + UFW ciblé IP opérateur.
- **Sécurité** : pas d’ouverture SIP mondiale ; TLS si possible ; Fail2Ban avec exceptions FAI.

---

## Documents liés

- `docs/vpn.md` — VPN vs trunk, VLAN 10
- `docs/implement-VPN.md` — télétravail softphone
- `S2-Phase2-Utilisateurs-Extensions.md` — extensions, numérotation FR
- `S3-Phase3-IVR-Monitoring.md` — modèle trunk Phase 3
- `S4-Phase4-Securite-complete.md` — TLS, UFW, Fail2Ban
- `Architecture-VoIP-communication-composants.md` — flux opérateur → pare-feu → Asterisk
- `scripts/phase3-apply-asterisk.sh` — injection modèle trunk
- `network/site.env` — UFW local (distinct du trunk Internet)
