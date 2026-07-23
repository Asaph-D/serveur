#!/usr/bin/env bash
# Dialplan PJSIP MESSAGE (chat Asaphone) + notification messagerie vocale
# Usage : sudo bash scripts/apply-message-dialplan.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_CUSTOM="/etc/asterisk/extensions_custom.conf"
MARK_BEGIN=";>>>BEGIN_SIP_MESSAGE"
MARK_END=";<<<END_SIP_MESSAGE"
PBX_DOMAIN="${PROVISION_PBX_HOST:-pbx.local}"

if [[ -f /etc/provision/provision.env ]]; then
	# shellcheck disable=SC1091
	source /etc/provision/provision.env
	PBX_DOMAIN="${PROVISION_PBX_HOST:-pbx.local}"
fi

if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

if grep -qF "$MARK_BEGIN" "$EXT_CUSTOM" 2>/dev/null; then
	sed -i "/$(printf '%s' "$MARK_BEGIN" | sed 's/[;]/\\&/g')/,/$(printf '%s' "$MARK_END" | sed 's/[;]/\\&/g')/d" "$EXT_CUSTOM"
fi

# Retirer ancien bloc from-message (sans marqueurs BEGIN_SIP_MESSAGE)
if grep -qF '[from-message]' "$EXT_CUSTOM" 2>/dev/null; then
	sed -i '/^;===.*PJSIP MESSAGE/,/^exten => _X\.,4,Hangup()/d' "$EXT_CUSTOM" 2>/dev/null || true
	sed -i '/^\[from-message\]$/,/^exten => _X\.,4,Hangup()/d' "$EXT_CUSTOM" 2>/dev/null || true
fi

NOTIFY_DIR="/var/lib/provision/tmp"
mkdir -p "$NOTIFY_DIR"
chown www-data:asterisk "$NOTIFY_DIR" 2>/dev/null || chown www-data:www-data "$NOTIFY_DIR"
chmod 0775 "$NOTIFY_DIR"

MSG_BLOCK=$(cat <<DIAL

;>>>BEGIN_SIP_MESSAGE
; PJSIP MESSAGE — chat Asaphone + notification messagerie (même flux)
; Fix To URI : sip:\${EXTEN}@${PBX_DOMAIN}

[from-message]
exten => _X.,1,NoOp(PJSIP MESSAGE to \${EXTEN} from \${MESSAGE(from)})
 same => n,Set(MESSAGE(to)=sip:\${EXTEN}@${PBX_DOMAIN})
 same => n,Set(CHAT_TMP=${NOTIFY_DIR}/chat-\${UNIQUEID}.txt)
 same => n,System(printf '%s' "\${MESSAGE(body)}" > \${CHAT_TMP})
 same => n,System(printf '%s' "\${MESSAGE(from)}" > \${CHAT_TMP}.from)
 same => n,System(sudo -n /usr/local/bin/asaphone-chat-ingest store \${EXTEN} \${CHAT_TMP} > \${CHAT_TMP}.id 2>/dev/null)
 same => n,Set(CHAT_ID=\${SHELL(cat \${CHAT_TMP}.id 2>/dev/null | tr -d '\\n')})
 same => n,Set(MESSAGE(body)=\${MESSAGE(body)})
 same => n,MessageSend(pjsip:\${EXTEN})
 same => n,ExecIf(\$["\${MESSAGE_SEND_STATUS}"="SUCCESS" & \${LEN(\${CHAT_ID})} > 0]?System(sudo -n /usr/local/bin/asaphone-chat-ingest delivered \${CHAT_ID} 2>/dev/null))
 same => n,System(rm -f \${CHAT_TMP} \${CHAT_TMP}.from \${CHAT_TMP}.id)
 same => n,Hangup()

[vm-notify-out]
exten => _X.,1,NoOp(Notification VM → \${EXTEN})
 same => n,Set(VM_NOTIFY_FILE=${NOTIFY_DIR}/vm-notify-\${EXTEN}.json)
 same => n,Set(VM_NOTIFY_BODY=\${SHELL(cat \${VM_NOTIFY_FILE} 2>/dev/null | tr -d '\\n')})
 same => n,GotoIf(\$["\${LEN(\${VM_NOTIFY_BODY})}" = "0"]?fail)
 same => n,Set(VM_CALLER=\${SHELL(cat ${NOTIFY_DIR}/vm-notify-\${EXTEN}.caller 2>/dev/null | tr -d '\\n')})
 same => n,Set(VM_CALLER=\${IF(\$[\${LEN(\${VM_CALLER})} > 0]?\${VM_CALLER}:pbx)})
 same => n,Set(MESSAGE(from)=sip:\${VM_CALLER}@${PBX_DOMAIN})
 same => n,Set(MESSAGE(to)=sip:\${EXTEN}@${PBX_DOMAIN})
 same => n,Set(MESSAGE(body)=\${VM_NOTIFY_BODY})
 same => n,MessageSend(pjsip:\${EXTEN})
 same => n,System(rm -f \${VM_NOTIFY_FILE} ${NOTIFY_DIR}/vm-notify-\${EXTEN}.caller)
 same => n,Hangup()
 same => n(fail),NoOp(vm-notify-out: fichier absent pour \${EXTEN})
 same => n,Hangup()
;<<<END_SIP_MESSAGE
DIAL
)

printf '%s\n' "$MSG_BLOCK" >> "$EXT_CUSTOM"
chown www-data:asterisk "$EXT_CUSTOM" 2>/dev/null || chown asterisk:asterisk "$EXT_CUSTOM" 2>/dev/null || true

echo "Dialplan MESSAGE : from-message + vm-notify-out (domaine ${PBX_DOMAIN})"
if command -v fwconsole >/dev/null 2>&1; then
	fwconsole reload
else
	asterisk -rx "dialplan reload"
fi
