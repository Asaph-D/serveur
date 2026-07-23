#!/usr/bin/env bash
# ConfBridge Asaphone — salles 6000 / asaphone-grp-* + invitation membres
# Usage : sudo bash scripts/apply-conference-dialplan.sh
set -euo pipefail

EXT_CUSTOM="/etc/asterisk/extensions_custom.conf"
CONF_CUSTOM="/etc/asterisk/confbridge_custom.conf"
MARK_BEGIN=";>>>BEGIN_ASAPHONE_CONF"
MARK_END=";<<<END_ASAPHONE_CONF"

if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

DIAL=$(cat <<'DIAL'
;>>>BEGIN_ASAPHONE_CONF
; Appel de groupe Asaphone — le client compose call_uri ; le PBX mixe (ConfBridge).

[from-internal]
exten => 6000,1,Gosub(asaphone-conf-start,s,1(6000))
exten => _60[0-9][0-9],1,Gosub(asaphone-conf-start,s,1(${EXTEN}))
exten => _asaphone-grp-.,1,Gosub(asaphone-conf-start,s,1(${EXTEN}))

[asaphone-conf-start]
exten => s,1,NoOp(Asaphone conference ${ARG1} caller ${CALLERID(num)})
 same => n,Answer()
 same => n,Set(ASAPHONE_CONF_ROOM=${ARG1})
 same => n,System(sudo -n /usr/bin/php /var/www/provision/bin/conf-invite.php auto ${ASAPHONE_CONF_ROOM} ${CALLERID(num)} >/dev/null 2>&1)
 same => n,ConfBridge(${ASAPHONE_CONF_ROOM},asaphone_conf_bridge,asaphone_conf_user)
 same => n,Hangup()

[asaphone-conf-join]
exten => s,1,NoOp(Join conf room ${ASAPHONE_CONF_ROOM})
 same => n,Answer()
 same => n,Wait(1)
 same => n,Set(ROOM=${IF($["${ASAPHONE_CONF_ROOM}"=""]?6000:${ASAPHONE_CONF_ROOM})})
 same => n,ConfBridge(${ROOM},asaphone_conf_bridge,asaphone_conf_user)
 same => n,Hangup()
;<<<END_ASAPHONE_CONF
DIAL
)

if grep -qF "$MARK_BEGIN" "$EXT_CUSTOM" 2>/dev/null; then
	sed -i "/$(printf '%s' "$MARK_BEGIN" | sed 's/[;]/\\&/g')/,/$(printf '%s' "$MARK_END" | sed 's/[;]/\\&/g')/d" "$EXT_CUSTOM"
fi
printf '%s\n' "$DIAL" >> "$EXT_CUSTOM"
chown www-data:asterisk "$EXT_CUSTOM" 2>/dev/null || chown asterisk:asterisk "$EXT_CUSTOM" 2>/dev/null || true

CONF=$(cat <<'CONF'
; Profils ConfBridge Asaphone (audio mix serveur)
[asaphone_conf_bridge]
type=bridge
max_members=25
record_conference=no
mixing_interval=20

[asaphone_conf_user]
type=user
marked=no
startmuted=no
quiet=no
dsp_drop_silence=yes
announce_join_leave=no
CONF
)
printf '%s\n' "$CONF" > "$CONF_CUSTOM"
chown www-data:asterisk "$CONF_CUSTOM" 2>/dev/null || chown asterisk:asterisk "$CONF_CUSTOM" 2>/dev/null || true
chmod 664 "$CONF_CUSTOM"

echo "Dialplan conférence Asaphone appliqué (6000, 60XX, asaphone-grp-*)"
if command -v fwconsole >/dev/null 2>&1; then
	fwconsole reload
else
	asterisk -rx "dialplan reload"
	asterisk -rx "module reload app_confbridge.so"
fi
