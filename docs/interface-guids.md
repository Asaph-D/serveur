# Guide interface FreePBX — tout ce qu’il faut savoir

Document de référence pour naviguer dans l’interface FreePBX, savoir **où configurer quoi**, et éviter de modifier les mauvais fichiers (`pjsip.conf`, etc.).

Aligné sur le serveur actuel :
- PBX gestion : `192.168.1.104`
- PBX VLAN voix : `10.10.10.10`
- VPN WireGuard : `10.200.0.1`
- Extensions : `1001`–`1010`

---

## Table des matières

1. [Principe fondamental : ne pas éditer pjsip.conf](#1-principe-fondamental--ne-pas-éditer-pjsipconf)
2. [Accéder à l’interface](#2-accéder-à-linterface)
3. [Carte des menus FreePBX](#3-carte-des-menus-freepbx)
4. [Où configurer quoi (table rapide)](#4-où-configurer-quoi-table-rapide)
5. [Interface vs scripts vs fichiers](#5-interface-vs-scripts-vs-fichiers)
6. [Extensions PJSIP (1001–1010)](#6-extensions-pjsip-10011010)
7. [Transports SIP : UDP, TLS, WebSocket](#7-transports-sip--udp-tls-websocket)
8. [Trunks et routes (PSTN, inter-PBX)](#8-trunks-et-routes-pstn-inter-pbx)
9. [IVR, files d’attente, conférences](#9-ivr-files-dattente-conférences)
10. [Messagerie vocale et e-mail](#10-messagerie-vocale-et-e-mail)
11. [Certificats TLS et sécurité](#11-certificats-tls-et-sécurité)
12. [Monitoring Grafana](#12-monitoring-grafana)
13. [Logs et diagnostic dans l’interface](#13-logs-et-diagnostic-dans-linterface)
14. [Appliquer les changements (reload)](#14-appliquer-les-changements-reload)
15. [Logiciels pour tester avec des softphones](#15-logiciels-pour-tester-avec-des-softphones)
16. [Plan de test complet](#16-plan-de-test-complet)
17. [Erreurs fréquentes](#17-erreurs-fréquentes)
18. [Documents liés](#18-documents-liés)

---

## 1. Principe fondamental : ne pas éditer pjsip.conf

Sur **FreePBX**, la configuration n’est **pas** dans les fichiers Asterisk classiques. Le flux est :

```text
Interface FreePBX  ──►  Base MariaDB  ──►  fwconsole reload  ──►  fichiers générés
   (ou scripts)              (asterisk)                         (/etc/asterisk/*.conf)
```

### Fichiers à ne pas modifier à la main

| Fichier | Pourquoi |
|---------|----------|
| `/etc/asterisk/pjsip.conf` | Fichier d’inclusion généré |
| `/etc/asterisk/pjsip.endpoint.conf` | Endpoints régénérés à chaque reload |
| `/etc/asterisk/pjsip.auth.conf` | Auth régénérée |
| `/etc/asterisk/pjsip.aor.conf` | AOR régénérés |
| `/etc/asterisk/extensions.conf` | Dialplan principal généré |
| `/etc/asterisk/extensions_additional.conf` | Dialplan FreePBX généré |

**Conséquence** : si tu modifies `pjsip.conf` directement, tes changements **disparaissent** au prochain `fwconsole reload` et **n’apparaissent pas** dans l’interface.

### Fichiers sûrs pour du custom (hors interface)

| Fichier | Usage |
|---------|-------|
| `/etc/asterisk/extensions_custom.conf` | Dialplan personnalisé (8000, 7000, IVR…) |
| `/etc/asterisk/pjsip_custom.conf` | Override PJSIP (avant génération) |
| `/etc/asterisk/pjsip_custom_post.conf` | Override PJSIP (après génération) |
| `/etc/asterisk/manager_custom.conf` | Utilisateurs AMI (monitoring) |
| `/etc/asterisk/queues_custom.conf` | Files d’attente custom |

**Règle** : extensions, trunks, routes → **interface FreePBX** ou **scripts du projet** qui écrivent dans la base.

---

## 2. Accéder à l’interface

| Élément | Valeur |
|---------|--------|
| URL | `https://192.168.1.104` ou `http://192.168.1.104` |
| Nom mDNS | `pbx.local` (si mDNS actif sur le LAN) |
| VLAN voix | `https://10.10.10.10` (si routage OK) |
| VPN distant | `https://192.168.1.104` via tunnel WireGuard |

**Connexion** : identifiants admin FreePBX (créés à l’installation).

**Si l’UI ne charge pas** :
```bash
sudo systemctl status apache2
sudo tail -n 50 /var/log/apache2/error.log
```

---

## 3. Carte des menus FreePBX

L’interface est organisée en sections. Les noms peuvent varier légèrement selon la langue (FR/EN) et la version.

### Barre latérale principale

```text
┌─────────────────────────────────────────────────────────────┐
│  FreePBX                                                    │
├─────────────────────────────────────────────────────────────┤
│  📊 Tableau de bord (Dashboard)                            │
│                                                             │
│  📱 Applications                                            │
│     ├─ Extensions          ← postes 1001–1010              │
│     ├─ Ring Groups         ← groupes de sonnerie (GUI)     │
│     ├─ Conferences         ← conférences                   │
│     ├─ Queues              ← files d’attente (ACD)         │
│     ├─ IVR                 ← menus vocaux interactifs      │
│     └─ Voicemail           ← messagerie vocale             │
│                                                             │
│  🔌 Connectivité                                            │
│     ├─ Trunks              ← opérateur PSTN, inter-PBX     │
│     ├─ Routes sortantes    ← appels vers l’extérieur       │
│     └─ Routes entrantes    ← appels entrants (DID)         │
│                                                             │
│  ⚙️ Réglages (Settings)                                   │
│     ├─ Asterisk SIP Settings  ← ports, transports, codecs  │
│     ├─ Asterisk Log Files     ← logs                       │
│     └─ Advanced Settings      ← options avancées           │
│                                                             │
│  👤 Admin                                                   │
│     ├─ Module Admin        ← installer/mettre à jour       │
│     ├─ Certificate Management  ← certificats TLS           │
│     ├─ Backup & Restore    ← sauvegardes                   │
│     └─ Updates             ← mises à jour FreePBX          │
│                                                             │
│  📈 Reports                                                 │
│     ├─ Asterisk Info       ← état système                  │
│     ├─ Call Event Logging  ← CDR                           │
│     └─ Asterisk Log Files  ← consultation logs             │
└─────────────────────────────────────────────────────────────┘
```

### Équivalences FR / EN courantes

| Français (approx.) | Anglais FreePBX | Contenu |
|--------------------|-----------------|---------|
| Applications | Applications | Extensions, IVR, conférences… |
| Connectivité | Connectivity | Trunks, routes |
| Réglages | Settings | SIP, logs, avancé |
| Admin | Admin | Modules, certificats |
| Rapports | Reports | CDR, logs, infos |

---

## 4. Où configurer quoi (table rapide)

| Besoin | Menu FreePBX | Alternative script |
|--------|--------------|-------------------|
| Créer extension 1005 | Applications → Extensions → Ajouter | `scripts/phase2-create-extensions.php` |
| Activer WebRTC sur 1003 | Applications → Extensions → 1003 → Avancé | `scripts/align-pjsip-site.sh` |
| Changer mot de passe SIP | Applications → Extensions → 1003 → Secret | UI ou base (éviter pjsip.conf) |
| Trunk opérateur OVH | Connectivité → Trunks → Ajouter PJSIP | `scripts/apply-trunks.sh` |
| Appels vers mobile (06…) | Connectivité → Routes sortantes | `scripts/apply-trunks.sh` |
| Appels entrants (DID) | Connectivité → Routes entrantes | `scripts/apply-trunks.sh` |
| Ports 5060 / 5061 / 8089 | Réglages → Asterisk SIP Settings | `scripts/enable-webrtc-websocket.sh` |
| Certificat TLS | Admin → Certificate Management | `scripts/phase4-assign-pjsip-tls-cert.php` |
| IVR 7000 / file 7020 | Applications → IVR / Queues **ou** dialplan custom | `scripts/phase3-apply-asterisk.sh` |
| Conférence 8001 | Applications → Conferences **ou** dialplan custom | `extensions_custom.conf` |
| Messagerie vocale | Applications → Extensions → Voicemail | `scripts/phase2-enable-voicemail.php` |
| Pare-feu / réseau | (hors FreePBX) | `scripts/net-apply-site.sh` |
| VPN télétravail | (hors FreePBX) | `scripts/install-startup-service.sh`, WireGuard |

---

## 5. Interface vs scripts vs fichiers

```text
                    ┌─────────────────────┐
                    │   Toi (admin)       │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      Interface Web     Scripts projet    Fichiers custom
      (FreePBX GUI)     (apply-*.sh)      (*_custom.conf)
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    Base MariaDB (asterisk)
                              │
                              ▼
                    sudo fwconsole reload
                              │
                              ▼
                    /etc/asterisk/*.conf (générés)
```

### Scripts du projet et leur équivalent UI

| Script | Équivalent interface |
|--------|---------------------|
| `phase2-create-extensions.php` | Applications → Extensions (création en masse) |
| `align-pjsip-site.sh` | Applications → Extensions → onglet Avancé (WebRTC, codecs) |
| `apply-trunks.sh` | Connectivité → Trunks + Routes |
| `net-apply-site.sh` | Réglages SIP (localnets) + UFW (hors GUI) |
| `enable-webrtc-websocket.sh` | Réglages → Asterisk SIP Settings → WS/WSS |
| `phase4-assign-pjsip-tls-cert.php` | Admin → Certificate Management |
| `fix-cert-perms.sh` | (permissions fichiers, pas dans l’UI) |
| `server-startup.sh` | (démarrage système, pas dans l’UI) |

**Quand utiliser l’interface plutôt qu’un script ?**
- Modification ponctuelle d’**une** extension
- Test visuel (voir l’état, les options)
- Découverte / apprentissage

**Quand utiliser un script ?**
- Déploiement reproductible (plusieurs postes, trunks, routes)
- Versionné dans Git (`network/*.env`)
- Automatisation au démarrage

---

## 6. Extensions PJSIP (1001–1010)

### Accès interface

**Applications → Extensions → cliquer sur le numéro (ex. 1003)**

Onglets utiles :

| Onglet | Contenu |
|--------|---------|
| **General** | Nom affiché, Caller ID |
| **Advanced** | WebRTC, NAT, codecs, DTLS |
| **Voicemail** | Boîte vocale, e-mail, PIN |
| **Find Me / Follow Me** | Renvoi si absent |
| **Recording** | Enregistrement des appels |

### Profils actuels du projet

| Extensions | Type | Transport | Script |
|------------|------|-----------|--------|
| 1001, 1002 | Classique (Zoiper, téléphone IP) | UDP / TLS | `network/pjsip-align.env` → `CLASSIC_EXTENSIONS` |
| 1003–1010 | WebRTC (navigateur, WSS) | WebSocket | `WEBRTC_EXTENSIONS` |

### Secrets SIP

```bash
sudo cat /root/phase2-pjsip-secrets.txt
```

Format : `extension<TAB>secret` (ex. `1003	abc123...`)

**Ne jamais** mettre ces secrets dans Git.

### Vérifier l’enregistrement (hors interface)

```bash
sudo asterisk -rx "pjsip show contacts"
sudo asterisk -rx "pjsip show endpoint 1003"
```

Un poste **Reachable** = enregistré et joignable.

### Modifier WebRTC via l’interface (ex. extension 1003)

1. **Applications → Extensions → 1003**
2. Onglet **Advanced** (ou **PJSIP Advanced**)
3. Activer :
   - **WebRTC** : Yes
   - **DTLS Enable** : Yes
   - **ICE Support** : Yes
   - **RTCP MUX** : Yes
   - **AVPF** : Yes
4. **Media Encryption** : DTLS
5. Codecs : `g722`, `ulaw`, `alaw`
6. **Submit** puis **Apply Config** (barre orange en haut)

---

## 7. Transports SIP : UDP, TLS, WebSocket

### Accès interface

**Réglages (Settings) → Asterisk SIP Settings → onglet Chan PJSIP**

| Transport | Port | Usage |
|-----------|------|--------|
| UDP | 5060 | Téléphones IP, Zoiper, Linphone |
| TLS | 5061 | Softphones sécurisés |
| WS | 8088 | WebRTC (signalisation HTTP) |
| WSS | 8089 | WebRTC (signalisation TLS) |

### Vérifier côté serveur

```bash
sudo asterisk -rx "pjsip show transports"
```

Résultat attendu :
```text
0.0.0.0-udp     → 5060
0.0.0.0-tls     → 5061
transport-wss   → 8089
```

### WebRTC côté client

URL type : `wss://pbx.local:8089/ws`

Si `pbx.local` ne résout pas (Windows sans mDNS) :
```text
# C:\Windows\System32\drivers\etc\hosts
192.168.1.104  pbx.local  pbx
```

---

## 8. Trunks et routes (PSTN, inter-PBX)

### Trunks

**Connectivité → Trunks**

| Trunk projet | Nom | Rôle | État |
|--------------|-----|------|------|
| PSTN | `trunk-operateur-pstn` | Appels vers/fixe/mobile | Désactivé sans identifiants opérateur |
| Inter-PBX | `trunk-interpbx-site-b` | Lien avec autre PBX | Actif (réception LAN + VPN) |

**Créer un trunk via l’interface :**
1. Connectivité → Trunks → **Add Trunk**
2. Choisir **Add PJSIP Trunk**
3. Renseigner : serveur SIP, username, secret, transport
4. **Submit** → **Apply Config**

**Via script (recommandé pour ce projet) :**
```bash
sudo nano /root/trunks-secrets.env    # PSTN_USERNAME, PSTN_SECRET
sudo bash scripts/apply-trunks.sh
```

### Routes sortantes

**Connectivité → Outbound Routes**

| Route | Pattern | Trunk |
|-------|---------|-------|
| France-metropole | `0XXXXXXXXX` | trunk-operateur-pstn |
| International | `00.` | trunk-operateur-pstn |
| Inter-PBX-site-B | `8X.` | trunk-interpbx-site-b |

**Tester** : depuis 1001, composer `0612345678` (quand trunk PSTN actif).

### Routes entrantes

**Connectivité → Inbound Routes**

| Route | DID | Destination |
|-------|-----|-------------|
| Catch-all | (vide) | IVR 7000 |
| DID principal | `+33…` (à configurer) | IVR 7000 ou extension |

---

## 9. IVR, files d’attente, conférences

### Numéros utiles (dialplan custom + Phase 3)

| Numéro | Fonction | Configuré via |
|--------|----------|---------------|
| **8000** | Sonnerie groupe (1001–1010) | `extensions_custom.conf` |
| **7000** | Routage horaire → IVR ou fermeture | `extensions_custom.conf` |
| **7010** | IVR intelligent (AGI Python) | `extensions_custom.conf` |
| **7020** | File d’attente `phase3-support` (1001–1010) | `queues-ivr.conf` + `apply-ivr-queues.sh` |
| **7101–7110** | File IVR par extension (`ivr-ext-1001` … `ivr-ext-1010`) | idem |
| **7010** | IVR AGI + saisie extension → queue dédiée | idem |
| **8001** | Conférence (PIN 1234) | `extensions_custom.conf` |

### Interface vs custom

| Service | Interface FreePBX | Fichier custom actuel |
|---------|-------------------|----------------------|
| IVR simple | Applications → IVR | Non (AGI custom 7010) |
| File d’attente | Applications → Queues | `queues_custom.conf` |
| Conférence | Applications → Conferences | Dialplan 8001 custom |
| Ring group | Applications → Ring Groups | Dialplan 8000 custom |

**Pour modifier 8000 / 7000** : éditer `/etc/asterisk/extensions_custom.conf`, puis :
```bash
sudo fwconsole reload
```

---

## 10. Messagerie vocale et e-mail

### Pas de menu « Voicemail » au premier niveau

FreePBX 16 n’affiche **pas** un menu global « Voicemail » dans la barre latérale (contrairement à d’anciennes versions). La messagerie se gère **par extension** :

**Applications → Extensions → [extension] → onglet Voicemail**

Les messages enregistrés sont aussi visibles dans **Reports → CDR** (durée) et sur disque sous `/var/spool/asterisk/voicemail/default/<ext>/INBOX/`.

### Codes d’accès téléphone (recommandé)

| Extension | Code direct | PIN (autre poste) |
|-----------|-------------|-------------------|
| 1001 | `*81001` | `1001` |
| 1003 | `*81003` | `1003` |
| … | `*81` + 3 derniers chiffres | idem |

Depuis **son propre poste** : composer le code → accès direct aux messages (sans tutoriel initial).

**Empilement** : plusieurs messages (même appelant ou non) s’accumulent dans la **même boîte** ; le code ne change pas. À l’écoute, Asterisk annonce « vous avez X nouveaux messages ».

**Notification** : **aucun e-mail avec WAV**. À chaque nouveau message, le PBX envoie un **SIP MESSAGE** sur le même flux que le chat Asaphone (`from-message`), avec un JSON :

```json
{"type":"voicemail","vm_code":"*81003","caller":"1001","text":"Nouveau message vocal…","deeplink":"asaphone://voicemail?code=*81003&ext=1003"}
```

Installation : `sudo bash scripts/apply-voicemail-codes.sh` + `sudo bash scripts/apply-message-dialplan.sh` + `sudo php scripts/apply-voicemail-policy.php`

**Récupération côté Asaphone** :
- **À la reconnexion** (poste était offline) : `GET https://pbx.local/provision/api/v1/voicemail/pending.php?ext=1003` + header `X-Provision-Jti: <jti>` → notifications en attente + liens écoute
- Deep link : `asaphone://voicemail?code=*81003&ext=1003`
- Liste complète : `GET .../voicemail/open.php?ext=1003` + `X-Provision-Jti`
- Écoute audio : `GET .../voicemail/listen.php?ext=1003&jti=<jti>&msg=msg0010`

Le **fichier audio** est toujours sur le serveur (`/var/spool/asterisk/voicemail/...`) même si le destinataire est déconnecté.

**Messages chat texte** : chaque MESSAGE est enregistré en base (`provision_chat_messages`). Si le SIP instantané échoue (offline), récupération à la reconnexion :

`GET https://pbx.local/provision/api/v1/chat/pending.php?ext=1001` + header `X-Provision-Jti: <jti>`

Ne renvoie que les messages **non livrés en SIP** (`sip_delivered=0`). Un message déjà reçu en live n’est pas re-proposé. Chaque message renvoyé par le GET est **retiré de la file** immédiatement (pas de doublon à la reconnexion suivante).

### Interface

**Applications → Extensions → [extension] → onglet Voicemail**

| Paramètre | Valeur par défaut projet |
|-----------|--------------------------|
| Enable | Oui |
| PIN | 4 derniers chiffres (ex. 1003 → `1003`) |
| E-mail | À renseigner par poste |
| Attach WAV | Oui (`attach=yes`) |

### SMTP (envoi e-mail)

Hors menu simple : configurer **Postfix** ou relais SMTP sur le serveur, puis vérifier dans les paramètres messagerie FreePBX.

**Tester** : laisser un message sur 1003, vérifier réception e-mail.

---

## 11. Certificats TLS et sécurité

### Interface

**Admin → Certificate Management (Certman)**

| Usage | Certificat |
|-------|------------|
| HTTPS FreePBX | default ou Let’s Encrypt |
| SIP TLS 5061 | Assigner dans SIP Settings |
| WSS 8089 | Même certificat PJSIP |

**Réglages → Asterisk SIP Settings → TLS** : sélectionner le certificat **default**.

### Scripts projet

```bash
sudo bash scripts/fix-cert-perms.sh
sudo php scripts/phase4-assign-pjsip-tls-cert.php
sudo bash scripts/phase4-apply-fail2ban.sh
```

### Fail2Ban

Pas dans l’interface FreePBX — géré par le système (`/etc/fail2ban/`).

---

## 12. Monitoring Grafana

| Service | URL | Menu / accès |
|---------|-----|--------------|
| Grafana | `http://192.168.1.104:3000` | Hors FreePBX (Docker) |
| InfluxDB | `:8086` | Hors FreePBX |

**FreePBX** : pas de dashboard natif équivalent — utiliser Grafana pour les métriques Asterisk.

Démarrage :
```bash
cd monitoring && docker compose up -d
```

---

## 13. Logs et diagnostic dans l’interface

### Via FreePBX

**Reports → Asterisk Log Files** (ou **Réglages → Asterisk Log Files**)

| Fichier | Contenu |
|---------|---------|
| `full` | Tout Asterisk (SIP, dialplan, erreurs) |
| `security` | Tentatives auth, sécurité |

### Via terminal (plus détaillé)

```bash
# Console interactive
sudo asterisk -rvvv

# Logs SIP
sudo asterisk -rx "pjsip set logger on"

# RTP (pas d’audio)
sudo asterisk -rx "rtp set debug on"

# Fin debug
sudo asterisk -rx "pjsip set logger off"
sudo asterisk -rx "rtp set debug off"
```

### CDR (historique appels)

**Reports → Call Event Logging** ou **CDR**

---

## 14. Appliquer les changements (reload)

Après **toute** modification dans l’interface :

1. Cliquer **Submit** sur le formulaire
2. Cliquer **Apply Config** (barre orange en haut de l’écran)

Ou en ligne de commande :
```bash
sudo fwconsole reload
```

**Attention** : `fwconsole reload` **régénère** tous les fichiers PJSIP — d’où l’importance de ne pas éditer `pjsip.conf` à la main.

### Démarrage complet du serveur

```bash
sudo systemctl start serveur-startup.service   # FreePBX + réseau + certs
sudo systemctl start wg-quick@wg0              # VPN
```

---

## 15. Logiciels pour tester avec des softphones

### Softphones manuels (tests utilisateur réels)

| Logiciel | Plateforme | Protocole | Extensions test |
|----------|------------|-----------|-----------------|
| **Zoiper 5** | Win/Mac/Linux/Mobile | UDP, TLS | 1001, 1002 |
| **Linphone** | Win/Mac/Linux/Mobile | UDP, TLS | 1001–1010 |
| **MicroSIP** | Windows (léger) | UDP | 1001, 1002 |
| **Asaphone** (client maison) | Navigateur | WebRTC/WSS | 1003–1010 |

### Paramètres softphone (résumé)

| Paramètre | Valeur |
|-----------|--------|
| Serveur | `192.168.1.104` ou `pbx.local` |
| UDP | port `5060` |
| TLS | port `5061` |
| WebRTC | `wss://pbx.local:8089/ws` |
| Utilisateur | `1001` … `1010` |
| Mot de passe | `/root/phase2-pjsip-secrets.txt` |

### Outils techniques (sans softphone)

| Outil | Usage |
|-------|-------|
| `sudo asterisk -rvvv` | Console temps réel |
| **Wireshark** | Analyse paquets SIP/RTP |
| **SIPp** | Simulation d’appels automatisés |
| **SIPvicious** | Audit / scan SIP |
| **Grafana** | Métriques continues |

---

## 16. Plan de test complet

Checklist pour valider le serveur :

| # | Test | Comment | OK ? |
|---|------|---------|------|
| 1 | UI FreePBX accessible | `https://192.168.1.104` | ☐ |
| 2 | 1001 s’enregistre (Zoiper UDP) | `pjsip show contacts` → Reachable | ☐ |
| 3 | 1003 s’enregistre (WebRTC WSS) | `pjsip show contacts` → Reachable | ☐ |
| 4 | Appel 1001 → 1003 | Audio bidirectionnel | ☐ |
| 5 | Appel 1003 → 1001 | Mix WebRTC ↔ UDP | ☐ |
| 6 | Ring group 8000 | Tous les postes sonnent | ☐ |
| 7 | IVR 7000 | Horaire ouvert/fermé | ☐ |
| 8 | Conférence 8001 (PIN 1234) | Plusieurs participants | ☐ |
| 9 | Messagerie vocale 1003 | Laisser message, consulter | ☐ |
| 10 | VPN + softphone distant | Contact IP `10.200.0.x` | ☐ |
| 11 | Trunk inter-PBX (préfixe 8) | Quand 2e PBX disponible | ☐ |
| 12 | Trunk PSTN (06…) | Quand identifiants opérateur | ☐ |
| 13 | Grafana | `http://192.168.1.104:3000` | ☐ |

---

## 17. Erreurs fréquentes

| Symptôme | Cause | Solution |
|----------|-------|----------|
| Modif `pjsip.conf` perdue | Fichier régénéré par FreePBX | Passer par l’interface ou scripts |
| Extension Unavailable | Pas d’enregistrement REGISTER | Vérifier softphone, mot de passe, UFW |
| 488 Not Acceptable | WebRTC mal configuré | Extensions → WebRTC + DTLS + ICE |
| Pas d’audio | RTP bloqué ou ICE | UFW ports 10000–20000, `rtp set debug on` |
| TLS échoue | Certificat non assigné | Certificate Management + SIP Settings |
| `pbx.local` ne résout pas | Pas de mDNS | Fichier `hosts` Windows |
| Trunk PSTN inactif | Pas de credentials | `/root/trunks-secrets.env` |
| UI FreePBX lente / sessions | Sessions PHP | `server-startup.sh` nettoie les sessions |

---

## 18. Documents liés

| Document | Sujet |
|----------|-------|
| `S2-Phase2-Utilisateurs-Extensions.md` | Extensions, softphones, 8000 |
| `S3-Phase3-IVR-Monitoring.md` | IVR 7000, Grafana, files |
| `S4-Phase4-Securite-complete.md` | TLS, SRTP, Fail2Ban |
| `docs/trunk.md` | Trunks SIP, routes |
| `docs/vpn.md` | VPN vs trunk, télétravail |
| `docs/implement-VPN.md` | Installation WireGuard |
| `docs/Configuration-VLAN-VoIP-production.md` | VLAN 10, réseau |
| `network/site.env` | Profil réseau |
| `network/trunks.env` | Configuration trunks |
| `network/pjsip-align.env` | Extensions WebRTC/classiques |

---

*Guide interface FreePBX — projet serveur VoIP. Mettre à jour les IP si le réseau change (`network/site.env` + `net-apply-site.sh`).*
