#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagrammes du rapport ASAPHONE — matplotlib → PNG 300 dpi.
Style : cartes à bandeau, ombres portées, zones teintées, étiquettes pastille.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse, Circle

# ── Palette ───────────────────────────────────────────────────────────────
BLUE = "#1B4F72"
BLUE_D = "#123B5C"
TEAL = "#148F77"
PURPLE = "#7D3C98"
RED = "#C0392B"
AMBER = "#B7950B"
GREY = "#5D6D7E"
INK = "#22313F"
LIGHT = "#F4F6F7"
BLUE_L = "#EAF2F9"
TEAL_L = "#E8F6F1"
PURPLE_L = "#F3EBF8"
RED_L = "#FBEEEC"
YELL_L = "#FCF6E3"
SHADOW = "#8FA1AF"

FIGDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")
os.makedirs(FIGDIR, exist_ok=True)

plt.rcParams.update({
    "font.family": ["Ubuntu", "DejaVu Sans"],
    "font.size": 9,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "text.color": INK,
})


def save(fig, name):
    path = os.path.join(FIGDIR, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white", pad_inches=0.12)
    plt.close(fig)
    print("figure :", path)


def new_ax(w, h, xmax=10, ymax=10):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.axis("off")
    return fig, ax


def title(ax, text, x=5.0, y=None, fs=12):
    ax.set_title(text, fontsize=fs, weight="bold", color=BLUE_D, pad=14,
                 fontfamily=["Ubuntu", "DejaVu Sans"])


# ── Briques visuelles ─────────────────────────────────────────────────────

def _shadow(ax, x, y, w, h, style, z, dx=0.045, dy=0.05):
    p = FancyBboxPatch((x + dx, y - dy), w, h, boxstyle=style,
                       fc=SHADOW, ec="none", alpha=0.30, zorder=z)
    ax.add_patch(p)


def box(ax, x, y, w, h, text, fc=BLUE_L, ec=BLUE, fs=8.5, weight="normal",
        tc=INK, lw=1.1, zorder=3, shadow=True, radius=0.10):
    """Carte simple arrondie avec ombre portée douce."""
    style = f"round,pad=0.02,rounding_size={radius}"
    if shadow:
        _shadow(ax, x, y, w, h, style, zorder - 1)
    p = FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fc, ec=ec, lw=lw, zorder=zorder)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, weight=weight, zorder=zorder + 1, linespacing=1.35)
    return p


def card(ax, x, y, w, h, head, body, color=BLUE, fs_head=8.6, fs_body=7.7,
         zorder=3, head_ratio=None):
    """Carte à bandeau : entête colorée + corps blanc."""
    style = "round,pad=0.02,rounding_size=0.10"
    _shadow(ax, x, y, w, h, style, zorder - 1)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style,
                                fc="white", ec=color, lw=1.2, zorder=zorder))
    hh = head_ratio if head_ratio else min(0.62, h * 0.42)
    ax.add_patch(FancyBboxPatch((x, y + h - hh), w, hh,
                                boxstyle="round,pad=0.02,rounding_size=0.10",
                                fc=color, ec=color, lw=1.2, zorder=zorder + 1))
    # masque du bas de l'entête pour angles droits côté corps
    ax.add_patch(plt.Rectangle((x, y + h - hh), w, hh * 0.45,
                               fc=color, ec="none", zorder=zorder + 1))
    ax.text(x + w / 2, y + h - hh / 2, head, ha="center", va="center",
            fontsize=fs_head, color="white", weight="bold", zorder=zorder + 2)
    ax.text(x + w / 2, y + (h - hh) / 2, body, ha="center", va="center",
            fontsize=fs_body, color=INK, zorder=zorder + 2, linespacing=1.45)


def chip(ax, x, y, text, color, fs=8.0, zorder=6):
    ax.text(x, y, text, ha="left", va="center", fontsize=fs, color="white",
            weight="bold", zorder=zorder,
            bbox=dict(boxstyle="round,pad=0.32", fc=color, ec="none"))


def zone(ax, x, y, w, h, ttl, color=GREY, alpha=0.35, fs=8.4):
    """Zone teintée arrondie avec titre en pastille."""
    fills = {BLUE: BLUE_L, TEAL: TEAL_L, PURPLE: PURPLE_L, RED: RED_L, GREY: LIGHT}
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.16",
                                fc=fills.get(color, LIGHT), ec=color, lw=1.0,
                                alpha=alpha, zorder=1))
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.02,rounding_size=0.16",
                                fc="none", ec=color, lw=1.0, alpha=0.75, zorder=1))
    chip(ax, x + 0.22, y + h, ttl, color, fs=fs)


