#!/usr/bin/env python3
"""An observation, never a verdict: what happens to due times when operators go back to release 1.4.0 and return.

The `ticket-due-times` request says a due time is set once and that operators can go back to 1.4.0 on the data file the
new release wrote. It does not say what happens when they come forward again. 1.4.0 drops the field it does not know when
it saves, so the answer is a design choice, and this script records it. It changes no check and no verdict.

What it does, with the case's own fixture, data file and server handling (checks/due_times_probe.py):
1. starts the delivery with DUE_TIMES=on over a version-1 file of eight tickets and reads every due time;
2. keeps a copy of the file, then starts 1.4.0 on it, makes T-0001 low instead of urgent and creates a ticket;
3. returns to the delivery the ordinary way and reads the due times again;
4. when the delivery offers a backfill command that takes `--restore-from`, returns once more from the same 1.4.0 file
   with the kept copy, and reads them a third time.
A delivery that will not start until its tickets hold due times is given its own backfill command first: a script that
package.json adds whose name holds "backfill" or "migrat".

For each return it reports whether the delivery starts, how many of the eight due times are the same, and whether what
1.4.0 wrote is still there (T-0001 low, the ticket it created present with a due time).

Usage: python3 ticket_return.py DELIVERED_TREE       prints one JSON object
Exit 0 whatever the delivery does; 2 for a usage error; 3 when the observation could not be made (the reason is printed).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "checks"))
import due_times_probe as probe  # noqa: E402  (the fixture, the data file and the server lifecycle: one implementation)

VERSION = 1
CHANGED = "T-0001"   # urgent and open in the fixture: its due time is its creation time plus 4 hours


def start(tree: Path, data: Path, scratch: Path, label: str, **env: str):
    """The delivery or 1.4.0 over `data`, or None and the end of its error output when it does not start."""
    quiet = io.StringIO()
    try:
        with contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            return probe.started(tree, data, scratch, label, **env), ""
    except SystemExit:
        log = scratch / f"{label}.stderr"
        text = log.read_text(errors="replace") if log.is_file() else quiet.getvalue()
        return None, " ".join(text.split())[-300:]


def backfill_scripts(tree: Path) -> list[tuple[str, str]]:
    """(name, command) of each script package.json adds to 1.4.0's whose name says it fills or migrates the data."""
    try:
        new = json.loads((tree / "package.json").read_text()).get("scripts") or {}
        old = json.loads((probe.BASE / "package.json").read_text()).get("scripts") or {}
    except (OSError, ValueError):
        return []
    return [(name, str(command)) for name, command in new.items()
            if name not in old and ("backfill" in name or "migrat" in name)]


