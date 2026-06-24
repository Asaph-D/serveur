# Publier le bootstrap sur GitHub Pages

Copier ce dossier dans le dépôt **Portfolio** :

```
Portfolio/
  provision/
    bootstrap.json   ← ce fichier
```

URL finale : `https://asaph-d.github.io/Portfolio/provision/bootstrap.json`

Après `git push`, tester :

```bash
curl -s 'https://asaph-d.github.io/Portfolio/provision/bootstrap.json'
```

Mettre à jour `api_remote` et `vpn.endpoint_remote` quand l’IP publique change.
