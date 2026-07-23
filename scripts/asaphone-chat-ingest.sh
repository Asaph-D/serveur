#!/bin/bash
# Stockage chat depuis dialplan Asterisk (user www-data)
exec runuser -u www-data -- /usr/bin/php /var/www/provision/bin/chat-ingest.php "$@"
