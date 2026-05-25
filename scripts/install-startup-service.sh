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
echo "- Logs: journalctl -u serveur-startup.service -b --no-pager"
echo "- Log fichier: /var/log/serveur-startup.log"
