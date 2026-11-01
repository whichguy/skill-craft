#!/usr/bin/env python3
"""The implement send-back class in the 20 scored runs of replication R3 (../send-back-replication-r3-20261101/README.md), read-only.
Prints (1) every implement attempt with the kind of its Proof and its outcome, (2) the shipped proof-order gate (rules A, B, C)
replayed on every accepted step plan of the runs, and (3) the direct time cost of each implement send-back loop.
Usage: python3 -I implement_class.py > implement-class-analysis.txt   (reads ~/e2e-runs-r3/20261101, outside git)
"""
import collections
import json
import os
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
import shiploop_item_scope as scope  # noqa: E402
import shiploop_store as store  # noqa: E402

ROOT = Path(os.path.expanduser("~/e2e-runs-r3/20261101"))
RUNS = sorted((p for p in ROOT.glob("[AB]-shared-expenses-s*") if p.is_dir()), key=lambda p: (p.name[0], int(p.name.rsplit("-s", 1)[1])))


def run_folder(out):
    return (sorted(out.glob("work/.shiploop")) + sorted(out.glob(".shiploop-runs/*/run")))[0]


def short(name):
    return name.replace("-shared-expenses-s", "")


print("== 1. every implement attempt (35 in 20 runs): the Proof the model was held to, and what implement did")
print(f"{'run':5} {'step':5} {'executed':8} {'test-based Confirm by':21} {'proof kind':11} outcome   proof")
attempts = []
for out in RUNS:
    run = run_folder(out)
    state = store.read_record(run / "state.md")
    for entry in state["history"]:
        if entry["stage"] != "implement":
            continue
        text = (run / "packets" / (entry["action"] + ".md")).read_text(encoding="utf-8", errors="replace")
        step = re.search(r"Step (S\d+) \((\d+) of (\d+)\)", text)
        criteria = re.findall(r"^\s+(C\d+) \[(executed|searched)\]: (.*)$", text, re.M)
        proof = re.search(r"^\s+Proof \(ShipLoop runs it[^)]*\)[^:]*: (.*)$", text, re.M)
        proof = proof.group(1).strip() if proof else "?"
        executed = [c for c in criteria if c[1] == "executed"]
        by_tests = [c for c in executed if re.search(r"Confirm by:[^.]*\b(node --test|test|TC_\d+)", c[2])]
        kind = "test-runner" if re.search(r"--test|npm test|unittest|pytest|jest|vitest", proof) else "direct probe"
        attempts.append((short(out.name), f"{step.group(1)}/{step.group(3)}" if step else "?", len(executed), len(by_tests), kind, entry["outcome"], proof))
        print(f"{short(out.name):5} {attempts[-1][1]:5} {len(executed):8} {len(by_tests):21} {kind:11} {entry['outcome']:9} {proof[:70]!r}")
print("\n(proof kind, outcome):", dict(collections.Counter((a[4], a[5]) for a in attempts)))
print("(executed criteria whose Confirm by names tests are present, outcome):", dict(collections.Counter((a[3] > 0, a[5]) for a in attempts)))
first = {}
for a in attempts:
    first.setdefault(a[0], a)
print("first implement attempt of each run, by Proof kind:",
      {kind: dict(collections.Counter(a[5] for a in first.values() if a[4] == kind)) for kind in ("test-runner", "direct probe")})

print("\n== 2. the shipped proof-order gate (rules A, B, C of shiploop_item_scope.proof_order_refusal) on every accepted step plan")
refused = looked = 0
for out in RUNS:
    run = run_folder(out)
    state = store.read_record(run / "state.md")
    for entry in state["history"]:
        if entry["stage"] == "step-plan" and entry["outcome"] == "done":
            looked += 1
            if scope.proof_order_refusal(state["accepted"][entry["action"]], lambda path: False):
                refused += 1
print(f"plans looked at {looked}, refused by the shipped gate on an empty base {refused} (the six implement send-backs of the class all stand)")

print("\n== 3. the direct cost of each implement send-back loop (the send-back implement and the stages that re-ran up to the next implement)")
loops = []
for out in RUNS:
    metrics = json.loads((out / "metrics.json").read_text())
    stages = metrics.get("stages") or []
    i = 0
    while i < len(stages):
        if stages[i].get("stage") == "implement" and stages[i].get("outcome") == "send-back":
            cost, j = stages[i].get("seconds") or 0, i + 1
            while j < len(stages) and stages[j].get("stage") != "implement":
                cost += stages[j].get("seconds") or 0
                j += 1
            loops.append((short(out.name), round(cost / 60, 1)))
            i = j
        else:
            i += 1
print("loops (run, minutes):", loops)
total_minutes = statistics.mean(
    sum(s.get("seconds") or 0 for s in (json.loads((o / "metrics.json").read_text()).get("stages") or [])) / 60 for o in RUNS)
print(f"mean {statistics.mean(m for _, m in loops):.1f} minutes a loop (n={len(loops)}); {sum(m for _, m in loops) / len(RUNS):.2f} minutes a run over all {len(RUNS)} runs,"
      f" on a mean of {total_minutes:.1f} stage minutes a run")
