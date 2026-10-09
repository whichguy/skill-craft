"""The TCP listeners a case's host left behind: find them, stop them, and say so (SPEC: a run leaves nothing listening).

A model's `node server.js &` outlives its session. The harness's own group kill never reaches it (Claude Code gives each
Bash call a process group of its own), so on 2026-10-08 a server of one run, parent pid 1, still held port 3457 when two
later runs chose the same port, and one of them committed a false lesson about it. After a host session, and after the
case checks, the harness stops every listener of its own user whose working directory or command line lies under the
case's output folder, and records what it found as ``left_behind`` in result.json. This module is the one place that
looks at the process table.

Nothing here is a verdict. Where the table cannot be read the answer is :class:`Unobserved`, which a caller records as
"not observed" and never as "none".
"""

from __future__ import annotations

import contextlib
import fcntl
import os
from pathlib import Path
import re
import signal
import subprocess
import time

# A ceiling for one lsof or ps call, not a tuning value: an idle scan takes about 0.15 s. Past it the world is unobserved.
LSOF_TIMEOUT = 30
# After SIGTERM a listener gets this long to go before SIGKILL, and SIGKILL this long to take effect.
GRACE_SECONDS = 3.0
FORCE_SECONDS = 2.0
POLL_SECONDS = 0.1
LOCK_NAME = ".harness-lock"


class Unobserved(Exception):
    """The process table could not be read: the message says why."""


def _run(argv: list[str]) -> str:
    """One read-only tool call. lsof and ps exit 1 when they match nothing; any other failure is Unobserved."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=LSOF_TIMEOUT, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        raise Unobserved(f"{argv[0]} not found") from None
    except subprocess.TimeoutExpired:
        raise Unobserved(f"{argv[0]} timed out after {LSOF_TIMEOUT}s") from None
    except OSError as exc:
        raise Unobserved(f"{argv[0]} could not run: {exc}") from None
    if done.returncode not in (0, 1):
        first = next((line.strip() for line in done.stderr.splitlines() if line.strip()), "")
        raise Unobserved(f"{argv[0]} exited {done.returncode}" + (f": {first[:120]}" if first else ""))
    return done.stdout


def _parse_fields(text: str) -> list[dict]:
    """lsof -F output: a `p<pid>` line opens a process, `c` its command, `u` its uid, `n` each file name."""
    processes: list[dict] = []
    for line in text.splitlines():
        tag, value = line[:1], line[1:]
        if tag == "p" and value.isdigit():
            processes.append({"pid": int(value), "command": "", "uid": None, "names": []})
        elif processes and tag == "c":
            processes[-1]["command"] = value
        elif processes and tag == "u" and value.isdigit():
            processes[-1]["uid"] = int(value)
        elif processes and tag == "n":
            processes[-1]["names"].append(value)
    return processes


def listeners_of(text: str, uid: int) -> list[dict]:
    """The listening processes of user `uid` in `lsof -iTCP -sTCP:LISTEN -Fpcun` output, with their ports (each once)."""
    found = []
    for process in _parse_fields(text):
        if process["uid"] != uid:
            continue
        ports = sorted({int(name.rsplit(":", 1)[1]) for name in process["names"]
                        if name.rsplit(":", 1)[-1].isdigit()})
        found.append({"pid": process["pid"], "command": process["command"], "ports": ports})
    return found


def cwds_of(text: str) -> dict[int, str]:
    """pid -> working directory, from `lsof -a -d cwd -Fpn` output."""
    return {process["pid"]: process["names"][0] for process in _parse_fields(text) if process["names"]}


def argvs_of(text: str) -> dict[int, str]:
    """pid -> command line, from `ps -ww -o pid=,command=` output."""
    found = {}
    for line in text.splitlines():
        pid, _, command = line.strip().partition(" ")
        if pid.isdigit():
            found[int(pid)] = command.strip()
    return found


def observe() -> list[dict]:
    """Every TCP listener of this user: ``{pid, command, ports, cwd, argv}`` (cwd None and argv "" if the process just ended).

    Raises Unobserved when lsof or ps cannot be read; it never returns an empty list for a failure.
    """
    listening = listeners_of(_run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-Fpcun"]), os.getuid())
    if not listening:
        return []
    pids = ",".join(str(item["pid"]) for item in listening)
    cwds = cwds_of(_run(["lsof", "-nP", "-a", "-d", "cwd", "-p", pids, "-Fpn"]))
    argvs = argvs_of(_run(["ps", "-ww", "-o", "pid=,command=", "-p", pids]))
    return [dict(item, cwd=cwds.get(item["pid"]), argv=argvs.get(item["pid"], "")) for item in listening]


def ancestors(parents: dict[int, int], pid: int) -> set[int]:
    """`pid` and every ancestor in a pid -> parent table."""
    chain = {pid}
    while parents.get(pid, 0) > 1 and parents[pid] not in chain:
        pid = parents[pid]
        chain.add(pid)
    return chain


def protected_pids() -> set[int]:
    """This process and everything that started it: a reap can never stop the harness or its launcher."""
    me = os.getpid()
    try:
        rows = [line.split() for line in _run(["ps", "-axo", "pid=,ppid="]).splitlines()]
    except Unobserved:
        return {me, os.getppid()}
    return ancestors({int(a): int(b) for a, b in (row for row in rows if len(row) == 2 and all(x.isdigit() for x in row))}, me)


def _inside(place: str, spellings: set[str]) -> bool:
    return any(place == folder or place.startswith(folder + os.sep) for folder in spellings)


def under(items: list[dict], folder, protected=frozenset()) -> list[dict]:
    """The listeners whose working directory, or a command-line path, lies in `folder` (the folder itself or below it).

    The match is on a path boundary, never a bare prefix: `.../case-1` does not contain `.../case-10`. A working directory
    is a real path, so it is compared with the folder's real path; a command line spells the folder as it was given, so
    its words are compared with both spellings (`--root=<path>` counts as the path). Pid 1 and `protected` are skipped.
    """
    real = os.path.realpath(folder)
    spellings = {real, str(folder)}
    chosen = []
    for item in items:
        if item["pid"] <= 1 or item["pid"] in protected:
            continue
        words = [re.sub(r"^--?[\w-]+=", "", word) for word in (item.get("argv") or "").split()]
        if (item.get("cwd") and _inside(item["cwd"], {real})) or any(_inside(word, spellings) for word in words):
            chosen.append(item)
    return chosen


def _signal(pid: int, number: int) -> None:
    """A pid that has already ended is the goal, not an error; one this user may not signal is left alone."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.kill(pid, number)


