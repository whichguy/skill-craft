#!/usr/bin/env python3
"""Re-read the 2026-10-16 Backchain workflow study and export what this audit relies on.

Reads only: the study directory (``--study``, default the private harness's
``results/full-workflow-20261016``) and the Backchain sources in this checkout.
Writes one JSON file (``--out``). Never launches a model.

Per run: commands, tokens, wall time, tool-output bytes, the Backchain and Until Loop
instruction files the run's commands name, helper scripts the run wrote, the review
classification of each loop callback and the candidate digest each review saw, the
review gate, and the study's own qualification and workflow errors.
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
DEFAULT_STUDY = Path("/Users/dadleet/src/backchain/results/full-workflow-20261016")
RESOURCE = re.compile(r"resources/(?:backchain|until-loop)/[\w./-]+?\.(?:md|py|json)")
HELPER = re.compile(r"cat > ([\w./-]+\.(?:py|js|mjs))")
# Code the model wrote and ran inline: Python or Node read from a heredoc or a -c / -e string.
INLINE_CODE = re.compile(r"(python3? -(?: |I |B )*-?\s*<<|python3? -c |node -e |node - <<|node <<)")
INSTRUCTIONS = (
    "SKILL.md", "references/convergence.md", "references/technical-lenses.md",
    "references/technical-lens-cards.md", "references/technical-interactions.md",
    "references/dependency-context.md", "references/caller-contract.md",
    "prompts/convergence-review.prompt.md", "prompts/generator.v1.md",
    "prompts/dependency-review.prompt.md", "prompts/elaborator.v1.md",
    "prompts/audit.prompt.md", "prompts/revise.prompt.md",
)
UNTIL_LOOP = ("ADAPTER.md", "references/runtime-ephemeral.md")


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def sizes(base):
    return {name: (base / name).stat().st_size for name in INSTRUCTIONS if (base / name).is_file()}


def run_record(run_dir, qualification):
    meta = load(run_dir / "summary.json")["meta"]
    commands, output_bytes, helpers, inline, named = 0, 0, [], 0, collections.Counter()
    for line in (run_dir / "events.jsonl").read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item", {})
        if event.get("type") != "item.completed" or item.get("type") != "command_execution":
            continue
        commands += 1
        command = item.get("command", "")
        output_bytes += len((item.get("aggregated_output") or "").encode())
        helpers += HELPER.findall(command)
        inline += len(INLINE_CODE.findall(command))
        for resource in set(RESOURCE.findall(command)):
            named[resource] += 1
    artifacts = run_dir / "artifacts"
    contract = load(artifacts / "loop" / "contract.json") or load(artifacts / "loop" / "start.json") or {}
    reviews = []
    for report in sorted(glob.glob(str(artifacts / "loop" / "report*.json"))):
        reviews.append((load(report) or {}).get("classification", "unknown"))
    digests = [hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]
               for p in sorted(glob.glob(str(artifacts / "candidates" / "*.json")))]
    usage = meta["usage"]
    case, arm, rep = run_dir.name.rsplit("-", 2)
    attempt = qualification.get(run_dir.name, {})
    return {
        "run": run_dir.name, "case": case, "arm": arm, "rep": int(rep.lstrip("r")),
        "commands": commands, "tool_output_bytes": output_bytes,
        "input_tokens": usage["input_tokens"], "cached_input_tokens": usage["cached_input_tokens"],
        "uncached_input_tokens": usage["input_tokens"] - usage["cached_input_tokens"],
        "output_tokens": usage["output_tokens"], "wall_seconds": round(meta["elapsed_ms"] / 1000, 1),
        "helper_scripts_written": sorted(set(helpers)),
        "hand_written_code_blocks": len(helpers) + inline,
        "instruction_files_named": dict(sorted(named.items())),
        "required_trivial_reviews": contract.get("required_trivial_reviews"),
        "review_classes": reviews, "reviewed_candidate_digests": digests,
        "qualified": attempt.get("qualified"), "workflow_errors": attempt.get("workflow_errors", []),
        "adjudicated_semantic": attempt.get("adjudicated_semantic"),
    }


def summarize(runs):
    out = {}
    for arm in sorted({r["arm"] for r in runs}):
        rs = [r for r in runs if r["arm"] == arm]
        med = lambda key: statistics.median(r[key] for r in rs)  # noqa: E731
        out[arm] = {
            "runs": len(rs), "qualified": sum(bool(r["qualified"]) for r in rs),
            "median_commands": med("commands"), "median_input_tokens": med("input_tokens"),
            "median_uncached_input_tokens": med("uncached_input_tokens"),
            "median_output_tokens": med("output_tokens"), "median_wall_seconds": med("wall_seconds"),
            "median_tool_output_bytes": med("tool_output_bytes"),
            "median_hand_written_code_blocks": med("hand_written_code_blocks"),
            "range_hand_written_code_blocks": [min(r["hand_written_code_blocks"] for r in rs),
                                               max(r["hand_written_code_blocks"] for r in rs)],
        }
    confirming = found = 0
    for r in runs:
        classes = r["review_classes"]
        for before, after in zip(classes, classes[1:]):
            if before == "trivial":
                confirming += 1
                found += after != "trivial"
    errors = collections.Counter(e for r in runs if not r["qualified"] for e in set(r["workflow_errors"]))
    binding = ("missing exact bound resource", "latest packet resource not retained")
    binding_only = [r["run"] for r in runs if not r["qualified"] and r["workflow_errors"]
                    and all(e.startswith(binding) for e in r["workflow_errors"])]
    return {"by_arm": out,
            "confirming_reviews": {"after_a_trivial_review": confirming, "found_anything": found,
                                   "runs_with_gate_2": sum(r["required_trivial_reviews"] == 2 for r in runs)},
            "disqualifying_workflow_errors": dict(errors.most_common()),
            "disqualified_with_binding_errors_only": binding_only}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--out", type=Path, default=HERE.with_name("audit.json"))
    args = parser.parse_args()
    decision = load(args.study / "decision-analysis.json")
    qualification = {a["attempt"]: a for a in decision["attempts"]}
    runs = [run_record(Path(p), qualification) for p in sorted(glob.glob(str(args.study / "runs" / "*")))
            if os.path.isfile(os.path.join(p, "events.jsonl"))]
    loop = ROOT / "skills/improve/runtime/until-loop"
    report = {
        "schema": "backchain-efficiency-audit/v1",
        "study": str(args.study),
        "study_decision_sha256": hashlib.sha256((args.study / "decision-analysis.json").read_bytes()).hexdigest(),
        "instruction_bytes": {
            "backchain_study_0.6.3": sizes(args.study / "snapshots/current/backchain"),
            "backchain_checkout": sizes(ROOT / "skills/backchain"),
            "until_loop_checkout": {name: (loop / name).stat().st_size for name in UNTIL_LOOP},
        },
        "summary": summarize(runs),
        "runs": runs,
    }
    args.out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()
