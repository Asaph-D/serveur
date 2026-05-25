#!/bin/bash
# Applique dialplan / files d’attente / AMI Telegraf / AGI Phase 3 sur le serveur FreePBX local.
# Exécuter : sudo bash scripts/phase3-apply-asterisk.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
MARK_BEGIN=";>>>BEGIN_PHASE3"
MARK_END=";<<<END_PHASE3"

if [[ $(id -u) -ne 0 ]]; then
	echo "Root requis : sudo bash $0" >&2
	exit 1
fi

if ! grep -qF "$MARK_BEGIN" /etc/asterisk/extensions_custom.conf 2>/dev/null; then
	cat >> /etc/asterisk/extensions_custom.conf <<'DIAL'

;>>>BEGIN_PHASE3
; Phase 3 — IVR AGI, horaires GotoIfTime, file ACD, conférence ConfBridge, enregistrement MixMonitor
; Numéros : 7000 routage horaire → 7010 IVR | 7020 file | 8001 conf (PIN 1234) | 8100 test enregistrement

[from-internal-custom]
; Routage horaire (lun–ven 09:00–17:59) — ajustez les plages au besoin
exten => 7000,1,NoOp(Phase3 time condition)
 same => n,GotoIfTime(09:00-17:59,mon-fri,*,*?open,closed)
 same => n(open),Goto(from-internal,7010,1)
 same => n(closed),Playback(vm-goodbye)
 same => n,Hangup()

; IVR intelligent (AGI Python)
exten => 7010,1,NoOp(Phase3 IVR AGI)
 same => n,AGI(phase3_intelligent_ivr.py,fr)
 same => n,Hangup()

; File d’attente ACD (app_queue) — stratégie leastrecent dans queues_custom.conf ; sonnerie groupée : créer une 2e queue ringall si besoin
exten => 7020,1,NoOp(Phase3 queue phase3-support)
 same => n,Set(CALLFILE=${STRFTIME(${EPOCH},,%Y%m%d-%H%M%S)}-${FILTER(0-9,${CALLERID(num)})})
 same => n,MixMonitor(/var/spool/asterisk/monitor/${CALLFILE}.wav,b)
 same => n,Queue(phase3-support,t,,,90)
 same => n,Hangup()

; Conférence dynamique (PIN 1234 — à changer en prod)
exten => 8001,1,NoOp(Phase3 ConfBridge)
 same => n,Answer()
 same => n,Read(PIN,,4,,3,5)
 same => n,GotoIf($[${LEN(${PIN})} >= 4]?pinok:badpin)
 same => n(pinok),GotoIf($["${PIN}" = "1234"]?join:badpin)
 same => n(join),Set(CONFROOM=phase3-${PIN})
 same => n,ConfBridge(${CONFROOM})
 same => n,Hangup()
 same => n(badpin),Playback(vm-goodbye)
 same => n,Hangup()

; Test enregistrement seul (MixMonitor + messagerie 1001)
exten => 8100,1,NoOp(Phase3 test MixMonitor)
 same => n,Answer()
 same => n,Set(CALLFILE=test-${STRFTIME(${EPOCH},,%Y%m%d-%H%M%S)}-${FILTER(0-9,${CALLERID(num)})})
 same => n,MixMonitor(/var/spool/asterisk/monitor/${CALLFILE}.wav,b)
 same => n,Voicemail(1001@default,s)
 same => n,Hangup()
;<<<END_PHASE3
DIAL
	echo "Bloc Phase3 ajouté à extensions_custom.conf"
else
	echo "Bloc Phase3 déjà présent dans extensions_custom.conf"
fi

install -d -o asterisk -g asterisk -m 0755 /var/spool/asterisk/monitor
install -d -o asterisk -g asterisk -m 0755 /var/lib/asterisk/agi-bin
install -m 0755 -o asterisk -g asterisk "$REPO/phase3/agi/phase3_intelligent_ivr.py" /var/lib/asterisk/agi-bin/phase3_intelligent_ivr.py
install -m 0644 -o asterisk -g asterisk "$REPO/phase3/asterisk/phase3-vip.txt" /etc/asterisk/phase3-vip.txt

if [[ ! -s /etc/asterisk/queues_custom.conf ]] || ! grep -q '^\[phase3-support\]' /etc/asterisk/queues_custom.conf; then
	cat >> /etc/asterisk/queues_custom.conf <<'QC'
[phase3-support]
strategy=leastrecent
timeout=20
retry=2
wrapuptime=5
maxlen=0
ringinuse=no
joinempty=yes
leavewhenempty=no
member => PJSIP/1001,0
member => PJSIP/1002,0
member => PJSIP/1003,0
member => PJSIP/1004,0
member => PJSIP/1005,0
; MoH : classe default (core sounds). Installer module music FreePBX pour fichiers dédiés.
musicclass=default
QC
	echo "Queue phase3-support ajoutée dans queues_custom.conf"
else
	echo "Queue phase3-support déjà définie"
fi

AMI_PASS=""
if [[ -f "$REPO/monitoring/.env" ]]; then
	# shellcheck disable=SC1090
	source "$REPO/monitoring/.env"
	AMI_PASS="${AMI_TELEGRAF_PASSWORD:-}"
fi
if [[ -z "$AMI_PASS" ]]; then
	echo "AMI_TELEGRAF_PASSWORD introuvable : créez monitoring/.env via phase3-gen-monitoring-env.sh" >&2
	exit 1
fi

if ! grep -q '^\[telegraf\]' /etc/asterisk/manager_custom.conf; then
	{
		printf '\n[telegraf]\nsecret = %s\n' "$AMI_PASS"
		printf '%s\n' 'deny=0.0.0.0/0.0.0.0' 'permit=127.0.0.1/255.255.255.255' 'read = system,call,log,verbose,reporting,command' 'write = command'
	} >> /etc/asterisk/manager_custom.conf
	echo "Utilisateur AMI [telegraf] ajouté (manager_custom.conf)"
else
	echo "Réutilisez l’AMI [telegraf] existant ; si mot de passe à changer, éditez manager_custom.conf et monitoring/.env"
fi

if ! grep -q 'BEGIN_PHASE3_TRUNK_TEMPLATE' /etc/asterisk/pjsip_custom_post.conf 2>/dev/null; then
	cat >> /etc/asterisk/pjsip_custom_post.conf <<'PJSIP'

; BEGIN_PHASE3_TRUNK_TEMPLATE — décommenter et adapter (OVH, Twilio, etc.). Vérifier conflit avec trunks FreePBX UI.
;[wizard-ovh]
;type = wizard
;transport = transport-udp
;accepts_registrations = no
;sends_auth = yes
;sends_registrations = yes
;endpoint = ovh-endpoint
;identify = ovh-identify
;remote_hosts = sip.ovh.fr
;outbound_auth/username = VOTRE_LOGIN
;outbound_auth/password = VOTRE_SECRET
;aor/contact = sip:VOTRE_LOGIN@sip.ovh.fr
PJSIP
	echo "Modèle trunk wizard ajouté (commenté) dans pjsip_custom_post.conf"
fi

/usr/sbin/asterisk -rx "manager reload"
/usr/sbin/fwconsole reload

echo "Phase 3 Asterisk appliquée. Vérifications :"
echo "  sudo asterisk -rx \"queue show phase3-support\""
echo "  sudo asterisk -rx \"dialplan show from-internal\""
