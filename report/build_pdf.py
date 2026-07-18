#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assemblage du rapport PDF « asterisk-asaphone-report.pdf » (reportlab / Platypus).

Prérequis : exécuter d'abord gen_diagrams.py et gen_consoles.py (dossier figures/),
et disposer des captures réelles dans capture/.

Contenu aligné sur les documents du dépôt serveur (S2/S3/S4, Architecture-*,
Plan-adressage-*, INSTALLATION.md, docs/*, security/*, webrtc/, monitoring/).
Aucun secret n'est inclus.
"""

import os
from PIL import Image as PILImage

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Image,
    Table, TableStyle, PageBreak, KeepTogether, NextPageTemplate,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
CAP = os.path.join(ROOT, "capture")
OUT = os.path.join(ROOT, "asterisk-asaphone-report.pdf")

# ── Palette ───────────────────────────────────────────────────────────────
BLUE = colors.HexColor("#1B4F72")
TEAL = colors.HexColor("#148F77")
PURPLE = colors.HexColor("#7D3C98")
RED = colors.HexColor("#C0392B")
GREY = colors.HexColor("#5D6D7E")
LIGHT = colors.HexColor("#F4F6F7")
BLUE_L = colors.HexColor("#D6EAF8")
TEAL_L = colors.HexColor("#D1F2EB")

# ── Polices (DejaVu : accents + symboles → · ↔ ≥) ────────────────────────
FDIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DVS", os.path.join(FDIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVS-B", os.path.join(FDIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DVS-I", os.path.join(FDIR, "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DVS-BI", os.path.join(FDIR, "DejaVuSans-BoldOblique.ttf")))
pdfmetrics.registerFont(TTFont("DVM", os.path.join(FDIR, "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("DVS", normal="DVS", bold="DVS-B",
                              italic="DVS-I", boldItalic="DVS-BI")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# ── Styles ────────────────────────────────────────────────────────────────
S = {}
S["title"] = ParagraphStyle("title", fontName="DVS-B", fontSize=24, leading=30,
                            textColor=BLUE, alignment=TA_CENTER, spaceAfter=6)
S["subtitle"] = ParagraphStyle("subtitle", fontName="DVS", fontSize=13, leading=18,
                               textColor=GREY, alignment=TA_CENTER)
S["h1"] = ParagraphStyle("h1", fontName="DVS-B", fontSize=16, leading=20,
                         textColor=colors.white, backColor=BLUE,
                         borderPadding=(6, 8, 6, 8), spaceBefore=6, spaceAfter=12)
S["h2"] = ParagraphStyle("h2", fontName="DVS-B", fontSize=12.5, leading=16,
                         textColor=BLUE, spaceBefore=12, spaceAfter=5,
                         borderColor=TEAL, borderWidth=0, leftIndent=0)
S["h3"] = ParagraphStyle("h3", fontName="DVS-B", fontSize=10.5, leading=14,
                         textColor=TEAL, spaceBefore=9, spaceAfter=4)
S["body"] = ParagraphStyle("body", fontName="DVS", fontSize=9.3, leading=13.4,
                           alignment=TA_JUSTIFY, spaceAfter=5,
                           textColor=colors.HexColor("#1B2631"))
S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=12,
                             bulletIndent=3, spaceAfter=2.5)
S["caption"] = ParagraphStyle("caption", fontName="DVS-I", fontSize=8, leading=10.5,
                              textColor=GREY, alignment=TA_CENTER,
                              spaceBefore=3, spaceAfter=10)
S["mono"] = ParagraphStyle("mono", fontName="DVM", fontSize=8, leading=11,
                           textColor=colors.HexColor("#1B2631"),
                           backColor=LIGHT, borderPadding=(4, 6, 4, 6),
                           spaceBefore=4, spaceAfter=6)
S["kp-title"] = ParagraphStyle("kp-title", fontName="DVS-B", fontSize=9.5,
                               leading=12, textColor=colors.white)
S["kp-body"] = ParagraphStyle("kp-body", parent=S["body"], fontSize=8.8,
                              leading=12.4, spaceAfter=2, textColor=colors.HexColor("#0E3D2E"))
S["toc-title"] = ParagraphStyle("toc-title", fontName="DVS-B", fontSize=16,
                                leading=20, textColor=BLUE, spaceAfter=12)
S["abstract"] = ParagraphStyle("abstract", parent=S["body"], fontSize=9.5,
                               leading=14.2)
S["cell"] = ParagraphStyle("cell", fontName="DVS", fontSize=8.2, leading=10.8,
                           textColor=colors.HexColor("#1B2631"))
S["cell-b"] = ParagraphStyle("cell-b", parent=S["cell"], fontName="DVS-B")
S["cell-h"] = ParagraphStyle("cell-h", fontName="DVS-B", fontSize=8.4, leading=11,
                             textColor=colors.white)

TOC_H1 = ParagraphStyle("toc1", fontName="DVS-B", fontSize=10, leading=15,
                        textColor=BLUE, leftIndent=2)
TOC_H2 = ParagraphStyle("toc2", fontName="DVS", fontSize=9, leading=13,
                        textColor=GREY, leftIndent=14)


# ── Gabarit de document (numéro de page, en-tête, signets, TOC) ──────────
class ReportDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, pagesize=A4,
                         leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=MARGIN, bottomMargin=16 * mm, **kw)
        frame = Frame(MARGIN, 16 * mm, CONTENT_W, PAGE_H - MARGIN - 16 * mm - 6 * mm,
                      id="main")
        cover = Frame(MARGIN, 16 * mm, CONTENT_W, PAGE_H - MARGIN - 16 * mm,
                      id="cover")
        self.addPageTemplates([
            PageTemplate(id="Cover", frames=[cover], onPage=self._cover_deco),
            PageTemplate(id="Body", frames=[frame], onPage=self._body_deco),
        ])

    def _cover_deco(self, canv, doc):
        canv.saveState()
        canv.setFillColor(BLUE)
        canv.rect(0, PAGE_H - 14 * mm, PAGE_W, 14 * mm, stroke=0, fill=1)
        canv.setFillColor(TEAL)
        canv.rect(0, PAGE_H - 16.5 * mm, PAGE_W, 2.5 * mm, stroke=0, fill=1)
        canv.setFillColor(BLUE)
        canv.rect(0, 0, PAGE_W, 10 * mm, stroke=0, fill=1)
        canv.restoreState()

    def _body_deco(self, canv, doc):
        canv.saveState()
        canv.setStrokeColor(TEAL)
        canv.setLineWidth(0.8)
        canv.line(MARGIN, PAGE_H - 12 * mm, PAGE_W - MARGIN, PAGE_H - 12 * mm)
        canv.setFont("DVS", 7.2)
        canv.setFillColor(GREY)
        canv.drawString(MARGIN, PAGE_H - 10.5 * mm,
                        "Mémoire technique — PBX Asterisk 20 / FreePBX 17 & softphone Asaphone")
        canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 10.5 * mm, "Juillet 2026")
        canv.setFont("DVS", 8)
        canv.setFillColor(BLUE)
        canv.drawCentredString(PAGE_W / 2, 9 * mm, f"— {doc.page} —")
        canv.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style = flowable.style.name
            text = flowable.getPlainText()
            if style == "h1":
                key = f"h1-{self.seq.nextf('h1key')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, 0, 0)
                self.notify("TOCEntry", (0, text, self.page, key))
            elif style == "h2":
                key = f"h2-{self.seq.nextf('h2key')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, 1, 0)
                self.notify("TOCEntry", (1, text, self.page, key))


# ── Aides de mise en page ─────────────────────────────────────────────────
def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    return [Paragraph(f"• {t}", S["bullet"]) for t in items]


def img_flow(path, max_w=CONTENT_W, max_h=150 * mm):
    with PILImage.open(path) as im:
        iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    return Image(path, width=iw * scale, height=ih * scale)


def figure(path, caption, max_w=CONTENT_W, max_h=150 * mm):
    return KeepTogether([img_flow(path, max_w, max_h), Paragraph(caption, S["caption"])])


def capture(name, caption, max_h=110 * mm, max_w=None):
    path = os.path.join(CAP, name)
    w = max_w or (CONTENT_W * 0.92)
    return figure(path, f"Capture — {caption} <i>(capture/{name})</i>", w, max_h)


def schema(name, caption, max_h=170 * mm, max_w=CONTENT_W):
    path = os.path.join(FIG, name)
    return figure(path, f"Schéma généré — {caption} <i>(figures/{name})</i>", max_w, max_h)


def two_captures(n1, c1, n2, c2, each_h=95 * mm):
    """Deux captures portrait côte à côte."""
    w = CONTENT_W / 2 - 4 * mm
    cell1 = [img_flow(os.path.join(CAP, n1), w, each_h),
             Paragraph(f"Capture — {c1} <i>(capture/{n1})</i>", S["caption"])]
    cell2 = [img_flow(os.path.join(CAP, n2), w, each_h),
             Paragraph(f"Capture — {c2} <i>(capture/{n2})</i>", S["caption"])]
    t = Table([[cell1, cell2]], colWidths=[CONTENT_W / 2, CONTENT_W / 2])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def table(headers, rows, widths=None, header_bg=BLUE, fs=8.2):
    data = [[Paragraph(h, S["cell-h"]) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), S["cell"]) for c in r])
    if widths is None:
        widths = [CONTENT_W / len(headers)] * len(headers)
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C4CE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def keypoints(items):
    """Encadré « Points clés » en fin de chapitre."""
    head = Table([[Paragraph("Points clés du chapitre", S["kp-title"])]],
                 colWidths=[CONTENT_W])
    head.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    body = Table([[[Paragraph(f"✔  {t}", S["kp-body"]) for t in items]]],
                 colWidths=[CONTENT_W])
    body.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_L),
        ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([Spacer(1, 6), head, body, Spacer(1, 4)])


def h1(text):
    return Paragraph(text, S["h1"])


def h2(text):
    return Paragraph(text, S["h2"])


def h3(text):
    return Paragraph(text, S["h3"])


# ═════════════════════════════════════════════════════════════════════════
# Construction du contenu
# ═════════════════════════════════════════════════════════════════════════
story = []

# ── Page de garde ────────────────────────────────────────────────────────
story.append(NextPageTemplate("Body"))
story.append(Spacer(1, 30 * mm))
story.append(Paragraph("Plateforme de téléphonie IP<br/>Asterisk 20 / FreePBX 17<br/>&amp; softphone Asaphone", S["title"]))
story.append(Spacer(1, 8 * mm))
story.append(Paragraph("Mémoire technique — architecture, déploiement, sécurité et exploitation<br/>"
                       "VLAN voix · WebRTC · provisionnement QR · VPN WireGuard · monitoring InfluxDB/Grafana",
                       S["subtitle"]))
story.append(Spacer(1, 14 * mm))
cover_tbl = table(
    ["Élément", "Référence"],
    [
        ["Dépôt serveur", '<link href="https://github.com/Asaph-D/serveur" color="#1B4F72"><u>github.com/Asaph-D/serveur</u></link> (branche main)'],
        ["Dépôt client", '<link href="https://github.com/Asaph-D/asaphone" color="#1B4F72"><u>github.com/Asaph-D/asaphone</u></link> (branche main)'],
        ["Cœur VoIP", "Asterisk 20 LTS (réf. 20.18.2) + FreePBX 17 — PJSIP, ConfBridge, WebRTC"],
        ["Client", "Asaphone (Flutter, projet OBSCURA) — Android / Windows / iOS"],
        ["Monitoring", "InfluxDB 2.7 · Grafana 11.4.0 · Telegraf 1.33 (image AMI maison)"],
        ["Date", "Juillet 2026"],
    ],
    widths=[42 * mm, CONTENT_W - 42 * mm],
)
story.append(cover_tbl)
story.append(Spacer(1, 12 * mm))
story.append(Paragraph("Document généré par un pipeline Python reproductible "
                       "(matplotlib pour les figures, reportlab pour le PDF) — voir report/README.md.",
                       S["caption"]))
story.append(PageBreak())

# ── Abstracts ────────────────────────────────────────────────────────────
story.append(Paragraph("Résumé (FR)", S["toc-title"]))
story.append(P(
    "Ce mémoire décrit la conception, le déploiement et l'exploitation d'une plateforme de téléphonie "
    "IP de bout en bout construite autour d'<b>Asterisk 20 LTS</b> administré par <b>FreePBX 17</b>, et de son "
    "client multiplateforme <b>Asaphone</b> (Flutter). Le serveur est en <i>dual-homing</i> : une patte de "
    "gestion sur le LAN (ex. 192.168.1.0/24, nom mDNS <b>pbx.local</b>) et une patte voix sur un "
    "<b>VLAN 10 dédié (10.10.10.0/24)</b> avec marquage QoS DSCP EF du RTP. Dix extensions PJSIP "
    "(<b>1001–1010</b>) couvrent deux profils : postes classiques SIP UDP/TLS + SRTP (1001–1002) et postes "
    "WebRTC via WSS 8089 + DTLS-SRTP (1003–1010). Les services avancés incluent un IVR AGI Python avec "
    "routage horaire (7000/7010), des files d'attente ACD (7020), des salles de conférence ConfBridge "
    "(6000, 8001, salles de groupe Asaphone), la messagerie vocale avec notification (*81001–*81010) et un "
    "chat via SIP MESSAGE.", "abstract"))
story.append(P(
    "Le provisionnement est original : une mini-API PHP hébergée sur le PBX délivre par e-mail un "
    "<b>QR one-shot chiffré</b> (inscription → code de vérification → claim → REGISTER WSS), avec découverte "
    "via un <b>bootstrap.json publié sur GitHub Pages</b> et une API distante exposée par tunnel Cloudflare. "
    "L'accès distant repose sur un VPN <b>WireGuard</b> (10.200.0.0/24) avec relais WSS pour les liens CGNAT. "
    "La sécurité (Phase 4) combine TLS 5061, SRTP/DTLS, UFW en <i>default deny</i>, Fail2Ban et une politique "
    "de secrets. L'observabilité s'appuie sur la chaîne <b>Telegraf (AMI) → InfluxDB 2 → Grafana</b> en "
    "conteneurs Docker. L'ensemble du démarrage est automatisé par un service systemd "
    "(<b>serveur-startup.service</b>) résilient hors ligne.", "abstract"))
story.append(Spacer(1, 6 * mm))
story.append(Paragraph("Abstract (EN)", S["toc-title"]))
story.append(P(
    "This report describes the design, deployment and operation of an end-to-end IP telephony platform "
    "built on <b>Asterisk 20 LTS</b> managed by <b>FreePBX 17</b>, together with its cross-platform softphone "
    "<b>Asaphone</b> (Flutter). The server is dual-homed: a management leg on the office LAN (e.g. "
    "192.168.1.0/24, mDNS name <b>pbx.local</b>) and a voice leg on a dedicated <b>VLAN 10 (10.10.10.0/24)</b> "
    "with DSCP EF QoS marking of RTP. Ten PJSIP extensions (<b>1001–1010</b>) cover two profiles: classic "
    "SIP UDP/TLS + SRTP endpoints (1001–1002) and WebRTC endpoints over WSS 8089 + DTLS-SRTP (1003–1010). "
    "Advanced services include a Python AGI IVR with time-based routing (7000/7010), ACD queues (7020), "
    "ConfBridge conference rooms (6000, 8001, per-group Asaphone rooms), voicemail with notification "
    "(*81001–*81010) and chat over SIP MESSAGE.", "abstract"))
story.append(P(
    "Provisioning is a distinctive feature: a small PHP API hosted on the PBX delivers a one-shot encrypted "
    "<b>QR code</b> by e-mail (sign-up → verification code → claim → WSS REGISTER), with discovery through a "
    "<b>bootstrap.json published on GitHub Pages</b> and a remote API exposed through a Cloudflare tunnel. "
    "Remote access relies on a <b>WireGuard</b> VPN (10.200.0.0/24) with a WSS relay for CGNAT links. "
    "Security (Phase 4) combines TLS 5061, SRTP/DTLS, default-deny UFW, Fail2Ban and a secrets policy. "
    "Observability relies on the <b>Telegraf (AMI) → InfluxDB 2 → Grafana</b> chain running in Docker. "
    "The whole boot sequence is automated by an offline-resilient systemd unit "
    "(<b>serveur-startup.service</b>).", "abstract"))
story.append(PageBreak())

# ── Sommaire ─────────────────────────────────────────────────────────────
story.append(Paragraph("Sommaire", S["toc-title"]))
toc = TableOfContents()
toc.levelStyles = [TOC_H1, TOC_H2]
story.append(toc)
story.append(PageBreak())

# ═══ 1. Introduction ═════════════════════════════════════════════════════
story.append(h1("1.  Introduction et objectifs"))
story.append(h2("1.1  Contexte"))
story.append(P(
    "Le projet consiste à construire une plateforme de téléphonie d'entreprise complète et auto-hébergée : "
    "un PBX <b>Asterisk 20 LTS</b> déployé via <b>FreePBX 17</b> sur une VM Ubuntu, et un softphone maison, "
    "<b>Asaphone</b>, développé en Flutter (projet OBSCURA) pour Android, Windows et iOS. Le périmètre couvre "
    "toute la chaîne : plan d'adressage et VLAN voix, extensions et services de PBX (IVR, files, conférences, "
    "messagerie), transport sécurisé (TLS, SRTP, DTLS), accès distant (VPN WireGuard, tunnel Cloudflare), "
    "provisionnement automatisé par QR, supervision et automatisation du démarrage."))
story.append(h2("1.2  Démarche par phases"))
story.append(table(
    ["Phase", "Périmètre", "Document source"],
    [
        ["Phase 1", "Plan d'adressage, VLAN 10 voix, QoS RTP DSCP EF", "Plan-adressage-reseau-VoIP-QoS.md"],
        ["Phase 2", "Extensions PJSIP 1001–1010, groupes, TLS 5061, messagerie", "S2-Phase2-Utilisateurs-Extensions.md"],
        ["Phase 3", "IVR AGI, files ACD, ConfBridge, monitoring Influx/Grafana", "S3-Phase3-IVR-Monitoring.md"],
        ["Phase 4", "Sécurisation : TLS, SRTP, Fail2Ban, UFW, mots de passe", "S4-Phase4-Securite-complete.md"],
        ["Extension", "WebRTC, client Asaphone, provisionnement, VPN, groupes", "webrtc/, security/, docs/, provision/"],
    ],
    widths=[22 * mm, 88 * mm, CONTENT_W - 110 * mm],
))
story.append(h2("1.3  Modalité « production »"))
story.append(P(
    "Le plan d'adressage précise la modalité de travail : tout ce qui est déployé vise la production — pas de "
    "cadre « démo » pour reporter des vérifications. Chaque fonctionnalité vérifiable est contrôlée sur le "
    "flux réel (appel, capture réseau sur l'interface concernée) et le résultat est consigné dans les "
    "documents de phase. Les valeurs d'adressage montrées dans ce rapport sont celles documentées dans le "
    "dépôt ; l'IP LAN du PBX varie selon le site (elle est centralisée dans <font face='DVM'>network/global-config.env</font> "
    "et resynchronisée au boot)."))
story.append(keypoints([
    "PBX Asterisk 20 LTS + FreePBX 17 auto-hébergé, client Flutter Asaphone multiplateforme.",
    "Déploiement incrémental en 4 phases documentées, complétées par WebRTC, provision QR et VPN.",
    "Logique production : chaque fonction est validée sur flux réel et consignée dans le dépôt.",
]))
story.append(PageBreak())

# ═══ 2. Architecture ═════════════════════════════════════════════════════
story.append(h1("2.  Architecture générale"))
story.append(h2("2.1  Vue d'ensemble"))
story.append(P(
    "Les flux vont de l'Internet (fournisseur SIP/PSTN pour la phase trunk, tunnel Cloudflare pour la "
    "provision, clients 4G pour le VPN) jusqu'aux terminaux du réseau voix, en passant par une couche de "
    "sécurité périmétrique (UFW, Fail2Ban, WireGuard), le cœur applicatif Asterisk/FreePBX et les briques "
    "d'observabilité. Le serveur expose deux pattes réseau permanentes (gestion + VLAN voix) et une patte "
    "tunnel (wg0)."))
story.append(schema("fig-architecture-globale.png",
                    "architecture globale Internet → pare-feu → PBX → LAN gestion / VLAN voix "
                    "(d'après Architecture-VoIP-communication-composants.md)", max_h=155 * mm))
story.append(h2("2.2  Dual-homing gestion / voix"))
story.append(P(
    "La patte de gestion (<font face='DVM'>ens33</font>, ex. 192.168.1.104 selon docs/vpn.md — l'IP exacte varie "
    "selon le site) porte l'UI FreePBX, la mini-API de provisionnement et les softphones du LAN bureau. La "
    "patte voix (<font face='DVM'>ens33.10</font>, 10.10.10.10/24 statique) est réservée aux téléphones du "
    "VLAN 10. Les <i>localnets</i> PJSIP déclarent les deux réseaux plus le sous-réseau VPN, ce qui garantit "
    "une signalisation SIP correcte (pas de réécriture NAT erronée) quelle que soit la patte utilisée."))
story.append(schema("fig-dual-homing.png",
                    "dual-homing MGMT / VLAN 10 voix / WireGuard et clients associés (d'après docs/vpn.md)",
                    max_h=120 * mm))
story.append(h2("2.3  Rôles des composants"))
story.append(table(
    ["Composant", "Rôle", "Interfaces principales"],
    [
        ["Asterisk 20 LTS", "Cœur SIP/RTP : PJSIP, dialplan, ConfBridge, voicemail, B2BUA", "SIP 5060/5160, TLS 5061/5161, WSS 8089, RTP 10000–20000"],
        ["FreePBX 17", "Administration : extensions, trunks, routes, certificats", "Apache 80/443, fwconsole, base MariaDB"],
        ["Mini-API provision", "Onboarding Asaphone : register/verify/claim, VPN enroll, groupes", "HTTPS 443 (/provision), MariaDB, SMTP"],
        ["MariaDB", "Config FreePBX, CDR, tables provision_*", "SQL local"],
        ["Stack monitoring", "Métriques AMI + logs → dashboards", "AMI 5038 (local), HTTP 8086/3000"],
        ["WireGuard / Cloudflare", "Accès distant réseau (L3) / exposition API (L7)", "UDP 51820, tunnel HTTPS sortant"],
    ],
    widths=[32 * mm, 72 * mm, CONTENT_W - 104 * mm],
))
story.append(keypoints([
    "Trois pattes IP : gestion (ens33), voix (ens33.10 — 10.10.10.10), VPN (wg0 — 10.200.0.1).",
    "Asterisk est le B2BUA central : chaque appel est ponté sur le PBX, y compris entre profils UDP et WebRTC.",
    "La sécurité entoure le cœur (UFW/Fail2Ban) et s'y intègre (TLS, SRTP, certificats Certman).",
]))
story.append(PageBreak())

# ═══ 3. Adressage / QoS ══════════════════════════════════════════════════
story.append(h1("3.  Plan d'adressage et QoS (Phase 1)"))
story.append(h2("3.1  VLAN 10 voix — plan IPv4"))
story.append(P(
    "Le sous-réseau voix retenu est <b>10.10.10.0/24</b> (VLAN ID 10), volontairement distinct du LAN de "
    "gestion pour permettre segmentation, filtrage inter-VLAN et politiques QoS dédiées. Le document de "
    "phase 1 justifie ce choix face aux alternatives (réseau plat, second /24 en 192.168.148.0/24)."))
story.append(table(
    ["Élément", "Valeur retenue", "Rôle"],
    [
        ["Réseau VLAN 10", "10.10.10.0/24", "Sous-réseau voix uniquement"],
        ["Passerelle (SVI L3 / firewall)", "10.10.10.1", "Gateway téléphones + routage inter-VLAN"],
        ["FreePBX / Asterisk (patte voix)", "10.10.10.10/24", "IP statique (connexion NM voix-vlan10, ens33.10)"],
        ["Plage DHCP téléphones", "10.10.10.50 – 10.10.10.200", "Scope terminaux"],
        ["Plage réservée infra", "10.10.10.2 – 10.10.10.49", "Passerelles, SBC, SNMP, futurs services"],
        ["LAN gestion (exemple site)", "192.168.1.0/24 (ex. doc : 192.168.147.0/24)", "UI FreePBX, admin, softphones bureau"],
    ],
    widths=[52 * mm, 52 * mm, CONTENT_W - 104 * mm],
))
story.append(h2("3.2  QoS — DSCP EF sur le RTP"))
story.append(P(
    "Le marquage QoS est appliqué côté serveur dans la table <font face='DVM'>mangle</font> d'UFW "
    "(<font face='DVM'>/etc/ufw/before.rules</font>) : tout paquet UDP dont le port source ou destination est "
    "dans la plage RTP <b>10000–20000</b> reçoit la classe <b>DSCP EF (46, 0x2e)</b>. La plage RTP est celle "
    "constatée dans <font face='DVM'>rtp_additional.conf</font> généré par FreePBX. Les équipements réseau "
    "doivent ensuite faire confiance au marquage (<i>trust DSCP</i>) ou classifier eux-mêmes."))
story.append(P("Vérification opérationnelle documentée :", "body"))
story.append(Paragraph(
    "$ sudo iptables -t mangle -L OUTPUT -n -v<br/>"
    "DSCP set 0x2e  udp  multiport sports 10000:20000<br/>"
    "DSCP set 0x2e  udp  multiport dports 10000:20000", S["mono"]))
story.append(h2("3.3  Matrice de flux voix"))
story.append(table(
    ["Flux", "VLAN cible", "Protocole / ports", "Marquage"],
    [
        ["SIP", "10", "UDP/TCP 5060, 5160 · TLS 5061, 5161", "Best effort (AF31 en option)"],
        ["RTP", "10", "UDP 10000–20000", "DSCP EF (fait côté serveur)"],
        ["WebRTC (signalisation)", "MGMT/10", "WSS 8089/tcp (HTTP 8088 en lab)", "Best effort"],
    ],
))
story.append(P(
    "Statut d'infrastructure : la VM est prête côté OS (interface <font face='DVM'>ens33.10</font> configurée, "
    "localnets FreePBX à jour, UFW appliqué). Le raccordement final — trunk 802.1Q sur le switch physique et "
    "port group VLAN 10 côté hyperviseur — est documenté comme restant à réaliser côté infrastructure ; la file "
    "prioritaire (trust DSCP) sur les équipements L2/L3 également."))
story.append(keypoints([
    "VLAN 10 = segment voix 10.10.10.0/24 ; le VLAN se configure sous Asterisk (switch/hyperviseur), pas dedans.",
    "RTP marqué DSCP EF (46) dans ufw/before.rules ; plage RTP FreePBX 10000–20000 alignée avec les règles.",
    "OS prêt ; le trunk VLAN switch/hyperviseur et le trust DSCP restent côté infrastructure.",
]))
story.append(PageBreak())

# ═══ 4. Extensions FreePBX ═══════════════════════════════════════════════
story.append(h1("4.  Utilisateurs et extensions FreePBX (Phase 2)"))
story.append(h2("4.1  Extensions PJSIP 1001–1010"))
story.append(P(
    "Dix extensions <b>chan_pjsip</b> sont créées par script PHP FreePBX "
    "(<font face='DVM'>scripts/phase2-create-extensions.php</font>) : contexte <font face='DVM'>from-internal</font>, "
    "3 contacts max par extension (plusieurs appareils), secrets aléatoires stockés hors dépôt "
    "(<font face='DVM'>/root/phase2-pjsip-secrets.txt</font>, chmod 600). Chaque poste possède une boîte vocale "
    "(pièce jointe WAV activée). Les profils sont ensuite alignés par "
    "<font face='DVM'>align-pjsip-site.sh</font> : postes classiques et postes WebRTC."))
story.append(table(
    ["Extensions", "Profil", "Transport", "Média", "Codecs"],
    [
        ["1001–1002", "Classique (Zoiper, téléphone IP)", "UDP 5060 / TLS 5061", "RTP + SRTP SDES", "ulaw, alaw, gsm, g726, g722"],
        ["1003–1010", "WebRTC (Asaphone, navigateur)", "WSS 8089 (transport-wss)", "DTLS-SRTP, ICE, AVPF, rtcp-mux", "Opus + ulaw/alaw (G.722 possible)"],
        ["8000", "Sonnerie de groupe (dialplan custom)", "—", "Dial simultané 1001…1010, 45 s", "—"],
    ],
    widths=[24 * mm, 52 * mm, 38 * mm, 38 * mm, CONTENT_W - 152 * mm],
))
story.append(h2("4.2  Interface FreePBX"))
story.append(P(
    "Principe fondamental : sous FreePBX on ne modifie jamais <font face='DVM'>pjsip.conf</font> à la main. "
    "Le flux est UI (ou scripts) → base MariaDB → <font face='DVM'>fwconsole reload</font> → fichiers générés. "
    "Le custom vit dans <font face='DVM'>extensions_custom.conf</font>, <font face='DVM'>pjsip_custom_post.conf</font>, "
    "<font face='DVM'>manager_custom.conf</font>…"))
story.append(capture("freePBX-interface.png", "tableau de bord FreePBX 17 (UI d'administration du PBX)", max_h=95 * mm))
story.append(capture("extension-interface.png", "liste des extensions PJSIP 1001–1010 dans FreePBX", max_h=95 * mm))
story.append(h2("4.3  Création d'une extension"))
story.append(P(
    "La création se fait dans Applications → Extensions (ou par le script de la phase 2). Les captures "
    "suivantes montrent le formulaire de création d'une extension PJSIP puis sa confirmation."))
story.append(capture("creating-new-extention.png", "création d'une nouvelle extension PJSIP dans FreePBX", max_h=92 * mm))
story.append(capture("extension-created.png", "extension créée et visible dans FreePBX", max_h=92 * mm))
story.append(h2("4.4  Groupes d'appels"))
story.append(P(
    "Les postes 1001–1010 partagent <font face='DVM'>namedcallgroup</font> / <font face='DVM'>namedpickupgroup</font> "
    "« phase2 ». La sonnerie simultanée est portée par le numéro <b>8000</b> dans "
    "<font face='DVM'>extensions_custom.conf</font> (module GUI ringgroups indisponible lors du déploiement — "
    "timeout du miroir Sangoma, réinstallation possible ultérieurement)."))
story.append(keypoints([
    "10 extensions PJSIP (1001–1010) créées par script, secrets ≥ 16 caractères hors Git.",
    "Deux profils média : classique UDP/TLS + SRTP (1001–1002) et WebRTC WSS + DTLS (1003–1010).",
    "Jamais d'édition manuelle des fichiers générés : UI/scripts → MariaDB → fwconsole reload.",
    "Sonnerie de groupe 8000 en dialplan custom, call/pickup group « phase2 ».",
]))
story.append(PageBreak())

# ═══ 5. Phase 3 IVR ══════════════════════════════════════════════════════
story.append(h1("5.  IVR, files d'attente et services avancés (Phase 3)"))
story.append(h2("5.1  Plan de numérotation des services"))
story.append(table(
    ["Numéro", "Fonction", "Détail"],
    [
        ["7000", "Routage horaire", "GotoIfTime : lun–ven 09:00–17:59 → 7010, sinon message de fermeture"],
        ["7010", "IVR intelligent (AGI Python)", "phase3_intelligent_ivr.py — VIP via phase3-vip.txt, logique horaire/langue, saisie d'extension"],
        ["7020", "File ACD phase3-support", "Stratégie leastrecent, membres 1001–1010, MixMonitor vers /var/spool/asterisk/monitor/"],
        ["7101–7110", "Files individuelles ivr-ext-*", "Une file par poste, accessibles depuis l'IVR"],
        ["8001", "ConfBridge à PIN", "Salle phase3-<PIN> (PIN de test 1234, à changer)"],
        ["8100", "Test MixMonitor", "Enregistrement + renvoi messagerie 1001"],
        ["8000", "Sonnerie de groupe (Phase 2)", "Inchangé"],
    ],
    widths=[20 * mm, 52 * mm, CONTENT_W - 72 * mm],
))
story.append(P(
    "Le dialplan Phase 3 est appliqué de façon idempotente par "
    "<font face='DVM'>scripts/phase3-apply-asterisk.sh</font> (bloc balisé BEGIN_PHASE3/END_PHASE3 dans "
    "<font face='DVM'>extensions_custom.conf</font>) ; les files viennent de "
    "<font face='DVM'>phase3/asterisk/queues-ivr.conf</font> injecté dans <font face='DVM'>queues_custom.conf</font>. "
    "Cette approche fichiers custom + app_queue/ConfBridge fonctionne sans dépendre des modules GUI Sangoma "
    "(dont le téléchargement des packs de sons échouait en timeout)."))
story.append(h2("5.2  IVR pour toutes les extensions"))
story.append(capture("ivr-interface-for-all-extentions.png",
                     "IVR et files d'attente couvrant l'ensemble des extensions (phase 3)", max_h=100 * mm))
story.append(h2("5.3  Enregistrements"))
story.append(P(
    "Les appels de la file support sont enregistrés par <b>MixMonitor</b> vers "
    "<font face='DVM'>/var/spool/asterisk/monitor/</font>. Le montage d'un export NFS pour centraliser les "
    "fichiers est prévu côté infrastructure (non monté automatiquement)."))
story.append(keypoints([
    "Chaîne d'accueil : 7000 (horaires) → 7010 (IVR AGI Python, VIP) → 7020 (file ACD) ou 7101–7110.",
    "Application idempotente par scripts (blocs balisés) — indépendante des modules GUI queues/ivr.",
    "Conférence à PIN 8001 ; enregistrements MixMonitor, NFS à monter côté infra.",
]))
story.append(PageBreak())

# ═══ 6. WebRTC ═══════════════════════════════════════════════════════════
story.append(h1("6.  WebRTC — WSS, DTLS-SRTP et pont média"))
story.append(h2("6.1  Couche transport"))
story.append(P(
    "Asterisk expose son mini-serveur HTTP sur <b>8088</b> (lab) et <b>TLS 8089</b> pour le <b>WSS</b> : les "
    "clients WebRTC ouvrent la signalisation SIP sur <font face='DVM'>wss://pbx.local:8089/ws</font> "
    "(chemin /ws imposé par Asterisk). Le transport PJSIP <font face='DVM'>transport-wss</font> est lié à "
    "0.0.0.0:8089. Sous FreePBX, <font face='DVM'>enable-webrtc-websocket.sh</font> force via "
    "<font face='DVM'>fwconsole setting</font> (HTTPENABLED, HTTPBINDADDRESS, HTTPTLSBINDADDRESS) l'écoute sur "
    "toutes les interfaces, car le fichier généré impose sinon 127.0.0.1. Les certificats sont ceux du "
    "Certificate Manager (<font face='DVM'>/etc/asterisk/keys/default.crt|key</font>) ; le module "
    "<font face='DVM'>res_srtp.so</font> est indispensable (sans lui : erreur 488 / « SRTP support module is "
    "not loaded »)."))
story.append(table(
    ["Paramètre endpoint WebRTC", "Valeur", "Rôle"],
    [
        ["transport", "transport-wss", "Signalisation SIP over WebSocket TLS"],
        ["media_encryption", "dtls", "DTLS-SRTP exigé par les navigateurs/WebRTC"],
        ["ice_support / use_avpf / rtcp_mux", "yes / yes / yes", "ICE, profil AVPF, multiplexage RTCP"],
        ["Codecs", "Opus + ulaw/alaw (G.722 possible)", "Aligner avec l'autre jambe pour éviter le transcodage"],
    ],
    widths=[58 * mm, 48 * mm, CONTENT_W - 106 * mm],
))
story.append(h2("6.2  Configuration SIP côté client"))
story.append(capture("sip-config.png", "configuration SIP du client Asaphone (serveur, extension, transport WSS)",
                     max_h=95 * mm, max_w=70 * mm))
story.append(h2("6.3  Appel mixte UDP ↔ WebRTC : Asterisk B2BUA"))
story.append(P(
    "Asterisk ne fait pas du WebRTC de bout en bout : il <b>termine</b> la jambe WebRTC (WSS + DTLS-SRTP + ICE) "
    "et ressort une jambe RTP classique vers le poste UDP. Le pont média est donc toujours sur le PBX ; il faut "
    "des codecs communs (ou du transcodage Opus ↔ G.711, au prix de CPU). Un échec de négociation SDP se "
    "manifeste par un « 488 Not Acceptable Here » alors que la signalisation WSS est correcte."))
story.append(schema("fig-seq-appel-1001-1003.png",
                    "séquence d'appel 1001 (UDP/SRTP) ↔ 1003 (WSS/DTLS-SRTP) via le B2BUA (d'après webrtc/README.md)",
                    max_h=150 * mm))
story.append(P(
    "Piège applicatif documenté : un REGISTER avec <font face='DVM'>Contact: *</font> et "
    "<font face='DVM'>Expires: 0</font> désenregistre tous les contacts du poste — à réserver au logout "
    "explicite, sinon le PBX voit l'endpoint « Unreachable » et bascule vers la messagerie. Autre point de "
    "vigilance relevé dans les logs : « DTLS packet dropped, ICE not completed yet » — un souci ICE/STUN côté "
    "client, pas un problème serveur."))
story.append(keypoints([
    "Signalisation WebRTC : wss://pbx.local:8089/ws — WSS TLS 8089, certificats Certman, res_srtp chargé.",
    "Endpoint WebRTC : dtls + ice + avpf + rtcp_mux + Opus/G.711 ; poste classique inchangé.",
    "Asterisk est B2BUA : deux jambes média distinctes, transcodage si codecs non alignés.",
]))
story.append(PageBreak())

# ═══ 7. Client Asaphone ══════════════════════════════════════════════════
story.append(h1("7.  Client Asaphone (Flutter)"))
story.append(h2("7.1  Présentation"))
story.append(P(
    "Asaphone (dépôt <font face='DVM'>github.com/Asaph-D/asaphone</font>, projet OBSCURA) est le softphone "
    "multiplateforme du projet : Flutter pour Android, Windows et iOS. Il consomme la provision du serveur "
    "(bootstrap.json → API provision → credentials SIP) et parle WebRTC au PBX : signalisation "
    "<b>SIP over WSS</b>, média <b>DTLS-SRTP</b> (audio/vidéo), messagerie instantanée par <b>SIP MESSAGE</b>, "
    "messagerie vocale et appels de groupe via les API du PBX. Les détails d'implémentation interne du client "
    "(architecture Flutter, gestion d'état) sont documentés dans le dépôt client ; côté serveur, son contrat "
    "d'interface est entièrement décrit par le bootstrap et la mini-API."))
story.append(schema("fig-usecase-asaphone.png",
                    "cas d'utilisation Asaphone ↔ PBX (provision, appels, chat, messagerie, groupes, VPN)",
                    max_h=135 * mm))
story.append(h2("7.2  Accueil et connexion"))
story.append(P(
    "Au premier lancement, l'utilisateur choisit entre « J'ai déjà mes identifiants » (saisie manuelle ou scan "
    "d'un QR déjà reçu) et « M'enregistrer » (parcours e-mail décrit au chapitre 15)."))
story.append(two_captures(
    "welcome-login.png", "écran d'accueil / connexion d'Asaphone",
    "config-page.png", "page de configuration du client Asaphone", each_h=95 * mm))
story.append(h2("7.3  Clavier et appels"))
story.append(two_captures(
    "clavier.png", "clavier d'appel d'Asaphone (numérotation interne)",
    "appel-audio.png", "appel audio en cours (démonstration)", each_h=95 * mm))
story.append(h2("7.4  Appels vidéo"))
story.append(P(
    "La vidéo suit le même chemin que l'audio : SDP WebRTC négocié via WSS, média DTLS-SRTP. Les codecs vidéo "
    "annoncés par le bootstrap du dépôt sont <b>VP8</b> et <b>H.264</b>."))
story.append(capture("appel-video.png", "appel vidéo en cours (démonstration)", max_h=100 * mm, max_w=64 * mm))
story.append(keypoints([
    "Softphone Flutter unique pour Android/Windows/iOS, entièrement provisionné par le serveur.",
    "Connexion : REGISTER WSS 8089 + DTLS-SRTP ; vidéo VP8/H.264 annoncée par bootstrap.json.",
    "Chat, voicemail et groupes s'appuient sur les endpoints /provision du PBX (chapitres 8, 9, 15).",
]))
story.append(PageBreak())

# ═══ 8. Messagerie & chat ════════════════════════════════════════════════
story.append(h1("8.  Messagerie vocale et chat"))
story.append(h2("8.1  Messagerie vocale (app_voicemail)"))
story.append(P(
    "Toutes les boîtes 1001–1010 sont créées et mappées par <font face='DVM'>phase2-enable-voicemail.php</font> "
    "(contexte default, nom « Poste &lt;ext&gt; », PIN = 4 derniers chiffres à personnaliser, "
    "<font face='DVM'>attach=yes</font>, <font face='DVM'>envelope=yes</font>, <font face='DVM'>saycid=yes</font>, "
    "<font face='DVM'>vmdelete=no</font>). Un incident documenté — « No entry in voicemail config file » — "
    "venait de mailboxes manquantes pour certaines extensions ; la remise en cohérence par script l'a corrigé."))
story.append(table(
    ["Élément", "Valeur"],
    [
        ["Consultation directe", "Codes *81001 … *81010 → boîte du poste 1001–1010 (apply-voicemail-codes.sh)"],
        ["Dépôt de message", "Automatique après le bip (comportement VoiceMail() standard, renvoi sur non-réponse/occupation)"],
        ["Notification e-mail", "Pièce jointe WAV (attach=yes) ; SMTP à configurer par poste dans l'UI"],
        ["Notification Asaphone", "asaphone-vm-notify.sh + hook — notification côté client via l'API provision"],
        ["Vérification", "asterisk -rx \"voicemail show users\" → default 1001 … default 1010"],
    ],
    widths=[46 * mm, CONTENT_W - 46 * mm],
))
story.append(h2("8.2  Chat — SIP MESSAGE"))
story.append(P(
    "La messagerie instantanée d'Asaphone passe par des requêtes <b>SIP MESSAGE</b> hors dialogue, routées par "
    "un bloc dédié du dialplan (<font face='DVM'>apply-message-dialplan.sh</font>, marqueurs "
    "BEGIN_SIP_MESSAGE/END_SIP_MESSAGE dans <font face='DVM'>extensions_custom.conf</font>). Le même flux "
    "porte les notifications de messagerie vocale. L'historique côté serveur est ingéré par "
    "<font face='DVM'>asaphone-chat-ingest.sh</font> (schéma <font face='DVM'>provision-schema-chat.sql</font>), "
    "ce qui permet au client de resynchroniser ses conversations via l'API provision."))
story.append(P(
    "Ce choix évite tout serveur XMPP séparé : la signalisation SIP existante transporte le texte, et le PBX "
    "reste le seul point d'authentification (mêmes credentials que la voix)."))
story.append(keypoints([
    "Boîtes vocales complètes 1001–1010, consultation par *8100X, pièce jointe WAV par e-mail.",
    "Chat = SIP MESSAGE dans le dialplan custom + ingestion en base pour resynchronisation client.",
    "Un seul référentiel d'identité : les credentials SIP servent à la voix, au chat et aux notifications.",
]))
story.append(PageBreak())

# ═══ 9. Groupes / ConfBridge ═════════════════════════════════════════════
story.append(h1("9.  Appels de groupe — ConfBridge"))
story.append(h2("9.1  Principe"))
story.append(P(
    "Le téléphone ne mixe jamais l'audio : il compose un seul numéro interne (<font face='DVM'>call_uri</font>) "
    "ou appelle l'API provision. C'est Asterisk <b>ConfBridge</b> qui crée la salle, invite les extensions "
    "(originate) et mixe. Les groupes créés dans Asaphone sont synchronisés vers le PBX "
    "(<font face='DVM'>groups/sync.php</font>) qui attribue à chaque groupe une salle "
    "<font face='DVM'>asaphone-grp-&lt;slug&gt;</font>."))
story.append(table(
    ["call_uri", "Usage"],
    [
        ["6000", "Salle par défaut (sans groupe en base) — annoncée par bootstrap (conference.default_call_uri)"],
        ["6001–6099", "Salles numériques réservées"],
        ["asaphone-grp-*", "Une salle par groupe synchronisé (call_uri attribué par le PBX)"],
        ["8001", "ConfBridge à PIN de la Phase 3 (salle phase3-<PIN>)"],
    ],
    widths=[38 * mm, CONTENT_W - 38 * mm],
))
story.append(h2("9.2  Séquence complète"))
story.append(schema("fig-seq-confbridge.png",
                    "appel de groupe : sync → INVITE call_uri → ConfBridge + originate des membres "
                    "(d'après docs/asaphone-group-conference.md)", max_h=140 * mm))
story.append(h2("9.3  Invitation en cours d'appel"))
story.append(P(
    "Depuis une salle active, le client peut inviter d'autres postes via "
    "<font face='DVM'>POST conference/invite.php</font> (liste d'extensions ou <font face='DVM'>auto:true</font> "
    "pour tout le groupe) : le PBX originate vers les invités, le client ne rouvre pas d'appel. "
    "L'authentification de ces API suit le modèle commun : paramètre <font face='DVM'>?ext=</font> + en-tête "
    "<font face='DVM'>X-Provision-Jti</font> (jti de session). Déploiement : "
    "<font face='DVM'>provision-schema-groups.sql</font> + <font face='DVM'>apply-conference-dialplan.sh</font>."))
story.append(keypoints([
    "Un appel de groupe = un seul INVITE client vers call_uri ; mixage 100 % côté ConfBridge.",
    "Salles : 6000 (défaut), 6001–6099, asaphone-grp-* par groupe synchronisé.",
    "Invitation à chaud par API (conference/invite.php), auth ext + X-Provision-Jti.",
]))
story.append(PageBreak())

# ═══ 10. Trunks ══════════════════════════════════════════════════════════
story.append(h1("10.  Trunks SIP — PSTN et inter-PBX"))
story.append(h2("10.1  Trois « trunks » à ne pas confondre"))
story.append(P(
    "Le mot trunk recouvre trois notions distinctes dans le projet : le <b>trunk SIP</b> (lien logique "
    "PBX ↔ opérateur ou PBX ↔ PBX, couche applicative), le <b>trunk VLAN 802.1Q</b> (port switch transportant "
    "plusieurs VLANs, couche 2 locale) et l'offre <b>trunk opérateur PSTN</b> (cas particulier du premier). "
    "Un trunk SIP ne relie jamais des LAN distants — c'est le rôle du VPN."))
story.append(schema("fig-comparatif-liaisons.png",
                    "comparatif extension PJSIP / trunk SIP / VPN WireGuard / VLAN / tunnel Cloudflare "
                    "(d'après docs/vpn.md et docs/trunk.md)", max_h=115 * mm))
story.append(h2("10.2  Ce qui fonctionne sans trunk"))
story.append(P(
    "Toute la téléphonie interne (extensions 1001–1010, appels mixtes UDP ↔ WSS, conférences, télétravail via "
    "VPN) fonctionne <b>sans aucun trunk</b> : ce sont des extensions PJSIP et le B2BUA. Le trunk devient "
    "nécessaire uniquement pour appeler ou être appelé depuis le PSTN (numéro DID) ou pour relier un second PBX."))
story.append(h2("10.3  État préconfiguré"))
story.append(table(
    ["Élément", "Détail"],
    [
        ["trunk-operateur-pstn", "Trunk opérateur — actif après renseignement de /root/trunks-secrets.env (hors Git)"],
        ["trunk-interpbx-site-b", "Trunk inter-PBX — réception depuis 192.168.1.0/24 et 10.200.0.0/24, préfixe 8"],
        ["Routes sortantes", "France (0XXXXXXXXX), International (00.), Inter-PBX — via apply-trunks.sh"],
        ["Route entrante", "Catch-all → IVR 7000"],
        ["Sécurité", "UFW ciblé sur les IP opérateur (pas de SIP « Anywhere ») ; IP FAI en ignoreip Fail2Ban si besoin"],
    ],
    widths=[46 * mm, CONTENT_W - 46 * mm],
))
story.append(keypoints([
    "Trunk SIP = couche applicative FreePBX ; il ne remplace ni VPN (L3) ni VLAN (L2).",
    "La téléphonie interne du projet n'exige aucun trunk ; PSTN/DID et inter-PBX en exigent un.",
    "Trunks et routes préconfigurés par apply-trunks.sh, secrets opérateur hors dépôt.",
]))
story.append(PageBreak())

# ═══ 11. VPN & accès Windows ═════════════════════════════════════════════
story.append(h1("11.  VPN WireGuard et accès distant"))
story.append(h2("11.1  Pourquoi un VPN"))
story.append(P(
    "Un softphone qui quitte le LAN du PBX perd tout : mDNS ne traverse pas Internet, l'IP privée du serveur "
    "devient injoignable, UFW et les localnets refusent les sources inconnues. Le scénario documenté "
    "(« M. Dupont passe sur 192.168.137.0/24 ») aboutit à « Registration failed ». La correction est un "
    "<b>VPN utilisateur WireGuard</b> : interface <font face='DVM'>wg0</font> sur le PBX (10.200.0.1, "
    "UDP 51820), clients en 10.200.0.x, et autorisation du sous-réseau tunnel — jamais du LAN distant — dans "
    "<font face='DVM'>EXTRA_LAN_CIDRS</font> puis <font face='DVM'>net-apply-site.sh</font>."))
story.append(h2("11.2  Enrôlement VPN par l'API (MVP sans compte)"))
story.append(P(
    "La connexion VPN d'Asaphone ne demande ni e-mail ni session : "
    "<font face='DVM'>POST vpn/enroll.php</font> avec un <font face='DVM'>device_id</font> stable retourne une "
    "URL de claim ; <font face='DVM'>GET vpn/claim.php?token=…</font> délivre la configuration WireGuard "
    "(plus les indications sip_server / wss_url). Une fois le tunnel actif, le client est « dans le réseau "
    "site ». La révocation d'un appareil passe par <font face='DVM'>vpn/revoke.php</font>. Cas CGNAT "
    "(Starlink) : pas d'UDP entrant — le relais <b>WG sur WebSocket</b> intégré "
    "(<font face='DVM'>install-wg-wss-relay.sh</font>, tunnel trycloudflare) transporte WireGuard vers "
    "127.0.0.1:51820."))
story.append(h2("11.3  Résolution pbx.local sous Windows"))
story.append(P(
    "macOS et Linux résolvent <font face='DVM'>pbx.local</font> par mDNS (Avahi côté serveur). Windows peut ne "
    "pas résoudre les noms .local : le script réseau régénère à chaque application le fichier "
    "<font face='DVM'>network/windows-hosts.txt</font> avec la ligne à copier — en administrateur — dans "
    "<font face='DVM'>C:\\Windows\\System32\\drivers\\etc\\hosts</font> :"))
story.append(Paragraph("192.168.1.80  pbx.local  pbx   # exemple généré — réseau 192.168.1.0/24", S["mono"]))
story.append(capture("editing-host-file-for-windows.png",
                     "édition du fichier hosts Windows pour résoudre pbx.local (accès distant / mDNS absent)",
                     max_h=92 * mm))
story.append(keypoints([
    "Le VPN (L3) est la seule réponse au softphone hors site ; autoriser 10.200.0.0/24, pas le LAN distant.",
    "Enrôlement VPN sans compte : enroll (device_id) → claim (.conf WireGuard) → tunnel actif ; revoke par API.",
    "CGNAT : relais WG-sur-WSS via tunnel Cloudflare, WireGuard vers 127.0.0.1:51820.",
    "Windows sans mDNS : ligne windows-hosts.txt à copier dans le fichier hosts.",
]))
story.append(PageBreak())

# ═══ 12. Sécurité ════════════════════════════════════════════════════════
story.append(h1("12.  Sécurité (Phase 4)"))
story.append(h2("12.1  Modèle en couches"))
story.append(P(
    "La sécurité n'est pas un bloc unique : elle est répartie en couches autour et dans le PBX, de la "
    "segmentation physique (L0) aux données au repos (L7). Le schéma suivant reprend l'état documenté de "
    "chaque couche."))
story.append(schema("fig-securite-couches.png",
                    "matrice des couches de sécurité L0–L7 (d'après security/cryptographic_implementation.md)",
                    max_h=125 * mm))
story.append(h2("12.2  Signalisation et média"))
story.append(bullets([
    "<b>TLS 5061</b> : transport PJSIP TLS avec certificat du Certificate Manager — la clé FreePBX "
    "<font face='DVM'>pjsipcertid</font> doit pointer vers un certificat valide, sinon le transport TLS "
    "s'expose sans cert_file (script phase4-assign-pjsip-tls-cert.php ; contrôle "
    "<font face='DVM'>pjsip show transport 0.0.0.0-tls</font>).",
    "<b>SRTP SDES</b> : <font face='DVM'>media_encryption=sdes</font> appliqué aux extensions 1001–1010 "
    "(phase4-enable-srtp-extensions.php) ; les terminaux doivent activer SRTP/SAVP.",
    "<b>DTLS-SRTP</b> : chiffrement média imposé par WebRTC sur les endpoints 1003–1010.",
    "<b>verify_client=no</b> pour les softphones sans certificat client ; le client doit faire confiance au "
    "certificat serveur (auto-signé accepté ou Let's Encrypt).",
]))
story.append(h2("12.3  Pare-feu et anti-abus"))
story.append(table(
    ["Mesure", "Configuration documentée"],
    [
        ["UFW", "default deny incoming ; SIP+RTP depuis 10.10.10.0/24 ; 5061/tcp restreint au LAN gestion (plus d'accès « Anywhere ») ; règles ciblées par IP opérateur pour les trunks"],
        ["Fail2Ban", "Jail asterisk : logpath /var/log/asterisk/full, backend auto, ports 5060/5061/5160/5161, bannissement /32 ; test par phase4-test-fail2ban-filter.sh (fail2ban-regex sur extrait)"],
        ["Mots de passe SIP", "Secrets aléatoires ≥ 16 caractères, rotation planifiée 90 j ; stockage FreePBX réversible par nécessité → accès base restreint, pas de diffusion"],
        ["MariaDB", "Identifiants AMPDB* dans /etc/freepbx.conf (jamais dans le dépôt) ; procédure de rotation ALTER USER + fwconsole reload"],
        ["Permissions", "Clés TLS www-data:asterisk 0640 (les 0600 cassent WSS) ; freepbx_chown.conf réapplique après chaque fwconsole start"],
    ],
    widths=[34 * mm, CONTENT_W - 34 * mm],
))
story.append(h2("12.4  Limite structurelle"))
story.append(P(
    "Un chiffrement de bout en bout strict poste-à-poste (sans déchiffrement sur le PBX) est incompatible avec "
    "le modèle B2BUA : Asterisk termine chaque jambe média pour ponter, transcoder, enregistrer (MixMonitor) et "
    "mixer (ConfBridge). Le modèle retenu est un chiffrement <i>par segment</i> : chaque jambe est chiffrée "
    "(SRTP ou DTLS-SRTP), le PBX étant un point de confiance."))
story.append(keypoints([
    "Défense en profondeur L0–L7 : VLAN, WireGuard, UFW/Fail2Ban, HTTPS, TLS 5061, SRTP/DTLS, QR one-shot, secrets.",
    "5061 n'est plus exposé « Anywhere » ; les trunks passent par des règles UFW ciblées par IP opérateur.",
    "Chiffrement par segment (le PBX est un point de confiance) — l'E2EE strict est hors modèle B2BUA.",
]))
story.append(PageBreak())

# ═══ 13. Monitoring ══════════════════════════════════════════════════════
story.append(h1("13.  Monitoring — Telegraf, InfluxDB, Grafana"))
story.append(h2("13.1  Chaîne de collecte"))
story.append(P(
    "La stack d'observabilité (Phase 3) tourne en Docker Compose dans <font face='DVM'>monitoring/</font> : "
    "<b>InfluxDB 2.7</b> (org voip, bucket asterisk, port 8086), <b>Grafana 11.4.0</b> (port 3000, datasource "
    "InfluxDB-VoIP et dashboard provisionnés par fichiers) et <b>Telegraf 1.33</b> dans une image maison "
    "<font face='DVM'>voip-telegraf:1.33-ami</font> en <font face='DVM'>network_mode: host</font> pour joindre "
    "l'AMI d'Asterisk sur 127.0.0.1:5038. Les images officielles n'ayant pas de plugin Asterisk, la collecte "
    "est faite par deux scripts Python appelés en <font face='DVM'>[[inputs.exec]]</font> toutes les 10 s : "
    "<font face='DVM'>ami_metrics.py</font> (AMI → mesure asterisk_core) et "
    "<font face='DVM'>log_metrics.py</font> (logs Asterisk et Fail2Ban montés en lecture seule). "
    "Prometheus est volontairement absent."))
story.append(schema("fig-monitoring-pipeline.png",
                    "pipeline Telegraf AMI → InfluxDB 2 → Grafana (d'après monitoring/docker-compose.yml et telegraf/)",
                    max_h=125 * mm))
story.append(h2("13.2  Exploitation en console"))
story.append(P(
    "Démarrage : <font face='DVM'>phase3-gen-monitoring-env.sh</font> génère les secrets de "
    "<font face='DVM'>monitoring/.env</font> (jamais commités), puis <font face='DVM'>docker compose up -d</font>. "
    "L'utilisateur AMI dédié « telegraf » (manager_custom.conf) doit avoir <font face='DVM'>write=command</font> "
    "pour l'action « core show channels »."))
story.append(schema("console-monitoring-cli.png",
                    "état de la stack et logs Telegraf en console (d'après monitoring/README.md et docker-compose.yml)",
                    max_h=95 * mm))
story.append(h2("13.3  Dashboards Grafana"))
story.append(P(
    "La datasource Flux et le tableau « VoIP / Asterisk — monitoring » (dossier VoIP) sont provisionnés "
    "automatiquement depuis <font face='DVM'>grafana/provisioning/</font> et "
    "<font face='DVM'>grafana/dashboards/voip-asterisk.json</font> : stats canaux / appels actifs et séries "
    "temporelles sur la mesure <font face='DVM'>asterisk_core</font>. Requête Flux type : "
    "<font face='DVM'>from(bucket: \"asterisk\") |&gt; range(start: -1h) |&gt; filter(fn: (r) =&gt; "
    "r._measurement == \"asterisk_core\")</font>."))
story.append(capture("grafana-welcome-page.png", "page d'accueil Grafana après connexion (stack monitoring)", max_h=92 * mm))
story.append(capture("monitoring.png", "dashboard VoIP / Asterisk — vue d'ensemble du monitoring", max_h=92 * mm))
story.append(keypoints([
    "Chaîne Telegraf (scripts AMI Python) → InfluxDB 2 (bucket asterisk) → Grafana (Flux) — sans Prometheus.",
    "Provisioning Grafana par fichiers : datasource + dashboard versionnés dans le dépôt.",
    "Ports 3000/8086 ouverts uniquement vers les LAN autorisés ; secrets dans monitoring/.env hors Git.",
]))
story.append(PageBreak())

# ═══ 14. Exploitation ════════════════════════════════════════════════════
story.append(h1("14.  Installation et exploitation"))
story.append(h2("14.1  Installation des outils (système vierge)"))
story.append(P(
    "INSTALLATION.md décrit le déploiement sur Debian 12 / Ubuntu 22.04 : paquets système, pile FreePBX 17 + "
    "Asterisk 20 (guide officiel), Docker pour le monitoring, puis service systemd. Les planches suivantes "
    "condensent les étapes et leurs critères de réussite — versions strictement issues du dépôt."))
story.append(schema("console-install-1-prerequis.png",
                    "phase d'installation (universelle) — prérequis OS et paquets (d'après INSTALLATION.md)",
                    max_h=105 * mm))
story.append(schema("console-install-2-asterisk-freepbx.png",
                    "phase d'installation (universelle) — Asterisk 20 LTS et FreePBX 17 (asterisk -V, fwconsole -V)",
                    max_h=95 * mm))
story.append(schema("console-install-3-docker-monitoring.png",
                    "phase d'installation (universelle) — Docker Compose v2 et stack monitoring (Influx 2.7, Grafana 11.4, Telegraf AMI)",
                    max_h=112 * mm))
story.append(schema("console-install-4-systemd.png",
                    "phase d'installation (universelle) — service systemd serveur-startup (ExecStart à adapter au chemin réel)",
                    max_h=105 * mm))
story.append(h2("14.2  Démarrage automatisé — serveur-startup.service"))
story.append(P(
    "Le boot complet du PBX est orchestré par <font face='DVM'>scripts/server-startup.sh</font> (unit "
    "<font face='DVM'>systemd/serveur-startup.service</font>, journal "
    "<font face='DVM'>/var/log/serveur-startup.log</font>). Le script est <b>résilient hors ligne</b> : le cœur "
    "PBX (FreePBX, permissions, Apache, profil réseau) démarre sans Internet ; les étapes Internet (tunnel "
    "Cloudflare, publication GitHub, relais WG) sont optionnelles et marquées OK ou SKIP sans bloquer. "
    "Les trois planches suivantes reproduisent fidèlement le déroulé et le style console du script "
    "(<font face='DVM'>scripts/lib/startup-console.sh</font> : banner, barre de progression, ✓/⚠/○)."))
story.append(schema("console-startup-1-banner.png",
                    "sortie console serveur-startup 1/3 — banner ASAPHONE et cœur PBX "
                    "(d'après scripts/server-startup.sh)", max_h=128 * mm))
story.append(schema("console-startup-2-coeur.png",
                    "sortie console serveur-startup 2/3 — FreePBX, WSS 8089, permissions, Apache, profil réseau, relais WG "
                    "(d'après scripts/server-startup.sh)", max_h=140 * mm))
story.append(schema("console-startup-3-resume.png",
                    "sortie console serveur-startup 3/3 — Internet optionnel (tunnel, sync bootstrap), HTTPS 443 et résumé final "
                    "(d'après scripts/server-startup.sh)", max_h=140 * mm))
story.append(h2("14.3  Ordre exact des étapes au boot"))
story.append(table(
    ["#", "Étape (label du script)", "Type"],
    [
        ["0", "Banner ASAPHONE (FreePBX · Provision · VoIP · VPN WireGuard) + date + rappels", "affichage"],
        ["1", "FreePBX chown.conf (VM + clés TLS + run)", "optionnelle"],
        ["2", "Permissions GUI FreePBX", "optionnelle"],
        ["3", "Permissions certificats TLS (pre-start)", "optionnelle"],
        ["4", "FreePBX (fwconsole start)", "optionnelle"],
        ["5", "WSS TLS 8089 (certs + reload)", "optionnelle"],
        ["6", "Permissions /var/run/asterisk (reload.lock + ctl)", "optionnelle"],
        ["7", "Permissions spool messagerie", "optionnelle"],
        ["8", "Sessions PHP (purge + chmod 1733)", "interne"],
        ["9", "Apache (restart)", "critique"],
        ["10", "Profil réseau site (UFW, mDNS, localnets) — net-apply-site.sh", "critique (warn si partiel)"],
        ["11", "Relais WG/WebSocket (Starlink 4G) + URL tunnel WG relay", "optionnelle (si script présent)"],
        ["12", "Cloudflare tunnel provision (start/restart, refresh trycloudflare si mode quick)", "optionnelle (skip si non activé)"],
        ["13", "Sync bootstrap (api_remote + relay WSS) — sync-global-config.sh --deploy", "optionnelle"],
        ["14", "Publication bootstrap → GitHub Pages (skip si GITHUB_BOOTSTRAP_PUBLISH ≠ yes)", "optionnelle"],
        ["15", "Apache HTTPS (443) — enable-apache-https.sh", "optionnelle"],
        ["16", "Résumé final (IP LAN, pbx.local, API distante) + « serveur-startup: OK <horodatage> »", "affichage"],
    ],
    widths=[10 * mm, CONTENT_W - 10 * mm - 40 * mm, 40 * mm],
))
story.append(h2("14.4  Appliquer la configuration FreePBX"))
story.append(P(
    "Toute modification dans l'UI FreePBX doit être suivie d'un « Apply Config » (équivalent "
    "<font face='DVM'>fwconsole reload</font>) qui régénère les fichiers Asterisk depuis la base :"))
story.append(capture("applying-changes.png", "application des changements FreePBX (Apply Config / fwconsole reload)",
                     max_h=90 * mm))
story.append(keypoints([
    "Un seul point d'entrée d'exploitation : systemctl start serveur-startup.service (log /var/log/serveur-startup.log).",
    "Cœur PBX sans Internet ; tunnel/GitHub/VPN distant en étapes optionnelles OK/SKIP non bloquantes.",
    "bootstrap.json régénéré après le refresh des tunnels pour éviter une api_remote périmée sur GitHub.",
    "Après toute modification UI : Apply Config (fwconsole reload).",
]))
story.append(PageBreak())

# ═══ 15. Provisioning ════════════════════════════════════════════════════
story.append(h1("15.  Provisionnement Asaphone de bout en bout"))
story.append(h2("15.1  Architecture de découverte"))
story.append(table(
    ["Couche", "URL / transport", "Rôle"],
    [
        ["Discovery", "GitHub Pages — bootstrap.json (statique)", "Toujours joignable ; indique api_lan, api_remote, wss_url, VPN"],
        ["API LAN", "https://pbx.local/provision", "register, verify, claim, session, VPN, groupes, chat"],
        ["API distante", "Tunnel Cloudflare (URL trycloudflare dans le bootstrap)", "Même PHP sur le PBX ; bootstrap republié au boot"],
        ["VPN", "WireGuard UDP 51820 (ou relais WSS si CGNAT)", "Accès réseau complet après claim du .conf"],
    ],
    widths=[24 * mm, 72 * mm, CONTENT_W - 96 * mm],
))
story.append(P(
    "GitHub Pages n'héberge qu'un JSON statique : toute la logique reste sur le PBX (Apache + PHP + MariaDB + "
    "SMTP Gmail), sans backend cloud séparé. Sur LAN le client utilise api_lan ; hors LAN, api_remote — jamais "
    "pbx.local avant l'établissement du tunnel."))
story.append(h2("15.2  Parcours d'inscription (politique auto)"))
story.append(P(
    "L'utilisateur qui choisit « M'enregistrer » saisit son e-mail ; le serveur envoie un code à 6 chiffres "
    "(TTL 15 min, haché en base). Après vérification, la politique <font face='DVM'>auto</font> attribue la "
    "prochaine extension libre du pool <b>1003–1010</b> et envoie par e-mail un <b>QR one-shot</b> (token de "
    "claim, validité 24 h) — jamais de secret SIP en clair dans le corps du mail. Une extension n'est "
    "réellement réservée (<font face='DVM'>taken=true</font>) qu'après authentification réussie "
    "(REGISTER → consume → statut provisioned)."))
story.append(capture("sign-up.png", "écran d'inscription Asaphone (parcours « M'enregistrer », saisie e-mail)",
                     max_h=95 * mm, max_w=64 * mm))
story.append(schema("fig-seq-provision.png",
                    "séquence de provisionnement : bootstrap → register/verify → QR → claim → REGISTER WSS → consume "
                    "(d'après security/asaphone-onboarding-flow.md)", max_h=145 * mm))
story.append(h2("15.3  Endpoints de la mini-API"))
story.append(table(
    ["Endpoint (provision/api/v1/)", "Méthode", "Rôle"],
    [
        ["register.php", "POST", "Saisie e-mail → envoi code de vérification (6 chiffres)"],
        ["verify.php", "POST", "Valide le code → attribution + QR (policy auto) ou pending_admin"],
        ["claim.php?token=", "GET", "Credentials SIP one-shot (extension, secret, server, wss, port)"],
        ["consume.php", "POST", "Révoque le token après premier REGISTER (jti, used=1)"],
        ["status.php / extension.php", "GET", "État d'un compte / état du pool 1003–1010"],
        ["session.php / reconnect.php", "GET/POST", "Session courante (jti) — inclut groups[], conference, endpoints"],
        ["vpn/enroll.php · vpn/claim.php · vpn/revoke.php", "POST/GET/POST", "Enrôlement VPN sans compte (device_id) et révocation"],
        ["groups/sync.php · groups/list.php · conference/invite.php", "POST/GET/POST", "Groupes et conférences (chapitre 9)"],
    ],
    widths=[64 * mm, 22 * mm, CONTENT_W - 86 * mm],
))
story.append(h2("15.4  Sécurité du flux"))
story.append(bullets([
    "Rate-limit par IP et par e-mail (fenêtre glissante 1 h, table provision_rate_limits).",
    "Réponses génériques contre l'énumération d'e-mails ; codes hachés (bcrypt) en base.",
    "QR à usage unique : jti révoqué au premier scan/REGISTER ; expiration 24 h.",
    "Secrets SMTP dans /etc/provision/provision-secrets.env (chmod 640, hors Git).",
    "API isolée de l'admin FreePBX (alias Apache /provision dédié, pas de session admin).",
]))
story.append(keypoints([
    "Découverte robuste : bootstrap.json statique sur GitHub Pages, republié au boot avec l'URL tunnel fraîche.",
    "Onboarding : e-mail → code 6 chiffres → QR chiffré one-shot → claim → REGISTER WSS → consume.",
    "Pool 1003–1010 : réservation effective seulement après authentification (provisioned).",
    "Aucun backend séparé : Apache + PHP + MariaDB + SMTP sur le PBX lui-même.",
]))
story.append(PageBreak())

# ═══ 16. Tests ═══════════════════════════════════════════════════════════
story.append(h1("16.  Tests et validations"))
story.append(h2("16.1  Validations réalisées (documentées dans le dépôt)"))
story.append(table(
    ["Domaine", "Validation", "Référence"],
    [
        ["Appels internes", "Appel 1001 (UDP) → 1003 (WSS/WebRTC) : sonnerie, décrochage, bridge OK", "docs/trunk.md §« point de vigilance » / docs/vpn.md §11"],
        ["QoS", "Règles mangle DSCP EF présentes (iptables -t mangle -L OUTPUT) ; contrôle tcpdump en appel réel prescrit", "Plan-adressage §4.2/4.3"],
        ["Extensions", "pjsip show endpoints ; SELECT extension,name,voicemail sur users (1001–1010)", "S2 §3"],
        ["Messagerie", "voicemail show users → default 1001…1010 ; dépôt après bip validé", "docs/Rapport-messagerie-vocale"],
        ["WSS/TLS", "http show status → HTTPS 8089 ; pjsip show transports → wss 0.0.0.0:8089", "webrtc/README.md, network/run.txt"],
        ["Fail2Ban", "fail2ban-regex sur extrait du log full (script phase4-test-fail2ban-filter.sh)", "S4 §4"],
        ["Provision", "Scénario curl complet register → verify → claim → consume ; état du pool par extension.php", "asaphone-onboarding-flow §15"],
        ["Monitoring", "Mesure asterisk_core visible dans Grafana (Explore, Flux)", "S3 §1"],
    ],
    widths=[26 * mm, 92 * mm, CONTENT_W - 118 * mm],
))
story.append(h2("16.2  Commandes de contrôle rapide"))
story.append(Paragraph(
    "sudo asterisk -rx \"pjsip show contacts\"        # postes enregistrés<br/>"
    "sudo asterisk -rx \"http show status\"           # HTTPS/WSS 8089<br/>"
    "ss -tlnp | grep -E '8088|8089|443'              # sockets en écoute<br/>"
    "sudo ufw status numbered                        # pare-feu<br/>"
    "sudo fail2ban-client status asterisk            # jail anti-abus<br/>"
    "journalctl -u serveur-startup.service -b        # démarrage<br/>"
    "curl -sk https://pbx.local/provision/           # santé mini-API", S["mono"]))
story.append(P(
    "Un avertissement connu subsiste dans les logs d'appels WebRTC — « DTLS packet dropped. ICE not completed "
    "yet » — identifié comme un comportement média côté client (négociation ICE), sans impact sur "
    "l'établissement de l'appel observé."))
story.append(keypoints([
    "Chaque phase embarque ses vérifications (SQL, CLI Asterisk, curl, fail2ban-regex) rejouables.",
    "Le scénario provision complet est testable en curl sans client mobile.",
    "Un point d'attention ICE/DTLS côté client est documenté, l'appel s'établit.",
]))
story.append(PageBreak())

# ═══ 17. Limites ═════════════════════════════════════════════════════════
story.append(h1("17.  Limites et travaux futurs"))
story.append(h2("17.1  Limites actuelles"))
story.append(bullets([
    "<b>Trunk VLAN 10 physique</b> : la config OS est prête, mais le trunk 802.1Q switch ↔ hyperviseur et le "
    "trust DSCP restent à raccorder côté infrastructure (Plan-adressage §8).",
    "<b>Trunks opérateur</b> : préconfigurés mais inactifs tant que les identifiants opérateur "
    "(/root/trunks-secrets.env) ne sont pas renseignés — pas d'appels PSTN à ce stade.",
    "<b>SMTP par poste</b> : la notification e-mail de messagerie vocale requiert la configuration SMTP/adresse "
    "par extension dans l'UI (S2 §7, marqué « à faire »).",
    "<b>Module ringgroups GUI</b> : non installé (timeout miroir Sangoma) ; contourné par le dialplan 8000.",
    "<b>Secrets SIP réversibles</b> en base (limitation FreePBX) : compensé par restriction d'accès et rotation, "
    "pas de hachage irréversible.",
    "<b>E2EE strict</b> : hors modèle B2BUA (chapitre 12) ; chiffrement par segment assumé.",
    "<b>URL trycloudflare éphémères</b> (mode quick) : d'où la republication du bootstrap à chaque boot ; un "
    "tunnel nommé avec domaine propre supprimerait cette dépendance.",
    "<b>NFS enregistrements</b> : montage non automatisé (S3 §2).",
    "<b>MFA admin FreePBX</b> et chiffrement disque : non déployés (cryptographic_implementation.md).",
]))
story.append(h2("17.2  Pistes d'évolution"))
story.append(bullets([
    "Activer un trunk opérateur (TLS si disponible) + routes DID vers l'IVR 7000 déjà en place.",
    "Basculer le tunnel Cloudflare en mode nommé (domaine dédié) et certificat Let's Encrypt sur l'UI.",
    "Automatiser la rotation 90 j des secrets SIP (scripts fwconsole + calendrier).",
    "Étendre les dashboards Grafana (files 7020, Fail2Ban, qualité RTP) à partir des mesures log_metrics.",
    "Finaliser côté client les écrans de la roadmap onboarding (phase 4 du flux).",
]))
story.append(keypoints([
    "Les limites sont identifiées et tracées dans les documents de phase — aucune n'est bloquante pour l'usage interne.",
    "Priorités : raccordement VLAN physique, trunk opérateur, tunnel nommé, rotation automatisée des secrets.",
]))
story.append(PageBreak())

# ═══ 18. Conclusion ══════════════════════════════════════════════════════
story.append(h1("18.  Conclusion"))
story.append(P(
    "Le projet aboutit à une plateforme VoIP complète, documentée et reproductible : un PBX Asterisk 20 / "
    "FreePBX 17 durci (TLS, SRTP, UFW, Fail2Ban), segmenté (VLAN voix 10.10.10.0/24, QoS DSCP EF), supervisé "
    "(Telegraf → InfluxDB → Grafana) et entièrement automatisé au démarrage (serveur-startup.service, résilient "
    "hors ligne). Le softphone Asaphone en est le prolongement naturel : provisionné par QR one-shot via une "
    "mini-API embarquée sur le PBX, découvert par un bootstrap statique GitHub Pages, connecté en WSS/DTLS-SRTP, "
    "et enrichi de services concrets — chat SIP MESSAGE, messagerie vocale notifiée, appels de groupe ConfBridge, "
    "VPN WireGuard auto-enrôlé jusque derrière un CGNAT."))
story.append(P(
    "La méthode retenue — phases incrémentales, scripts idempotents versionnés, secrets hors dépôt, "
    "vérifications sur flux réels — rend l'ensemble opérable par un tiers : chaque brique se rejoue depuis le "
    "dépôt, du plan d'adressage au dashboard Grafana. Les travaux restants (trunk opérateur, raccordement VLAN "
    "physique, tunnel nommé) sont circonscrits et préparés par la configuration déjà en place."))
story.append(keypoints([
    "Chaîne complète démontrée : provision QR → REGISTER WSS → appels audio/vidéo chiffrés → supervision.",
    "Infrastructure as code : scripts + systemd + Docker versionnés, secrets exclus du dépôt.",
    "Base saine pour l'ouverture PSTN et le multi-sites (trunks préconfigurés, VPN opérationnel).",
]))
story.append(PageBreak())

# ═══ Annexes ═════════════════════════════════════════════════════════════
story.append(h1("Annexe A — Matrice des ports"))
story.append(table(
    ["Port(s)", "Protocole", "Service", "Exposition (UFW)"],
    [
        ["5060, 5160", "UDP/TCP", "SIP (signalisation)", "VLAN voix 10.10.10.0/24 (+ MGMT si autorisé)"],
        ["5061, 5161", "TCP (TLS)", "SIP TLS", "LAN gestion + VLAN voix (plus d'« Anywhere » en Phase 4)"],
        ["10000–20000", "UDP", "RTP / SRTP (média) — marqué DSCP EF", "CIDR voix + LAN autorisés"],
        ["8088", "TCP", "HTTP Asterisk (WebRTC lab)", "LAN autorisés (option)"],
        ["8089", "TCP (TLS)", "WSS WebRTC (wss://pbx.local:8089/ws)", "LAN autorisés + VPN"],
        ["80, 443", "TCP", "Apache : UI FreePBX + /provision", "LAN / VPN"],
        ["3000", "TCP", "Grafana", "LAN autorisés (option monitoring)"],
        ["8086", "TCP", "InfluxDB 2", "LAN autorisés (option monitoring)"],
        ["5038", "TCP", "AMI Asterisk (Telegraf)", "127.0.0.1 uniquement (permit)"],
        ["51820", "UDP", "WireGuard wg0", "Internet (forward box) ou relais WSS si CGNAT"],
    ],
    widths=[26 * mm, 22 * mm, 62 * mm, CONTENT_W - 110 * mm],
))
story.append(Spacer(1, 6))
story.append(h1("Annexe B — Extensions et numéros de service"))
story.append(table(
    ["Numéro", "Type", "Description"],
    [
        ["1001–1002", "Extension PJSIP classique", "SIP UDP/TLS + SRTP SDES (Zoiper, téléphones IP)"],
        ["1003–1010", "Extension PJSIP WebRTC", "WSS 8089 + DTLS-SRTP (Asaphone) — pool de provisionnement"],
        ["8000", "Sonnerie de groupe", "Dial simultané 1001–1010 (45 s), dialplan custom Phase 2"],
        ["7000 / 7010", "Accueil / IVR", "Routage horaire puis IVR AGI Python"],
        ["7020", "File ACD", "phase3-support (leastrecent) + MixMonitor"],
        ["7101–7110", "Files individuelles", "ivr-ext-1001 … ivr-ext-1010"],
        ["8001", "ConfBridge à PIN", "Salle phase3-<PIN>"],
        ["8100", "Test enregistrement", "MixMonitor + renvoi messagerie 1001"],
        ["6000 / 6001–6099", "Conférences Asaphone", "Salle par défaut / salles numériques réservées"],
        ["asaphone-grp-*", "Conférences de groupe", "Une salle ConfBridge par groupe synchronisé"],
        ["*81001–*81010", "Messagerie directe", "Consultation de la boîte du poste correspondant"],
    ],
    widths=[30 * mm, 42 * mm, CONTENT_W - 72 * mm],
))
story.append(PageBreak())
story.append(h1("Annexe C — Scripts et services du dépôt serveur"))
story.append(table(
    ["Chemin", "Rôle"],
    [
        ["scripts/server-startup.sh + scripts/lib/startup-console.sh", "Orchestration du boot + rendu console (banner, OK/WARN/SKIP)"],
        ["systemd/serveur-startup.service", "Unit systemd du démarrage (ExecStart vers server-startup.sh)"],
        ["scripts/net-apply-site.sh + network/site.env", "Profil réseau site : UFW, mDNS, localnets, windows-hosts.txt, monitoring"],
        ["scripts/sync-global-config.sh + network/global-config.env", "Source unique de config (IP LAN, tunnel) ; --deploy régénère bootstrap.json"],
        ["scripts/phase2-create-extensions.php / phase2-enable-voicemail.php", "Extensions 1001–1010 + boîtes vocales"],
        ["scripts/phase3-apply-asterisk.sh / apply-ivr-queues.sh", "Dialplan IVR/files Phase 3 (blocs balisés)"],
        ["scripts/phase4-apply-all.sh (fail2ban, TLS cert, SRTP)", "Durcissement Phase 4 enchaîné"],
        ["scripts/enable-webrtc-websocket.sh / fix-wss-tls.sh / align-pjsip-site.sh", "WebRTC : HTTP/WSS 8089, certificats, profils endpoints"],
        ["scripts/provision-install.sh + provision/ + scripts/provision-schema*.sql", "Mini-API PHP + schémas SQL (provision, chat, groupes, VM, VPN)"],
        ["scripts/apply-message-dialplan.sh / apply-conference-dialplan.sh / apply-voicemail-codes.sh", "Chat SIP MESSAGE, salles 6000/asaphone-grp-*, codes *8100X"],
        ["scripts/apply-trunks.sh + network/trunks.env", "Trunks PSTN / inter-PBX + routes (secrets hors Git)"],
        ["scripts/install-wg-wss-relay.sh / install-provision-tunnel.sh / publish-bootstrap-github.sh", "Relais WG-WSS, tunnel Cloudflare, publication GitHub Pages"],
        ["monitoring/docker-compose.yml + telegraf/ + grafana/", "Stack InfluxDB 2.7 / Grafana 11.4 / Telegraf 1.33-ami"],
    ],
    widths=[92 * mm, CONTENT_W - 92 * mm],
))
story.append(Spacer(1, 6))
story.append(h1("Annexe D — Glossaire"))
story.append(table(
    ["Terme", "Définition"],
    [
        ["AGI / AMI", "Interfaces Asterisk : Gateway Interface (scripts dialplan) / Manager Interface (contrôle & événements, port 5038)"],
        ["B2BUA", "Back-to-back user agent : le PBX termine chaque jambe d'appel et les ponte (média jamais direct entre postes)"],
        ["ConfBridge", "Application Asterisk de conférence (mixage serveur)"],
        ["DSCP EF", "Classe QoS Expedited Forwarding (valeur 46 / 0x2e) appliquée aux paquets RTP"],
        ["DTLS-SRTP", "Chiffrement média WebRTC : clés négociées en DTLS, flux en SRTP"],
        ["ICE / AVPF / rtcp-mux", "Négociation de candidats réseau / profil RTP retour rapide / RTP et RTCP sur un même port — exigences WebRTC"],
        ["jti", "Identifiant unique de token (JWT ID) — sert à la révocation one-shot du QR et à l'auth des API"],
        ["localnets", "Réseaux déclarés « locaux » à PJSIP (pas de réécriture NAT pour ces sources)"],
        ["mDNS", "Multicast DNS (Avahi) — résolution pbx.local sans serveur DNS"],
        ["PJSIP", "Pile SIP moderne d'Asterisk (chan_pjsip), remplaçant chan_sip"],
        ["SDES", "Échange de clés SRTP dans le SDP (media_encryption=sdes) pour les postes classiques"],
        ["Trunk SIP", "Lien SIP permanent PBX ↔ opérateur ou PBX ↔ PBX (≠ trunk VLAN 802.1Q)"],
        ["WSS", "WebSocket sécurisé (TLS) — signalisation SIP des clients WebRTC sur le port 8089"],
    ],
    widths=[36 * mm, CONTENT_W - 36 * mm],
))
story.append(PageBreak())
story.append(h1("Annexe E — Chemins GitHub de référence"))
story.append(table(
    ["Sujet", "Chemin (dépôt Asaph-D/serveur, branche main)"],
    [
        ["Architecture & flux", "Architecture-VoIP-communication-composants.md"],
        ["Adressage & QoS", "Plan-adressage-reseau-VoIP-QoS.md"],
        ["Phases 2 / 3 / 4", "S2-Phase2-Utilisateurs-Extensions.md · S3-Phase3-IVR-Monitoring.md · S4-Phase4-Securite-complete.md"],
        ["Installation", "INSTALLATION.md"],
        ["WebRTC", "webrtc/README.md"],
        ["VPN / trunks / interface / groupes", "docs/vpn.md · docs/implement-VPN.md · docs/trunk.md · docs/interface-guids.md · docs/asaphone-group-conference.md"],
        ["Sécurité & onboarding", "security/cryptographic_implementation.md · security/asaphone-onboarding-flow.md"],
        ["Monitoring", "monitoring/README.md · monitoring/docker-compose.yml · monitoring/telegraf/ · monitoring/grafana/"],
        ["Boot & réseau", "scripts/server-startup.sh · scripts/lib/startup-console.sh · systemd/serveur-startup.service · network/"],
        ["Provision (API + bootstrap)", "provision/ · network/github-pages/provision/bootstrap.json · scripts/provision-*.php|sql|sh"],
        ["Client Asaphone", "github.com/Asaph-D/asaphone (Flutter — Android / Windows / iOS)"],
    ],
    widths=[42 * mm, CONTENT_W - 42 * mm],
))
story.append(Spacer(1, 6))
story.append(h1("Annexe F — Inventaire des captures (capture/)"))
story.append(table(
    ["Fichier", "Contenu", "Chapitre"],
    [
        ["welcome-login.png", "Accueil / connexion Asaphone", "7"],
        ["sign-up.png", "Inscription (saisie e-mail)", "15"],
        ["config-page.png", "Page de configuration du client", "7"],
        ["sip-config.png", "Configuration SIP (WSS)", "6"],
        ["clavier.png", "Clavier d'appel", "7"],
        ["appel-audio.png", "Appel audio en cours (démo)", "7"],
        ["appel-video.png", "Appel vidéo en cours (démo)", "7"],
        ["freePBX-interface.png", "Tableau de bord FreePBX", "4"],
        ["extension-interface.png", "Liste des extensions", "4"],
        ["creating-new-extention.png", "Création d'une extension", "4"],
        ["extension-created.png", "Extension créée", "4"],
        ["applying-changes.png", "Apply Config FreePBX", "14"],
        ["ivr-interface-for-all-extentions.png", "IVR / files pour toutes les extensions", "5"],
        ["monitoring.png", "Vue d'ensemble monitoring", "13"],
        ["grafana-welcome-page.png", "Accueil Grafana", "13"],
        ["editing-host-file-for-windows.png", "Fichier hosts Windows (pbx.local)", "11"],
    ],
    widths=[62 * mm, 78 * mm, CONTENT_W - 140 * mm],
))
story.append(Spacer(1, 10))
story.append(Paragraph(
    "Fin du document — généré automatiquement (matplotlib + reportlab). "
    "Les informations non présentes dans les dépôts sont signalées « non documenté dans le dépôt » ; "
    "aucun secret (.env, tokens, mots de passe SIP/DB) n'est reproduit.", S["caption"]))


def main():
    doc = ReportDoc(OUT)
    doc.multiBuild(story)
    print("PDF généré :", OUT)


if __name__ == "__main__":
    main()
