#!/usr/bin/env python3
"""Score the F31 live check (README.md in this folder), read-only, over the run folders launch.sh made.

    python3 -I score.py SHIPLOOP_SCRIPTS RUNS_ROOT --blind            # every implement send-back, shuffled, no run names
    python3 -I score.py SHIPLOOP_SCRIPTS RUNS_ROOT [--labels labels.jsonl] [--out scores.json]

Each folder RUNS_ROOT/<arm>-<case>-s<n> is a slice (slice-result.json) or a csv-report delivery (result.json). Per run it
records the item's implement results in order, and for each implement send-back its headline, its summary and whether
the text matches F31's registered pattern. The pattern only finds candidates: labels.jsonl, one reading per send-back,
decides, and an unlabelled candidate is reported as unread. Labels are made from ``--blind``'s list, which shows each
send-back's headline, summary and the Proofs of the step plan in force under a key (a hash of run and action), in a
fixed shuffled order, without its run (README, amendment of 2026-11-01). It also records the test files implement changed (slices:
the candidate's changed paths that are test files), the case checks (slices) or run.py's pass (deliveries), and the
minutes. Then it applies the registered decision rule.
"""
import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

# F31's pattern (README, "Measures"): the send-back names a test and says it is unwritten, forbidden at implement, or
# the test stage's.
NAMES_TEST = re.compile(r"\b(tests?|tc[-_ ]?\d+|unittest|focused|confirm)", re.IGNORECASE)
SAYS_WHY = re.compile(r"(not exist|does not exist|doesn'?t exist|unwritten|not yet written|not written|forbid|may not "
                      r"write|cannot write|can'?t write|not allowed to write|later stage|test stage|written later|"
                      r"before the test)", re.IGNORECASE)
TEST_FILE = re.compile(r"(^|/)(test|tests|__tests__)/|\.test\.[a-z]+$|(^|/)test_[^/]+\.py$")
NAME = re.compile(r"^(?P<arm>[AB])-(?P<case>.+)-s(?P<sample>\d+)$")


def state_dirs(out: Path):
    """The ShipLoop run folders inside one output, skipping builds, sandboxed homes and checked-out trees."""
    for state in sorted(out.glob("**/state.md")):
        run = state.parent
        text = str(run)
        if any(part in text for part in ("/build/", "/home/", "/node_modules/")):
            continue
        if any((folder / "skills" / "shiploop" / "SKILL.md").is_file() for folder in run.parents if out in folder.parents
               or folder == out):
            continue
        if (run.name == "run" and run.parent.parent.name == ".shiploop-runs") or (run.name == ".shiploop"):
            yield run


def implement_results(store, run: Path, item: str | None):
    """The item's implement results in order, each with the Proofs of the step plan in force when it ran (the plan of
    the item's last accepted step-plan before it; a seeded plan when the run never ran step-plan)."""
    state = store.read_record(run / "state.md")
    accepted = state.get("accepted") or {}
    rows, plan_of = [], {}
    for row in state.get("history") or []:
        if row.get("stage") == "step-plan" and row.get("outcome") == "done":
            plan = accepted.get(row.get("action"))
            if isinstance(plan, dict):
                plan_of[row.get("workitem")] = plan
        if row.get("stage") != "implement" or (item and row.get("workitem") != item):
            continue
        headline = ""
        result_file = run / "results" / (str(row.get("action")) + ".md")
        if result_file.is_file():
            try:
                headline = str((store.read_record(result_file).get("result") or {}).get("headline") or "")
            except Exception:  # noqa: BLE001 - an unreadable result keeps the history summary
                headline = ""
        plan = plan_of.get(row.get("workitem")) or {}
        proofs = [str(step.get("id")) + ": " + str(step.get("proof") or "")[:400]
                  for step in plan.get("steps") or () if isinstance(step, dict)]
        rows.append({"action": row.get("action"), "outcome": row.get("outcome"), "headline": headline,
                     "summary": str(row.get("summary") or ""), "proofs": proofs})
    return rows


