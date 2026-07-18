#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génération des planches « console » du rapport (matplotlib → PNG) :

  A) Phases d'installation des outils (INSTALLATION.md + monitoring/docker-compose.yml)
  B) Monitoring en console (docker compose ps, logs Telegraf stylisés)
  C) Sortie console de lancement serveur-startup — reproduction fidèle de
     scripts/server-startup.sh + scripts/lib/startup-console.sh

Aucun secret, IP d'exemple documentées uniquement (192.168.1.80 / pbx.local
issues de network/windows-hosts.txt et bootstrap.json du dépôt).
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIGDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")
os.makedirs(FIGDIR, exist_ok=True)

# Palette terminal
T_BG = "#14181F"        # fond
T_BAR = "#232A35"       # barre de titre
T_FG = "#D5DBE3"        # texte normal
T_DIM = "#7B8794"       # gris (skip / info)
T_GREEN = "#5FD38D"     # OK
T_YELLOW = "#F2C94C"    # WARN / accent
T_CYAN = "#56C1D6"      # étapes
T_MAGENTA = "#C792EA"   # banner
T_RED = "#EB6F6F"
T_BLUE = "#6FA8DC"

MONO = "DejaVu Sans Mono"


def render_terminal(lines, name, title="asaph@pbx: ~", width=9.6, fontsize=7.6,
                    line_h_pt=11.5):
    """lines: liste de (texte, couleur) ou (texte, couleur, poids)."""
    n = len(lines)
    fig_h = 0.55 + n * line_h_pt / 72.0 + 0.25
    fig = plt.figure(figsize=(width, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # fond + barre de titre
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, fc=T_BG, ec="#3B4452", lw=1.2,
                               transform=ax.transAxes, zorder=0))
    bar_h = 0.38 / fig_h
    ax.add_patch(plt.Rectangle((0, 1 - bar_h), 1, bar_h, fc=T_BAR, ec="none",
                               transform=ax.transAxes, zorder=1))
    for i, c in enumerate(["#EB6F6F", "#F2C94C", "#5FD38D"]):
        ax.add_patch(plt.Circle((0.022 + i * 0.028, 1 - bar_h / 2), 0.09 / width / 3,
                                fc=c, ec="none", transform=ax.transAxes, zorder=2))
    ax.text(0.5, 1 - bar_h / 2, title, ha="center", va="center", color=T_DIM,
            fontsize=7.5, family=MONO, transform=ax.transAxes, zorder=2)

    top = 1 - bar_h - (0.14 / fig_h)
    step = (line_h_pt / 72.0) / fig_h
    for i, line in enumerate(lines):
        text, color = line[0], line[1]
        weight = line[2] if len(line) > 2 else "normal"
        ax.text(0.018, top - i * step, text, ha="left", va="top", color=color,
                fontsize=fontsize, family=MONO, weight=weight,
                transform=ax.transAxes, zorder=3)

    path = os.path.join(FIGDIR, name)
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    print("figure :", path)


# ═════════════════════════════════════════════════════════════════════════
# A) Phases d'installation (INSTALLATION.md)
# ═════════════════════════════════════════════════════════════════════════
def fig_install_prerequis():
    L = [
        ("ÉTAPE 1/6 — Prérequis OS et paquets système", T_YELLOW, "bold"),
        ("  Cible : Debian 12 (Bookworm) ou Ubuntu 22.04 LTS — accès root + systemd", T_DIM),
        ("", T_FG),
        ("$ sudo apt-get update", T_CYAN),
        ("$ sudo apt-get install -y \\", T_CYAN),
        ("    apache2 mariadb-server \\", T_FG),
        ("    ufw avahi-daemon \\", T_FG),
        ("    fail2ban \\", T_FG),
        ("    libsrtp2-dev \\", T_FG),
        ("    python3 \\", T_FG),
        ("    git curl", T_FG),
        ("", T_FG),
        ("$ apache2 -v", T_CYAN),
        ("Server version: Apache/2.4.x (Ubuntu)", T_FG),
        ("$ mariadb --version", T_CYAN),
        ("mariadb ... 10.6+ (Debian 12 : souvent 10.11)", T_FG),
        ("$ php -v", T_CYAN),
        ("PHP 8.2.x (cli)", T_FG),
        ("", T_FG),
        ("  ✓ Critère OK : apache2, mariadb, php, ufw, avahi, fail2ban installés", T_GREEN, "bold"),
    ]
    render_terminal(L, "console-install-1-prerequis.png", "Installation — prérequis (INSTALLATION.md)")


