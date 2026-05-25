#!/bin/bash
set -euo pipefail
# Installe res_srtp pour WebRTC DTLS-SRTP. Usage: sudo bash scripts/install-asterisk-res-srtp.sh
# Asterisk 20 : pas de cible make res/res_srtp.so seule ; il faut compiler le module via make (incremental).
[[ $(id -u) -eq 0 ]] || exit 1
AST_SRC="${AST_SRC:-/usr/src/asterisk-20.18.2}"
MOD="/usr/lib/asterisk/modules"
JOBS="${JOBS:-$(nproc)}"
test -f "$AST_SRC/res/res_srtp.c" || exit 1
apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y libsrtp2-dev
cd "$AST_SRC"
./configure
test -x menuselect/menuselect || make -C menuselect
menuselect/menuselect --enable res_srtp menuselect.makeopts
menuselect/menuselect --check-deps menuselect.makeopts || true
if ! grep -q 'MENUSELECT_RES=.*res_srtp' menuselect.makeopts; then
  echo "ERREUR: res_srtp non selectionne dans menuselect.makeopts (dependance ?)." >&2
  exit 1
fi
make -j"$JOBS"
test -f res/res_srtp.so || { echo "res/res_srtp.so introuvable apres make" >&2; exit 1; }
install -m 755 res/res_srtp.so "$MOD/res_srtp.so"
asterisk -rx "module load res_srtp.so" || true
test -x /usr/sbin/fwconsole && /usr/sbin/fwconsole reload || true
