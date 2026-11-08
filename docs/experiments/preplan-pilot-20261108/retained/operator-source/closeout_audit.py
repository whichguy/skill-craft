"""Verify retained study evidence; never alter a subject or judge result."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

from analyze import document

ROOT = Path(__file__).resolve().parent.parent
OP = ROOT / "operator"
SUITE = ROOT / "source/docs/experiments/preplan-pilot-20261108"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value, str):
        yield value
        try:
            nested = json.loads(value)
        except ValueError:
            nested = None
        if isinstance(nested, (dict, list)):
            yield from strings(nested)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def normalized(text):
    return re.sub(r"\s+", " ", text).strip()


def judge_checks(path):
    call = json.loads(path.read_text())
    argv = call["argv"]
    return {
        "success": call.get("exit") == 0 and bool(call.get("text")),
        "astra_xhigh": call["spec"] == "codex:gpt-6-astra@xhigh"
        and argv[argv.index("-m") + 1] == "gpt-6-astra"
        and 'model_reasoning_effort="xhigh"' in argv,
        "no_tools_or_outside_access": call.get("tool_items") == []
        and call.get("outside") == [],
        "prompt_hash_matches": digest(path.parent / "prompt.txt")
        == call["prompt_sha256"],
        "stdin_transport": call["transport"] == "codex-stdin-v2" and argv[-1] == "-",
    }


def run():
    manifest = json.loads((OP / "manifest.json").read_text())
    analysis = json.loads((OP / "analysis.json").read_text())
    indexed = {row["id"]: row for row in analysis["rows"]}
    scope = json.loads((OP / "scope-audit-findings.json").read_text())
    deviations = {item["sample"] for item in scope["findings"]}
    result = {
        "scope": "Mechanical evidence validity, separate from outcome judgment",
        "frozen_suite_unchanged": {
            name: digest(SUITE / name) == value
            for name, value in manifest["suite_files"].items()
        },
        "cells": [],
        "pairs": [],
        "pending": [],
        "scope_deviation_samples": sorted(deviations),
        "scope_audit_complete": set(scope["checked"]) == {c["id"] for c in manifest["cells"]},
    }
    for cell in manifest["cells"]:
        name = cell["id"]
        graded = OP / "graded" / name
        out = Path(cell["out"])
        required = [
            OP / (name + "-complete.json"),
            graded / "judge.json",
            out / "slice-result.json",
        ]
        if any(not p.exists() for p in required):
            result["pending"].append(name)
            continue
        row = indexed[name]
        meta = json.loads((graded / "metadata.json").read_text())
        invocation = json.loads((out / "invocation.json").read_text())
        sliced = json.loads((out / "slice-result.json").read_text())
        fixture = SUITE / "fixtures" / cell["case"]
        fixture_mismatches = []
        for expected_file in sorted(fixture.rglob("*")):
            if not expected_file.is_file() or "__pycache__" in expected_file.parts:
                continue
            relative = str(expected_file.relative_to(fixture))
            observed = subprocess.run(
                ["git", "-C", sliced["worktree"], "show", invocation["seeded"]["start_head"] + ":" + relative],
                capture_output=True,
            )
            if observed.returncode or observed.stdout != expected_file.read_bytes():
                fixture_mismatches.append(relative)
        checks = {
            "runner_success": row["attempt"]["exit"] == 0 and sliced["pass"],
            "real_plan_improve_completion": meta["completion"]
            and meta["runtime_executed"]
            and meta["plan_count"] == 1
            and all(
                receipt["runtime_phase"] == "complete"
                and receipt["archived_terminal_exists"]
                and receipt["terminal_hash_matches"]
                for receipt in meta["receipt_checks"]
            ),
            "stop_boundary": sliced["stage_at_stop"] == "prepare"
            and sliced["stop_after"] == "plan"
            and sliced["overshoot"] == [],
            "plugin_identity": row["plugin_identity_matches"],
            "sol_high": invocation["model"] == "gpt-6.1-sol"
            and invocation["effort"] == "high"
            and bool(meta["host_commands"])
            and all(
                "-m gpt-6.1-sol " in command
                and "model_reasoning_effort=high " in command
                for command in meta["host_commands"]
            ),
            "source_freeze": invocation["local_head"] == manifest["source_commit"],
            "initial_fixture_identity": not fixture_mismatches,
            "individual_criterion_set": row.get("criterion_set_valid") is True,
            "individual_criterion_quotes": row.get("quote_failures") == [],
            "no_heuristic_access_findings": row["access_audit_findings"] == [],
        }
        checks.update({"judge_" + k: v for k, v in judge_checks(graded / "judge.json").items()})
        result["cells"].append({"id": name, "checks": checks, "fixture_mismatches": fixture_mismatches})
    for case in manifest["registration"]["cases"]:
        for rep in range(1, 3):
            name = f"{case}-{rep}"
            directory = OP / "pairs" / name
            if not (directory / "judge.json").exists():
                result["pending"].append(name)
                continue
            call = json.loads((directory / "judge.json").read_text())
            judgment = document(call["text"])
            pair = json.loads((directory / "prompt.txt").read_text().split("\nPAIR EVIDENCE\n", 1)[1])
            evidence = {
                side: normalized("\n".join(strings({k: v for k, v in arm.items() if k != "individual_judgment"})))
                for side, arm in pair.items()
            }
            failed_quotes = [
                item for item in judgment["decisive_evidence"]
                if normalized(item["quote"]) not in evidence[item["side"]]
            ]
            mapping = json.loads((directory / "mapping.json").read_text())
            expected = {c["id"] for c in manifest["cells"] if c["case"] == case and c["rep"] == rep}
            checks = judge_checks(directory / "judge.json")
            checks.update(
                quotes_match_own_side=not failed_quotes,
                mapping_matches_pair=set(mapping.values()) == expected and set(mapping) == {"A", "B"},
                outcome_valid=judgment["final_quality"] in {"A_better", "B_better", "tie", "inconclusive"},
            )
            result["pairs"].append({
                "id": name,
                "checks": checks,
                "quote_findings": failed_quotes,
                "clean_comparison_eligible": not (expected & deviations),
                "scope_deviation_samples": sorted(expected & deviations),
            })
    result["failed"] = [
        {"id": row["id"], "checks": [k for k, v in row["checks"].items() if not v]}
        for row in result["cells"] + result["pairs"] if not all(row["checks"].values())
    ]
    result["complete"] = not result["pending"] and len(result["cells"]) == 16 and len(result["pairs"]) == 8
    result["pass"] = result["complete"] and not result["failed"] and all(result["frozen_suite_unchanged"].values()) and result["scope_audit_complete"]
    result["pass_meaning"] = "Mechanical evidence accounting passed; scope deviations remain explicit exclusions from the clean comparative subset, never erased by this result."
    result["limits"] = [
        "Requested model and effort are verified from launch controls; served identity is not independently exposed.",
        "Transcript access scan is heuristic, not an OS read fence or proof against computed paths.",
        "Matching receipts establish execution/completion provenance, not truth of every subject or judge claim.",
        "Quote checks ignore whitespace only and decode retained nested JSON stdout.",
    ]
    (OP / "closeout-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("complete", "pass", "failed", "pending")}, indent=2))
    if "--require-complete" in sys.argv and not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
