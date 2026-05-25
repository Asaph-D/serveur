# Discussion : créer notre propre client SIP (type Zoiper / Linphone)

Ce document pose les enjeux, les options réalistes et les compromis quand on veut **plus de fonctionnalités** (vidéo, appels de groupe, etc.) sans dépendre des versions payantes de Zoiper, Linphone Pro, etc.

---

## 1. Pourquoi ces logiciels sont « payants » pour les grosses fonctionnalités

- **Vidéo** : codecs (H.264, VP8/VP9), négociation SDP, rendu caméra/écran, adaptation réseau — beaucoup de R&D et de tests.
- **Appels de groupe / conférence côté client** : souvent en réalité une **conférence côté serveur** (Asterisk ConfBridge, MCU, ou service cloud) ; le client ne fait qu’envoyer un flux et recevoir un mix — mais l’UI (liste participants, mute, layout) reste du travail.
- **Support, marque blanche, déploiement MDM** : ce que facturent beaucoup d’éditeurs « Pro ».
- **Conformité** (TLS, SRTP, push notifications sur mobile) : coût de maintenance.

Donc payer n’est pas « arbitraire » : c’est souvent le prix du **pack complet prêt prod**.

---

## 2. « Faire notre propre Zoiper » : trois niveaux de réalisme

### Niveau A — Client léger maison (réaliste en équipe réduite)

- **Audio SIP** uniquement (ce que vous avez déjà bien calibré : codecs, NAT, SRTP selon serveur).
- Stack : **PJSIP** (C, très utilisé avec Asterisk), ou **BareSIP**, ou **Linphone SDK** en mode intégration.
- Cibles : **desktop** (Qt / Electron + module natif) ou **web** (WebRTC + gateway SIP, plus complexe).

**Avantages** : contrôle total, pas de licence « Pro » tierce pour *votre* binaire.  
**Limites** : la vidéo et la conférence « riche » demandent encore beaucoup de temps.

### Niveau B — Partir d’un logiciel open source existant (fork)

- **Linphone** : code ouvert ; possibilité de **fork** et d’ajouter des features, en respectant la **licence** (GPL pour une grande partie — implications si vous distribuez un binaire fermé).
- **Jami** (GNU), autres clients communautaires : même logique licence + effort de fork.

**Avantages** : vidéo et SIP déjà présents dans Linphone.  
**Inconvénients** : maintenir un fork = suivre les mises à jour sécurité, Play Store / App Store, builds iOS/Android.

### Niveau C — « Tout refaire » (peu réaliste sans grosse équipe)

Réimplémenter SIP + RTP + SRTP + codecs + UI + mobile + push ≈ **années-homme**.

---

## 3. Côté serveur (Asterisk / FreePBX) : ce qui est déjà là

- **Audio** : extensions PJSIP, dialplan, queues, ConfBridge — déjà en place chez vous.
- **Vidéo** : Asterisk *peut* faire de la vidéo SIP, mais il faut **codecs vidéo** côté serveur et clients alignés (H.264 souvent), et souvent plus de charge CPU.
- **Groupe / conférence** : plutôt **ConfBridge** ou **app_confbridge** côté Asterisk que « multiparty pur P2P » dans le téléphone — le client appelle une **extension de conférence** ; pas besoin que Zoiper vende la « fonction magique » si le PBX fait le mix.

**Idée** : pour limiter le besoin d’un client Pro, on peut **porter la logique métier sur le PBX** (numéros courts, IVR, conférence avec PIN) et garder un client **simple** qui ne fait qu’audio/vidéo de base.

---

## 4. Alternatives « sans tout coder »

| Approche | Idée |
|----------|------|
| **Linphone community** | Gratuit ; vidéo selon plateforme ; moins de « polish » Pro. |
| **WebRTC + portail web** | Navigateur + Asterisk (chan_webrtc / PJSIP WebSocket) : une seule app web maison, pas les stores. |
| **Softphone open source + branding** | Fork léger (logo, serveur par défaut) si licence compatible. |
| **Négocier volume / éducation** | Certains éditeurs ont des tarifs association / volume. |

---

## 5. Si on décide « client maison » : périmètre minimal viable (MVP)

1. **Audio** : enregistrement, appel, DTMF, message SIP (déjà côté serveur chez vous).
2. **Serveur** : champ config (IP, TLS optionnel plus tard).
3. **Plateforme** : une seule en premier (ex. Android **ou** desktop Linux).
4. **Vidéo** : phase 2, un codec (ex. H.264) + tests sur le LAN.
5. **Groupe** : phase 2 bis = **raccourci vers ConfBridge** (composer 8001 + PIN) plutôt que multiparty UI dans l’app.

---

## 6. Risques et points de vigilance

- **Licences** : GPL (Linphone) vs usage interne vs redistribution.
- **Sécurité** : mises à jour TLS, pas de mots de passe en clair dans l’app.
- **Stores** : Apple/Google ont des exigences (privacy, background audio).
- **Coût réel** : un client « maison » a un **coût de maintenance** ; comparer au prix annuel des licences Pro sur *n* postes.

---

## 7. Pistes de décision (à trancher ensemble)

- Objectif prioritaire : **réduire la facture** ou **contrôle total / données** ou **marque blanche** ?
- Cible : **interne uniquement** (APK side-load) ou **public sur les stores** ?
- Vidéo **indispensable** dès V1 ou acceptable en V2 ?
- Préférence technique : **PJSIP natif**, **Linphone SDK**, ou **WebRTC** ?

---

## 8. Références utiles (à creuser)

- [PJSIP](https://www.pjsip.org/) — stack SIP/RTP largement utilisée avec Asterisk.
- [Linphone / Liblinphone SDK](https://www.linphone.org/en/liblinphone/) — SDK sous licence à lire attentivement.
- Documentation Asterisk : **PJSIP**, **ConfBridge**, **WebRTC** (selon version).
- Dans ce dépôt : **`webrtc/README.md`** — activation WSS / transport `transport-wss` et pare-feu.

---

*Document de discussion — à enrichir selon vos choix de périmètre (MVP, plateformes, licence).*