def arrow(ax, x1, y1, x2, y2, color=GREY, lw=1.5, style="-|>", ls="-",
          label=None, lfs=7.3, loff=(0, 0), rad=0.0, zorder=2, pill=True):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
                        color=color, lw=lw, linestyle=ls, zorder=zorder,
                        shrinkA=3, shrinkB=3,
                        connectionstyle=f"arc3,rad={rad}", capstyle="round")
    ax.add_patch(a)
    if label:
        bx = dict(boxstyle="round,pad=0.28", fc="white", ec=color, lw=0.7) if pill else None
        ax.text((x1 + x2) / 2 + loff[0], (y1 + y2) / 2 + loff[1], label,
                ha="center", va="center", fontsize=lfs, color=color,
                weight="bold", zorder=zorder + 2, bbox=bx, linespacing=1.3)
    return a


# ═════════════════════════════════════════════════════════════════════════
# a) Architecture globale
# ═════════════════════════════════════════════════════════════════════════
def fig_architecture():
    fig, ax = new_ax(10.8, 7.6)

    zone(ax, 0.2, 8.30, 9.6, 1.42, "INTERNET", GREY)
    box(ax, 0.55, 8.52, 2.30, 0.92, "Fournisseur SIP / PSTN\n(trunk — phase ultérieure)", fc="white", ec=GREY, fs=7.6)
    box(ax, 3.10, 8.52, 2.45, 0.92, "Cloudflare Tunnel\nAPI provision distante", fc="white", ec=PURPLE, fs=7.6)
    box(ax, 5.80, 8.52, 2.05, 0.92, "GitHub Pages\nbootstrap.json", fc="white", ec=PURPLE, fs=7.6)
    box(ax, 8.10, 8.52, 1.50, 0.92, "Client 4G\nAsaphone", fc="white", ec=TEAL, fs=7.6)

    zone(ax, 0.2, 6.78, 9.6, 1.16, "SÉCURITÉ PÉRIMÉTRIQUE", RED)
    box(ax, 0.95, 6.96, 3.25, 0.74, "UFW — default deny incoming\nrègles par CIDR autorisé", fc="white", ec=RED, fs=7.5)
    box(ax, 4.45, 6.96, 2.45, 0.74, "Fail2Ban\njail asterisk (nftables)", fc="white", ec=RED, fs=7.5)
    box(ax, 7.15, 6.96, 2.25, 0.74, "WireGuard wg0\nUDP 51820", fc="white", ec=RED, fs=7.5)

    zone(ax, 0.2, 3.05, 9.6, 3.36, "ZONE SERVEUR — VM Ubuntu, dual-homing", BLUE, alpha=0.25)
    card(ax, 0.55, 4.78, 3.00, 1.44,
         "Asterisk 20 LTS · PJSIP",
         "SIP 5060/5160 · TLS 5061/5161\nRTP 10000–20000 (DSCP EF)\nWSS 8089 (WebRTC)",
         color=BLUE, head_ratio=0.48)
    card(ax, 3.85, 5.42, 2.55, 0.86, "FreePBX 17", "UI Apache · AMI · fwconsole",
         color=BLUE, head_ratio=0.42, fs_head=8.0)
    card(ax, 3.85, 4.42, 2.55, 0.82, "Mini-API provision", "PHP · /provision (443)",
         color=PURPLE, head_ratio=0.42, fs_head=8.0)
    box(ax, 6.65, 5.52, 1.55, 0.72, "IVR / AGI\n7000 · 7010", fc=TEAL_L, ec=TEAL, fs=7.5)
    box(ax, 8.38, 5.52, 1.28, 0.72, "Files ACD\n7020", fc=TEAL_L, ec=TEAL, fs=7.5)
    box(ax, 6.65, 4.62, 1.55, 0.72, "ConfBridge\n6000 · 8001", fc=TEAL_L, ec=TEAL, fs=7.5)
    box(ax, 8.38, 4.62, 1.28, 0.72, "Voicemail\n*81001…", fc=TEAL_L, ec=TEAL, fs=7.5)
    box(ax, 0.55, 3.38, 3.00, 0.86, "MariaDB — base asterisk\nCDR · provision_* · users", fc="white", ec=GREY, fs=7.5)
    box(ax, 3.85, 3.38, 2.55, 0.86, "Monitoring Docker\nInfluxDB 2.7 · Grafana 11.4\nTelegraf AMI", fc="white", ec=PURPLE, fs=7.1)
    box(ax, 6.65, 3.38, 3.01, 0.86, "Enregistrements MixMonitor\n/var/spool/asterisk/monitor", fc="white", ec=GREY, fs=7.5)

    zone(ax, 0.2, 0.22, 4.62, 2.44, "LAN GESTION — ex. 192.168.1.0/24", TEAL)
    box(ax, 0.50, 1.32, 1.95, 0.88, "Admin\nUI FreePBX (HTTPS)", fc="white", ec=TEAL, fs=7.5)
    box(ax, 2.62, 1.32, 1.95, 0.88, "Softphones LAN\nZoiper · Asaphone", fc="white", ec=TEAL, fs=7.5)
    box(ax, 0.50, 0.42, 4.07, 0.62, "Patte gestion : ens33 · pbx.local (mDNS)", fc=TEAL_L, ec=TEAL, fs=7.4)

    zone(ax, 5.18, 0.22, 4.62, 2.44, "VLAN 10 VOIX — 10.10.10.0/24", BLUE)
    box(ax, 5.48, 1.32, 1.95, 0.88, "Téléphones IP\nDHCP .50 – .200", fc="white", ec=BLUE, fs=7.5)
    box(ax, 7.60, 1.32, 1.95, 0.88, "Passerelle / SVI\n10.10.10.1", fc="white", ec=BLUE, fs=7.5)
    box(ax, 5.48, 0.42, 4.07, 0.62, "Patte voix : ens33.10 — 10.10.10.10 · DSCP EF", fc=BLUE_L, ec=BLUE, fs=7.4)

    arrow(ax, 1.70, 8.52, 2.10, 7.72, color=GREY, ls="--", label="SIP trunk (futur)", lfs=6.8, loff=(-0.75, 0.06))
    arrow(ax, 4.32, 8.52, 4.85, 7.72, color=PURPLE)
    arrow(ax, 8.85, 8.52, 8.35, 7.72, color=TEAL, label="WG / relais WSS", lfs=6.8, loff=(1.0, 0.05))
    arrow(ax, 2.55, 6.96, 2.05, 6.24, color=RED)
    arrow(ax, 5.65, 6.96, 5.10, 6.30, color=RED)
    arrow(ax, 8.25, 6.96, 7.20, 6.26, color=RED)
    arrow(ax, 2.05, 4.78, 2.05, 4.26, color=GREY, label="CDR", lfs=6.8, loff=(0.55, 0))
    arrow(ax, 3.57, 5.20, 3.85, 5.00, color=PURPLE)
    arrow(ax, 3.57, 5.62, 3.85, 5.80, color=BLUE)
    arrow(ax, 5.10, 4.26, 5.10, 4.42, color=PURPLE, label="AMI 5038", lfs=6.8, loff=(1.05, -0.02))
    arrow(ax, 6.42, 5.86, 6.65, 5.86, color=TEAL)
    arrow(ax, 2.45, 2.22, 2.25, 3.32, color=TEAL, label="SIP · WSS · HTTPS", lfs=6.8, loff=(1.35, -0.34))
    arrow(ax, 6.40, 2.22, 5.95, 3.32, color=BLUE, label="SIP / SRTP", lfs=6.8, loff=(1.1, -0.36))

    title(ax, "Architecture globale — de l'Internet au VLAN voix")
    save(fig, "fig-architecture-globale.png")


