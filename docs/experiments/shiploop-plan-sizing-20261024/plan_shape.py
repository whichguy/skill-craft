#!/usr/bin/env python3
"""Measure the shape of ShipLoop plans in saved runs: work items per plan, steps per item, criteria per step, and what
each implement step cost (docs/shiploop-plan-sizing-experiment-plan-2026-10-24.md).

    python3 -B docs/experiments/shiploop-plan-sizing-20261024/plan_shape.py export RUNS... > rows.json
    python3 -B docs/experiments/shiploop-plan-sizing-20261024/plan_shape.py summary rows.json

`export` walks every ShipLoop run directory under RUNS (a `run/state.md` or `.shiploop/state.md`) and writes one row per
work item that has an accepted step plan. It reads only what ShipLoop saved: `state.md` history (stage, outcome, item),
`results/<action>.md` (the plan's `work_items`, the step plan's `steps`, `criteria` and `concerns`), `timeline.json`
(accepted times), `loops/<action>-terminal.json` (the implement loop's iteration count and step id) and
`commits/<action>.txt` (the step commit, diffed in the run's worktree when it still exists). Host, model and effort come
from the nearest `result.json` or `invocation.json` above the run, never from the directory name.

An action's minutes are the gap since the previous accepted action of the run, so a stage's minutes include any host
time spent before its packet's work began. Slice seeds and S-6 clear probes are kept and flagged (`kind`), so a summary
can leave them out.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BLOCK = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
# A range such as "R-4 through R-9" counts its two ends only, so this measure is a floor.
REQUIREMENT = re.compile(r"\b(?:NFR|R)-\d+\b")


def _block(path: Path):
    match = BLOCK.search(path.read_text(encoding="utf-8")) if path.exists() else None
    return json.loads(match.group(1)) if match else None


def _time(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")


def _meta(run: Path) -> dict:
    for folder in [run, *run.parents]:
        for name in ("result.json", "invocation.json"):
            try:
                record = json.loads((folder / name).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if record.get("host"):
                return {key: record.get(key) for key in ("host", "model", "effort", "case")}
    return {"host": None, "model": None, "effort": None, "case": None}


def _diffstat(worktree: Path, sha: str):
    try:
        out = subprocess.run(["git", "-C", str(worktree), "show", "--numstat", "--format=", sha],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    files = lines = 0
    for row in out.splitlines():
        added, deleted = (row.split("\t") + ["", ""])[:2]
        if added.isdigit() and deleted.isdigit():
            files, lines = files + 1, lines + int(added) + int(deleted)
    return {"files": files, "lines": lines} if files else None


def _kind(run: Path) -> str:
    text = str(run)
    if "/seed/" in text:
        return "slice"
    if "/s6-" in text or "-audit-" in text:
        return "probe"
    return "full"


def rows_of(run: Path) -> list:
    state = _block(run / "state.md")
    if not state or not state.get("history"):
        return []
    timeline = json.loads((run / "timeline.json").read_text()) if (run / "timeline.json").exists() else {}
    accepted = timeline.get("accepted") or {}
    previous = _time(timeline["started"]) if isinstance(timeline.get("started"), str) else None
    meta, worktree = _meta(run), run.parent / "worktree"
    plan_items, items = None, {}
    for entry in state["history"]:
        action, stage, item = entry["action"], entry["stage"], entry.get("workitem")
        end = _time(accepted[action]) if action in accepted else None
        minutes = round((end - previous).total_seconds() / 60, 1) if end and previous else None
        previous = end or previous
        result = (_block(run / "results" / (action + ".md")) or {}).get("result") or {}
        if stage == "plan" and entry["outcome"] == "done":
            plan_items = len(result.get("work_items") or [])
        if not item:
            continue
        row = items.setdefault(item, {"item": item, "stage_minutes": {}, "step_plan": None, "implements": []})
        row["stage_minutes"][stage] = round(row["stage_minutes"].get(stage, 0) + (minutes or 0), 1)
        if stage == "step-plan" and entry["outcome"] == "done":
            concerns = result.get("concerns") or []
            texts = {str(c.get("id")): str(c.get("text") or "") for c in result.get("criteria") or []
                     if isinstance(c, dict)}
            row["step_plan"] = {
                "criteria": len(texts),
                "steps": [{"id": step.get("id"), "criteria": len(step.get("criteria") or []),
                           # the spec requirements its criteria serve (the step-plan template has each criterion name
                           # the R-<n> it serves), a size measure a step cannot shrink by writing fewer, larger criteria
                           "requirements": len({ref for c in step.get("criteria") or []
                                                for ref in REQUIREMENT.findall(texts.get(str(c), ""))}),
                           "paths": len(step.get("paths") or []), "task_chars": len(str(step.get("task") or "")),
                           "concerns": sum(1 for row_ in concerns if step.get("id") in (row_.get("steps") or []))}
                          for step in result.get("steps") or [] if isinstance(step, dict)]}
        if stage == "implement":
            receipt = run / "loops" / (action + "-terminal.json")
            loop = json.loads(receipt.read_text()) if receipt.exists() else {}
            step = re.search(r"step (S\d+)", str(loop.get("work", "")))
            commit = run / "commits" / (action + ".txt")
            row["implements"].append({
                "step": step.group(1) if step else None, "outcome": entry["outcome"], "minutes": minutes,
                "loop_iterations": (loop.get("progress") or {}).get("action_number"),
                "diff": _diffstat(worktree, commit.read_text().strip()) if commit.exists() and worktree.exists()
                else None})
    return [{"run": str(run), "kind": _kind(run), **meta, "plan_items": plan_items,
             "send_backs": (state.get("revisions") or {}).get(row["item"], 0), **row}
            for row in items.values() if row["step_plan"] and row["step_plan"]["steps"]]


def export(roots: list) -> list:
    runs = sorted({path.parent for root in roots for pattern in ("**/run/state.md", "**/.shiploop/state.md")
                   for path in Path(root).glob(pattern)})
    return [row for run in runs for row in rows_of(run)]


def _quantiles(values: list) -> str:
    values = sorted(value for value in values if value is not None)
    if not values:
        return "n=0"
    pick = lambda share: values[min(len(values) - 1, int(share * len(values)))]  # noqa: E731
    return f"n={len(values)} median={pick(.5)} p90={pick(.9)} max={values[-1]}"


def summary(rows: list) -> str:
    groups = collections.defaultdict(list)
    for row in rows:
        if row["kind"] == "full":
            groups[(row["host"], row["model"], row["effort"])].append(row)
    lines = []
    for key in sorted(groups, key=str):
        group = groups[key]
        steps = [len(row["step_plan"]["steps"]) for row in group]
        per_step = [step["criteria"] for row in group for step in row["step_plan"]["steps"]]
        implement = [i["minutes"] for row in group for i in row["implements"] if (i["minutes"] or 0) < 300]
        lines.append(f"{key}: items={len(group)} one-step={steps.count(1)}")
        lines.append(f"  steps per item: {_quantiles(steps)}")
        lines.append(f"  criteria per step: {_quantiles(per_step)}")
        served = [step["requirements"] for row in group for step in row["step_plan"]["steps"] if step["criteria"]]
        lines.append(f"  requirements served per step (steps that name criteria): {_quantiles(served)}")
        lines.append(f"  implement minutes per step: {_quantiles(implement)}")
        cases = collections.Counter(row["case"] for row in group)
        lines.append("  cases: " + ", ".join(f"{case} {count}" for case, count in sorted(cases.items(), key=str)))
    iterations = collections.Counter(i["loop_iterations"] for row in rows for i in row["implements"]
                                     if i["loop_iterations"] is not None)
    lines.append(f"implement Until Loop iterations per receipt (all kinds): {dict(iterations)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("export").add_argument("roots", nargs="+")
    sub.add_parser("summary").add_argument("rows", type=Path)
    args = parser.parse_args()
    if args.command == "export":
        json.dump(export(args.roots), sys.stdout, indent=1)
        sys.stdout.write("\n")
    else:
        print(summary(json.loads(args.rows.read_text(encoding="utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
