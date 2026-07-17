#!/usr/bin/env bash
# WebRTC (opus) : forcer ulaw avant lecture des prompts VM / Playback (pas de codec_opus).
# Usage : sudo bash scripts/apply-webrtc-audio-codec-fix.sh
set -euo pipefail

EXT_CUSTOM="/etc/asterisk/extensions_custom.conf"
MARK_BEGIN=";>>>BEGIN_WEBRTC_ULAW"
MARK_END=";<<<END_WEBRTC_ULAW"

if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

BLOCK=$(cat <<'DIAL'

;>>>BEGIN_WEBRTC_ULAW
; Postes WebRTC (opus) : prompts VM/IVR en gsm/ulaw — forcer ulaw sur le canal appelant.

[asaphone-force-ulaw]
exten => s,1,GotoIf($["${CHANNEL(channeltype)}" != "PJSIP"]?done)
 same => n,Set(CHANNEL(audiowriteformat)=ulaw)
 same => n,Set(CHANNEL(audioreadformat)=ulaw)
 same => n(done),Return()

; Avant Dial interne (ex. 1003 → 1004 puis messagerie)
[macro-dial-one-predial-hook]
exten => s,1,Gosub(asaphone-force-ulaw,s,1)
 same => n,Return()

[macro-dial-hunt-predial-hook]
exten => s,1,Gosub(asaphone-force-ulaw,s,1)
 same => n,Return()

; extensions_custom chargé après extensions_additional : extensions exactes > motif _s-.
[macro-vm]
exten => s-BUSY,1,Noop(BUSY voicemail)
 same => n,Macro(get-vmcontext,${MEXTEN})
 same => n,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMail(${MEXTEN}@${VMCONTEXT},${VM_OPTS}b${VMGAIN})
 same => n,Goto(exit-${VMSTATUS},1)

exten => s-NOANSWER,1,Macro(get-vmcontext,${MEXTEN})
 same => n,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMail(${MEXTEN}@${VMCONTEXT},${VM_OPTS}u${VMGAIN})
 same => n,Goto(exit-${VMSTATUS},1)

exten => s-CHANUNAVAIL,1,Macro(get-vmcontext,${MEXTEN})
 same => n,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMail(${MEXTEN}@${VMCONTEXT},${VM_OPTS}u${VMGAIN})
 same => n,Goto(exit-${VMSTATUS},1)

exten => s-CONGESTION,1,Macro(get-vmcontext,${MEXTEN})
 same => n,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMail(${MEXTEN}@${VMCONTEXT},${VM_OPTS}u${VMGAIN})
 same => n,Goto(exit-${VMSTATUS},1)

exten => s-NOMESSAGE,1,Noop(NOMESSAGE voicemail)
 same => n,Macro(get-vmcontext,${MEXTEN})
 same => n,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMail(${MEXTEN}@${VMCONTEXT},s${VM_OPTS}${VMGAIN})
 same => n,Goto(exit-${VMSTATUS},1)

exten => s-INSTRUCT,1,Noop(INSTRUCT voicemail)
 same => n,Macro(get-vmcontext,${MEXTEN})
 same => n,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMail(${MEXTEN}@${VMCONTEXT},${VM_OPTS}${VMGAIN})
 same => n,Goto(exit-${VMSTATUS},1)

exten => s-DIRECTDIAL,1,Noop(DIRECTDIAL voicemail)
 same => n,Macro(get-vmcontext,${MEXTEN})
 same => n,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMail(${MEXTEN}@${VMCONTEXT},${VM_OPTS}${VM_DDTYPE}${VMGAIN})
 same => n,Goto(exit-${VMSTATUS},1)

exten => dovm,1,Noop(VMX Timeout - go to voicemail)
 same => n,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMail(${MEXTEN}@${VMCONTEXT},${VMX_OPTS}${VMGAIN})
 same => n,Goto(exit-${VMSTATUS},1)

exten => adef,1,Gosub(asaphone-force-ulaw,s,1)
 same => n,VoiceMailMain(${MEXTEN}@${VMCONTEXT})
 same => n,GotoIf($["${RETVM}" = "RETURN"]?exit-RETURN,1)
 same => n,Hangup()
;<<<END_WEBRTC_ULAW
DIAL
)

if grep -qF "$MARK_BEGIN" "$EXT_CUSTOM" 2>/dev/null; then
	sed -i "/$(printf '%s' "$MARK_BEGIN" | sed 's/[;]/\\&/g')/,/$(printf '%s' "$MARK_END" | sed 's/[;]/\\&/g')/d" "$EXT_CUSTOM"
fi

printf '%s\n' "$BLOCK" >> "$EXT_CUSTOM"
chown www-data:asterisk "$EXT_CUSTOM" 2>/dev/null || chown asterisk:asterisk "$EXT_CUSTOM" 2>/dev/null || true

echo "WebRTC ulaw fix : macro-vm extensions exactes + predial hooks"
if command -v fwconsole >/dev/null 2>&1; then
	fwconsole reload
else
	asterisk -rx "dialplan reload"
fi