# ═════════════════════════════════════════════════════════════════════════
# b) Dual-homing
# ═════════════════════════════════════════════════════════════════════════
def fig_dual_homing():
    fig, ax = new_ax(9.8, 5.9)

    card(ax, 3.30, 6.35, 3.40, 2.75,
         "SERVEUR PBX",
         "Asterisk 20 + FreePBX 17\n\nlocalnets PJSIP :\n192.168.1.0/24 · 10.10.10.0/24\n10.200.0.0/24",
         color=BLUE, head_ratio=0.62, fs_head=9.4, fs_body=8.0)

    box(ax, 0.30, 4.55, 2.60, 0.95, "ens33 — MGMT\nex. 192.168.1.104", fc="white", ec=TEAL, weight="bold", fs=8.2)
    box(ax, 3.70, 4.55, 2.60, 0.95, "ens33.10 — VLAN 10\n10.10.10.10", fc="white", ec=BLUE, weight="bold", fs=8.2)
    box(ax, 7.10, 4.55, 2.60, 0.95, "wg0 — WireGuard\n10.200.0.1", fc="white", ec=PURPLE, weight="bold", fs=8.2)

    arrow(ax, 3.95, 6.35, 1.60, 5.55, color=TEAL, rad=0.12)
    arrow(ax, 5.00, 6.35, 5.00, 5.55, color=BLUE)
    arrow(ax, 6.05, 6.35, 8.40, 5.55, color=PURPLE, rad=-0.12)

    zone(ax, 0.10, 0.35, 3.00, 3.60, "LAN gestion", TEAL)
    box(ax, 0.35, 2.55, 2.50, 0.92, "UI FreePBX (HTTPS)\nAPI provision LAN", fc="white", ec=TEAL, fs=7.6)
    box(ax, 0.35, 1.48, 2.50, 0.92, "Softphones bureau\n1001 UDP · 1003 WSS", fc="white", ec=TEAL, fs=7.6)
    box(ax, 0.35, 0.55, 2.50, 0.76, "pbx.local sans mDNS :\nfichier hosts Windows", fc=LIGHT, ec=GREY, fs=7.2)

    zone(ax, 3.50, 0.35, 3.00, 3.60, "VLAN 10 voix — 802.1Q", BLUE)
    box(ax, 3.75, 2.55, 2.50, 0.92, "Téléphones IP\nDHCP 10.10.10.50–200", fc="white", ec=BLUE, fs=7.6)
    box(ax, 3.75, 1.48, 2.50, 0.92, "QoS : RTP → DSCP EF\n(mangle netfilter)", fc="white", ec=BLUE, fs=7.6)
    box(ax, 3.75, 0.55, 2.50, 0.76, "Passerelle 10.10.10.1\ntrunk switch VLAN 10", fc=LIGHT, ec=GREY, fs=7.2)

    zone(ax, 6.90, 0.35, 3.00, 3.60, "Accès distant — VPN", PURPLE)
    box(ax, 7.15, 2.55, 2.50, 0.92, "Client télétravail\n10.200.0.2 (tunnel)", fc="white", ec=PURPLE, fs=7.6)
    box(ax, 7.15, 1.48, 2.50, 0.92, "Starlink / CGNAT :\nrelais WSS intégré\n→ WG 127.0.0.1:51820", fc="white", ec=PURPLE, fs=7.0)
    box(ax, 7.15, 0.55, 2.50, 0.76, "Box classique :\nforward UDP 51820", fc=LIGHT, ec=GREY, fs=7.2)

    arrow(ax, 1.60, 4.55, 1.60, 3.62, color=TEAL)
    arrow(ax, 5.00, 4.55, 5.00, 3.62, color=BLUE)
    arrow(ax, 8.40, 4.55, 8.40, 3.62, color=PURPLE)

    title(ax, "Dual-homing du PBX — gestion, voix et tunnel VPN")
    save(fig, "fig-dual-homing.png")


