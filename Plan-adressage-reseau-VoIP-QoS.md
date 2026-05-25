# Plan d’adressage réseau — Voix (VLAN 10) et QoS RTP (DSCP EF)

Document opérationnel **Phase 1** : VLAN dédié voix + marquage **DSCP EF** sur le **RTP**.

**Dernière mise à jour du rapport** : 2026-03-27 — **VLAN 10 + IP voix + localnets FreePBX + UFW** appliqués sur le serveur (voir §7) ; QoS RTP DSCP EF déjà en place (§4.2).

### Modalité — production

Tout ce qui est déployé ici vise **la production** : pas de cadre « démo » ou « lab » pour reporter des vérifications. **Si une fonctionnalité est vérifiable, on la contrôle sur le flux réel** (appel, trafic réel, capture sur l’interface concernée) et on enregistre le résultat ; ensuite on enchaîne. Les mentions de contrôle technique (pare-feu, DSCP, `tcpdump`) sont des **validations d’exploitation**, pas des jeux d’essai à part.

---

## 0. Ce que tu es censé comprendre (la phrase du cahier des charges)

La mention *« Plan d’adressage réseau — VLAN 10 dédié voix, QoS DSCP EF pour les paquets RTP »* recouvre **deux choses distinctes** :

| Idée | Ce que c’est | Où ça se configure |
|------|----------------|---------------------|
| **VLAN 10 voix** | Un **segment réseau logique** (802.1Q) : tout le trafic téléphonie (téléphones, RTP/SIP vers le PBX) vit dans le **VLAN ID 10**, séparé du LAN « bureautique ». | **Switch** (ports access/trunk), **VMware/vSwitch** (port group VLAN 10), éventuellement **pare-feu L3** si le routage inter-VLAN est centralisé. **Ce n’est pas** une option qu’on coche dans Asterisk : Asterisk voit des **adresses IP** ; le VLAN est **en dessous** (couche 2 sur le câble / l’hyperviseur). |
| **QoS DSCP EF sur le RTP** | Un **marquage** sur les paquets IP **UDP** du média audio (**RTP**) : le champ **DSCP** vaut **EF (46)** pour que routeurs/switchs compatibles mettent ces paquets en **file prioritaire**. | **Serveur Linux** (iptables/nftables **mangle**), et/ou **switch** (classification ou confiance au marquage), et/ou **routeur**. **Asterisk** n’écrit pas le DSCP tout seul : il faut l’OS ou le réseau. |

En résumé : **oui, c’est une vraie configuration** — mais **répartie** : une partie **sur le LAN** (VLAN), une partie **sur le serveur et le chemin réseau** (QoS). Tout ne se fait pas au même endroit.

---

## 1. Objectifs

| Objectif | Détail |
|----------|--------|
| Isolation | Trafic **SIP + RTP + téléphones** sur un **VLAN 10** distinct du LAN data. |
| Priorité | Paquets **RTP** marqués **DSCP EF** pour **Expedited Forwarding** sur équipements qui appliquent la QoS. |
| Cohérence | Même plan d’adresses et mêmes règles sur **switch L3**, **firewall**, **serveur PBX**. |

**Rappel** : DSCP **EF** = **46** (décimal) ; sous `iptables` la cible `DSCP --set-dscp-class EF` apparaît souvent comme **`DSCP set 0x2e`** (0x2e = 46).

---

## 2. VLAN 10 — voix (couche 2)

### 2.1 Paramètres logiques

| Paramètre | Valeur retenue |
|-----------|----------------|
| ID VLAN | **10** |
| Nom (documentation) | `VOIX` |
| Usage | Téléphones IP, passerelles, **NIC / port group** du serveur FreePBX côté téléphonie |

### 2.2 Statut de **configuration** VLAN 10

