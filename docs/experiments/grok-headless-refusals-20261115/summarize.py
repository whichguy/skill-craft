#!/usr/bin/env python3
"""Rate tables over analyze.py's output, and the compact evidence the repository keeps.

Usage: summarize.py ANALYSIS_DIR EVIDENCE_DIR
Reads ANALYSIS_DIR/runs.json and calls.jsonl. Writes EVIDENCE_DIR/summary.json, summary.md and refusals.jsonl (one row per
refused shell call: run, build, mode, stage, how fast Grok refused it, the probe-derived shapes and the command's head,
with the home folder written as ~).
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HOME = os.path.expanduser("~")
TIMEOUT_MS = 25_000  # Grok's classifier gives up at about 30 s ("classifier timed out ... prompting user")
LOCAL_MS = 50        # a decision this fast never reached the classifier (its reviews take 1.8 s to 8 s)


def build_of(run: dict) -> str:
    recorded = run.get("build") or ""
    if recorded.startswith("grok "):
        return recorded.split()[1]
    logged = run.get("logged_builds") or []
    return ",".join(logged) if logged else "unrecorded"


def kind_of(run: dict) -> str:
    path = run["run"]
    if "/slice" in path:
        return "slice"
    if "e2e-runs-startroute" in path:
        return "start-route probe"
    return "delivery"


def refusal_class(row: dict) -> str:
    wait = row.get("wait_ms")
    if wait is None:
        return "refused (stream only)"
    if wait <= LOCAL_MS:
        return "floor"
    if wait >= TIMEOUT_MS:
        return "classifier timeout"
    return "classifier escalation"


def short(path: str) -> str:
    return path.replace(HOME, "~")


def main() -> int:
    analysis, evidence = Path(sys.argv[1]), Path(sys.argv[2])
    runs = json.loads((analysis / "runs.json").read_text())
    rows = [json.loads(line) for line in (analysis / "calls.jsonl").read_text().splitlines()]
    by_run = {r["run"]: r for r in runs}
    for run in runs:
        run["build_"] = build_of(run)
        run["kind"] = kind_of(run)
        run["mode"] = "+".join(run["modes"])
    refused = [r for r in rows if r["refused"]]
    summary: dict = {"runs": len(runs), "paired_runs": sum(r["paired"] for r in runs), "refused_calls": len(refused)}

    # A: by build and mode, over every Grok run (paired runs give decisions; stream-only runs give refusals only).
    table_a = defaultdict(Counter)
    for run in runs:
        key = (run["build_"], run["mode"])
        cell = table_a[key]
        cell["runs"] += 1
        cell["shell calls"] += run["shell_calls"]
        cell["refused"] += run["refused_stream"]
        cell["runs with a refusal"] += run["refused_stream"] > 0
        cell["classifier blocks (model told)"] += run["decisions"].get("run_terminal_command:deny", 0)
    for row in refused:
        table_a[(by_run[row["run"]]["build_"], by_run[row["run"]]["mode"])][refusal_class(row)] += 1
    summary["by_build_mode"] = {f"{b} | {m}": dict(c) for (b, m), c in sorted(table_a.items())}

    # B: by run kind, for the auto mode.
    table_b = defaultdict(Counter)
    for run in runs:
        if run["mode"] != "auto":
            continue
        cell = table_b[run["kind"]]
        cell["runs"] += 1
        cell["shell calls"] += run["shell_calls"]
        cell["refused"] += run["refused_stream"]
        cell["runs with a refusal"] += run["refused_stream"] > 0
    summary["by_kind_auto"] = {k: dict(c) for k, c in sorted(table_b.items())}

    # C: every delivery run (not a slice or probe), one row each.
    deliveries = []
    for run in sorted((r for r in runs if r["kind"] == "delivery"), key=lambda r: r["date"]):
        mine = [r for r in refused if r["run"] == run["run"]]
        deliveries.append({
            "run": short(run["run"]), "date": run["date"], "build": run["build_"], "mode": run["mode"],
            "case": run.get("case"), "shell_calls": run["shell_calls"], "refused": len(mine),
            "floor": sum(refusal_class(r) == "floor" for r in mine),
            "timeout": sum(refusal_class(r) == "classifier timeout" for r in mine),
            "sessions": run.get("sessions"), "cancelled_sessions": run.get("cancelled_sessions"),
            "final": f"{run.get('final_status')} at {run.get('final_stage')}", "outcome": run.get("outcome"),
            "resume_stop": run.get("resume_stop"), "seconds": run.get("seconds"), "cost_usd": run.get("cost_usd")})
    summary["deliveries"] = deliveries

    # D: refusals by ShipLoop stage (paired runs, where each refusal has a time).
    stages = Counter(r.get("stage") or "unattributed" for r in refused if r.get("wait_ms") is not None)
    summary["refusals_by_stage"] = dict(stages.most_common())
    delivery_stages = Counter(r.get("stage") or "unattributed" for r in refused
                              if r.get("wait_ms") is not None and by_run[r["run"]]["kind"] == "delivery")
    summary["delivery_refusals_by_stage"] = dict(delivery_stages.most_common())
    # Repeats: a refusal followed by another refusal within the next 10 shell calls of the same run (paired runs).
    repeats = total = 0
    for run in runs:
        if not run["paired"]:
            continue
        indexes = sorted(r["index"] for r in refused if r["run"] == run["run"])
        total += len(indexes)
        repeats += sum(1 for a, b in zip(indexes, indexes[1:]) if b - a <= 10)
    summary["repeats_within_10_calls"] = {"refusals": total, "followed_by_another": repeats}

    # E: the probe-derived shapes of each refusal, by build.
    shapes = defaultdict(Counter)
    for row in refused:
        if row.get("wait_ms") is not None and row["wait_ms"] <= LOCAL_MS:
            shapes[by_run[row["run"]]["build_"]][",".join(row.get("floor_shapes") or []) or "none found"] += 1
    summary["floor_shapes_by_build"] = {b: dict(c.most_common()) for b, c in sorted(shapes.items())}

    # F: how well the probe-derived shapes predict a floor refusal, by build (paired auto runs).
    confusion = defaultdict(Counter)
    for row in rows:
        run = by_run[row["run"]]
        if not run["paired"] or run["mode"] != "auto":
            continue
        floor = row["refused"] and row["wait_ms"] is not None and row["wait_ms"] <= LOCAL_MS
        confusion[run["build_"]][("flagged" if row.get("floor_shapes") else "not flagged") + " / "
                                 + ("floor refusal" if floor else "not a floor refusal")] += 1
    summary["shape_rule_by_build"] = {b: dict(c) for b, c in sorted(confusion.items())}

    # G: what a refusal costs before the next session's first tool call.
    gaps = sorted(r["restart_gap_s"] for r in refused if r.get("restart_gap_s") is not None)
    if gaps:
        summary["restart_gap_s"] = {"n": len(gaps), "median": gaps[len(gaps) // 2], "p90": gaps[int(len(gaps) * 0.9)],
                                    "max": gaps[-1]}

    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    with open(evidence / "refusals.jsonl", "w") as handle:
        for row in refused:
            run = by_run[row["run"]]
            handle.write(json.dumps({
                "run": short(row["run"]), "build": run["build_"], "mode": run["mode"], "kind": run["kind"],
                "stage": row.get("stage"), "wait_ms": row.get("wait_ms"), "class": refusal_class(row),
                "floor_shapes": row.get("floor_shapes"), "restart_gap_s": row.get("restart_gap_s"),
                "command_head": short(row["command"])[:300]}) + "\n")

    lines = ["# Grok headless refusals: summary", "",
             f"{summary['runs']} Grok runs read; {summary['paired_runs']} kept Grok's session store, so each of their "
             f"shell calls is paired with Grok's own decision; {summary['refused_calls']} refused shell calls.", "",
             "## By Grok build and permission mode", "",
             "| build | mode | runs | shell calls | refused | per 100 calls | runs with a refusal | floor | classifier timeout | classifier escalation | stream only | classifier blocks (model told) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, cell in summary["by_build_mode"].items():
        build, mode = key.split(" | ")
        per = 100 * cell.get("refused", 0) / cell["shell calls"] if cell.get("shell calls") else 0
        lines.append(f"| {build} | {mode} | {cell['runs']} | {cell['shell calls']} | {cell.get('refused', 0)} | {per:.2f} | "
                     f"{cell.get('runs with a refusal', 0)} | {cell.get('floor', 0)} | {cell.get('classifier timeout', 0)} | "
                     f"{cell.get('classifier escalation', 0)} | {cell.get('refused (stream only)', 0)} | "
                     f"{cell.get('classifier blocks (model told)', 0)} |")
    lines += ["", "## Auto mode by run kind", "", "| kind | runs | shell calls | refused | runs with a refusal |",
              "|---|---|---|---|---|"]
    for kind, cell in summary["by_kind_auto"].items():
        lines.append(f"| {kind} | {cell['runs']} | {cell['shell calls']} | {cell.get('refused', 0)} | "
                     f"{cell.get('runs with a refusal', 0)} |")
    lines += ["", "## Delivery runs", "",
              "| date | run | build | mode | shell calls | refused (floor, timeout) | sessions (cancelled) | ShipLoop at the end | resume stop |",
              "|---|---|---|---|---|---|---|---|---|"]
    for d in deliveries:
        lines.append(f"| {d['date']} | {d['run']} | {d['build']} | {d['mode']} | {d['shell_calls']} | {d['refused']} "
                     f"({d['floor']}, {d['timeout']}) | {d['sessions']} ({d['cancelled_sessions']}) | {d['final']} | "
                     f"{d['resume_stop'] or ''} |")
    lines += ["", "## Refusals by ShipLoop stage (paired runs)", "", "| stage | all paired runs | delivery runs |",
              "|---|---|---|"]
    lines += [f"| {stage} | {n} | {summary['delivery_refusals_by_stage'].get(stage, 0)} |"
              for stage, n in summary["refusals_by_stage"].items()]
    rep = summary["repeats_within_10_calls"]
    lines += ["", f"Of {rep['refusals']} refusals in paired runs, {rep['followed_by_another']} were followed by another "
                  "refusal within the next 10 shell calls of the same run."]
    lines += ["", "## Floor refusals by probe-derived shape", ""]
    for build, cell in summary["floor_shapes_by_build"].items():
        lines.append(f"- {build}: " + ", ".join(f"{shape} {n}" for shape, n in cell.items()))
    lines += ["", "## How well the shapes predict a floor refusal (paired auto runs)", ""]
    for build, cell in summary["shape_rule_by_build"].items():
        lines.append(f"- {build}: " + "; ".join(f"{k} {v}" for k, v in sorted(cell.items())))
    if "restart_gap_s" in summary:
        g = summary["restart_gap_s"]
        lines += ["", f"Refusal to the next session's first tool call: median {g['median']} s, 90th percentile {g['p90']} s, "
                      f"max {g['max']} s (n = {g['n']})."]
    (evidence / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
