# Phase 4 — Sécurisation complète

Aligné sur le cahier : **TLS signalisation**, **SRTP médias**, **Fail2Ban 0.11+** (jail type `asterisk` / bannissement IP), **pare-feu** (5060/5061, RTP), **politique mots de passe SIP** et **MariaDB**.

---

## 1. Identifiants MariaDB (FreePBX)

Ils sont définis dans **`/etc/freepbx.conf`** :

- `AMPDBUSER` — compte applicatif (souvent `asteriskuser`)
- `AMPDBPASS` — mot de passe
- `AMPDBNAME` — base (souvent `asterisk`)
- `AMPDBHOST` / `AMPDBPORT`

**Ne pas coller ces valeurs dans un chat ou un dépôt Git.** Consultation locale :

```bash
sudo grep -E '^AMPDB(USER|NAME|HOST|PORT|ENGINE)=' /etc/freepbx.conf
sudo sh -c 'grep ^AMPDBPASS= /etc/freepbx.conf | sed "s/=.*/=<masqué>/"'
```

Pour voir le mot de passe en local uniquement : `sudo grep ^AMPDBPASS= /etc/freepbx.conf`

**Rotation recommandée** (mot de passe fort, ≥ 16 caractères) :

1. MySQL : `ALTER USER 'asteriskuser'@'localhost' IDENTIFIED BY '...';` puis `FLUSH PRIVILEGES;`
2. Mettre à jour **`AMPDBPASS`** dans `/etc/freepbx.conf` (même valeur).
3. `sudo fwconsole reload` ; vérifier l’UI FreePBX.

Compte **root** MariaDB : gestion habituelle (`sudo mysql` ou mot de passe root défini à l’installation) — distinct de `AMPDB*`.

---

## 2. TLS (signalisation, port 5061)

- Transport **PJSIP TLS** sur **5061** (Phase 2) + **certificat serveur** obligatoire pour que les clients TLS négocient correctement.
- **Source de vérité FreePBX** : table **`kvstore_Sipsettings`**, clé **`pjsipcertid`** → identifiant **`cid`** dans **`certman_certs`** (ex. certificat **default** = `cid` **1**). Si `pjsipcertid` vaut **0**, Asterisk peut exposer un transport TLS **sans** `cert_file` / `priv_key_file`.
- **UI** : *Admin → Certificate Management* (certificat par défaut ou Let’s Encrypt) puis *Réglages → Asterisk SIP Settings* — section TLS / certificat PJSIP.
- **Script** (équivalent automatique du choix « default ») :

```bash
sudo php /home/asaph/Documents/serveur/scripts/phase4-assign-pjsip-tls-cert.php
```

- **Contrôle** : `sudo asterisk -rx "pjsip show transport 0.0.0.0-tls"` → `cert_file` et `priv_key_file` doivent pointer vers les fichiers sous `/etc/asterisk/keys/`.
- **Fichier custom** : ne pas dupliquer `cert_file` dans `pjsip.transports_custom_post.conf` si vous passez par Certificate Manager (voir `phase4/asterisk/pjsip.transports_custom_post.conf.snippet`).
- **Pare-feu** : voir §5 — **5061/tcp** limité aux LAN autorisés (plus d’ouverture « Anywhere » en durcissement Phase 4).

---

## 3. SRTP (médias chiffrés — SDES)

- **Cahier** : chiffrement RTP type **SDES** (`media_encryption=sdes` sur les endpoints PJSIP).
- **UI** : *Applications → Extensions → … → onglet PJSIP avancé* — chiffrement média **SDES**.
- **Script** (extensions **1001–1010**) :

```bash
sudo php /home/asaph/Documents/serveur/scripts/phase4-enable-srtp-extensions.php
```

- **Contrôle** : `grep media_encryption= /etc/asterisk/pjsip.endpoint.conf | head` → attendu **`sdes`** pour les postes concernés.
- **Terminaux** : activer **SRTP** / **SAVP** côté téléphone ou softphone ; sinon appels en échec ou sans chiffrement selon option *optimistic*.

---

## 4. Fail2Ban — jail Asterisk (« asterisk-iptables »)

Le paquet **fail2ban** utilise ici le backend **nftables** (Ubuntu récent). Le principe cahier — **ban automatique /32** après échecs — est le même qu’avec iptables classique.

Fichier fourni : **`phase4/fail2ban/jail.d/asterisk-freepbx.local`**

- **logpath** : `/var/log/asterisk/full` (standard FreePBX ; pas `messages` seul).
- **backend** : `auto` (obligatoire : le défaut `systemd` du fichier Debian ne convient pas aux journaux fichier).
- **ports** : 5060, 5061, 5160, 5161 (TCP+UDP selon action du jail).

Installation :