| Lieu | Statut | Commentaire |
|------|--------|-------------|
| Switch physique | **À faire** | Créer VLAN 10, ports téléphones en access, **trunk** vers l’hyperviseur avec VLAN 10 autorisé. Sans côté switch, les trames taguées 10 n’atteignent pas la VM. |
| VMware / Proxmox | **À faire** | Port group **VLAN 10** (802.1Q) sur la vNIC qui reçoit le trunk. |
| Ubuntu dans la VM | **Fait** | **NetworkManager** : connexion **`voix-vlan10`**, interface **`ens33.10`**, IP **`10.10.10.10/24`**, `ipv4.never-default yes` (route par défaut inchangée sur le LAN data). Si l’activation échoue, vérifier que **`vlan.parent`** pointe bien vers l’UUID de **`netplan-ens33`** (sinon corriger avec `nmcli connection modify voix-vlan10 vlan.parent $(nmcli -g connection.uuid connection show netplan-ens33)`). |

La VM est **prête côté OS** : dès que le lien physique/hyperviseur envoie le VLAN 10, **`ens33.10`** est **UP** et joignable sur **10.10.10.10**. Tant que le trunk n’est pas en place, l’interface peut rester **sans trafic voix réel** mais la config est déjà chargée.

### 2.3 Switch (rappel opérationnel)

- Ports téléphones : VLAN **10** (access ou voice VLAN selon constructeur).
- Lien vers hyperviseur : **trunk** autorisant VLAN 10 (et VLAN admin si besoin).
- QoS : **trust DSCP** sur les ports vers le PBX et vers le cœur (si tu marques au serveur — c’est le cas après §4).

---

## 3. Plan d’adressage IPv4 — **préfixe voix retenu**

**Décision documentaire** : le sous-réseau **voix (VLAN 10)** est **10.10.10.0/24**. Rien n’oblige à l’abandonner : c’est lisible, standard en doc d’archi, et évite toute collision avec un LAN type **192.168.147.0/24**.

*Alternative possible* (si tu préfères rester visuellement dans la même série que le LAN 192.168.147.x) : **192.168.148.0/24** — même logique de **deuxième /24** distinct, décrite en §3.1. Tant que ce fichier dit **10.10.10.0/24**, c’est celui-ci qui fait foi.

| Élément | Valeur **retenue** | Rôle |
|---------|-------------------|------|
| Réseau VLAN 10 | **10.10.10.0/24** | Sous-réseau **voix uniquement** |
| Passerelle (SVI L3 / firewall) | **10.10.10.1** | Gateway téléphones + sortie routée |
| FreePBX / Asterisk (interface voix) | **10.10.10.10/24** | IP **statique** recommandée |
| Plage DHCP téléphones | **10.10.10.50 – 10.10.10.200** | Réservations / scope |
| Plage **réservée** infra | **10.10.10.2 – 10.10.10.49** | Passerelles, SBC, SNMP, futurs services |
| Broadcast | **10.10.10.255** | Implicite /24 |

**LAN serveur / gestion** (exemple site) : **192.168.147.0/24** — **distinct** du voix **10.10.10.0/24**. Schéma à deux pattes : gestion sur le LAN data, téléphonie sur **10.10.10.x** une fois le VLAN 10 raccordé.

### 3.1 Enjeux : préfixe voix **distinct** vs **réutiliser** le préfixe du LAN serveur

On entend par « préfixe du LAN serveur » le réseau où vit aujourd’hui la VM (ex. `192.168.147.0/24`).