def fig_install_asterisk_freepbx():
    L = [
        ("ÉTAPE 2/6 — Asterisk 20 LTS  ·  ÉTAPE 3/6 — FreePBX 17", T_YELLOW, "bold"),
        ("  Installation via le guide officiel FreePBX (script Sangoma ou ISO Distro).", T_DIM),
        ("  Référence projet : Asterisk 20.18.2 (sources /usr/src/asterisk-20.18.2)", T_DIM),
        ("", T_FG),
        ("$ asterisk -V", T_CYAN),
        ("Asterisk 20.18.2", T_GREEN),
        ("", T_FG),
        ("$ fwconsole -V", T_CYAN),
        ("FreePBX 17.0.x", T_GREEN),
        ("", T_FG),
        ("  Module SRTP (WebRTC) — si compilation source sans libsrtp2 :", T_DIM),
        ("$ sudo bash serveur/scripts/install-asterisk-res-srtp.sh", T_CYAN),
        ("$ asterisk -rx \"module show like res_srtp\"", T_CYAN),
        ("res_srtp.so    Secure RTP (SRTP)    ... Running", T_GREEN),
        ("", T_FG),
        ("  ✓ Critère OK : asterisk -V → 20.x  ·  fwconsole -V → 17.x  ·  res_srtp chargé", T_GREEN, "bold"),
    ]
    render_terminal(L, "console-install-2-asterisk-freepbx.png",
                    "Installation — Asterisk 20 + FreePBX 17")


def fig_install_docker_monitoring():
    L = [
        ("ÉTAPE 4/6 — Docker + Compose v2  ·  ÉTAPE 5/6 — Stack monitoring", T_YELLOW, "bold"),
        ("", T_FG),
        ("$ sudo apt-get install -y docker.io docker-compose-plugin", T_CYAN),
        ("$ docker --version", T_CYAN),
        ("Docker version 24+ ...", T_FG),
        ("$ docker compose version", T_CYAN),
        ("Docker Compose version v2.x", T_FG),
        ("", T_FG),
        ("$ cd serveur/monitoring", T_CYAN),
        ("$ bash ../scripts/phase3-gen-monitoring-env.sh   # génère .env (secrets)", T_CYAN),
        ("$ docker compose pull", T_CYAN),
        ("influxdb    Pulled   influxdb:2.7-alpine", T_FG),
        ("grafana     Pulled   grafana/grafana:11.4.0", T_FG),
        ("telegraf    Pulled   telegraf:1.33 (base du build)", T_FG),
        ("$ docker compose build", T_CYAN),
        ("=> => naming to docker.io/library/voip-telegraf:1.33-ami        done", T_FG),
        ("$ docker compose up -d", T_CYAN),
        ("[+] Running 3/3", T_FG),
        (" ✔ Container voip-influxdb   Started", T_GREEN),
        (" ✔ Container voip-grafana    Started", T_GREEN),
        (" ✔ Container voip-telegraf   Started", T_GREEN),
        ("", T_FG),
        ("  ✓ Critère OK : Grafana http://pbx.local:3000 · InfluxDB http://pbx.local:8086", T_GREEN, "bold"),
    ]
    render_terminal(L, "console-install-3-docker-monitoring.png",
                    "Installation — Docker + stack monitoring (docker-compose.yml)")


