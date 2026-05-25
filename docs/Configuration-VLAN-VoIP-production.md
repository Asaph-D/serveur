# Configuration VLAN VoIP de production

Ce document décrit une architecture VLAN de production pour la voix sur IP (VoIP) autour du PBX FreePBX/Asterisk. Il s'appuie sur le fichier `network/site.env`, notamment sur le réseau de gestion actuel :

```env
MGMT_CIDR="192.168.137.0/24"
VOICE_CIDR="10.10.10.0/24"
PBX_MDNS_NAME="pbx"
```

Objectifs :

- isoler les téléphones IP et softphones dans un réseau voix dédié ;
- garder l'administration FreePBX dans le LAN de gestion ;
- permettre les appels entre postes UDP, WebSocket/WSS et mixtes UDP <-> WebSocket ;
- permettre l'ajout d'autres secteurs voix sans interférence avec la production existante ;
- préparer les appels de groupe avec une logique simple : tous les postes rejoignent le PBX, le PBX mélange ou relaie les flux.

---

## 1. Principe général

Le PBX doit être le point central de communication. Les postes ne doivent pas dépendre du protocole utilisé par l'autre poste :

| Cas | Signalisation | Media | Comportement attendu |
|-----|---------------|-------|----------------------|
| Téléphone UDP -> téléphone UDP | SIP UDP | RTP UDP | Appel classique via Asterisk |
| WebRTC/WSS -> WebRTC/WSS | SIP sur WSS | DTLS-SRTP | Appel navigateur/softphone WebRTC |
| WebRTC/WSS -> téléphone UDP | WSS d'un côté, UDP de l'autre | SRTP côté WebRTC, RTP côté UDP | Asterisk fait la passerelle |
| Appel de groupe | Chaque poste appelle une conférence | Mix media côté Asterisk | Le protocole des participants n'a pas d'importance |

Le point important : le PBX doit rester dans le chemin media. Pour cela, les endpoints doivent avoir `direct_media=no`. Ainsi, Asterisk peut relier proprement UDP, WSS, RTP et SRTP.

---

## 2. Plan d'adressage recommandé

### Réseau de gestion existant

Le LAN de gestion reste celui défini dans `network/site.env` :

```env
MGMT_CIDR="192.168.137.0/24"
```

Usage :

- interface FreePBX ;
- SSH serveur ;
- Grafana/InfluxDB ;
- administration des équipements réseau.

Exemple :

| Élément | Adresse exemple |
|---------|-----------------|
| Routeur / passerelle gestion | `192.168.137.1` |
| PBX côté gestion | `192.168.137.61` |
| Admin PC | `192.168.137.0/24` |

L'adresse exacte du PBX doit être celle réellement utilisée sur ton serveur.

### VLAN voix principal

Le VLAN voix principal est déjà prévu dans `site.env` :

```env
VOICE_CIDR="10.10.10.0/24"
```

Proposition de production :

| Élément | Valeur |
|---------|--------|
| VLAN voix | `10` |
| Sous-réseau | `10.10.10.0/24` |
| Passerelle | `10.10.10.1` |
| DHCP téléphones | `10.10.10.50` -> `10.10.10.250` |
| DNS | routeur, DNS interne ou PBX selon ton choix |
| Serveur SIP | `pbx.local`, ou mieux une entrée DNS interne stable |

### Secteurs voix supplémentaires

Pour un autre étage, bâtiment ou secteur, il ne faut pas étendre aveuglément le même domaine L2 si on veut éviter les interférences broadcast. Le plus propre est de créer d'autres VLAN/subnets voix routés vers le PBX.

Exemple :

| Secteur | VLAN | CIDR | Passerelle |
|---------|------|------|------------|
| Voix principal | `10` | `10.10.10.0/24` | `10.10.10.1` |
| Voix secteur A | `11` | `10.10.11.0/24` | `10.10.11.1` |
| Voix secteur B | `12` | `10.10.12.0/24` | `10.10.12.1` |

