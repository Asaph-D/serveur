## Rapport — Messagerie vocale FreePBX (1001–1010)

### Symptôme observé

Lors d’un appel vers une extension (ex. `1001`), FreePBX bascule vers la messagerie (`macro-vm`) puis Asterisk loggue :

- `leave_voicemail: Exten: 1001: No entry in voicemail config file for '1001'`
- lecture des prompts `im-sorry` / `an-error-has-occurred`
- raccrochage

Conclusion : **l’extension existe côté PJSIP**, mais **la mailbox voicemail correspondante n’existe pas** (ou n’est pas mappée) côté Voicemail.

### Constat technique

- La table SQL `voicemail` n’existe pas dans cette base (normal selon versions/modules FreePBX).
- La gestion de la messagerie se fait via le module FreePBX **Voicemail** (BMO) et génère la config Asterisk.
- Vérification runtime : `asterisk -rx "voicemail show users"` affichait des mailboxes pour certaines extensions (ex. `1002`, `1005`… ) mais **pas toutes**.

### Objectif

- Activer une messagerie **complète** pour **toutes les extensions 1001–1010**.
- Comportement “laisser un message” : **automatique après le signal sonore** (comportement standard `VoiceMail()` côté Asterisk).

### Action appliquée

Utilisation / remise en cohérence du script FreePBX existant :

- `scripts/phase2-enable-voicemail.php`
  - crée/active la mailbox `default/<ext>` pour `1001..1010`
  - définit le nom `Poste <ext>`
  - PIN `vmpwd` = 4 derniers chiffres de l’extension (ex. `1001` → `1001`, `1010` → `1010`)
  - options : `attach=yes`, `envelope=yes`, `saycid=yes`, `vmdelete=no`
  - met `users.voicemail=default` et mappe la mailbox (`mapMailBox`)

Puis :

- `fwconsole reload`

### Vérifications à faire / faites

- **Mailboxes présentes** :

```bash
sudo asterisk -rx "voicemail show users"
```

Attendu : `default 1001` … `default 1010` listés.

- **Test fonctionnel** :
  - Appeler une extension (ex. `1001`) depuis un autre poste.
  - Laisser sonner / occuper / éteindre selon la règle de renvoi.
  - Après le “bip”, l’enregistrement du message démarre automatiquement.

### Notes

- Les menus vocaux et options (écouter/supprimer/enregistrer, etc.) sont ceux de l’application Voicemail Asterisk/FreePBX et dépendront des prompts/locale installés.
- Si un client se “désenregistre” (REGISTER `Expires: 0`) au mauvais moment, il peut être vu comme **Unreachable** et déclencher le renvoi VM : c’est indépendant de l’existence de la mailbox.

