#!/usr/bin/env bash
# Affiche le dernier démarrage (après systemctl start/restart serveur-startup).
#
# Usage :
#   bash scripts/startup-show.sh          # résumé du dernier boot
#   bash scripts/startup-show.sh -f       # suit le log en direct
#   sudo bash scripts/server-startup.sh   # relancer ET voir la console ici
set -euo pipefail

LOG="${LOG_FILE:-/var/log/serveur-startup.log}"

if [[ "${1:-}" == "-f" || "${1:-}" == "--follow" ]]; then
	echo "Suivi de ${LOG} (Ctrl+C pour quitter)"
	echo ""
	exec tail -f "$LOG"
fi

if [[ ! -f "$LOG" ]]; then
	echo "Log introuvable : $LOG" >&2
	echo "Lancez : sudo systemctl start serveur-startup.service" >&2
	exit 1
fi

last_ok="$(grep -n '^serveur-startup: OK' "$LOG" | tail -1 | cut -d: -f1 || true)"
if [[ -z "$last_ok" ]]; then
	echo "Aucun démarrage terminé dans ${LOG}"
	tail -30 "$LOG"
	exit 0
fi

start=$(( last_ok > 120 ? last_ok - 120 : 1 ))
echo "Dernier démarrage (lignes ${start}-${last_ok}) — ${LOG}"
echo ""
sed -n "${start},${last_ok}p" "$LOG"

echo ""
echo "── Pour voir la console EN DIRECT dans ce terminal ──"
echo "  sudo bash scripts/server-startup.sh"
echo ""
echo "── Après systemctl restart (arrière-plan) ──"
echo "  bash scripts/startup-show.sh"
echo "  journalctl -u serveur-startup.service -n 60 --no-pager"
