# WebRTC / WebSocket (navigateur) vers Asterisk

## Ce que fait cette couche

- **HTTP** Asterisk sur **8088** (signaling WS possible en lab, souvent non utilisé en prod).
- **TLS** sur **8089** : **WSS** pour que le navigateur ouvre une signalisation SIP sécurisée vers PJSIP.
- Transport PJSIP **`transport-wss`** lié au port **8089**.

Les **téléphones classiques** (UDP 5060) ne changent pas.

## Prérequis

- Certificats **`/etc/asterisk/keys/default.crt`** et **`default.key`** (FreePBX Certificate Manager, ou chemins adaptés dans `http_custom-webrtc.conf`).
- Pare-feu : ouvrir **8089/tcp** (et optionnellement **8088/tcp**) vers les réseaux autorisés — voir `network/site.env` + `scripts/net-apply-site.sh`.
- **Module `res_srtp.so`** chargé dans Asterisk. Sans lui, avec `media_encryption=dtls` (WebRTC), les logs montrent : *SRTP support module is not loaded or available. Try loading res_srtp.so* puis **488** / *Couldn't negotiate stream*. Sur une **compilation source** sans libsrtp2 au moment du build, le fichier `.so` est absent : installer **`libsrtp2-dev`**, dans `/usr/src/asterisk-*/` relancer **`./configure`**, **`menuselect/menuselect --enable res_srtp menuselect.makeopts`**, **`make res/res_srtp.so`**, copier vers **`/usr/lib/asterisk/modules/`**, puis **`asterisk -rx "module load res_srtp.so"`** (ou redémarrage Asterisk).

## Déploiement sur le PBX

```bash
sudo bash /home/asaph/Documents/serveur/scripts/enable-webrtc-websocket.sh
sudo bash /home/asaph/Documents/serveur/scripts/net-apply-site.sh
sudo bash /home/asaph/Documents/serveur/scripts/align-pjsip-site.sh
```

**Codecs + profil WebRTC par extension** : éditer `network/pjsip-align.env` (listes `WEBRTC_EXTENSIONS` / `CLASSIC_EXTENSIONS`), puis `sudo bash scripts/align-pjsip-site.sh`. Une extension **navigateur** doit être en mode **`--webrtc`** (Opus + DTLS + ICE, etc.) ; une extension **Zoiper / téléphone** reste **classique** (`align-pjsip-endpoint.sh` sans `--webrtc`).

Sous **FreePBX**, le fichier auto-généré `http_additional.conf` impose souvent `enabled=no` et une liaison sur **127.0.0.1** : le script appelle donc aussi **`fwconsole setting`** (`HTTPENABLED`, `HTTPBINDADDRESS`, `HTTPTLSBINDADDRESS`) pour que **8088/8089** écoutent sur **0.0.0.0**. Les certificats TLS du mini-serveur HTTP restent ceux définis dans FreePBX (**Certificate Management** / chemins `integration`), en complément du bloc optionnel dans `http_custom.conf`.

Puis vérifier :

```bash
sudo asterisk -rx "http show status"
sudo asterisk -rx "pjsip show transports"
```

Tu dois voir un transport **wss** sur **0.0.0.0:8089**.

## Architecture média, pont Asterisk et performances

### Ce qui se passe sur un appel mixte (ex. 1002 → 1001)

L’**INVITE** du navigateur porte un SDP **WebRTC** : **SAVPF**, **DTLS-SRTP**, **ICE**, souvent **Opus** + téléphone-event, etc. L’autre extension (ex. **1001** sur **Zoiper**) parle en général **RTP/AVP** « classique » (PCMU/PCMA, sans la même enveloppe).

