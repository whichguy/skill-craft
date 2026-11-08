"""Run unittest behavior tests against isolated public-API implementations."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ORACLE = Path(__file__).resolve().parent
ROOT = ORACLE.parent
SUBJECT = ROOT / "subject"
WORKER = ORACLE / "worker.py"

MUTANT_REQUIREMENTS = {
    "setup_noop": {
        "api_area": "setup",
        "required_behavior": "successful save_setup persists the exact supplied configuration",
    },
    "denied_write": {
        "api_area": "setup",
        "required_behavior": "a denied save_setup leaves configuration unchanged",
    },
    "preconfirmation_write": {
        "api_area": "record",
        "required_behavior": "propose_change does not persist before confirmation",
    },
    "duplicate_replay": {
        "api_area": "record",
        "required_behavior": "confirm replay does not write or increment version again",
    },
    "cancel_still_writes": {
        "api_area": "record",
        "required_behavior": "cancel_change never persists the proposed amount",
    },
    "wrong_persisted_value": {
        "api_area": "record",
        "required_behavior": "confirm_change persists the exact proposed amount",
    },
}
MUTANT_NAMES = tuple(MUTANT_REQUIREMENTS)
BASELINE_NAMES = ("correct", "alternative")
ALL_CANDIDATES = [
    *BASELINE_NAMES,
    *(f"mutant:{name}" for name in MUTANT_NAMES),
]
CLASSIFICATION_EXPECTED = {
    "ordinary_assertion": "assertion_failures",
    "subtest_assertion": "assertion_failures",
    "subtest_error": "invalid",
    "subtest_helper": "assertion_failures",
    "expected_failure": "invalid",
    "ordinary_pass": "pass",
    "subtest_pass": "pass",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract_fingerprints():
    inputs = {
        "contract.txt": SUBJECT / "contract.txt",
        "setup_app.py": SUBJECT / "setup_app.py",
        "change_app.py": SUBJECT / "change_app.py",
    }
    combined = hashlib.sha256()
    for name, path in inputs.items():
        combined.update(name.encode("utf-8"))
        combined.update(b"\0")
        combined.update(path.read_bytes())
        combined.update(b"\0")
    return {
        "contract_txt_sha256": sha256(inputs["contract.txt"]),
        "api_sources_sha256": {
            "setup_app.py": sha256(inputs["setup_app.py"]),
            "change_app.py": sha256(inputs["change_app.py"]),
        },
        "combined_spec_and_api_sha256": combined.hexdigest(),
    }


def fixture_fingerprint():
    digest = hashlib.sha256()
    for path in sorted(
        path for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        and path.relative_to(ROOT).as_posix() != "oracle/hashes.sha256"
    ):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def candidate_files(name):
    files = {
        "setup_app.py": SUBJECT / "setup_app.py",
        "change_app.py": SUBJECT / "change_app.py",
    }
    if name == "alternative":
        folder = ORACLE / "controls" / "alternative"
        return {filename: folder / filename for filename in files}
    if name.startswith("mutant:"):
        mutant = name.split(":", 1)[1]
        if mutant not in MUTANT_REQUIREMENTS:
            raise ValueError(f"unknown mutant: {mutant}")
        folder = ORACLE / "mutants" / mutant
        mutated_file = "setup_app.py" if mutant in {"setup_noop", "denied_write"} else "change_app.py"
        files[mutated_file] = folder / mutated_file
        return files
    if name != "correct":
        raise ValueError(f"unknown candidate: {name}")
    return files


def invoke(candidate, tests):
    with tempfile.TemporaryDirectory(prefix="public-api-fixture-") as temp_name:
        temp = Path(temp_name)
        app_dir = temp / "app"
        test_dir = temp / "tests"
        app_dir.mkdir()
        test_dir.mkdir()
        for filename, source in candidate_files(candidate).items():
            shutil.copyfile(source, app_dir / filename)
        if candidate.startswith("mutant:"):
            mutated = candidate.split(":", 1)[1]
            base_module = "base_setup.py" if mutated in {"setup_noop", "denied_write"} else "base_change.py"
            base_source = SUBJECT / ("setup_app.py" if base_module == "base_setup.py" else "change_app.py")
            shutil.copyfile(base_source, app_dir / base_module)
        test_copy = test_dir / "generated_tests.py"
        shutil.copyfile(tests, test_copy)
        env = {"PYTHONDONTWRITEBYTECODE": "1"}
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(WORKER), str(app_dir), str(test_copy)],
                cwd=temp,
                env=env,
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raw_out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            raw_err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return {
                "status": "invalid",
                "phase": "process",
                "reason": "timeout",
                "raw_stdout": raw_out,
                "raw_stderr": raw_err,
            }
        raw = {
            "returncode": proc.returncode,
            "raw_stdout": proc.stdout,
            "raw_stderr": proc.stderr,
        }
        try:
            output = json.loads(proc.stdout)
        except (json.JSONDecodeError, TypeError):
            return {
                "status": "invalid",
                "phase": "worker",
                "reason": "worker_output_not_json",
                **raw,
            }
        if proc.returncode != 0:
            return {
                "status": "invalid",
                "phase": "worker",
                "reason": "worker_nonzero_exit",
                "worker": output,
                **raw,
            }
        return {**output, **raw}


def _classification(name, output):
    if output["status"] == "invalid":
        return "INVALID"
    if output["status"] == "assertion_failures":
        return "KILLED" if name.startswith("mutant:") else "INVALID"
    if name.startswith("mutant:"):
        return "SURVIVED"
    return "PASS" if output["status"] == "pass" else "INVALID"


def evaluate(tests, candidates=None):
    requested = list(dict.fromkeys(candidates or ALL_CANDIDATES))
    for name in requested:
        if name not in BASELINE_NAMES and not (
            name.startswith("mutant:")
            and name.split(":", 1)[1] in MUTANT_REQUIREMENTS
        ):
            raise ValueError(f"unknown candidate: {name}")

    # Both independently correct implementations are required gates, even if
    # the caller only requested a subset of mutant results.
    results = {}
    for name in BASELINE_NAMES:
        output = invoke(name, tests)
        results[name] = {**output, "classification": _classification(name, output)}

    suite_valid = all(
        results[name]["status"] == "pass" for name in BASELINE_NAMES
    )
    if suite_valid:
        for name in requested:
            if name in BASELINE_NAMES:
                continue
            output = invoke(name, tests)
            result = {**output, "classification": _classification(name, output)}
            result.update(MUTANT_REQUIREMENTS[name.split(":", 1)[1]])
            results[name] = result
    else:
        for name in requested:
            if name in BASELINE_NAMES:
                continue
            mutant_name = name.split(":", 1)[1]
            results[name] = {
                "status": "not_run",
                "reason": "suite_did_not_pass_all_correct_implementations",
                "classification": "INVALID",
                **MUTANT_REQUIREMENTS[mutant_name],
            }

    return {
        "suite_valid": suite_valid,
        "test_sha256": sha256(tests),
        "mutant_requirements": MUTANT_REQUIREMENTS,
        "results": results,
    }


def classification_calibration():
    rows = []
    for filename, expected in CLASSIFICATION_EXPECTED.items():
        path = ORACLE / "classification-controls" / f"{filename}.py"
        runs = {name: invoke(name, path) for name in BASELINE_NAMES}
        observed = {name: output["status"] for name, output in runs.items()}
        rows.append({
            "control": filename,
            "expected": expected,
            "observed": observed,
            "matched": all(value == expected for value in observed.values()),
            "raw": runs,
        })
    return {
        "valid": len(rows) == len(CLASSIFICATION_EXPECTED)
        and all(row["matched"] for row in rows),
        "controls": rows,
    }


def invalid_suite_calibration():
    rows = []
    paths = sorted((ORACLE / "controls").glob("*.py"))
    for path in paths:
        result = evaluate(path, ALL_CANDIDATES)
        baseline_invalid = all(
            result["results"][name]["classification"] == "INVALID"
            for name in BASELINE_NAMES
        )
        mutants_invalid = all(
            result["results"][f"mutant:{name}"]["classification"] == "INVALID"
            for name in MUTANT_NAMES
        )
        rows.append({
            "control": path.stem,
            "suite_valid": result["suite_valid"],
            "both_corrects_rejected": baseline_invalid,
            "mutants_not_counted_as_kills": mutants_invalid,
            "matched": (not result["suite_valid"] and baseline_invalid and mutants_invalid),
            "result": result,
        })
    return {
        "valid": len(rows) == 6 and all(row["matched"] for row in rows),
        "controls": rows,
    }


def skipped_suite_calibration():
    result = evaluate(
        ORACLE / "suite-controls" / "skipped_with_assertion.py",
        ALL_CANDIDATES,
    )
    corrects_invalid = all(
        result["results"][name]["classification"] == "INVALID"
        for name in BASELINE_NAMES
    )
    mutants_invalid = all(
        result["results"][f"mutant:{name}"]["classification"] == "INVALID"
        for name in MUTANT_NAMES
    )
    return {
        "valid": (
            not result["suite_valid"] and corrects_invalid and mutants_invalid
        ),
        "corrects_invalid": corrects_invalid,
        "mutants_not_counted_as_kills": mutants_invalid,
        "result": result,
    }


def alternative_gate_regression_control():
    real_invoke = invoke
    calls = []

    def synthetic_invoke(candidate, tests):
        calls.append(candidate)
        if candidate == "correct":
            return {"status": "pass"}
        if candidate == "alternative":
            return {"status": "assertion_failures"}
        raise AssertionError(f"mutant should not run before the correct gate: {candidate}")

    globals()["invoke"] = synthetic_invoke
    try:
        result = evaluate(SUBJECT / "test_existing.py", ["mutant:setup_noop"])
    finally:
        globals()["invoke"] = real_invoke

    mutant_result = result["results"]["mutant:setup_noop"]
    valid = (
        not result["suite_valid"]
        and result["results"]["correct"]["classification"] == "PASS"
        and result["results"]["alternative"]["classification"] == "INVALID"
        and mutant_result["classification"] == "INVALID"
        and mutant_result["status"] == "not_run"
        and calls == ["correct", "alternative"]
    )
    return {
        "valid": valid,
        "prior_v3_behavior": (
            "Only correct gated suite_valid; an alternative assertion failure "
            "could coexist with suite_valid=true."
        ),
        "v4_behavior": (
            "Both correct and alternative must pass; mutants are not run if either "
            "correct implementation rejects the suite."
        ),
        "probe": {
            "calls": calls,
            "suite_valid": result["suite_valid"],
            "correct": result["results"]["correct"]["classification"],
            "alternative": result["results"]["alternative"]["classification"],
            "mutant": mutant_result["classification"],
            "mutant_status": mutant_result["status"],
        },
    }


def calibration():
    reference = evaluate(ORACLE / "reference_tests.py", ALL_CANDIDATES)
    existing = evaluate(SUBJECT / "test_existing.py", ALL_CANDIDATES)
    invalid_controls = invalid_suite_calibration()
    classification_controls = classification_calibration()
    gate_control = alternative_gate_regression_control()
    skipped_control = skipped_suite_calibration()

    arity_good = evaluate(
        ORACLE / "suite-controls" / "omitted_arguments_good.py",
        ALL_CANDIDATES,
    )
    arity_bad = evaluate(
        ORACLE / "suite-controls" / "omitted_arguments_bad.py",
        ALL_CANDIDATES,
    )
    seed_only = evaluate(
        ORACLE / "suite-controls" / "setup_seed_only_gap.py",
        ALL_CANDIDATES,
    )
    save_behavior = evaluate(
        ORACLE / "suite-controls" / "setup_save_behavior_good.py",
        ALL_CANDIDATES,
    )

    arity_controls_valid = (
        arity_good["suite_valid"]
        and all(arity_good["results"][name]["classification"] == "PASS"
                for name in BASELINE_NAMES)
        and not arity_bad["suite_valid"]
        and all(arity_bad["results"][name]["classification"] == "INVALID"
                for name in BASELINE_NAMES)
        and all(arity_bad["results"][f"mutant:{name}"]["classification"] == "INVALID"
                for name in MUTANT_NAMES)
    )
    seed_controls_valid = (
        seed_only["suite_valid"]
        and seed_only["results"]["mutant:setup_noop"]["classification"] == "SURVIVED"
        and seed_only["results"]["mutant:denied_write"]["classification"] == "SURVIVED"
        and save_behavior["suite_valid"]
        and save_behavior["results"]["mutant:setup_noop"]["classification"] == "KILLED"
        and save_behavior["results"]["mutant:denied_write"]["classification"] == "KILLED"
    )
    reference_mutants_killed = all(
        reference["results"][f"mutant:{name}"]["classification"] == "KILLED"
        for name in MUTANT_NAMES
    )
    existing_gap_observed = all(
        existing["results"][f"mutant:{name}"]["classification"] == "SURVIVED"
        for name in (
            "setup_noop",
            "denied_write",
            "preconfirmation_write",
            "duplicate_replay",
            "cancel_still_writes",
        )
    )

    success = (
        reference["suite_valid"]
        and all(reference["results"][name]["classification"] == "PASS"
                for name in BASELINE_NAMES)
        and reference_mutants_killed
        and existing["suite_valid"]
        and all(existing["results"][name]["classification"] == "PASS"
                for name in BASELINE_NAMES)
        and existing_gap_observed
        and existing["results"]["mutant:wrong_persisted_value"]["classification"] == "KILLED"
        and invalid_controls["valid"]
        and classification_controls["valid"]
        and gate_control["valid"]
        and skipped_control["valid"]
        and arity_controls_valid
        and seed_controls_valid
    )
    receipt = {
        "fixture": "portable-public-api-boundaries-v4",
        "valid": success,
        "fixture_fingerprint": fixture_fingerprint(),
        "contract_fingerprints": contract_fingerprints(),
        "mutant_requirements": MUTANT_REQUIREMENTS,
        "checker_gate_assessment": gate_control,
        "skipped_suite_fail_closed_control": skipped_control,
        "reference_tests": reference,
        "existing_suite_gap_control": existing,
        "invalid_suite_controls": invalid_controls,
        "classification_controls": classification_controls,
        "omitted_argument_controls": {
            "valid_contract": arity_good,
            "bad_envelope_expectation": arity_bad,
            "valid": arity_controls_valid,
        },
        "fixture_seeded_only_controls": {
            "seed_only_false_positive": seed_only,
            "save_behavior_positive": save_behavior,
            "valid": seed_controls_valid,
            "interpretation": (
                "The seed-only suite is deliberately valid but survives both setup "
                "mutants because it never calls save_setup. Save-specific behavior "
                "is checked separately and kills both setup mutants; record mutants "
                "are outside those setup controls' required behavior mapping."
            ),
        },
    }
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", type=Path, default=SUBJECT / "test_existing.py")
    parser.add_argument(
        "--candidates",
        default=None,
        help="comma-separated candidates: correct, alternative, mutant:NAME",
    )
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        help="write JSON result here; calibration output must be outside this fixture",
    )
    args = parser.parse_args()

    if args.calibrate:
        result = calibration()
    else:
        result = evaluate(args.tests.resolve(), args.candidates.split(",") if args.candidates else None)

    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        target = args.output.resolve()
        if target == ROOT or ROOT in target.parents:
            print("--output must be outside the checked fixture", file=sys.stderr)
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized)
    print(serialized, end="")
    if args.calibrate:
        return 0 if result["valid"] else 1
    return 0 if result["suite_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
