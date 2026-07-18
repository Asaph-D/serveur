#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Présentation ASAPHONE — diapositives 16:9 rendues en PDF (WeasyPrint).
Produit : asterisk-asaphone-presentation.pdf (racine du dépôt).
"""

import os
import base64
from weasyprint import HTML

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "asterisk-asaphone-presentation.pdf")


def wm(fill, opacity):
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='1123' height='631' "
        "viewBox='0 0 1123 631'>"
        f"<text x='561' y='340' font-family='Ubuntu,sans-serif' font-size='72' "
        f"font-weight='700' letter-spacing='20' fill='{fill}' fill-opacity='{opacity}' "
        "text-anchor='middle' transform='rotate(-30 561 315)'>ASAPHONE</text></svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


WM_INK = wm("#1B4F72", "0.045")
WM_WHITE = wm("#FFFFFF", "0.05")

CSS = """
@page { size: 297mm 167mm; margin: 0; }
* { box-sizing: border-box; }
body { font-family:"Ubuntu","DejaVu Sans",sans-serif; color:#22313F; margin:0; }

.sl { width:297mm; height:167mm; page-break-after:always; position:relative;
  padding:16mm 20mm 14mm; overflow:hidden;
  background:url("__WM_INK__") no-repeat center center / 297mm 167mm, #FBFCFD; }
.sl.dark { color:#fff;
  background:url("__WM_WHITE__") no-repeat center center / 297mm 167mm,
             linear-gradient(135deg,#071B2C 0%,#0E3050 45%,#1B4F72 75%,#12695C 100%); }

/* bandes décoratives */
.sl::after { content:""; position:absolute; left:0; top:0; bottom:0; width:2.4mm;
  background:linear-gradient(180deg,#1B4F72,#148F77); }
.sl.dark::after { background:linear-gradient(180deg,#2EC4A5,#7D3C98); }

.kick { font-size:10pt; font-weight:700; letter-spacing:.30em; text-transform:uppercase;
  color:#148F77; margin:0 0 3mm; }
.dark .kick { color:#7FD4C3; }
h1.t { font-size:24pt; font-weight:700; color:#132F45; margin:0 0 2.5mm;
  letter-spacing:-.01em; line-height:1.15; }
.dark h1.t { color:#fff; }
p.sub { font-size:11pt; color:#5B7183; margin:0 0 7mm; }
.dark p.sub { color:#A8C6DA; }

.foot { position:absolute; bottom:7mm; left:20mm; right:20mm; display:flex;
  justify-content:space-between; font-size:7.5pt; color:#9AAAB8;
  border-top:.4pt solid #DCE4EA; padding-top:2.2mm; }
.dark .foot { color:#7E9DB2; border-top-color:rgba(255,255,255,.2); }

.row { display:flex; gap:8mm; }
.col { flex:1; min-width:0; }

ul.big { margin:0; padding-left:5.5mm; font-size:11.5pt; line-height:1.55; }
ul.big li { margin-bottom:3.5mm; }
ul.big li b { color:#1B4F72; }
.dark ul.big li b { color:#7FD4C3; }

.imgbox { text-align:center; }
.imgbox img { max-width:100%; border:.4pt solid #D5DEE6; border-radius:2mm;
  background:#fff; }
.imgcap { font-size:8pt; color:#8296A6; font-style:italic; margin-top:2mm; text-align:center;}

.kard { background:#fff; border:.4pt solid #D8E2EA; border-left:2.8pt solid #148F77;
  border-radius:2mm; padding:4.5mm 5.5mm; margin-bottom:4.5mm; }
.kard.p { border-left-color:#7D3C98; }
.kard.r { border-left-color:#C0392B; }
.kard.b { border-left-color:#1B4F72; }
.kard h3 { margin:0 0 1.6mm; font-size:11.5pt; color:#1B4F72; }
.kard p { margin:0; font-size:9.5pt; color:#33475A; line-height:1.5; }

.stat { display:inline-block; width:30%; margin:0 1.2% 4mm 0; padding:4.5mm 4mm;
  background:rgba(255,255,255,.07); border:.4pt solid rgba(255,255,255,.25);
  border-radius:2.4mm; vertical-align:top; }
.stat b { display:block; font-size:19pt; color:#7FD4C3; }
.stat span { font-size:8pt; color:#C4D9E6; text-transform:uppercase; letter-spacing:.07em;
  line-height:1.3; display:block; margin-top:1.2mm; }

table.tb { width:100%; border-collapse:collapse; font-size:9.5pt; }
.tb th { background:#1B4F72; color:#fff; text-align:left; padding:2.6mm 3mm; font-size:8.8pt; }
.tb td { padding:2.4mm 3mm; border-bottom:.4pt solid #DCE4EA; vertical-align:top; }
.tb tr:nth-child(even) td { background:#F2F6F9; }

.agitem { display:flex; align-items:baseline; gap:4mm; padding:3.2mm 0;
  border-bottom:.35pt solid #DCE4EA; font-size:12pt; }
.agitem .n { color:#148F77; font-weight:700; font-size:11pt; width:9mm; }

.pill { display:inline-block; background:#EAF7F3; color:#0E6B58; font-weight:700;
  font-size:8.4pt; border-radius:5mm; padding:1mm 3.6mm; margin:0 1.5mm 1.5mm 0; }
.pill.p { background:#F3EBF8; color:#6A2F84; }
.pill.b { background:#EAF2F9; color:#1B4F72; }

.punch { position:absolute; bottom:16mm; left:20mm; right:20mm; text-align:center;
  font-size:12.5pt; color:#1B4F72; font-weight:600; }
.punch em { color:#148F77; font-style:normal; }

.qm { font-size:15pt; line-height:1.6; color:#DCE9F2; font-weight:300; max-width:230mm; }
.qm b { color:#7FD4C3; font-weight:700; }
"""

S = []


def slide(kick, title, sub, body, num, total, dark=False):
    cls = "sl dark" if dark else "sl"
    S.append(
        f'<div class="{cls}">'
        + (f'<div class="kick">{kick}</div>' if kick else "")
        + (f'<h1 class="t">{title}</h1>' if title else "")
        + (f'<p class="sub">{sub}</p>' if sub else "")
        + body
        + f'<div class="foot"><span>ASAPHONE · Rapport technique — présentation</span>'
          f'<span>{num} / {total}</span></div></div>'
    )


TOTAL = 18

# ── 1. Titre ──────────────────────────────────────────────────────────────
S.append(f"""
<div class="sl dark" style="padding-top:26mm">
  <div class="kick" style="letter-spacing:.5em">A S A P H O N E</div>
  <h1 class="t" style="font-size:34pt; margin-top:6mm">La téléphonie d'entreprise,<br/>
  <span style="font-weight:300;color:#BFD8E8">reconstruite de bout en bout.</span></h1>
  <p class="sub" style="max-width:200mm; margin-top:5mm">PBX Asterisk 20 / FreePBX 17 · softphone Flutter
  multiplateforme · provisionnement par QR · VPN WireGuard · supervision temps réel.</p>
  <div style="margin-top:10mm">
    <div class="stat"><b>10</b><span>extensions PJSIP · 1001–1010</span></div>
    <div class="stat"><b>&lt; 2 min</b><span>onboarding utilisateur</span></div>
    <div class="stat"><b>0</b><span>backend cloud — tout vit sur le PBX</span></div>
  </div>
  <div class="foot"><span>github.com/Asaph-D/serveur · github.com/Asaph-D/asaphone</span>
  <span>Juillet 2026</span></div>
</div>
""")

# ── 2. Accroche ───────────────────────────────────────────────────────────
slide("Entrée de jeu", "Deux minutes, un QR code, un appel.", "",
      """
<div class="qm" style="margin-top:8mm; color:#33475A; font-size:14pt">
« Lundi, 8 h 47. Une nouvelle collaboratrice ouvre Asaphone. Elle n'a ni compte, ni identifiants :
elle saisit son e-mail, tape le code à six chiffres reçu, scanne le QR qui arrive dans la foulée.<br/><br/>
À 8 h 49, son poste <b style="color:#148F77">1007</b> est enregistré sur le PBX en WebSocket sécurisé ;
elle compose <b style="color:#148F77">1001</b> — son premier appel, chiffré, traverse le VLAN voix
avec la priorité d'un paquet marqué or. »</div>
<div class="punch">Cette présentation montre comment cette simplicité apparente est <em>fabriquée</em>.</div>
""", 2, TOTAL)

# ── 3. Agenda ─────────────────────────────────────────────────────────────
slide("Agenda", "Le parcours en cinq temps", "",
      """
<div class="row" style="margin-top:4mm">
<div class="col">
  <div class="agitem"><span class="n">01</span>Problématique &amp; concepts clés</div>
  <div class="agitem"><span class="n">02</span>Conception — architecture, réseau, sécurité</div>
  <div class="agitem"><span class="n">03</span>Réalisation — postes, services, WebRTC, client</div>
</div>
<div class="col">
  <div class="agitem"><span class="n">04</span>Exploitation — VPN, supervision, boot automatisé</div>
  <div class="agitem"><span class="n">05</span>Bilan — validation, limites, conclusion</div>
  <div style="margin-top:8mm">
    <span class="pill">Asterisk 20 LTS</span><span class="pill">FreePBX 17</span>
    <span class="pill p">Flutter</span><span class="pill p">WebRTC</span>
    <span class="pill b">WireGuard</span><span class="pill b">Grafana</span>
  </div>
</div>
</div>
""", 3, TOTAL)

# ── 4. Problématique ──────────────────────────────────────────────────────
slide("Problématique", "Quatre tensions à résoudre simultanément",
      "Souveraine, sécurisée, utilisable en 2 minutes, exploitable par une seule personne — même sans Internet.",
      """
<div class="row">
<div class="col">
  <div class="kard"><h3>T1 · Qualité vs mutualisation</h3>
  <p>La voix exige latence et priorité ; le LAN bureautique n'en offre aucune.
  → <b>VLAN 10 dédié + QoS DSCP EF</b>.</p></div>
  <div class="kard r"><h3>T2 · Ouverture vs surface d'attaque</h3>
  <p>Un PBX joignable de partout est scanné en continu.
  → <b>deny par défaut + Fail2Ban + accès exclusivement tunnelé</b>.</p></div>
</div>
<div class="col">
  <div class="kard p"><h3>T3 · Simplicité vs rigueur</h3>
  <p>L'utilisateur veut un QR ; la sécurité veut des secrets forts et révocables.
  → <b>QR one-shot, token révoqué au premier usage</b>.</p></div>
  <div class="kard b"><h3>T4 · Automatisation vs fragilité</h3>
  <p>Le boot doit réussir même sans Internet.
  → <b>étapes critiques vs optionnelles (OK / SKIP)</b>.</p></div>
</div>
</div>
""", 4, TOTAL)

# ── 5. Concepts clés ──────────────────────────────────────────────────────
slide("Concepts clés", "Le vocabulaire en une diapositive", "",
      """
<div class="row">
<div class="col">
  <div class="kard"><h3>SIP &amp; RTP/SRTP</h3><p><b>SIP</b> gère la sonnette (REGISTER, INVITE, BYE) ;
  <b>RTP</b> transporte la voix — <b>SRTP</b> en est la version chiffrée.</p></div>
  <div class="kard"><h3>PBX · B2BUA</h3><p>Le central téléphonique (Asterisk). Chaque appel est terminé
  puis ré-émis : deux jambes indépendantes, pontées au centre — c'est ce qui permet de tout mélanger.</p></div>
  <div class="kard"><h3>WebRTC</h3><p>La pile temps réel du web : signalisation <b>WSS</b>,
  média <b>DTLS-SRTP</b>, négociation <b>ICE</b>, codec <b>Opus</b>. Celle d'Asaphone.</p></div>
</div>
<div class="col">
  <div class="kard p"><h3>VLAN &amp; QoS (DSCP)</h3><p>Le VLAN isole la voix sur un segment dédié ;
  le marquage DSCP EF la fait passer devant tout le reste.</p></div>
  <div class="kard p"><h3>VPN WireGuard · CGNAT</h3><p>Tunnel chiffré qui ramène un poste distant
  « au bureau » ; le relais WebSocket contourne les réseaux 4G/Starlink sans port entrant.</p></div>
  <div class="kard p"><h3>Provisionnement &amp; bootstrap</h3><p>Configuration automatique du poste par QR ;
  le client découvre API, WSS et VPN via un fichier publié — il ne connaît rien d'avance.</p></div>
</div>
</div>
""", 5, TOTAL)

# ── 6. Architecture ───────────────────────────────────────────────────────
slide("Conception", "Architecture globale",
      "Chaque flux traverse une frontière de sécurité avant d'atteindre le cœur B2BUA.",
      """
<div class="imgbox"><img src="figures/fig-architecture-globale.png" style="max-height:112mm"/></div>
""", 6, TOTAL)

# ── 7. Réseau ─────────────────────────────────────────────────────────────
slide("Conception", "Un PBX, trois pattes réseau",
      "Gestion, voix et VPN : trois mondes étanches, unifiés par les localnets PJSIP.",
      """
<div class="row">
<div class="col" style="flex:1.6"><div class="imgbox">
  <img src="figures/fig-dual-homing.png" style="max-height:104mm"/></div></div>
<div class="col">
  <ul class="big" style="font-size:10.5pt">
    <li><b>VLAN 10 — 10.10.10.0/24</b> : PBX en .10, téléphones en DHCP .50–.200.</li>
    <li><b>QoS</b> : tout paquet RTP (10000–20000) marqué <b>DSCP EF</b> — la file prioritaire.</li>
    <li><b>VPN — 10.200.0.0/24</b> : un poste distant devient un poste local.</li>
    <li>Un /24 distinct par zone : ACL lisibles, domaines de broadcast séparés.</li>
  </ul>
</div>
</div>
""", 7, TOTAL)

# ── 8. Sécurité ───────────────────────────────────────────────────────────
slide("Conception", "Sécurité en profondeur — huit couches",
      "Chaque couche est scriptée, contrôlable, et rattrape les failles de la précédente.",
      """
<div class="row">
<div class="col" style="flex:1.7"><div class="imgbox">
  <img src="figures/fig-securite-couches.png" style="max-height:106mm"/></div></div>
<div class="col">
  <ul class="big" style="font-size:10.5pt">
    <li><b>Chiffrement par segment</b> : TLS + SRTP côté classique, WSS + DTLS côté WebRTC.</li>
    <li><b>Frontière</b> : UFW deny par défaut, Fail2Ban bannit les scans SIP.</li>
    <li><b>Secrets</b> : ≥ 16 caractères, hors dépôt, rotation 90 j.</li>
    <li>Limite assumée : le PBX est un <b>point de confiance</b> (services média obligent).</li>
  </ul>
</div>
</div>
""", 8, TOTAL)

# ── 9. Extensions ─────────────────────────────────────────────────────────
slide("Réalisation", "Dix postes, deux profils média, zéro geste manuel",
      "UI ou scripts → base MariaDB → fwconsole reload : les fichiers Asterisk sont générés, jamais édités.",
      """
<div class="row">
<div class="col" style="flex:1.5"><div class="imgbox">
  <img src="capture/freePBX-interface.png" style="max-height:98mm"/>
  <div class="imgcap">FreePBX 17 — l'interface d'administration du PBX</div></div></div>
<div class="col">
  <table class="tb">
    <tr><th>Postes</th><th>Profil</th></tr>
    <tr><td><b>1001–1002</b></td><td>Classique — UDP/TLS + SRTP (Zoiper, téléphone IP)</td></tr>
    <tr><td><b>1003–1010</b></td><td>WebRTC — WSS 8089 + DTLS-SRTP (pool Asaphone)</td></tr>
    <tr><td><b>8000</b></td><td>Sonnerie générale — les 10 postes, 45 s</td></tr>
    <tr><td><b>7000/7010/7020</b></td><td>Accueil horaire → IVR Python → file ACD</td></tr>
    <tr><td><b>6000 · grp-*</b></td><td>Salles ConfBridge (groupes Asaphone)</td></tr>
  </table>
</div>
</div>
""", 9, TOTAL)

# ── 10. WebRTC ────────────────────────────────────────────────────────────
slide("Réalisation", "Faire parler deux mondes : UDP ↔ WebRTC",
      "Le B2BUA termine chaque jambe et traduit au milieu — SRTP d'un côté, DTLS-SRTP de l'autre.",
      """
<div class="imgbox"><img src="figures/fig-seq-appel-1001-1003.png" style="max-height:110mm"/></div>
""", 10, TOTAL)

# ── 11. Client ────────────────────────────────────────────────────────────
slide("Réalisation", "Le client Asaphone",
      "Un seul code Flutter pour Android, Windows et iOS — et un client qui ne connaît rien d'avance.",
      """
<div class="row" style="align-items:flex-start">
<div class="col" style="flex:2.2">
  <div class="row">
    <div class="col imgbox"><img src="capture/welcome-login.png" style="max-height:92mm"/></div>
    <div class="col imgbox"><img src="capture/clavier.png" style="max-height:92mm"/></div>
    <div class="col imgbox"><img src="capture/appel-video.png" style="max-height:92mm"/></div>
  </div>
  <div class="imgcap">Accueil · clavier d'appel · appel vidéo (démonstration)</div>
</div>
<div class="col">
  <ul class="big" style="font-size:10.5pt">
    <li><b>Appels audio/vidéo</b> DTLS-SRTP (Opus, VP8/H.264).</li>
    <li><b>Chat</b> via SIP MESSAGE — aucun serveur supplémentaire.</li>
    <li><b>Messagerie vocale</b> + notification poussée.</li>
    <li><b>Groupes</b> : un seul appel, ConfBridge mixe côté serveur.</li>
  </ul>
</div>
</div>
""", 11, TOTAL)

# ── 12. Provision ─────────────────────────────────────────────────────────
slide("Réalisation", "Provisionnement de bout en bout",
      "E-mail → code → QR one-shot → REGISTER WSS → token révoqué. Quatre gestes, moins de deux minutes.",
      """
<div class="imgbox"><img src="figures/fig-seq-provision.png" style="max-height:110mm"/></div>
""", 12, TOTAL)

# ── 13. VPN ───────────────────────────────────────────────────────────────
slide("Exploitation", "Joindre le PBX de partout",
      "Un softphone hors site est un problème de couche 3 — la réponse est un pont réseau, pas un réglage SIP.",
      """
<div class="imgbox"><img src="figures/fig-comparatif-liaisons.png" style="max-height:104mm"/></div>
""", 13, TOTAL)

# ── 14. Monitoring ────────────────────────────────────────────────────────
slide("Exploitation", "Observer sans peser",
      "Trois conteneurs, un utilisateur AMI dédié, des dashboards versionnés — l'observabilité se reconstruit d'une commande.",
      """
<div class="row">
<div class="col" style="flex:1.5"><div class="imgbox">
  <img src="figures/fig-monitoring-pipeline.png" style="max-height:100mm"/></div></div>
<div class="col"><div class="imgbox">
  <img src="capture/monitoring.png" style="max-height:64mm"/>
  <div class="imgcap">Dashboard « VoIP / Asterisk » — canaux et appels actifs</div></div>
  <ul class="big" style="font-size:10pt; margin-top:4mm">
    <li>Telegraf interroge l'<b>AMI</b> toutes les 10 s (scripts Python).</li>
    <li>InfluxDB 2 archive, Grafana affiche (Flux) — <b>pas de Prometheus</b>.</li>
  </ul>
</div>
</div>
""", 14, TOTAL)

# ── 15. Boot ──────────────────────────────────────────────────────────────
slide("Exploitation", "Un boot qui se répare tout seul",
      "17 étapes systemd : le cœur PBX démarre sans Internet, les étapes en ligne marquent SKIP et le boot continue.",
      """
<div class="row">
<div class="col" style="flex:1.6"><div class="imgbox">
  <img src="figures/console-startup-3-resume.png" style="max-height:102mm"/></div></div>
<div class="col">
  <ul class="big" style="font-size:10.5pt">
    <li><b>Permissions → fwconsole → WSS → réseau</b> : l'ordre encode les leçons d'exploitation.</li>
    <li><b>Tunnels → bootstrap → publication</b> : l'API distante est republiée à chaque boot.</li>
    <li>Un serveur qui redémarre est un serveur <b>réparé</b>.</li>
  </ul>
</div>
</div>
""", 15, TOTAL)

# ── 16. Validation ────────────────────────────────────────────────────────
slide("Bilan", "« Production d'abord » : tout se vérifie",
      "Chaque brique a une validation consignée et une commande de rejeu.",
      """
<div class="row">
<div class="col">
  <table class="tb">
    <tr><th>Domaine</th><th>Preuve</th></tr>
    <tr><td>Appels mixtes</td><td>1001 (UDP) ↔ 1003 (WSS) : bridge établi en réel</td></tr>
    <tr><td>WSS / TLS</td><td>HTTPS 8089 actif, transport wss vérifié</td></tr>
    <tr><td>Provision</td><td>Flux complet rejouable en curl, sans client</td></tr>
    <tr><td>QoS</td><td>Marquage EF contrôlé (iptables + tcpdump)</td></tr>
    <tr><td>Boot</td><td>Journal complet + résumé « serveur-startup: OK »</td></tr>
  </table>
</div>
<div class="col">
  <div class="kard b"><h3>Le réflexe santé</h3>
  <p style="font-family:'Ubuntu Mono',monospace; font-size:9pt; line-height:1.7">
  pjsip show contacts · http show status<br/>
  ufw status · fail2ban-client status asterisk<br/>
  curl -sk https://pbx.local/provision/<br/>
  tail -50 /var/log/serveur-startup.log</p></div>
  <div class="kard r"><h3>Vigilance ouverte</h3>
  <p>« DTLS packet dropped, ICE not completed yet » en début d'appel — négociation ICE côté client,
  sans impact constaté sur l'établissement.</p></div>
</div>
</div>
""", 16, TOTAL)

# ── 17. Limites ───────────────────────────────────────────────────────────
slide("Bilan", "Limites assumées, chantiers ordonnés",
      "Aucune limite n'est cachée : chacune est tracée avec sa parade déjà préparée.",
      """
<div class="row">
<div class="col">
  <div class="kard"><h3>Ce qui manque encore</h3><p>
  Trunk VLAN 10 physique à raccorder · trunks opérateur inactifs (secrets à fournir) ·
  SMTP par poste · URL de tunnel éphémères · pas d'E2EE strict (B2BUA).</p></div>
  <div class="kard p"><h3>Pourquoi ce n'est pas bloquant</h3><p>
  La téléphonie interne est complète et autonome ; chaque parade est déjà écrite
  (routes trunk préparées, mode tunnel nommé prévu, notification Asaphone opérationnelle).</p></div>
</div>
<div class="col">
  <div class="kard b"><h3>Les cinq chantiers suivants</h3><p>
  1 · Raccorder le VLAN 10 (switch / hyperviseur)<br/>
  2 · Activer un trunk opérateur — l'IVR attend les appels<br/>
  3 · Tunnel Cloudflare nommé + domaine dédié<br/>
  4 · Rotation automatique des secrets SIP (90 j)<br/>
  5 · Supervision enrichie : files, bannissements, qualité RTP</p></div>
</div>
</div>
""", 17, TOTAL)

# ── 18. Conclusion ────────────────────────────────────────────────────────
slide("Conclusion", "Une infrastructure racontable", "",
      """
<div class="qm" style="margin-top:6mm">
Chaque choix est un document, chaque document un script, chaque script un contrôle.<br/><br/>
C'est cette chaîne — plus que les 10 extensions ou les 17 étapes de boot — qui permet à
<b>une personne seule</b> d'opérer une plateforme que l'on croirait exiger une équipe.<br/><br/>
ASAPHONE prouve qu'une petite structure peut <b>posséder sa téléphonie</b> : chiffrée, supervisée,
auto-réparante — sans cloud, et sans qu'aucun utilisateur n'ait jamais à savoir ce qu'est un codec.
</div>
<div style="position:absolute; bottom:16mm; left:20mm">
  <span class="pill" style="background:rgba(255,255,255,.12); color:#7FD4C3">Merci — questions ?</span>
</div>
""", 18, TOTAL, dark=True)

html = ('<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
        '<title>ASAPHONE — Présentation</title>'
        f'<style>{CSS.replace("__WM_INK__", WM_INK).replace("__WM_WHITE__", WM_WHITE)}</style>'
        "</head><body>" + "".join(S) + "</body></html>")

HTML(string=html, base_url=ROOT).write_pdf(OUT)
print("PDF généré :", OUT)