**Asterisk ne fait pas du WebRTC de bout en bout jusqu’au téléphone UDP.** Il joue le rôle de **B2BUA** : il **termine** la jambe WebRTC côté **1002** (WSS + DTLS-SRTP + ICE gérés avec l’endpoint WebRTC) et **ressort** une jambe **RTP** (souvent PCMU/PCMA) vers **1001**. Si l’endpoint WebRTC ou les codecs ne sont pas cohérents, tu obtiens **`488`** / **`Couldn't negotiate stream … (nothing)`** : la signalisation WSS peut être OK alors que la **montée de la jambe média** vers l’autre profil échoue.

### Rôles attendus côté PBX

| Rôle | Exemple | Transport / média |
|------|---------|-------------------|
| Client navigateur | **1002** | **Endpoint WebRTC / WSS** — pas un trunk UDP. |
| Softphone / téléphone | **1001** | **SIP UDP** + **RTP/AVP** (ex. Zoiper). |

**Appel interne 1002 ↔ 1001** : un seul Asterisk au milieu ; le **pont média** est **toujours sur le PBX**. Il faut des **codecs communs** entre ce qu’accepte le navigateur et ce qu’accepte l’autre poste, **ou** du **transcodage** activé côté Asterisk (souvent **ulaw/alaw** des deux côtés est le plus simple).

### Autres combinaisons (même logique)

- **WSS + WSS** : les **deux** extensions en profil **WebRTC** ; Asterisk pont entre deux jambes WebRTC.
- **UDP + UDP** : deux endpoints **classiques** ; même logique **RTP** qu’habituellement.
- **Trunk opérateur** : le trunk est en général **UDP** ou **TLS** vers l’opérateur ; le client **WebRTC** reste un **endpoint WSS** séparé. Le média ne va **pas** « en direct » du navigateur vers le SIP du FAI : le **pont** (et souvent transcodage / sécurité) reste **sur Asterisk**.

### Performances (codecs)

- **Mieux** : aligner **PCMU et/ou PCMA** (et éventuellement **Opus** si les deux côtés le supportent) pour **éviter le transcodage** CPU sur le PBX.
- **Transcodage** Opus ↔ G.711 : fonctionne si les modules sont présents, mais **coût CPU** et latence un peu plus sensibles sous charge.

### Piège côté application (impression de « déconnexion »)

Un **`REGISTER`** avec **`Contact: *`** et **`Expires: 0`** = **désenregistrement** de toutes les contacts de l’extension. Si l’appli envoie ça au démarrage d’appel, au **hot reload** ou en changeant d’écran, le PBX voit l’endpoint **Unreachable** brièvement — ce n’est **pas** le serveur qui raccroche avant la connexion. Éviter ces REGISTER sauf **logout** explicite.

## Extension « navigateur » (WebRTC)

Un poste **WebRTC** n’a pas la même config qu’un Zoiper UDP. Dans FreePBX (extension dédiée, ex. `1099`) ou en base, viser typiquement :

- **Transport** : `transport-wss` (ou équivalent selon l’UI).
- **ICE** : `ice_support=yes`
- **AVPF** : `use_avpf=yes`
- **RTCP mux** : `rtcp_mux=yes`
- **Media** : `media_encryption=dtls` (souvent requis navigateur), `dtls_auto_generate_cert` ou certificats selon doc Asterisk.

Sans ces réglages sur **l’endpoint** utilisé par le navigateur, le WSS peut être OK mais l’appel audio/vidéo échouera encore.

### Dépannage : `488 Not Acceptable Here` / `Couldn't negotiate stream … (nothing)`

Si les logs Asterisk montrent :

`handle_incoming_sdp: … Couldn't negotiate stream 0:audio … (nothing)` puis **`SIP/2.0 488 Not Acceptable Here`**, la signalisation **WSS fonctionne**, mais le serveur **refuse ou n’arrive pas à négocier le SDP média** pour l’extension navigateur (ex. **1002**).

À corriger **côté PBX** sur **l’extension utilisée par le WebRTC** (pas sur le poste UDP classique) :

