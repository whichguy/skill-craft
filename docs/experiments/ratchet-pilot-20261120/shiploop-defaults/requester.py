#!/usr/bin/env python3
"""A stand-in requester for one E2E delivery: it reads the defaults the run printed for the requester and may reply.

DESIGN.md section 3 registers the rule.  The stand-in watches the output folder of one ``test/shiploop_e2e/run.py``
invocation.  It waits for the packet of the stage after the spec (``shiploop_defaults.SHOWN_AT``) to be printed, and
reads from that packet's own text what a requester is shown there: the block "Defaults the spec recorded" and its rows
(the rows a long list spills to its run file are read from that file, which the block names).  It does not read the
run's state for the list: the surface under test is the printed one.

When a row is about the case's point (``about_the_point``), and the stand-in was started with ``--reply``, it sends the
requester's reply (``program/replies.json``) as one owner note, with the CLI the run itself uses.  That is an
observation of ShipLoop's existing owner-note route, which the candidate does not change and no surface of it
promises.  Without ``--reply`` it sends nothing.  Either way it writes what it saw and did beside the output folder, in
``<out>-requester.json``, and ends.

It reads the run's files and writes at most one note.  It never reads or writes the session's work folder, and nothing
it holds (the reply, the rule) is in a folder a session can see.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(ROOT / "test/shiploop_e2e"))

import run_choice
import shiploop_defaults as defaults
import shiploop_navigator as navigator
import shiploop_trace

SUFFIX = "-requester.json"
POLL_SECONDS = 2.0
WRITTEN = re.compile(r"^Owner note (N\d+) written", re.MULTILINE)
HEAD = "Defaults the spec recorded:"
ROW = re.compile(r"^\d+\. R-\d+ .+$")
SPILL = re.compile(r"\(\d+ more lines? not printed here: RUN/(\S+) holds all \d+ whole\)")
# The rule of DESIGN.md section 3: a row is about the point when it names the tickets that are already there (TICKETS),
# or names starting the service together with a due time that is absent (START and ABSENT).  A reader scores the same
# rows afterwards against the rubric of that section; this rule only decides, during the run, whether to reply.
TICKETS = re.compile(r"\b(backfill\w*|back-fill\w*|migrat\w*|existing|already|older)\b", re.IGNORECASE)
START = re.compile(r"\b(start\w*|start-up|boot\w*|launch\w*|restart\w*)\b", re.IGNORECASE)
ABSENT = re.compile(r"\b(missing|without|lack\w*|no due|has none|have none|has no|have no)\b", re.IGNORECASE)
CASES = ("ticket-due-times",)


def about_the_point(case: str, row: str) -> bool:
    assert case in CASES, case
    return bool(TICKETS.search(row) or (START.search(row) and ABSENT.search(row)))


def reply_for(case: str) -> str:
    return json.loads((HERE.parent / "program" / "replies.json").read_text(encoding="utf-8"))[case]["reply"]


def run_cli(out: Path) -> Path | None:
    found = sorted(out.glob("build/**/skills/shiploop/scripts/shiploop"))
    return found[0] if found else None


def shown_rows(run_dir: Path, packet: str) -> tuple[bool, list[str]]:
    """(the block is in the packet, its rows): the rows printed, or every row from the file a cut block names."""
    lines = packet.splitlines()
    start = next((index for index, line in enumerate(lines) if line.startswith(HEAD)), None)
    if start is None:
        return False, []
    rows = []
    for line in lines[start + 1:]:
        spilled = SPILL.search(line)
        if spilled:
            whole = run_dir / spilled.group(1)
            return True, [row for row in whole.read_text(encoding="utf-8").splitlines() if ROW.match(row)]
        if not ROW.match(line):
            break
        rows.append(line)
    return True, rows


def printed_packet(run_dir: Path) -> tuple[dict, str] | None:
    """(state, packet text) once the stage after the spec is current and its packet has been printed; else None."""
    state = shiploop_trace.current_state(run_dir)
    if not state or state.get("status") != "active" or state.get("active_improve"):
        return None
    stage, action, _item = shiploop_trace._cursor(state)
    action_id = (action or {}).get("id")
    if stage != defaults.SHOWN_AT or not action_id:
        return None
    path = run_dir / navigator.PACKET_DIR / (action_id + ".md")
    return (state, path.read_text(encoding="utf-8")) if path.is_file() else None


def past_the_stage(run_dir: Path) -> bool:
    """Whether the run has an accepted result of the stage after the spec: the packet can no longer be awaited."""
    state = shiploop_trace.current_state(run_dir)
    return bool(state) and any(row.get("stage") == defaults.SHOWN_AT and row.get("outcome") == "done"
                               for row in state.get("history") or ())


def watch(out: Path, case: str, deadline: float, reply: bool) -> dict:
    record: dict = {"case": case, "reply_enabled": reply,
                    "rule": {"tickets": TICKETS.pattern, "start": START.pattern, "absent": ABSENT.pattern}}
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        if not out.is_dir():
            continue
        try:
            chosen = run_choice.choose(out).chosen
            run_dir = Path(chosen["run_dir"]) if chosen else None
            found = printed_packet(run_dir) if run_dir else None
            if found:
                state, packet = found
                block, rows = shown_rows(run_dir, packet)
                record.update(run_dir=str(run_dir), seen_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                              block_printed=block, rows=rows, recorded=defaults.recorded(state),
                              about=[about_the_point(case, row) for row in rows])
                record["note"] = None
                if reply and any(record["about"]):
                    text = reply_for(case)
                    done = subprocess.run([sys.executable, str(run_cli(out)), "note", "--run-dir", str(run_dir),
                                           "--text", text], capture_output=True, text=True, timeout=120, check=False)
                    hit = WRITTEN.search(done.stdout)
                    record["note"] = {"exit": done.returncode, "id": hit.group(1) if hit else None, "text": text,
                                      "output": (done.stdout + done.stderr).strip()[:1500]}
                return record
            if run_dir and past_the_stage(run_dir):
                record["ended"] = "the stage after the spec was accepted before its packet was read"
                return record
        except Exception as exc:  # noqa: BLE001 - a folder still being made, a state file read mid-write
            record["last_error"] = f"{type(exc).__name__}: {exc}"[:300]
        if (out / "result.json").exists():
            record["ended"] = "the delivery ended before the stage after the spec printed its packet"
            return record
    record["ended"] = "deadline"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="the output folder of the delivery's run.py invocation")
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--reply", action="store_true",
                        help="send the requester's reply as an owner note when a row is about the point")
    parser.add_argument("--hours", type=float, default=3.0, help="give up after this long")
    args = parser.parse_args()
    record = watch(args.out, args.case, time.time() + args.hours * 3600, args.reply)
    args.out.with_name(args.out.name + SUFFIX).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: record.get(key) for key in ("block_printed", "about", "note", "ended")})[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
