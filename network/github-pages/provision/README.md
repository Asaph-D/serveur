# Publier le bootstrap sur GitHub Pages

## Automatique (recommandé sans domaine propre)

1. Créer un **Personal Access Token** GitHub (scope `repo` sur le dépôt Portfolio)
2. Sur le PBX :
   ```bash
   echo "ghp_VOTRE_TOKEN" | sudo tee /etc/provision/github-token
   sudo chmod 600 /etc/provision/github-token
   ```
3. Vérifier `GITHUB_BOOTSTRAP_PUBLISH="yes"` dans `network/global-config.env`

À chaque boot, `serveur-startup.service` met à jour `api_remote` (tunnel trycloudflare) et pousse le fichier sur GitHub.

Test manuel :
```bash
bash scripts/publish-bootstrap-github.sh
curl -s 'https://asaph-d.github.io/Portfolio/provision/bootstrap.json' | jq .api_remote
```

## Manuel

Copier `bootstrap.json` dans le dépôt **Portfolio** :

```
Portfolio/
  provision/
    bootstrap.json
```

URL : `https://asaph-d.github.io/Portfolio/provision/bootstrap.json`
