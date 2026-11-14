#!/usr/bin/env python3
"""dagkit: the ledger and the synthetic work unit of the parallel-plan-execution probes.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (see its README); it is not ShipLoop code and no
skill uses it. Every arm calls it through the host's own shell tool, so each command is a visible host tool call. The
ledger (``RUN/ledger.jsonl``, one JSON object per line) is the ground truth for when each step ran.

  dagkit.py init     --plan PLAN.json --run RUN
  dagkit.py ready    --run RUN [--claim]      one JSON line: ready, claimed, running, done, failed, blocked, waiting, complete
  dagkit.py run      --run RUN --step ID      refuses (exit 3) a premature or repeated start; else works, then logs end
  dagkit.py verify   --run RUN                VERIFY OK | PARTIAL | FAIL, from the ledger and the hash chain
  dagkit.py timeline --run RUN                the ledger in order, with seconds from the first event

A step's work is a sleep of the step's declared seconds, then an output file whose hash chains the hashes of the
steps it depends on, so a step that ran on a missing or stale input cannot produce a valid chain. ``PPE_TIME_SCALE``
(tests only) scales the sleeps and is written into every start event, so a scaled trial is never mistaken for a
live one. Exit codes: 0 done, 1 a step failed (an injected fault) or verify failed, 2 verify partial, 3 refused.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

SCALE = float(os.environ.get("PPE_TIME_SCALE", "1"))
SCHEMA = "ppe-ledger/v1"


def _at(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + f".{int((ts % 1) * 1000):03d}Z"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Run:
    """One run directory: plan.json, meta.json, ledger.jsonl, ledger.lock and out/."""

    def __init__(self, path):
        self.dir = Path(path)
        self.ledger = self.dir / "ledger.jsonl"
        self.lock = self.dir / "ledger.lock"

    def plan(self) -> dict:
        return json.loads((self.dir / "plan.json").read_text())

    def meta(self) -> dict:
        return json.loads((self.dir / "meta.json").read_text())

    def events(self) -> list[dict]:
        if not self.ledger.is_file():
            return []
        return [json.loads(line) for line in self.ledger.read_text().splitlines() if line.strip()]

    @contextlib.contextmanager
    def locked(self):
        with open(self.lock, "a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def append(self, kind: str, step: str | None = None, **detail) -> dict:
        """Append one event; call only while holding ``locked()`` so ``seq`` is a total order."""
        ts = time.time()
        event = {"seq": len(self.events()) + 1, "ts": round(ts, 3), "at": _at(ts), "kind": kind, "step": step,
                 "pid": os.getpid(), "ppid": os.getppid(), "detail": detail}
        with open(self.ledger, "a") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event


def out_hash(plan_sha: str, step: str, inputs: dict) -> str:
    return _sha(f"{plan_sha}|{step}|{json.dumps(inputs, sort_keys=True)}")


def derive(plan: dict, events: list[dict]) -> dict:
    """The state of every step from the ledger alone."""
    state = {s["id"]: {"state": "pending", "claimed": False, "starts": 0, "start": None, "end": None,
                       "start_seq": None, "end_seq": None, "sha": None} for s in plan["steps"]}
    for event in events:
        step = event.get("step")
        if step not in state:
            continue
        item, kind = state[step], event["kind"]
        if kind == "claim":
            item["claimed"] = True
        elif kind == "start":
            item["starts"] += 1
            if item["start"] is None:
                item["start"], item["start_seq"] = event["ts"], event["seq"]
            if item["state"] == "pending":
                item["state"] = "running"
        elif kind == "end":
            item.update(state="done", end=event["ts"], end_seq=event["seq"], sha=event["detail"].get("sha"))
        elif kind == "fail":
            item.update(state="failed", end=event["ts"], end_seq=event["seq"])
    for s in plan["steps"]:  # deps name earlier steps only, so one pass settles the blocked ones
        if state[s["id"]]["state"] == "pending" and any(state[d]["state"] in ("failed", "blocked") for d in s["deps"]):
            state[s["id"]]["state"] = "blocked"
    return state


def classify(plan: dict, state: dict) -> dict:
    groups = {name: [] for name in ("ready", "claimed", "running", "done", "failed", "blocked", "waiting")}
    for s in plan["steps"]:
        item = state[s["id"]]
        if item["state"] == "done":
            groups["done"].append(s["id"])
        elif item["state"] in ("failed", "running", "blocked"):
            groups[item["state"]].append(s["id"])
        elif item["claimed"]:
            groups["claimed"].append(s["id"])
        elif all(state[d]["state"] == "done" for d in s["deps"]):
            groups["ready"].append(s["id"])
        else:
            groups["waiting"].append(s["id"])
    groups["complete"] = not (groups["ready"] or groups["claimed"] or groups["running"] or groups["waiting"])
    return groups


def check_plan(plan: dict) -> None:
    seen: set = set()
    for s in plan["steps"]:
        if s["id"] in seen or any(d not in seen for d in s["deps"]):
            raise SystemExit(f"plan invalid at {s['id']}: ids must be unique and deps must name earlier steps")
        if not isinstance(s.get("kit", {}).get("seconds"), (int, float)):
            raise SystemExit(f"plan invalid at {s['id']}: kit.seconds is required")
        seen.add(s["id"])


def cmd_init(args) -> int:
    run = Run(args.run)
    plan_text = Path(args.plan).read_text()
    plan = json.loads(plan_text)
    check_plan(plan)
    run.dir.mkdir(parents=True, exist_ok=False)
    (run.dir / "out").mkdir()
    (run.dir / "plan.json").write_text(plan_text)
    (run.dir / "meta.json").write_text(json.dumps({"schema": SCHEMA, "plan_sha": _sha(plan_text),
                                                   "plan": plan.get("name"), "scale": SCALE}, indent=1))
    with run.locked():
        run.append("init", None, plan=plan.get("name"), steps=[s["id"] for s in plan["steps"]], scale=SCALE)
    print(f"INIT {plan.get('name')} steps={len(plan['steps'])} run={run.dir}")
    return 0


def cmd_ready(args) -> int:
    run = Run(args.run)
    with run.locked():
        plan = run.plan()
        groups = classify(plan, derive(plan, run.events()))
        if args.claim:
            for step in groups["ready"]:
                run.append("claim", step)
        printed = {key: groups[key] for key in ("ready", "claimed", "running", "done", "failed", "blocked", "waiting")}
        printed["complete"] = groups["complete"]
        run.append("ready", None, result=printed, claim=bool(args.claim))
    print(json.dumps(printed, separators=(",", ":")))
    return 0


def cmd_run(args) -> int:
    run, step_id = Run(args.run), args.step
    with run.locked():
        plan, meta = run.plan(), run.meta()
        steps = {s["id"]: s for s in plan["steps"]}
        if step_id not in steps:
            run.append("refused", step_id, reason="unknown step", command="run")
            print(f"REFUSED {step_id}: not a step of this plan")
            return 3
        state = derive(plan, run.events())
        step, reasons = steps[step_id], []
        if state[step_id]["starts"]:
            reasons.append("it already started; each step runs once")
        unfinished = [d for d in step["deps"] if state[d]["state"] != "done"]
        if unfinished:
            reasons.append("its dependencies have not finished OK: " + ", ".join(f"{d} ({state[d]['state']})" for d in unfinished))
        if reasons:
            run.append("refused", step_id, reason="; ".join(reasons), command="run")
            print(f"REFUSED {step_id}: " + "; ".join(reasons))
            return 3
        inputs = {d: state[d]["sha"] for d in step["deps"]}
        run.append("start", step_id, deps=inputs, seconds=step["kit"]["seconds"], scale=SCALE)
    began = time.time()
    time.sleep(step["kit"]["seconds"] * SCALE)
    actual = round(time.time() - began, 3)
    if step["kit"].get("fail"):
        with run.locked():
            run.append("fail", step_id, reason="injected failure", seconds=actual)
        print(f"STEP {step_id} FAILED (injected failure); steps that depend on it must not run")
        return 1
    sha = out_hash(meta["plan_sha"], step_id, inputs)
    target = run.dir / "out" / f"{step_id}.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps({"step": step_id, "inputs": inputs, "sha": sha}))
    os.replace(tmp, target)
    with run.locked():
        run.append("end", step_id, sha=sha, seconds=actual)
    print(f"STEP {step_id} OK sha={sha[:12]} seconds={actual} (finished; do not run it again)")
    return 0


def verdict(run: Run) -> tuple[str, str]:
    """(OK|PARTIAL|FAIL, the one line) recomputed from the ledger and the output files."""
    plan, meta = run.plan(), run.meta()
    state = derive(plan, run.events())
    problems = []
    for s in plan["steps"]:
        step, item = s["id"], state[s["id"]]
        if item["starts"] > 1:
            problems.append(f"{step} started {item['starts']} times")
        if item["state"] == "running":
            problems.append(f"{step} started and never ended")
        for d in s["deps"]:
            if item["start_seq"] is not None and (state[d]["end_seq"] is None or item["start_seq"] < state[d]["end_seq"]):
                problems.append(f"{step} started before {d} ended")
        if item["state"] == "done":
            inputs = {d: state[d]["sha"] for d in s["deps"]}
            expect = out_hash(meta["plan_sha"], step, inputs)
            target = run.dir / "out" / f"{step}.json"
            written = json.loads(target.read_text()).get("sha") if target.is_file() else None
            if written != expect or item["sha"] != expect:
                problems.append(f"{step} output does not chain from its dependencies")
    ok = [s["id"] for s in plan["steps"] if state[s["id"]]["state"] == "done"]
    failed = [s["id"] for s in plan["steps"] if state[s["id"]]["state"] == "failed"]
    not_run = [s["id"] for s in plan["steps"] if state[s["id"]]["state"] in ("blocked", "pending")]
    if problems:
        return "FAIL", "VERIFY FAIL " + "; ".join(problems)
    if len(ok) == len(plan["steps"]):
        root = _sha("|".join(state[s["id"]]["sha"] for s in plan["steps"]))[:12]
        return "OK", f"VERIFY OK steps={len(ok)} chain={root}"
    return "PARTIAL", "VERIFY PARTIAL ok=" + ",".join(ok) + " failed=" + ",".join(failed) + " not_run=" + ",".join(not_run)


def cmd_verify(args) -> int:
    run = Run(args.run)
    kind, line = verdict(run)
    with run.locked():
        run.append("verify", None, verdict=kind, line=line)
    print(line)
    return {"OK": 0, "PARTIAL": 2, "FAIL": 1}[kind]


def cmd_timeline(args) -> int:
    events = Run(args.run).events()
    t0 = events[0]["ts"] if events else 0.0
    for e in events:
        extra = {k: v for k, v in e["detail"].items() if k in ("reason", "sha", "seconds", "line", "deps") or k == "result"}
        print(f"+{e['ts'] - t0:8.3f}s  #{e['seq']:<3} {e['kind']:<8} {e['step'] or '-':<4} pid={e['pid']} {json.dumps(extra, separators=(',', ':')) if extra else ''}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("init", cmd_init), ("ready", cmd_ready), ("run", cmd_run), ("verify", cmd_verify),
                     ("timeline", cmd_timeline)):
        p = sub.add_parser(name)
        p.add_argument("--run", required=True)
        if name == "init":
            p.add_argument("--plan", required=True)
        if name == "ready":
            p.add_argument("--claim", action="store_true")
        if name == "run":
            p.add_argument("--step", required=True)
        p.set_defaults(fn=fn)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