Ces secteurs doivent être déclarés dans `network/site.env` :

```env
VOICE_CIDR="10.10.10.0/24"
EXTRA_VOICE_CIDRS="10.10.11.0/24 10.10.12.0/24"
```

Si aucun autre secteur n'est encore utilisé, laisser :

```env
EXTRA_VOICE_CIDRS=""
```

---

## 3. Architecture réseau

Architecture simple et robuste :

```text
                   Internet / WAN
                         |
                    Routeur/Firewall
                         |
             +-----------+------------+
             |                        |
      VLAN gestion              VLAN voix routés
   192.168.137.0/24      10.10.10.0/24, 10.10.11.0/24
             |                        |
       PBX FreePBX              Téléphones IP
       UI / SSH / SIP           Softphones UDP/WSS
```

Le PBX peut rester dans le réseau de gestion, à condition que le routeur/firewall autorise les VLAN voix à joindre uniquement les ports nécessaires du PBX.

Option plus stricte : ajouter une interface VLAN dédiée au PBX, par exemple `ens33.10` avec une IP `10.10.10.2/24`. Dans ce cas, les téléphones utilisent l'IP voix du PBX, tandis que l'administration reste sur `192.168.137.0/24`.

---

## 4. Règles firewall entre VLAN

Les postes voix doivent pouvoir joindre le PBX sur les ports SIP, WebSocket et RTP, mais ne doivent pas accéder librement au LAN de gestion.

### Autoriser depuis les VLAN voix vers le PBX

| Service | Protocole | Port |
|---------|-----------|------|
| SIP UDP | UDP | `5060` |
| SIP TCP | TCP | `5060` |
| SIP TLS | TCP | `5061` |
| PJSIP secondaire UDP | UDP | `5160` |
| PJSIP secondaire TLS | TCP | `5161` |
| RTP audio | UDP | `10000:20000` |
| WebRTC HTTP | TCP | `8088` |
| WebRTC WSS | TCP | `8089` |

### Bloquer le reste

Recommandation ACL :

```text
ALLOW  VLAN_VOICE_*  -> PBX_IP    ports SIP/RTP/WSS nécessaires
ALLOW  VLAN_VOICE_*  -> DNS       UDP/TCP 53
ALLOW  VLAN_VOICE_*  -> NTP       UDP 123
DENY   VLAN_VOICE_*  -> MGMT_CIDR tout le reste
ALLOW  MGMT_CIDR     -> PBX_IP    UI/SSH/monitoring
```

Le script `scripts/net-apply-site.sh` applique déjà les règles UFW côté serveur pour `VOICE_CIDR`, `EXTRA_VOICE_CIDRS`, `MGMT_CIDR` et `EXTRA_LAN_CIDRS`.

Commande d'application :

```bash
sudo bash /home/asaph/Documents/serveur/scripts/net-apply-site.sh
```

---

## 5. Configuration switch

### Port routeur/firewall

Le port vers le routeur doit être en trunk/tagged pour transporter les VLAN :

```text
Port vers routeur :
  VLAN gestion : tagged ou native selon ton design
  VLAN 10 voix : tagged
  VLAN 11 voix secteur A : tagged si utilisé
  VLAN 12 voix secteur B : tagged si utilisé
```

### Ports téléphones IP

Pour un téléphone seul :

```text
Port téléphone :
  VLAN voix : untagged/access VLAN 10
  PVID : 10
```

Pour un téléphone avec un PC branché derrière :

```text
Port téléphone + PC :
  VLAN data/gestion : untagged/native
  VLAN voix : tagged VLAN 10
  LLDP-MED ou Voice VLAN : activé si le switch le supporte
```

Le téléphone reçoit le VLAN voix par LLDP-MED ou par configuration manuelle. Le PC reste dans le réseau data/gestion.

### Ports entre switches

Les uplinks entre switches doivent être en trunk/tagged pour transporter les VLAN nécessaires :