```bash
sudo bash /home/asaph/Documents/serveur/scripts/phase4-apply-fail2ban.sh
sudo fail2ban-client status asterisk
```

**Tester le filtre**

Le fichier `/var/log/asterisk/full` peut être **très volumineux** : `fail2ban-regex` sur tout le fichier est lent et semble « bloquer » sans afficher tout de suite le résumé.

1. **Extrait rapide** (recommandé) :

```bash
bash /home/asaph/Documents/serveur/scripts/phase4-test-fail2ban-filter.sh 2000
```

Ou manuellement :

```bash
sudo tail -n 2000 /var/log/asterisk/full > /tmp/asterisk-test.log
sudo fail2ban-regex /tmp/asterisk-test.log /etc/fail2ban/filter.d/asterisk.conf
```

2. **Lire le résultat** : lignes du type `Failregex: X total` / `Ignoreregex: X total`.

   - **`0 total`** sur un extrait **après** des vraies tentatives (mauvais REGISTER, scanner, etc.) → affiner le filtre ou vérifier que `full` contient bien les messages (niveau de log / `security` events).
   - **`> 0`** → le filtre **matche** ; la jail pourra bannir si le seuil `maxretry` est atteint.

3. **Verbose** : `sudo fail2ban-regex /tmp/asterisk-test.log /etc/fail2ban/filter.d/asterisk.conf -v` pour voir **quelles lignes** ont matché.

4. **Test sur le fichier entier** (long) :

```bash
sudo fail2ban-regex /var/log/asterisk/full /etc/fail2ban/filter.d/asterisk.conf
```

**UFW + Fail2Ban** : les deux peuvent coexister ; en cas de ban invisible, vérifier l’ordre des chaînes nftables/iptables et la politique UFW (`ufw status verbose`).

---

## 5. Pare-feu (UFW / nftables)

Objectif cahier : n’autoriser que l’utile, **bloquer le reste**.

| Flux | Ports | Protocole |
|------|-------|-----------|
| SIP | 5060, 5160 | UDP/TCP (selon déploiement) |
| SIP TLS | 5061, 5161 | TCP |
| RTP | 10000–20000 | UDP |

**Durcissement Phase 4 (exemple appliqué)** :

- **SIP + RTP** depuis **`10.10.10.0/24`** (VLAN voix) : UDP/TCP **5060, 5160, 5161** + UDP **10000–20000** (inchangé par rapport à la Phase 1).
- **5061/tcp** : ne plus ouvrir en **Anywhere** ; autoriser explicitement le **LAN de gestion** **`192.168.147.0/24`** (softphones / admin sur ce segment). Le VLAN voix a déjà **5061** via la règle TCP groupée.
- Trunk / opérateur / utilisateurs **hors** ces réseaux : ajouter des règles **UFW** ciblées (`allow from IP_FAI to any port 5060`) plutôt qu’un accès mondial.

Politique par défaut : **`default deny incoming`** (déjà le cas avec UFW actif). Compléter avec `sudo ufw status numbered` après chaque changement.

---

## 6. Politique mots de passe SIP (≥ 16 car., rotation 90 j.)

- **Nouvelles extensions** : générer des secrets **≥ 16** caractères (aléatoires).
- **Rotation** : planifier tous les 90 jours (calendrier + procédure `fwconsole` / UI).
- **Stockage « hash » en MariaDB** : FreePBX/Asterisk stockent en pratique des **secrets réversibles** pour SIP dans la base (nécessité d’authentifier les flux). Le cahier « hash » se traduit souvent par **stockage centralisé en base + accès restreint + rotation** ; un vrai stockage uniquement haché impose des mécanismes avancés hors GUI standard. Ne pas committer ni diffuser `/etc/freepbx.conf` ni exports SQL.

---

## 7. Fichiers Phase 4 (dépôt)

| Élément | Chemin |
|---------|--------|
| Jail Asterisk | `phase4/fail2ban/jail.d/asterisk-freepbx.local` |
| Snippet TLS (commentaires) | `phase4/asterisk/pjsip.transports_custom_post.conf.snippet` |
| Fail2Ban | `scripts/phase4-apply-fail2ban.sh` |
| Test filtre Fail2Ban | `scripts/phase4-test-fail2ban-filter.sh` |
| Certificat PJSIP TLS | `scripts/phase4-assign-pjsip-tls-cert.php` |
| SRTP SDES extensions 1001–1010 | `scripts/phase4-enable-srtp-extensions.php` |
| Tout enchaîner (Fail2Ban + TLS + SRTP) | `scripts/phase4-apply-all.sh` |

---

*Document d’exploitation Phase 4 — ajuster les sources UFW (trunks, VPN, IPv6) selon votre topologie réelle.*
