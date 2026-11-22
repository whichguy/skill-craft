#!/usr/bin/env python3
"""Ratchet against ShipLoop: run one arm on one case, each in a new Git repository of its own.

    python3 launch.py checkout ROOT [--commit REF]     a detached checkout of this repository at REF (default origin/main),
                                                       with the comparison's cases that the ShipLoop harness lacks added
    python3 launch.py run ROOT ARM CASE LABEL          ARM (shiploop or ratchet) on CASE, into ROOT/LABEL
    python3 launch.py resume ROOT LABEL                a ShipLoop run whose host was stopped, resumed in place

Both arms run on the same host, model and effort (HOST, MODEL, EFFORT below), and both come from the one checkout that
`checkout` makes, so the ShipLoop source and the Ratchet apparatus are the same commit. Each arm's own tool makes the
run's repository: the E2E harness (`test/shiploop_e2e/run.py --source checkout`) copies the case's starting files into an
empty `work/` and commits them (brownfield.start), and `ratchet.py run` does the same (`work/`, first commit `base`).
Nothing here writes into either repository; it only starts the tool and records what it did.

`checkout` adds a case to the harness's cases.json only where the harness has none of that name, built from the
Ratchet pilot's cases.json: the request word for word as the prompt, the same starting files (a fixture's
docs/shiploop knowledge home removed, as ratchet.py removes it), and the case's own check commands as the harness's
verdict checks, in the harness's pass-count form. The added cases are committed in the detached checkout only. That
checkout's ShipLoop source is the commit given, unchanged: the one added commit touches test/shiploop_e2e alone.

ROOT/LABEL.launch.json records the command, the attempts, start and end times and the exit status. A ShipLoop launch
that the harness refuses because another session's run holds a machine-wide port lease (no output folder is written)
is tried again every RETRY_SECONDS, for up to RETRY_HOURS.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PILOT = "docs/experiments/ratchet-pilot-20261120"
E2E = "test/shiploop_e2e"

HOST, MODEL, EFFORT = "codex", "gpt-6.2-sol", "medium"
ENRICH = "reworded"  # the Ratchet specification text that did best in the pilot (journal section 21)
RETRY_SECONDS, RETRY_HOURS = 60, 6
LEASE_LINES = ("is leased by the harness of", "a listener an ended case left is still bound")
IDENTITY = ["-c", "user.name=comparison launcher", "-c", "user.email=comparison-launcher@example.invalid"]
PASS_CHECK = ("log=$(mktemp); {command} > \"$log\" 2>&1; rc=$?; grep -Eq '^(ℹ|#) pass [1-9]' \"$log\" && [ $rc -eq 0 ]; "
              "r=$?; rm -f \"$log\"; exit $r")
STYLE = {"node-chess-engine": "cli-files", "grokbot-local": "web-service"}


def git(*args, cwd=None, check=True):
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {done.stderr.strip()[-400:]}")
    return done.stdout.strip()


def source_of(root: Path) -> dict:
    record = root / "source.json"
    if not record.exists():
        raise SystemExit(f"{record} is missing: run `launch.py checkout {root}` first")
    return json.loads(record.read_text())


def starting_files(case: dict, checkout: Path) -> Path | None:
    """The folder a Ratchet case starts from, inside `checkout`, or None for a case that starts empty."""
    if case.get("fixture_path"):
        return checkout / PILOT / case["fixture_path"]
    if case.get("fixture"):
        return checkout / E2E / "fixtures" / case["fixture"]
    return None


def checkout(root: Path, ref: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    git("-C", str(REPO), "fetch", "-q", "origin")
    commit = git("-C", str(REPO), "rev-parse", ref)
    target = root / f"source-{commit[:12]}"
    if target.exists():
        raise SystemExit(f"{target} exists already")
    git("-C", str(REPO), "worktree", "add", "-q", "--detach", str(target), commit)
    sys.path.insert(0, str(target / E2E))
    import brownfield  # the harness's own pin of a base: boundary.files_digest over the fixture's files

    cases_path = target / E2E / "cases.json"
    harness_cases = json.loads(cases_path.read_text())
    pilot_cases = json.loads((target / PILOT / "cases.json").read_text())
    added = {}
    for name in COMPARED:
        if name in harness_cases:
            continue
        case = pilot_cases[name]
        entry = {"style": STYLE[name], "prompt": case["request"],
                 "checks": [PASS_CHECK.format(command=command) for command in case["checks"]],
                 "checks_source": f"the comparison of docs/experiments/ratchet-vs-shiploop-20261121: the case's own commands "
                                  f"({', '.join(case['checks'])}) from {PILOT}/cases.json; its held-out checks are run apart"}
        start = starting_files(case, target)
        if start is not None:
            fixture = target / E2E / "fixtures" / f"compare-{name}"
            shutil.copytree(start, fixture, ignore=shutil.ignore_patterns("node_modules", "__pycache__"))
            shutil.rmtree(fixture / "docs" / "shiploop", ignore_errors=True)  # as ratchet.py removes a seeded knowledge home
            if (fixture / "docs").is_dir() and not any((fixture / "docs").iterdir()):
                (fixture / "docs").rmdir()
            entry["base"] = {"fixture": fixture.name, "digest": brownfield.digest(fixture),
                             "source": f"the starting files of {PILOT}/cases.json {name}, the same files ratchet.py starts from"}
        harness_cases[name] = entry
        added[name] = {"base": entry.get("base"), "checks": entry["checks"]}
    cases_path.write_text(json.dumps(harness_cases, indent=2, ensure_ascii=False) + "\n")
    git("-C", str(target), "add", "-A", E2E)
    git("-C", str(target), *IDENTITY, "commit", "-q", "--allow-empty", "-m",
        "comparison cases for docs/experiments/ratchet-vs-shiploop-20261121 (a throwaway checkout; never pushed)")
    version = next((line.split(":", 1)[1].strip() for line in (target / "skills/shiploop/SKILL.md").read_text().splitlines()
                    if line.startswith("version:")), None)
    record = {"commit": commit, "checkout": str(target), "checkout_head": git("-C", str(target), "rev-parse", "HEAD"),
              "shiploop_version": version, "shiploop_last_commit": git("-C", str(target), "log", "-1", "--format=%H", commit, "--",
                                                                         "skills/shiploop"),
              "added_cases": added, "host": HOST, "model": MODEL, "effort": EFFORT, "ratchet_enrich": ENRICH,
              "made": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (root / "source.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))


COMPARED = ("shared-expenses", "node-chess-engine", "ticket-assignment", "grokbot-local")


def command_for(arm: str, case: str, out: Path, source: dict, root: Path) -> list[str]:
    checkout_dir = Path(source["checkout"])
    if arm == "shiploop":
        return [sys.executable, str(checkout_dir / E2E / "run.py"), "--source", "checkout", "--case", case, "--host", HOST,
                "--model", MODEL, "--effort", EFFORT, "--output", str(out), "--baseline", str(root / "baselines.jsonl"), "--quiet"]
    if arm == "ratchet":
        return [sys.executable, str(checkout_dir / PILOT / "ratchet.py"), "run", "--case", case, "--host", HOST, "--model", MODEL,
                "--effort", EFFORT, "--enrich", ENRICH, "--output", str(out), "--quiet"]
    raise SystemExit(f"unknown arm {arm!r}")


def launch(root: Path, argv: list[str], out: Path, label: str, record: dict) -> int:
    log = root / f"{label}.log"
    record.update(argv=argv, attempts=[], log=str(log))
    record_path = root / f"{label}.launch.json"
    deadline = time.time() + RETRY_HOURS * 3600
    while True:
        started = time.time()
        with log.open("a") as handle:
            handle.write(f"[{time.strftime('%H:%M:%S')}] start: {' '.join(argv[:3])} ...\n")
            handle.flush()
            done = subprocess.run(argv, stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, check=False)
        ended = time.time()
        tail = log.read_text(errors="replace")[-3000:]
        refused = (done.returncode != 0 and not (out.exists() and any(out.iterdir()))
                   and any(line in tail for line in LEASE_LINES))
        record["attempts"].append({"started": started, "ended": ended, "returncode": done.returncode, "refused_by_lease": refused})
        record_path.write_text(json.dumps(record, indent=1) + "\n")
        if refused and time.time() < deadline:
            time.sleep(RETRY_SECONDS)
            continue
        return done.returncode


def run(root: Path, arm: str, case: str, label: str) -> int:
    if case not in COMPARED:
        raise SystemExit(f"{case!r} is not a case of this comparison: {', '.join(COMPARED)}")
    source = source_of(root)
    out = root / label
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty; give a new label")
    argv = command_for(arm, case, out, source, root)
    record = {"arm": arm, "case": case, "label": label, "output": str(out), "commit": source["commit"],
              "shiploop_version": source["shiploop_version"], "host": HOST, "model": MODEL, "effort": EFFORT}
    return launch(root, argv, out, label, record)


def resume(root: Path, label: str) -> int:
    record = json.loads((root / f"{label}.launch.json").read_text())
    if record["arm"] != "shiploop":
        raise SystemExit("only a ShipLoop run resumes in place (run.py --resume-run); a stopped Ratchet run is reported as stopped")
    source = source_of(root)
    argv = [sys.executable, str(Path(source["checkout"]) / E2E / "run.py"), "--resume-run", record["output"],
            "--baseline", str(root / "baselines.jsonl"), "--quiet"]
    resumes = record.setdefault("resumes", [])
    started = time.time()
    with (root / f"{label}.log").open("a") as handle:
        handle.write(f"[{time.strftime('%H:%M:%S')}] resume\n")
        handle.flush()
        done = subprocess.run(argv, stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, check=False)
    resumes.append({"started": started, "ended": time.time(), "returncode": done.returncode, "argv": argv})
    (root / f"{label}.launch.json").write_text(json.dumps(record, indent=1) + "\n")
    return done.returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("checkout")
    one.add_argument("root", type=Path)
    one.add_argument("--commit", default="origin/main")
    two = sub.add_parser("run")
    two.add_argument("root", type=Path)
    two.add_argument("arm", choices=("shiploop", "ratchet"))
    two.add_argument("case")
    two.add_argument("label")
    three = sub.add_parser("resume")
    three.add_argument("root", type=Path)
    three.add_argument("label")
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    if args.command == "checkout":
        checkout(root, args.commit)
        return 0
    if args.command == "run":
        return run(root, args.arm, args.case, args.label)
    return resume(root, args.label)


if __name__ == "__main__":
    sys.exit(main())
