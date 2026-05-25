#!/usr/bin/env python3
"""Métriques Asterisk via AMI → ligne Influx pour Telegraf [[inputs.exec]].

Pourquoi Grafana affichait 0 "active_channels" alors que des postes sont enregistrés :
- `core show channels` mesure les canaux/appels EN COURS, pas les terminaux enregistrés.

On exporte donc aussi des compteurs PJSIP (contacts/enregistrements) via `pjsip show contacts`
et une présence par endpoint (permet de suivre création/suppression côté monitoring).
"""
from __future__ import annotations

import os
import re
import socket
import sys
import time


def _env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if v is None or v == "":
        print(f"ami_metrics: variable {name} requise", file=sys.stderr)
        sys.exit(1)
    return v


def _readline(sock: socket.socket, buf: bytearray) -> str:
    while True:
        if b"\n" in buf:
            i = buf.index(b"\n")
            raw = bytes(buf[: i + 1])
            del buf[: i + 1]
            return raw.decode(errors="replace").rstrip("\r\n")
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("AMI: socket fermé")
        buf.extend(chunk)


def main() -> None:
    host = os.environ.get("AMI_HOST", "127.0.0.1")
    port = int(os.environ.get("AMI_PORT", "5038"))
    user = os.environ.get("AMI_USER", "telegraf")
    secret = _env("AMI_PASSWORD")

    sock = socket.create_connection((host, port), timeout=8)
    sock.settimeout(20)
    buf = bytearray()

    banner = _readline(sock, buf)
    if "Asterisk Call Manager" not in banner:
        print(f"ami_metrics: bannière inattendue: {banner!r}", file=sys.stderr)

    login = (
        "Action: Login\r\nUsername: %s\r\nSecret: %s\r\nEvents: off\r\n\r\n"
        % (user, secret)
    )
    sock.sendall(login.encode())

    ok = False
    while True:
        line = _readline(sock, buf)
        if "Authentication accepted" in line:
            ok = True
        if "Authentication failed" in line or "Permission denied" in line:
            print(f"ami_metrics: login refusé ({line})", file=sys.stderr)
            sys.exit(1)
        if line == "":
            if ok:
                break

    def ami_command(command: str) -> str:
        sock.sendall(f"Action: Command\r\nCommand: {command}\r\n\r\n".encode())
        outputs: list[str] = []
        while True:
            line = _readline(sock, buf)
            if line == "--END COMMAND OUTPUT--":
                break
            if line.startswith("Response: Error"):
                raise RuntimeError(line)
            if line.startswith("Output:"):
                outputs.append(line[7:].lstrip())
                continue
            # AMI 9.x : fin de Command souvent = ligne vide après les Output (sans --END COMMAND OUTPUT--)
            if line == "" and outputs:
                break
        return "\n".join(outputs)

    try:
        text = ami_command("core show channels")
        contacts = ami_command("pjsip show contacts")
        endpoints = ami_command("pjsip show endpoints")
    except Exception as e:
        print(f"ami_metrics: AMI commande échouée: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            sock.sendall(b"Action: Logoff\r\n\r\n")
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
    ch = 0
    calls = 0
    m = re.search(r"(\d+)\s+active\s+channel", text, re.I)
    if m:
        ch = int(m.group(1))
    m = re.search(r"(\d+)\s+active\s+call", text, re.I)
    if m:
        calls = int(m.group(1))

    ts = int(time.time() * 1_000_000_000)
    # Compte des contacts enregistrés : lignes "Contact:" dans la sortie.
    # (Ex: "Contact:  1001/sip:1001@192.168....")
    contact_count = len(re.findall(r"^\s*Contact:\s+", contacts, re.M))

    print(
        "asterisk_core,host=freepbx "
        f"active_channels={ch}i,active_calls={calls}i,registered_contacts={contact_count}i {ts}"
    )

    # Présence par endpoint (pour inventaire / durée de vie).
    # Format lignes dans "pjsip show endpoints" :
    #   Endpoint:  1001/1001  ...  (ou autre ID)
    for m in re.finditer(r"^\s*Endpoint:\s+([A-Za-z0-9_.-]+)/", endpoints, re.M):
        eid = m.group(1)
        # Evite la pollution si jamais un endpoint "anonymous" apparaît.
        if not eid or len(eid) > 32:
            continue
        safe = eid.replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")
        print(f"pjsip_endpoint_presence,host=freepbx,endpoint={safe} present=1i {ts}")


if __name__ == "__main__":
    main()