# ═════════════════════════════════════════════════════════════════════════
# c) Use case Asaphone
# ═════════════════════════════════════════════════════════════════════════
def fig_usecase():
    fig, ax = new_ax(9.8, 6.6)

    def actor(x, y, name, color=BLUE):
        ax.add_patch(Circle((x, y + 0.62), 0.17, fc="white", ec=color, lw=1.6, zorder=4))
        ax.plot([x, x], [y + 0.45, y + 0.10], color=color, lw=1.6, zorder=4, solid_capstyle="round")
        ax.plot([x - 0.24, x + 0.24], [y + 0.35, y + 0.35], color=color, lw=1.6, zorder=4, solid_capstyle="round")
        ax.plot([x, x - 0.17], [y + 0.10, y - 0.20], color=color, lw=1.6, zorder=4, solid_capstyle="round")
        ax.plot([x, x + 0.17], [y + 0.10, y - 0.20], color=color, lw=1.6, zorder=4, solid_capstyle="round")
        ax.text(x, y - 0.48, name, ha="center", va="top", fontsize=8.2,
                weight="bold", color=color, linespacing=1.3)

    def usecase(x, y, w, h, text, ec=BLUE, fc="white"):
        ax.add_patch(Ellipse((x + 0.04, y - 0.05), w, h, fc=SHADOW, ec="none", alpha=0.28, zorder=2))
        e = Ellipse((x, y), w, h, fc=fc, ec=ec, lw=1.3, zorder=3)
        ax.add_patch(e)
        ax.text(x, y, text, ha="center", va="center", fontsize=7.7, zorder=4,
                color=INK, linespacing=1.3)
        return (x, y, w, h)

    zone(ax, 2.30, 0.30, 5.60, 9.35, "Système — PBX Asterisk / FreePBX + mini-API provision", BLUE, alpha=0.18)

    actor(1.00, 7.60, "Utilisateur\nAsaphone", TEAL)
    actor(1.00, 3.10, "Utilisateur\nsoftphone SIP", GREY)
    actor(9.15, 5.40, "Administrateur\nFreePBX", PURPLE)

    u1 = usecase(4.0, 8.9, 2.9, 0.88, "S'enregistrer\n(e-mail + code)", PURPLE, PURPLE_L)
    u2 = usecase(6.4, 7.9, 2.9, 0.88, "Provisionner par QR\n(claim → credentials)", PURPLE, PURPLE_L)
    u3 = usecase(4.0, 7.0, 2.9, 0.88, "Se connecter au PBX\nREGISTER WSS 8089", BLUE, BLUE_L)
    u4 = usecase(6.4, 6.0, 2.9, 0.88, "Appel audio / vidéo\nDTLS-SRTP", BLUE, BLUE_L)
    u5 = usecase(4.0, 5.1, 2.9, 0.88, "Chat\n(SIP MESSAGE)", BLUE, BLUE_L)
    u6 = usecase(6.4, 4.1, 2.9, 0.88, "Messagerie vocale\n*81001 … *81010", BLUE, BLUE_L)
    u7 = usecase(4.0, 3.2, 2.9, 0.88, "Appel de groupe\nConfBridge", BLUE, BLUE_L)
    u8 = usecase(6.4, 2.2, 2.9, 0.88, "VPN WireGuard\nenroll / claim", PURPLE, PURPLE_L)
    u9 = usecase(4.0, 1.15, 2.9, 0.88, "Appeler un poste\nclassique (UDP/SRTP)", GREY, LIGHT)

    for (x, y, w, h) in [u1, u3, u5, u7]:
        arrow(ax, 1.45, 7.50, x - w / 2 + 0.15, y, color=TEAL, lw=1.0, style="-", pill=False)
    for (x, y, w, h) in [u2, u4, u6, u8]:
        arrow(ax, 1.45, 7.42, x - w / 2 + 0.10, y, color=TEAL, lw=1.0, style="-", pill=False)
    arrow(ax, 1.50, 3.00, 2.65, 1.35, color=GREY, lw=1.0, style="-", pill=False)
    arrow(ax, 1.50, 3.15, 5.05, 6.00, color=GREY, lw=1.0, style="-", pill=False)
    arrow(ax, 8.75, 5.30, 7.75, 7.85, color=PURPLE, lw=1.0, style="-", pill=False)
    arrow(ax, 8.75, 5.20, 5.40, 8.85, color=PURPLE, lw=1.0, style="-", pill=False)

    arrow(ax, 5.2, 8.65, 5.6, 8.30, color=GREY, lw=0.9, ls=":", label="« include »", lfs=6.3)
    arrow(ax, 6.4, 7.45, 5.0, 7.35, color=GREY, lw=0.9, ls=":", label="« include »", lfs=6.3)
    arrow(ax, 4.6, 2.85, 6.0, 2.50, color=GREY, lw=0.9, ls=":", pill=False)

    title(ax, "Cas d'utilisation Asaphone — du provisionnement aux appels de groupe", fs=11.5)
    save(fig, "fig-usecase-asaphone.png")


