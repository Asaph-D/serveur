# Asaphone — appels de groupe et conférence

Le téléphone **ne mixe pas** l’audio : il compose **un seul numéro interne** (`call_uri`) ou appelle une **API provision**. Asterisk **ConfBridge** crée la salle, invite les extensions et mixe.

## Principe (comme SIP / VPN / VM)

```
Bootstrap / reconnect / session
        ↓
JSON provision (souple : item_maps, endpoints, groups[], conference)
        ↓
Client parse → compose call_uri OU POST conference/invite
        ↓
PBX : ConfBridge + originate PJSIP vers les membres
```

## Ce que le serveur envoie

### À chaque `reconnect` / `session` / `claim`

```json
{
  "session": {
    "jti": "…",
    "conference": {
      "default_call_uri": "6000",
      "default_room": "6000",
      "room_prefix": "asaphone-grp-",
      "dial_mode": "extension",
      "hint": "Appeler call_uri comme extension interne"
    },
    "groups": [
      {
        "id": "uuid-client",
        "group_id": "uuid-client",
        "title": "Équipe",
        "owner": "1003",
        "members": ["1001", "1002", "1003"],
        "room": "asaphone-grp-uuidclient",
        "call_uri": "asaphone-grp-uuidclient",
        "dial": "asaphone-grp-uuidclient"
      }
    ],
    "item_maps": {
      "group_id": "id",
      "group_call_uri": "call_uri",
      "group_dial": "dial"
    },
    "api": {
      "endpoints": {
        "groups_sync": "https://…/provision/api/v1/groups/sync.php",
        "groups_list": "https://…/provision/api/v1/groups/list.php",
        "conference_invite": "https://…/provision/api/v1/conference/invite.php"
      },
      "group_call": "6000"
    }
  }
}
```

### `bootstrap.json` (découverte)

- `endpoints.groups_sync`, `groups_list`, `conference_invite`
- `conference.default_call_uri` = `6000`

## Flux 1 — Groupe → appel (principal)

1. **Créer le groupe** côté app (UI immédiate).
2. **Sync serveur** (dès que `jti` dispo) :

```http
POST /provision/api/v1/groups/sync.php?ext=1003
X-Provision-Jti: <jti>
Content-Type: application/json

{
  "groups": [{
    "id": "a1b2c3d4-e5f6-…",
    "title": "Support",
    "members": ["1001", "1002", "1003"]
  }]
}
```

Réponse : `groups[]` avec **`call_uri`** assigné par le PBX (`asaphone-grp-<slug>`).

3. **Bouton « Appeler le groupe »** :

```dart
// Pseudo-code — remplace resolveGroupCallDialInput local
final uri = group.callUri ?? session.conference.defaultCallUri;
launchVoiceCall(context, uri);  // un seul appel SIP
```

4. **Côté PBX** (automatique) :
   - Dialplan `asaphone-conf-start` → entre en ConfBridge
   - `conf-invite.php auto` → originate vers chaque membre (sauf l’appelant)

**Numéros utilisables**

| `call_uri` | Usage |
|------------|--------|
| `6000` | Salle par défaut (sans groupe en base) |
| `6001`–`6099` | Salles numériques réservées |
| `asaphone-grp-*` | Une salle par groupe sync |

## Flux 2 — Appel en cours → inviter (phase 2)

Pendant un appel 1:1 déjà connecté à une salle (ou après avoir rejoint `6000`) :

```http
POST /provision/api/v1/conference/invite.php?ext=1003
X-Provision-Jti: <jti>
Content-Type: application/json

{
  "room": "asaphone-grp-a1b2c3d4",
  "extensions": ["1004", "1005"]
}
```

Réponse :

```json
{
  "ok": true,
  "room": "asaphone-grp-a1b2c3d4",
  "invited": ["1004", "1005"],
  "skipped": [],
  "errors": []
}
```

Pour ré-inviter **tout le groupe** sans lister les extensions :

```json
{ "room": "asaphone-grp-…", "auto": true }
```

Le client **ne ouvre pas** un second appel : il reste sur la salle ; le PBX sonne les invités.

## Liste des groupes

```http
GET /provision/api/v1/groups/list.php?ext=1003
X-Provision-Jti: <jti>
```

## Intégration client — checklist

| Étape | Action |
|-------|--------|
| Parser | `session.conference`, `session.groups`, `api.endpoints.*` |
| Sync | Après création groupe → `groups_sync` |
| Stockage local | `LocalMessagingStore` : `call_uri` serveur **prioritaire** sur `asaphone-grp-{id}` local |
| Appel groupe | `launchVoiceCall(context, group.callUri)` |
| Inviter | `POST conference_invite` + toast « invitation envoyée » |
| Retrait | Supprimer fallback `asaphone-grp-*` généré localement quand `call_uri` présent |

## Auth

Même modèle que chat / VM : `?ext=` + header **`X-Provision-Jti`** (valeur `session.jti`).

## Déploiement serveur

```bash
sudo bash scripts/provision-install.sh
# ou partiel :
sudo mysql asterisk < scripts/provision-schema-groups.sql
sudo bash scripts/apply-conference-dialplan.sh
sudo rsync -a provision/ /var/www/provision/
```

## Fichiers serveur

| Fichier | Rôle |
|---------|------|
| `provision/lib/groups.php` | Sync / liste groupes |
| `provision/lib/conference.php` | Originate invités |
| `provision/api/v1/groups/sync.php` | POST sync |
| `provision/api/v1/groups/list.php` | GET liste |
| `provision/api/v1/conference/invite.php` | POST inviter |
| `scripts/apply-conference-dialplan.sh` | Dialplan 6000 / asaphone-grp-* |
| `provision/bin/conf-invite.php` | CLI originate |
 