| Question | Réponse technique |
|----------|-------------------|
| Mettre **exactement le même /24** sur le VLAN 10 **et** sur le LAN data ? | **Non viable** comme deux segments **séparés** : un même identifiant de sous-réseau IP ne peut pas être routé correctement sur **deux domaines de broadcast** (deux VLAN) sans les fusionner en pratique en un seul LAN étendu. Tu obtiens conflits de passerelle, ARP et routage incohérents. |
| Mettre **tout le monde** (PC, téléphones, serveur) dans **un seul /24** sans sous-réseau voix ? | **Possible** (réseau **plat**) : tout partage `192.168.147.0/24`. Le VLAN 10 n’apporte alors **pas** de séparation **L3** (adresses) ; au mieux du **tag 802.1Q** côté switch pour des politiques L2/QoS. **Enjeux** : pas de filtrage inter-VLAN net au routeur ; broadcast et découverte **mélangés** ; DHCP unique plus difficile à **spécialiser** (options TFTP, provisioning téléphones) ; surface d’attaque **une seule zone** ; audits / bonnes pratiques télécom préconisent souvent une **zone voix** identifiable. |
| Garder la **même famille** d’adresses privées mais un **autre /24** (ex. LAN `192.168.147.0/24`, voix `192.168.148.0/24`) ? | **Souvent le bon compromis** : cohérence visuelle avec ton adressage existant, **routage** et **ACL** clairs (autoriser SIP/RTP uniquement depuis la zone voix, etc.). Ce n’est **pas** « le préfixe du serveur » au sens strict, mais **deux préfixes distincts** dans le même plan privé. |
| Utiliser un préfixe **totalement différent** (ex. `10.10.10.0/24`) ? | **Classique** : lecture immédiate (« tout ce qui est en 10.10.10.x, c’est la voix »), documentation simple, moins de risque de chevauchement avec d’autres sites VPN ou fusions réseau plus tard. |

**Synthèse** : on n’utilise **pas** « le même préfixe que le LAN serveur » **au sens strict** (même /24 sur deux VLAN ou doublon d’adresses) parce que ce serait **incohérent IP**. On **peut** rester en **réseau plat** avec le préfixe du serveur pour **tout** — mais on **renonce** à la **segmentation** que le cahier des charges vise avec un **VLAN voix dédié** au niveau **adresses**. Un **deuxième /24** (voix) reste l’approche alignée avec **VLAN 10 + routage** ; son choix (`10.x` vs `192.168.x` adjacent) est **politique d’exploitation**, pas une obligation technique unique.

---

## 4. QoS — DSCP EF pour le RTP

### 4.1 Plage RTP Asterisk (FreePBX) — **constatée sur le serveur**

Fichier généré FreePBX : `/etc/asterisk/rtp_additional.conf`

| Paramètre | Valeur |
|-----------|--------|
| `rtpstart` | **10000** |
| `rtpend` | **20000** |

*Ne pas modifier `rtp.conf` à la main ; changements via l’UI FreePBX → **Asterisk SIP Settings** (ports RTP). Si la plage change, il faudra **aligner** les règles §4.2.*

### 4.2 **Configuration effectuée sur le serveur** (Ubuntu, UFW)

| Élément | Détail |
|---------|--------|
| Méthode | Table **`mangle`**, chaîne **`OUTPUT`** dans **`/etc/ufw/before.rules`** (compatible **iptables-nft** utilisé par UFW). |
| Règles | UDP **source ports** 10000–20000 → **DSCP EF** ; UDP **destination ports** 10000–20000 → **DSCP EF** (couvre RTP sortant / réponses sur les mêmes ports). |
| Sauvegarde | **`/etc/ufw/before.rules.bak-phase1-qos`** (copie avant modification). |
| Rechargement | `sudo ufw reload` (déjà exécuté après ajout). |

Vérification rapide :

```bash
sudo iptables -t mangle -L OUTPUT -n -v
```

Tu dois voir deux lignes `DSCP ... multiport sports 10000:20000` et `dports 10000:20000` avec `DSCP set 0x2e`.

### 4.3 Ce qui reste **réseau** (hors serveur)

- [ ] Switch / routeur : **file prioritaire** (LLQ ou équivalent) pour **EF**, ou politique **trust DSCP** sur les bons ports.
- [ ] **Contrôle en production** : pendant un **appel réel**, capture sur l’interface qui porte le RTP (`tcpdump -vv -n -i <iface> udp portrange 10000-20000`) et vérifier le champ **DSCP / tos** ; noter le résultat et clôturer le point (cf. modalité production en tête de document).

### 4.4 SIP (hors cahier strict)

Le cahier cite surtout le **RTP** en EF. La signalisation **SIP** peut rester en best effort ou être marquée **AF31/CS3** plus tard si tu le demandes.

---

## 5. Matrice de flux (résumé)

