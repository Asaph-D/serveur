#!/bin/bash
# Originate join ConfBridge (root / socket asterisk)
set -euo pipefail
ROOM="${1:?room}"
TARGET="${2:?target ext}"
CALLER="${3:-pbx}"
exec /usr/bin/php /var/www/provision/bin/conf-invite.php "$ROOM" "$TARGET" "$CALLER"
