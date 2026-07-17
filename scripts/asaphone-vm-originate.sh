#!/bin/bash
# Originate vm-notify-out (root / asterisk socket)
set -euo pipefail
EXT="${1:?extension}"
CALLER="${2:-pbx}"
# /n obligatoire sur Local ; __VM_CALLER hérité par le dialplan vm-notify-out
asterisk -rx "channel originate {__VM_CALLER=${CALLER}}Local/${EXT}@vm-notify-out/n application NoOp notify"
