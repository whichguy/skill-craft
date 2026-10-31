#!/usr/bin/env python3
"""SG2 smoke, 2026-10-31: what the nine slices show, exported compactly to sg2-smoke-20261031.json beside this file.

    python3 docs/experiments/sdlc-gates-20261030/sg2_smoke_export.py [OUT]       # default ~/e2e-runs/sg2-20261031

One record per sample, read from the run folders and judged by nothing here: the score (value, seconds, the scorer's
`improve_fix_commits`), the carry-forward Improve review (its class and its `Changed:` line), the commits after the seed,
the product files changed after the step's own commit, and the lines the step's commit message gives as its learning and
decision. `counted_commits` are the commits `sg2_recall.py` counted as Improve fix commits, so the column can be checked
against the commits themselves. The summary adds what the records decide: how many samples scored 1, how many reviews
changed anything, and minutes per slice by arm.
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parents[2] / "test" / "shiploop_e2e"
sys.path.insert(0, str(HARNESS / "evaluators"))
sys.path.insert(0, str(HARNESS))
import common
import e5_regression

DEFAULT_OUT = Path.home() / "e2e-runs" / "sg2-20261031"


def git(tree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, check=False).stdout


def line_after(message: str, heading: str) -> str | None:
    found = re.search(rf"^{heading}:\n- (.*)$", message, re.MULTILINE)
    return found.group(1) if found else None


def record(out: Path, score_path: Path) -> dict:
    score = json.loads(score_path.read_text())
    sample = score_path.parent
    invocation = json.loads((sample / "slice" / "invocation.json").read_text())
    tree = common.worktree(sample / "slice")
    start = invocation["seeded"]["start_head"]
    subjects = git(tree, "log", "--reverse", "--format=%h %s", f"{start}..HEAD").splitlines()
    step = next((line.split()[0] for line in subjects if " feat(" in line), None)
    after = git(tree, "diff", "--name-only", f"{step}..HEAD").split() if step else []
    message = git(tree, "show", "-s", "--format=%B", step) if step else ""
    reviews = sorted(tree.glob(".shiploop-improve/carry-forward-*/reviews/review-*.md"))
    first = reviews[0].read_text() if reviews else ""
    klass = re.search(r"^classification:\s*(\S+)", first, re.MULTILINE)
    changed = re.search(r"^Changed:\s*(.*)$", first, re.MULTILINE)
    return {
        "sample": f"{score['experiment']}/{score['arm']}/{score['sample']}", "case": invocation["case"],
        "delegation": invocation["delegation"], "value": score["value"], "slice_pass": score["slice_pass"],
        "seconds": score["seconds"], "improve_fix_commits": score["improve_fix_commits"],
        "counted_commits": [row["sha"][:7] + " " + git(tree, "log", "-1", "--format=%s", row["full"]).strip()
                            for row in e5_regression.fix_commits(tree, start)],
        "commits": subjects,
        "product_files_changed_after_step_commit": [p for p in after if not p.startswith("docs/shiploop/")],
        "carry_forward_review": {"reviews": len(reviews), "class": klass.group(1) if klass else None,
                                 "changed": changed.group(1) if changed else None},
        "step_commit_learned": line_after(message, "Key learnings"),
        "step_commit_decision": line_after(message, "Key decisions"),
    }


def main(argv: list[str]) -> int:
    out = Path(argv[1]).expanduser() if len(argv) > 1 else DEFAULT_OUT
    rows = [record(out, path) for path in sorted(out.glob("SG2-K*/*/*/score.json"))]
    minutes = {arm: [r["seconds"] / 60 for r in rows if r["delegation"] == name]
               for arm, name in (("A", "inline"), ("B", "ask-agent"))}
    summary = {
        "samples": len(rows), "scored_1": sum(r["value"] == 1 for r in rows),
        "reviews_by_class": {k: sum(r["carry_forward_review"]["class"] == k for r in rows)
                             for k in sorted({r["carry_forward_review"]["class"] for r in rows}, key=str)},
        "samples_with_a_product_file_changed_after_the_step_commit":
            sum(bool(r["product_files_changed_after_step_commit"]) for r in rows),
        "samples_where_improve_fix_commits_counted_the_step_commit":
            sum(any(" feat(" in c for c in r["counted_commits"]) for r in rows),
        "minutes_per_slice": {arm: {"n": len(v), "mean": round(statistics.mean(v), 2), "min": round(min(v), 2),
                                    "max": round(max(v), 2)} for arm, v in minutes.items() if v},
    }
    target = HERE / "sg2-smoke-20261031.json"
    target.write_text(json.dumps({"source": "~/e2e-runs/sg2-20261031", "summary": summary, "samples": rows},
                                 indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
