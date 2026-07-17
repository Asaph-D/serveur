#!/usr/bin/env bash
# Installe codec_opus Digium pour transcoding GSM/ulaw ↔ opus (messagerie WebRTC).
# Usage : sudo bash scripts/install-codec-opus.sh
set -euo pipefail

AST_VER="$(asterisk -V 2>/dev/null | sed -n 's/.*Asterisk \([0-9]*\.[0-9]*\).*/\1/p' | head -1)"
AST_VER="${AST_VER:-20.0}"
MOD_DIR="/usr/lib/asterisk/modules"
DOC_DIR="/var/lib/asterisk/documentation/thirdparty"
TMP="/tmp/codec_opus-install"
TARBALL="codec_opus-${AST_VER}_1.3.0-x86_64.tar.gz"
URL="http://downloads.digium.com/pub/telephony/codec_opus/asterisk-${AST_VER}/x86-64/${TARBALL}"

[[ $(id -u) -eq 0 ]] || { echo "Root requis." >&2; exit 1; }

if asterisk -rx "module show like codec_opus" 2>/dev/null | grep -qE 'codec_opus\.so.*Running'; then
	echo "codec_opus déjà actif."
	exit 0
fi

mkdir -p "$TMP"
if [[ ! -f "$TMP/$TARBALL" ]]; then
	echo "Téléchargement $URL ..."
	wget -q -O "$TMP/$TARBALL" "$URL" || {
		echo "Échec téléchargement. Essayer AST_VER=20.0 manuellement." >&2
		exit 1
	}
fi

tar xzf "$TMP/$TARBALL" -C "$TMP"
SRC="$(find "$TMP" -maxdepth 1 -type d -name 'codec_opus-*' | head -1)"
[[ -n "$SRC" && -f "$SRC/codec_opus.so" ]] || { echo "Archive invalide." >&2; exit 1; }

mkdir -p "$MOD_DIR" "$DOC_DIR"
cp -f "$SRC/codec_opus.so" "$MOD_DIR/"
[[ -f "$SRC/format_ogg_opus.so" ]] && cp -f "$SRC/format_ogg_opus.so" "$MOD_DIR/"
cp -f "$SRC/codec_opus_config-en_US.xml" "$DOC_DIR/"
[[ -f "$SRC/manifest.xml" ]] && cp -f "$SRC/manifest.xml" "$DOC_DIR/"
chown asterisk:asterisk "$MOD_DIR/codec_opus.so" "$DOC_DIR/codec_opus_config-en_US.xml" 2>/dev/null || true

if ! grep -q '^load => codec_opus.so' /etc/asterisk/modules.conf 2>/dev/null; then
	echo 'load => codec_opus.so' >> /etc/asterisk/modules.conf
fi

asterisk -rx "module load codec_opus.so" 2>&1 || true
if asterisk -rx "module show like codec_opus" 2>/dev/null | grep -qE 'codec_opus\.so.*Running'; then
	echo "OK — codec_opus actif."
	asterisk -rx "core show translation" 2>/dev/null | grep -m1 opus || true
else
	echo "AVERTISSEMENT : codec_opus présent mais non chargé (ABI Asterisk ?)." >&2
	echo "  La messagerie WebRTC utilise Answer + force-ulaw en secours." >&2
fi
