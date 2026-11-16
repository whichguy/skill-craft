#!/usr/bin/env python3
"""A stand-in for `iterate.py --qualify --iterations 1`, for the facade's hermetic tests (test/shiploop-e2e-adapter-steps.test.py).

It keeps the observable contract of the real loop (read from the harness and checked against a real run by the real-engine test): a new
worktree and branch from the checkout's HEAD, LOOP.md in the output folder, learning rows committed on the loop branch, run folders with
result.json, review.json and a judge verdict, one baseline row per run (the exploration's into the checkout's tracked baselines file, an
epoch attempt's into the epoch's own file), a cycle's cycle-result.json and epoch events, a kept candidate ref when a candidate is not
promoted, and the stop line. It decides between exploring and a cycle with the harness's own `learning_records.select`.

Behaviour per case comes from the JSON file named by $FAKE_ENGINE, `{"<case>" or "*": {...}}`:
  kind      "quiet" (default: an exploration that finds nothing) | "discover" (it opens a material record; with "admit" true it also admits
            it, so a cycle follows) | "cycle" is not a kind: a cycle runs when `select` offers a record for the case
  record    the record id a discovery opens (default: a new one)
  decision  a cycle's decision: PROMOTE | DROP (default) | UNDECIDED | NO_CANDIDATE | UNKNOWN_LAUNCH
  oracle    "fail": the runs miss the accuracy floor
  fault     "crash": exit 3 right after the worktree exists | "hang": stage a ledger row, then sleep for an hour
  sleep     seconds to wait before doing anything (a step that stays running)
  stray     leave an untracked file in the evaluator checkout
  review_invalid  the exploration's review is not discovery-qualified (and no judge runs)
  attribution     false: the run's card says it cannot be attributed to the build under test
  escape    "ledger": leave a harmless process in a session of its own, recorded in the run's resources.jsonl, as a model host is |
            "tree": the same without the record (only a process snapshot of the engine's children finds it)
  stop      the stop line to write instead of the ordinary one
The arguments of every call are appended to $FAKE_LOG when it is set.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import learning_records as lr  # noqa: E402
import lifecycle  # noqa: E402

CONFIG = ["-c", "user.name=Fake", "-c", "user.email=fake@example.invalid", "-c", "commit.gpgsign=false"]
LEDGER = "test/shiploop_e2e/learning-records.jsonl"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *CONFIG, *args], check=True, capture_output=True, text=True).stdout.strip()


def card(oracle, attribution=True):
    return {"floors": {"accuracy": "fail" if oracle == "fail" else "pass", "enterprise": "not_applicable", "fidelity": "pass"},
            "validity": {"correctness": {"valid": True, "why": []},
                         "attribution": {"valid": attribution, "why": [] if attribution else ["the build under test was not what ran"]},
                         "timing": {"valid": True, "why": []}}}


def run_folder(folder: Path, case: str, args, baselines: Path, oracle, attribution=True) -> Path:
    """One run folder as the harness leaves it (the keys the facade reads) and its row in a baseline file."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "invocation.json").write_text("{}\n")
    (folder / "resources.jsonl").write_text("")
    (folder / "result.json").write_text(json.dumps({
        "case": case, "host": args.host, "model": args.model, "effort": args.effort, "source": "checkout", "prompt_sha256": "p1",
        "invoked": {"pass": True, "skill": "skill-craft:shiploop"}, "plugin": {"pass": True}}))
    (folder / "card.json").write_text(json.dumps(card(oracle, attribution)))
    row = {"date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "case": case, "style": None, "host": args.host, "model": args.model,
           "effort": args.effort, "source": "checkout", "planning_review": "stage", "prompt_sha256": "p1", "pass": True,
           "output": str(folder), "termination": {"engine_status": "done"}, "verdicts": {"shiploop": True}}
    with baselines.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    return folder


def review_folders(run: Path, qualified=True) -> None:
    """The review and the judge's verdict; a review that is not discovery-qualified ends the exploration before the judge, as in the loop."""
    status = {"status": "valid" if qualified else "invalid", "reason": None if qualified else "the reviewer returned no usable document"}
    (run / "review.json").write_text(json.dumps({"validity": {**status, "discovery_qualified": qualified}}))
    if qualified:
        (run / "review-judge").mkdir(exist_ok=True)
        (run / "review-judge" / "verdict.json").write_text(json.dumps({"validity": {"status": "valid", "reason": None}}))