```text
Uplink switch <-> switch :
  VLAN gestion : tagged/native selon design
  VLAN voix principal : tagged
  VLAN voix secteurs : tagged uniquement si le secteur en a besoin
```

Ne transporter que les VLAN nécessaires limite les interférences et les erreurs de broadcast.

---

## 6. DHCP et résolution du PBX

Chaque VLAN voix doit avoir un DHCP propre.

Exemple pour `10.10.10.0/24` :

```text
Range DHCP : 10.10.10.50 - 10.10.10.250
Gateway    : 10.10.10.1
DNS        : DNS interne ou routeur
NTP        : routeur, PBX ou serveur NTP local
```

Pour les téléphones physiques, ajouter si nécessaire :

```text
Option 66  : adresse de provisioning, si utilisée
Option 150 : adresse TFTP, surtout pour certains téléphones Cisco
```

Attention à `pbx.local` : mDNS ne traverse pas toujours les VLAN. En production multi-VLAN, le plus fiable est une entrée DNS interne, par exemple :

```text
pbx.local -> IP du PBX
```

ou mieux :

```text
pbx.voip.lan -> IP du PBX
```

Tous les postes doivent utiliser le même nom serveur SIP, peu importe leur VLAN.

---

## 7. Configuration PBX/Asterisk

### Localnets

Les réseaux locaux connus d'Asterisk doivent inclure :

- `MGMT_CIDR` ;
- `VOICE_CIDR` ;
- tous les réseaux dans `EXTRA_VOICE_CIDRS` ;
- les LAN supplémentaires dans `EXTRA_LAN_CIDRS`.

Le script `net-apply-site.sh` met à jour ces localnets automatiquement depuis `site.env`.

### Endpoints UDP classiques

Pour les téléphones UDP :

```text
Transport : UDP
NAT       : rewrite_contact=yes, force_rport=yes, rtp_symmetric=yes
Media     : direct_media=no
Codecs    : g722, ulaw, alaw
```

### Endpoints WebRTC / WebSocket

Pour les clients navigateur ou WSS :

```text
Transport : WSS
WebRTC    : yes
Media     : DTLS-SRTP
ICE       : yes
RTCP mux  : yes
Codecs    : g722, ulaw, alaw si OPUS n'est pas géré
```

Le fichier `network/pjsip-align.env` distingue déjà les postes WebRTC et classiques :

```env
WEBRTC_EXTENSIONS="1003 1004 1005 1006 1007 1008 1009 1010"
CLASSIC_EXTENSIONS="1001 1002"
```

Après modification :

```bash
sudo bash /home/asaph/Documents/serveur/scripts/align-pjsip-site.sh
sudo fwconsole reload
```

---

## 8. Appels de groupe

Pour les appels de groupe, éviter une logique où les clients essaient de se joindre directement entre eux. Le plus stable est :

```text
Chaque poste -> PBX -> ConfBridge / conférence Asterisk
```

Avantages :

- un poste UDP et un poste WebRTC peuvent rejoindre le même appel ;
- le PBX gère le mix audio ;
- les VLAN restent isolés ;
- les participants n'ont pas besoin de connaître le protocole des autres.

Recommandation :

- créer une ou plusieurs salles de conférence côté FreePBX/Asterisk ;
- donner des numéros courts, par exemple `8001`, `8002` ;
- autoriser les extensions internes à appeler ces salles ;
- garder `direct_media=no` pour que le PBX reste dans le chemin audio.

---

## 9. Qualité de service

Pour éviter les coupures et la latence :

| Trafic | Marquage recommandé |
|--------|---------------------|
| RTP audio | DSCP EF `46` |
| SIP signalisation | DSCP CS3 / AF31 |
| Gestion | priorité normale |

Sur les switches :

- activer QoS ;
- faire confiance au DSCP/CoS des téléphones si les postes sont maîtrisés ;
- prioriser RTP sur les uplinks ;
- éviter que le VLAN voix transporte du trafic PC inutile.

Sur Asterisk, les valeurs vues dans les endpoints indiquent déjà souvent :

