#!/usr/bin/env bash
# Installe les hooks FreePBX hors /home (www-data ne traverse pas /home/asaph).
# Usage : sudo bash scripts/install-freepbx-reload-hooks.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $(id -u) -eq 0 ]] || { echo "Root requis." >&2; exit 1; }

chmod +x "$ROOT/scripts/freepbx-pre-reload.sh" "$ROOT/scripts/freepbx-post-reload.sh" \
	"$ROOT/scripts/align-pjsip-site.sh" "$ROOT/scripts/ensure-pjsip-extension.sh"

mkdir -p /var/lib/provision/log
chmod 1777 /var/lib/provision/log
touch /var/lib/provision/log/freepbx-pre-reload.log /var/lib/provision/log/freepbx-post-reload.log
chown www-data:www-data /var/lib/provision/log/*.log
chmod 666 /var/lib/provision/log/*.log

# Wrappers dans /usr/local/sbin (executables par www-data)
cat > /usr/local/sbin/asaphone-freepbx-pre-reload-root.sh <<EOF
#!/usr/bin/env bash
exec bash ${ROOT}/scripts/freepbx-pre-reload.sh
EOF
cat > /usr/local/sbin/asaphone-freepbx-post-reload-root.sh <<EOF
#!/usr/bin/env bash
exec bash ${ROOT}/scripts/freepbx-post-reload.sh
EOF
cat > /usr/local/sbin/asaphone-freepbx-pre-reload.sh <<'EOF'
#!/usr/bin/env bash
if [[ $(id -u) -ne 0 ]]; then
  exec sudo -n /usr/local/sbin/asaphone-freepbx-pre-reload-root.sh
fi
exec /usr/local/sbin/asaphone-freepbx-pre-reload-root.sh
EOF
cat > /usr/local/sbin/asaphone-freepbx-post-reload.sh <<'EOF'
#!/usr/bin/env bash
if [[ $(id -u) -ne 0 ]]; then
  exec sudo -n /usr/local/sbin/asaphone-freepbx-post-reload-root.sh
fi
exec /usr/local/sbin/asaphone-freepbx-post-reload-root.sh
EOF
chmod 755 /usr/local/sbin/asaphone-freepbx-*.sh

install -m 0440 "$ROOT/scripts/asaphone-pjsip-align.sudoers" /etc/sudoers.d/asaphone-pjsip-align
# Completer sudoers avec wrappers
cat > /etc/sudoers.d/asaphone-pjsip-align <<EOF
# Alignement PJSIP WebRTC + hooks Apply Config (www-data → root).
www-data ALL=(root) NOPASSWD: /usr/local/sbin/asaphone-freepbx-pre-reload-root.sh
www-data ALL=(root) NOPASSWD: /usr/local/sbin/asaphone-freepbx-post-reload-root.sh
www-data ALL=(root) NOPASSWD: ${ROOT}/scripts/ensure-pjsip-extension.sh
www-data ALL=(root) NOPASSWD: ${ROOT}/scripts/fix-cert-perms.sh
www-data ALL=(root) NOPASSWD: ${ROOT}/scripts/fix-asterisk-run-perms.sh
www-data ALL=(root) NOPASSWD: ${ROOT}/scripts/align-pjsip-site.sh
EOF
chmod 440 /etc/sudoers.d/asaphone-pjsip-align
visudo -c -f /etc/sudoers.d/asaphone-pjsip-align

fwconsole setting PRE_RELOAD /usr/local/sbin/asaphone-freepbx-pre-reload.sh
fwconsole setting POST_RELOAD /usr/local/sbin/asaphone-freepbx-post-reload.sh

# STUN + Strict RTP via sipsettings (persistant Apply Config)
bash "$ROOT/scripts/apply-rtp-relaxed.sh" || true

echo "OK — hooks FreePBX (chemin /usr/local/sbin, accessible www-data)"
echo "  PRE_RELOAD  = /usr/local/sbin/asaphone-freepbx-pre-reload.sh"
echo "  POST_RELOAD = /usr/local/sbin/asaphone-freepbx-post-reload.sh"
