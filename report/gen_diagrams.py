#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génération des diagrammes du rapport Asterisk / Asaphone (matplotlib → PNG).

Sources de vérité :
  - Architecture-VoIP-communication-composants.md
  - Plan-adressage-reseau-VoIP-QoS.md
  - S2/S3/S4 (extensions, IVR, sécurité)
  - docs/vpn.md, docs/trunk.md, docs/asaphone-group-conference.md
  - security/asaphone-onboarding-flow.md, security/cryptographic_implementation.md
  - webrtc/README.md, monitoring/docker-compose.yml, monitoring/README.md

Sortie : figures/*.png (300 dpi)
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse
from matplotlib.lines import Line2D

# ── Palette du rapport ────────────────────────────────────────────────────
BLUE = "#1B4F72"      # principal
TEAL = "#148F77"      # secondaire
PURPLE = "#7D3C98"    # accent
RED = "#C0392B"       # alerte / sécurité
GREY = "#5D6D7E"
LIGHT = "#F4F6F7"
BLUE_L = "#D6EAF8"
TEAL_L = "#D1F2EB"
PURPLE_L = "#EBDEF0"
RED_L = "#FADBD8"
YELL_L = "#FCF3CF"

FIGDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")
os.makedirs(FIGDIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "figure.dpi": 300,
    "savefig.dpi": 300,
})


def save(fig, name):
    path = os.path.join(FIGDIR, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("figure :", path)


def box(ax, x, y, w, h, text, fc=BLUE_L, ec=BLUE, fs=8.5, weight="normal",
        tc="#1B2631", rounded=True, lw=1.3, zorder=3):
    style = "round,pad=0.02,rounding_size=0.12" if rounded else "square,pad=0.02"
    p = FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fc, ec=ec, lw=lw, zorder=zorder)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, weight=weight, zorder=zorder + 1)
    return p


def arrow(ax, x1, y1, x2, y2, color=GREY, lw=1.4, style="-|>", ls="-",
          label=None, lfs=7.5, loff=(0, 0.12), lcolor=None, zorder=2):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13,
                        color=color, lw=lw, linestyle=ls, zorder=zorder,
                        shrinkA=2, shrinkB=2)
    ax.add_patch(a)
    if label:
        ax.text((x1 + x2) / 2 + loff[0], (y1 + y2) / 2 + loff[1], label,
                ha="center", va="bottom", fontsize=lfs,
                color=lcolor or color, zorder=zorder + 1)
    return a


def zone(ax, x, y, w, h, title, ec=GREY, fc="none", fs=9):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                       fc=fc, ec=ec, lw=1.1, linestyle=(0, (4, 2)), zorder=1)
    ax.add_patch(p)
    ax.text(x + 0.12, y + h - 0.02, title, ha="left", va="top",
            fontsize=fs, color=ec, weight="bold", zorder=2)


def new_ax(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    return fig, ax


# ═════════════════════════════════════════════════════════════════════════
# a) Architecture globale : Internet → pare-feu → PBX → VLAN / MGMT
# ═════════════════════════════════════════════════════════════════════════
def fig_architecture():
    fig, ax = new_ax(10.5, 7.2)

    # Internet
    zone(ax, 0.2, 8.35, 9.6, 1.5, "INTERNET", ec=GREY)
    box(ax, 0.6, 8.55, 2.3, 0.85, "Fournisseur SIP / PSTN\n(trunk — phase ultérieure)", fc=LIGHT, ec=GREY)
    box(ax, 3.4, 8.55, 2.4, 0.85, "Cloudflare Tunnel\n(provision API distante)", fc=PURPLE_L, ec=PURPLE)
    box(ax, 6.2, 8.55, 1.9, 0.85, "GitHub Pages\nbootstrap.json", fc=PURPLE_L, ec=PURPLE)
    box(ax, 8.3, 8.55, 1.3, 0.85, "Client 4G\nAsaphone", fc=TEAL_L, ec=TEAL)

    # Pare-feu
    zone(ax, 0.2, 6.9, 9.6, 1.15, "SÉCURITÉ PÉRIMÉTRIQUE", ec=RED)
    box(ax, 1.0, 7.05, 3.2, 0.7, "UFW (default deny incoming)\nrègles par CIDR autorisé", fc=RED_L, ec=RED)
    box(ax, 4.5, 7.05, 2.4, 0.7, "Fail2Ban\njail asterisk (nftables)", fc=RED_L, ec=RED)
    box(ax, 7.2, 7.05, 2.2, 0.7, "WireGuard wg0\nUDP 51820", fc=RED_L, ec=RED)

    # Zone serveur
    zone(ax, 0.2, 3.15, 9.6, 3.45, "ZONE SERVEUR — Ubuntu (VM), dual-homing", ec=BLUE)
    box(ax, 0.6, 4.85, 2.9, 1.35,
        "Asterisk 20 LTS (PJSIP)\nSIP 5060/5160 · TLS 5061/5161\nRTP 10000–20000 (DSCP EF)\nWSS 8089 (WebRTC)",
        fc=BLUE_L, ec=BLUE, weight="bold")
    box(ax, 3.8, 5.5, 2.5, 0.7, "FreePBX 17 (UI Apache)\nAMI · fwconsole", fc=BLUE_L, ec=BLUE)
    box(ax, 3.8, 4.75, 2.5, 0.6, "Mini-API provision PHP\n/provision (443)", fc=PURPLE_L, ec=PURPLE)
    box(ax, 6.6, 5.5, 1.55, 0.7, "IVR / AGI\nPython (7000/7010)", fc=TEAL_L, ec=TEAL)
    box(ax, 8.35, 5.5, 1.3, 0.7, "Queues\n7020 · MoH", fc=TEAL_L, ec=TEAL)
    box(ax, 6.6, 4.75, 1.55, 0.6, "ConfBridge\n6000 · 8001", fc=TEAL_L, ec=TEAL)
    box(ax, 8.35, 4.75, 1.3, 0.6, "Voicemail\n*81001…", fc=TEAL_L, ec=TEAL)
    box(ax, 0.6, 3.45, 2.9, 0.85, "MariaDB (base asterisk)\nCDR · provision_* · users", fc=LIGHT, ec=GREY)
    box(ax, 3.8, 3.45, 2.5, 0.85, "Monitoring Docker\nInfluxDB 2.7 · Grafana 11.4\nTelegraf AMI (host)", fc=PURPLE_L, ec=PURPLE)
    box(ax, 6.6, 3.45, 3.05, 0.85, "Enregistrements MixMonitor\n/var/spool/asterisk/monitor (NFS possible)", fc=LIGHT, ec=GREY)

    # Réseaux bas
    zone(ax, 0.2, 0.25, 4.6, 2.5, "LAN GESTION (MGMT) — ex. 192.168.1.0/24", ec=TEAL)
    box(ax, 0.5, 1.35, 1.9, 0.85, "Admin / UI FreePBX\nnavigateur HTTPS", fc=TEAL_L, ec=TEAL)
    box(ax, 2.6, 1.35, 1.9, 0.85, "Softphones LAN\n(Zoiper, Asaphone)\nex. 192.168.1.101", fc=TEAL_L, ec=TEAL)
    box(ax, 0.5, 0.45, 4.0, 0.6, "PBX patte gestion : ens33 — ex. 192.168.1.104 · pbx.local (mDNS)",
        fc=LIGHT, ec=TEAL, fs=7.5)

    zone(ax, 5.2, 0.25, 4.6, 2.5, "VLAN 10 VOIX — 10.10.10.0/24", ec=BLUE)
    box(ax, 5.5, 1.35, 1.9, 0.85, "Téléphones IP\nex. 10.10.10.50", fc=BLUE_L, ec=BLUE)
    box(ax, 7.6, 1.35, 1.9, 0.85, "Passerelle / SVI\n10.10.10.1", fc=BLUE_L, ec=BLUE)
    box(ax, 5.5, 0.45, 4.0, 0.6, "PBX patte voix : ens33.10 — 10.10.10.10 · QoS RTP DSCP EF (46)",
        fc=LIGHT, ec=BLUE, fs=7.5)

    # Flux
    arrow(ax, 1.75, 8.55, 2.0, 7.75, label="SIP trunk\n(futur)", lfs=7)
    arrow(ax, 4.6, 8.55, 4.9, 7.9, color=PURPLE)
    arrow(ax, 8.95, 8.55, 8.5, 7.75, color=TEAL, label="WG / WSS-relay", lfs=7, loff=(0.9, 0.0))
    arrow(ax, 2.6, 7.05, 2.05, 6.2, color=RED)
    arrow(ax, 5.7, 7.05, 5.05, 6.2, color=RED)
    arrow(ax, 8.3, 7.05, 6.9, 6.35, color=RED)
    arrow(ax, 2.05, 4.85, 2.05, 4.3, color=GREY, label="CDR (SQL)", lfs=7, loff=(0.75, -0.05))
    arrow(ax, 3.5, 5.2, 3.8, 5.2, color=BLUE)
    arrow(ax, 3.5, 5.55, 3.8, 5.85, color=BLUE)
    arrow(ax, 5.05, 4.3, 5.05, 4.75, color=PURPLE, label="AMI 5038", lfs=7, loff=(0.65, -0.3))
    arrow(ax, 3.5, 5.9, 6.6, 5.85, color=TEAL)
    arrow(ax, 2.5, 2.2, 2.3, 3.4, color=TEAL, label="SIP UDP/TLS · WSS · HTTPS", lfs=7, loff=(-0.1, 0.25))
    arrow(ax, 6.45, 2.2, 5.9, 3.4, color=BLUE, label="SIP/RTP (SRTP)", lfs=7, loff=(0.9, 0.2))

    ax.set_title("Architecture globale — Internet → pare-feu → Asterisk/FreePBX → LAN gestion + VLAN voix",
                 fontsize=11, weight="bold", color=BLUE, pad=12)
    save(fig, "fig-architecture-globale.png")


# ═════════════════════════════════════════════════════════════════════════
# b) Dual-homing MGMT / VLAN voix / VPN
# ═════════════════════════════════════════════════════════════════════════
def fig_dual_homing():
    fig, ax = new_ax(9.5, 5.6)

    box(ax, 3.4, 6.4, 3.2, 2.6,
        "SERVEUR PBX\nAsterisk 20 + FreePBX 17\n\nlocalnets PJSIP :\n192.168.1.0/24\n10.10.10.0/24\n10.200.0.0/24",
        fc=BLUE_L, ec=BLUE, weight="bold", fs=9)

    # Trois pattes
    box(ax, 0.3, 4.6, 2.6, 0.9, "ens33 — MGMT\nex. 192.168.1.104", fc=TEAL_L, ec=TEAL, weight="bold")
    box(ax, 3.7, 4.6, 2.6, 0.9, "ens33.10 — VLAN 10\n10.10.10.10", fc=BLUE_L, ec=BLUE, weight="bold")
    box(ax, 7.1, 4.6, 2.6, 0.9, "wg0 — WireGuard\n10.200.0.1", fc=PURPLE_L, ec=PURPLE, weight="bold")

    arrow(ax, 4.0, 6.4, 1.6, 5.5, color=TEAL)
    arrow(ax, 5.0, 6.4, 5.0, 5.5, color=BLUE)
    arrow(ax, 6.0, 6.4, 8.4, 5.5, color=PURPLE)

    zone(ax, 0.1, 0.4, 3.0, 3.6, "LAN gestion", ec=TEAL)
    box(ax, 0.35, 2.6, 2.5, 0.9, "UI FreePBX (HTTPS)\nprovision API LAN", fc=TEAL_L, ec=TEAL)
    box(ax, 0.35, 1.5, 2.5, 0.9, "Softphones bureau\n1001 UDP · 1003 WSS", fc=TEAL_L, ec=TEAL)
    box(ax, 0.35, 0.55, 2.5, 0.75, "windows-hosts.txt\n(pbx.local sans mDNS)", fc=LIGHT, ec=GREY, fs=7.5)

    zone(ax, 3.5, 0.4, 3.0, 3.6, "VLAN 10 voix (802.1Q)", ec=BLUE)
    box(ax, 3.75, 2.6, 2.5, 0.9, "Téléphones IP\nDHCP 10.10.10.50–200", fc=BLUE_L, ec=BLUE)
    box(ax, 3.75, 1.5, 2.5, 0.9, "QoS : RTP → DSCP EF\n(ufw before.rules mangle)", fc=BLUE_L, ec=BLUE)
    box(ax, 3.75, 0.55, 2.5, 0.75, "Passerelle 10.10.10.1\nswitch trunk VLAN 10", fc=LIGHT, ec=GREY, fs=7.5)

    zone(ax, 6.9, 0.4, 3.0, 3.6, "Accès distant (VPN)", ec=PURPLE)
    box(ax, 7.15, 2.6, 2.5, 0.9, "Client télétravail\n10.200.0.2 (tunnel)", fc=PURPLE_L, ec=PURPLE)
    box(ax, 7.15, 1.5, 2.5, 0.9, "Starlink / CGNAT :\nrelay WSS intégré\n→ WG vers 127.0.0.1:51820", fc=PURPLE_L, ec=PURPLE, fs=7.5)
    box(ax, 7.15, 0.55, 2.5, 0.75, "Box classique :\nforward UDP 51820", fc=LIGHT, ec=GREY, fs=7.5)

    arrow(ax, 1.6, 4.6, 1.6, 3.5, color=TEAL)
    arrow(ax, 5.0, 4.6, 5.0, 3.5, color=BLUE)
    arrow(ax, 8.4, 4.6, 8.4, 3.5, color=PURPLE)

    ax.text(5, 9.55, "", fontsize=1)
    ax.set_title("Dual-homing du PBX — patte gestion (MGMT), patte voix (VLAN 10) et tunnel WireGuard",
                 fontsize=11, weight="bold", color=BLUE, pad=10)
    save(fig, "fig-dual-homing.png")


# ═════════════════════════════════════════════════════════════════════════
# c) Use case Asaphone
# ═════════════════════════════════════════════════════════════════════════
def fig_usecase():
    fig, ax = new_ax(9.5, 6.4)

    def actor(x, y, name, color=BLUE):
        ax.add_patch(plt.Circle((x, y + 0.62), 0.16, fc="white", ec=color, lw=1.4, zorder=4))
        ax.plot([x, x], [y + 0.46, y + 0.12], color=color, lw=1.4, zorder=4)
        ax.plot([x - 0.22, x + 0.22], [y + 0.36, y + 0.36], color=color, lw=1.4, zorder=4)
        ax.plot([x, x - 0.16], [y + 0.12, y - 0.18], color=color, lw=1.4, zorder=4)
        ax.plot([x, x + 0.16], [y + 0.12, y - 0.18], color=color, lw=1.4, zorder=4)
        ax.text(x, y - 0.42, name, ha="center", fontsize=8.5, weight="bold", color=color)

    def usecase(x, y, w, h, text, ec=BLUE, fc=BLUE_L):
        e = Ellipse((x, y), w, h, fc=fc, ec=ec, lw=1.3, zorder=3)
        ax.add_patch(e)
        ax.text(x, y, text, ha="center", va="center", fontsize=7.8, zorder=4)
        return (x, y, w, h)

    # système
    zone(ax, 2.3, 0.35, 5.6, 9.3, "Système — PBX Asterisk/FreePBX + mini-API provision", ec=BLUE)

    actor(1.0, 7.6, "Utilisateur\nAsaphone", TEAL)
    actor(1.0, 3.1, "Utilisateur\nsoftphone SIP\n(Zoiper…)", GREY)
    actor(9.15, 5.4, "Administrateur\nFreePBX", PURPLE)

    u1 = usecase(4.0, 8.9, 2.9, 0.85, "S'enregistrer\n(e-mail + code)", PURPLE, PURPLE_L)
    u2 = usecase(6.4, 7.9, 2.9, 0.85, "Provisionner par QR\n(claim → credentials)", PURPLE, PURPLE_L)
    u3 = usecase(4.0, 7.0, 2.9, 0.85, "Se connecter au PBX\nREGISTER WSS 8089")
    u4 = usecase(6.4, 6.0, 2.9, 0.85, "Appel audio / vidéo\nDTLS-SRTP")
    u5 = usecase(4.0, 5.1, 2.9, 0.85, "Chat (SIP MESSAGE)")
    u6 = usecase(6.4, 4.1, 2.9, 0.85, "Messagerie vocale\n*81001…*81010")
    u7 = usecase(4.0, 3.2, 2.9, 0.85, "Appel de groupe\nConfBridge 6000 / grp-*")
    u8 = usecase(6.4, 2.2, 2.9, 0.85, "VPN WireGuard\nenroll / claim .conf", PURPLE, PURPLE_L)
    u9 = usecase(4.0, 1.15, 2.9, 0.85, "Appeler un poste\nclassique (UDP/SRTP)", GREY, LIGHT)

    for (x, y, w, h) in [u1, u3, u5, u7]:
        arrow(ax, 1.45, 7.55, x - w / 2 + 0.15, y, color=TEAL, lw=1.1, style="-")
    for (x, y, w, h) in [u2, u4, u6, u8]:
        arrow(ax, 1.45, 7.45, x - w / 2 + 0.1, y, color=TEAL, lw=1.1, style="-")
    arrow(ax, 1.5, 3.0, 2.65, 1.35, color=GREY, lw=1.1, style="-")
    arrow(ax, 1.5, 3.15, 5.05, 6.0, color=GREY, lw=1.1, style="-")   # reçoit appels
    arrow(ax, 8.75, 5.3, 7.75, 7.85, color=PURPLE, lw=1.1, style="-")
    arrow(ax, 8.75, 5.2, 5.4, 8.85, color=PURPLE, lw=1.1, style="-")

    # includes
    arrow(ax, 5.2, 8.65, 5.6, 8.3, color=GREY, lw=1.0, ls=":", label="« include »", lfs=6.5)
    arrow(ax, 6.4, 7.45, 5.0, 7.35, color=GREY, lw=1.0, ls=":", label="« include »", lfs=6.5)
    arrow(ax, 4.6, 2.85, 6.0, 2.5, color=GREY, lw=1.0, ls=":")

    ax.set_title("Cas d'utilisation Asaphone — provisionnement, enregistrement, appels, chat, messagerie, groupes",
                 fontsize=10.5, weight="bold", color=BLUE, pad=10)
    save(fig, "fig-usecase-asaphone.png")


# ═════════════════════════════════════════════════════════════════════════
# Helper séquence
# ═════════════════════════════════════════════════════════════════════════
def seq_diagram(title, actors, messages, name, w=10.5, h=7.0, note=None):
    """actors: [(label, color)], messages: [(i_from, i_to, label, color, style)]
    style: 'solid' | 'dashed' | 'both' (double flèche)"""
    fig, ax = plt.subplots(figsize=(w, h))
    n = len(actors)
    xs = [1 + i * (8.5 / max(n - 1, 1)) for i in range(n)]
    total = len(messages)
    top, bottom = 9.0, 0.6
    ax.set_xlim(0, 10.5)
    ax.set_ylim(0, 10.6)
    ax.axis("off")

    for (label, color), x in zip(actors, xs):
        box(ax, x - 0.85, top, 1.7, 0.9, label, fc="white", ec=color, weight="bold", fs=8.2)
        ax.plot([x, x], [bottom, top], color=color, lw=1.0, ls=(0, (5, 3)), zorder=1)

    step = (top - bottom - 0.4) / max(total, 1)
    y = top - 0.35
    for (i, j, label, color, style) in messages:
        y -= step
        x1, x2 = xs[i], xs[j]
        if style == "note":
            xm = (x1 + x2) / 2 if i != j else x1
            wd = max(abs(x2 - x1), 3.4)
            box(ax, xm - wd / 2, y - 0.18, wd, 0.52, label, fc=YELL_L, ec="#B7950B", fs=7.3)
            continue
        ls = "--" if style == "dashed" else "-"
        st = "<|-|>" if style == "both" else "-|>"
        arrow(ax, x1, y, x2, y, color=color, lw=1.4, ls=ls, style=st,
              label=label, lfs=7.4, loff=(0, 0.06))

    if note:
        ax.text(5.25, 0.15, note, ha="center", fontsize=7.5, color=GREY, style="italic")
    ax.set_title(title, fontsize=11, weight="bold", color=BLUE, pad=10)
    save(fig, name)


# d) Séquence appel 1001 ↔ 1003 (UDP/SRTP vs WSS/DTLS)
def fig_seq_call():
    actors = [("Poste 1001\nZoiper — SIP UDP 5060", GREY),
              ("Asterisk 20\nB2BUA (pont média)", BLUE),
              ("Asaphone 1003\nWebRTC — WSS 8089", TEAL)]
    m = [
        (0, 1, "REGISTER (UDP 5060, auth Digest, SRTP SDES)", GREY, "solid"),
        (2, 1, "REGISTER (wss://pbx.local:8089/ws, Digest)", TEAL, "solid"),
        (0, 1, "INVITE 1003 — SDP RTP/SAVP (PCMU/PCMA, G.722)", GREY, "solid"),
        (1, 2, "INVITE — SDP WebRTC : SAVPF, DTLS-SRTP, ICE, Opus", BLUE, "solid"),
        (2, 1, "180 Ringing → 200 OK (SDP answer)", TEAL, "dashed"),
        (1, 0, "200 OK (SDP answer classique)", BLUE, "dashed"),
        (0, 1, "ACK", GREY, "solid"),
        (1, 2, "ACK  ·  DTLS handshake + ICE checks", BLUE, "solid"),
        (0, 1, "Média : SRTP (SDES) — RTP UDP 10000–20000, DSCP EF", RED, "both"),
        (1, 2, "Média : DTLS-SRTP (WebRTC) — mêmes ports RTP", RED, "both"),
        (1, 1, "Asterisk termine chaque jambe et transcode si besoin\n(Opus ↔ G.711) — le média ne va jamais en direct", BLUE, "note"),
        (0, 1, "BYE", GREY, "solid"),
        (1, 2, "BYE  →  CDR écrit dans MariaDB", BLUE, "solid"),
    ]
    seq_diagram("Séquence — appel 1001 (UDP/SRTP) ↔ 1003 (WSS/DTLS-SRTP), pont B2BUA sur le PBX",
                actors, m, "fig-seq-appel-1001-1003.png",
                note="Sources : webrtc/README.md — signalisation UDP 5060 / WSS 8089, média RTP 10000–20000 chiffré SDES ou DTLS selon la jambe.")


# e) Séquence provision (QR → claim → session → WSS)
def fig_seq_provision():
    actors = [("Asaphone\n(client)", TEAL),
              ("GitHub Pages\nbootstrap.json", PURPLE),
              ("Mini-API provision\nApache/PHP (443)", BLUE),
              ("MariaDB +\nSMTP Gmail", GREY),
              ("Asterisk\nWSS 8089", RED)]
    m = [
        (0, 1, "GET bootstrap.json (discovery — toujours joignable)", PURPLE, "solid"),
        (1, 0, "api_lan · api_remote · wss_url · vpn.endpoint", PURPLE, "dashed"),
        (0, 2, "POST /api/v1/register.php  { email }", TEAL, "solid"),
        (2, 3, "INSERT provision_requests + mail code 6 chiffres (15 min)", BLUE, "solid"),
        (0, 2, "POST /api/v1/verify.php  { email, code }", TEAL, "solid"),
        (2, 3, "policy=auto : extension libre (pool 1003–1010)\n+ QR chiffré envoyé par e-mail", BLUE, "solid"),
        (0, 0, "Scan du QR reçu par e-mail (token one-shot, 24 h)", TEAL, "note"),
        (0, 2, "GET /api/v1/claim.php?token=…", TEAL, "solid"),
        (2, 0, "credentials : extension, secret, server, transport=wss, port=8089", BLUE, "dashed"),
        (0, 4, "REGISTER wss://pbx.local:8089/ws (Digest)", RED, "solid"),
        (4, 0, "200 OK — poste enregistré", RED, "dashed"),
        (0, 2, "POST /api/v1/consume.php { jti } → token révoqué (used=1)", TEAL, "solid"),
    ]
    seq_diagram("Séquence — provisionnement Asaphone : inscription e-mail → QR → claim → REGISTER WSS",
                actors, m, "fig-seq-provision.png",
                note="Source : security/asaphone-onboarding-flow.md — PROVISION_POLICY=auto ; hors LAN, api_remote (tunnel Cloudflare) remplace pbx.local.")


# f) Séquence appel de groupe ConfBridge
def fig_seq_confbridge():
    actors = [("Asaphone 1003\n(initiateur)", TEAL),
              ("Mini-API provision\ngroups / conference", PURPLE),
              ("Asterisk\nConfBridge", BLUE),
              ("Membres 1001, 1002\n(originate)", GREY)]
    m = [
        (0, 1, "POST groups/sync.php?ext=1003 + X-Provision-Jti\n{ id, title, members:[1001,1002,1003] }", PURPLE, "solid"),
        (1, 0, "call_uri = asaphone-grp-<slug>  (salle dédiée)", PURPLE, "dashed"),
        (0, 2, "INVITE call_uri (un seul appel SIP — le client ne mixe pas)", TEAL, "solid"),
        (2, 2, "Dialplan asaphone-conf-start → entre en ConfBridge", BLUE, "note"),
        (2, 1, "conf-invite.php auto (membres sauf appelant)", BLUE, "solid"),
        (1, 2, "Originate PJSIP/1001 · PJSIP/1002 → salle", PURPLE, "solid"),
        (2, 3, "Les postes sonnent, décrochent, rejoignent la salle", BLUE, "solid"),
        (2, 2, "ConfBridge mixe l'audio pour tous les participants", BLUE, "note"),
        (0, 1, "POST conference/invite.php { room, extensions:[1004] }\n(invitation en cours d'appel — phase 2)", PURPLE, "solid"),
        (1, 2, "Originate PJSIP/1004 → même salle", PURPLE, "solid"),
    ]
    seq_diagram("Séquence — appel de groupe : sync des groupes, ConfBridge et originate des membres",
                actors, m, "fig-seq-confbridge.png",
                note="Source : docs/asaphone-group-conference.md — salles 6000 (défaut), 6001–6099, asaphone-grp-* ; auth par ?ext= + header X-Provision-Jti.")


# g) Pipeline monitoring
def fig_monitoring_pipeline():
    fig, ax = new_ax(10.2, 5.2)

    zone(ax, 0.15, 5.7, 4.4, 3.9, "Hôte PBX", ec=BLUE)
    box(ax, 0.45, 7.6, 3.8, 1.15, "Asterisk 20\nAMI 127.0.0.1:5038 (user telegraf,\nwrite=command)", fc=BLUE_L, ec=BLUE, weight="bold")
    box(ax, 0.45, 6.0, 3.8, 1.1, "Logs :\n/var/log/asterisk/full\n/var/log/fail2ban.log", fc=LIGHT, ec=GREY)

    zone(ax, 0.15, 0.5, 4.4, 4.6, "Docker — network_mode: host", ec=PURPLE)
    box(ax, 0.45, 2.9, 3.8, 1.7,
        "Telegraf — voip-telegraf:1.33-ami\n[[inputs.exec]] ami_metrics.py (10 s)\n[[inputs.exec]] log_metrics.py (10 s)\n[[outputs.influxdb_v2]]",
        fc=PURPLE_L, ec=PURPLE, weight="bold", fs=8)
    box(ax, 0.45, 0.85, 3.8, 1.4,
        "Dockerfile : image telegraf:1.33\n+ scripts Python AMI\n(pas de plugin asterisk officiel)", fc=LIGHT, ec=GREY, fs=7.8)

    box(ax, 5.5, 5.9, 4.2, 1.7,
        "InfluxDB 2.7 (alpine) — voip-influxdb\norg « voip » · bucket « asterisk »\nmesure asterisk_core\nport 8086", fc=TEAL_L, ec=TEAL, weight="bold")
    box(ax, 5.5, 3.0, 4.2, 1.9,
        "Grafana 11.4.0 — voip-grafana\ndatasource InfluxDB-VoIP (Flux)\nprovisionnée + dashboard JSON\n« VoIP / Asterisk — monitoring »\nport 3000", fc=PURPLE_L, ec=PURPLE, weight="bold")
    box(ax, 5.5, 1.0, 4.2, 1.2,
        "Navigateur admin (LAN autorisé)\nhttp://pbx.local:3000 — dossier VoIP", fc=LIGHT, ec=GREY)

    arrow(ax, 2.35, 7.6, 2.35, 4.6, color=BLUE, label="AMI : core show channels\n(canaux, appels actifs)", lfs=7.3, loff=(1.35, -0.55))
    arrow(ax, 1.1, 6.0, 1.1, 4.6, color=GREY, label="lecture ro", lfs=7, loff=(-0.62, -0.5))
    arrow(ax, 4.25, 3.9, 5.5, 6.3, color=TEAL, label="line protocol\nHTTP 8086 + token", lfs=7.3, loff=(0.55, 0.0))
    arrow(ax, 7.6, 5.9, 7.6, 4.9, color=TEAL, label="requêtes Flux : from(bucket:\"asterisk\")", lfs=7.3, loff=(0, 0.05))
    arrow(ax, 7.6, 3.0, 7.6, 2.2, color=PURPLE, label="HTTP 3000 (UFW : LAN autorisés)", lfs=7.3, loff=(0, 0.03))

    ax.text(5.1, 0.2, "Prometheus absent — chaîne Telegraf → InfluxDB 2 → Grafana (Flux). "
                      "Secrets dans monitoring/.env (générés par phase3-gen-monitoring-env.sh).",
            ha="center", fontsize=7.4, color=GREY, style="italic")
    ax.set_title("Pipeline monitoring — Telegraf (AMI + logs) → InfluxDB 2 → Grafana",
                 fontsize=11, weight="bold", color=BLUE, pad=10)
    save(fig, "fig-monitoring-pipeline.png")


# h) Couches sécurité Phase 4
def fig_security_layers():
    fig, ax = new_ax(10.0, 6.0)
    layers = [
        ("L0", "Segmentation physique / L2", "VLAN 10 voix (10.10.10.0/24) séparé du MGMT — 802.1Q, QoS trust DSCP", "✓ déployé", TEAL),
        ("L1", "Transport réseau", "VPN WireGuard wg0 (10.200.0.0/24, UDP 51820) — relay WSS si CGNAT", "✓ déployé", TEAL),
        ("L2", "Pare-feu / anti-abus", "UFW default deny + règles par CIDR · Fail2Ban jail asterisk (logpath /var/log/asterisk/full)", "✓ Phase 4", TEAL),
        ("L3", "Administration web", "HTTPS Apache 443 (cert Certman) · session FreePBX · permissions GUI", "✓ déployé", TEAL),
        ("L4", "Signalisation SIP", "TLS 5061/5161 (pjsipcertid → certman) · WSS 8089 · auth Digest", "✓ partiel", "#B7950B"),
        ("L5", "Média audio/vidéo", "SRTP SDES (postes classiques) · DTLS-SRTP (WebRTC) — res_srtp requis", "✓ partiel", "#B7950B"),
        ("L6", "Provisionnement", "QR chiffré one-shot · claim token 24 h · consume/révocation jti · rate-limit", "✓ implémenté", TEAL),
        ("L7", "Données au repos", "Secrets chmod 600/640 hors Git · rotation ≥16 car. / 90 j · CDR MariaDB", "⚠ partiel", RED),
    ]
    y = 9.3
    for code, name, detail, state, sc in layers:
        box(ax, 0.2, y - 0.95, 0.85, 0.95, code, fc=BLUE, ec=BLUE, tc="white", weight="bold", fs=10)
        box(ax, 1.15, y - 0.95, 2.35, 0.95, name, fc=BLUE_L, ec=BLUE, weight="bold", fs=8.2)
        box(ax, 3.6, y - 0.95, 4.9, 0.95, detail, fc=LIGHT, ec=GREY, fs=7.5)
        box(ax, 8.6, y - 0.95, 1.2, 0.95, state, fc="white", ec=sc, tc=sc, weight="bold", fs=7.8)
        y -= 1.13
    ax.set_title("Matrice sécurité Phase 4 — modèle en couches L0 → L7 (état projet documenté)",
                 fontsize=11, weight="bold", color=BLUE, pad=10)
    ax.text(5.0, 0.12, "Source : security/cryptographic_implementation.md §2 — E2EE strict poste-à-poste non compatible avec le modèle B2BUA du PBX.",
            ha="center", fontsize=7.4, color=GREY, style="italic")
    save(fig, "fig-securite-couches.png")


# i) Comparatif Extension / Trunk SIP / VPN / VLAN / Cloudflare
def fig_comparatif():
    fig, ax = new_ax(10.6, 5.6)
    cols = ["", "Extension PJSIP", "Trunk SIP", "VPN WireGuard", "VLAN 10 (802.1Q)", "Tunnel Cloudflare"]
    rows = [
        ("Couche", "SIP (L7) — poste", "SIP (L7) — inter-PBX /\nopérateur", "IP (L3) — kernel", "Ethernet (L2) — switch", "HTTPS (L7) — sortant"),
        ("Relie quoi ?", "Poste ↔ PBX\n(1001–1010)", "PBX ↔ PSTN\nou autre PBX", "PC distant ↔ LAN PBX\n(10.200.0.0/24)", "Téléphones du site ↔ PBX\n(10.10.10.0/24)", "Internet ↔ mini-API\nprovision (443)"),
        ("Authentification", "REGISTER + secret\n(≥ 16 car.)", "Login/secret opérateur\nou identify IP", "Paires de clés\nWireGuard", "Aucune (tag VLAN\nsur ports switch)", "Tunnel sortant\n(pas de port entrant)"),
        ("Où configurer ?", "FreePBX → Extensions\n(scripts phase2)", "FreePBX → Trunks\n(apply-trunks.sh)", "OS Linux (wg0)\n+ site.env + UFW", "Switch + hyperviseur\n+ ens33.10", "cloudflared-provision\n.service (systemd)"),
        ("Softphone\ndistant ?", "Oui, via VPN\nou relay WSS", "Non", "Oui (télétravail)", "Non (site uniquement)", "Non (API HTTP\nseulement)"),
        ("État projet", "✓ production\n1001–1010", "Préconfiguré\n(secrets à fournir)", "✓ opérationnel\n(wg0 + enroll API)", "✓ OS prêt — trunk\nswitch à raccorder", "✓ au boot (mode\nquick trycloudflare)"),
    ]
    cw = [1.25, 1.87, 1.87, 1.87, 1.87, 1.87]
    ax.set_xlim(0, 10.75)
    x0, y0, rh = 0.15, 9.35, 1.42
    x = x0
    for c, wd in zip(cols, cw):
        box(ax, x, y0, wd - 0.06, 0.75, c, fc=BLUE if c else "white", ec=BLUE if c else "white",
            tc="white" if c else "black", weight="bold", fs=8)
        x += wd
    y = y0
    for r in rows:
        y -= rh
        x = x0
        for i, (cell, wd) in enumerate(zip(r, cw)):
            if i == 0:
                box(ax, x, y, wd - 0.06, rh - 0.08, cell, fc=BLUE_L, ec=BLUE, weight="bold", fs=7.6)
            else:
                fc = TEAL_L if r[0] == "État projet" else LIGHT
                box(ax, x, y, wd - 0.06, rh - 0.08, cell, fc=fc, ec=GREY, fs=6.9)
            x += wd
    ax.set_ylim(0.4, 10.4)
    ax.set_title("Comparatif — extension PJSIP, trunk SIP, VPN WireGuard, VLAN voix, tunnel Cloudflare",
                 fontsize=11, weight="bold", color=BLUE, pad=8)
    save(fig, "fig-comparatif-liaisons.png")


if __name__ == "__main__":
    fig_architecture()
    fig_dual_homing()
    fig_usecase()
    fig_seq_call()
    fig_seq_provision()
    fig_seq_confbridge()
    fig_monitoring_pipeline()
    fig_security_layers()
    fig_comparatif()
    print("Diagrammes générés dans", FIGDIR)
