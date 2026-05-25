#!/usr/bin/env python3
"""
IVR Phase 3 — logique AGI (sans dépendance pip).
- Plage horaire / jour : renvoie un code pour le dialplan (optionnel) ou joue des prompts.
- VIP : numéros listés dans /etc/asterisk/phase3-vip.txt (un par ligne, préfixes autorisés).
- Langue : agi_arg_1 depuis le dialplan (ex. fr / en) pour choix de prompts.
"""
from __future__ import annotations

import datetime as _dt
import os
import sys


def _read_agi_env() -> dict[str, str]:
    env: dict[str, str] = {}
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.rstrip("\r\n")
        if line == "":
            break
        if ": " in line:
            k, _, v = line.partition(": ")
            env[k] = v
    return env


def _agi(cmd: str) -> str:
    sys.stdout.write(cmd + "\n")
    sys.stdout.flush()
    return sys.stdin.readline() or ""


def _load_vip_patterns(path: str = "/etc/asterisk/phase3-vip.txt") -> list[str]:
    if not os.path.isfile(path):
        return ["1001", "1002"]
    out: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out or ["1001"]


def _caller_num(env: dict[str, str]) -> str:
    n = env.get("agi_calleridnum", "") or env.get("agi_callerid", "")
    for ch in '()"<>':
        n = n.replace(ch, "")
    return n.strip()


def _is_vip(num: str, patterns: list[str]) -> bool:
    digits = "".join(c for c in num if c.isdigit())
    if not digits:
        return False
    for p in patterns:
        if digits == p or digits.endswith(p) or digits.startswith(p):
            return True
    return False


def main() -> int:
    env = _read_agi_env()
    caller = _caller_num(env)
    lang = (env.get("agi_arg_1", "") or "fr").lower()
    vip = _is_vip(caller, _load_vip_patterns())

    _agi('VERBOSE "phase3_ivr caller=%s vip=%s lang=%s" 3' % (caller, int(vip), lang))

    now = _dt.datetime.now()
    open_hours = now.weekday() < 5 and 9 <= now.hour < 18

    _agi("ANSWER")

    if vip:
        _agi('STREAM FILE hello-world ""')

    if lang.startswith("en"):
        prompt_open = "hello-world"
        prompt_closed = "vm-goodbye"
    else:
        prompt_open = "hello-world"
        prompt_closed = "vm-goodbye"

    if open_hours:
        _agi('STREAM FILE %s ""' % prompt_open)
        _agi('SET VARIABLE PHASE3_SLOT "open"')
    else:
        _agi('STREAM FILE %s ""' % prompt_closed)
        _agi('SET VARIABLE PHASE3_SLOT "closed"')

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