# ═════════════════════════════════════════════════════════════════════════
# Helper séquence
# ═════════════════════════════════════════════════════════════════════════
def seq_diagram(ttl, actors, messages, name, w=10.6, h=7.2, note=None):
    """actors : [(entête, sous-titre, couleur)] ; messages : [(i, j, label, couleur, style)]."""
    fig, ax = plt.subplots(figsize=(w, h))
    n = len(actors)
    xs = [1.05 + i * (8.5 / max(n - 1, 1)) for i in range(n)]
    total = len(messages)
    top, bottom = 8.95, 0.55
    ax.set_xlim(0, 10.6)
    ax.set_ylim(0, 10.6)
    ax.axis("off")

    for (head, sub, color), x in zip(actors, xs):
        ax.plot([x, x], [bottom, top], color=color, lw=1.1, ls=(0, (4, 3)),
                alpha=0.45, zorder=1)
        card(ax, x - 0.92, top, 1.84, 1.02, head, sub, color=color,
             head_ratio=0.52, fs_head=8.0, fs_body=6.9)

    step = (top - bottom - 0.35) / max(total, 1)
    y = top - 0.28
    for (i, j, label, color, style) in messages:
        y -= step
        x1, x2 = xs[i], xs[j]
        if style == "note":
            xm = (x1 + x2) / 2 if i != j else x1
            wd = max(abs(x2 - x1), 3.6)
            box(ax, xm - wd / 2, y - 0.20, wd, 0.56, label, fc=YELL_L, ec=AMBER,
                fs=7.0, radius=0.08)
            continue
        ls = "--" if style == "dashed" else "-"
        st = "<|-|>" if style == "both" else "-|>"
        arrow(ax, x1, y, x2, y, color=color, lw=1.5, ls=ls, style=st,
              label=label, lfs=7.1, loff=(0, 0.02))

    if note:
        ax.text(5.3, 0.12, note, ha="center", fontsize=7.4, color=GREY, style="italic")
    title(ax, ttl, fs=11.5)
    save(fig, name)


