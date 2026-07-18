#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rapport technique ASAPHONE — rendu HTML/CSS → PDF (WeasyPrint).
Produit : asterisk-asaphone-report.pdf (racine du dépôt).

Contenu aligné sur les documents du dépôt serveur ; captures réelles de
capture/, schémas générés de figures/. Aucun secret reproduit.
"""

import os
import base64
from weasyprint import HTML

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "asterisk-asaphone-report.pdf")

# ═══════════════════════════════ Helpers ═════════════════════════════════

_FIG = {"n": 0, "chap": "—", "reg": []}


def _num(caption):
    _FIG["n"] += 1
    _FIG["reg"].append((_FIG["n"], caption, _FIG["chap"]))
    return _FIG["n"]


def fig(src, caption, w=100):
    return (f'<figure style="width:{w}%">'
            f'<img src="{src}" alt=""/>'
            f'<figcaption><b>Fig. {_num(caption)}</b> · {caption}</figcaption></figure>')


def cap(src, caption, w=88):
    return fig(f"capture/{src}", caption, w)


def sch(src, caption, w=100):
    return fig(f"figures/{src}", caption, w)


def duo(src1, cap1, src2, cap2):
    return (f'<div class="duo">'
            f'<figure><img src="capture/{src1}"/>'
            f'<figcaption><b>Fig. {_num(cap1)}</b> · {cap1}</figcaption></figure>'
            f'<figure><img src="capture/{src2}"/>'
            f'<figcaption><b>Fig. {_num(cap2)}</b> · {cap2}</figcaption></figure>'
            f'</div>')


def callout(kind, title, body):
    icons = {"key": "◆", "info": "ℹ", "warn": "⚠", "next": "➜", "goal": "🎯"}
    return (f'<div class="co co-{kind}"><div class="co-t">{icons.get(kind,"◆")}&nbsp; {title}</div>'
            f'<div class="co-b">{body}</div></div>')


def keypoints(items):
    lis = "".join(f"<li>{i}</li>" for i in items)
    return (f'<div class="co co-key"><div class="co-t">◆&nbsp; L\'essentiel du chapitre</div>'
            f'<div class="co-b"><ul class="kp">{lis}</ul></div></div>')


def nxt(text):
    return callout("next", "Et ensuite ?", text)


def tbl(headers, rows, cls="tbl", widths=None):
    colgroup = ""
    if widths:
        colgroup = "<colgroup>" + "".join(f'<col style="width:{w}%"/>' for w in widths) + "</colgroup>"
    thead = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
    return f'<table class="{cls}">{colgroup}<thead>{thead}</thead><tbody>{body}</tbody></table>'


def chap(num, cid, title, lead):
    _FIG["chap"] = f"Ch. {int(num)}" if num.isdigit() else f"Annexe {num}"
    return (f'<h2 class="chap" id="{cid}"><span class="chip">{num}</span> {title}</h2>'
            f'<p class="lead">{lead}</p>')


def part(pid, roman, title, subtitle, chapters):
    lis = "".join(f'<div class="pt-item"><span>{n}</span>{t}</div>' for n, t in chapters)
    return (f'<div class="part" id="{pid}">'
            f'<div class="pt-top"><div class="pt-kicker">PARTIE</div>'
            f'<div class="pt-num">{roman}</div></div>'
            f'<h1 class="pt-title">{title}</h1>'
            f'<div class="pt-sub">{subtitle}</div>'
            f'<div class="pt-list">{lis}</div>'
            f'</div>')


# ═══════════════════════════════ Filigrane ═══════════════════════════════

def _watermark_uri(fill, opacity):
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='794' height='1123' "
        "viewBox='0 0 794 1123'>"
        f"<text x='397' y='580' font-family='Ubuntu,sans-serif' font-size='92' "
        f"font-weight='700' letter-spacing='22' fill='{fill}' fill-opacity='{opacity}' "
        "text-anchor='middle' transform='rotate(-45 397 561)'>ASAPHONE</text>"
        f"<text x='397' y='680' font-family='Ubuntu,sans-serif' font-size='26' "
        f"letter-spacing='10' fill='{fill}' fill-opacity='{opacity}' "
        "text-anchor='middle' transform='rotate(-45 397 561)'>RAPPORT TECHNIQUE · 2026</text>"
        "</svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


WM_DARK_INK = _watermark_uri("#1B4F72", "0.055")   # pages claires
WM_WHITE = _watermark_uri("#FFFFFF", "0.045")      # pages sombres (couverture, parties)

# ═══════════════════════════════ CSS ═════════════════════════════════════

CSS = """
:root{}
@page {
  size: A4;
  margin: 21mm 16mm 17mm 16mm;
  background: url("__WM_INK__") no-repeat center center;
  background-size: 210mm 297mm;
  @top-left  { content: "ASAPHONE · Rapport technique"; font: 600 6.8pt "Ubuntu"; color:#8CA3B5; letter-spacing:.12em; text-transform:uppercase; }
  @top-right { content: string(chap); font: 6.8pt "Ubuntu"; color:#8CA3B5; }
  @bottom-center { content: counter(page); font: 700 8pt "Ubuntu"; color:#1B4F72; }
  @bottom-right { content: "Juillet 2026"; font: 6.5pt "Ubuntu"; color:#B0BEC9; }
}
@page clean { margin:0;
  @top-left{content:none} @top-right{content:none}
  @bottom-center{content:none} @bottom-right{content:none} }

html { font-size: 9.6pt; }
body { font-family:"Ubuntu","DejaVu Sans",sans-serif; color:#22313F;
       line-height:1.52; hyphens:auto; }
p { margin:0 0 5.5pt; text-align:justify; }
b, strong { color:#16324A; }
code, .mono { font-family:"Ubuntu Mono","DejaVu Sans Mono",monospace; font-size:8.8pt;
       background:#EFF3F6; padding:0 2.5pt; border-radius:2.5pt; color:#14425F; }
ul { margin:2pt 0 7pt 14pt; padding:0; }
li { margin:0 0 2.6pt; text-align:justify; }

/* ── Couverture ─────────────────────────────────────────────────────── */
.cover { page: clean; width:210mm; height:297mm;
  background: url("__WM_WHITE__") no-repeat center center / 210mm 297mm,
              linear-gradient(152deg,#071B2C 0%, #0E3050 42%, #1B4F72 68%, #12695C 100%);
  color:#fff; position:relative; }
.cv-in { padding: 26mm 20mm; }
.cv-brand { font-size:10pt; letter-spacing:.42em; color:#7FD4C3; font-weight:700; }
.cv-rule { width:34mm; height:1.4mm; background:linear-gradient(90deg,#2EC4A5,#7D3C98); border-radius:1mm; margin:7mm 0 9mm; }
.cv-title { font-size:29pt; line-height:1.16; font-weight:700; letter-spacing:-.01em; }
.cv-title .thin { font-weight:300; color:#BFD8E8; }
.cv-sub { margin-top:7mm; font-size:11.5pt; color:#A8C6DA; line-height:1.55; max-width:150mm; }
.cv-kpis { margin-top:11mm; }
.kpi { display:inline-block; width:39mm; margin:0 3.4mm 3.4mm 0; padding:4mm 4.5mm;
  background:rgba(255,255,255,.07); border:0.4pt solid rgba(255,255,255,.22); border-radius:2.4mm; vertical-align:top;}
.kpi b { display:block; font-size:15.5pt; color:#7FD4C3; letter-spacing:-.02em;}
.kpi span { font-size:6.9pt; color:#C4D9E6; text-transform:uppercase; letter-spacing:.09em; line-height:1.3; display:block; margin-top:1mm;}
.cv-meta { margin-top:10mm; border-collapse:collapse; width:100%; }
.cv-meta td { padding:2.3mm 3.5mm; font-size:8.6pt; border-bottom:.35pt solid rgba(255,255,255,.16); color:#D9E7F0; }
.cv-meta td:first-child { color:#7FD4C3; font-weight:700; width:34mm; text-transform:uppercase; font-size:7.2pt; letter-spacing:.08em;}
.cv-meta a { color:#fff; text-decoration:none; border-bottom:.5pt dotted #7FD4C3;}
.cv-foot { position:absolute; bottom:12mm; left:20mm; right:20mm; font-size:7.4pt; color:#7E9DB2;
  border-top:.4pt solid rgba(255,255,255,.18); padding-top:3mm; }

/* ── Page accroche ──────────────────────────────────────────────────── */
.hook { page: clean; width:210mm; height:297mm; position:relative;
  background: url("__WM_INK__") no-repeat center center / 210mm 297mm, #F5F8FA; }
.hk-band { height:64mm; background:linear-gradient(135deg,#0E3050,#1B4F72 60%,#7D3C98); color:#fff; padding:20mm 20mm 0; }
.hk-k { font-size:8pt; letter-spacing:.35em; color:#9FE8D8; font-weight:700; }
.hk-t { font-size:20pt; font-weight:700; margin-top:4mm; }
.hk-body { padding:12mm 20mm; }
.hk-scene { background:#fff; border-radius:3mm; padding:8mm 9mm; border:.4pt solid #D8E2EA;
  box-shadow:0 1mm 3mm rgba(27,79,114,.09); }
.hk-scene p { font-size:10.3pt; line-height:1.72; color:#33475A; }
.hk-scene .q { font-size:26pt; color:#148F77; line-height:0; vertical-align:-8pt; font-family:Georgia,serif;}
.hk-steps { margin-top:8mm; }
.hk-step { display:inline-block; width:41mm; vertical-align:top; margin-right:3mm; }
.hk-step .n { display:inline-block; width:7.5mm; height:7.5mm; border-radius:50%;
  background:#148F77; color:#fff; font-weight:700; text-align:center; line-height:7.5mm; font-size:9.5pt;}
.hk-step .arrow { color:#148F77; font-size:13pt; float:right; margin-top:1mm;}
.hk-step h4 { margin:2.5mm 0 1mm; font-size:9.2pt; color:#1B4F72;}
.hk-step p { font-size:7.8pt; color:#5B7183; line-height:1.45; text-align:left;}
.hk-punch { margin-top:9mm; font-size:11.5pt; color:#1B4F72; font-weight:600; line-height:1.6; text-align:center;}
.hk-punch em { color:#148F77; font-style:normal; }

/* ── Sommaire ───────────────────────────────────────────────────────── */
.toc h1 { font-size:17pt; color:#1B4F72; margin:0 0 8mm; bookmark-level:none; }
.toc .grp { margin:5.5mm 0 2mm; font-size:8pt; font-weight:700; letter-spacing:.22em;
  color:#7D3C98; text-transform:uppercase; border-bottom:.7pt solid #E4D5EE; padding-bottom:1.2mm;}
.toc a { display:block; text-decoration:none; color:#2C3E50; font-size:9.4pt; margin:1.7mm 0; }
.toc a .n { display:inline-block; width:9mm; color:#148F77; font-weight:700; }
.toc a::after { content: leader(dotted) " " target-counter(attr(href), page);
  color:#1B4F72; font-weight:700; }

/* ── Pages de partie ────────────────────────────────────────────────── */
.part { page: clean; width:210mm; height:297mm; color:#fff; padding:30mm 22mm;
  background: url("__WM_WHITE__") no-repeat center center / 210mm 297mm,
              linear-gradient(160deg,#0A2238 0%,#123B5C 55%,#1B4F72 100%);
  position:relative;}
.pt-top { border-bottom:.5pt solid rgba(255,255,255,.25); padding-bottom:4mm; }
.pt-kicker { font-size:9pt; letter-spacing:.5em; color:#7FD4C3; font-weight:700; display:inline-block;}
.pt-num { font-size:52pt; font-weight:300; color:rgba(255,255,255,.92); float:right; margin-top:-9mm; }
.pt-title { font-size:24pt; font-weight:700; margin:16mm 0 4mm; bookmark-level:1; }
.pt-sub { font-size:10.5pt; color:#A8C6DA; line-height:1.6; max-width:150mm; }
.pt-list { margin-top:14mm; }
.pt-item { padding:3.4mm 0; border-bottom:.35pt solid rgba(255,255,255,.14); font-size:10pt; color:#DCE9F2;}
.pt-item span { display:inline-block; width:11mm; color:#7FD4C3; font-weight:700; }

/* ── Chapitres ──────────────────────────────────────────────────────── */
h2.chap { string-set: chap content(); bookmark-level:2;
  font-size:14.5pt; color:#132F45; margin:2mm 0 3mm; padding-bottom:2.2mm;
  border-bottom:1.6pt solid #148F77; page-break-after:avoid; }
h2.chap .chip { display:inline-block; background:#1B4F72; color:#fff; border-radius:2mm;
  font-size:10.5pt; padding:1mm 2.8mm; margin-right:2.5mm; vertical-align:1pt; }
p.lead { font-size:10pt; color:#4A6274; font-style:italic; margin:0 0 6pt; text-align:justify;}
h3 { font-size:11pt; color:#1B4F72; margin:8pt 0 3pt; page-break-after:avoid; bookmark-level:3;}
h3::before { content:"› "; color:#148F77; font-weight:700;}
h4 { font-size:9.8pt; color:#7D3C98; margin:6pt 0 2pt; page-break-after:avoid; bookmark-level:none;}

/* ── Tableaux ───────────────────────────────────────────────────────── */
table.tbl { width:100%; border-collapse:collapse; margin:4pt 0 8pt; font-size:8.4pt; }
.tbl th { background:#1B4F72; color:#fff; text-align:left; padding:2.6mm 2.6mm;
  font-size:7.9pt; letter-spacing:.03em; }
.tbl td { padding:2.1mm 2.6mm; border-bottom:.4pt solid #DCE4EA; vertical-align:top; line-height:1.42;}
.tbl tr:nth-child(even) td { background:#F4F7F9; }
.tbl tr { page-break-inside:avoid; }
table.tbl.teal th { background:#148F77; }
table.tbl.purple th { background:#7D3C98; }

/* ── Callouts ───────────────────────────────────────────────────────── */
.co { border-radius:2mm; padding:3.4mm 4.5mm; margin:5pt 0 8pt; page-break-inside:avoid; font-size:8.8pt;}
.co-t { font-weight:700; font-size:8.6pt; letter-spacing:.05em; text-transform:uppercase; margin-bottom:1.6mm;}
.co-b p { margin:0 0 3pt; }
.co-key  { background:#EAF7F3; border-left:2.6pt solid #148F77; } .co-key .co-t{color:#0E6B58;}
.co-info { background:#EAF2F9; border-left:2.6pt solid #1B4F72; } .co-info .co-t{color:#1B4F72;}
.co-warn { background:#FBEEEC; border-left:2.6pt solid #C0392B; } .co-warn .co-t{color:#9A2E22;}
.co-goal { background:#F3EBF8; border-left:2.6pt solid #7D3C98; } .co-goal .co-t{color:#6A2F84;}
.co-next { background:#FDF6E7; border-left:2.6pt solid #C9971C; } .co-next .co-t{color:#8F6A0E;}
ul.kp { margin:0 0 0 12pt; } ul.kp li { margin-bottom:2pt; }

/* ── Figures ────────────────────────────────────────────────────────── */
figure { margin:6pt auto 9pt; text-align:center; page-break-inside:avoid; }
figure img { max-width:100%; border:.4pt solid #D5DEE6; border-radius:1.6mm; }
figcaption { font-size:7.7pt; color:#63788A; margin-top:1.8mm; line-height:1.4; font-style:italic;}
figcaption .path { color:#9AAAB8; font-size:7pt; }
.duo { text-align:center; page-break-inside:avoid; }
.duo figure { display:inline-block; width:47%; vertical-align:top; margin:4pt 1% 8pt; }
.duo figure img { max-height:118mm; width:auto; max-width:100%; }
img.phone { max-height:105mm; width:auto; }

/* ── Console / code ─────────────────────────────────────────────────── */
pre.term { background:#14181F; color:#D5DBE3; font-family:"Ubuntu Mono","DejaVu Sans Mono",monospace;
  font-size:8pt; line-height:1.5; padding:4mm 5mm; border-radius:2.2mm; margin:4pt 0 8pt;
  white-space:pre-wrap; page-break-inside:avoid;}
pre.term .c { color:#56C1D6; } pre.term .g { color:#5FD38D; } pre.term .d { color:#7B8794; }

/* ── Cartes de concepts ─────────────────────────────────────────────── */
.cptgrid { margin:4pt 0 6pt; }
.cpt { display:inline-block; vertical-align:top; box-sizing:border-box;
  width:48.4%; margin:0 1.2% 3mm 0;
  background:#fff; border:.4pt solid #D8E2EA; border-left:2.8pt solid #148F77;
  border-radius:1.8mm; padding:2.8mm 3.8mm; page-break-inside:avoid; }
.cpt.alt { border-left-color:#7D3C98; }
.cpt .t { display:block; color:#1B4F72; font-size:9.6pt; font-weight:700; margin-bottom:1.2mm; }
.cpt .t small { color:#148F77; font-weight:600; font-size:7.4pt; }
.cpt p { font-size:8.2pt; margin:0; color:#33475A; text-align:justify; line-height:1.48; }

/* Divers */
.pb { page-break-before:always; }
.avoid { page-break-inside:avoid; }
.small { font-size:8pt; color:#63788A; }
hr.sep { border:none; border-top:.5pt solid #DCE4EA; margin:7pt 0; }
"""

# ═══════════════════════════════ HTML ════════════════════════════════════

H = []
A = H.append

CSS = CSS.replace("__WM_INK__", WM_DARK_INK).replace("__WM_WHITE__", WM_WHITE)

A('<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">')
A('<title>ASAPHONE — Rapport technique</title>')
A(f"<style>{CSS}</style></head><body>")

# ─────────────────────────────── COUVERTURE ──────────────────────────────
A("""
<div class="cover"><div class="cv-in">
  <div class="cv-brand">A&nbsp;S&nbsp;A&nbsp;P&nbsp;H&nbsp;O&nbsp;N&nbsp;E</div>
  <div class="cv-rule"></div>
  <div class="cv-title">La téléphonie d'entreprise,<br/>
  <span class="thin">reconstruite de bout en bout.</span></div>
  <div class="cv-sub">Rapport technique — conception, sécurisation et exploitation d'une plateforme
  VoIP souveraine : PBX <b>Asterisk 20 / FreePBX 17</b>, softphone <b>Flutter</b> multiplateforme,
  provisionnement par QR, VPN WireGuard et supervision temps réel.</div>

  <div class="cv-kpis">
    <div class="kpi"><b>10</b><span>extensions PJSIP<br/>1001 – 1010</span></div>
    <div class="kpi"><b>2</b><span>profils média<br/>SRTP &amp; DTLS-WebRTC</span></div>
    <div class="kpi"><b>4</b><span>phases de déploiement<br/>adressage → sécurité</span></div>
    <div class="kpi"><b>3</b><span>pattes réseau<br/>MGMT · VLAN 10 · VPN</span></div>
    <div class="kpi"><b>8</b><span>couches de sécurité<br/>L0 → L7</span></div>
    <div class="kpi"><b>17</b><span>étapes de boot<br/>automatisées (systemd)</span></div>
    <div class="kpi"><b>&lt; 2 min</b><span>onboarding utilisateur<br/>e-mail → QR → appel</span></div>
    <div class="kpi"><b>0</b><span>backend cloud<br/>tout vit sur le PBX</span></div>
  </div>

  <table class="cv-meta">
    <tr><td>Dépôt serveur</td><td><a href="https://github.com/Asaph-D/serveur">github.com/Asaph-D/serveur</a> — branche main</td></tr>
    <tr><td>Dépôt client</td><td><a href="https://github.com/Asaph-D/asaphone">github.com/Asaph-D/asaphone</a> — Flutter (Android · Windows · iOS)</td></tr>
    <tr><td>Cœur VoIP</td><td>Asterisk 20 LTS (réf. 20.18.2) · FreePBX 17 · PJSIP · ConfBridge · WebRTC</td></tr>
    <tr><td>Supervision</td><td>Telegraf 1.33 (AMI) → InfluxDB 2.7 → Grafana 11.4</td></tr>
  </table>

  <div class="cv-foot">Rapport technique ASAPHONE · Juillet 2026 · Document reproductible —
  aucun secret (tokens, mots de passe, .env) n'est reproduit.</div>
</div></div>
""")

# ─────────────────────────────── ACCROCHE ────────────────────────────────
A("""
<div class="hook">
  <div class="hk-band">
    <div class="hk-k">ENTRÉE&nbsp;DE&nbsp;JEU</div>
    <div class="hk-t">Deux minutes, un QR code, un appel.</div>
  </div>
  <div class="hk-body">
    <div class="hk-scene">
      <p><span class="q">“</span>&nbsp;Lundi, 8&nbsp;h&nbsp;47. Une nouvelle collaboratrice ouvre Asaphone sur son
      téléphone. Elle n'a ni compte, ni identifiants, ni contact avec l'administrateur : elle saisit son
      adresse e-mail, tape le code à six chiffres reçu dans sa boîte, puis scanne le QR qui arrive dans la
      foulée. À 8&nbsp;h&nbsp;49, son poste <b>1007</b> est enregistré sur le PBX en WebSocket sécurisé ;
      elle compose <b>1001</b> et son premier appel — chiffré de bout de jambe en bout de jambe — traverse
      le VLAN voix avec la priorité réseau d'un paquet marqué or.&nbsp;<span class="q">”</span></p>
    </div>
    <div class="hk-steps">
      <div class="hk-step"><span class="n">1</span><span class="arrow">➜</span>
        <h4>S'inscrire</h4><p>E-mail + code à 6 chiffres (validité 15 min, haché en base).</p></div>
      <div class="hk-step"><span class="n">2</span><span class="arrow">➜</span>
        <h4>Scanner</h4><p>QR one-shot chiffré reçu par e-mail — extension attribuée du pool.</p></div>
      <div class="hk-step"><span class="n">3</span><span class="arrow">➜</span>
        <h4>Se connecter</h4><p>REGISTER wss://pbx.local:8089/ws, token révoqué au premier usage.</p></div>
      <div class="hk-step"><span class="n">4</span>
        <h4>Appeler</h4><p>Audio/vidéo DTLS-SRTP, chat, messagerie, conférences — sans configuration.</p></div>
    </div>
    <div class="hk-punch">Ce document raconte comment cette simplicité apparente est
    <em>fabriquée</em> : par un PBX durci, un réseau segmenté, une API de provisionnement
    embarquée et un démarrage entièrement automatisé.</div>
  </div>
</div>
""")

# ─────────────────────────────── SOMMAIRE ────────────────────────────────
A("""
<div class="toc pb">
<h1>Sommaire</h1>
<div class="grp">Partie I — Cadrage</div>
<a href="#ch1"><span class="n">01</span>Introduction</a>
<a href="#concepts"><span class="n">◆</span>Définition des concepts clés</a>
<a href="#ch2"><span class="n">02</span>Problématique</a>
<a href="#ch3"><span class="n">03</span>Contexte d'entreprise et approche retenue</a>
<div class="grp">Partie II — Conception</div>
<a href="#ch4"><span class="n">04</span>Architecture générale</a>
<a href="#ch5"><span class="n">05</span>Réseau : adressage, VLAN voix et QoS</a>
<a href="#ch6"><span class="n">06</span>Sécurité en profondeur (L0 → L7)</a>
<div class="grp">Partie III — Réalisation</div>
<a href="#ch7"><span class="n">07</span>Extensions et administration FreePBX</a>
<a href="#ch8"><span class="n">08</span>Services d'appel : IVR, files, conférences et groupes</a>
<a href="#ch9"><span class="n">09</span>WebRTC : WSS, DTLS-SRTP et pont média</a>
<a href="#ch10"><span class="n">10</span>Le client Asaphone</a>
<a href="#ch11"><span class="n">11</span>Messagerie vocale et chat</a>
<a href="#ch12"><span class="n">12</span>Provisionnement de bout en bout</a>
<div class="grp">Partie IV — Exploitation</div>
<a href="#ch13"><span class="n">13</span>Accès distant : VPN WireGuard, tunnels et trunks</a>
<a href="#ch14"><span class="n">14</span>Supervision : Telegraf → InfluxDB → Grafana</a>
<a href="#ch15"><span class="n">15</span>Installation et démarrage automatisé</a>
<a href="#ch16"><span class="n">16</span>Validation et tests</a>
<div class="grp">Partie V — Bilan</div>
<a href="#ch17"><span class="n">17</span>Limites et perspectives</a>
<a href="#ch18"><span class="n">18</span>Conclusion</a>
<div class="grp">Annexes</div>
<a href="#axa"><span class="n">A</span>Matrice des ports</a>
<a href="#axb"><span class="n">B</span>Plan de numérotation complet</a>
<a href="#axc"><span class="n">C</span>Glossaire</a>
<a href="#axd"><span class="n">D</span>Table des figures</a>
</div>
""")

# ═══════════════════════ PARTIE I — CADRAGE ══════════════════════════════
A(part("p1", "I", "Cadrage",
       "Avant la technique, le pourquoi : ce que coûte une téléphonie subie, ce qu'exige une "
       "téléphonie choisie, et la stratégie adoptée pour passer de l'une à l'autre.",
       [("01", "Introduction"), ("02", "Problématique"),
        ("03", "Contexte d'entreprise et approche retenue")]))

# ── 1. Introduction ──────────────────────────────────────────────────────
A('<div class="pb"></div>')
A(chap("01", "ch1", "Introduction",
       "Un projet de téléphonie complet : du plan d'adressage au doigt qui décroche."))
A("""
<p>La téléphonie d'entreprise est un service que l'on remarque uniquement quand il tombe. Derrière
chaque appel « qui marche », il y a un empilement précis : un réseau qui isole et priorise la voix,
un cœur SIP qui route et ponte, du chiffrement à chaque segment, des identités provisionnées sans
friction, et une exploitation qui survit aux redémarrages comme aux coupures Internet.</p>

<p><b>ASAPHONE</b> couvre l'intégralité de cet empilement, avec deux composants jumeaux&nbsp;:
d'un côté un <b>PBX Asterisk 20 LTS</b> administré par <b>FreePBX 17</b> sur une VM Ubuntu — dépôt
<code>Asaph-D/serveur</code> — et de l'autre un <b>softphone Flutter multiplateforme</b> (Android,
Windows, iOS) — dépôt <code>Asaph-D/asaphone</code>, projet OBSCURA. Le premier fournit le service ;
le second le rend accessible sans qu'aucun utilisateur n'ait jamais à connaître un port, un codec ou
un certificat.</p>
""")
A("<h3>Ce que le lecteur va traverser</h3>")
A(tbl(["Partie", "Question à laquelle elle répond", "Chapitres"],
      [["I — Cadrage", "Pourquoi construire plutôt que louer ? Quelles contraintes structurent tout le reste ?", "1 – 3"],
       ["II — Conception", "Comment l'architecture, le réseau et la sécurité sont-ils pensés <i>avant</i> la première extension ?", "4 – 6"],
       ["III — Réalisation", "Comment les services concrets (postes, IVR, WebRTC, chat, provision) sont-ils construits ?", "7 – 12"],
       ["IV — Exploitation", "Comment on y accède de loin, comment on l'observe, comment il démarre tout seul ?", "13 – 16"],
       ["V — Bilan", "Qu'est-ce qui reste à faire, et qu'est-ce que le projet démontre ?", "17 – 18"]],
      widths=[18, 62, 20]))
A(callout("info", "Conventions de lecture",
          "Les illustrations sont numérotées en continu (Fig. 1, Fig. 2…) et récapitulées en annexe D. "
          "Les adresses IP montrées sont les valeurs d'exemple documentées (<code>pbx.local</code>, "
          "<code>10.10.10.10</code>, <code>192.168.1.80</code>…) — l'IP LAN réelle varie par site et vit "
          "dans la configuration du serveur. Aucun secret n'est reproduit."))
A(nxt("Avant d'entrer dans le vif, la section suivante fixe le vocabulaire : chaque concept manipulé "
      "dans ce rapport y est défini en quelques lignes. Le chapitre 2 posera ensuite la problématique."))

# ── Définition des concepts clés ─────────────────────────────────────────
A('<h2 class="chap" id="concepts"><span class="chip">◆</span> Définition des concepts clés</h2>')
A('<p class="lead">Douze notions suffisent à lire ce rapport sans être spécialiste en téléphonie — '
  'les voici, définies dans le contexte du projet.</p>')

def cpt(term, tag, definition, alt=False):
    cls = "cpt alt" if alt else "cpt"
    small = f' <small>· {tag}</small>' if tag else ""
    return f'<div class="{cls}"><span class="t">{term}{small}</span><p>{definition}</p></div>'

A('<h3>Le socle : transporter la voix sur un réseau de données</h3>')
A('<div class="cptgrid">'
  + cpt("VoIP — voix sur IP", "principe",
        "Technique qui transforme la voix en paquets de données transportés sur un réseau IP "
        "(LAN, Internet), au lieu d'une ligne téléphonique dédiée. Toute la plateforme repose "
        "sur ce principe : un appel est un flux de paquets comme un autre — mais qui ne tolère "
        "ni retard ni perte.")
  + cpt("PBX / IPBX", "le cœur",
        "Le « central téléphonique » de l'entreprise : il enregistre les postes, route les appels, "
        "héberge les services (messagerie, conférences, files d'attente). Ici, le PBX est le logiciel "
        "libre <b>Asterisk 20</b>, administré par l'interface web <b>FreePBX 17</b>.")
  + cpt("SIP — la signalisation", "protocole",
        "Protocole qui gère la « conversation administrative » d'un appel : s'enregistrer "
        "(REGISTER), inviter un correspondant (INVITE), raccrocher (BYE). Le SIP transporte "
        "la sonnette et le carnet d'adresses — jamais la voix elle-même.")
  + cpt("RTP / SRTP — le média", "protocole",
        "Une fois l'appel accepté, la voix et la vidéo circulent en <b>RTP</b>, un flux continu de "
        "paquets UDP (ports 10000–20000 ici). <b>SRTP</b> en est la version chiffrée : indispensable "
        "pour qu'une capture réseau ne permette pas de réécouter la conversation.")
  + cpt("Codec", "compression",
        "Algorithme qui compresse la voix avant transport : <b>G.711</b> (qualité téléphone, simple), "
        "<b>Opus</b> (qualité supérieure, robuste aux réseaux mobiles — le choix de WebRTC), "
        "<b>VP8/H.264</b> pour la vidéo. Deux postes doivent en partager au moins un — sinon le PBX transcode.")
  + cpt("Extension / softphone", "les postes",
        "L'<b>extension</b> est l'identité téléphonique interne d'un utilisateur (ici 1001 à 1010) ; "
        "le <b>softphone</b> est le téléphone logiciel qui la porte — application mobile ou de bureau "
        "(Asaphone, Zoiper) plutôt que combiné physique.")
  + '</div>')

A('<h3>Les technologies différenciantes du projet</h3>')
A('<div class="cptgrid">'
  + cpt("WebRTC", "temps réel", 
        "Norme de communication temps réel née du web : signalisation via <b>WebSocket sécurisé "
        "(WSS)</b>, média chiffré en <b>DTLS-SRTP</b>, négociation de chemin réseau par <b>ICE</b>. "
        "C'est la pile utilisée par Asaphone — elle traverse bien les réseaux mobiles et n'exige "
        "aucune configuration du poste client.", alt=True)
  + cpt("B2BUA — back-to-back user agent", "architecture",
        "Mode de fonctionnement d'Asterisk : chaque appel est <i>terminé</i> sur le PBX puis "
        "<i>ré-émis</i> vers l'autre poste, en deux jambes indépendantes. C'est ce qui permet à un "
        "téléphone SIP classique de converser avec un client WebRTC — le PBX traduit au milieu.", alt=True)
  + cpt("VLAN & QoS (DSCP)", "réseau",
        "Le <b>VLAN</b> découpe un réseau physique en segments étanches — ici le VLAN 10 est réservé "
        "à la voix. La <b>QoS</b> marque chaque paquet voix d'une étiquette de priorité "
        "(<b>DSCP EF</b>, « expedited forwarding ») que les équipements servent en premier : "
        "l'appel reste fluide même si le réseau est chargé.", alt=True)
  + cpt("VPN WireGuard / NAT & CGNAT", "accès distant",
        "Le <b>VPN</b> crée un tunnel chiffré qui donne à un poste distant une adresse du réseau de "
        "l'entreprise — comme s'il était au bureau. Le <b>NAT</b> (et son extension opérateur, le "
        "<b>CGNAT</b> des connexions 4G/Starlink) masque les adresses et bloque les connexions "
        "entrantes : c'est l'obstacle que le VPN — et son relais WebSocket — contourne.", alt=True)
  + cpt("Provisionnement & bootstrap", "onboarding",
        "Le <b>provisionnement</b> est la configuration automatique d'un poste : l'utilisateur "
        "scanne un QR, l'application reçoit identifiants et réglages. Le <b>bootstrap</b> est le "
        "fichier de découverte publié par le serveur qui indique au client où se trouvent l'API, "
        "le WSS et le VPN — le client ne connaît rien d'avance.", alt=True)
  + cpt("IVR, file ACD & ConfBridge", "services",
        "L'<b>IVR</b> est le serveur vocal interactif (« tapez 1 pour… ») ; la <b>file ACD</b> met "
        "les appelants en attente et les distribue aux agents disponibles ; <b>ConfBridge</b> est la "
        "salle de conférence d'Asterisk, qui mixe l'audio de tous les participants côté serveur.", alt=True)
  + '</div>')

A(callout("info", "Et la supervision ?",
          "Observer la plateforme (appels actifs, canaux, attaques bloquées) repose sur un trio "
          "standard : un <b>collecteur</b> (Telegraf) interroge le PBX, une <b>base de séries "
          "temporelles</b> (InfluxDB) archive les mesures, un <b>tableau de bord</b> (Grafana) les "
          "affiche. Le chapitre 14 lui est consacré."))
A(nxt("Le vocabulaire est posé. Le chapitre 2 formule la question de départ : pourquoi construire "
      "cette plateforme plutôt que louer un service cloud ?"))

# ── 2. Problématique ─────────────────────────────────────────────────────
A(chap("02", "ch2", "Problématique",
       "Quatre tensions à résoudre simultanément — et qui, prises séparément, ont des solutions contradictoires."))
A("""
<p>Formulée en une phrase, la question centrale du projet est la suivante&nbsp;:</p>
""")
A(callout("goal", "Question centrale",
          "<i>Comment offrir à une petite structure une téléphonie <b>souveraine</b> (auto-hébergée, "
          "sans dépendance cloud), <b>sécurisée de bout en bout</b>, <b>utilisable par des non-techniciens "
          "en moins de deux minutes</b>, et <b>exploitable par une seule personne</b> — y compris quand "
          "Internet est coupé ?</i>"))
A("""
<p>Cette question se décompose en quatre tensions, chacune arbitrée dans ce rapport&nbsp;:</p>
""")
A(tbl(["#", "Tension", "Pourquoi c'est difficile", "Où c'est résolu"],
      [["T1", "<b>Qualité vs mutualisation</b> — la voix exige latence et priorité, le LAN bureautique n'en offre aucune",
        "Un paquet RTP retardé de 150 ms s'entend ; un e-mail retardé de 2 s, non. Mélanger les deux trafics condamne la voix aux aléas du réseau data.",
        "Ch. 5 — VLAN 10 dédié + DSCP EF"],
       ["T2", "<b>Ouverture vs surface d'attaque</b> — un PBX joignable de partout est un PBX attaqué de partout",
        "Le SIP exposé est scanné en continu (force brute REGISTER). Mais le télétravail et les mobiles exigent un accès hors LAN.",
        "Ch. 6 &amp; 13 — UFW deny + Fail2Ban + WireGuard + tunnel sortant"],
       ["T3", "<b>Simplicité vs rigueur</b> — l'utilisateur veut un QR, la sécurité veut des secrets forts et révocables",
        "Distribuer des mots de passe SIP de 16 caractères par oral ou par mail en clair ruine la politique de secrets.",
        "Ch. 12 — provision QR one-shot, token révoqué au premier usage"],
       ["T4", "<b>Automatisation vs fragilité</b> — un démarrage à 17 étapes doit réussir même sans Internet",
        "Tunnel Cloudflare, publication GitHub et VPN distant dépendent du réseau ; FreePBX, Apache et le LAN, non. Un boot monolithique casserait au premier lien coupé.",
        "Ch. 15 — étapes critiques vs optionnelles (OK/SKIP)"]],
      widths=[6, 27, 43, 24]))
A("""
<p>À ces tensions s'ajoute une contrainte de méthode, assumée dès la phase 1 du dépôt&nbsp;: la modalité
<b>« production d'abord »</b>. Aucune fonctionnalité n'est considérée acquise sur la foi d'une maquette —
chaque brique est validée sur flux réel (appel effectif, capture réseau, requête API) et le résultat
consigné. Cette exigence irrigue tout le document&nbsp;: les vérifications du chapitre 16 ne sont pas un
appendice, elles sont la définition même du « terminé ».</p>
""")
A(nxt("La problématique étant posée, le chapitre 3 la replace dans son contexte d'usage : quelle "
      "organisation, quels utilisateurs, et quelle stratégie pour tenir les quatre tensions à la fois."))

# ── 3. Contexte d'entreprise ─────────────────────────────────────────────
A(chap("03", "ch3", "Contexte d'entreprise et approche retenue",
       "Une petite structure, un site principal, des collaborateurs mobiles — et le refus du SaaS par défaut."))
A("<h3>Le cadre d'usage</h3>")
A("""
<p>La plateforme est dimensionnée pour le profil d'organisation que dessinent les documents du dépôt&nbsp;:
une <b>petite structure</b> (dix postes, pool d'extensions 1001–1010) avec un <b>site principal</b> équipé
d'un LAN de gestion et d'un VLAN voix, et des <b>collaborateurs mobiles</b> — télétravail, déplacement,
connexions 4G ou Starlink derrière du CGNAT. Trois populations cohabitent&nbsp;:</p>
""")
A(tbl(["Population", "Terminal", "Besoin dominant"],
      [["Postes fixes du site", "Téléphones IP / softphones classiques (Zoiper) sur le VLAN voix ou le LAN", "Fiabilité et qualité d'appel constantes"],
       ["Collaborateurs équipés Asaphone", "Mobile ou desktop Flutter, sur le LAN ou à distance", "Zéro configuration : s'inscrire, scanner, appeler"],
       ["L'administrateur (unique)", "UI FreePBX + SSH", "Tout doit se réparer par script et survivre au reboot"]],
      widths=[28, 40, 32]))
A("<h3>Pourquoi pas une offre cloud ?</h3>")
A("""
<p>Une solution SaaS aurait répondu en apparence plus vite. Elle a été écartée pour trois raisons
convergentes&nbsp;: la <b>souveraineté des données</b> (les CDR, messages vocaux et annuaires restent sur
une machine maîtrisée — MariaDB locale, spool local), le <b>coût récurrent par poste</b> qui pénalise les
petites équipes, et surtout la <b>maîtrise du chemin critique</b>&nbsp;: ici, la téléphonie interne
fonctionne intégralement <i>sans Internet</i> — le cœur PBX, le LAN et le VLAN voix sont autonomes, seuls
les accès distants exigent le réseau extérieur. C'est une propriété qu'aucune offre hébergée ne peut fournir.</p>
""")
A("<h3>L'approche : quatre phases, des scripts, pas de gestes manuels</h3>")
A("""
<p>Pour rendre le projet <i>faisable par une seule personne</i>, l'approche refuse le « clic unique dans
une UI » comme méthode de déploiement. Chaque évolution du serveur est portée par un <b>script idempotent
versionné</b> — rejouable sans dégât — et le cheminement suit quatre phases incrémentales, chacune
adossée à un document d'exploitation&nbsp;:</p>
""")
A(tbl(["Phase", "Livrable", "Ce qu'elle rend possible ensuite"], [
    ["<b>1 — Réseau</b>", "VLAN 10 voix (10.10.10.0/24), QoS DSCP EF sur le RTP, localnets, UFW",
     "Un socle où la voix est isolée et prioritaire — condition de tout le reste"],
    ["<b>2 — Utilisateurs</b>", "Extensions PJSIP 1001–1010, TLS 5061, messagerie vocale, groupe 8000",
     "Des identités et des postes — la matière première des services"],
    ["<b>3 — Services</b>", "IVR AGI Python, files ACD, ConfBridge, monitoring Docker",
     "L'expérience « standard d'accueil » et l'observabilité"],
    ["<b>4 — Sécurité</b>", "TLS généralisé, SRTP, Fail2Ban, durcissement UFW, politique de secrets",
     "L'ouverture maîtrisée vers l'extérieur (VPN, provision, mobiles)"]],
    widths=[16, 44, 40], cls="tbl teal"))
A("""
<p>Au-delà des phases, trois principes transversaux structurent l'ensemble — on les retrouvera dans
chaque chapitre&nbsp;:</p>
<ul>
<li><b>Une seule source de vérité par domaine</b> — la configuration réseau du site vit dans
<code>network/site.env</code> et <code>global-config.env</code> ; la configuration téléphonique vit en
base FreePBX (jamais dans les fichiers générés) ; les secrets vivent hors dépôt
(<code>/root/*.txt</code>, <code>/etc/provision/*.env</code>, <code>monitoring/.env</code>).</li>
<li><b>Le boot est le contrat</b> — tout ce qui est nécessaire au service est réappliqué à chaque
démarrage par <code>serveur-startup.service</code> : permissions, certificats, pare-feu, tunnels,
publication du bootstrap. Un serveur qui redémarre est un serveur réparé.</li>
<li><b>Le client ne sait rien, le serveur publie tout</b> — Asaphone découvre l'intégralité de sa
configuration (API, WSS, VPN, codecs, salles de conférence) via un <code>bootstrap.json</code> publié ;
aucune valeur n'est codée en dur côté client.</li>
</ul>
""")
A(keypoints([
    "Cible : petite structure mono-site avec mobilité — 10 postes, 1 administrateur.",
    "Choix de l'auto-hébergement : souveraineté des données, coût, et téléphonie interne autonome sans Internet.",
    "Méthode : 4 phases incrémentales, scripts idempotents versionnés, secrets hors dépôt.",
    "Trois principes : source de vérité unique, boot auto-réparant, client entièrement provisionné.",
]))
A(nxt("Le cadre est posé. La partie II ouvre le capot : d'abord la vue d'ensemble de l'architecture "
      "(chapitre 4), puis le réseau qui la porte (chapitre 5), enfin la sécurité qui l'enveloppe (chapitre 6)."))

# ═══════════════════════ PARTIE II — CONCEPTION ══════════════════════════
A(part("p2", "II", "Conception",
       "L'architecture avant le service : un cœur B2BUA, un réseau à trois pattes, "
       "et huit couches de sécurité emboîtées.",
       [("04", "Architecture générale"),
        ("05", "Réseau : adressage, VLAN voix et QoS"),
        ("06", "Sécurité en profondeur (L0 → L7)")]))

# ── 4. Architecture ──────────────────────────────────────────────────────
A('<div class="pb"></div>')
A(chap("04", "ch4", "Architecture générale",
       "De l'Internet au combiné : chaque flux traverse une frontière de sécurité avant d'atteindre le cœur."))
A("""
<p>La lecture de l'architecture se fait du haut vers le bas&nbsp;: <b>en haut</b>, l'Internet — fournisseur
SIP (phase trunk, préparée), tunnel Cloudflare pour l'API de provision distante, GitHub Pages pour la
découverte, clients 4G. <b>Au milieu</b>, la frontière : UFW en <i>default deny</i>, Fail2Ban, et le point
d'entrée WireGuard. <b>Au cœur</b>, la zone serveur : Asterisk et ses satellites (FreePBX, mini-API PHP,
MariaDB, monitoring). <b>En bas</b>, les deux mondes desservis : le LAN de gestion et le VLAN voix.</p>
""")
A(sch("fig-architecture-globale.png",
      "architecture globale — Internet → pare-feu → Asterisk/FreePBX → LAN gestion + VLAN voix"))
A("<h3>Le choix structurant : un B2BUA au centre</h3>")
A("""
<p>Asterisk n'est pas un simple relais SIP&nbsp;: c'est un <b>B2BUA</b> (<i>back-to-back user agent</i>).
Chaque appel est <i>terminé</i> sur le PBX puis <i>ré-émis</i> vers l'autre poste — deux jambes
indépendantes, négociées séparément. Cette décision, qui peut sembler un détail d'implémentation,
conditionne en réalité tout le projet&nbsp;:</p>
<ul>
<li><b>Elle rend l'hétérogénéité possible</b> — un Zoiper en UDP/G.711 peut appeler un Asaphone en
WSS/Opus : le PBX transcode et adapte l'enveloppe (chapitre 9).</li>
<li><b>Elle rend les services possibles</b> — ConfBridge mixe, MixMonitor enregistre, l'IVR interagit :
autant d'opérations qui exigent l'accès au média en clair sur le PBX.</li>
<li><b>Elle fixe la limite du chiffrement</b> — chaque jambe est chiffrée (SRTP ou DTLS-SRTP), mais le
PBX est un point de confiance : l'E2EE strict poste-à-poste est hors modèle (chapitre 6).</li>
</ul>
""")
A("<h3>Trois pattes réseau, trois mondes</h3>")
A(sch("fig-dual-homing.png",
      "dual-homing du PBX — patte gestion (MGMT), patte voix (VLAN 10) et tunnel WireGuard, "
      "avec les clients de chaque monde", w=94))
A(tbl(["Interface", "Réseau", "Qui s'y connecte", "Ce qui y circule"],
      [["<code>ens33</code>", "LAN gestion (ex. 192.168.1.0/24)", "Admin (UI FreePBX), softphones bureau, API provision LAN", "HTTPS 443, SIP 5060/5061, WSS 8089"],
       ["<code>ens33.10</code>", "VLAN 10 voix — 10.10.10.0/24", "Téléphones IP du site (DHCP .50–.200)", "SIP + RTP prioritaire (DSCP EF)"],
       ["<code>wg0</code>", "VPN — 10.200.0.0/24", "Clients distants enrôlés (10.200.0.x)", "Tout le trafic PBX, chiffré WireGuard"]],
      widths=[14, 26, 32, 28]))
A(callout("info", "Pourquoi les localnets comptent",
          "PJSIP décide de réécrire (ou non) les adresses SIP selon que la source est « locale ». Les trois "
          "réseaux ci-dessus sont déclarés dans les <b>localnets</b> FreePBX (base <code>kvstore_Sipsettings</code>) "
          "et régénérés à chaque <code>fwconsole reload</code> — un poste VPN est ainsi traité comme un poste "
          "du LAN, sans bricolage NAT."))
A(keypoints([
    "Lecture verticale : Internet → frontière (UFW/Fail2Ban/WG) → cœur (Asterisk + satellites) → LAN/VLAN.",
    "Le B2BUA est le choix fondateur : hétérogénéité des clients, services média, chiffrement par segment.",
    "Trois pattes réseau étanches ; les localnets PJSIP unifient leur traitement SIP.",
]))
A(nxt("L'architecture suppose un réseau qui isole et priorise la voix. Le chapitre 5 détaille ce socle : "
      "plan d'adressage, VLAN 10 et marquage QoS."))

# ── 5. Réseau ────────────────────────────────────────────────────────────
A(chap("05", "ch5", "Réseau : adressage, VLAN voix et QoS",
       "Isoler d'abord, prioriser ensuite : le VLAN sépare les mondes, le DSCP fait passer la voix devant."))
A("<h3>Deux mécanismes distincts — et complémentaires</h3>")
A("""
<p>Le cahier « VLAN 10 dédié voix, QoS DSCP EF pour le RTP » recouvre deux choses que le document de
phase 1 prend soin de distinguer, car elles ne se configurent pas au même endroit&nbsp;:
le <b>VLAN</b> est un segment de couche 2 (802.1Q) — il se crée sur le switch et l'hyperviseur,
Asterisk ne voit que des adresses IP ; le <b>marquage DSCP</b> est une étiquette de priorité posée sur
chaque paquet IP — il se fait sur le serveur (netfilter) et doit être <i>honoré</i> par les équipements
(<i>trust DSCP</i>).</p>
""")
A(tbl(["Élément du plan", "Valeur retenue", "Justification"],
      [["Réseau voix (VLAN 10)", "<b>10.10.10.0/24</b>", "Préfixe immédiatement lisible (« tout 10.10.10.x = voix »), aucun risque de collision avec les LAN 192.168.x des sites"],
       ["PBX — patte voix", "10.10.10.10/24 (statique, <code>ens33.10</code>)", "IP stable pour les téléphones, connexion NetworkManager <code>voix-vlan10</code>, jamais de route par défaut"],
       ["Passerelle voix", "10.10.10.1", "SVI/firewall — routage inter-VLAN contrôlé"],
       ["Téléphones", "DHCP 10.10.10.50 – 200", "Plage .2–.49 réservée à l'infrastructure (SBC, SNMP…)"],
       ["Plage RTP", "UDP 10000 – 20000", "Constatée dans <code>rtp_additional.conf</code> (FreePBX) — les règles QoS y sont alignées"]],
      widths=[26, 30, 44]))
A("""
<p>Le choix d'un second /24 <i>distinct</i> plutôt qu'un réseau plat n'est pas esthétique&nbsp;: un même
/24 posé sur deux VLANs casse ARP et routage ; un réseau plat unique renonce au filtrage inter-zones et
mélange les domaines de broadcast. Le /24 dédié donne des ACL lisibles — « autoriser SIP/RTP depuis la
zone voix » s'écrit en une règle UFW.</p>
""")
A("<h3>La QoS en pratique</h3>")
A("""
<p>Le marquage est inséré dans la table <code>mangle</code> d'UFW (<code>/etc/ufw/before.rules</code>,
sauvegarde préalable versionnée)&nbsp;: tout paquet UDP dont le port <i>source ou destination</i> tombe
dans 10000–20000 reçoit la classe <b>EF (46, 0x2e)</b> — la file « expedited forwarding » que les
équipements réseau servent en premier. La vérification fait partie de la procédure&nbsp;:</p>
""")
A('<pre class="term"><span class="c">$ sudo iptables -t mangle -L OUTPUT -n -v</span>\n'
  'DSCP set 0x2e  udp  multiport <b>sports 10000:20000</b>\n'
  'DSCP set 0x2e  udp  multiport <b>dports 10000:20000</b>\n'
  '<span class="d"># contrôle en appel réel : tcpdump -vv -n -i ens33.10 udp portrange 10000-20000 → champ tos/DSCP</span></pre>')
A(callout("warn", "Frontière de responsabilité",
          "Côté serveur, tout est en place (interface, localnets, UFW, marquage). Le raccordement physique "
          "— trunk 802.1Q sur le switch, port group VLAN 10 sur l'hyperviseur, files prioritaires "
          "<i>trust DSCP</i> — relève de l'infrastructure du site et est documenté comme restant à réaliser "
          "(Plan-adressage §8). La VM est prête : dès que le lien tagué arrive, <code>ens33.10</code> est opérationnelle."))
A(keypoints([
    "VLAN (L2, switch/hyperviseur) et DSCP (L3, serveur) sont deux mécanismes distincts, tous deux nécessaires.",
    "Plan : 10.10.10.0/24, PBX en .10, passerelle .1, téléphones .50–.200, RTP 10000–20000.",
    "Marquage EF posé dans ufw/before.rules, aligné sur la plage RTP FreePBX, vérifiable en une commande.",
]))
A(nxt("Un réseau isolé n'est pas encore un réseau sûr. Le chapitre 6 empile les huit couches de "
      "sécurité qui enveloppent ce socle — du tag VLAN au stockage des secrets."))

# ── 6. Sécurité ──────────────────────────────────────────────────────────
A(chap("06", "ch6", "Sécurité en profondeur (L0 → L7)",
       "Aucun mécanisme unique ne protège un PBX : huit couches se recouvrent, chacune rattrapant les failles de la précédente."))
A("""
<p>La sécurité du projet n'est pas un chapitre ajouté à la fin — c'est la <b>phase 4</b> du déploiement,
et elle est pensée en couches emboîtées. Chaque couche a son mécanisme, son script d'application et son
contrôle. Le schéma suivant en donne l'état documenté&nbsp;:</p>
""")
A(sch("fig-securite-couches.png",
      "matrice des couches de sécurité L0 → L7 et leur état", w=96))
A("<h3>Signalisation et média : chiffrer chaque jambe</h3>")
A(tbl(["Segment", "Mécanisme", "Mise en œuvre", "Contrôle"],
      [["SIP classique", "TLS 1.2+ sur <b>5061</b>", "Certificat Certman assigné à PJSIP (<code>pjsipcertid</code>) par <code>phase4-assign-pjsip-tls-cert.php</code>", "<code>pjsip show transport 0.0.0.0-tls</code> → cert_file renseigné"],
       ["Média classique", "<b>SRTP SDES</b>", "<code>media_encryption=sdes</code> sur 1001–1010 (<code>phase4-enable-srtp-extensions.php</code>)", "<code>grep media_encryption /etc/asterisk/pjsip.endpoint.conf</code>"],
       ["SIP WebRTC", "<b>WSS</b> (TLS 8089)", "Transport <code>transport-wss</code> + certificats Certman (<code>fix-wss-tls.sh</code>)", "<code>http show status</code> → HTTPS 8089"],
       ["Média WebRTC", "<b>DTLS-SRTP</b> + ICE", "Profil endpoint WebRTC (<code>align-pjsip-site.sh</code>) ; module <code>res_srtp</code> requis", "Appel réel 1001 ↔ 1003 (ch. 16)"]],
      widths=[16, 18, 40, 26]))
A("<h3>Frontière : refuser par défaut, bannir les insistants</h3>")
A("""
<ul>
<li><b>UFW</b> — politique <code>default deny incoming</code> ; le SIP et le RTP ne sont ouverts que
depuis les CIDR déclarés (VLAN voix, LAN gestion, VPN). Durcissement notable de la phase 4&nbsp;:
<b>5061/tcp n'est plus exposé « Anywhere »</b> — il est restreint aux réseaux nommés ; les futurs trunks
opérateur passeront par des règles ciblées par IP du fournisseur.</li>
<li><b>Fail2Ban</b> — jail <code>asterisk</code> sur <code>/var/log/asterisk/full</code> (backend auto,
ports 5060/5061/5160/5161) : bannissement /32 après échecs répétés. Le filtre se teste sur un extrait du
log avec <code>phase4-test-fail2ban-filter.sh</code> (le log complet rendrait <code>fail2ban-regex</code>
interminable).</li>
<li><b>Secrets</b> — mots de passe SIP aléatoires ≥ 16 caractères, rotation planifiée à 90 jours ;
identifiants MariaDB uniquement dans <code>/etc/freepbx.conf</code> ; aucun secret dans Git.</li>
</ul>
""")
A("<h3>Le point souvent oublié : les permissions</h3>")
A(callout("warn", "Leçon d'exploitation — les clés TLS et le groupe asterisk",
          "Un incident documenté (network/run.txt) : des clés en <code>0600 www-data:www-data</code> "
          "<b>cassent le WSS</b>, car le démon Asterisk ne lit qu'avec le groupe <code>asterisk</code>. "
          "Le modèle durable est <code>www-data:asterisk</code> en <code>0640</code>, réappliqué à chaque "
          "boot par <code>freepbx_chown.conf</code> + les scripts <code>fix-*</code> — jamais de "
          "<code>chmod 777</code>, jamais de <code>chown -R</code> global."))
A(callout("info", "La limite assumée : pas d'E2EE strict",
          "Chaque jambe est chiffrée, mais le PBX déchiffre pour ponter, transcoder, mixer (ConfBridge) et "
          "enregistrer (MixMonitor). Le modèle de menace retenu fait du serveur un <b>point de confiance</b> — "
          "c'est le prix des services média, et c'est documenté plutôt que masqué."))
A(keypoints([
    "Huit couches emboîtées, chacune scriptée et contrôlable — la phase 4 est un durcissement, pas un vernis.",
    "Chiffrement par segment : TLS/SRTP côté classique, WSS/DTLS côté WebRTC ; le PBX reste point de confiance.",
    "5061 fermé au monde ; Fail2Ban banni les scans ; secrets ≥ 16 caractères hors dépôt, rotation 90 j.",
    "Les permissions (clés 0640 www-data:asterisk) sont une couche de sécurité à part entière, réappliquée au boot.",
]))
A(nxt("La conception est complète : architecture, réseau, sécurité. La partie III construit dessus, "
      "en commençant par la matière première de toute téléphonie — les extensions (chapitre 7)."))

# ═══════════════════════ PARTIE III — RÉALISATION ════════════════════════
A(part("p3", "III", "Réalisation",
       "Des identités aux services : postes PJSIP, standard d'accueil, WebRTC, client Flutter, "
       "messagerie et provisionnement automatisé.",
       [("07", "Extensions et administration FreePBX"),
        ("08", "Services d'appel : IVR, files, conférences et groupes"),
        ("09", "WebRTC : WSS, DTLS-SRTP et pont média"),
        ("10", "Le client Asaphone"),
        ("11", "Messagerie vocale et chat"),
        ("12", "Provisionnement de bout en bout")]))

# ── 7. Extensions ────────────────────────────────────────────────────────
A('<div class="pb"></div>')
A(chap("07", "ch7", "Extensions et administration FreePBX",
       "Dix postes, deux profils média, zéro édition manuelle de fichier : tout passe par la base."))
A("<h3>La règle d'or FreePBX</h3>")
A("""
<p>Sous FreePBX, les fichiers Asterisk « classiques » (<code>pjsip.conf</code>,
<code>extensions.conf</code>…) sont <b>générés</b>&nbsp;: les modifier à la main, c'est écrire dans du
sable — le prochain <code>fwconsole reload</code> les écrase. Le flux légitime est&nbsp;:</p>
""")
A('<pre class="term">UI FreePBX <span class="d">(ou scripts PHP du dépôt)</span>  ──▶  base MariaDB '
  '<span class="d">(asterisk)</span>  ──▶  <span class="c">fwconsole reload</span>  ──▶  '
  '/etc/asterisk/*.conf <span class="d">(générés)</span>\n'
  '<span class="d">Custom autorisé : extensions_custom.conf · pjsip_custom_post.conf · '
  'queues_custom.conf · manager_custom.conf</span></pre>')
A("""
<p>C'est pourquoi la phase 2 crée les postes par <b>script PHP FreePBX</b>
(<code>phase2-create-extensions.php</code>) plutôt qu'à la main&nbsp;: contexte
<code>from-internal</code>, <b>3 contacts max</b> par extension (plusieurs appareils simultanés),
secrets aléatoires écrits dans <code>/root/phase2-pjsip-secrets.txt</code> (chmod 600, hors Git),
boîte vocale activée pour chacun.</p>
""")
A(tbl(["Extensions", "Profil", "Transport", "Média", "Codecs"],
      [["<b>1001 – 1002</b>", "Classique (Zoiper, téléphone IP)", "UDP 5060 · TLS 5061", "RTP + SRTP SDES", "ulaw · alaw · gsm · g726 · g722"],
       ["<b>1003 – 1010</b>", "WebRTC (Asaphone) — pool de provision", "WSS 8089", "DTLS-SRTP · ICE · AVPF · rtcp-mux", "Opus + ulaw/alaw"],
       ["<b>8000</b>", "Sonnerie de groupe (dialplan custom)", "—", "Dial simultané 1001…1010, 45 s", "—"]],
      widths=[14, 30, 18, 22, 16]))
A("<h3>L'interface au quotidien</h3>")
A(cap("freePBX-interface.png", "tableau de bord FreePBX 17 — l'UI d'administration du PBX", w=92))
A(cap("extension-interface.png", "liste des extensions PJSIP dans FreePBX (Applications → Extensions)", w=92))
A("<h3>Créer un poste : le parcours complet</h3>")
A("""
<p>Le formulaire de création (ci-dessous) illustre le principe base-d'abord&nbsp;: les champs saisis
alimentent MariaDB, et c'est le <i>reload</i> qui matérialise le poste dans la configuration Asterisk.
Les groupes d'appel (<code>namedcallgroup</code>/<code>namedpickupgroup</code> « phase2 ») sont posés
sur les dix postes ; la sonnerie générale répond au <b>8000</b>.</p>
""")
A(cap("creating-new-extention.png", "création d'une nouvelle extension PJSIP", w=92))
A(cap("extension-created.png", "l'extension créée, prête à être rechargée", w=92))
A(keypoints([
    "Jamais d'édition des fichiers générés : UI/scripts → MariaDB → fwconsole reload.",
    "10 extensions scriptées, secrets ≥ 16 caractères hors dépôt, 3 appareils par poste.",
    "Deux profils média distincts alignés par align-pjsip-site.sh ; sonnerie de groupe 8000 en custom.",
]))
A(nxt("Des postes qui sonnent, c'est le minimum. Le chapitre 8 leur ajoute un standard : accueil "
      "horaire, IVR intelligent, files d'attente et salles de conférence."))

# ── 8. Services d'appel ──────────────────────────────────────────────────
A(chap("08", "ch8", "Services d'appel : IVR, files, conférences et groupes",
       "Un standard d'accueil complet — porté par le dialplan custom, indépendant des modules GUI."))
A("<h3>Le parcours d'un appel entrant</h3>")
A("""
<p>Le service d'accueil suit une chaîne à trois étages, chacun étant un numéro interne testable
isolément&nbsp;: le <b>7000</b> applique la fenêtre horaire (<code>GotoIfTime</code>, lun–ven
9h–18h) et route vers le <b>7010</b> — l'IVR proprement dit, un <b>AGI Python</b>
(<code>phase3_intelligent_ivr.py</code>) qui reconnaît les appelants VIP
(<code>phase3-vip.txt</code>), adapte son comportement à l'heure et permet la saisie directe
d'une extension ; en bout de chaîne, le <b>7020</b> place l'appelant dans la file
<code>phase3-support</code> (stratégie <i>leastrecent</i>, membres 1001–1010) dont les conversations
sont enregistrées par MixMonitor.</p>
""")
A(tbl(["Numéro", "Service", "Détail"],
      [["7000", "Porte d'entrée horaire", "Ouvré → 7010 ; fermé → message de fermeture"],
       ["7010", "IVR AGI Python", "VIP, logique horaire/langue, saisie d'extension"],
       ["7020", "File ACD support", "leastrecent, 1001–1010, MixMonitor → /var/spool/asterisk/monitor/"],
       ["7101–7110", "Files individuelles", "ivr-ext-1001 … ivr-ext-1010 (un poste chacune)"],
       ["8001", "ConfBridge à PIN", "Salle phase3-&lt;PIN&gt; (PIN de test à changer)"],
       ["8100", "Test d'enregistrement", "MixMonitor + renvoi messagerie 1001"]],
      widths=[14, 26, 60]))
A(cap("ivr-interface-for-all-extentions.png",
      "IVR et files d'attente couvrant toutes les extensions (phase 3)", w=92))
A(callout("info", "Résilience vis-à-vis des modules Sangoma",
          "Le téléchargement des gros modules GUI (queues, packs de sons) échouait en timeout sur le miroir "
          "Sangoma. Plutôt que d'attendre, la phase 3 s'appuie directement sur <code>app_queue</code> et "
          "ConfBridge via les fichiers <code>*_custom.conf</code>, appliqués par blocs balisés "
          "(<code>BEGIN_PHASE3…END_PHASE3</code>) et donc rejouables. Les modules GUI restent installables plus tard."))
A("<h3>Appels de groupe Asaphone : le client ne mixe jamais</h3>")
A("""
<p>Le principe est radical de simplicité côté téléphone&nbsp;: pour appeler un groupe, Asaphone compose
<b>un seul numéro</b> (<code>call_uri</code>). Tout le reste est serveur — le dialplan fait entrer
l'appelant dans une salle <b>ConfBridge</b>, puis le PBX <i>originate</i> vers chaque membre. Les groupes
créés dans l'application sont synchronisés (<code>groups/sync.php</code>) et reçoivent chacun une salle
dédiée <code>asaphone-grp-&lt;slug&gt;</code> ; la salle <b>6000</b> sert de défaut, les <b>6001–6099</b>
sont réservées.</p>
""")
A(sch("fig-seq-confbridge.png",
      "appel de groupe — synchronisation, ConfBridge et originate des membres", w=94))
A("""
<p>En cours d'appel, l'invitation d'un participant supplémentaire passe par
<code>POST conference/invite.php</code> (extensions listées, ou <code>auto:true</code> pour tout le
groupe)&nbsp;: le client reste dans la salle, le PBX fait sonner les invités. L'authentification de ces
API suit le modèle commun du projet — paramètre <code>?ext=</code> + en-tête
<code>X-Provision-Jti</code>.</p>
""")
A(keypoints([
    "Chaîne d'accueil 7000 → 7010 (AGI Python, VIP) → 7020 (ACD enregistrée) — testable étage par étage.",
    "Dialplan custom balisé et rejouable, indépendant des modules GUI Sangoma.",
    "Groupes : un seul INVITE client ; ConfBridge mixe, le PBX originate les membres, invitation à chaud par API.",
]))
A(nxt("Tous ces services supposent que des clients très différents — téléphone SIP et application "
      "WebRTC — puissent converser. Le chapitre 9 explique comment le PBX réconcilie ces deux mondes."))

# ── 9. WebRTC ────────────────────────────────────────────────────────────
A(chap("09", "ch9", "WebRTC : WSS, DTLS-SRTP et pont média",
       "Faire parler un navigateur avec un téléphone SIP : deux dialectes, un traducteur central."))
A("<h3>Le problème à résoudre</h3>")
A("""
<p>Un client WebRTC et un softphone SIP classique ne parlent pas la même langue média. Le premier exige
<b>DTLS-SRTP</b>, <b>ICE</b>, le profil <b>SAVPF</b> et privilégie <b>Opus</b> ; le second envoie du
RTP/AVP en G.711 sans enveloppe particulière. Les faire dialoguer « en direct » est impossible — et c'est
exactement ce que le modèle B2BUA du chapitre 4 résout&nbsp;: Asterisk termine la jambe WebRTC d'un côté,
ouvre une jambe RTP classique de l'autre, et traduit au milieu.</p>
""")
A(sch("fig-seq-appel-1001-1003.png",
      "appel 1001 (UDP/SRTP) ↔ 1003 (WSS/DTLS-SRTP) — deux jambes négociées séparément, pont sur le PBX", w=96))
A("<h3>Côté serveur : ce qui rend le WSS possible</h3>")
A(tbl(["Brique", "Réglage", "Piège documenté"],
      [["Mini-serveur HTTP Asterisk", "TLS <b>8089</b> (WSS), 8088 en lab ; URL <code>wss://pbx.local:8089/ws</code>", "FreePBX régénère <code>http_additional.conf</code> avec bind 127.0.0.1 → le script force <code>HTTPTLSBINDADDRESS</code> via fwconsole setting"],
       ["Transport PJSIP", "<code>transport-wss</code> lié à 0.0.0.0:8089", "Vérifier par <code>pjsip show transports</code>"],
       ["Module SRTP", "<code>res_srtp.so</code> chargé", "Absent d'une compilation sans libsrtp2 → 488 systématique ; script <code>install-asterisk-res-srtp.sh</code>"],
       ["Endpoint WebRTC", "<code>media_encryption=dtls</code>, ICE, AVPF, rtcp_mux, Opus+G.711", "Sans ce profil, la signalisation WSS passe mais le média échoue (488 / « couldn't negotiate stream »)"],
       ["Certificats", "Certman <code>default.crt/key</code>, clés lisibles par le groupe asterisk", "Perms 0600 → WSS ne bind pas (cf. ch. 6)"]],
      widths=[22, 38, 40]))
A("<h3>Côté client : la configuration se réduit à trois champs</h3>")
A("""
<p>Grâce au provisionnement (chapitre 12), l'utilisateur ne voit jamais ces réglages — mais ils existent,
et l'écran de configuration SIP d'Asaphone les expose pour le diagnostic&nbsp;: serveur
(<code>pbx.local</code>), extension, transport WSS.</p>
""")
A(cap("sip-config.png", "configuration SIP du client Asaphone — serveur, extension, transport WSS", w=40))
A(callout("warn", "Deux comportements client à connaître",
          "<b>1.</b> Un REGISTER avec <code>Contact: *</code> et <code>Expires: 0</code> désenregistre "
          "<i>tous</i> les contacts du poste : à réserver au logout explicite, sous peine de voir le poste "
          "« Unreachable » et les appels filer en messagerie. <b>2.</b> L'avertissement « DTLS packet dropped, "
          "ICE not completed yet » observé en lab est un comportement ICE côté client — l'appel s'établit, "
          "mais c'est le premier endroit où chercher si l'audio devient instable."))
A(keypoints([
    "wss://pbx.local:8089/ws : le chemin /ws est celui d'Asterisk, le certificat doit couvrir le nom utilisé.",
    "Un endpoint WebRTC sans dtls/ice/avpf/rtcp-mux échoue en 488 même si le WSS fonctionne.",
    "Aligner Opus + G.711 des deux côtés évite le transcodage CPU sur le pont.",
]))
A(nxt("Le transport est prêt ; reste à voir ce que l'utilisateur tient en main. Le chapitre 10 parcourt "
      "le client Asaphone écran par écran."))

# ── 10. Client ───────────────────────────────────────────────────────────
A(chap("10", "ch10", "Le client Asaphone",
       "Un seul code Flutter pour Android, Windows et iOS — et un client qui ne connaît rien d'avance."))
A("""
<p>Asaphone est développé en <b>Flutter</b> (projet OBSCURA), ce qui donne un client unique pour les
trois plateformes cibles. Son principe directeur rejoint celui du chapitre 3&nbsp;: <i>le client ne sait
rien, le serveur publie tout</i>. Au démarrage, l'application récupère le <code>bootstrap.json</code>
(découverte), puis sa session provisionnée lui fournit — outre les credentials SIP — les endpoints d'API,
les salles de conférence, les groupes, les codecs vidéo (VP8/H.264) et les serveurs ICE. Le diagramme
suivant situe tout ce qu'un utilisateur peut faire, et par quel canal&nbsp;:</p>
""")
A(sch("fig-usecase-asaphone.png",
      "cas d'utilisation Asaphone ↔ PBX — provision, appels, chat, messagerie, groupes, VPN", w=90))
A("<h3>Premier contact : accueil et configuration</h3>")
A("""
<p>L'écran d'accueil propose les deux parcours du flux d'onboarding (« J'ai déjà mes identifiants » /
« M'enregistrer ») ; la page de configuration récapitule le compte et l'état de l'enregistrement SIP.</p>
""")
A(duo("welcome-login.png", "écran d'accueil / connexion d'Asaphone",
      "config-page.png", "page de configuration du client"))
A("<h3>Le geste quotidien : composer, parler, se voir</h3>")
A(duo("clavier.png", "clavier d'appel (numérotation interne)",
      "appel-audio.png", "appel audio en cours (démonstration)"))
A("""
<p>La vidéo emprunte exactement le même chemin que l'audio — SDP négocié via WSS, média DTLS-SRTP —
avec les codecs annoncés par le bootstrap (<b>VP8</b>, <b>H.264</b>)&nbsp;:</p>
""")
A(cap("appel-video.png", "appel vidéo en cours (démonstration)", w=38))
A(keypoints([
    "Un code Flutter, trois plateformes ; zéro constante serveur en dur dans l'application.",
    "Bootstrap → session : credentials, endpoints, groupes, conférences, ICE et codecs arrivent du PBX.",
    "Audio et vidéo partagent la même pile WSS + DTLS-SRTP (VP8/H.264 pour la vidéo).",
]))
A(nxt("Au-delà de l'appel en direct, il faut gérer l'asynchrone : messages vocaux et texte. "
      "C'est l'objet du chapitre 11."))

# ── 11. Messagerie ───────────────────────────────────────────────────────
A(chap("11", "ch11", "Messagerie vocale et chat",
       "L'asynchrone sans serveur supplémentaire : app_voicemail pour la voix, SIP MESSAGE pour le texte."))
A("<h3>Messagerie vocale : dix boîtes, un incident instructif</h3>")
A("""
<p>Chaque poste 1001–1010 dispose d'une boîte vocale (contexte <code>default</code>) créée et mappée par
<code>phase2-enable-voicemail.php</code>&nbsp;: pièce jointe WAV (<code>attach=yes</code>), horodatage et
identification de l'appelant annoncés, PIN initial à personnaliser. L'incident documenté du dépôt mérite
d'être raconté&nbsp;: certains appels basculaient en « an error has occurred » — le log révélait
<code>No entry in voicemail config file for '1001'</code>. Diagnostic&nbsp;: l'extension existait côté
PJSIP mais <i>pas sa mailbox</i> côté Voicemail. La remise en cohérence par script (plutôt qu'un correctif
manuel par poste) a rétabli les dix boîtes d'un coup — et illustré la valeur de l'approche scriptée.</p>
""")
A(tbl(["Fonction", "Mise en œuvre"],
      [["Consultation directe", "Codes <b>*81001 … *81010</b> → boîte du poste correspondant (<code>apply-voicemail-codes.sh</code>)"],
       ["Dépôt de message", "Automatique après le bip (renvoi sur non-réponse / occupation / poste injoignable)"],
       ["Notification e-mail", "WAV en pièce jointe ; SMTP + adresse à renseigner par poste dans l'UI (reste à faire, S2 §7)"],
       ["Notification Asaphone", "<code>asaphone-vm-notify.sh</code> — notification poussée au client via le flux provision"],
       ["Contrôle", "<code>asterisk -rx \"voicemail show users\"</code> → default 1001 … 1010"]],
      widths=[26, 74]))
A("<h3>Chat : le texte voyage dans la signalisation</h3>")
A("""
<p>Plutôt que d'ajouter un serveur XMPP ou un service de messagerie tiers, le chat d'Asaphone réutilise
le canal déjà authentifié et chiffré&nbsp;: des requêtes <b>SIP MESSAGE</b> hors dialogue, routées par un
bloc dédié du dialplan (<code>apply-message-dialplan.sh</code>, marqueurs
<code>BEGIN_SIP_MESSAGE…END</code>). Les bénéfices sont immédiats&nbsp;: <b>une seule identité</b> (les
credentials SIP servent à tout), <b>un seul chemin réseau</b> (le WSS déjà ouvert), et une intégration
naturelle avec les notifications de messagerie vocale qui empruntent le même flux. Côté serveur,
<code>asaphone-chat-ingest.sh</code> archive les messages en base
(<code>provision-schema-chat.sql</code>), ce qui permet au client de resynchroniser son historique via
l'API provision après réinstallation.</p>
""")
A(keypoints([
    "Dix boîtes vocales scriptées ; codes *8100X ; l'incident « mailbox manquante » a validé l'approche scriptée.",
    "Chat = SIP MESSAGE dans le canal SIP existant — pas de serveur de messagerie supplémentaire.",
    "Historique ingéré en base → resynchronisation du client via l'API provision.",
]))
A(nxt("Voix, vidéo, texte, groupes : tous ces services supposent un compte. Le chapitre 12 montre "
      "comment ce compte naît — en deux minutes, sans administrateur."))

# ── 12. Provision ────────────────────────────────────────────────────────
A(chap("12", "ch12", "Provisionnement de bout en bout",
       "De l'e-mail au REGISTER : la scène d'ouverture du rapport, décomposée image par image."))
A("<h3>Trois étages de découverte</h3>")
A("""
<p>Le défi initial est trivial en apparence&nbsp;: <i>comment une application fraîchement installée
sait-elle où est son serveur ?</i> La réponse tient en trois étages, du plus stable au plus volatil&nbsp;:</p>
""")
A(tbl(["Étage", "Support", "Contenu", "Disponibilité"],
      [["<b>Découverte</b>", "GitHub Pages — <code>bootstrap.json</code> statique", "api_lan, api_remote, wss_url, VPN, codecs, endpoints", "Toujours joignable (CDN GitHub)"],
       ["<b>API LAN</b>", "<code>https://pbx.local/provision</code> (Apache + PHP)", "register/verify/claim/session, VPN, groupes, chat", "Sur le LAN et via VPN"],
       ["<b>API distante</b>", "Tunnel Cloudflare sortant (URL trycloudflare)", "La même API PHP — le tunnel évite tout port entrant", "Republiée au boot dans le bootstrap"]],
      widths=[16, 32, 34, 18]))
A(callout("info", "Le détail qui rend le système robuste",
          "L'URL trycloudflare change à chaque démarrage (mode quick). Le boot enchaîne donc, dans cet ordre "
          "précis : rafraîchir le tunnel → <code>sync-global-config.sh --deploy</code> (régénérer le bootstrap "
          "avec la nouvelle URL) → publier sur GitHub Pages. Un client hors LAN retrouve ainsi toujours une "
          "<code>api_remote</code> valide, sans DNS ni domaine dédié."))
A("<h3>Le parcours utilisateur</h3>")
A("""
<p>Côté application, l'utilisateur qui choisit « M'enregistrer » saisit une adresse e-mail — c'est sa
seule action « administrative »&nbsp;:</p>
""")
A(cap("sign-up.png", "écran d'inscription Asaphone — parcours « M'enregistrer », saisie de l'e-mail", w=38))
A("""
<p>Le serveur déroule alors la séquence complète&nbsp;: code à 6 chiffres (TTL 15 minutes, haché en base),
vérification, attribution automatique d'une extension libre du pool <b>1003–1010</b>
(politique <code>auto</code>), génération d'un <b>QR one-shot</b> (token de claim, validité 24 h) envoyé
par e-mail — jamais de secret SIP en clair dans le corps du message. Le scan déclenche le
<code>claim</code> (credentials complets), le client s'enregistre en WSS, puis révoque son token
(<code>consume</code>, <code>used=1</code>)&nbsp;: un QR intercepté après coup ne vaut plus rien.</p>
""")
A(sch("fig-seq-provision.png",
      "séquence de provisionnement — bootstrap → register/verify → QR → claim → REGISTER WSS → consume", w=96))
A("<h3>Une réservation honnête du pool</h3>")
A("""
<p>Subtilité de conception qui évite l'épuisement du pool par des inscriptions abandonnées&nbsp;:
l'envoi du QR ne <i>réserve pas</i> l'extension. Seule l'authentification réussie
(REGISTER → consume → statut <code>provisioned</code>) marque le poste <code>taken=true</code>.
L'endpoint <code>extension.php</code> expose l'état du pool à tout moment — extension par extension,
avec l'e-mail en attente s'il y en a un.</p>
""")
A("<h3>Défenses du flux</h3>")
A(tbl(["Risque", "Contre-mesure"],
      [["Spam d'inscriptions", "Rate-limit par IP <i>et</i> par e-mail (fenêtre glissante 1 h, table dédiée)"],
       ["Énumération d'adresses", "Réponse générique « si l'e-mail existe, un message a été envoyé »"],
       ["Interception du code", "TTL 15 min, code haché (bcrypt), transport HTTPS"],
       ["Rejeu du QR", "Token one-shot : jti révoqué au premier claim/REGISTER, expiration 24 h"],
       ["Fuite de secret par e-mail", "Le QR chiffré est autoporteur — aucun mot de passe en clair dans le mail"],
       ["Accès à l'admin via l'API", "Alias Apache /provision isolé de l'UI FreePBX, sans session admin"]],
      cls="tbl purple", widths=[30, 70]))
A(keypoints([
    "Découverte en trois étages : bootstrap GitHub (stable) → API LAN → API tunnel (republiée au boot).",
    "Onboarding complet en 4 gestes utilisateur : e-mail, code, scan, appel — moins de deux minutes.",
    "QR one-shot révoqué à l'usage ; le pool ne se réserve qu'à l'authentification réelle.",
    "Zéro backend cloud : Apache + PHP + MariaDB + SMTP, le tout sur le PBX.",
]))
A(nxt("Le compte existe, le poste est enregistré — sur le LAN. La partie IV s'attaque au reste du "
      "monde : accès distant, supervision et exploitation quotidienne."))

# ═══════════════════════ PARTIE IV — EXPLOITATION ════════════════════════
A(part("p4", "IV", "Exploitation",
       "Joindre le PBX de partout, l'observer en continu, et le laisser se réparer tout seul "
       "à chaque démarrage.",
       [("13", "Accès distant : VPN WireGuard, tunnels et trunks"),
        ("14", "Supervision : Telegraf → InfluxDB → Grafana"),
        ("15", "Installation et démarrage automatisé"),
        ("16", "Validation et tests")]))

# ── 13. VPN ──────────────────────────────────────────────────────────────
A('<div class="pb"></div>')
A(chap("13", "ch13", "Accès distant : VPN WireGuard, tunnels et trunks",
       "Cinq mécanismes de liaison qui ne font pas la même chose — et le scénario qui les départage."))
A("<h3>Le scénario révélateur</h3>")
A("""
<p>Le document VPN du dépôt part d'un cas concret&nbsp;: M. Dupont, softphone opérationnel au bureau,
part travailler depuis un réseau domestique (<code>192.168.137.0/24</code>). Résultat immédiat —
« Registration failed ». Rien n'est en panne&nbsp;: mDNS ne traverse pas Internet, l'IP privée du PBX
est injoignable, et quand bien même une route existerait, UFW et les localnets refuseraient cette source
inconnue. La leçon&nbsp;: <b>aucun réglage téléphonique ne résout un problème de couche 3</b>. Il faut un
pont réseau — et c'est précisément ce que chaque mécanisme du tableau suivant fait… ou ne fait pas&nbsp;:</p>
""")
A(sch("fig-comparatif-liaisons.png",
      "comparatif — extension PJSIP, trunk SIP, VPN WireGuard, VLAN 802.1Q, tunnel Cloudflare", w=96))
A("<h3>La réponse : WireGuard enrôlé par l'API</h3>")
A("""
<p>Le VPN retenu est <b>WireGuard</b> (interface <code>wg0</code>, PBX en 10.200.0.1, UDP 51820) — et son
enrôlement est aussi automatisé que le reste&nbsp;: <code>POST vpn/enroll.php</code> avec un
<code>device_id</code> stable retourne une URL de claim ; <code>GET vpn/claim.php</code> délivre la
configuration WireGuard complète (avec les indications SIP/WSS). Pas de compte, pas d'e-mail pour ce
flux — la révocation d'un appareil se fait par <code>vpn/revoke.php</code>. Côté serveur, seule règle à
retenir&nbsp;: autoriser le <b>sous-réseau du tunnel</b> (10.200.0.0/24) dans
<code>EXTRA_LAN_CIDRS</code> — jamais le LAN distant de l'utilisateur, que le PBX ne verra jamais.</p>
""")
A(callout("info", "Le cas CGNAT (Starlink) — pas d'UDP entrant du tout",
          "Derrière un CGNAT, même le port 51820 est inaccessible. La parade du projet : un <b>relais "
          "WireGuard-sur-WebSocket</b> (<code>install-wg-wss-relay.sh</code>) exposé par tunnel Cloudflare "
          "<i>sortant</i>. L'application ouvre le relais WSS, puis établit WireGuard vers "
          "<code>127.0.0.1:51820</code> à travers lui. Le bootstrap publie <code>tunnel.wss_url</code> — "
          "le client bascule seul, sans app externe."))
A("<h3>Windows et pbx.local</h3>")
A("""
<p>Dernier maillon de l'accès distant, plus prosaïque&nbsp;: Windows ne résout pas toujours les noms
mDNS <code>.local</code>. Le profil réseau régénère donc à chaque application le fichier
<code>network/windows-hosts.txt</code>, dont la ligne se copie (en administrateur) dans le fichier
<code>hosts</code> du poste&nbsp;:</p>
""")
A('<pre class="term"><span class="d"># C:\\Windows\\System32\\drivers\\etc\\hosts</span>\n'
  '192.168.1.80  pbx.local  pbx   <span class="d"># exemple généré — réseau 192.168.1.0/24</span></pre>')
A(cap("editing-host-file-for-windows.png",
      "édition du fichier hosts Windows pour résoudre pbx.local (poste sans mDNS)", w=90))
A("<h3>Et les trunks ?</h3>")
A("""
<p>Il faut le dire clairement, car la confusion est fréquente&nbsp;: <b>rien de tout cela n'est un
trunk</b>. Toute la téléphonie interne — appels mixtes UDP↔WSS, conférences, télétravail — fonctionne
sans trunk, par extensions PJSIP et B2BUA. Le trunk SIP ne devient nécessaire que pour le PSTN (numéro
public, appels sortants) ou pour relier un second PBX. Le dépôt les a préparés&nbsp;:
<code>trunk-operateur-pstn</code> et <code>trunk-interpbx-site-b</code> avec leurs routes (France,
international, inter-PBX, entrante catch-all → IVR 7000), activables dès que les identifiants opérateur
seront renseignés — hors Git, dans <code>/root/trunks-secrets.env</code>.</p>
""")
A(keypoints([
    "Un softphone hors site est un problème de couche 3 : la réponse est le VPN, pas un réglage SIP.",
    "Enrôlement WireGuard sans compte (device_id → claim .conf) ; révocation par API.",
    "CGNAT : relais WG-sur-WSS via tunnel Cloudflare sortant — aucune ouverture de port.",
    "Trunks PSTN/inter-PBX préparés mais distincts : la téléphonie interne n'en a pas besoin.",
]))
A(nxt("L'accès est réglé ; encore faut-il voir ce qui se passe. Le chapitre 14 branche les instruments "
      "de mesure sur le cœur du PBX."))

# ── 14. Monitoring ───────────────────────────────────────────────────────
A(chap("14", "ch14", "Supervision : Telegraf → InfluxDB → Grafana",
       "Observer sans peser : trois conteneurs, un utilisateur AMI dédié, des dashboards versionnés."))
A("<h3>Une chaîne courte et assumée</h3>")
A("""
<p>La stack tient en trois conteneurs Docker Compose (<code>monitoring/</code>) et un choix
assumé&nbsp;: <b>pas de Prometheus</b>. Les métriques suivent la chaîne
Telegraf → InfluxDB 2 → Grafana (langage Flux) — plus simple à opérer pour une personne seule.
Particularité technique&nbsp;: les images Telegraf officielles n'ont pas de plugin Asterisk ; le dépôt
construit donc <code>voip-telegraf:1.33-ami</code>, qui embarque deux scripts Python appelés toutes les
10 secondes — <code>ami_metrics.py</code> (interroge l'AMI&nbsp;: canaux, appels actifs → mesure
<code>asterisk_core</code>) et <code>log_metrics.py</code> (lit les logs Asterisk et Fail2Ban montés en
lecture seule). Le conteneur tourne en <code>network_mode: host</code> pour joindre l'AMI sur
127.0.0.1:5038 — avec un utilisateur AMI dédié <code>telegraf</code>, limité mais doté de
<code>write=command</code> (nécessaire à <code>core show channels</code>).</p>
""")
A(sch("fig-monitoring-pipeline.png",
      "pipeline de supervision — Telegraf (AMI + logs) → InfluxDB 2 → Grafana", w=94))
A("<h3>En console</h3>")
A(sch("console-monitoring-cli.png",
      "état de la stack et logs Telegraf — docker compose ps / logs", w=96))
A("<h3>Dans le navigateur</h3>")
A("""
<p>Grafana est <i>provisionné par fichiers</i> — datasource InfluxDB-VoIP et dashboard
« VoIP / Asterisk — monitoring » sont versionnés dans le dépôt (<code>grafana/provisioning/</code>,
<code>grafana/dashboards/voip-asterisk.json</code>) et chargés au démarrage du conteneur&nbsp;: un
<code>docker compose up -d</code> sur une machine vierge reconstruit l'observabilité à l'identique.</p>
""")
A(cap("grafana-welcome-page.png", "page d'accueil Grafana (port 3000) après démarrage de la stack", w=90))
A(cap("monitoring.png", "dashboard « VoIP / Asterisk — monitoring » — canaux et appels actifs", w=90))
A(keypoints([
    "Trois conteneurs, zéro Prometheus : Telegraf (scripts AMI Python) → InfluxDB 2 → Grafana Flux.",
    "Image Telegraf maison en network host ; utilisateur AMI dédié, secrets générés dans monitoring/.env.",
    "Dashboards et datasource versionnés : l'observabilité se reconstruit d'un docker compose up.",
    "Ports 3000/8086 restreints aux LAN autorisés par UFW.",
]))
A(nxt("Dernière pièce de l'exploitation, et non la moindre : comment tout cela s'installe, et surtout "
      "comment tout cela redémarre — seul. Chapitre 15."))

# ── 15. Installation / boot ──────────────────────────────────────────────
A(chap("15", "ch15", "Installation et démarrage automatisé",
       "D'un OS vierge à un PBX complet — puis un boot en 17 étapes qui se répare lui-même."))
A("<h3>Installer : quatre jalons</h3>")
A("""
<p>Le déploiement sur machine vierge (Debian 12 / Ubuntu 22.04) suit INSTALLATION.md en quatre jalons,
chacun doté d'un critère de réussite vérifiable — les planches ci-dessous les condensent, versions
strictement issues du dépôt&nbsp;:</p>
""")
A(sch("console-install-1-prerequis.png", "installation 1/4 — prérequis OS et paquets système", w=92))
A(sch("console-install-2-asterisk-freepbx.png", "installation 2/4 — Asterisk 20 LTS et FreePBX 17 (contrôles asterisk -V, fwconsole -V, res_srtp)", w=92))
A(sch("console-install-3-docker-monitoring.png", "installation 3/4 — Docker Compose v2 et stack monitoring", w=92))
A(sch("console-install-4-systemd.png", "installation 4/4 — service systemd serveur-startup (ExecStart à adapter au chemin réel)", w=92))
A("<h3>Le boot : un contrat en 17 étapes</h3>")
A("""
<p>Le principe du chapitre 3 — « le boot est le contrat » — se matérialise dans
<code>server-startup.sh</code>. Sa propriété clé est la <b>résilience hors ligne</b>&nbsp;: les étapes
sont classées <i>critiques</i> (Apache, profil réseau — un échec marque WARN) ou <i>optionnelles</i>
(tout ce qui touche Internet — un échec marque SKIP et le boot continue). Un serveur qui démarre dans une
cave sans réseau offre quand même la téléphonie interne complète. Les trois planches suivantes
reproduisent fidèlement le déroulé et le style console du script (banner, progression, ✓/⚠/○)&nbsp;:</p>
""")
A(sch("console-startup-1-banner.png",
      "serveur-startup 1/3 — banner ASAPHONE, rappels hors-ligne, premières étapes FreePBX", w=94))
A(sch("console-startup-2-coeur.png",
      "serveur-startup 2/3 — fwconsole, WSS 8089, permissions, Apache, profil réseau, relais WG", w=94))
A(sch("console-startup-3-resume.png",
      "serveur-startup 3/3 — Internet optionnel (tunnel, sync bootstrap), HTTPS 443 et résumé final", w=94))
A("<h3>Pourquoi cet ordre-là</h3>")
A("""
<p>L'ordre des étapes n'est pas arbitraire — il encode les leçons d'exploitation du projet&nbsp;:
les <b>permissions avant fwconsole</b> (sinon le chown automatique de FreePBX casse les clés TLS),
le <b>WSS juste après le démarrage</b> (sinon le port 8089 reste fermé), le <b>réseau après le cœur</b>
(UFW et localnets supposent Apache et Asterisk debout), et surtout la <b>synchronisation du bootstrap
après le rafraîchissement des tunnels</b> — faute de quoi GitHub publierait une API distante périmée.</p>
""")
A(tbl(["Bloc", "Étapes", "Comportement en échec"],
      [["Cœur PBX (sans Internet)", "chown.conf → perms GUI → certs TLS → fwconsole start → WSS 8089 → perms run/spool", "SKIP par étape, le boot continue"],
       ["Système local", "Sessions PHP → <b>Apache restart</b> → <b>profil réseau site</b> → perms post-réseau", "Critique : WARN + indicateur hors-ligne"],
       ["Internet optionnel", "Relais WG/WSS → tunnel Cloudflare → <b>sync bootstrap --deploy</b> → publication GitHub → HTTPS 443", "SKIP silencieux (retenté au prochain boot ou à la main)"],
       ["Bilan", "Résumé (IP LAN, pbx.local, API distante, alertes) + <code>serveur-startup: OK &lt;date&gt;</code>", "—"]],
      widths=[22, 54, 24]))
A("<h3>Au quotidien : une seule règle</h3>")
A("""
<p>Après toute modification dans l'UI FreePBX, un geste — et un seul — matérialise le changement&nbsp;:
<b>Apply Config</b> (<code>fwconsole reload</code>), qui régénère les fichiers depuis la base&nbsp;:</p>
""")
A(cap("applying-changes.png", "application des changements FreePBX — Apply Config (fwconsole reload)", w=88))
A(keypoints([
    "Installation en 4 jalons vérifiables ; versions épinglées par le dépôt (Asterisk 20.18.2, FreePBX 17, Influx 2.7, Grafana 11.4, Telegraf 1.33).",
    "Boot en 17 étapes : critiques vs optionnelles — la téléphonie interne survit à l'absence d'Internet.",
    "L'ordre encode les leçons : permissions → fwconsole → WSS → réseau → tunnels → bootstrap → publication.",
    "Un seul geste quotidien : Apply Config après chaque modification d'UI.",
]))
A(nxt("Reste à prouver que tout cela fonctionne. Le chapitre 16 rassemble les validations — celles "
      "déjà consignées dans le dépôt et les commandes pour les rejouer."))

# ── 16. Tests ────────────────────────────────────────────────────────────
A(chap("16", "ch16", "Validation et tests",
       "La modalité « production d'abord » en actes : chaque brique a son contrôle, rejouable en une commande."))
A(tbl(["Domaine", "Validation consignée", "Comment la rejouer"],
      [["Appels mixtes", "1001 (UDP) → 1003 (WSS) : sonnerie, décrochage, bridge établi", "Appel réel + <code>pjsip set logger on</code>"],
       ["QoS", "Règles mangle EF présentes ; contrôle en appel réel prescrit", "<code>iptables -t mangle -L OUTPUT -n -v</code> · tcpdump portrange 10000-20000"],
       ["Extensions", "10 endpoints PJSIP + mapping voicemail en base", "<code>pjsip show endpoints</code> · SELECT sur <code>users</code>"],
       ["Messagerie", "default 1001…1010 listées ; dépôt après bip validé", "<code>voicemail show users</code> · appel test"],
       ["WSS/TLS", "HTTPS 8089 actif, transport wss 0.0.0.0:8089", "<code>http show status</code> · <code>pjsip show transports</code> · <code>ss -tlnp</code>"],
       ["Fail2Ban", "Filtre validé sur extrait de log réel", "<code>phase4-test-fail2ban-filter.sh 2000</code>"],
       ["Provision", "Scénario complet register → verify → claim → consume en curl", "Commandes du flux d'onboarding (§15 du document source)"],
       ["Monitoring", "Mesure asterisk_core visible dans Grafana", "Explore → Flux <code>from(bucket:\"asterisk\")</code>"],
       ["Boot", "Journal complet du démarrage + résumé OK", "<code>journalctl -u serveur-startup.service -b</code>"]],
      widths=[16, 44, 40]))
A("<h3>Le réflexe santé en sept commandes</h3>")
A('<pre class="term"><span class="c">$ sudo asterisk -rx "pjsip show contacts"</span>   <span class="d"># qui est enregistré ?</span>\n'
  '<span class="c">$ sudo asterisk -rx "http show status"</span>      <span class="d"># WSS 8089 actif ?</span>\n'
  '<span class="c">$ ss -tlnp | grep -E \'8089|443|3000\'</span>        <span class="d"># les ports écoutent ?</span>\n'
  '<span class="c">$ sudo ufw status numbered</span>                  <span class="d"># le pare-feu est conforme ?</span>\n'
  '<span class="c">$ sudo fail2ban-client status asterisk</span>      <span class="d"># qui est banni ?</span>\n'
  '<span class="c">$ curl -sk https://pbx.local/provision/</span>     <span class="d"># l\'API répond ?</span>\n'
  '<span class="c">$ tail -50 /var/log/serveur-startup.log</span>     <span class="d"># le dernier boot ?</span></pre>')
A(callout("warn", "Point de vigilance ouvert",
          "L'avertissement « DTLS packet dropped. ICE not completed yet » apparaît en début d'appel WebRTC. "
          "Diagnostic documenté : négociation ICE côté client, sans impact constaté sur l'établissement — mais "
          "c'est la première piste si l'audio devient instable (vérifier ICE/STUN et l'ouverture RTP)."))
A(keypoints([
    "Chaque domaine a une validation consignée et une commande de rejeu — le « terminé » est vérifiable.",
    "Le flux de provisionnement se teste intégralement en curl, sans client mobile.",
    "Un point ICE/DTLS côté client est tracé comme vigilance ouverte, sans impact fonctionnel constaté.",
]))
A(nxt("Le système fonctionne et se vérifie. La partie V prend du recul : ce qui manque encore, "
      "et ce que le projet démontre."))

# ═══════════════════════ PARTIE V — BILAN ════════════════════════════════
A(part("p5", "V", "Bilan",
       "Un regard honnête sur les limites, les chantiers ouverts — et ce que cette plateforme "
       "prouve déjà.",
       [("17", "Limites et perspectives"), ("18", "Conclusion")]))

# ── 17. Limites ──────────────────────────────────────────────────────────
A('<div class="pb"></div>')
A(chap("17", "ch17", "Limites et perspectives",
       "Aucune n'est cachée : chaque limite est tracée dans un document du dépôt, avec sa parade prévue."))
A("<h3>Ce qui manque encore — et pourquoi ce n'est pas bloquant</h3>")
A(tbl(["Limite", "Impact réel", "Parade prévue"],
      [["Trunk VLAN 10 physique non raccordé (switch/hyperviseur)", "Les téléphones du VLAN voix ne sont pas encore en production ; le LAN gestion porte les postes actuels", "Config OS déjà prête : trunk 802.1Q + port group, puis trust DSCP"],
       ["Trunks opérateur inactifs (secrets non renseignés)", "Pas d'appels PSTN ni de numéro public", "apply-trunks.sh + /root/trunks-secrets.env ; routes déjà écrites"],
       ["SMTP par poste non configuré", "Notification e-mail de la messagerie vocale inopérante (la notification Asaphone, elle, fonctionne)", "Adresse + SMTP par extension dans l'UI"],
       ["URL trycloudflare éphémères (mode quick)", "Dépendance à la republication du bootstrap à chaque boot", "Tunnel nommé + domaine propre (CLOUDFLARE_TUNNEL_MODE=named)"],
       ["Secrets SIP réversibles en base", "Limitation structurelle FreePBX", "Accès base restreint + rotation 90 j ; documenté plutôt que contourné"],
       ["Pas d'E2EE strict poste-à-poste", "Le PBX voit le média (nécessaire aux services)", "Modèle de menace assumé : chiffrement par segment"],
       ["Module GUI ringgroups absent", "Groupes gérés par dialplan custom (8000)", "Réinstallable quand le miroir Sangoma répond"],
       ["NFS enregistrements non monté", "Les enregistrements restent sur le disque local", "Export NFS vers /var/spool/asterisk/monitor côté infra"],
       ["MFA admin / chiffrement disque", "Non déployés", "Roadmap sécurité (module ou reverse proxy)"]],
      widths=[30, 36, 34]))
A("<h3>Les cinq chantiers suivants, dans l'ordre</h3>")
A("""
<ul>
<li><b>1. Raccorder le VLAN 10</b> — dernier maillon entre la conception réseau et sa réalité physique.</li>
<li><b>2. Activer un trunk opérateur</b> (TLS si l'offre le permet) — l'IVR 7000 attend déjà les appels entrants.</li>
<li><b>3. Passer au tunnel Cloudflare nommé</b> avec domaine dédié — bootstrap stable, certificat Let's Encrypt sur l'UI.</li>
<li><b>4. Automatiser la rotation des secrets SIP</b> (90 j) — aujourd'hui procédure manuelle documentée.</li>
<li><b>5. Enrichir la supervision</b> — files 7020, bannissements Fail2Ban et qualité RTP à partir des métriques log déjà collectées.</li>
</ul>
""")
A(keypoints([
    "Neuf limites tracées, aucune bloquante pour l'usage interne actuel.",
    "Les parades sont déjà préparées par la configuration en place (trunks écrits, mode named prévu, NFS documenté).",
    "Priorité 1 : le raccordement physique du VLAN — tout le reste du socle voix l'attend.",
]))

# ── 18. Conclusion ───────────────────────────────────────────────────────
A(chap("18", "ch18", "Conclusion",
       "Retour à la scène d'ouverture : la simplicité des deux minutes était le produit de tout le reste."))
A("""
<p>La collaboratrice de l'entrée de jeu ne le saura jamais, mais ses deux minutes d'onboarding ont
traversé l'intégralité de ce rapport&nbsp;: un <b>bootstrap</b> publié au boot par un service systemd
résilient, une <b>mini-API</b> isolée derrière Apache avec rate-limit et tokens one-shot, un
<b>pool d'extensions</b> créé par scripts idempotents, un <b>transport WSS</b> dont les certificats et
permissions sont réappliqués à chaque démarrage, un <b>pare-feu</b> qui ne connaît que des réseaux
nommés, et un <b>VLAN</b> prêt à prioriser chacun de ses paquets de voix.</p>

<p>Sur les quatre tensions de la problématique, le bilan est net. <b>Qualité contre mutualisation</b>&nbsp;:
résolue par conception (VLAN 10 + DSCP EF), en attente de son raccordement physique.
<b>Ouverture contre surface d'attaque</b>&nbsp;: résolue par le trio deny-par-défaut / Fail2Ban / accès
distant exclusivement tunnelé — au point qu'aucun port entrant n'est requis pour l'API distante.
<b>Simplicité contre rigueur</b>&nbsp;: résolue par le provisionnement QR one-shot, qui distribue des
secrets de 16 caractères sans que personne ne les voie jamais. <b>Automatisation contre fragilité</b>&nbsp;:
résolue par le boot à deux vitesses, où l'Internet est un bonus et non une condition.</p>

<p>Au-delà de la téléphonie, le projet démontre une méthode&nbsp;: <b>une infrastructure racontable</b>.
Chaque choix est un document, chaque document un script, chaque script un contrôle. C'est cette chaîne —
plus encore que les 10 extensions ou les 17 étapes de boot — qui permet à une personne seule d'opérer,
de réparer et de faire évoluer une plateforme que l'on croirait exiger une équipe.</p>
""")
A(callout("key", "En une phrase",
          "ASAPHONE prouve qu'une petite structure peut posséder sa téléphonie — chiffrée, supervisée, "
          "auto-réparante et agréable à utiliser — sans cloud, sans équipe dédiée, et sans qu'aucun "
          "utilisateur n'ait jamais à savoir ce qu'est un codec."))

# ═══════════════════════ ANNEXES ═════════════════════════════════════════
A('<div class="pb"></div>')
A(chap("A", "axa", "Annexe A — Matrice des ports",
       "Tous les flux réseau de la plateforme, avec leur exposition pare-feu."))
A(tbl(["Port(s)", "Proto", "Service", "Exposition (UFW)"],
      [["5060 · 5160", "UDP/TCP", "SIP — signalisation classique", "VLAN voix (+ LAN gestion si autorisé)"],
       ["5061 · 5161", "TCP/TLS", "SIP TLS", "LAN gestion + VLAN voix — jamais « Anywhere »"],
       ["10000 – 20000", "UDP", "RTP / SRTP (média) — marqué DSCP EF", "CIDR voix + LAN autorisés"],
       ["8088", "TCP", "HTTP Asterisk (WebRTC lab)", "LAN autorisés (option)"],
       ["8089", "TCP/TLS", "WSS WebRTC — wss://pbx.local:8089/ws", "LAN autorisés + VPN"],
       ["80 · 443", "TCP", "Apache : UI FreePBX + /provision", "LAN / VPN (443 requis pour l'API)"],
       ["3000", "TCP", "Grafana", "LAN autorisés (option monitoring)"],
       ["8086", "TCP", "InfluxDB 2", "LAN autorisés (option monitoring)"],
       ["5038", "TCP", "AMI Asterisk (collecte Telegraf)", "127.0.0.1 uniquement"],
       ["51820", "UDP", "WireGuard wg0", "Internet (forward box) — ou relais WSS si CGNAT"]],
      widths=[16, 12, 40, 32]))

A(chap("B", "axb", "Annexe B — Plan de numérotation complet",
       "Extensions, services et codes — la carte mémoire de la plateforme."))
A(tbl(["Numéro / code", "Type", "Description"],
      [["1001 – 1002", "Extension classique", "SIP UDP/TLS + SRTP SDES (softphones, téléphones IP)"],
       ["1003 – 1010", "Extension WebRTC", "WSS + DTLS-SRTP (Asaphone) — pool de provisionnement automatique"],
       ["8000", "Sonnerie générale", "Dial simultané des 10 postes, 45 s (dialplan custom)"],
       ["7000", "Accueil horaire", "Ouvré → 7010 ; fermé → message"],
       ["7010", "IVR intelligent", "AGI Python — VIP, horaires, saisie d'extension"],
       ["7020", "File support", "ACD leastrecent, 1001–1010, appels enregistrés"],
       ["7101 – 7110", "Files individuelles", "Une file par poste"],
       ["8001", "Conférence à PIN", "Salle ConfBridge phase3-&lt;PIN&gt;"],
       ["8100", "Test MixMonitor", "Enregistrement + renvoi messagerie 1001"],
       ["6000", "Salle de groupe par défaut", "Annoncée par bootstrap (conference.default_call_uri)"],
       ["6001 – 6099", "Salles numériques", "Réservées"],
       ["asaphone-grp-*", "Salles de groupe", "Une par groupe Asaphone synchronisé"],
       ["*81001 – *81010", "Messagerie directe", "Consultation de la boîte du poste correspondant"]],
      widths=[22, 24, 54]))

A(chap("C", "axc", "Annexe C — Glossaire",
       "Les termes qui reviennent, définis dans le contexte du projet."))
A(tbl(["Terme", "Définition"],
      [["AGI / AMI", "Interfaces Asterisk : Gateway Interface (scripts appelés par le dialplan) / Manager Interface (contrôle et événements, port 5038)"],
       ["B2BUA", "Back-to-back user agent — le PBX termine chaque jambe d'appel et les ponte ; le média ne circule jamais en direct entre postes"],
       ["Bootstrap", "Fichier JSON statique de découverte (GitHub Pages) : indique au client API, WSS, VPN, codecs — republié à chaque boot"],
       ["ConfBridge", "Application de conférence d'Asterisk : mixage audio côté serveur"],
       ["DSCP EF", "Classe QoS « Expedited Forwarding » (46 / 0x2e) posée sur les paquets RTP pour la file prioritaire"],
       ["DTLS-SRTP", "Chiffrement média WebRTC : clés négociées en DTLS, flux transporté en SRTP"],
       ["ICE / AVPF / rtcp-mux", "Négociation de chemins réseau / profil RTP à retour rapide / RTP+RTCP sur un même port — le triptyque exigé par WebRTC"],
       ["jti", "Identifiant unique de token — support de la révocation one-shot (QR) et de l'authentification des API (X-Provision-Jti)"],
       ["localnets", "Réseaux déclarés « locaux » à PJSIP : pas de réécriture NAT pour ces sources"],
       ["mDNS", "Multicast DNS (Avahi) — résolution de pbx.local sans serveur DNS ; suppléé par le fichier hosts sous Windows"],
       ["PJSIP", "Pile SIP moderne d'Asterisk (chan_pjsip), remplaçante de chan_sip"],
       ["SDES", "Échange des clés SRTP dans le SDP (media_encryption=sdes) — chiffrement média des postes classiques"],
       ["Trunk SIP", "Lien SIP permanent PBX ↔ opérateur ou PBX ↔ PBX — à ne pas confondre avec le trunk VLAN 802.1Q"],
       ["WSS", "WebSocket sécurisé (TLS) — canal de signalisation SIP des clients WebRTC, port 8089"]],
      widths=[20, 80]))

A(chap("D", "axd", "Annexe D — Table des figures",
       "Chaque illustration du document, son titre et le chapitre où la retrouver."))
A(tbl(["N°", "Titre de la figure", "Chapitre"],
      [[f"Fig. {n}", c[0].upper() + c[1:], ch] for (n, c, ch) in _FIG["reg"]],
      widths=[10, 74, 16]))
A('<p class="small" style="margin-top:6mm">Les informations absentes des dépôts sont signalées comme '
  'telles ; aucun secret (.env, tokens, mots de passe SIP/DB) n\'est reproduit. '
  '© Projet ASAPHONE, juillet 2026.</p>')

A("</body></html>")

html = "".join(H)
HTML(string=html, base_url=ROOT).write_pdf(OUT)
print("PDF généré :", OUT)
