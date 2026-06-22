#!/bin/bash
# Originate vm-notify-out (root / asterisk socket)
set -euo pipefail
EXT="${1:?extension}"
CALLER="${2:-pbx}"
asterisk -rx "channel originate {VM_CALLER=${CALLER}}Local/${EXT}@vm-notify-out application NoOp vm-notify"