def run_script(tree: Path, command: str, data: Path, extra: list[str]) -> str:
    env = {key: value for key, value in os.environ.items() if key not in probe.SCRUB}
    env["DATA_FILE"] = str(data)
    line = command + "".join(" " + shlex.quote(word) for word in extra)
    try:
        done = subprocess.run(["/bin/sh", "-c", line], cwd=tree, env=env, capture_output=True, text=True, timeout=60,
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "no end within 60 s"
    return f"exit {done.returncode}"


def takes_restore(tree: Path, command: str) -> bool:
    for word in shlex.split(command):
        path = tree / word
        if path.is_file() and "--restore-from" in path.read_text(errors="replace"):
            return True
    return False


def due_times(server) -> dict[str, str | None] | None:
    quiet = io.StringIO()
    with contextlib.redirect_stdout(quiet):
        items = server.listing()
    if items is None:
        return None
    return {str(item.get("id")): item.get("due") for item in items if isinstance(item, dict)}


def come_back(tree: Path, data: Path, scratch: Path, label: str, before: dict, made: str | None,
              prepare: tuple[str, list[str]] | None) -> dict:
    """Start the delivery again over the file 1.4.0 left (after `prepare`, a backfill command, when given)."""
    out: dict = {"prepared_by": None}
    if prepare is not None:
        out["prepared_by"] = prepare[0] + "".join(" " + word for word in prepare[1][:1])
        out["prepare_result"] = run_script(tree, prepare[0], data, prepare[1])
    server, why = start(tree, data, scratch, label, DUE_TIMES="on")
    if server is None:
        return {**out, "starts": False, "why": why}
    try:
        after = due_times(server)
        status, changed = server.call("GET", "/tickets/" + CHANGED)
    finally:
        with contextlib.redirect_stdout(io.StringIO()):
            server.stop()
    if after is None:
        return {**out, "starts": True, "listing": "not readable"}
    same = [ticket for ticket, due in before.items()
            if due and after.get(ticket) and probe.parse_time(after[ticket]) == probe.parse_time(due)]
    moved = sorted(ticket for ticket in before if ticket not in same)
    body = changed.get("ticket", changed) if isinstance(changed, dict) else {}
    return {**out, "starts": True, "due_same": len(same), "due_of": len(before), "moved": moved,
            "old_release_priority_kept": status == 200 and body.get("priority") == "low",
            "old_release_ticket_kept": bool(made) and made in after,
            "old_release_ticket_has_due": bool(made) and bool(after.get(made))}


def observe(tree: Path, scratch: Path) -> dict:
    out: dict = {"schema": "shiploop-e2e-observation/v1", "observer": "ticket-return", "version": VERSION}
    data = scratch / "tickets.json"
    probe.write(data, probe.base_document(dt.datetime.now(dt.timezone.utc)))
    scripts = backfill_scripts(tree)
    out["backfill_commands"] = [name for name, _command in scripts]
    server, why = start(tree, data, scratch, "delivery-first", DUE_TIMES="on")
    out["first_start"] = "by itself"
    if server is None and scripts:
        out["first_start"] = "after " + scripts[0][0] + " (" + run_script(tree, scripts[0][1], data, []) + ")"
        server, why = start(tree, data, scratch, "delivery-first-again", DUE_TIMES="on")
    if server is None:
        return {**out, "first_start": "does not start", "why": why, "summary": "not measured: the delivery does not start"}
    try:
        before = due_times(server)
    finally:
        with contextlib.redirect_stdout(io.StringIO()):
            server.stop()
    if not before or not all(before.values()):
        return {**out, "summary": "not measured: the delivery does not show a due time for every ticket", "seen": before}
    kept_copy = scratch / "kept-before-going-back.json"
    shutil.copyfile(data, kept_copy)

    old, why = start(probe.BASE, data, scratch, "release-1.4.0")
    if old is None:
        return {**out, "old_release_starts": False, "why": why, "summary": "not measured: 1.4.0 does not start on the file"}
    try:
        patched, _body = old.call("PATCH", "/tickets/" + CHANGED, {"priority": "low"})
        with contextlib.redirect_stdout(io.StringIO()):
            ticket = probe.make_ticket(old, "1.4.0", "normal")
    finally:
        with contextlib.redirect_stdout(io.StringIO()):
            old.stop()
    made = ticket.get("id") if isinstance(ticket, dict) else None
    out["old_release"] = {"starts": True, "priority_change": patched, "created": made,
                          "file_still_holds_due": '"due"' in data.read_text(errors="replace")}
    left = scratch / "left-by-1.4.0.json"
    shutil.copyfile(data, left)

    ordinary = come_back(tree, data, scratch, "delivery-return", before, made, None)
    if not ordinary.get("starts") and scripts:
        shutil.copyfile(left, data)
        ordinary = come_back(tree, data, scratch, "delivery-return-filled", before, made, (scripts[0][1], []))
    out["ordinary_return"] = ordinary
    assisted = None
    restoring = [(name, command) for name, command in scripts if takes_restore(tree, command)]
    if restoring:
        shutil.copyfile(left, data)
        assisted = come_back(tree, data, scratch, "delivery-return-restored", before, made,
                             (restoring[0][1], ["--restore-from", str(kept_copy)]))
    out["assisted_return"] = assisted

    def good(result: dict | None) -> bool:
        return bool(result and result.get("starts") and result.get("due_same") == result.get("due_of")
                    and result.get("old_release_priority_kept") and result.get("old_release_ticket_kept"))
    if good(ordinary):
        out["summary"] = "keeps every due time by itself"
    elif good(assisted):
        out["summary"] = "keeps every due time with its restore option"
    elif assisted and assisted.get("starts") and assisted.get("due_same") == assisted.get("due_of"):
        out["summary"] = "its restore option keeps the due times and loses what 1.4.0 wrote"
    elif ordinary.get("starts"):
        out["summary"] = "moves " + str(len(ordinary.get("moved") or [])) + " of " + str(ordinary.get("due_of")) + " due times"
    else:
        out["summary"] = "does not start again on the file 1.4.0 left"
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not (Path(argv[0]) / "src" / "server.js").is_file():
        print("usage: ticket_return.py DELIVERED_TREE (a folder holding src/server.js)", file=sys.stderr)
        return 2
    tree = Path(argv[0]).resolve()
    scratch = Path(tempfile.mkdtemp(prefix="ticket-return-"))
    begun = time.monotonic()
    try:
        result = observe(tree, scratch)
    except Exception as error:  # an observation that cannot be made is reported, never raised as a product failure
        print(json.dumps({"schema": "shiploop-e2e-observation/v1", "observer": "ticket-return", "version": VERSION,
                          "summary": "not measured: " + type(error).__name__ + ": " + str(error)[:300]}))
        return 3
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    result["seconds"] = round(time.monotonic() - begun, 1)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
