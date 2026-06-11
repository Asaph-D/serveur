# Asaphone — parcours d’inscription et provisionnement

Scénario utilisateur : à l’ouverture d’**Asaphone**, l’utilisateur choisit s’il a déjà ses identifiants ou s’il souhaite **s’enregistrer** pour les recevoir par e-mail (après vérification), puis **scanne un QR** et se connecte au PBX comme aujourd’hui.

**Pas d’API backend séparée** : tout tourne sur le **même serveur FreePBX** (Apache + PHP + MariaDB + SMTP Gmail).

**État** : mini-API provisionnement **implémentée** (`/var/www/provision/`, juin 2026).

Voir aussi : `security/cryptographic_implementation.md` (couches L6, normes crypto).

---

## Table des matières

1. [Vue d’ensemble](#1-vue-densemble)
2. [Écran d’accueil Asaphone](#2-écran-daccueil-asaphone)
3. [Parcours A — J’ai déjà mes identifiants](#3-parcours-a--jai-déjà-mes-identifiants)
4. [Parcours B — M’enregistrer](#4-parcours-b--menregistrer)
5. [Vérification e-mail](#5-vérification-e-mail)
6. [Envoi du QR par courrier électronique](#6-envoi-du-qr-par-courrier-électronique)
7. [Scan QR et connexion SIP (inchangée)](#7-scan-qr-et-connexion-sip-inchangée)
8. [Où ça vit sur le serveur (sans API externe)](#8-où-ça-vit-sur-le-serveur-sans-api-externe)
9. [Mini-API PHP sur le PBX](#9-mini-api-php-sur-le-pbx)
10. [Base de données](#10-base-de-données)
11. [Sécurité du flux](#11-sécurité-du-flux)
12. [Attribution d’extension](#12-attribution-dextension)
13. [Fichiers (implémentés)](#13-fichiers-implémentés)
14. [Roadmap](#14-roadmap)
15. [HTTPS et commandes de scénario](#15-https-et-commandes-de-scénario)

---

## 1. Vue d’ensemble

```text
                    ┌─────────────────┐
                    │    Asaphone     │
                    │  (client WSS)   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                                       │
         ▼                                       ▼
  « J’ai déjà mes ID »                  « M’enregistrer »
         │                                       │
         │                                       ▼
         │                              Saisie e-mail
         │                                       │
         │                                       ▼
         │                         Mini-API PHP (même serveur)
         │                         Vérif e-mail + token
         │                                       │
         │                                       ▼
         │                         Mail avec QR chiffré
         │                                       │
         └───────────────────┬───────────────────┘
                             ▼
                      Scan QR (ou saisie manuelle)
                             ▼
                   REGISTER WSS → PBX (comme aujourd’hui)
                             ▼
                        Appels internes
```

| Étape | Canal | Couche sécurité |
|-------|-------|-----------------|
| Choix utilisateur | UI Asaphone | — |
| Vérification e-mail | HTTPS + mail | L3 + SMTP TLS |
| QR / identifiants | E-mail + scan | L6 provisionnement |
| Appels | WSS + DTLS-SRTP | L4 + L5 (inchangé) |

---

## 2. Écran d’accueil Asaphone

Au premier lancement (ou dans Paramètres → Compte) :

```text
┌──────────────────────────────────────┐
│           Bienvenue sur Asaphone      │
│                                       │
│   [ J’ai déjà mes identifiants ]      │
│                                       │
│   [ M’enregistrer pour recevoir       │
│     mes identifiants par e-mail ]     │
│                                       │
└──────────────────────────────────────┘
```

| Bouton | Action |
|--------|--------|
| **J’ai déjà mes identifiants** | Formulaire manuel ou scan QR reçu autrement → Parcours A |
| **M’enregistrer** | Formulaire e-mail → Parcours B |

---

## 3. Parcours A — J’ai déjà mes identifiants

L’utilisateur a reçu ses identifiants par un autre canal (admin, QR papier, mail précédent).

```text
Écran connexion
  ├─ Serveur : pbx.local (pré-rempli)
  ├─ Extension : 1003
  ├─ Mot de passe : ****
  └─ [ Se connecter ]  ou  [ Scanner un QR ]

→ WebRTC REGISTER wss://pbx.local:8089/ws
→ Identique au comportement actuel
```

**Aucun appel** à la mini-API de provisionnement.

---

## 4. Parcours B — M’enregistrer

### Étape B1 — Saisie e-mail

```text
┌──────────────────────────────────────┐
│   Créer mon compte téléphonique       │
│                                       │
│   E-mail : [___________________]      │
│                                       │
│   [ Envoyer le code de vérification ] │
│                                       │
└──────────────────────────────────────┘
```

Asaphone appelle :

```http
POST https://pbx.local/provision/api/v1/register
Content-Type: application/json

{ "email": "utilisateur@example.com" }
```

Réponse :

```json
{
  "status": "pending_verification",
  "message": "Un e-mail de vérification a été envoyé."
}
```

### Étape B2 — Attente vérification

L’utilisateur consulte sa boîte mail et clique le lien **ou** saisit le code à 6 chiffres dans Asaphone.

---

## 5. Vérification e-mail

### Mécanisme recommandé : code à 6 chiffres + lien

| Élément | Valeur |
|---------|--------|
| Code | 6 chiffres aléatoires (ex. `482913`) |
| Durée | 15 minutes |
| Stockage | Table `provision_requests` (hash du code, pas en clair) |
| E-mail | « Votre code Asaphone : 482913 » + lien `https://pbx.local/provision/verify?token=...` |

### Vérification depuis Asaphone

```http
POST https://pbx.local/provision/api/v1/verify
Content-Type: application/json

{
  "email": "utilisateur@example.com",
  "code": "482913"
}
```

Réponse si OK :

```json
{
  "status": "verified",
  "message": "E-mail confirmé. Vos identifiants arrivent par e-mail sous peu."
}
```

### Vérification depuis le lien e-mail (navigateur)

Le lien ouvre une page PHP légère : « E-mail vérifié. Vous pouvez fermer cette page et retourner dans Asaphone. »

---

## 6. Envoi du QR par courrier électronique

**Déclenchement** : automatiquement après vérification e-mail réussie (ou après validation admin — voir §12).

### Ce que fait le serveur

1. Attribue une **extension libre** (ex. prochaine dans le pool `1003–1010` ou file d’attente admin)
2. Génère ou récupère le **secret PJSIP** de l’extension
3. Construit le **payload chiffré** (JWE / token — voir `cryptographic_implementation.md` §9)
4. Génère une **image QR** (PNG) ou un **lien one-shot**
5. Envoie l’e-mail via **SMTP Gmail** (`smtp.gmail.com:587`, STARTTLS) — client PHP embarqué, sans Postfix

### Contenu de l’e-mail (exemple)

```text
Objet : Vos identifiants Asaphone — action requise

Bonjour,

Votre compte téléphonique est prêt.

1. Ouvrez Asaphone sur votre appareil
2. Choisissez « Scanner un QR » ou « J’ai déjà mes identifiants »
3. Scannez le QR ci-dessous (valable 24 h)

[IMAGE QR]

Extension : 1007
Serveur : pbx.local

Ce QR est personnel et à usage unique.
```

**Ne pas** mettre le mot de passe SIP en clair dans le corps du mail si le QR est auto-suffisant.

### Niveau technique de l’envoi

```text
provision/lib/mail.php + provision/lib/tokens.php
        │
        ├─► MariaDB (extension, jti, claim_token, exp)
        ├─► Génération QR (qrencode → PNG embarqué dans le mail)
        └─► SMTP direct → smtp.gmail.com:587 (AUTH LOGIN + STARTTLS)
```

C’est la **couche L6** (provisionnement) — toujours sur le PBX, pas sur une API cloud séparée.

### Configuration SMTP (Gmail)

Secrets dans `/etc/provision/provision-secrets.env` (chmod 640, hors Git) :

| Variable | Rôle |
|----------|------|
| `EMAIL_USER` | Compte Gmail + **AUTH SMTP** + enveloppe `MAIL FROM` (obligatoire chez Google) |
| `EMAIL_PASSWORD` | Mot de passe d’application Google (16 caractères) |
| `EMAIL_FROM` | Adresse d’affichage souhaitée (`noreply@asaphone.com`) — utilisée en **Reply-To** |
| `EMAIL_HOST` / `EMAIL_PORT` | `smtp.gmail.com` / `587` |
| `EMAIL_ENABLED` | `true` pour activer l’envoi |

**Important Gmail** : sans alias « Envoyer des e-mails en tant que » configuré dans le compte Google, l’expéditeur affiché reste `EMAIL_USER` (ex. `kouokamasaph142@gmail.com`). Pour afficher `noreply@asaphone.com`, ajouter cet alias dans Gmail → Paramètres → Comptes → « Envoyer des e-mails en tant que ».

Test manuel :

```bash
sudo php /home/asaph/Documents/serveur/scripts/provision-send-mail.php --to destinataire@gmail.com
```

---

## 7. Scan QR et connexion SIP (inchangée)

Une fois le QR scanné dans Asaphone :

```text
1. Asaphone scanne le QR → URL claim one-shot (ou schéma asaphone://provision?url=...)
2. GET /provision/api/v1/claim.php?token=... → credentials JSON
3. Récupère : extension, secret, server, transport=wss, port=8089
4. Configure le client SIP interne
5. REGISTER → wss://pbx.local:8089/ws
6. Auth Digest + média DTLS-SRTP (WebRTC)
7. POST /consume avec jti (ou hook AMI) → token révoqué
8. Statut « Enregistré » — identique au flux actuel
```

```text
Asaphone  ──WSS/TLS──►  PBX Asterisk  ──►  from-internal / appels
```

**Rien ne change** dans la couche SIP/WebRTC après provisionnement : seule la **phase d’onboarding** est nouvelle.

### Marquer le token consommé

```http
POST https://pbx.local/provision/api/v1/consume
{ "jti": "uuid-du-token" }
```

Ou automatiquement au premier REGISTER réussi (hook AMI / script).

---

## 8. Où ça vit sur le serveur (sans API externe)

```text
┌─────────────────────────────────────────────────────────────┐
│  Serveur Linux (192.168.1.104) — UN SEUL HÔTE              │
├─────────────────────────────────────────────────────────────┤
│  Apache                                                     │
│    ├─ /admin/          → FreePBX (UI admin existante)       │
│    └─ /provision/    → Mini-API PHP + pages verify (NOUVEAU)│
├─────────────────────────────────────────────────────────────┤
│  PHP CLI scripts/    → provision-*.php (cron, admin)        │
├─────────────────────────────────────────────────────────────┤
│  MariaDB (asterisk)  → extensions + provision_* tables      │
├─────────────────────────────────────────────────────────────┤
│  SMTP Gmail          → e-mails vérification + QR (PHP)      │
│  /etc/provision/     → provision.env + provision-secrets.env│
├─────────────────────────────────────────────────────────────┤
│  Asterisk/FreePBX    → REGISTER WSS (inchangé)              │
└─────────────────────────────────────────────────────────────┘
```

| Composant | « API backend » ? |
|-----------|-------------------|
| `/provision/api/v1/*` | Mini-API **embarquée** sur le PBX (quelques endpoints PHP) |
| FreePBX | Admin + base extensions |
| Asaphone | Client uniquement — appelle le PBX en HTTPS puis WSS |

Tu n’as pas besoin de Node.js, Django ou microservice séparé pour ce scénario.

---

## 9. Mini-API PHP sur le PBX

Endpoints sous `https://pbx.local/provision/api/v1/` :

| Méthode | Fichier | Rôle |
|---------|---------|------|
| `POST` | `register.php` | Saisie e-mail → envoi code vérification (6 chiffres) |
| `POST` | `verify.php` | Valide code → `pending_admin` ou envoi QR (selon politique) |
| `GET` | `claim.php?token=` | Retourne credentials SIP (token one-shot) |
| `GET` | `status.php?email=` | État compte + `extension_info` si attribuée |
| `GET` | `extension.php?ext=` | Extension libre / associée à un compte |
| `GET` | `extension.php` | État de tout le pool `1003–1010` |
| `POST` | `consume.php` | Révoque token après scan / REGISTER (`jti`) |

Page web : `https://pbx.local/provision/verify/` — saisie code depuis le lien e-mail.

### Hébergement Apache

Installé via `scripts/provision-install.sh` → `/etc/apache2/conf-available/provision.conf` :

```apache
Alias /provision /var/www/provision
<Directory /var/www/provision>
    Options -Indexes +FollowSymLinks
    AllowOverride None
    Require all granted
</Directory>
```

Isolé de l’admin FreePBX (pas de session admin pour register) ; rate-limit IP/e-mail actif.

### Prérequis

- **HTTPS** actif sur le port 443 (`scripts/enable-apache-https.sh`) — certificat FreePBX `/etc/asterisk/keys/default.crt`
- **UFW** : `80/tcp` et `443/tcp` ouverts (LAN / VPN)
- **SMTP Gmail** : `EMAIL_USER` + mot de passe d’application dans `/etc/provision/provision-secrets.env`
- **qrencode** : génération PNG des QR

### HTTPS

Pas de service séparé : la mini-API est servie par **Apache** (comme FreePBX). Au démarrage, `serveur-startup.service` appelle `enable-apache-https.sh`.

Activation manuelle :

```bash
sudo bash /home/asaph/Documents/serveur/scripts/enable-apache-https.sh
```

Certificat actuel : auto-signé Certman (CN du serveur). Les clients doivent faire confiance au certificat ou utiliser `curl -k` en test. Pour un certificat reconnu : FreePBX → Admin → Certificats → Let’s Encrypt, puis relancer le script.

---

## 10. Base de données

Tables dédiées (base `asterisk` ou `provision` séparée) :

### `provision_requests`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INT PK | |
| `email` | VARCHAR | E-mail utilisateur |
| `email_verified` | TINYINT | 0/1 |
| `verify_code_hash` | VARCHAR | bcrypt du code 6 chiffres |
| `verify_expires` | DATETIME | |
| `extension` | VARCHAR | Attribuée après vérif |
| `status` | ENUM | pending, verified, pending_admin, provisioned, revoked |
| `created_at` | DATETIME | |

### `provision_tokens`

| Colonne | Type | Description |
|---------|------|-------------|
| `jti` | VARCHAR PK | UUID token QR |
| `extension` | VARCHAR | |
| `email` | VARCHAR | |
| `claim_token` | VARCHAR | Token opaque dans l’URL `/claim.php?token=` |
| `payload_enc` | TEXT | Payload AES-256-GCM optionnel |
| `expires` | DATETIME | |
| `used` | TINYINT | 0/1 |
| `used_at` | DATETIME | |

### `provision_rate_limits`

Rate-limit par scope (`register_ip`, `register_email`, `verify_ip`) — fenêtre glissante 1 h.

Lien avec FreePBX : secret PJSIP lu depuis `/root/phase2-pjsip-secrets.txt` ou tables `pjsip` / `users`.

---

## 11. Sécurité du flux

| Risque | Mitigation |
|--------|------------|
| Spam inscriptions | Rate-limit par IP + e-mail ; CAPTCHA si exposé WAN |
| Énumération e-mails | Réponse générique « Si l’e-mail existe, un message a été envoyé » |
| Code vérification intercepté | TTL 15 min ; hash en base ; HTTPS |
| QR intercepté | Token usage unique ; expiry 24 h ; révocation `jti` |
| Secret SIP dans mail clair | **QR chiffré uniquement** dans le mail |
| Rejeu QR | `used=1` après premier scan ou REGISTER |
| Extension réservée trop tôt | Seul `provisioned` (après `/consume`) bloque le pool ; `verified` = QR envoyé seulement |
| RGPD | Consentement e-mail ; politique rétention `provision_*` |

---

## 12. Attribution d’extension

Trois politiques possibles (choix métier) :

| Politique | Flux |
|-----------|------|
| **A — Pool automatique** | Après vérif e-mail → assigne prochaine ext libre (1003–1010) → envoi QR |
| **B — Validation admin** | Après vérif e-mail → statut `pending_admin` → admin valide dans FreePBX → envoi QR |
| **C — Pré-provisionnement** | Admin crée ext + e-mail à l’avance → utilisateur ne fait que vérifier que l’e-mail correspond |

**Configuration actuelle** : **`auto`** — QR envoyé automatiquement après vérification du code e-mail.

Config : `network/provision.env` → `PROVISION_POLICY=admin|auto|preprovisioned`

### Vérifier si une extension est libre ou associée

**Règle** : une extension n’est **prise** (`taken=true`) que si le compte s’est **authentifié** au moins une fois (SIP REGISTER → `POST /consume` → statut `provisioned`).  
L’envoi du code de vérification ou du QR **ne réserve pas** l’extension dans le pool.

```bash
curl -sk "https://pbx.local/provision/api/v1/extension.php?ext=1007"
curl -sk "https://pbx.local/provision/api/v1/extension.php"
```

Réponse — libre (QR envoyé mais pas encore authentifié) :

```json
{
  "ok": true,
  "extension": "1007",
  "free": true,
  "taken": false,
  "associated_email": null,
  "pending_email": "user@example.com",
  "pending_status": "verified",
  "reason": "free"
}
```

Réponse — authentifiée (extension garantie) :

```json
{
  "ok": true,
  "extension": "1007",
  "free": false,
  "taken": true,
  "associated_email": "user@example.com",
  "associated_status": "provisioned",
  "reason": "authenticated"
}
```

CLI équivalent :

```bash
sudo php scripts/provision-assign-ext.php --pool
sudo php scripts/provision-assign-ext.php --check 1007
```

---

## 13. Fichiers (implémentés)

```text
/var/www/provision/                    # Déployé par provision-install.sh
  api/v1/register.php
  api/v1/verify.php
  api/v1/claim.php
  api/v1/consume.php
  api/v1/status.php
  verify/index.php
  lib/                                 # config, db, mail, crypto, tokens, …

/etc/provision/
  provision.env                        # Copie de network/provision.env
  provision-secrets.env                # EMAIL_* (hors Git, chmod 640)

/home/asaph/Documents/serveur/
  network/provision.env
  network/provision.secrets.env.example
  provision/                           # Sources (rsync → /var/www/provision)
  scripts/provision-install.sh
  scripts/provision-schema.sql
  scripts/provision-send-mail.php      # Test SMTP
  scripts/provision-assign-ext.php     # Validation admin + envoi QR
  scripts/provision-generate-qr.php
  scripts/enable-apache-https.sh     # Port 443 (cert FreePBX)
  apache/freepbx-ssl.conf
  security/asaphone-onboarding-flow.md ← ce document
```

---

## 14. Roadmap

| Phase | Livrable | État |
|-------|----------|------|
| **1** | SMTP Gmail + test mail ; `provision.env` ; HTTPS 443 | ✅ |
| **2** | Tables SQL + `/register` + `/verify` | ✅ |
| **3** | Génération QR + e-mail credentials + `/claim` | ✅ |
| **4** | Écran Asaphone (2 boutons + scan) | 🔲 côté client |
| **5** | Révocation token + logs audit | ✅ `/consume` ; hook AMI optionnel |
| **6** | Validation admin UI FreePBX | ✅ CLI `provision-assign-ext.php` |

---

## Synthèse

- L’utilisateur choisit dans **Asaphone** : identifiants existants **ou** inscription par e-mail.
- La **vérification e-mail** et l’**envoi du QR** passent par une **mini-API PHP sur le même serveur** + **SMTP Gmail** — pas une API backend séparée.
- Après scan du QR, la **connexion au PBX reste identique** (WSS, REGISTER, DTLS-SRTP).
- La sécurité est en **couche L6** (provisionnement) pour l’onboarding ; **L4/L5** inchangées pour les appels.

---

---

## 15. HTTPS et commandes de scénario

### Installation initiale (une fois)

```bash
# Mini-API + tables SQL + alias Apache + HTTPS
sudo bash /home/asaph/Documents/serveur/scripts/provision-install.sh

# Secrets SMTP (hors Git)
sudo nano /etc/provision/provision-secrets.env
# EMAIL_USER, EMAIL_PASSWORD (mot de passe d'application Google), EMAIL_ENABLED=true

# Copier la config politique
sudo cp /home/asaph/Documents/serveur/network/provision.env /etc/provision/provision.env
sudo chown root:www-data /etc/provision/provision.env /etc/provision/provision-secrets.env
sudo chmod 640 /etc/provision/provision.env /etc/provision/provision-secrets.env
```

### Vérifier que tout tourne

```bash
# Apache + HTTPS (443)
sudo systemctl status apache2
ss -tlnp | grep ':443'

# Santé mini-API (certificat auto-signé → -k)
curl -sk https://pbx.local/provision/
```

Réponse attendue :

```json
{"service":"asaphone-provision","version":"1.0","enabled":true,"policy":"admin","base_url":"https://pbx.local/provision"}
```

### Scénario complet — Parcours B (inscription)

**Étape 1 — Asaphone envoie l’e-mail, serveur délivre le code de vérification**

```bash
curl -sk -X POST https://pbx.local/provision/api/v1/register.php \
  -H 'Content-Type: application/json' \
  -d '{"email":"utilisateur@example.com"}'
```

→ L’utilisateur reçoit un mail avec un **code à 6 chiffres** (valable 15 min).  
→ Asaphone **attend** la saisie du code.

**Étape 2 — Asaphone soumet le code, serveur vérifie**

```bash
curl -sk -X POST https://pbx.local/provision/api/v1/verify.php \
  -H 'Content-Type: application/json' \
  -d '{"email":"utilisateur@example.com","code":"123456"}'
```

Avec `PROVISION_POLICY=auto` (actuel) : **QR envoyé par mail immédiatement** après code valide.

Avec `PROVISION_POLICY=admin` : statut `pending_admin` — pas de QR tant que l’admin n’a pas approuvé.

Alternative navigateur (lien dans le mail) :

```bash
curl -sk "https://pbx.local/provision/verify/?email=utilisateur%40example.com&code=123456"
```

**Étape 3 — (auto) QR déjà envoyé par mail** — ou admin si `PROVISION_POLICY=admin` :

```bash
sudo php /home/asaph/Documents/serveur/scripts/provision-assign-ext.php \
  --approve utilisateur@example.com --extension 1007
```

Vérifier le pool avant/après :

```bash
curl -sk https://pbx.local/provision/api/v1/extension.php
sudo php /home/asaph/Documents/serveur/scripts/provision-assign-ext.php --pool
```

**Étape 4 — Asaphone scanne le QR → récupère les credentials**

```bash
# Récupérer le claim_token en base (debug admin)
sudo mysql -u asteriskuser -p asterisk -N -e \
  "SELECT claim_token FROM provision_tokens WHERE email='utilisateur@example.com' ORDER BY created_at DESC LIMIT 1"

curl -sk "https://pbx.local/provision/api/v1/claim.php?token=TOKEN_ICI"
```

**Étape 5 — Asaphone REGISTER réussi → révoquer le token**

```bash
curl -sk -X POST https://pbx.local/provision/api/v1/consume.php \
  -H 'Content-Type: application/json' \
  -d '{"jti":"UUID_DU_TOKEN"}'
```

### Commandes utiles

```bash
# Test SMTP seul
sudo php /home/asaph/Documents/serveur/scripts/provision-send-mail.php --to test@gmail.com

# État d’une inscription
curl -sk "https://pbx.local/provision/api/v1/status.php?email=utilisateur@example.com"

# Politique auto (sans validation admin) : dans provision.env
# PROVISION_POLICY="auto"
# → verify envoie le QR directement après le code

# Réactiver HTTPS après reboot (déjà dans serveur-startup.service)
sudo bash /home/asaph/Documents/serveur/scripts/enable-apache-https.sh
```

### Politique `auto` — scénario actuel

```bash
# 0. Vérifier extensions libres
curl -sk https://pbx.local/provision/api/v1/extension.php

# 1. Register → code par mail
curl -sk -X POST https://pbx.local/provision/api/v1/register.php \
  -H 'Content-Type: application/json' -d '{"email":"user@example.com"}'

# 2. Verify → attribution auto + QR par mail
curl -sk -X POST https://pbx.local/provision/api/v1/verify.php \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","code":"XXXXXX"}'

# 3. Scan QR dans Asaphone → claim → consume
```

---

*Document flux Asaphone — serveur implémenté ; client Asaphone en cours (phase 4).*
