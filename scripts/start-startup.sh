#!/usr/bin/env bash
# Démarre le PBX avec bannière + barre de progression dans CE terminal.
#
# systemctl start serveur-startup  → silencieux (boot automatique uniquement)
# bash scripts/start-startup.sh    → console complète ici
#
# Usage : bash scripts/start-startup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ $(id -u) -ne 0 ]]; then
	exec sudo -E bash "$0" "$@"
fi

export ROOT_SRV="$ROOT"
exec bash "$ROOT/scripts/server-startup.sh"
