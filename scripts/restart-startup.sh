#!/usr/bin/env bash
# Relance le démarrage avec bannière + barre de progression dans CE terminal.
#
# Usage : bash scripts/restart-startup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ $(id -u) -ne 0 ]]; then
	exec sudo -E bash "$0" "$@"
fi

export ROOT_SRV="$ROOT"
exec bash "$ROOT/scripts/server-startup.sh"
