#!/usr/bin/env python3
"""E-EFF2 rung S0: seven control slices and one treatment smoke slice, two at a time, on Grok 4.7 (plan section 1).

    python3 -B s0_queue.py [--dry-run]

The harness and the plugin come from the pinned worktree R2 uses (31933a73, plugin payload 2.9.0); before every launch the R2
launch guard (`freeze_manifest.py --check`: harness hashes, payload digest, worktree HEAD, schedules) must pass, and no other
session's Grok harness process may be running for three polls in a row. A slice that ends without slice-result.json is logged
INCOMPLETE and not retried (a finished slice is final; rerun it into a new folder by hand). Output: OUT/s0-<case>-<arm>/,
events in s0-queue-events.log next to this file. Environments are never read or printed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent / "shiploop-effort-by-stage-20261024"
WORKTREE = Path("/Users/dadleet/src/skill-craft/.claude/worktrees/eeff1-r2-ac0ac8")
PLUGIN = WORKTREE / "plugins" / "skill-craft"
OUT = Path("/Users/dadleet/e2e-runs/effort-eeff2")
EVENTS = HERE / "s0-queue-events.log"
CASES = ["node-add-function", "node-fix-bug", "node-add-route", "node-rename",
         "node-seeded-case-compare", "node-seeded-numeric-sort", "node-seeded-empty-guard"]
JOBS = [(case, "control") for case in CASES] + [("node-add-function", "treatment")]
WIDTH = 2
POLLS, POLL_SECONDS = 3, 120
TIMEOUT = 5400


def say(text: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + text
    print(line, flush=True)
    with EVENTS.open("a") as handle:
        handle.write(line + "\n")


def guard() -> str:
    for attempt in range(4):
        done = subprocess.run([sys.executable, "-B", str(EXP / "freeze_manifest.py"), "--check"], capture_output=True, text=True)
        if done.returncode == 0:
            return ""
        text = " | ".join((done.stdout + done.stderr).split("\n"))[:300]
        if attempt < 3:
            time.sleep(20)
    return text


def foreign(mine: set[int]) -> list[str]:
    found = []
    pids = subprocess.run(["pgrep", "-f", r"shiploop_e2e/(run|slice)\.py|experiment\.py"], capture_output=True, text=True).stdout.split()
    for pid in pids:
        if int(pid) in mine or int(pid) == os.getpid():
            continue
        line = subprocess.run(["ps", "-p", pid, "-o", "etime=,args="], capture_output=True, text=True).stdout.strip()
        match = re.match(r"(\S+)\s+(\S*[Pp]ython\S*)\s+(.*)", line)
        if not match:
            continue  # a shell wrapper: its arguments can carry environment text
        host = re.search(r"--host (\w+)", match.group(3))
        if "experiment.py" in match.group(3) or (host and host.group(1) == "grok"):
            found.append(f"pid {pid} {match.group(1)}")
    return found


def argv(case: str, arm: str) -> list[str]:
    return [sys.executable, "-B", str(WORKTREE / "test/shiploop_e2e/slice.py"), "--case", case, "--host", "grok", "--model", "grok-4.7",
            "--effort-schedule", str(EXP / f"{arm}.json"), "--output", str(OUT / f"s0-{case}-{arm}"), "--timeout", str(TIMEOUT),
            "--plugin-dir", str(PLUGIN), "--quiet"]


def facts(folder: Path) -> str:
    try:
        result = json.loads((folder / "slice-result.json").read_text())
    except (OSError, ValueError):
        return "INCOMPLETE: no slice-result.json"
    effort = {}
    try:
        effort = json.loads((folder / "effort.json").read_text())
    except (OSError, ValueError):
        pass
    return f"pass={result.get('pass')} restarts={len(effort.get('restarts', []))} launches={len(effort.get('launches', []))}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        say("dry run: guard=" + (guard() or "OK"))
        for case, arm in JOBS:
            print(" ".join(argv(case, arm)))
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    pending = [job for job in JOBS if not (OUT / f"s0-{job[0]}-{job[1]}" / "slice-result.json").exists()]
    say(f"S0 queue: {len(pending)} of {len(JOBS)} slices to run, {WIDTH} at a time")
    running: dict[tuple[str, str], subprocess.Popen] = {}
    quiet = 0
    while pending or running:
        for job, child in list(running.items()):
            if child.poll() is not None:
                say(f"{job[0]} {job[1]}: finished exit={child.returncode} " + facts(OUT / f"s0-{job[0]}-{job[1]}"))
                del running[job]
        if pending and len(running) < WIDTH:
            others = foreign({c.pid for c in running.values()})
            quiet = quiet + 1 if not others else 0
            if others:
                say("waiting for Grok: " + "; ".join(others[:3]))
            if quiet >= POLLS or (running and quiet >= 1 and not others):
                reason = guard()
                if reason:
                    say("GUARD FAILED: " + reason)
                    return 1
                case, arm = pending.pop(0)
                folder = OUT / f"s0-{case}-{arm}"
                if folder.exists():
                    say(f"{case} {arm}: output folder exists without a result; not launching over it")
                    continue
                running[(case, arm)] = subprocess.Popen(argv(case, arm), cwd=WORKTREE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                say(f"{case} {arm}: launched (pid {running[(case, arm)].pid})")
        time.sleep(POLL_SECONDS if not running else 30)
    say("S0 queue: all slices ended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
