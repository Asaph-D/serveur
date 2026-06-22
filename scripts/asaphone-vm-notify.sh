#!/bin/bash
# Wrapper externnotify Asterisk → mini-API Asaphone (www-data)
exec runuser -u www-data -- /usr/bin/php /var/www/provision/bin/vm-notify.php "$@"
