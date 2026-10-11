#!/usr/bin/env python3
"""Replay the recorded runs against the count floor: would ``shiploop_test_loop.accepted_counts`` have refused any run?

Question (G6, A5): the floor is the most any run ShipLoop accepted for the item has run since its latest step plan, with
test-refine restarting it.  Counted over every recorded test record that has a floor: how many ran fewer tests than the floor
(false refusals, on runs that did nothing wrong), and how far below the highest accepted count the model's own ``min_tests``
sat (what the floor adds).  Every recorded run is greenfield (the repository was empty), where tests are only added, so a
result of 0 refusals says nothing about brownfield items that remove tests: that is unmeasured.
Run from the repository root: ``python3 docs/experiments/batch-1010j-g6-ids-floors-20261008/a5_replay.py``.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

OUTER = tuple(test_loop.OUTER_SOURCES) + ("end-of-work review",)


def replay(run: dict) -> dict:
    stats = {"records": 0, "floored_runs": 0, "would_refuse": [], "min_vs_best": []}
    history = run["history"]
    rows = {row["action"]: index for index, row in enumerate(history) if row["action"] not in (None, "")}
    best = {}
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        for action, numbered in run["verify"].items():
            for number, record in numbered.items():
                store.write_record(root / test_loop.verify_path(action, int(number)), record)
        for action, numbered in sorted(run["verify"].items(), key=lambda item: rows.get(item[0], len(history))):
            first = next(iter(numbered.values()))
            item = first["work_item"]
            stats["records"] += len(numbered)
            if not item or first["stage"] in OUTER or first["stage"] == test_loop.REFINE_STAGE:
                continue
            state = {"history": history[:rows.get(action, len(history))], "accepted": run["step_plans"]}
            floors = test_loop.accepted_counts(root, state, item)
            for number in sorted(numbered, key=int):
                for ran_run in numbered[number]["runs"]:
                    ran = (ran_run.get("counts") or {}).get("ran")
                    floor = floors.get(ran_run["command"])
                    if floor and ran_run["status"] in ("passed", "red") and isinstance(ran, int):
                        stats["floored_runs"] += 1
                        if ran < floor:
                            stats["would_refuse"].append([action, first["stage"], ran_run["command"], ran, floor])
                    if numbered[number]["passed"] and ran_run["status"] in ("passed", "red") and isinstance(ran, int):
                        best[(item, ran_run["command"])] = max(best.get((item, ran_run["command"]), 0), ran)
    latest = {}  # the item's latest accepted step plan: the one its commands and minimums come from
    for row in history:
        plan = run["step_plans"].get(row["action"])
        if row["stage"] == "step-plan" and row["workitem"] and plan and plan["outcome"] == "done":
            latest[row["workitem"]] = plan
    for (item, command), top in best.items():
        for row in (latest.get(item) or {}).get("test_commands", ()):
            if row["command"] == command and row.get("min_tests"):
                stats["min_vs_best"].append([item, command, row["min_tests"], top])
    return stats


def main() -> int:
    recorded = json.loads(Path(__file__).with_name("a5-recorded-runs.json").read_text())
    total_refused = total_floored = total_records = 0
    ratios = []
    for run in recorded:
        stats = replay(run)
        total_records += stats["records"]
        total_floored += stats["floored_runs"]
        total_refused += len(stats["would_refuse"])
        for item, command, minimum, top in stats["min_vs_best"]:
            ratios.append(minimum / top)
            if minimum < top:
                print("    min_tests %3d against %3d accepted (%3.0f%%): %s" % (minimum, top, 100 * minimum / top, command[:70]))
        print("%-62s records %3d, runs held to a floor %3d, would refuse %d" % (
            run["run"][:62], stats["records"], stats["floored_runs"], len(stats["would_refuse"])))
        for refused in stats["would_refuse"]:
            print("    WOULD REFUSE", refused)
    print("TOTAL: %d runs, %d test records, %d recorded runs held to a floor, %d would be refused" % (
        len(recorded), total_records, total_floored, total_refused))
    if ratios:
        below = sorted(r for r in ratios if r < 1)
        print("model min_tests against the highest accepted count: %d commands name one, %d of them sit below it "
              "(%.0f%% to %.0f%% of it); the floor adds what those leave unheld" % (
                  len(ratios), len(below), 100 * below[0] if below else 100, 100 * below[-1] if below else 100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