def leave_a_child(run: Path, how: str) -> None:
    """A harmless process in a session of its own: where a model host's server would be, a hung one."""
    starter = ("import subprocess,sys;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(300)'],start_new_session=True,"
               "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print(p.pid)")
    if how == "ledger":  # started by a starter that exits, so its parent is init and only the ledger can name it
        pid = int(subprocess.run([sys.executable, "-c", starter], capture_output=True, text=True, check=True).stdout.strip())
        lifecycle.own(run, pid, "host")
    else:  # a direct child of this process: a snapshot of the engine's descendants finds it
        subprocess.Popen([sys.executable, "-c", "import time;time.sleep(300)"], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def commit_learnings(worktree: Path, out: Path, text: str, subject: str) -> str:
    with (worktree / "test" / "shiploop_e2e" / "LEARNINGS.md").open("a") as handle:
        handle.write("\n" + text + "\n")
    git(worktree, "add", "test/shiploop_e2e/LEARNINGS.md", LEDGER)
    (out / "learnings-commit.txt").write_text(subject + "\n")
    git(worktree, "commit", "-q", "-F", str(out / "learnings-commit.txt"))
    return git(worktree, "rev-parse", "HEAD")


def main() -> int:
    parser = argparse.ArgumentParser()
    for flag in ("--case", "--iterations", "--host", "--model", "--effort", "--tolerance", "--attempts", "--parallel", "--output",
                 "--generality-case", "--calibration"):
        parser.add_argument(flag)
    parser.add_argument("--qualify", action="store_true")
    args, _extra = parser.parse_known_args()
    if os.environ.get("FAKE_LOG"):
        with open(os.environ["FAKE_LOG"], "a") as handle:
            handle.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "pid": os.getpid()}) + "\n")
    if not args.qualify or args.iterations != "1" or not (args.calibration or (args.tolerance and args.attempts)):
        raise SystemExit("--qualify --iterations 1 and a calibration or a stated tolerance and attempts are required, as in the real loop")
    knobs = json.loads(Path(os.environ["FAKE_ENGINE"]).read_text())
    knob = knobs.get(args.case) or knobs.get("*") or {}
    out = Path(args.output).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit(f"output must be outside the checkout: {out}")
    out.mkdir(parents=True, exist_ok=False)
    name = f"shiploop-loop-{secrets.token_hex(3)}"
    branch = f"auto/{name}"
    worktree = ROOT / ".claude" / "worktrees" / name
    git(ROOT, "worktree", "add", "-q", str(worktree), "-b", branch, "HEAD")
    journal = out / "LOOP.md"
    journal.write_text(f"# Qualified loop: {args.case}\n\n- worktree {worktree}, branch {branch}\n- basis: stated, not measured\n\n")
    if knob.get("sleep"):
        time.sleep(float(knob["sleep"]))
    ledger = worktree / LEDGER
    if knob.get("stray"):
        (ROOT / "stray.txt").write_text("a file the engine left in the evaluator checkout\n")
    if knob.get("fault") == "crash":
        raise SystemExit(3)
    if knob.get("fault") == "hang":
        if knob.get("escape"):
            run = run_folder(out / "explore-1" / "run", args.case, args, ROOT / "test" / "shiploop_e2e" / "baselines.jsonl", None)
            leave_a_child(run, knob["escape"])
        lr.append("opened", "LR-20261115-feed01", ledger, title="found before the kill", materiality="material", confidence="high",
                  target="shiploop", source={"run": str(out), "case": args.case, "exposure": "development"})
        git(worktree, "add", LEDGER)  # staged, not committed: what a SIGKILL leaves; the last thing done, so a test can wait for it
        time.sleep(3600)
        return 0
    stop = knob.get("stop") or f"reached --iterations {args.iterations}"
    record = lr.select(ledger, args.case, args.generality_case)
    if record is None:
        explore = out / "explore-1"
        run = run_folder(explore / "run", args.case, args, ROOT / "test" / "shiploop_e2e" / "baselines.jsonl", knob.get("oracle"),
                         knob.get("attribution", True))
        review_folders(run, not knob.get("review_invalid"))
        if knob.get("escape"):
            leave_a_child(run, knob["escape"])
        opened = []
        if knob.get("kind") == "discover":
            found = knob.get("record") or f"LR-20261115-{secrets.token_hex(3)}"
            lr.append("opened", found, ledger, title="a finding", materiality="material", confidence="high", target="shiploop",
                      source={"run": str(run), "case": args.case, "exposure": "development"})
            opened.append(found)
            if knob.get("admit"):
                lr.append("admitted", found, ledger, reason="supported")
        commit_learnings(worktree, explore, f"## Exploration of {args.case}\n\nopened {opened or 'nothing'}",
                         f"test(shiploop): record E2E iteration 0 learnings ({args.case})")
        journal.open("a").write(f"## Exploration 1\n\n- records opened: {', '.join(opened) or 'none'}\n\n")
        record = lr.select(ledger, args.case, args.generality_case)
        if record is None:
            stop = knob.get("stop") or "no admitted learning record after exploring"
    if record is not None:
        cycle = out / "cycle-1"
        decision = knob.get("decision", "DROP")
        tip = git(worktree, "rev-parse", "HEAD")
        skill = worktree / "skills" / "shiploop" / "SKILL.md"
        skill.write_text(skill.read_text() + f"<!-- candidate for {record} -->\n")
        git(worktree, "add", "skills/shiploop/SKILL.md")
        git(worktree, "commit", "-q", "-m", f"candidate for {record}\n\nLearning-Record: {record}\n")
        candidate = git(worktree, "rev-parse", "HEAD")
        epoch = cycle / "epoch"
        (epoch / "receipts").mkdir(parents=True)
        events, attempts = [{"sequence": 1, "kind": "registered"}], []
        cases = [args.case] + ([args.generality_case] if args.generality_case else [])
        for arm in ("control", "candidate"):
            for case in cases:
                identifier = f"{arm}-{case}-1"
                run_folder(epoch / "runs" / identifier, case, args, epoch / "baselines.jsonl", knob.get("oracle"))
                attempts.append({"id": identifier, "arm": arm, "case": case, "outcome": "failure" if knob.get("oracle") == "fail" else "success",
                                 "evidence_valid": True})
        for attempt in attempts:
            receipt = f"receipts/{attempt['id']}-epoch-1.json"
            (epoch / receipt).write_text(json.dumps({"review": {"validity": {"status": "valid"}}, "judge": {"validity": {"status": "valid"}},
                                                     "routes": {}}))
            events.append({"kind": "reviewed", "attempt_id": attempt["id"], "receipt": receipt})
        events.append({"kind": "decision", "result": {"decision": decision, "attempts": attempts}})
        (epoch / "events.jsonl").write_text("".join(json.dumps(event) + "\n" for event in events))
        promoted = decision == "PROMOTE"
        if not promoted:
            git(worktree, "update-ref", f"refs/shiploop-loop/{name}/{record}", candidate)
            git(worktree, "reset", "-q", "--hard", tip)
        lr.append("predicted", record, ledger, prediction={"anchor": "S-14"}, candidate=candidate)
        lr.append("decided", record, ledger, decision=decision, epoch=str(epoch))
        if promoted:
            lr.append("verdict", record, ledger, verdict="supported", outcome="verified", reason="the epoch promoted it")
        elif decision == "DROP":
            lr.append("verdict", record, ledger, verdict="contradicted", outcome="refuted", reason="the epoch dropped it")
        sha = commit_learnings(worktree, cycle, f"## Cycle on {record}: {decision}", f"test(e2e): qualified cycle for {record}: {decision}")
        summary = {side: {"attempts": 1, "successes": 0 if knob.get("oracle") == "fail" else 1} for side in ("control", "candidate")}
        (cycle / "cycle-result.json").write_text(json.dumps({
            "contract": "shiploop-cycle/1", "decision": decision, "reasons": ["fake"], "cases": {case: {"role": "regression", **summary} for case in cases},
            "control_build": "c", "candidate_build": "d", "tip_note": "fake", "learnings_commit": sha}))
        journal.open("a").write(f"## Cycle 1: {record}\n\n- decision: {decision}\n- reasons: fake\n- fake tip note\n\n")
    journal.open("a").write(f"## Result\n\n- stopped: {stop}\n- branch {branch}: review it\n\n")
    print(f"cycle: {stop}\n  journal: {journal}\n  branch:  {branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
