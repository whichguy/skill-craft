#!/usr/bin/env python3
"""Read-only preregistered campaign accounting. Never launches or retries models."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

from workflow_review import validate_review
from grading import validate_receipt


def read(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _settings(manifest: dict, result: dict, before: dict | None) -> dict:
    initial = {key: before.get(key) for key in ("head", "branch", "status", "index", "files", "skipped", "new_empty_folder")} if before is not None else None
    return {"step_id": result.get("step_id"), "prompt_sha256": manifest.get("prompt_sha256"),
            "model": manifest.get("preflight", {}).get("model_requested"),
            "reasoning_effort": manifest.get("reasoning_effort_requested"),
            "timeout_seconds": manifest.get("timeout_seconds"), "max_turns": manifest.get("max_turns"),
            "permission_mode": manifest.get("permission_mode"), "partial": manifest.get("partial"),
            "stop_after_stage": manifest.get("stop_after_stage"),
            "observer_digest": manifest.get("harness_sha256"),
            "baseline_digest": result.get("baseline_digest"),
            "initial_source_digest": hashlib.sha256(json.dumps(initial, sort_keys=True).encode()).hexdigest() if initial is not None else None}


def summarize(document: dict, base: Path) -> dict:
    """Keep all planned rows and compare settings before comparing outcomes."""
    if document.get("schema") != "shiploop-e2e-campaign/1":
        raise ValueError("unsupported campaign schema")
    arms = document.get("arms")
    if not isinstance(arms, list) or not arms:
        raise ValueError("campaign requires nonempty arms")
    rows = []
    seen_arms: set[str] = set()
    seen_paths: set[Path] = set()
    for arm in arms:
        if not isinstance(arm, dict) or not isinstance(arm.get("id"), str) or not arm["id"] or arm["id"] in seen_arms:
            raise ValueError("arm ids must be nonempty and unique")
        seen_arms.add(arm["id"])
        cases = arm.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ValueError("every arm needs planned cases")
        seen_cases: set[tuple] = set()
        for case in cases:
            if not isinstance(case, dict) or not isinstance(case.get("step_id"), str) or not case["step_id"]:
                raise ValueError("every case needs a step_id")
            repeat = case.get("repetition")
            if type(repeat) is not int or repeat < 1:
                raise ValueError("repetition must be a positive integer")
            key = (case["step_id"], repeat)
            if key in seen_cases:
                raise ValueError("duplicate case/repetition in arm")
            seen_cases.add(key)
            row = {"arm": arm["id"], "step_id": key[0], "repetition": repeat, "status": "not-run",
                   "workflow": {"status": "unverified", "reason": "review not supplied"},
                   "comparability_limits": [], "result": None}
            rows.append(row)
            trial_value = case.get("trial")
            if trial_value is None:
                continue
            if not isinstance(trial_value, str) or not trial_value:
                raise ValueError("trial must be a path or null")
            trial = (base / trial_value).resolve()
            if trial in seen_paths:
                raise ValueError("same trial cannot count as another independent attempt")
            seen_paths.add(trial)
            row["trial"] = str(trial)
            if not (trial / "result.json").exists():
                row["status"] = "missing-result"
                continue
            try:
                result = read(trial / "result.json")
                manifest = read(trial / "manifest.json")
                row["result"] = result.get("statuses", {})
                row["status"] = result.get("statuses", {}).get("overall", "unverified")
                row["evidence_hashes"] = {name: fingerprint(trial / name) for name in ("result.json", "manifest.json")}
                if result.get("step_id") != key[0] or manifest.get("scenario", {}).get("id") != key[0]:
                    raise ValueError("planned step does not match trial")
                if result.get("trial_id") != manifest.get("trial_id"):
                    raise ValueError("result/manifest trial identity mismatch")
                before_path = trial / "before.json"
                before = read(before_path) if before_path.exists() else None
                if before is None:
                    row["comparability_limits"].append("initial source snapshot missing")
                else:
                    row["evidence_hashes"]["before.json"] = fingerprint(before_path)
                row["settings"] = _settings(manifest, result, before)
                expected_settings = {**arm.get("expected_settings", {}), **case.get("expected_settings", {})}
                for field, value in row["settings"].items():
                    if field == "step_id":
                        continue
                    if field not in expected_settings:
                        row["comparability_limits"].append(f"{field} not preregistered")
                    elif expected_settings[field] != value:
                        row["comparability_limits"].append(f"{field} differs from registered setting")
                row["skill_digest"] = result.get("skill_digest")
                if not arm.get("expected_skill_digest"):
                    row["comparability_limits"].append("skill digest not preregistered")
                elif row["skill_digest"] != arm["expected_skill_digest"]:
                    row["comparability_limits"].append("skill differs from registered arm")
                if result.get("skill_stable") is not True:
                    row["comparability_limits"].append("skill stability unverified")
                if result.get("observer_stable") is not True:
                    row["comparability_limits"].append("observer stability unverified")
                if result.get("diagnostic"):
                    row["comparability_limits"].append("diagnostic baseline")
                if result.get("partial"):
                    row["comparability_limits"].append("partial observation")
                row["duration_seconds"] = result.get("process", {}).get("duration_seconds")
                row["reported_terminal_usage"] = result.get("audit", {}).get("usage", {}).get("reported_terminal_usage")
                row["candidate_digest"] = result.get("candidate_digest")
                row["verifier_identity"] = result.get("grade", {}).get("verifier")
                receipt_path = trial / "verification.json"
                if receipt_path.exists():
                    receipt = read(receipt_path)
                    row["verifier_identity"] = receipt.get("verifier")
                    row["verifier_inputs_sha256"] = receipt.get("verifier_inputs_sha256")
                    row["receipt_sha256"] = fingerprint(receipt_path)
                    required = manifest.get("scenario", {}).get("required_checks")
                    if (result.get("required_checks") != required or not isinstance(required, list)
                            or not result.get("candidate_digest")):
                        row["comparability_limits"].append("receipt requirements/bindings incomplete")
                    else:
                        grade = validate_receipt(receipt, trial_id=result["trial_id"], candidate_digest=result["candidate_digest"],
                                                 baseline_digest=result.get("baseline_digest"), required_checks=required,
                                                 evidence_root=trial / "verification")
                        row["receipt_revalidation"] = {"receipt_valid": grade["receipt_valid"], "product_status": grade["product_status"]}
                        if not grade["receipt_valid"]:
                            row["comparability_limits"].append("receipt evidence/binding invalid")
                        grade_path = trial / "grade.json"
                        if not grade_path.exists() or read(grade_path) != grade:
                            row["comparability_limits"].append("saved grade missing or differs from current validation")
                        if row["status"] == "passed" and grade["product_status"] != "passed":
                            row["comparability_limits"].append("recorded pass contradicts receipt")
                else:
                    row["comparability_limits"].append("verification receipt missing")
                if not row["verifier_identity"]:
                    row["comparability_limits"].append("verifier identity missing")
                if not row.get("verifier_inputs_sha256"):
                    row["comparability_limits"].append("verifier source/configuration digest missing")
                for field in ("verifier_identity", "verifier_inputs_sha256"):
                    if field not in expected_settings:
                        row["comparability_limits"].append(f"{field} not preregistered")
                    elif expected_settings[field] != row.get(field):
                        row["comparability_limits"].append(f"{field} differs from registered setting")
                review_value = case.get("workflow_review")
                if review_value:
                    review_path = (base / review_value).resolve()
                    row["workflow"] = validate_review(read(review_path), result, review_path.parent)
                    row["workflow"]["review_sha256"] = fingerprint(review_path)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                row["status"] = "invalid-record"
                row["comparability_limits"].append(str(exc))
    arm_rows = []
    for arm in arms:
        members = [row for row in rows if row["arm"] == arm["id"]]
        durations = [row["duration_seconds"] for row in members if type(row.get("duration_seconds")) in (int, float)]
        arm_rows.append({"id": arm["id"], "selected": len(members),
                         "statuses": dict(sorted(Counter(row["status"] for row in members).items())),
                         "workflow_statuses": dict(sorted(Counter(row["workflow"]["status"] for row in members).items())),
                         "median_observed_seconds": statistics.median(durations) if durations else None})
    by_pair: dict[tuple, list] = defaultdict(list)
    for row in rows:
        by_pair[(row["step_id"], row["repetition"])].append(row)
    pairs = []
    for (step, repeat), members in sorted(by_pair.items()):
        limits = sorted({limit for row in members for limit in row["comparability_limits"]})
        if len(members) != len(arms) or len(arms) < 2:
            limits.append("no complete cross-arm pair")
        if any("settings" not in row for row in members):
            limits.append("planned attempt missing")
        else:
            fields = set(members[0]["settings"])
            for field in sorted(fields):
                values = [json.dumps(row["settings"][field], sort_keys=True) for row in members]
                if len(set(values)) != 1:
                    limits.append(f"different {field}")
                elif field not in {"baseline_digest", "stop_after_stage"} and members[0]["settings"][field] is None:
                    limits.append(f"missing {field}")
            if len({row.get("verifier_identity") for row in members}) != 1:
                limits.append("different verifier identity")
            if len({row.get("verifier_inputs_sha256") for row in members}) != 1:
                limits.append("different verifier source/configuration digest")
        if any(row["workflow"]["status"] in {"unverified", "invalid"} for row in members):
            limits.append("workflow review incomplete")
        pairs.append({"step_id": step, "repetition": repeat, "status": "descriptive-only" if limits else "settings-matched",
                      "limits": limits, "arms": [row["arm"] for row in members]})
    return {"schema": "shiploop-e2e-campaign-report/1", "arms": arm_rows, "attempts": rows, "pairs": pairs,
            "selected": len(rows), "counted": sum(sum(arm["statuses"].values()) for arm in arm_rows),
            "note": "No automatic winner. Settings-matched pairs still need effect-size, repetition and semantic review; sequential features are not replications. Original trial records are unchanged."}


def markdown(report: dict) -> str:
    lines = ["# ShipLoop campaign observations", "", report["note"], "",
             "| Arm | Step | Repetition | Recorded outcome | Workflow review |", "| --- | --- | ---: | --- | --- |"]
    for row in report["attempts"]:
        values = [str(row[key]).replace("|", "\\|").replace("\n", " ") for key in ("arm", "step_id", "repetition", "status")]
        lines.append("| " + " | ".join(values + [row["workflow"]["status"]]) + " |")
    lines.extend(["", f"Selected {report['selected']}; counted {report['counted']}. Missing attempts remain in the denominator.", "",
                  "See campaign-report.json for fingerprints, comparability limits, duration, and terminal usage.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new; prior comparisons are retained")
    report = summarize(read(args.manifest), args.manifest.resolve().parent)
    report["manifest_sha256"] = fingerprint(args.manifest)
    args.output.mkdir(parents=True)
    (args.output / "campaign-report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "REPORT.md").write_text(markdown(report))
    print(json.dumps({"selected": report["selected"], "counted": report["counted"], "report": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
