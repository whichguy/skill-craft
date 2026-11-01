#!/usr/bin/env python3
"""Descriptive extras for replication R3, read after the registered rules were applied (README.md, "Results"): none of it is a rule.
Per arm: refused callbacks by stage, the send-backs with their stage and text, the K12 row of every B ledger, what a run with a send-back costs,
and the post-hoc split of the implement send-backs.  Reads scores.json (written by r3_reader.py) and the run folders.
Usage: r3_extra.py > extra-analysis.txt"""
import json
import os
import statistics
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
import shiploop_store as store  # noqa: E402

rows = json.loads((HERE / "scores.json").read_text())["rows"]
by_arm = {arm: [r for r in rows if r["arm"] == arm] for arm in ("A", "B")}


def fisher_greater(a, n_a, b, n_b):
    k = a + b
    return sum(comb(n_b, x) * comb(n_a, k - x) for x in range(b, min(n_b, k) + 1)) / comb(n_a + n_b, k)


def mean(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return round(statistics.mean(values), 2) if values else None


print("== two-sided reading of the registered measure (descriptive; the rule is one-sided, B higher)")
a, b = (sum(1 for r in by_arm[arm] if r["send_backs"]) for arm in ("A", "B"))
print(f"runs with a send-back: A {a} of 10, B {b} of 10; one-sided exact p, B higher {fisher_greater(a, 10, b, 10):.4f}; A higher {fisher_greater(b, 10, a, 10):.4f}")

print("\n== send-backs, every one (stage: text)")
for r in rows:
    for sb in r["send_backs"]:
        print(f"{r['run']}: {sb['stage']}: {sb['summary']}")

print("\n== post-hoc, not registered: the implement send-backs (a proof that needs a test the test stage writes later)")
imp = {arm: [r["run"] for r in by_arm[arm] if any(sb["stage"] == "implement" for sb in r["send_backs"])] for arm in ("A", "B")}
for arm in ("A", "B"):
    print(f"{arm}: {len(imp[arm])} of 10 runs {imp[arm]}")
print(f"one-sided exact p that A has more such runs than B: {fisher_greater(len(imp['B']), 10, len(imp['A']), 10):.4f} (not a test: chosen after looking)")

print("\n== what a run with a send-back costs (pooled over both arms, descriptive)")
for label, subset in (("with a send-back", [r for r in rows if r["send_backs"]]), ("without", [r for r in rows if not r["send_backs"]])):
    print(f"{label}: {len(subset)} runs, minutes {mean([r['minutes'] for r in subset])}, processed tokens (M) "
          f"{mean([(r['tokens'] or 0) / 1e6 for r in subset])}, implement stages {mean([r['implement_stages'] for r in subset])}")

print("\n== refused callbacks by stage (all runs of the arm)")
for arm in ("A", "B"):
    counts = {}
    for r in by_arm[arm]:
        out = Path(os.path.expanduser("~/e2e-runs-r3/20261101")) / r["run"]
        folders = sorted(out.glob("work/.shiploop")) + sorted(out.glob(".shiploop-runs/*/run"))
        trace = folders[0] / "trace.jsonl" if folders else None
        if not trace or not trace.is_file():
            continue
        for line in trace.read_text().splitlines():
            if not line.strip():
                continue
            t = json.loads(line)
            if t.get("kind") == "command" and t.get("verb") in ("check", "complete") and t.get("exit") not in (0, None):
                stage = (t.get("stage") or ["?"])[0]
                counts[stage] = counts.get(stage, 0) + 1
    print(f"{arm}: total {sum(counts.values())} in 10 runs {dict(sorted(counts.items(), key=lambda kv: -kv[1]))}")

print("\n== the K12 row and questions of every B ledger")
for r in by_arm["B"]:
    out = Path(os.path.expanduser("~/e2e-runs-r3/20261101")) / r["run"]
    folders = sorted(out.glob("work/.shiploop")) + sorted(out.glob(".shiploop-runs/*/run"))
    state = store.read_record(folders[0] / "state.md")
    history = state.get("history") or []
    intake = next((h for h in history if h.get("stage") == "intake"), None)
    stored = ((state.get("accepted") or {}).get(intake["action"]) if intake else None) or {}
    k12 = next((c for c in stored.get("question_categories") or [] if isinstance(c, dict) and c.get("id") == "K12"), None)
    print(f"{r['run']}: {json.dumps(k12)[:400]}; questions {r['intake_questions']}, under K12 {len(r['k12_questions'])}")