```text
tos_audio = 184
cos_audio = 5
```

C'est cohérent avec une priorité voix.

---

## 10. Procédure de mise en production

1. Définir les VLAN sur le routeur/firewall :

```text
VLAN 10 -> 10.10.10.0/24
VLAN 11 -> 10.10.11.0/24 si secteur A
VLAN 12 -> 10.10.12.0/24 si secteur B
```

2. Configurer DHCP pour chaque VLAN voix.

3. Configurer les trunks entre routeur et switches.

4. Mettre les ports téléphones dans le bon VLAN voix.

5. Modifier `network/site.env` :

```env
MGMT_CIDR="192.168.137.0/24"
VOICE_CIDR="10.10.10.0/24"
EXTRA_VOICE_CIDRS="10.10.11.0/24 10.10.12.0/24"
EXTRA_LAN_CIDRS="192.168.137.0/24"
```

6. Appliquer côté PBX :

```bash
sudo bash /home/asaph/Documents/serveur/scripts/net-apply-site.sh
sudo bash /home/asaph/Documents/serveur/scripts/align-pjsip-site.sh
sudo fwconsole reload
```

7. Tester l'enregistrement des postes :

```bash
sudo asterisk -rx "pjsip show contacts"
sudo asterisk -rx "pjsip show endpoints"
```

8. Tester les appels :

```text
1001 UDP -> 1002 UDP
1003 WSS -> 1004 WSS
1003 WSS -> 1001 UDP
1001 UDP -> conférence
1003 WSS -> conférence
```

9. Tester le media :

```bash
sudo asterisk -rvvv
rtp set debug on
pjsip set logger on
```

10. Après test, désactiver les logs verbeux :

```text
rtp set debug off
pjsip set logger off
```

---

## 11. Checklist de validation

- Les téléphones du VLAN voix reçoivent une IP correcte.
- Les téléphones résolvent le nom du PBX.
- `pjsip show contacts` affiche les postes en `Reachable`.
- Les appels UDP -> UDP fonctionnent.
- Les appels WSS -> WSS fonctionnent.
- Les appels WSS -> UDP fonctionnent.
- Les appels de groupe passent par le PBX.
- Le VLAN voix ne peut pas accéder librement au LAN de gestion.
- Les ports RTP `10000:20000/udp` passent entre VLAN voix et PBX.
- SIP ALG est désactivé sur le routeur/firewall.
- QoS est activé sur les switches et uplinks.

---

## 12. Diagnostic rapide

### Poste enregistré mais pas d'audio

Vérifier :

```bash
sudo asterisk -rvvv
rtp set debug on
```

Causes probables :

- RTP bloqué par firewall ;
- mauvaise route entre VLAN ;
- mauvais localnet Asterisk ;
- direct media activé ;
- codec non commun.

### WebRTC enregistré mais appel refusé

Vérifier :

```bash
sudo asterisk -rx "pjsip show endpoint 1003"
```

Points importants :

```text
webrtc=yes
media_encryption=dtls
ice_support=yes
use_avpf=yes
rtcp_mux=yes
```

### UDP BYE retransmis ou réponse SIP malformée

Causes probables :

- SIP ALG actif ;
- mauvais port/contact NAT ;
- client SIP qui répond mal ;
- route asymétrique entre VLAN.

Désactiver SIP ALG et forcer les endpoints à utiliser :

```text
rewrite_contact=yes
force_rport=yes
rtp_symmetric=yes
direct_media=no
```

---

## 13. Résultat attendu

Une fois cette configuration appliquée :

- les postes du LAN de gestion, du VLAN voix principal et des secteurs voix supplémentaires peuvent joindre le PBX ;
- les appels entre UDP, WSS et mix UDP/WSS passent par Asterisk ;
- les appels de groupe sont possibles via conférence serveur ;
- les secteurs voix restent isolés les uns des autres sauf vers les services PBX autorisés ;
- le trafic voix peut être priorisé sans perturber le réseau de gestion.