1. **Profil WebRTC** : dans FreePBX, extension → onglet **Advanced** (ou équivalent) — activer **WebRTC** / options PJSIP type `webrtc=yes`, **ICE**, **AVPF**, **RTCP mux**, **DTLS** (`media_encryption=dtls`, `dtls_verify=fingerprint` ou selon version).
2. **Codecs** : autoriser au minimum **Opus** + **ulaw (G.711 µ-law)** + **alaw** (souvent **G.722** en plus). Vérifier : `sudo asterisk -rx "module show like codec_opus"` (module chargé) et `sudo asterisk -rx "pjsip show endpoint 1002"` (lignes *Codec*).
3. **Cohérence avec l’autre jambe** : pour appeler **1001** (Zoiper, etc.), celui-ci doit annoncer au moins un codec **aussi proposé par le navigateur** (souvent **PCMU/PCMA** ou **Opus** si le softphone le gère). Sinon la passerelle peut échouer plus tard ; l’erreur sur **1002** pointe d’abord vers l’endpoint **WebRTC** mal réglé.

Le flux **REGISTER** / **OPTIONS** que tu vois ensuite confirme que le transport **WSS** est bon ; le blocage est **SDP / codecs / chiffrement média**, pas le pare-feu.

## Clients SIP over WebSocket (référence unique)

Sur ce site, le nom stable annoncé par mDNS est **`pbx.local`** (voir `network/site.env` → `PBX_MDNS_NAME`).

Toute appli navigateur qui fait du **SIP over WebSocket** (JsSIP, SIP.js, autre) doit au minimum utiliser :

| Paramètre | Valeur |
|-----------|--------|
| **URL WebSocket sécurisée (WSS)** | **`wss://pbx.local:8089/ws`** |
| **Domaine SIP / realm** (souvent) | **`pbx.local`** |
| **URI SIP** (exemple extension 1000) | `sip:1000@pbx.local` |

Le chemin **`/ws`** est celui d’**Asterisk** pour la signalisation PJSIP sur WebSocket (pas un choix arbitraire du dépôt).

**WS sans chiffrement (lab uniquement)** : `ws://pbx.local:8088/ws` — utile pour des tests ; en **HTTPS** sur le site, le navigateur bloquera souvent le WS non chiffré (*mixed content*).

**Certificat TLS** : pour que **WSS** réussisse sans avertissement, le certificat servi sur le port **8089** doit être valide pour le nom utilisé dans l’URL (**`pbx.local`** en SAN, ou certificat auto-signé accepté manuellement / importé). Sinon, préférer un FQDN présent dans le certificat et la même valeur dans `SIP_WEBSOCKET_URL`.

**Résolution `pbx.local`** : macOS / Linux avec mDNS voient souvent le PBX tout seuls ; **Windows** peut nécessiter une entrée dans le fichier *hosts* (le script `net-apply-site.sh` régénère `network/windows-hosts.txt`).

Fichier d’exemple prêt à copier : **`webrtc/client-sip-over-ws.example.env`**.

### Exemples minimaux (pseudo-config)

**JsSIP** (champs typiques) : URI `sip:EXT@pbx.local`, mot de passe d’extension, sockets `wss://pbx.local:8089/ws`.

**SIP.js** (UserAgent) : `transportOptions.server` = `wss://pbx.local:8089/ws`, `uri` / `authorizationUsername` selon l’extension.

Les noms exacts des options varient selon la version de la lib ; l’invariant côté serveur reste **`wss://pbx.local:8089/ws`** + extension WebRTC sur le PBX.

## Fichiers du dépôt

| Fichier | Rôle |
|---------|------|
| `webrtc/asterisk/http_custom-webrtc.conf` | Fragment HTTP+TLS |
| `webrtc/asterisk/pjsip.transports_custom_post-webrtc.conf` | Transport `wss` |
| `scripts/enable-webrtc-websocket.sh` | Fusion dans `/etc/asterisk/*.conf` |
| `webrtc/client-sip-over-ws.example.env` | URL WSS + domaine pour applis web |
