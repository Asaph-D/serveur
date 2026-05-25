#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path


STATE_PATH = Path(os.environ.get("LOG_METRICS_STATE", "/tmp/log_metrics.state.json"))


@dataclass(frozen=True)
class FileSpec:
    measurement: str
    path: Path
    patterns: dict[str, re.Pattern[str]]


ASTERISK_LOG = Path(os.environ.get("ASTERISK_FULL_LOG", "/var/log/asterisk/full"))
FAIL2BAN_LOG = Path(os.environ.get("FAIL2BAN_LOG", "/var/log/fail2ban.log"))


SPECS: list[FileSpec] = [
    FileSpec(
        measurement="asterisk_events",
        path=ASTERISK_LOG,
        patterns={
            "rtp_timeout": re.compile(r"rtp_check_timeout: Disconnecting channel", re.I),
            "pjsip_auth_fail": re.compile(r"Authentication failed|Failed to authenticate", re.I),
            "pjsip_reg_fail": re.compile(r"Registration from .* failed|No matching endpoint found", re.I),
            "tls_fail": re.compile(r"TLS (?:fatal )?alert|SSL_accept|handshake failed", re.I),
            "sdp_fail": re.compile(r"Couldn't add sdp streams|create_local_sdp", re.I),
            "cdr_missing": re.compile(r"Unable to find CDR for channel", re.I),
        },
    ),
    FileSpec(
        measurement="fail2ban_events",
        path=FAIL2BAN_LOG,
        patterns={
            "ban": re.compile(r"\bBan\b", re.I),
            "unban": re.compile(r"\bUnban\b", re.I),
            "found": re.compile(r"\bFound\b", re.I),
        },
    ),
]


def load_state() -> dict[str, dict[str, int]]:
    try:
        data = json.loads(STATE_PATH.read_text())
        if isinstance(data, dict):
            return {str(k): {"pos": int(v.get("pos", 0)), "ino": int(v.get("ino", 0))} for k, v in data.items()}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return {}


def save_state(state: dict[str, dict[str, int]]) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        tmp.replace(STATE_PATH)
    except Exception:
        pass


def _stat_ino(p: Path) -> int:
    try:
        return p.stat().st_ino
    except Exception:
        return 0


def _read_new_lines(p: Path, prev_pos: int, prev_ino: int) -> tuple[list[str], int, int]:
    try:
        st = p.stat()
    except FileNotFoundError:
        return [], 0, 0
    except Exception:
        return [], prev_pos, prev_ino

    ino = st.st_ino
    size = st.st_size
    pos = prev_pos
    if prev_ino != 0 and ino != prev_ino:
        pos = 0
    if pos > size:
        pos = 0

    lines: list[str] = []
    try:
        with p.open("rb") as f:
            f.seek(pos)
            data = f.read()
            pos = f.tell()
        # best-effort decode; splitlines handles trailing newline
        text = data.decode(errors="replace")
        lines = text.splitlines()
    except Exception:
        return [], prev_pos, prev_ino

    return lines, pos, ino


def influx_escape_tag_value(v: str) -> str:
    return v.replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def print_counts(measurement: str, tags: dict[str, str], counts: dict[str, int], ts_ns: int) -> None:
    tagstr = ",".join([f"{k}={influx_escape_tag_value(v)}" for k, v in sorted(tags.items())])
    if tagstr:
        head = f"{measurement},{tagstr}"
    else:
        head = measurement
    fieldstr = ",".join([f"{k}={v}i" for k, v in sorted(counts.items())])
    print(f"{head} {fieldstr} {ts_ns}")


def main() -> int:
    host = os.environ.get("HOST_TAG", "freepbx")
    state = load_state()
    ts_ns = int(time.time() * 1_000_000_000)
    out_state: dict[str, dict[str, int]] = dict(state)

    for spec in SPECS:
        key = str(spec.path)
        prev = state.get(key, {"pos": 0, "ino": 0})
        lines, pos, ino = _read_new_lines(spec.path, prev.get("pos", 0), prev.get("ino", 0))
        out_state[key] = {"pos": pos, "ino": ino}

        counts = {name: 0 for name in spec.patterns.keys()}
        for line in lines:
            for name, pat in spec.patterns.items():
                if pat.search(line):
                    counts[name] += 1

        # Always emit fields (helps dashboards); if file missing, counts remain 0.
        print_counts(spec.measurement, {"host": host}, counts, ts_ns)

    save_state(out_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