def fig_seq_call():
    actors = [("Poste 1001", "Zoiper — SIP UDP 5060", GREY),
              ("Asterisk 20", "B2BUA — pont média", BLUE),
              ("Asaphone 1003", "WebRTC — WSS 8089", TEAL)]
    m = [
        (0, 1, "REGISTER — UDP 5060, auth Digest, SRTP SDES", GREY, "solid"),
        (2, 1, "REGISTER — wss://pbx.local:8089/ws", TEAL, "solid"),
        (0, 1, "INVITE 1003 — SDP RTP/SAVP (PCMU/PCMA, G.722)", GREY, "solid"),
        (1, 2, "INVITE — SDP WebRTC : SAVPF, DTLS-SRTP, ICE, Opus", BLUE, "solid"),
        (2, 1, "180 Ringing → 200 OK (SDP answer)", TEAL, "dashed"),
        (1, 0, "200 OK (SDP answer classique)", BLUE, "dashed"),
        (0, 1, "ACK", GREY, "solid"),
        (1, 2, "ACK · DTLS handshake + ICE checks", BLUE, "solid"),
        (0, 1, "Média : SRTP (SDES) — RTP UDP 10000–20000, DSCP EF", RED, "both"),
        (1, 2, "Média : DTLS-SRTP (WebRTC) — mêmes ports RTP", RED, "both"),
        (1, 1, "Asterisk termine chaque jambe et transcode si besoin (Opus ↔ G.711)\n— le média ne circule jamais en direct entre les postes", BLUE, "note"),
        (0, 1, "BYE", GREY, "solid"),
        (1, 2, "BYE → CDR écrit dans MariaDB", BLUE, "solid"),
    ]
    seq_diagram("Appel mixte — 1001 (UDP/SRTP) ↔ 1003 (WSS/DTLS-SRTP), pont B2BUA",
                actors, m, "fig-seq-appel-1001-1003.png",
                note="Signalisation UDP 5060 / WSS 8089 · média RTP 10000–20000 chiffré SDES ou DTLS selon la jambe.")


def fig_seq_provision():
    actors = [("Asaphone", "client mobile / desktop", TEAL),
              ("GitHub Pages", "bootstrap.json", PURPLE),
              ("Mini-API provision", "Apache / PHP · 443", BLUE),
              ("MariaDB + SMTP", "stockage · e-mails", GREY),
              ("Asterisk", "WSS 8089", RED)]
    m = [
        (0, 1, "GET bootstrap.json — découverte, toujours joignable", PURPLE, "solid"),
        (1, 0, "api_lan · api_remote · wss_url · vpn.endpoint", PURPLE, "dashed"),
        (0, 2, "POST register.php  { email }", TEAL, "solid"),
        (2, 3, "code 6 chiffres haché (TTL 15 min) + e-mail", BLUE, "solid"),
        (0, 2, "POST verify.php  { email, code }", TEAL, "solid"),
        (2, 3, "extension libre du pool 1003–1010\n+ QR chiffré envoyé par e-mail", BLUE, "solid"),
        (0, 0, "Scan du QR reçu par e-mail — token one-shot, validité 24 h", TEAL, "note"),
        (0, 2, "GET claim.php?token=…", TEAL, "solid"),
        (2, 0, "credentials : extension, secret, serveur, wss:8089", BLUE, "dashed"),
        (0, 4, "REGISTER wss://pbx.local:8089/ws (Digest)", RED, "solid"),
        (4, 0, "200 OK — poste enregistré", RED, "dashed"),
        (0, 2, "POST consume.php { jti } → token révoqué", TEAL, "solid"),
    ]
    seq_diagram("Provisionnement — inscription e-mail → QR → claim → REGISTER WSS",
                actors, m, "fig-seq-provision.png",
                note="Hors LAN, l'API distante (tunnel Cloudflare) remplace pbx.local — même flux, même sécurité.")


def fig_seq_confbridge():
    actors = [("Asaphone 1003", "initiateur", TEAL),
              ("Mini-API provision", "groups · conference", PURPLE),
              ("Asterisk", "ConfBridge", BLUE),
              ("Membres 1001, 1002", "postes appelés", GREY)]
    m = [
        (0, 1, "POST groups/sync.php + X-Provision-Jti\n{ id, titre, membres : 1001, 1002, 1003 }", PURPLE, "solid"),
        (1, 0, "call_uri = salle dédiée du groupe", PURPLE, "dashed"),
        (0, 2, "INVITE call_uri — un seul appel SIP, le client ne mixe pas", TEAL, "solid"),
        (2, 2, "Dialplan : l'appelant entre dans la salle ConfBridge", BLUE, "note"),
        (2, 1, "invitation automatique des membres (sauf appelant)", BLUE, "solid"),
        (1, 2, "Originate PJSIP/1001 · PJSIP/1002 → salle", PURPLE, "solid"),
        (2, 3, "les postes sonnent, décrochent, rejoignent la salle", BLUE, "solid"),
        (2, 2, "ConfBridge mixe l'audio pour tous les participants", BLUE, "note"),
        (0, 1, "POST conference/invite.php { room, extensions }\n— invitation en cours d'appel", PURPLE, "solid"),
        (1, 2, "Originate PJSIP/1004 → même salle", PURPLE, "solid"),
    ]
    seq_diagram("Appel de groupe — synchronisation, ConfBridge et originate des membres",
                actors, m, "fig-seq-confbridge.png",
                note="Salles : 6000 (défaut), 6001–6099 (réservées), une salle dédiée par groupe synchronisé.")


