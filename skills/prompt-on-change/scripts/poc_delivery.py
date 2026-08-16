#!/usr/bin/env python3
"""Wrapper-only Grok delivery helpers (not the detect engine)."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
FRESH_SECONDS = 24 * 60 * 60


def parse_to(spec: str) -> tuple[str, str]:
    if not spec or ":" not in spec:
        raise SystemExit("error: --to requires grok:<uuid>")
    host, ident = spec.split(":", 1)
    host = host.strip().lower()
    ident = ident.strip()
    if host != "grok":
        raise SystemExit(f"error: unknown host '{host}' — this slice supports grok:<uuid> only")
    if not UUID_RE.match(ident):
        raise SystemExit("error: --to grok:<uuid> requires a UUID (no titles, no last)")
    return host, ident.lower()


def grok_home() -> Path:
    return Path(os.environ.get("GROK_HOME") or Path.home() / ".grok")


def find_session_dir(session_id: str) -> Path | None:
    root = grok_home() / "sessions"
    if not root.is_dir():
        return None
    hits = [p for p in root.glob(f"*/{session_id}") if p.is_dir()]
    if not hits:
        return None
    if len(hits) > 1:
        raise SystemExit(f"error: multiple session dirs for {session_id}")
    return hits[0]


def session_cwd_from_dir(session_dir: Path) -> str | None:
    """Decode the glob parent. Does not re-encode a process cwd."""
    decoded = unquote(session_dir.parent.name)
    return decoded if decoded.startswith("/") else None


def env_assume_idle(flag: bool) -> bool:
    if flag:
        return True
    return os.environ.get("POC_ASSUME_IDLE") == "1"


def assert_cwd(session_dir: Path | None, cwd: str | None) -> str | None:
    decoded = session_cwd_from_dir(session_dir) if session_dir is not None else None
    if cwd and decoded:
        if os.path.realpath(cwd) != os.path.realpath(decoded):
            raise SystemExit(
                f"error: --cwd {cwd} disagrees with session dir cwd {decoded}"
            )
    return decoded


def _parse_opened_at(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def liveness(session_id: str) -> dict:
    """Return {state: live|uncertain|idle, reason, pid}."""
    path = grok_home() / "active_sessions.json"
    if not path.is_file():
        return {"state": "idle", "reason": "no active_sessions.json", "pid": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"state": "uncertain", "reason": "active_sessions.json unreadable", "pid": None}
    if not isinstance(data, list):
        return {"state": "uncertain", "reason": "active_sessions.json not a list", "pid": None}
    now = datetime.now(timezone.utc)
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("session_id", "")).lower() != session_id.lower():
            continue
        pid = entry.get("pid")
        alive = False
        if isinstance(pid, int) and pid > 0:
            try:
                os.kill(pid, 0)
                alive = True
            except OSError:
                alive = False
        opened = _parse_opened_at(str(entry.get("opened_at") or ""))
        age = (now - opened).total_seconds() if opened else None
        fresh = age is not None and 0 <= age <= FRESH_SECONDS
        if alive and fresh:
            return {"state": "live", "reason": f"fresh active pid {pid}", "pid": pid}
        if alive:
            return {
                "state": "uncertain",
                "reason": f"stale active_sessions entry pid {pid} opened_at={entry.get('opened_at')}",
                "pid": pid,
            }
        return {"state": "idle", "reason": f"recorded pid {pid} is dead", "pid": pid}
    return {"state": "idle", "reason": "id not in active_sessions.json", "pid": None}


def decide(session_id: str, *, force_new: bool, assume_idle: bool, cwd: str | None = None) -> dict:
    assume_idle = env_assume_idle(assume_idle)
    if force_new:
        return {
            "decision": "force-new",
            "session_dir": None,
            "session_cwd": None,
            "reason": "--force-new",
            "liveness": "n/a",
        }
    session_dir = find_session_dir(session_id)
    decoded = assert_cwd(session_dir, cwd)
    if session_dir is None:
        return {
            "decision": "new",
            "session_dir": None,
            "session_cwd": None,
            "reason": "no local session dir",
            "liveness": "n/a",
        }
    live = liveness(session_id)
    if live["state"] in {"live", "uncertain"} and not assume_idle:
        return {
            "decision": "refuse",
            "session_dir": str(session_dir),
            "session_cwd": decoded,
            "reason": live["reason"],
            "liveness": live["state"],
        }
    return {
        "decision": "resume",
        "session_dir": str(session_dir),
        "session_cwd": decoded,
        "reason": live["reason"] if assume_idle else "not live",
        "liveness": live["state"],
    }


def cmd_decide(args: argparse.Namespace) -> int:
    host, ident = parse_to(args.to)
    out = decide(
        ident,
        force_new=args.force_new,
        assume_idle=args.assume_idle,
        cwd=args.cwd,
    )
    out["host"] = host
    out["id"] = ident
    print(json.dumps(out))
    return 0


def cmd_parse_to(args: argparse.Namespace) -> int:
    host, ident = parse_to(args.to)
    print(json.dumps({"host": host, "id": ident}))
    return 0


def cmd_escalation_types(args: argparse.Namespace) -> int:
    matched: list[str] = []
    other: list[str] = []
    for raw in args.paths:
        path = Path(raw)
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            other.append(str(path))
            continue
        if data.get("escalation_type") == "condition_matched":
            matched.append(str(path))
        else:
            other.append(str(path))
    print(json.dumps({"condition_matched": matched, "other": other}))
    return 0


def cmd_with_lock(args: argparse.Namespace) -> int:
    lock_path = Path(args.lock)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return subprocess.call(args.command)


def main() -> int:
    parser = argparse.ArgumentParser(prog="poc_delivery")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse-to")
    p.add_argument("--to", required=True)
    p.set_defaults(func=cmd_parse_to)

    p = sub.add_parser("decide")
    p.add_argument("--to", required=True)
    p.add_argument("--force-new", action="store_true")
    p.add_argument("--assume-idle", action="store_true")
    p.add_argument("--cwd")
    p.set_defaults(func=cmd_decide)

    p = sub.add_parser("escalation-types")
    p.add_argument("paths", nargs="+")
    p.set_defaults(func=cmd_escalation_types)

    p = sub.add_parser("with-lock")
    p.add_argument("--lock", required=True)
    p.add_argument("command", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_with_lock)

    args = parser.parse_args()
    if args.cmd == "with-lock":
        if args.command and args.command[0] == "--":
            args.command = args.command[1:]
        if not args.command:
            print("error: with-lock needs a command", file=sys.stderr)
            return 64
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
