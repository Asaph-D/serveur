# Rapport PDF — pipeline de génération

Génère le mémoire technique **`asterisk-asaphone-report.pdf`** (racine du dépôt)
à partir des documents du dépôt serveur, des captures réelles de `capture/`
et de figures dessinées en Python.

**Aucun LaTeX** : figures = matplotlib → PNG, PDF = reportlab (Platypus).

## Contenu du dossier

| Fichier | Rôle |
|---------|------|
| `gen_diagrams.py` | Diagrammes vectoriels → `figures/fig-*.png` : architecture globale, dual-homing, use cases Asaphone, séquences (appel 1001↔1003, provision QR, ConfBridge), pipeline monitoring, couches sécurité L0–L7, comparatif extension/trunk/VPN/VLAN/Cloudflare |
| `gen_consoles.py` | Planches « terminal » → `figures/console-*.png` : phases d'installation (INSTALLATION.md), monitoring CLI (`docker compose ps` + logs Telegraf), sortie console `serveur-startup` (fidèle à `scripts/server-startup.sh` + `scripts/lib/startup-console.sh`) |
| `build_pdf.py` | Assemblage du PDF (A4, ~45 pages) : garde, abstracts FR/EN, sommaire cliquable, 18 chapitres, annexes A–F |
| `requirements.txt` | Dépendances Python |

## Prérequis

Python 3.10+ avec **matplotlib**, **reportlab** et **Pillow**.

```bash
# Debian / Ubuntu (paquets système)
sudo apt-get install -y python3-matplotlib python3-reportlab python3-pil

# ou via pip
pip install -r report/requirements.txt
```

Polices : DejaVu (`/usr/share/fonts/truetype/dejavu/`), présentes par défaut
sur Debian/Ubuntu — nécessaires pour les symboles (→ · ↔ ≥ ✓) dans le PDF.

## Régénérer le rapport

Depuis la **racine du dépôt** (`serveur/`) :

```bash
python3 report/gen_diagrams.py    # 1. diagrammes  → figures/fig-*.png
python3 report/gen_consoles.py    # 2. consoles    → figures/console-*.png
python3 report/build_pdf.py       # 3. assemblage  → asterisk-asaphone-report.pdf
```

Ordre obligatoire : `build_pdf.py` lit les PNG de `figures/` et les captures de
`capture/` (les 16 fichiers du mapping doivent exister).

## Règles éditoriales appliquées

- **Captures réelles** (`capture/*.png`) : utilisées telles quelles, légende
  « Capture — … » ; jamais remplacées par de faux screenshots.
- **Figures générées** (`figures/*.png`) : légende « Schéma généré — … » avec la
  source du dépôt entre parenthèses.
- **Aucun secret** : pas de tokens, mots de passe SIP/DB, contenus `.env`.
  IP/hosts = valeurs d'exemple documentées dans le dépôt (`pbx.local`,
  `10.10.10.10`, `192.168.1.80` de `network/windows-hosts.txt`…).
- Information absente des dépôts → mention « non documenté dans le dépôt ».

## Sources de vérité (dépôt serveur)

`Architecture-VoIP-communication-composants.md`, `Plan-adressage-reseau-VoIP-QoS.md`,
`S2/S3/S4-Phase*.md`, `INSTALLATION.md`, `webrtc/README.md`, `docs/*.md`,
`security/*.md`, `monitoring/` (docker-compose, telegraf, grafana),
`scripts/server-startup.sh`, `scripts/lib/startup-console.sh`,
`systemd/serveur-startup.service`, `provision/`, `network/`.
