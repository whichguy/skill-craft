"""Qualified, condition-matched comparisons for retained ShipLoop E2E runs."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time

import evidence


CONDITION_FIELDS = (
    "host", "model", "effort", "case_digest", "evaluator_digest", "inputs_digest",
    "environment", "budget", "concurrency", "dependency_digest",
)
IDENTITY_FIELDS = ("invocation_id", "subject_digest", "evaluator_digest", "case_digest")
JUDGE_IDENTITY_FIELDS = ("host", "model", "effort", "prompt_digest", "evaluator_digest", "control_digest")
LOWER_IS_BETTER = ("cost", "turn", "time", "duration", "session", "cancel", "glue", "failure", "attempt")
HIGHER_IS_BETTER = ("pass", "delivery", "coverage", "verified", "success")


def _present(value) -> bool:
    return value is not None and not (isinstance(value, str) and not value.strip())


def _identity_conditions(value: dict | None) -> dict | None:
    """Return shared conditions, excluding the intentionally changing subject."""
    if not isinstance(value, dict):
        return None
    missing = [key for key in CONDITION_FIELDS if key not in value or
               (key != "effort" and not _present(value.get(key)))]
    if missing:
        return None
    return {key: value[key] for key in CONDITION_FIELDS}


def _conditions(row: dict) -> dict | None:
    value = row.get("comparison")
    if isinstance(value, dict):
        identity = _identity_conditions(value)
        if identity is not None:
            return identity
    return _identity_conditions(row.get("comparison_identity"))


def _qualification(row: dict) -> tuple[bool, str | None, str | None]:
    qualification = row.get("qualification")
    if not isinstance(qualification, dict):
        return False, None, "qualification is missing or malformed"
    status, scope = qualification.get("status"), qualification.get("scope")
    if status != "qualified":
        return False, scope if isinstance(scope, str) else None, f"qualification status is {status!r}"
    if scope not in {"candidate", "release"}:
        return False, None, "qualification scope is missing or unsupported"
    return True, scope, None


def _judge_identity(row: dict) -> dict | None:
    identity = row.get("review_identity")
    if not isinstance(identity, dict) or any(key not in identity or
            (key != "effort" and not _present(identity[key])) for key in JUDGE_IDENTITY_FIELDS):
        return None
    return {key: identity[key] for key in JUDGE_IDENTITY_FIELDS}


def _valid_run_identity(row: dict, conditions: dict) -> tuple[bool, str | None]:
    identity = row.get("identity")
    if not isinstance(identity, dict) or any(not _present(identity.get(key)) for key in IDENTITY_FIELDS):
        return False, "run identity is missing or incomplete"
    if identity.get("evaluator_digest") != conditions["evaluator_digest"]:
        return False, "run evaluator identity does not match comparison conditions"
    if identity.get("case_digest") != conditions["case_digest"]:
        return False, "run case identity does not match comparison conditions"
    comparison = row.get("comparison")
    recorded_subject = comparison.get("subject_digest") if isinstance(comparison, dict) else None
    if _present(recorded_subject) and recorded_subject != identity.get("subject_digest"):
        return False, "subject identity is inconsistent within the retained row"
    return True, None


def baseline_row(result: dict, style: str | None, suite: str | None) -> dict:
    """Preserve established history fields and append comparison evidence."""
    metrics = result.get("metrics") or {}
    versions = result.get("versions") or {}
    conditions = result.get("comparison") if isinstance(result.get("comparison"), dict) else None
    checks = result.get("checks") if isinstance(result.get("checks"), list) else []
    known_check_failures = sum(isinstance(check, dict) and check.get("pass") is False for check in checks)
    return {
        "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "case": result.get("case"),
        "style": style, "suite": suite, "source": versions.get("source"),
        "plugin_version": versions.get("plugin_version"), "shiploop_version": versions.get("shiploop_version"),
        "pass": result.get("pass"),
        "verdicts": {key: (result.get(key) or {}).get("pass") for key in
                     ("invoked", "plugin", "process", "shiploop", "committed")},
        "checks_passed": sum(bool(check.get("pass")) for check in result.get("checks") or []),
        "checks": len(result.get("checks") or []),
        "mandatory_check_failures": known_check_failures,
        "turns": metrics.get("turns"), "cost_usd": metrics.get("cost_usd"),
        "cost_status": metrics.get("cost_status"),
        "cost_known_subtotal_usd": metrics.get("cost_known_subtotal_usd"),
        "sessions": len((result.get("process") or {}).get("sessions") or []),
        "cancelled_tool_calls": metrics.get("cancelled_tool_calls"), "model_glue": metrics.get("model_glue"),
        "tmp_writes": metrics.get("tmp_writes"), "shiploop_failures": metrics.get("shiploop_failures"),
        "compactions": metrics.get("compactions"), "truncated_outputs": metrics.get("truncated_outputs"),
        "narrative": metrics.get("narrative"), "output": result.get("output"),
        "status": result.get("status"),
        "evidence_status": (result.get("evidence") or {}).get("status")
        if isinstance(result.get("evidence"), dict) else None,
        "evidence_reasons": (result.get("evidence") or {}).get("reasons")
        if isinstance(result.get("evidence"), dict) else None,
        "criteria": result.get("criteria"),
        "skipped_reason": result.get("skipped_reason") or result.get("reason"),
        "process": {"pass": (result.get("process") or {}).get("pass"),
                    "sessions": (result.get("process") or {}).get("sessions") or []},
        "host": conditions.get("host") if conditions else None,
        "model": conditions.get("model") if conditions else None,
        "effort": conditions.get("effort") if conditions else None,
        "comparison": conditions, "comparison_identity": _identity_conditions(conditions),
        "identity": result.get("identity"), "qualification": result.get("qualification"),
        "review_identity": result.get("review_identity"),
        "review_validity_pass": result.get("review_validity_pass"),
        "review_calibration_pass": result.get("review_calibration_pass"),
        "review_process_pass": result.get("review_process_pass"),
        "review_schema_valid": result.get("review_schema_valid"),
        "review_qualification_reasons": result.get("review_qualification_reasons"),
    }


def previous_row(path: Path, case: str, source: str | None, conditions: dict | None = None) -> dict | None:
    """Find a same-case row only when its complete condition identity matches."""
    path = Path(path)
    expected = _identity_conditions(conditions)
    if expected is None or not path.is_file():
        return None
    found = None
    for line in path.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict) or row.get("case") != case or row.get("source") != source:
            continue
        if expected is not None and _conditions(row) != expected:
            continue
        found = row
    return found


def _metric_value(row: dict, name: str):
    parts = name.split(".")
    for source in (row, row.get("metrics")):
        value = source
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                break
            value = value[part]
        else:
            return value
    return None


def _direction(name: str, requested: str | None) -> str | None:
    if requested in {"lower", "higher"}:
        return requested
    lowered = name.lower()
    if any(word in lowered for word in LOWER_IS_BETTER):
        return "lower"
    if any(word in lowered for word in HIGHER_IS_BETTER):
        return "higher"
    return None


def _row_pass(row: dict) -> bool | None:
    value = row.get("pass")
    return value if isinstance(value, bool) else None


def _inconclusive(reasons: list[str], **fields) -> dict:
    return {"decision": "inconclusive", "reasons": reasons, **fields}


def compare(baseline: dict, candidate: dict, metric: str | dict | None = None,
            threshold: float | None = None) -> dict:
    """Compare two already-validated rows; numeric thresholds are relative benefit fractions."""
    if not isinstance(baseline, dict) or not isinstance(candidate, dict):
        return _inconclusive(["baseline and candidate must be retained row objects"])

    left_conditions, right_conditions = _conditions(baseline), _conditions(candidate)
    if left_conditions is None or right_conditions is None:
        return _inconclusive(["comparison identity or required conditions are missing"])
    if left_conditions != right_conditions:
        return _inconclusive(["comparison conditions differ"])
    for label, row in (("baseline", baseline), ("candidate", candidate)):
        valid, reason = _valid_run_identity(row, left_conditions)
        if not valid:
            return _inconclusive([f"{label}: {reason}"])
    if baseline["identity"].get("invocation_id") == candidate["identity"].get("invocation_id"):
        return _inconclusive(["baseline and candidate identify the same invocation"])

    for field in ("case", "style", "suite"):
        left, right = baseline.get(field), candidate.get(field)
        if left is not None or right is not None:
            if left != right:
                return _inconclusive([f"{field} differs"])

    baseline_qualified, baseline_scope, baseline_reason = _qualification(baseline)
    candidate_qualified, candidate_scope, candidate_reason = _qualification(candidate)
    if not baseline_qualified:
        return _inconclusive([f"baseline: {baseline_reason}"])
    if baseline_scope != candidate_scope:
        return _inconclusive(["qualification scopes differ"])

    baseline_judge, candidate_judge = _judge_identity(baseline), _judge_identity(candidate)
    if baseline_judge is None or candidate_judge is None:
        return _inconclusive(["reviewer calibration identity is missing or incomplete"])
    if baseline_judge != candidate_judge:
        return _inconclusive(["reviewer calibration identities differ; regrade both sides with the same judge"])

    baseline_pass, candidate_pass = _row_pass(baseline), _row_pass(candidate)
    common = {"scope": baseline_scope, "sample_size": 1, "reliability_claim": False}
    if baseline_pass is not True:
        return _inconclusive(["baseline is not a qualified mandatory success"], **common)
    if not candidate_qualified:
        qualification = candidate.get("qualification") if isinstance(candidate.get("qualification"), dict) else {}
        reasons = [f"candidate: {candidate_reason}"]
        known_failures = candidate.get("mandatory_check_failures")
        review_valid = all(candidate.get(key) is True for key in (
            "review_validity_pass", "review_calibration_pass", "review_process_pass", "review_schema_valid"))
        process = candidate.get("process") if isinstance(candidate.get("process"), dict) else {}
        evidence_valid = candidate.get("evidence_status") == "valid"
        if (qualification.get("status") == "unresolved" and candidate_pass is False
                and type(known_failures) is int and known_failures > 0 and review_valid
                and process.get("pass") is True and evidence_valid):
            return {
                "decision": "regressed",
                "reasons": [f"candidate failed {known_failures} mandatory check(s) with valid retained review evidence"],
                "known_mandatory_check_failures": known_failures,
                "unknowns": list(qualification.get("reasons") or []),
                **common,
            }
        reasons.extend(candidate.get("review_qualification_reasons") or qualification.get("reasons") or [])
        if not evidence_valid:
            reasons.append("candidate retained evidence is missing or incomplete")
        if process.get("pass") is not True:
            reasons.append("candidate run process did not complete successfully")
        return _inconclusive(reasons, **common)
    if baseline_scope != candidate_scope:
        return _inconclusive(["qualification scopes differ"])

    if baseline_pass is None or candidate_pass is None:
        return _inconclusive(["mandatory outcome is missing"], **common)
    if baseline_pass and not candidate_pass:
        return {"decision": "regressed", "reasons": ["candidate failed a mandatory run gate that baseline passed"],
                **common}
    baseline_verdicts = baseline.get("verdicts") or {}
    candidate_verdicts = candidate.get("verdicts") or {}
    regressed_gates = [key for key, value in baseline_verdicts.items()
                       if value is True and candidate_verdicts.get(key) is False]
    if regressed_gates:
        return {"decision": "regressed", "reasons": ["candidate regressed mandatory gate(s): "
                + ", ".join(sorted(regressed_gates))], **common}
    if (isinstance(baseline.get("checks"), int) and isinstance(candidate.get("checks"), int)
            and baseline["checks"] != candidate["checks"]):
        return _inconclusive(["mandatory check counts differ despite matched evaluator identity"], **common)
    if (isinstance(baseline.get("checks_passed"), int) and isinstance(candidate.get("checks_passed"), int)
            and candidate["checks_passed"] < baseline["checks_passed"]):
        return {"decision": "regressed", "reasons": ["candidate passed fewer mandatory checks than baseline"],
                **common}
    if not baseline_pass and candidate_pass:
        return {"decision": "improved", "reasons": ["candidate passed the mandatory run gates baseline failed"],
                "efficiency_compared": False, **common}
    if not baseline_pass or not candidate_pass:
        return {"decision": "no_demonstrated_change",
                "reasons": ["both rows fail a mandatory run gate; partial work cannot establish improvement"],
                **common}

    if metric is None:
        if threshold is not None:
            return _inconclusive(["a threshold requires a declared target metric"], **common)
        return {"decision": "no_demonstrated_change",
                "reasons": ["mandatory outcomes match and no target metric was declared"], **common}
    if isinstance(metric, dict):
        metric_name = metric.get("name")
        requested_direction = metric.get("direction")
        if threshold is None:
            threshold = metric.get("threshold")
    else:
        metric_name, requested_direction = metric, None
    if not isinstance(metric_name, str) or not metric_name:
        return _inconclusive(["metric name is missing"], **common)
    direction = _direction(metric_name, requested_direction)
    if direction is None:
        return _inconclusive([f"metric direction is not declared for {metric_name!r}"],
                             metric=metric_name, **common)
    if "cost" in metric_name.lower() and any(
            row.get("cost_status") in {"partial", "unknown"} for row in (baseline, candidate)):
        return _inconclusive(["cost is partial or unknown on at least one side"], metric=metric_name, **common)
    before, after = _metric_value(baseline, metric_name), _metric_value(candidate, metric_name)
    if (not isinstance(before, (int, float)) or isinstance(before, bool) or not math.isfinite(before)
            or not isinstance(after, (int, float)) or isinstance(after, bool) or not math.isfinite(after)):
        return _inconclusive([f"metric {metric_name!r} is missing or non-numeric"], metric=metric_name, **common)
    if threshold is not None and (not isinstance(threshold, (int, float)) or isinstance(threshold, bool)
                                  or not math.isfinite(threshold) or threshold < 0):
        return _inconclusive(["threshold must be a non-negative relative fraction"], metric=metric_name, **common)
    delta = before - after if direction == "lower" else after - before
    benefit = delta / abs(before) if before else None
    if delta < 0:
        decision, reasons = "regressed", [f"candidate worsened the declared {metric_name} metric"]
    elif delta == 0:
        decision, reasons = "no_demonstrated_change", [f"declared {metric_name} metric did not change"]
    elif before == 0:
        return _inconclusive([f"relative benefit for {metric_name!r} is undefined from a zero baseline"],
                             metric=metric_name, direction=direction, baseline_value=before,
                             candidate_value=after, absolute_delta=delta, benefit_fraction=None,
                             threshold=threshold, **common)
    elif threshold is None:
        decision, reasons = "no_demonstrated_change", [
            f"observed {metric_name} benefit has no predeclared acceptance threshold"]
    elif benefit < threshold:
        decision, reasons = "no_demonstrated_change", [
            f"benefit did not meet the declared {threshold:g} relative threshold"]
    else:
        decision, reasons = "improved", [f"candidate met the declared {metric_name} benefit"]
    return {"decision": decision, "reasons": reasons, "metric": metric_name, "direction": direction,
            "baseline_value": before, "candidate_value": after, "absolute_delta": delta,
            "benefit_fraction": benefit,
            "threshold": threshold, **common}


def _attempt_status(row: dict) -> str:
    explicit = row.get("status")
    if explicit in {"failed", "skipped", "unknown", "incomplete", "blocked_preflight",
                    "cancelled", "unsupported", "planned"}:
        return explicit
    if _row_pass(row) is False:
        return "failed"
    qualified, _, _ = _qualification(row)
    if not qualified or _row_pass(row) is not True:
        return "unknown"
    criteria = row.get("criteria") if isinstance(row.get("criteria"), dict) else {}
    kind = criteria.get("kind") or row.get("kind")
    if kind == "delivery":
        return "verified_delivery"
    if kind == "boundary":
        return "verified_boundary"
    if kind == "noop":
        return "verified_noop"
    return "unknown"


def _is_retry(row: dict) -> bool:
    attempt = row.get("attempt")
    return bool(row.get("retry_of") is not None or row.get("resumed") is True or row.get("retry") is True
                or (isinstance(attempt, int) and not isinstance(attempt, bool) and attempt > 1))


def suite_counts(rows: list[dict]) -> dict:
    """Summarize cohorts by unique slots; retries never add denominator trials."""
    cohorts: dict[str, dict] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        cohort = str(row.get("suite") or row.get("cohort") or "unspecified")
        slot = str(row.get("slot_id") or row.get("slot") or row.get("case") or row.get("case_id") or f"row-{index}")
        cohorts.setdefault(cohort, {}).setdefault(slot, []).append(row)

    summary = {}
    outcome_names = ("verified_delivery", "verified_boundary", "verified_noop", "failed", "skipped", "unknown",
                     "incomplete", "blocked_preflight", "cancelled", "unsupported", "planned")
    for cohort, slots in sorted(cohorts.items()):
        required = independent = attempts = retries = resumed = 0
        first_counts = dict.fromkeys(outcome_names, 0)
        latest_counts = dict.fromkeys(outcome_names, 0)
        attempt_counts = dict.fromkeys(outcome_names, 0)
        for attempts_for_slot in slots.values():
            ordered = sorted(enumerate(attempts_for_slot),
                             key=lambda pair: (pair[1].get("attempt") if isinstance(pair[1].get("attempt"), int)
                                               else pair[0] + 1, pair[0]))
            required += any(row.get("required", True) is not False for row in attempts_for_slot)
            attempts += sum(_attempt_status(row) not in {"planned", "skipped", "unsupported", "blocked_preflight"}
                            for _, row in ordered)
            retries += sum(_is_retry(row) for _, row in ordered)
            resumed += sum(row.get("resumed") is True for _, row in ordered)
            for _, row in ordered:
                attempt_counts[_attempt_status(row)] += 1
            independent_rows = [(index, row) for index, row in ordered if not _is_retry(row)]
            first_status = _attempt_status(independent_rows[0][1]) if independent_rows else "unknown"
            independent += any(_attempt_status(row) not in
                               {"planned", "skipped", "unsupported", "blocked_preflight"}
                               for _, row in independent_rows)
            first_counts[first_status] += 1
            latest_counts[_attempt_status(ordered[-1][1])] += 1
        summary[cohort] = {
            "slots": len(slots), "required_slots": required, "started_attempts": attempts,
            "independent_started_trials": independent, "retry_attempts": retries, "resumed_attempts": resumed,
            "first_attempt": first_counts, "latest_attempt": latest_counts, "all_attempts": attempt_counts,
            "verified_deliveries": latest_counts["verified_delivery"],
            "verified_scenarios": latest_counts["verified_boundary"] + latest_counts["verified_noop"],
            "verified_boundary_scenarios": latest_counts["verified_boundary"],
            "verified_noop_scenarios": latest_counts["verified_noop"], "failed_slots": first_counts["failed"],
            "skipped_slots": first_counts["skipped"],
            "unknown_slots": first_counts["unknown"] + first_counts["incomplete"] + first_counts["blocked_preflight"],
            "incomplete_slots": first_counts["incomplete"],
            "blocked_preflight_slots": first_counts["blocked_preflight"],
            "coverage": latest_counts["verified_delivery"] / required if required else None,
        }
    return summary


def _load_object(path: Path) -> dict:
    text = Path(path).read_text()
    try:
        value = json.loads(text)
    except ValueError:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        if not rows:
            raise ValueError(f"no JSON object in {path}")
        value = rows[-1]
    if isinstance(value, list):
        if not value:
            raise ValueError(f"no JSON object in {path}")
        value = value[-1]
    if not isinstance(value, dict):
        raise ValueError(f"expected a result or row object in {path}")
    return value


def _row_for_cli(value: dict) -> dict:
    if isinstance(value.get("result"), dict):
        value = value["result"]
    if isinstance(value.get("checks"), int) and "case" in value:
        return value
    if (isinstance(value.get("metrics"), dict) or isinstance(value.get("versions"), dict)
            or isinstance(value.get("checks"), list)):
        return baseline_row(value, value.get("style"), value.get("suite"))
    return value


def _overlay_review(row: dict, result_path: Path, review_path: Path) -> tuple[dict, list[str]]:
    errors = []
    result = dict(row)
    try:
        review = _load_object(review_path)
    except (OSError, ValueError) as exc:
        return result, [f"review unavailable: {exc}"]
    if review.get("schema") != "shiploop-e2e-review/1":
        errors.append("review schema is missing or unsupported")
    if review.get("identity") != result.get("identity"):
        errors.append("review identity does not match retained result")
    if not isinstance(review.get("validity"), dict) or review["validity"].get("pass") is not True:
        errors.append("review validity did not pass")
    review_process = review.get("process")
    if not isinstance(review_process, dict) or review_process.get("status") != "exited" \
            or type(review_process.get("returncode")) is not int or review_process.get("returncode") != 0:
        errors.append("reviewer process did not exit successfully")
    elif (not isinstance(review_process.get("capture_errors"), list) or review_process["capture_errors"]
          or review_process.get("cleanup_error") not in (None, "")):
        errors.append("reviewer process capture or cleanup reported errors")
    calibration = review.get("judge_calibration")
    if not isinstance(calibration, dict) or calibration.get("status") != "passed":
        errors.append("judge calibration did not pass")
    elif _judge_identity({"review_identity": calibration.get("identity")}) is None:
        errors.append("judge calibration identity is missing or incomplete")
    if not isinstance(result.get("process"), dict) or result["process"].get("pass") is not True:
        errors.append("retained run process did not pass")
    output = result_path.parent if result_path.name == "result.json" else Path(result.get("output") or result_path.parent)
    seal_errors = evidence.verify_seal(output)
    if seal_errors:
        errors.extend(f"evidence seal: {reason}" for reason in seal_errors)
    if "seal_digest_after" in review:
        current_seal = evidence.tree_digest(output / "evidence-seal.json")
        if review.get("seal_digest_after") != current_seal:
            errors.append("review seal digest does not match the current evidence seal")
    qualification = review.get("qualification")
    if (not isinstance(qualification, dict) or not isinstance(qualification.get("status"), str)
            or not qualification.get("status") or qualification.get("scope") not in {"candidate", "release"}):
        errors.append("review qualification is missing")
    if not errors:
        result["qualification"] = qualification
        result["review_identity"] = calibration["identity"]
        result["review_validity_pass"] = True
        result["review_calibration_pass"] = True
        result["review_process_pass"] = True
        result["review_schema_valid"] = True
        result["review_qualification_reasons"] = list(qualification.get("reasons") or [])
    return result, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="retained result.json or row file")
    parser.add_argument("candidate", type=Path, help="retained result.json or row file")
    parser.add_argument("--metric", help="target metric, such as cost_usd or turns")
    parser.add_argument("--threshold", type=float, help="minimum relative benefit fraction, e.g. 0.15 for 15 percent")
    parser.add_argument("--baseline-review", type=Path)
    parser.add_argument("--candidate-review", type=Path)
    args = parser.parse_args(argv)
    try:
        baseline_source, candidate_source = _load_object(args.baseline), _load_object(args.candidate)
        errors = []
        if args.baseline_review:
            baseline_source = baseline_source.get("result") if isinstance(baseline_source.get("result"), dict) else baseline_source
            baseline_source, found = _overlay_review(baseline_source, args.baseline, args.baseline_review)
            errors.extend(f"baseline: {reason}" for reason in found)
        if args.candidate_review:
            candidate_source = candidate_source.get("result") if isinstance(candidate_source.get("result"), dict) else candidate_source
            candidate_source, found = _overlay_review(candidate_source, args.candidate, args.candidate_review)
            errors.extend(f"candidate: {reason}" for reason in found)
        baseline, candidate = _row_for_cli(baseline_source), _row_for_cli(candidate_source)
        result = _inconclusive(errors) if errors else compare(baseline, candidate, args.metric, args.threshold)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"decision": "inconclusive", "reasons": [str(exc)]}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