# ═════════════════════════════════════════════════════════════════════════
# g) Pipeline monitoring
# ═════════════════════════════════════════════════════════════════════════
def fig_monitoring_pipeline():
    fig, ax = new_ax(10.4, 5.5)

    zone(ax, 0.15, 5.55, 4.45, 3.95, "HÔTE PBX", BLUE, alpha=0.22)
    card(ax, 0.45, 7.45, 3.85, 1.35, "Asterisk 20",
         "AMI 127.0.0.1:5038\nutilisateur telegraf · write=command",
         color=BLUE, head_ratio=0.46, fs_head=8.4)
    box(ax, 0.45, 5.85, 3.85, 1.15, "Journaux :\n/var/log/asterisk/full\n/var/log/fail2ban.log",
        fc="white", ec=GREY, fs=7.6)

    zone(ax, 0.15, 0.45, 4.45, 4.60, "DOCKER — network_mode : host", PURPLE, alpha=0.22)
    card(ax, 0.45, 2.80, 3.85, 1.80, "Telegraf 1.33 — image AMI",
         "exec · ami_metrics.py (10 s)\nexec · log_metrics.py (10 s)\noutput → InfluxDB v2",
         color=PURPLE, head_ratio=0.50, fs_head=8.2)
    box(ax, 0.45, 0.80, 3.85, 1.40,
        "Image construite sur telegraf:1.33\n+ scripts Python AMI\n(pas de plugin Asterisk officiel)",
        fc="white", ec=GREY, fs=7.5)

    card(ax, 5.55, 5.80, 4.25, 1.75, "InfluxDB 2.7",
         "org « voip » · bucket « asterisk »\nmesure asterisk_core · port 8086",
         color=TEAL, head_ratio=0.52, fs_head=8.6)
    card(ax, 5.55, 2.90, 4.25, 2.00, "Grafana 11.4",
         "datasource Flux provisionnée\ndashboard « VoIP / Asterisk »\nport 3000",
         color=PURPLE, head_ratio=0.52, fs_head=8.6)
    box(ax, 5.55, 1.00, 4.25, 1.20, "Navigateur admin — LAN autorisé\nhttp://pbx.local:3000",
        fc="white", ec=GREY, fs=7.8)

    arrow(ax, 2.37, 7.45, 2.37, 4.60, color=BLUE, label="AMI : canaux,\nappels actifs", lfs=7.0, loff=(1.35, 0))
    arrow(ax, 1.10, 5.85, 1.10, 4.60, color=GREY, label="lecture seule", lfs=6.8, loff=(0.95, 0.22))
    arrow(ax, 4.30, 3.85, 5.55, 6.30, color=TEAL, rad=-0.15, label="line protocol\nHTTP 8086 + token", lfs=7.0, loff=(0.55, -0.1))
    arrow(ax, 7.67, 5.80, 7.67, 4.90, color=TEAL, label="requêtes Flux", lfs=7.0)
    arrow(ax, 7.67, 2.90, 7.67, 2.20, color=PURPLE, label="HTTP 3000", lfs=7.0)

    ax.text(5.2, 0.15, "Chaîne courte sans Prometheus — secrets générés hors dépôt, ports 3000/8086 restreints par UFW.",
            ha="center", fontsize=7.4, color=GREY, style="italic")
    title(ax, "Pipeline de supervision — Telegraf (AMI + logs) → InfluxDB 2 → Grafana")
    save(fig, "fig-monitoring-pipeline.png")


# ═════════════════════════════════════════════════════════════════════════
# h) Couches sécurité
# ═════════════════════════════════════════════════════════════════════════
def fig_security_layers():
    fig, ax = new_ax(10.2, 6.3)
    layers = [
        ("L0", "Segmentation L2", "VLAN 10 voix (10.10.10.0/24) séparé du LAN gestion — 802.1Q, QoS trust DSCP", "déployé", TEAL),
        ("L1", "Transport réseau", "VPN WireGuard wg0 (10.200.0.0/24, UDP 51820) — relais WSS si CGNAT", "déployé", TEAL),
        ("L2", "Pare-feu / anti-abus", "UFW default deny + règles par CIDR · Fail2Ban jail asterisk", "déployé", TEAL),
        ("L3", "Administration web", "HTTPS Apache 443 (certificat) · session FreePBX · permissions GUI", "déployé", TEAL),
        ("L4", "Signalisation SIP", "TLS 5061/5161 · WSS 8089 · authentification Digest", "partiel", AMBER),
        ("L5", "Média audio / vidéo", "SRTP SDES (postes classiques) · DTLS-SRTP (WebRTC)", "partiel", AMBER),
        ("L6", "Provisionnement", "QR chiffré one-shot · claim 24 h · révocation jti · rate-limit", "déployé", TEAL),
        ("L7", "Données au repos", "Secrets 600/640 hors Git · rotation 90 j · CDR MariaDB", "partiel", RED),
    ]
    y = 9.45
    for code, name, detail, state, sc in layers:
        # pastille numéro
        ax.add_patch(Circle((0.72, y - 0.47), 0.34, fc=BLUE, ec="none", zorder=4))
        ax.text(0.72, y - 0.47, code, ha="center", va="center", fontsize=9.5,
                color="white", weight="bold", zorder=5)
        # carte de la couche
        box(ax, 1.30, y - 0.92, 8.55, 0.92, "", fc="white", ec="#D5DEE6", lw=1.0, radius=0.08)
        ax.text(1.60, y - 0.30, name, ha="left", va="center", fontsize=8.8,
                weight="bold", color=BLUE_D, zorder=5)
        ax.text(1.60, y - 0.66, detail, ha="left", va="center", fontsize=7.5,
                color=INK, zorder=5)
        # pastille d'état
        ax.text(9.55, y - 0.47, state, ha="center", va="center", fontsize=7.6,
                color="white", weight="bold", zorder=6,
                bbox=dict(boxstyle="round,pad=0.32", fc=sc, ec="none"))
        y -= 1.12
    ax.text(5.1, 0.16, "Chaque jambe est chiffrée ; le PBX reste un point de confiance (B2BUA) — l'E2EE strict poste-à-poste est hors modèle.",
            ha="center", fontsize=7.5, color=GREY, style="italic")
    title(ax, "Sécurité en profondeur — huit couches emboîtées, de la trame au secret")
    save(fig, "fig-securite-couches.png")