def fig_install_systemd():
    L = [
        ("ÉTAPE 6/6 — Service systemd serveur-startup.service", T_YELLOW, "bold"),
        ("  Adapter d'abord ExecStart= au chemin réel du dépôt (INSTALLATION.md §2).", T_DIM),
        ("", T_FG),
        ("$ sudo install -m 0644 serveur/systemd/serveur-startup.service \\", T_CYAN),
        ("       /etc/systemd/system/serveur-startup.service", T_CYAN),
        ("$ sudo systemctl daemon-reload", T_CYAN),
        ("$ sudo systemctl enable --now serveur-startup.service", T_CYAN),
        ("Created symlink /etc/systemd/system/multi-user.target.wants/", T_FG),
        ("  serveur-startup.service → /etc/systemd/system/serveur-startup.service.", T_FG),
        ("", T_FG),
        ("$ systemctl status serveur-startup.service --no-pager -l", T_CYAN),
        ("● serveur-startup.service - Demarrage PBX (FreePBX/Asterisk + reseau site)", T_FG),
        ("     Loaded: loaded (/etc/systemd/system/serveur-startup.service; enabled)", T_FG),
        ("     Active: active (exited) — journal : /var/log/serveur-startup.log", T_GREEN),
        ("", T_FG),
        ("  Optionnel documenté : WireGuard (docs/implement-VPN.md), tunnel Cloudflare", T_DIM),
        ("  (install-provision-tunnel.sh), Apache HTTPS (enable-apache-https.sh).", T_DIM),
        ("", T_FG),
        ("  ✓ Critère OK : service enabled · log /var/log/serveur-startup.log alimenté", T_GREEN, "bold"),
    ]
    render_terminal(L, "console-install-4-systemd.png",
                    "Installation — service systemd serveur-startup")


# ═════════════════════════════════════════════════════════════════════════
# B) Monitoring en console
# ═════════════════════════════════════════════════════════════════════════
def fig_monitoring_ps():
    L = [
        ("$ cd /home/asaph/Documents/serveur/monitoring && docker compose ps", T_CYAN),
        ("NAME            IMAGE                    STATUS          PORTS", T_DIM),
        ("voip-influxdb   influxdb:2.7-alpine      Up (healthy)    0.0.0.0:8086->8086/tcp", T_GREEN),
        ("voip-grafana    grafana/grafana:11.4.0   Up              0.0.0.0:3000->3000/tcp", T_GREEN),
        ("voip-telegraf   voip-telegraf:1.33-ami   Up              network_mode: host", T_GREEN),
        ("", T_FG),
        ("$ docker compose logs --tail 6 telegraf", T_CYAN),
        ("voip-telegraf  | I! Starting Telegraf 1.33.0", T_FG),
        ("voip-telegraf  | I! Loaded inputs: exec (2x: ami_metrics.py, log_metrics.py)", T_FG),
        ("voip-telegraf  | I! Loaded outputs: influxdb_v2", T_FG),
        ("voip-telegraf  | I! [agent] interval:10s, flush_interval:10s, host \"freepbx\"", T_FG),
        ("voip-telegraf  | D! ami_metrics: AMI login 127.0.0.1:5038 user=telegraf OK", T_GREEN),
        ("voip-telegraf  | D! asterisk_core channels=2i,calls_active=1i → bucket asterisk", T_GREEN),
        ("", T_FG),
        ("  Rappel ports : Grafana → http://pbx.local:3000 (dossier VoIP)", T_YELLOW),
        ("                 InfluxDB 2 → http://pbx.local:8086 (org voip, bucket asterisk)", T_YELLOW),
        ("  UFW : 3000/tcp et 8086/tcp ouverts uniquement depuis les LAN autorisés.", T_DIM),
    ]
    render_terminal(L, "console-monitoring-cli.png",
                    "Monitoring CLI — docker compose (monitoring/README.md)")


# ═════════════════════════════════════════════════════════════════════════
# C) serveur-startup — reproduction fidèle du déroulé
# ═════════════════════════════════════════════════════════════════════════
BAR_FULL = "█" * 36


