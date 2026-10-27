#!/usr/bin/env python3
"""R1 report: timing, restarts and Improve passes of the hello pair (plan section 4, R1).

    python3 -B r1_report.py RUNS_DIR [--json OUT.json]

For each arm folder (control-hello, treatment-hello): the result, every session (reason, effort, seconds), the effort record,
whole-run totals (run_totals.py), the Improve children with their passes (pass-<n>.json, written by `improve-pass`) and a
cross-check of the schedule against them: each restart into class I2 should match a child that really reached pass 2 and had
pass 1 recorded before the restart. Reads files only; no model call.
"""
from __future__ import annotations

import argparse
import calendar
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_totals  # noqa: E402

ARMS = ("control", "treatment")


def epoch(stamp: str | None) -> float | None:
    try:
        return calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))
    except (TypeError, ValueError):
        return None


def children(out: Path) -> list[dict]:
    found = []
    for reviews in sorted(out.glob(".shiploop-runs/*/worktree/.shiploop-improve/**/reviews")):
        passes = []
        for path in sorted(reviews.glob("pass-*.json")):
            try:
                row = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            passes.append({"pass": row.get("pass"), "label": row.get("label"), "changed": row.get("changed"),
                           "at": row.get("at"), "t": epoch(row.get("at"))})
        notes = len(list(reviews.glob("review-*.md")))
        found.append({"child": str(reviews.parent.relative_to(out / ".shiploop-runs")), "review_notes": notes,
                      "passes": sorted(passes, key=lambda p: p["pass"] or 0)})
    return found


def sessions(out: Path) -> list[dict]:
    rows, open_rows = [], {}
    try:
        lines = (out / "sessions.jsonl").read_text().splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("row") == "start":
            open_rows[row["n"]] = row
        elif row.get("row") == "end" and row.get("n") in open_rows:
            s = open_rows.pop(row["n"])
            rows.append({"n": s["n"], "kind": s["kind"], "reason": s["reason"], "effort": s.get("effort"),
                         "seconds": round(row["t"] - s["t"], 1), "status": row.get("status")})
    return rows


def arm_report(out: Path) -> dict:
    result = {}
    try:
        result = json.loads((out / "result.json").read_text())
    except (OSError, ValueError):
        pass
    effort = {}
    try:
        effort = json.loads((out / "effort.json").read_text())
    except (OSError, ValueError):
        pass
    kids = children(out)
    all_passes = [p for k in kids for p in k["passes"]]
    ge2 = [p for p in all_passes if (p["pass"] or 0) >= 2]
    restarts = effort.get("restarts", [])
    into_i2 = [r for r in restarts if r["to"] == "I2"]
    # An I2 restart is matched when a child had pass 1 recorded at or before it and reached pass 2.
    matched = []
    for r in into_i2:
        for k in kids:
            first = next((p for p in k["passes"] if p["pass"] == 1), None)
            reached2 = any((p["pass"] or 0) >= 2 for p in k["passes"])
            if first and first["t"] is not None and first["t"] <= r["t"] + 2 and reached2:
                matched.append({"restart": r["n"], "stage": r["stage"], "child": k["child"]})
                break
    stages = ((result.get("metrics") or {}).get("stages")) or []
    return {
        "output": str(out), "pass": result.get("pass"), "status_line": (result.get("termination") or {}).get("engine_status"),
        "schedule": effort.get("schedule"), "totals": run_totals.totals(out), "sessions": sessions(out),
        "launches": [(x["class"], x["effort"], x["why"]) for x in effort.get("launches", [])],
        "restarts": [(r["n"], r["from"], r["to"], r["stage"], r["effort_before"], r["effort_after"]) for r in restarts],
        "improve": {"children": len(kids), "passes": len(all_passes), "passes_ge2": len(ge2),
                    "ge2_changed_tree": sum(1 for p in ge2 if p["changed"] is True),
                    "ge2_tree_unknown": sum(1 for p in ge2 if p["changed"] is None),
                    "children_with_ge2": sum(1 for k in kids if any((p["pass"] or 0) >= 2 for p in k["passes"])),
                    "per_child_passes": [len(k["passes"]) for k in kids]},
        "schedule_check": {"restarts_into_I2": len(into_i2), "matched_to_a_child_that_reached_pass_2": len(matched),
                           "unmatched": [r["n"] for r in into_i2 if r["n"] not in {m["restart"] for m in matched}],
                           "children_that_reached_pass_2": sum(1 for k in kids if any((p["pass"] or 0) >= 2 for p in k["passes"]))},
        "stage_seconds": [(s.get("stage"), s.get("seconds")) for s in stages],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir")
    ap.add_argument("--json")
    args = ap.parse_args()
    report = {arm: arm_report(Path(args.runs_dir) / f"{arm}-hello") for arm in ARMS if (Path(args.runs_dir) / f"{arm}-hello").exists()}
    text = json.dumps(report, indent=1, default=str)
    if args.json:
        Path(args.json).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
