# Phase 2 — Utilisateurs, extensions PJSIP, groupes, softphones, messagerie

Document d’exploitation **production** : premier lot réalisé sur le serveur FreePBX ; **Zoiper 5** et **Linphone** restent de ton côté (comme convenu).

---

## 1. Périmètre cahier des charges vs FreePBX

| Sujet cahier | Réalisation |
|--------------|-------------|
| **PJSIP** (remplacement chan_sip) | Oui — extensions **1001–1010** en **chan_pjsip**. |
| **Extensions 1001–1010** | Créées via script PHP FreePBX (`scripts/phase2-create-extensions.php`). |
| **Groupes d’appels / ring groups** | **Call group + pickup group** nommés **`phase2`** sur chaque poste (1001–1010). **Sonnerie simultanée** : extension **8000** (dialplan custom, voir §4). Module **ringgroups** non installé (téléchargement Sangoma en **timeout SSL** — réessayer plus tard : `sudo fwconsole ma downloadinstall ringgroups`). |
| **Softphones** | **À ta charge** : Zoiper 5 / Linphone — paramètres §5. |
| **5061 TLS + G.722** | **TLS** : transport **`0.0.0.0-tls`** sur **5061** activé (binds SIP) ; **UFW** autorise **5061/tcp**. **Certificat serveur** : assigner le cert **default** dans l’UI si les clients TLS échouent (§5.1). **G.722** : déjà dans la chaîne de codecs FreePBX (`allow=ulaw,alaw,gsm,g726,g722` sur les endpoints). |
| **Dial plan [internal] / [external]** | Sous FreePBX, l’interne = **`from-internal`** ; l’externe passe par **`from-trunk`**, **`from-pstn`**, etc. Pas de fichiers `extensions.conf` manuels pour le cœur : tout est généré ; le custom = **`extensions_custom.conf`** (§4). |
| **Numérotation nationale** | À définir dans **Connectivité → Routes sortantes** quand les **trunks** existeront ; exemples FR dans §6. |
| **Messagerie vocale + email WAV** | Boîtes créées pour **1001–1010** ; **pièce jointe** activée (`attach=yes`). **Adresse e-mail** par poste à renseigner dans l’UI + **SMTP** système / FreePBX (§7). |

---

## 2. Fichiers et scripts ajoutés

| Élément | Emplacement |
|---------|-------------|
| Création extensions | `scripts/phase2-create-extensions.php` |
| Activation messagerie | `scripts/phase2-enable-voicemail.php` |
| Dialplan ring group | `/etc/asterisk/extensions_custom.conf` |
| Secrets SIP générés | **`/root/phase2-pjsip-secrets.txt`** (chmod **600**, **ne pas diffuser**) |

**Ré-exécution** : ne relancer `phase2-create-extensions.php` qu’après suppression des extensions en conflit — sinon erreur « device id already in use ».

---

## 3. Extensions PJSIP 1001–1010

- **Contexte** : `from-internal`  
- **Max contacts** : **3** par extension (plusieurs appareils possibles).  
- **Secrets** : un secret **aléatoire** par poste dans `/root/phase2-pjsip-secrets.txt` (format `extension<TAB>secret`).  
- **Messagerie** : activée (**`default`** dans `users`) ; **PIN** = **4 derniers chiffres** du numéro (ex. 1001 → **1001**). À personnaliser dans **Applications → Messagerie vocale** si besoin.

Vérifications :

```bash
mysql -u asteriskuser -p asterisk -e "SELECT extension,name,voicemail FROM users WHERE extension BETWEEN '1001' AND '1010'"
sudo asterisk -rx "pjsip show endpoints" | head -40
```

---

## 4. Groupes d’appels et ring group « maison »

### 4.1 Call group / Pickup group

- **`namedcallgroup` / `namedpickupgroup`** = **`phase2`** pour **1001–1010** (dépôt `sip`, régénéré par FreePBX).  
- **Interception** : selon téléphone / codes FreePBX (feature codes) une fois le module **featurecodeadmin** installé si besoin.

### 4.2 Sonnerie de groupe (numéro **8000**)