# ═════════════════════════════════════════════════════════════════════════
# i) Comparatif liaisons
# ═════════════════════════════════════════════════════════════════════════
def fig_comparatif():
    fig, ax = new_ax(10.8, 5.9, xmax=10.9)
    cols = ["", "Extension PJSIP", "Trunk SIP", "VPN WireGuard", "VLAN 10 (802.1Q)", "Tunnel Cloudflare"]
    rows = [
        ("Couche", "SIP (L7) — poste", "SIP (L7) — inter-PBX\nou opérateur", "IP (L3) — kernel", "Ethernet (L2) — switch", "HTTPS (L7) — sortant"),
        ("Relie quoi ?", "Poste ↔ PBX\n(1001–1010)", "PBX ↔ PSTN\nou autre PBX", "PC distant ↔ LAN PBX\n(10.200.0.0/24)", "Téléphones du site ↔ PBX\n(10.10.10.0/24)", "Internet ↔ API\nprovision (443)"),
        ("Authentification", "REGISTER + secret\n(≥ 16 caractères)", "Login opérateur\nou identify IP", "Paires de clés\nWireGuard", "Aucune — tag VLAN\nsur ports switch", "Tunnel sortant,\naucun port entrant"),
        ("Où configurer ?", "FreePBX → Extensions\n(scripts phase 2)", "FreePBX → Trunks\n(routes préparées)", "OS Linux (wg0)\n+ pare-feu", "Switch + hyperviseur\n+ ens33.10", "Service systemd\ndédié"),
        ("Softphone\ndistant ?", "Oui — via VPN\nou relais WSS", "Non", "Oui (télétravail)", "Non (site uniquement)", "Non (API HTTP\nseulement)"),
        ("État projet", "production\n1001–1010", "préconfiguré\n(secrets à fournir)", "opérationnel\n(enrôlement API)", "OS prêt — switch\nà raccorder", "actif au boot\n(URL éphémère)"),
    ]
    cw = [1.30, 1.90, 1.90, 1.90, 1.90, 1.90]
    x0, y0, rh = 0.10, 9.30, 1.44

    # entête
    x = x0
    for c, wd in zip(cols, cw):
        if c:
            box(ax, x, y0, wd - 0.08, 0.78, c, fc=BLUE, ec=BLUE, tc="white",
                weight="bold", fs=7.9, radius=0.07)
        x += wd
    # corps
    y = y0
    for ri, r in enumerate(rows):
        y -= rh
        x = x0
        for i, (cell, wd) in enumerate(zip(r, cw)):
            if i == 0:
                box(ax, x, y, wd - 0.08, rh - 0.10, cell, fc=BLUE_L, ec=BLUE,
                    weight="bold", fs=7.5, radius=0.07, shadow=False)
            else:
                last = r[0] == "État projet"
                fc = TEAL_L if last else ("white" if ri % 2 == 0 else "#F7FAFC")
                ec = TEAL if last else "#D5DEE6"
                box(ax, x, y, wd - 0.08, rh - 0.10, cell, fc=fc, ec=ec, fs=6.9,
                    radius=0.07, shadow=False, tc=("#0E6B58" if last else INK),
                    weight=("bold" if last else "normal"))
            x += wd
    ax.set_ylim(0.35, 10.45)
    title(ax, "Cinq façons de relier — extension, trunk, VPN, VLAN, tunnel", fs=11.5)
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
