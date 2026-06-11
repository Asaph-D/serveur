# Implémentation cryptographique — couche sécurité VoIP

Document de référence : **où se situe la sécurité** dans l’architecture du serveur FreePBX/Asterisk, **ce qui est déjà en place**, **ce qui reste à déployer** (dont le **QR chiffré** de provisionnement d’extension), et **les normes** à respecter.

Aligné sur : `S4-Phase4-Securite-complete.md`, `Architecture-VoIP-communication-composants.md`, `docs/interface-guids.md`.

---

## Table des matières

1. [Où se situe la couche sécurité ?](#1-où-se-situe-la-couche-sécurité-)
2. [Modèle en couches (stack)](#2-modèle-en-couches-stack)
3. [Ce qui existe déjà sur le serveur](#3-ce-qui-existe-déjà-sur-le-serveur)
4. [Chiffrement « bout en bout » : ce que ça veut dire en VoIP](#4-chiffrement-bout-en-bout--ce-que-ça-veut-dire-en-voip)
5. [Signalisation : TLS et authentification SIP](#5-signalisation--tls-et-authentification-sip)
6. [Média : SRTP, DTLS-SRTP et WebRTC](#6-média--srtp-dtls-srtp-et-webrtc)
7. [Réseau : VLAN, UFW, VPN, Fail2Ban](#7-réseau--vlan-ufw-vpn-fail2ban)
8. [Administration : dashboard FreePBX](#8-administration--dashboard-freepbx)
9. [Provisionnement par QR chiffré (cible)](#9-provisionnement-par-qr-chiffré-cible)
10. [Parcours Asaphone — inscription e-mail + QR](#10-parcours-asaphone--inscription-e-mail--qr)
11. [Normes et algorithmes recommandés](#11-normes-et-algorithmes-recommandés)
12. [Matrice par type de poste](#12-matrice-par-type-de-poste)
13. [Roadmap d’implémentation](#13-roadmap-dimplémentation)
14. [Checklist sécurité](#14-checklist-sécurité)
15. [Documents liés](#15-documents-liés)

---

## 1. Où se situe la couche sécurité ?

La sécurité **n’est pas un seul bloc** : elle est **répartie en couches** autour et dans le PBX.

```text
                         INTERNET
                             │
                    ┌────────▼────────┐
                    │  Couche réseau  │  UFW, Fail2Ban, NAT, VPN WireGuard
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Couche admin    │  HTTPS UI FreePBX, auth session, rôles
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Couche signal.  │  SIP Digest, TLS 5061, WSS 8089
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────────┐ ┌───▼───┐ ┌────────▼────────┐
     │ Couche média    │ │ Trunk │ │ Provisionnement │
     │ SRTP / DTLS     │ │ TLS   │ │ QR chiffré      │
     └────────┬────────┘ └───┬───┘ └────────┬────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │ Couche données  │  MariaDB, secrets, CDR, enregistrements
                    └─────────────────┘
```

### Position dans l’architecture projet

| Zone architecture | Couche(s) sécurité |
|-------------------|-------------------|
| Internet / Trunk SIP | TLS trunk, UFW IP opérateur, auth trunk |
| Pare-feu | UFW, Fail2Ban |
| Zone serveur (Asterisk/FreePBX) | TLS, SRTP, certificats, secrets SIP |
| VLAN voix | Segmentation, QoS, RTP filtré |
| VPN télétravail | WireGuard (chiffrement tunnel) |
| Terminaux | Auth SIP + chiffrement média + QR provisionnement |
| Observabilité | Grafana/Influx en LAN restreint |

La couche sécurité **ne remplace pas** FreePBX : elle **l’entoure** (réseau) et **s’intègre** dedans (TLS, SRTP, auth).

---

## 2. Modèle en couches (stack)

| Couche | Nom | Protocoles / mécanismes | État projet |
|--------|-----|-------------------------|-------------|
| **L0** | Physique / segmentation | VLAN 10, MGMT séparé | ✅ Déployé |
| **L1** | Transport réseau | WireGuard, IPsec (option) | ✅ VPN WireGuard |
| **L2** | Pare-feu / anti-abus | UFW, Fail2Ban | ✅ Phase 4 |
| **L3** | Admin web | HTTPS, session FreePBX | ✅ Dashboard auth |
| **L4** | Signalisation SIP | TLS 1.2+, WSS, Digest auth | ✅ Partiel (TLS + WSS) |
| **L5** | Média audio | SRTP (SDES), DTLS-SRTP (WebRTC) | ✅ Partiel (scripts Phase 4) |
| **L6** | Provisionnement | QR / token chiffré | ⏳ À implémenter |
| **L7** | Données au repos | Chiffrement disque, secrets 600, rotation DB | ⚠️ Partiel |

---

## 3. Ce qui existe déjà sur le serveur

### Déjà opérationnel

| Mécanisme | Rôle | Fichiers / scripts |
|-----------|------|-------------------|
| **Auth dashboard FreePBX** | Seuls les admins authentifiés accèdent à l’UI | Session web Apache/PHP |
| **TLS signalisation SIP** | Chiffrement INVITE/REGISTER (port 5061) | `phase4-assign-pjsip-tls-cert.php`, Certman |
| **WSS WebRTC** | Signalisation navigateur chiffrée (8089) | `enable-webrtc-websocket.sh` |
| **SRTP SDES** | Chiffrement RTP extensions classiques | `phase4-enable-srtp-extensions.php` |
| **DTLS-SRTP** | Chiffrement média WebRTC | Endpoints WebRTC (`align-pjsip-site.sh`) |
| **UFW** | Filtrage entrant par CIDR | `net-apply-site.sh`, `apply-trunks.sh` |
| **Fail2Ban** | Bannissement IP après échecs SIP | `phase4-apply-fail2ban.sh` |
| **VPN WireGuard** | Tunnel chiffré télétravail | `implement-VPN.md`, `wg0` |
| **Secrets SIP** | Mots de passe aléatoires ≥ 16 car. | `/root/phase2-pjsip-secrets.txt` |
| **Permissions certificats** | Clés privées protégées | `fix-cert-perms.sh` |

### Pas encore en place (hors scope Phase 4 actuelle)

| Mécanisme | Statut |
|-----------|--------|
| QR chiffré de provisionnement | Documenté ici — **à développer** |
| E2EE strict poste-à-poste (sans déchiffrement PBX) | Non compatible modèle PBX actuel |
| Hachage irréversible des secrets SIP en base | Limitation FreePBX (secrets réversibles) |
| MFA admin FreePBX | Option module / reverse proxy |
| Rotation automatique secrets 90 j | Procédure manuelle documentée |

---

## 4. Chiffrement « bout en bout » : ce que ça veut dire en VoIP

### Distinction importante

| Terme | Signification dans notre architecture |
|-------|--------------------------------------|
| **Chiffrement de transport** | TLS sur SIP, SRTP sur RTP — le PBX **voit** le contenu en clair en interne |
| **Chiffrement bout-en-bout (E2EE)** | Seuls les deux postes voient l’audio ; **personne au milieu** (y compris le PBX) |
| **Chiffrement « hop-by-hop »** | Chaque segment est chiffré (client↔PBX, PBX↔trunk) — **modèle Asterisk standard** |

### Modèle actuel : hop-by-hop via PBX (B2BUA)

```text
Poste A ──[TLS+SRTP]──► PBX ──[TLS+SRTP]──► Poste B
              │                    │
              └── Asterisk déchiffre ├── re-chiffre
                  (mix audio, IVR, conférence)
```

**Conséquence** : avec FreePBX/Asterisk en **proxy média** (`direct_media=no`), on obtient :

- ✅ **Confidentialité sur le réseau** (LAN, Internet, Wi‑Fi)
- ✅ **Intégrité** des flux SIP/RTP
- ❌ **Pas d’E2EE** au sens Signal/WhatsApp — le serveur **doit** déchiffrer pour mixer, enregistrer, transcrire, conférence

### Quand l’E2EE strict serait requis

- Messagerie entre pairs sans serveur central
- Appels P2P directs (téléphones en `direct_media=yes` — incompatible conférence/IVR)
- Clients avec clés propres (ZK, double ratchet) — **hors FreePBX standard**

**Recommandation projet** : viser **TLS + SRTP/DTLS sur tous les segments** + **segmentation réseau** ; réserver l’E2EE strict à un **client dédié** si besoin métier futur.

---

## 5. Signalisation : TLS et authentification SIP

### Couche L4 — Signalisation

| Flux | Protocole | Port | Norme |
|------|-----------|------|-------|
| SIP classique | UDP | 5060 | RFC 3261 |
| SIP sécurisé | TLS 1.2+ | 5061 | RFC 3261 + RFC 8446 |
| WebRTC signaling | WSS | 8089 | RFC 6455 + SIP over WebSocket |
| Auth poste | Digest (MD5) | — | RFC 2617 / RFC 7616 |

### Implémentation serveur

```bash
# Vérifier transport TLS
sudo asterisk -rx "pjsip show transport 0.0.0.0-tls"

# Assigner certificat
sudo php scripts/phase4-assign-pjsip-tls-cert.php
```

**Source de vérité certificat** : `kvstore_Sipsettings.pjsipcertid` → `certman_certs`.

### Limitation Digest MD5

FreePBX utilise encore **Digest MD5** pour l’auth SIP (standard historique). Bonnes pratiques :

- Toujours **TLS 5061** ou **WSS** pour protéger le secret en transit
- Secrets **≥ 16 caractères**, aléatoires
- **Fail2Ban** contre brute-force
- À terme : évaluer **TLS client cert** pour postes sensibles

---

## 6. Média : SRTP, DTLS-SRTP et WebRTC

### Couche L5 — Média audio

| Type poste | Chiffrement média | Mécanisme | Script / config |
|------------|-------------------|-----------|-----------------|
| Zoiper / Linphone / téléphone IP | SRTP (SDES) | Clé négociée dans SDP | `phase4-enable-srtp-extensions.php` |
| WebRTC (1003–1010) | DTLS-SRTP | Poignée de main DTLS + fingerprint | `align-pjsip-site.sh` (webrtc=yes) |
| Trunk opérateur | Souvent RTP clair ou SRTP opérateur | Selon offre FAI | `trunks.env` |

### Vérifications

```bash
# SRTP SDES sur extensions classiques
grep media_encryption= /etc/asterisk/pjsip.endpoint.conf | head

# WebRTC DTLS sur 1003
sudo asterisk -rx "pjsip show endpoint 1003" | grep -iE 'webrtc|dtls|media_encryption|ice'
```

### Normes média

| Norme | Objet |
|-------|-------|
| RFC 3550 | RTP |
| RFC 3711 | SRTP |
| RFC 5764 | DTLS-SRTP (WebRTC) |
| RFC 8825–8829 | WebRTC architecture |

---

## 7. Réseau : VLAN, UFW, VPN, Fail2Ban

### Couches L0–L2

```text
Client ──► [VLAN / UFW] ──► PBX ──► [UFW] ──► Trunk opérateur
              │                      │
              └── Fail2Ban ◄─────────┘
```

| Contrôle | Fichier | CIDR autorisés (exemple) |
|----------|---------|--------------------------|
| SIP/RTP LAN | `network/site.env` | `192.168.1.0/24`, `10.10.10.0/24` |
| WebRTC WSS | `site.env` | MGMT + VLAN + `EXTRA_LAN_CIDRS` |
| VPN | `implement-VPN.md` | `10.200.0.0/24` |
| Trunk PSTN | `network/trunks.env` | `PSTN_OPERATOR_CIDRS` (IP FAI) |

**Principe** : ne jamais ouvrir SIP/RTP en `Anywhere` sur Internet sans VPN ou SBC frontal.

---

## 8. Administration : dashboard FreePBX

### Couche L3 — Accès admin

| Mécanisme | Détail |
|-----------|--------|
| **Authentification** | Login / mot de passe admin FreePBX (session PHP) |
| **Transport** | HTTPS recommandé (certificat Certman ou Let’s Encrypt) |
| **Autorisation** | Rôles FreePBX (admin, opérateur selon modules) |
| **Séparation** | Admin sur LAN gestion — pas exposé sur VLAN voix seul |

### Ce que le dashboard **ne couvre pas**

- Le dashboard protège **la configuration**, pas les **appels** eux-mêmes
- Les postes SIP s’authentifient **séparément** (Digest + secret extension)
- Chiffrer l’UI **ne remplace pas** TLS 5061 ni SRTP sur les téléphones

### Durcissement recommandé (à planifier)

| Mesure | Priorité |
|--------|----------|
| HTTPS obligatoire (redirect HTTP→HTTPS) | Haute |
| MFA / 2FA (module ou reverse proxy) | Moyenne |
| Restriction IP admin (UFW 443 depuis MGMT seul) | Haute |
| Comptes admin nominatifs (pas un seul `admin`) | Haute |
| Journalisation des actions admin | Moyenne |

---

## 9. Provisionnement par QR chiffré (cible)

### Objectif

Permettre à un **dispositif** (softphone, téléphone, client WebRTC) de **recevoir sa configuration d’extension** via un **QR code chiffré**, sans saisie manuelle du secret, tout en respectant les normes cryptographiques du serveur.

```text
Admin FreePBX / script
        │
        ▼
 Génère payload chiffré
 (extension, serveur, secret, expiry)
        │
        ▼
   QR code affiché / PDF / e-mail
        │
        ▼
 Dispositif scanne QR
        │
        ▼
 Déchiffre localement → configure SIP → REGISTER
```

### Ce que contient le payload (avant chiffrement)

```json
{
  "v": 1,
  "ext": "1003",
  "server": "pbx.local",
  "transport": "wss",
  "port": 8089,
  "secret": "<secret_sip_ou_token_usage_unique>",
  "codecs": ["g722", "ulaw", "alaw"],
  "webrtc": true,
  "iat": 1710000000,
  "exp": 1710003600,
  "jti": "uuid-unique-revocable"
}
```

### Architecture cryptographique proposée

#### Option A — JWE symétrique (recommandée pour QR compact)

| Élément | Choix normé |
|---------|-------------|
| Chiffrement | **AES-256-GCM** |
| Dérivation clé | **PBKDF2** (≥ 100 000 itérations) ou **Argon2id** |
| Secret de déverrouillage | **PIN à 6–8 chiffres** affiché séparément du QR, ou clé pré-partagée sur le device |
| Format | **JWE** compact (RFC 7516) encodé en Base64URL dans le QR |
| Intégrité | GCM (authentifié) + **exp** + **jti** en base pour révocation |

```text
QR = JWE( payload, clé_dérivée(PIN_admin_ou_device) )
```

#### Option B — JWE asymétrique (device avec clé publique)

| Élément | Choix normé |
|---------|-------------|
| Chiffrement contenu | AES-256-GCM (CEK aléatoire) |
| Chiffrement CEK | **RSA-OAEP-2048** ou **ECDH P-256** (clé publique du device) |
| Signature payload | **Ed25519** ou **RSASSA-PSS** (serveur signe, device vérifie) |
| Format | **JWS** signé + **JWE** chiffré (nested JWT, RFC 7519) |

```text
QR = JWE( JWS( payload, clé_privée_serveur ), clé_publique_device )
```

#### Option C — Token à usage unique (plus simple)

| Élément | Détail |
|---------|--------|
| QR contient | URL `https://pbx.local/provision?token=<opaque>` |
| Serveur | Token stocké en base, lié à extension, **expire 15 min**, **usage unique** |
| Livraison secret | HTTPS + auth admin ou PIN |

**Recommandation** : **Option A** pour simplicité terrain ; **Option B** si chaque device a une paire de clés (mobile géré).

### Flux opérationnel proposé

1. **Admin** : Applications → Extensions → 1003 → **Générer QR provisionnement** (futur module ou script CLI)
2. Le serveur génère un **secret temporaire** ou réutilise le secret PJSIP (selon politique)
3. Payload chiffré → **QR** affiché à l’écran + **PIN** communiqué séparément (SMS, oral)
4. **Device** scanne QR, dérive la clé, déchiffre, configure le client SIP
5. **REGISTER** vers PBX en TLS/WSS
6. Token / `jti` marqué **consommé** côté serveur (révocation)

### Où vit cette couche dans le stack

| Composant | Rôle |
|-----------|------|
| **Générateur QR** | Script PHP ou module FreePBX custom (couche L6) |
| **Clé maître serveur** | `/etc/asterisk/keys/provision-master.key` (chmod 600, hors Git) |
| **Révocation** | Table MariaDB `provision_tokens` (jti, ext, exp, used) |
| **Client** | Asaphone / Zoiper avec lecteur QR intégré |

### Fichiers cibles (implémentation future)

```text
security/
  cryptographic_implementation.md    ← ce document
scripts/
  provision-generate-qr.php            ← à créer
  provision-revoke-token.php         ← à créer
network/
  provision.env                        ← politique (durée token, algorithme)
```

### Exemple commande (cible)

```bash
# Générer QR pour extension 1003 (expire 1 h, PIN affiché séparément)
sudo php scripts/provision-generate-qr.php --ext 1003 --ttl 3600 --pin
# Sortie : /var/spool/asterisk/provision/1003-qr.png + PIN à l'écran
```

---

## 10. Parcours Asaphone — inscription e-mail + QR

Scénario validé : l’utilisateur ouvre **Asaphone** et choisit :

1. **« J’ai déjà mes identifiants »** → saisie manuelle ou scan QR → REGISTER WSS (flux actuel).
2. **« M’enregistrer »** → saisie e-mail → **vérification** → **e-mail avec QR** → scan → REGISTER WSS (flux actuel).

```text
Asaphone                    Mini-API PHP (même serveur)           Mail
   │                              │                                │
   │ POST /provision/register     │                                │
   │─────────────────────────────►│  code vérif + mail ───────────►│ utilisateur
   │ POST /provision/verify       │                                │
   │─────────────────────────────►│  génère QR + mail credentials ►│ utilisateur
   │ scan QR                      │                                │
   │────────────────────────────────────────────────────────────────►│
   │ REGISTER wss://pbx.local:8089/ws (inchangé)                    │
   │─────────────────────────────► Asterisk                         │
```

**Pas d’API backend séparée** : Apache héberge `/provision/api/v1/` en PHP sur le PBX ; Postfix envoie les mails.

Document détaillé (écrans, endpoints, tables SQL, sécurité) :

→ **`security/asaphone-onboarding-flow.md`**

Config : **`network/provision.env`**

---

## 11. Normes et algorithmes recommandés

### Référentiels

| Organisme | Application |
|-----------|-------------|
| **IETF (RFC)** | SIP, TLS, SRTP, DTLS, WebRTC, JOSE/JWT |
| **NIST SP 800-57** | Longueur des clés, rotation |
| **NIST SP 800-132** | PBKDF2 |
| **ANSSI** | Guides TLS, segmentation, durcissement Linux |
| **RGPD** | CDR, enregistrements, messagerie (données personnelles) |
| **ETSI EN 319 411** | Confiance et certificats (si PKI interne) |

### Algorithmes : autorisés vs interdits

| Usage | ✅ Recommandé | ⚠️ Legacy toléré | ❌ Interdit |
|-------|--------------|------------------|------------|
| Signalisation WAN | TLS 1.2, TLS 1.3 | — | SSLv3, TLS 1.0/1.1 |
| Média VoIP | SRTP-AES-128/256, DTLS-SRTP | — | RTP clair sur Internet |
| Auth SIP | Digest + TLS | Digest MD5 sur LAN isolé | Digest sans TLS sur WAN |
| QR / tokens | AES-256-GCM, Argon2id | AES-128-GCM | DES, 3DES, ECB |
| Signatures | Ed25519, RSASSA-PSS-2048 | RSA PKCS#1 v1.5 | SHA-1 seul |
| VPN | WireGuard (ChaCha20-Poly1305) | — | PPTP, WEP |
| Hash mots de passe admin | bcrypt, Argon2 | — | MD5, SHA1 seul |

### Correspondance RFC principales

| RFC | Sujet |
|-----|-------|
| RFC 3261 | SIP |
| RFC 2617 / 7616 | HTTP Digest Authentication |
| RFC 3711 | SRTP |
| RFC 5764 | DTLS-SRTP |
| RFC 5246 / 8446 | TLS |
| RFC 7515–7519 | JWS, JWE, JWT |
| RFC 8032 | Ed25519 |
| RFC 8825–8829 | WebRTC |

---

## 12. Matrice par type de poste

| Poste | Réseau | Signalisation | Média | Provisionnement | État |
|-------|--------|---------------|-------|-----------------|------|
| Téléphone IP VLAN 10 | VLAN isolé | UDP ou TLS 5061 | SRTP SDES | QR chiffré (cible) | ⚠️ |
| Zoiper LAN | MGMT / VLAN | TLS 5061 | SRTP SDES | QR ou saisie manuelle | ⚠️ |
| WebRTC 1003–1010 | LAN / VPN | WSS 8089 | DTLS-SRTP | QR chiffré (cible) | ⚠️ |
| Softphone VPN | WireGuard | TLS vers 192.168.1.104 | SRTP | QR + VPN | ⚠️ |
| Trunk opérateur | Internet | TLS si FAI | RTP ou SRTP FAI | Credentials FAI | ⏳ |
| Admin FreePBX | LAN gestion | HTTPS | — | Login session | ✅ |

Légende : ✅ en place · ⚠️ partiel · ⏳ en attente credentials / dev

---

## 13. Roadmap d’implémentation

### Phase actuelle (déjà faite)

- [x] TLS 5061 + Certman
- [x] SRTP SDES extensions 1001–1010
- [x] WebRTC DTLS-SRTP (1003–1010)
- [x] UFW + Fail2Ban
- [x] VPN WireGuard
- [x] Secrets SIP aléatoires
- [x] Auth dashboard FreePBX

### Phase suivante — onboarding Asaphone (e-mail + QR)

- [x] Document flux `security/asaphone-onboarding-flow.md`
- [x] Config `network/provision.env`
- [ ] Postfix / relais SMTP opérationnel
- [ ] Tables `provision_requests` + `provision_tokens`
- [ ] Mini-API `/provision/api/v1/` (register, verify, consume)
- [ ] Script envoi mail + QR PNG
- [ ] Écrans Asaphone (2 parcours + scan)
- [ ] Révocation token + logs audit

### Phase ultérieure — durcissement

- [ ] HTTPS obligatoire UI
- [ ] MFA admin
- [ ] Rotation automatique secrets 90 j
- [ ] Let’s Encrypt automatique (si exposé)
- [ ] Audit CDR / RGPD (rétention, anonymisation)
- [ ] TLS mutuel pour postes sensibles (option)

---

## 14. Checklist sécurité

| # | Contrôle | Commande / lieu |
|---|----------|-------------------|
| 1 | TLS 5061 avec certificat | `pjsip show transport 0.0.0.0-tls` |
| 2 | SRTP actif extensions | `grep media_encryption= pjsip.endpoint.conf` |
| 3 | WebRTC DTLS sur 1003+ | `pjsip show endpoint 1003` |
| 4 | UFW actif | `sudo ufw status verbose` |
| 5 | Fail2Ban actif | `sudo fail2ban-client status asterisk` |
| 6 | Secrets non exposés | `ls -l /root/phase2-pjsip-secrets.txt` → 600 |
| 7 | Certificats permissions | `fix-cert-perms.sh` |
| 8 | VPN actif | `sudo wg show` |
| 9 | Pas de SIP ouvert monde | `ufw status \| grep 5060` |
| 10 | Dashboard HTTPS | Navigateur → cadenas |
| 11 | QR provisionnement | Roadmap §12 |

---

## 15. Documents liés

| Document | Sujet |
|----------|-------|
| `security/asaphone-onboarding-flow.md` | Parcours inscription e-mail + QR Asaphone |
| `network/provision.env` | Politique provisionnement |
| `S4-Phase4-Securite-complete.md` | TLS, SRTP, Fail2Ban, UFW |
| `Architecture-VoIP-communication-composants.md` | Couche pare-feu dans l’archi |
| `docs/interface-guids.md` | Certificats dans l’UI FreePBX |
| `docs/vpn.md` | VPN vs exposition SIP |
| `docs/implement-VPN.md` | WireGuard |
| `scripts/phase4-apply-all.sh` | Enchaîner sécurité Phase 4 |
| `network/site.env` | Politique réseau |

---

## Synthèse

- La **couche sécurité** est **transversale** : réseau (UFW, VLAN, VPN), admin (HTTPS, auth UI), signalisation (TLS/WSS), média (SRTP/DTLS), données (secrets, DB).
- L’**auth dashboard** protège la **configuration** ; les **postes** ont leur **propre auth SIP**.
- Le chiffrement **bout en bout strict** n’est **pas** le modèle d’Asterisk en mode proxy ; on vise **TLS + SRTP sur chaque segment** + **segmentation**.
- Le **QR chiffré** est la **couche L6 provisionnement** à ajouter : payload signé/chiffré (JWE/JWT), token à durée limitée, révocation côté serveur, normes **AES-256-GCM**, **TLS 1.2+**, **Ed25519** ou **RSA-OAEP**.

---

*Document sécurité — projet serveur VoIP. Mettre à jour lors de l’implémentation du module QR (`scripts/provision-generate-qr.php`).*
