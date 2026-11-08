#!/usr/bin/env python3
"""Recount retained records; never rerun a subject, mutate a run, or grade quality."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


def identity(path, repo):
    return {
        "path": str(path.relative_to(repo)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def audit(repo):
    corpus = repo / "docs/experiments/step-plan-review-20261101"
    runs = rows(corpus / "runs.jsonl")
    sends = rows(corpus / "sendbacks.jsonl")
    classes = rows(corpus / "sendback_classes.jsonl")
    if len(sends) != len(classes):
        raise ValueError("Send-back and classification record counts differ")
    unmatched = []
    for entry in classes:
        matches = [
            send for send in sends
            if (send["at"], send["from"], send["item"])
            == (entry["at"], entry["from"], entry["item"])
            and send["trace"].startswith(entry["run"].rstrip("/") + "/")
        ]
        if len(matches) != 1:
            unmatched.append(entry["n"])
    if unmatched:
        raise ValueError(f"Missing or ambiguous record matches: {unmatched}")
    traces = []
    for run in runs:
        path = Path(run["trace"]).expanduser()
        exists = path.is_file()
        traces.append({
            "path": run["trace"],
            "present": exists,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if exists else None,
        })
    sources = [
        corpus / name for name in (
            "runs.jsonl", "sendbacks.jsonl", "sendback_classes.jsonl", "README.md"
        )
    ] + [repo / path for path in (
        "docs/shiploop-question-driven-planning-journal.md",
        "docs/shiploop-question-record-verdicts-and-plan-2026-10-31.md",
        "docs/shiploop-planning-experiments-results-2026-09-21.md",
        "skills/shiploop/references/planning-experiments.md",
        "skills/shiploop/scripts/shiploop_prompts.py",
        "skills/shiploop/scripts/shiploop_stage_spec.py",
        "skills/improve/runtime/until-loop/ADAPTER.md",
    )]
    return {
        "method": "Recount committed summaries and hash available primary traces; semantic screening is a separate review.",
        "source_head": subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_inputs": [identity(path, repo) for path in sources],
        "summary": {
            "run_records": len(runs),
            "step_plan_actions": sum(len(run["step_plans"]) for run in runs),
            "sendback_records": len(sends),
            "distinct_sendback_traces": len({send["trace"] for send in sends}),
            "sendbacks_by_stage": dict(sorted(Counter(send["from"] for send in sends).items())),
            "sendbacks_by_recorded_class": dict(sorted(Counter(entry["class"] for entry in classes).items())),
            "primary_traces_present": sum(trace["present"] for trace in traces),
            "primary_traces_missing": sum(not trace["present"] for trace in traces),
            "classification_matches": len(classes),
        },
        "traces": traces,
        "limits": [
            "Existing classifications are not a new blinded adjudication.",
            "Trace presence and hashes do not mean every trace was reread semantically.",
            "These are historical mixed-version runs, not trials of current ShipLoop.",
            "Send-back records, actions and independent tasks are different denominators.",
            "No model quality, causal benefit, latency or token improvement is measured.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.repo.resolve())
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
