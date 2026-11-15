#!/usr/bin/env python3
"""Export each probe run's evidence into this folder, compactly, with no product code (the E2E rule: products are never
committed). Scoring is score.py's; this only copies what a reader needs to check it.

    python3 -I docs/experiments/planning-points-probe-20261114/export.py RUN_OUT [RUN_OUT ...]

Writes evidence/runs/<run>/:
- identity.json: case, host, model, effort, versions, termination, ShipLoop status and the action history (stage, outcome);
- plan.json: every accepted plan result (the first is the scored one);
- step-plans.json: per accepted step plan, its work item, steps (ids, deps, task, criteria, paths; no proofs), the text of
  each criterion the steps cite, and the concern mapping;
- release-plan.json: every accepted release-plan result;
- checks.json: the case checks as result.json records them;
- delivery.json: the files the delivery added, changed or deleted against the base commit, with line counts, and the
  lines it added to README.md, docs/operations.md, docs/api.md and CHANGELOG.md (documents, not code).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score  # noqa: E402  (one reader of a run: score.Run)

DOCS = ("README.md", "docs/operations.md", "docs/api.md", "CHANGELOG.md")


def write(folder: pathlib.Path, name: str, value) -> None:
    (folder / name).write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n")


def export(out: pathlib.Path) -> pathlib.Path:
    run = score.Run(out)
    folder = HERE / "evidence" / "runs" / out.name
    folder.mkdir(parents=True, exist_ok=True)
    result = run.result
    write(folder, "identity.json", {
        "run": str(out), "case": result.get("case"), "host": result.get("host"), "model": result.get("model"),
        "effort": result.get("effort"), "pass": result.get("pass"), "versions": result.get("versions"),
        "termination": result.get("termination"), "span": result.get("span"), "shiploop": {
            key: (result.get("shiploop") or {}).get(key) for key in ("status", "stage", "revision", "runs")},
        "history": [{"stage": entry.get("stage"), "outcome": entry.get("outcome"), "workitem": entry.get("workitem"),
                     "accepted": entry.get("action") in run.accepted} for entry in run.history]})
    write(folder, "plan.json", [{"action": entry["action"], "result": entry["result"]} for entry in run.results("plan")])
    write(folder, "step-plans.json", [{
        "action": entry["action"], "workitem": entry["workitem"], "concerns": entry["result"].get("concerns"),
        "steps": [{key: step.get(key) for key in ("id", "deps", "task", "criteria", "paths", "skills", "title", "summary",
                                                  "change") if key in step}
                  for step in entry["result"].get("steps") or [] if isinstance(step, dict)],
        "criteria": [{key: criterion.get(key) for key in ("id", "text") if key in criterion}
                     for criterion in entry["result"].get("criteria") or [] if isinstance(criterion, dict)],
        "headline": entry["result"].get("headline")} for entry in run.results("step-plan")])
    write(folder, "release-plan.json", [{"action": entry["action"], "result": entry["result"]}
                                        for entry in run.results("release-plan")])
    write(folder, "checks.json", result.get("checks") or [])
    delivery = {"start_head": run.start_head, "files": [], "documents_added_lines": {}}
    if run.work.is_dir() and run.start_head:
        stat = subprocess.run(["git", "-C", str(run.work), "diff", "--numstat", run.start_head, "HEAD"], capture_output=True,
                              text=True).stdout
        status = subprocess.run(["git", "-C", str(run.work), "diff", "--name-status", run.start_head, "HEAD"],
                                capture_output=True, text=True).stdout
        kinds = {line.split("\t")[-1]: line.split("\t")[0] for line in status.splitlines() if line}
        for line in stat.splitlines():
            added, removed, name = line.split("\t", 2)
            delivery["files"].append({"path": name, "status": kinds.get(name), "added": added, "removed": removed})
        delivery["head"] = subprocess.run(["git", "-C", str(run.work), "rev-parse", "HEAD"], capture_output=True,
                                          text=True).stdout.strip()
        for name in DOCS:
            delivery["documents_added_lines"][name] = score.added_lines(run.base_file(name), run.file(name)).splitlines()
    write(folder, "delivery.json", delivery)
    return folder


def main(argv) -> int:
    for arg in argv:
        print(export(pathlib.Path(arg).expanduser().resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