def inside(folder) -> list[dict]:
    """The listeners under `folder` right now, never this process or its ancestors. Raises Unobserved."""
    items = observe()
    return under(items, folder, protected_pids()) if items else []


def reap(folder) -> dict:
    """Stop every listener under `folder`: SIGTERM, then SIGKILL for what is still there after GRACE_SECONDS.

    The process table is read again before each signal and each wait, so a pid that ended and was reused is never signalled
    from a stale list. Returns ``{"observed": True, "reaped": [...], "survived": [...]}`` (each entry ``pid, command, ports,
    cwd, argv`` and, for a reaped one, ``ended_by``), or ``{"observed": False, "reason": ...}`` where the table was unreadable.
    """
    try:
        found = inside(folder)
    except Unobserved as exc:
        return {"observed": False, "reason": str(exc)}
    seen = {item["pid"]: item for item in found}
    ended_by: dict[int, str] = {}
    pending = {item["pid"] for item in found}
    for name, number, wait in (("SIGTERM", signal.SIGTERM, GRACE_SECONDS), ("SIGKILL", signal.SIGKILL, FORCE_SECONDS)):
        if not pending:
            break
        for pid in sorted(pending):
            _signal(pid, number)
        end = time.monotonic() + wait
        while True:
            time.sleep(POLL_SECONDS)
            try:
                now = inside(folder)
            except Unobserved as exc:
                return {"observed": False, "reason": f"{exc} (after signalling pids {', '.join(map(str, sorted(pending)))})"}
            for item in now:
                seen.setdefault(item["pid"], item)
            still = {item["pid"] for item in now}
            for pid in pending - still:
                ended_by[pid] = name
            pending = still
            if not pending or time.monotonic() >= end:
                break
    return {"observed": True,
            "reaped": [dict(seen[pid], ended_by=ended_by[pid]) for pid in seen if pid in ended_by],
            "survived": [seen[pid] for pid in seen if pid not in ended_by]}


def _unique(items: list[dict]) -> list[dict]:
    """One entry per pid, the first seen."""
    seen: dict[int, dict] = {}
    for item in items:
        seen.setdefault(item["pid"], item)
    return list(seen.values())


def merge_left_behind(records: list) -> dict | None:
    """One ``left_behind`` record from the passes of a run (and the record an earlier invocation of it kept).

    None when no pass ran (a regrade). ``observed`` is True only if every pass could look; otherwise ``reason`` says why
    next to whatever the passes that did look found, so a pass that could not look never reads as "none". ``reaped`` and
    ``survived`` are present only if at least one pass looked.
    """
    records = [record for record in records if isinstance(record, dict)]
    if not records:
        return None
    merged: dict = {"observed": all(record.get("observed") for record in records)}
    reasons = list(dict.fromkeys(record["reason"] for record in records if record.get("reason")))
    if reasons:
        merged["reason"] = "; ".join(reasons)
    looked = [record for record in records if "reaped" in record]
    if looked:
        reaped = _unique([item for record in looked for item in record["reaped"]])
        merged["reaped"] = reaped
        merged["survived"] = [item for item in _unique([item for record in looked for item in record["survived"]])
                              if item["pid"] not in {r["pid"] for r in reaped}]
    return merged


def left_behind_line(record: dict | None) -> str | None:
    """The one printed line for a run that stopped a listener, could not, or could not look; None when nothing is to be said."""
    if not record:
        return None

    def named(item: dict) -> str:
        ports = ",".join(map(str, item.get("ports") or [])) or "none"
        return f"pid {item['pid']} {item.get('command') or '?'} (port {ports})"

    parts = [f"stopped {named(item)} by {item.get('ended_by')}" for item in record.get("reaped") or []]
    parts += [f"could not stop {named(item)}" for item in record.get("survived") or []]
    if not record.get("observed"):
        parts.append(f"not observed: {record.get('reason')}")
    return "  left      " + "; ".join(parts) if parts else None