Fichier **`/etc/asterisk/extensions_custom.conf`**, contexte **`[from-internal-custom]`** :

- Composer **8000** → `Dial` simultané **PJSIP/1001** … **PJSIP/1010**, temporisation **45 s**.

Après toute modification : `sudo fwconsole reload`.

---

## 5. Softphones (Zoiper 5 / Linphone) — **ta configuration**

Paramètres types alignés Phase 2 :

| Paramètre | Valeur |
|-----------|--------|
| **Domaine / serveur** | IP ou FQDN du PBX (**ex.** `10.10.10.10` en VLAN voix, ou `192.168.147.61` selon patte utilisée) |
| **Utilisateur / auth** | Numéro d’extension (**1001** … **1010**) + secret du fichier `/root/phase2-pjsip-secrets.txt` |
| **UDP** | Port **5060**, transport **UDP** (déjà ouvert côté UFW pour zones déjà autorisées) |
| **TLS** | Port **5061**, transport **TLS** / SIP TLS ; accepter le certificat **auto-signé** (ou installer le CA / certificat émis par ta PKI) |
| **Codec** | Forcer ou privilégier **G.722** si le terminal le permet (sinon ulaw/alaw en repli) |

### 5.1 TLS — certificat serveur

Le transport **TLS** est **publié** ; si le client ne se connecte pas :

1. **Admin FreePBX** → **Réglages** → **Asterisk SIP Settings** → onglet **Chan PJSIP** / section **TLS**  
2. Choisir le certificat **default** (Certificate Manager) pour **PJSIP TLS**  
3. **`sudo fwconsole reload`**  

`verify_client` a été passé à **no** en base pour les softphones **sans** certificat client. `verify_server=yes` : le client doit faire confiance au cert serveur (auto-signé).

---

## 6. Plan de numérotation nationaux (à brancher avec trunks)

Une fois **trunk(s)** et **routes sortantes** créés dans FreePBX, patterns usuels **France** (à adapter) :

| Usage | Pattern sortant | Commentaire |
|-------|-----------------|-------------|
| Métropole 10 chiffres | `0XXXXXXXXX` | `0` + 9 chiffres |
| Numéros courts | `1[0-9]XX` etc. | Services, urgence — **conformité réglementaire** à valider |
| International | `00.` ou `+` converti en `00` | Selon normalisation opérateur |

Ces règles se configurent dans **Connectivité → Routes sortantes** (préfixe, masque, trunk) — pas en dur dans `extensions_custom.conf` pour rester maintenable.

---

## 7. Messagerie vocale — email + WAV

- **Module** : `app_voicemail` via FreePBX **voicemail**.  
- **Pièce jointe** : **oui** (`attach=yes`) sur les boîtes créées.  
- **E-mail par poste** : **Applications** → **Extensions** → chaque extension → **Voicemail** : renseigner **l’adresse e-mail**.  
- **Envoi** : configurer **SMTP** (OS **postfix** / relai, ou module **Voicemail Notification** / paramètres messagerie selon ta version). Sans SMTP fonctionnel, pas d’e-mail mais consultation téléphone / UCP si installé.

---

## 8. Pare-feu (rappel)

- **5060** UDP (et TCP si utilisé) — déjà gérés selon ta politique.  
- **5061/tcp** : ouvert pour **TLS Phase 2**.  
- Restreindre **5060/5061** aux seuls **LAN voix + gestion** si possible (éviter exposition Internet sans besoin).

---

## 9. État / suite

| Point | État |
|-------|------|
| Extensions + VM + groupes + 8000 + TLS bind + UFW 5061 | **Fait** |
| Certificat TLS assigné dans l’UI | **À confirmer** si besoin client |
| E-mail + SMTP par utilisateur | **À faire** (opérationnel) |
| Routes nationales + trunks | **Phase suivante** |
| Module **ringgroups** | **Réinstaller** quand le dépôt Sangoma répond (`fwconsole ma downloadinstall ringgroups`) |
| Zoiper / Linphone | **Utilisateur** |

---

*Document : Phase 2 utilisateurs & extensions — aligné avec l’état du serveur au moment de la rédaction.*