def key_of(run: str, action: str) -> str:
    return hashlib.sha256((run + "/" + action).encode()).hexdigest()[:10]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("scripts")
    p.add_argument("runs", type=Path)
    p.add_argument("--labels", type=Path, default=Path(__file__).resolve().parent / "labels.jsonl")
    p.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "scores.json")
    p.add_argument("--blind", action="store_true", help="print every implement send-back to label, without its run")
    args = p.parse_args()
    sys.path.insert(0, args.scripts)
    import shiploop_store as store  # noqa: E402

    labels = {}
    if args.labels.is_file():
        for line in args.labels.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                labels[row["key"]] = row
    runs = []
    for out in sorted(path for path in args.runs.iterdir() if path.is_dir()):
        name = NAME.match(out.name)
        if not name:
            continue
        slice_file, delivery_file = out / "slice-result.json", out / "result.json"
        kind = "slice" if slice_file.is_file() else "delivery" if delivery_file.is_file() else None
        if kind is None:
            runs.append({"run": out.name, **name.groupdict(), "kind": "unfinished"})
            continue
        result = json.loads((slice_file if kind == "slice" else delivery_file).read_text())
        item = result.get("item") if kind == "slice" else None
        implements = [row for run in state_dirs(out) for row in implement_results(store, run, item)]
        sendbacks = []
        for row in implements:
            if row["outcome"] != "send-back":
                continue
            text = row["headline"] + " " + row["summary"]
            label = labels.get(key_of(out.name, str(row["action"])))
            sendbacks.append({"key": key_of(out.name, str(row["action"])), "action": row["action"],
                              "headline": row["headline"], "summary": row["summary"][:600], "proofs": row["proofs"],
                              "pattern": bool(NAMES_TEST.search(text) and SAYS_WHY.search(text)),
                              "f31": label["f31"] if label else None, "reading": label.get("reading") if label else None})
        entry = {"run": out.name, **name.groupdict(), "kind": kind,
                 "implement_outcomes": [row["outcome"] for row in implements], "sendbacks": sendbacks,
                 "f31": sum(1 for s in sendbacks if s["f31"] is True),
                 "f31_unread": sum(1 for s in sendbacks if s["f31"] is None and s["pattern"])}
        if kind == "slice":
            changed = [str(path) for path in (result.get("assembled") or {}).get("changed") or ()]
            entry.update(tests_written=[path for path in changed if TEST_FILE.search(path)], changed=changed,
                         checks_pass=bool(result.get("checks")) and all(c.get("pass") for c in result["checks"]),
                         implement_done=bool(implements) and implements[-1]["outcome"] == "done",
                         first_try_done=bool(implements) and implements[0]["outcome"] == "done",
                         minutes=round(sum(s.get("elapsed_seconds") or 0 for s in result.get("sessions") or ()) / 60, 1))
        else:
            entry.update(passed=bool(result.get("pass")), outcome_class=result.get("outcome_class"),
                         minutes=round(((result.get("process") or {}).get("elapsed_seconds") or 0) / 60, 1))
        runs.append(entry)

    if args.blind:
        shown = [{"key": s["key"], "headline": s["headline"], "summary": s["summary"], "proofs": s["proofs"]}
                 for r in runs for s in r.get("sendbacks") or ()]
        random.Random(20261101).shuffle(shown)
        print(json.dumps(shown, indent=1))
        return

    def arm(a, kind=None):
        return [r for r in runs if r.get("arm") == a and (kind is None or r["kind"] == kind)]
    summary = {}
    for a in ("A", "B"):
        slices, deliveries = arm(a, "slice"), arm(a, "delivery")
        summary[a] = {"slices": len(slices), "deliveries": len(deliveries),
                      "f31": sum(r["f31"] for r in arm(a) if "f31" in r),
                      "f31_unread": sum(r["f31_unread"] for r in arm(a) if "f31_unread" in r),
                      "implement_sendbacks": sum(len(r["sendbacks"]) for r in arm(a) if "sendbacks" in r),
                      "slices_writing_tests": sum(1 for r in slices if r["tests_written"]),
                      "slices_checks_pass": sum(1 for r in slices if r["checks_pass"]),
                      "slices_first_try_done": sum(1 for r in slices if r["first_try_done"]),
                      "deliveries_pass": sum(1 for r in deliveries if r["passed"]),
                      "unfinished": len([r for r in arm(a) if r["kind"] == "unfinished"])}
    A, B = summary["A"], summary["B"]
    rule = {"1_no_f31_in_B": B["f31"] == 0 and B["f31_unread"] == 0,
            "2_no_tests_written_in_B": B["slices_writing_tests"] == 0,
            "3_no_harm": B["slices_checks_pass"] >= A["slices_checks_pass"] and B["deliveries_pass"] >= A["deliveries_pass"],
            "complete": A["unfinished"] == 0 and B["unfinished"] == 0 and A["f31_unread"] == 0}
    decision = ("adopt" if all(rule.values()) else "incomplete: score again when every run is finished and every candidate is read"
                if not rule["complete"] else "not adopted (rule 1 or 2 failed)" if not (rule["1_no_f31_in_B"] and
                rule["2_no_tests_written_in_B"]) else "read every failing run before deciding (rule 3)")
    report = {"summary": summary, "rule": rule, "decision": decision,
              "benefit": f"arm A F31 send-backs: {A['f31']}" + ("" if A["f31"] else " (mechanism unexercised; benefit unmeasured)"),
              "runs": runs}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "runs"}, indent=1))


if __name__ == "__main__":
    main()