def bar(cur, total):
    filled = cur * 36 // total
    return "█" * filled + "░" * (36 - filled)


def progress_block(cur, total, label):
    pct = cur * 100 // total
    return [
        ("  ┌─ Lancement ─────────────────────────────────────────────────────────┐", T_CYAN),
        (f"  │ [{bar(cur, total)}] {pct}%", T_CYAN, "bold"),
        (f"  │ étape {cur}/{total}", T_DIM),
        (f"  │ ▸ {label}", T_CYAN),
        ("  └──────────────────────────────────────────────────────────────────────┘", T_CYAN),
    ]


def fig_startup_banner():
    L = [
        ("$ sudo systemctl start serveur-startup.service", T_CYAN),
        ("$ sudo tail -f /var/log/serveur-startup.log", T_CYAN),
        ("", T_FG),
        ("╔══════════════════════════════════════════════════════════════════════════╗", T_FG),
        ("║                                                                          ║", T_FG),
        ("║     █▀▀█ █▀▀█ ▄▀▄ ▀▄▀ █▀▀█   ░   █▀▄▀█ █▀▀█ █▀▀█ █▀▀█                    ║", T_MAGENTA, "bold"),
        ("║     ▀▄▀█ █▄▄█ █▀█ ░░█ █▄▄█   ░   █ ▀ █ █▄▄█ █▄▄█ ░░░                    ║", T_MAGENTA, "bold"),
        ("║                                                                          ║", T_FG),
        ("║                          ▀▄▀  A S A P H O N E  ▄▀▀                        ║", T_YELLOW, "bold"),
        ("║                                                                          ║", T_FG),
        ("║              FreePBX  ·  Provision  ·  VoIP  ·  VPN WireGuard              ║", T_CYAN),
        ("║                                                                          ║", T_FG),
        ("╚══════════════════════════════════════════════════════════════════════════╝", T_FG),
        ("", T_FG),
        ("  samedi 18 juillet 2026 — 08:00:12", T_FG, "bold"),
        ("  │ LAN / FreePBX / Apache  → démarrent sans Internet", T_DIM),
        ("  │ Cloudflare · GitHub · VPN distant  → nécessitent Internet", T_DIM),
        ("  │ Journal complet  → /var/log/serveur-startup.log", T_DIM),
        ("", T_FG),
    ] + progress_block(1, 10, "FreePBX chown.conf (VM + clés TLS + run) (optionnel — Internet ou réseau)") + [
        ("▶ FreePBX chown.conf (VM + clés TLS + run) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ FreePBX chown.conf (VM + clés TLS + run)", T_GREEN, "bold"),
        ("", T_FG),
        ("▶ Permissions GUI FreePBX (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ Permissions GUI FreePBX", T_GREEN, "bold"),
        ("", T_FG),
        ("▶ Permissions certificats TLS (pre-start) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ Permissions certificats TLS (pre-start)", T_GREEN, "bold"),
    ]
    render_terminal(L, "console-startup-1-banner.png",
                    "serveur-startup — banner + cœur PBX (1/3)", fontsize=7.2)