| Flux | VLAN cible | Protocole | Marquage |
|------|------------|-----------|----------|
| SIP | 10 | TCP/UDP 5060 / TLS 5061 | Best effort ou AF31 (option) |
| RTP | 10 | UDP 10000–20000 | **DSCP EF** (fait côté serveur §4.2) |

---

## 6. Rapport synthétique (pour revue)

| Tâche | État |
|-------|------|
| Compréhension / découpage VLAN vs QoS | Documenté §0 |
| Plan IP VLAN 10 | **Retenu** **10.10.10.0/24** §3 (alternative §3.1 : 192.168.148.0/24) |
| VLAN 10 sur switch / hyperviseur | **À faire** (trunk + tag 10 vers la VM) |
| Interface **`ens33.10` + IP 10.10.10.10** | **Fait** (NetworkManager `voix-vlan10`) §7 |
| **Local networks** PJSIP (147 + 10.10.10) | **Fait** (table `kvstore_Sipsettings`, clé **`localnets`**) §7 |
| Plage RTP | **Déjà** 10000–20000 (FreePBX) |
| Marquage DSCP EF RTP sur le serveur | **Fait** (`/etc/ufw/before.rules` + reload UFW) |
| **UFW** : SIP/RTP depuis **10.10.10.0/24** | **Fait** §7 |
| Queues / trust DSCP sur LAN | **À faire** sur équipements L2/L3 |

---

## 7. Configuration **appliquée** sur le serveur (production)

| Composant | Détail |
|-----------|--------|
| **VLAN / IP** | Connexion NM **`voix-vlan10`** : `ens33.10`, **10.10.10.10/24**, autoconnect, pas de route par défaut sur cette interface. |
| **FreePBX — réseaux locaux** | Entrée **`localnets`** dans **`kvstore_Sipsettings`** (base **`asterisk`**) : **`192.168.147.0/255.255.255.0`** et **`10.10.10.0/255.255.255.0`**. Régénère **`local_net=`** dans **`/etc/asterisk/pjsip.transports.conf`** au **`fwconsole reload`**. Vérification : `sudo asterisk -rx "pjsip show transport 0.0.0.0-udp"`. |
| **UFW** | Autorisation **depuis 10.10.10.0/24** vers : UDP/TCP **5060,5160,5161** ; UDP **10000–20000** (RTP). **Phase 4** : **5061/tcp** limité au LAN gestion **192.168.147.0/24** (plus d’accès mondial « Anywhere ») — voir **`S4-Phase4-Securite-complete.md` §5. |
| **Fichiers Asterisk custom** | **`pjsip.transports_custom.conf`** / **`pjsip.transports_custom_post.conf`** : laissés sans `local_net` en doublon (source de vérité = FreePBX **localnets**). |

**Attention** : si tu modifies les **réseaux locaux** dans l’UI FreePBX (**Réglages SIP Asterisk**), la base peut **réécrire** `localnets` — garder cohérence avec **10.10.10.0/24** et **192.168.147.0/24**.

---

## 8. Prochaines actions

1. **Trunk VLAN 10** côté **switch + VMware** jusqu’à la VM (sinon pas de téléphones sur **10.10.10.x** malgré la config OS).
2. **Passerelle 10.10.10.1** (SVI / firewall) : routes inter-VLAN si les téléphones doivent joindre d’autres zones ; ajuster **NAT / externip** FreePBX si besoin selon ton FAI / IP publique.
3. Indiquer **marque/modèle** du switch pour une **annexe commandes** (VLAN 10 + **trust DSCP**).
4. **Contrôle en production** : appel réel + `tcpdump` sur **`ens33.10`** (cf. §4.3).

---

*Document d’exploitation : mis à jour quand les plages ou l’infra évoluent.*

À faire hors serveur
Trunk VLAN 10 sur le switch + port group VLAN 10 sur VMware vers la VM ; sans ça, pas de flux voix réel sur ens33.10 même si l’interface est configurée.
10.10.10.1 (passerelle) et QoS trust DSCP sur le LAN, comme dans le plan.
Note : si tu changes les réseaux locaux dans l’UI FreePBX, vérifie que 192.168.147.0/24 et 10.10.10.0/24 restent cohérents avec la base.