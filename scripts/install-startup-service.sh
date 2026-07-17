#!/bin/bash
set -euo pipefail

UNIT_SRC="/home/asaph/Documents/serveur/systemd/serveur-startup.service"
UNIT_DST="/etc/systemd/system/serveur-startup.service"

if [[ $(id -u) -ne 0 ]]; then
  echo "ERREUR: exécuter en root (ex. sudo bash $0)" >&2
  exit 1
fi

test -f "$UNIT_SRC" || { echo "Fichier introuvable: $UNIT_SRC" >&2; exit 1; }

install -m 0644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload
systemctl enable --now serveur-startup.service

echo "OK: service installé et démarré."
echo ""
echo "  Console interactive (bannière + barre de progression) :"
echo "    bash scripts/start-startup.sh"
echo "    bash scripts/restart-startup.sh"
echo ""
echo "  Boot automatique (silencieux, pas de sortie terminal) :"
echo "    systemctl start serveur-startup.service"