def fig_startup_core():
    L = [
        ("▶ FreePBX (fwconsole start) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("Running FreePBX startup...", T_FG),
        ("Starting Asterisk...", T_FG),
        ("  ✓ FreePBX (fwconsole start)", T_GREEN, "bold"),
        ("", T_FG),
        ("▶ WSS TLS 8089 (certs + reload) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ WSS TLS 8089 (certs + reload)", T_GREEN, "bold"),
        ("", T_FG),
        ("▶ Permissions /var/run/asterisk (reload.lock + ctl) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ Permissions /var/run/asterisk (reload.lock + ctl)", T_GREEN, "bold"),
        ("", T_FG),
        ("▶ Permissions spool messagerie (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ Permissions spool messagerie", T_GREEN, "bold"),
        ("", T_FG),
    ] + progress_block(5, 10, "Sessions PHP") + [
        ("▶ Sessions PHP", T_CYAN, "bold"),
        ("  ✓ Sessions PHP", T_GREEN, "bold"),
        ("", T_FG),
        ("▶ Apache (restart)", T_CYAN, "bold"),
        ("  ✓ Apache (restart)", T_GREEN, "bold"),
        ("", T_FG),
        ("▶ Profil réseau site (UFW, mDNS, localnets)", T_CYAN, "bold"),
        ("  ✓ Profil réseau site", T_GREEN, "bold"),
        ("", T_FG),
        ("▶ Permissions /var/run/asterisk (post-réseau) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ Permissions /var/run/asterisk (post-réseau)", T_GREEN, "bold"),
        ("", T_FG),
        ("  ○ Tailscale (désactivé — utiliser wg-wss-relay)", T_DIM),
        ("", T_FG),
        ("▶ Relais WG/WebSocket (Starlink 4G) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ Relais WG/WebSocket (Starlink 4G)", T_GREEN, "bold"),
        ("▶ URL tunnel WG relay (trycloudflare) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ URL tunnel WG relay (trycloudflare)", T_GREEN, "bold"),
    ]
    render_terminal(L, "console-startup-2-coeur.png",
                    "serveur-startup — cœur PBX + réseau (2/3)", fontsize=7.2)


def fig_startup_summary():
    L = [
        ("▶ Cloudflare tunnel (provision API distante)", T_CYAN, "bold"),
        ("  │ mode quick — URL trycloudflare rafraîchie", T_DIM),
        ("▶ URL trycloudflare (refresh-tunnel-url) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ URL trycloudflare (refresh-tunnel-url)", T_GREEN, "bold"),
        ("", T_FG),
        ("▶ Sync bootstrap (api_remote + relay WSS) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ Sync bootstrap (api_remote + relay WSS)", T_GREEN, "bold"),
        ("", T_FG),
        ("  ○ Publication GitHub (GITHUB_BOOTSTRAP_PUBLISH≠yes)", T_DIM),
        ("", T_FG),
        ("▶ Apache HTTPS (443) (optionnel — Internet ou réseau)", T_CYAN, "bold"),
        ("  ✓ Apache HTTPS (443)", T_GREEN, "bold"),
        ("", T_FG),
        ("╔══════════════════════════════════════════════════════════════════════════╗", T_FG),
        ("  DÉMARRAGE TERMINÉ", T_GREEN, "bold"),
        ("╚══════════════════════════════════════════════════════════════════════════╝", T_FG),
        ("", T_FG),
        ("  │ Interface LAN   : 192.168.1.80  (pbx.local)", T_DIM),
        ("  │ FreePBX         : https://pbx.local", T_DIM),
        ("  │ Provision API   : https://pbx.local/provision", T_DIM),
        ("  │ Asaphone login  : POST …/api/v1/reconnect.php", T_DIM),
        ("  │ API distante    : https://<tunnel>.trycloudflare.com/provision", T_DIM),
        ("  │ Alertes         : 0 avertissement(s), 2 étape(s) ignorée(s)", T_DIM),
        ("  │ Astuce dev      : asterisk -rx \"pjsip show contacts\"", T_DIM),
        ("  │                  sudo bash scripts/sync-global-config.sh", T_DIM),
        ("", T_FG),
    ] + progress_block(10, 10, "terminé") + [
        ("", T_FG),
        ("serveur-startup: OK 2026-07-18T08:01:04+01:00", T_GREEN, "bold"),
    ]
    render_terminal(L, "console-startup-3-resume.png",
                    "serveur-startup — Internet optionnel + résumé (3/3)", fontsize=7.2)


if __name__ == "__main__":
    fig_install_prerequis()
    fig_install_asterisk_freepbx()
    fig_install_docker_monitoring()
    fig_install_systemd()
    fig_monitoring_ps()
    fig_startup_banner()
    fig_startup_core()
    fig_startup_summary()
    print("Planches console générées dans", FIGDIR)
