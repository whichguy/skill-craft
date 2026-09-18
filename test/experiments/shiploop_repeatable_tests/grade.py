#!/usr/bin/env python3
"""Independent, local-only grader for repeatable-test pilot fixtures.

It never runs a worker tree in place: discovery and every test command run in a
disposable copy.  Results retain raw command output so a later reviewer can
separate a harness fault from a behavioral test failure.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping

from fixtures import CASES, CASE_DATA


DISCOVER = r'''
import json, unittest
from pathlib import Path
root = Path.cwd()
def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite): yield from flatten(item)
        else: yield item
def tags(test):
    method = getattr(test, getattr(test, "_testMethodName", ""), None)
    return sorted(getattr(method, "__shiploop_suites__", getattr(type(test), "__shiploop_suites__", ())))
tests = list(flatten(unittest.TestLoader().discover(str(root), pattern="test_*.py", top_level_dir=str(root))))
print(json.dumps([{"id": test.id(), "tags": tags(test)} for test in tests], sort_keys=True))
'''

EXECUTION_OBSERVER = r'''
import json, runpy, sys, unittest

starts, skips, batches = [], [], []
class ObservedResult(unittest.TextTestResult):
    def startTest(self, test):
        starts.append(test.id())
        super().startTest(test)
    def addSkip(self, test, reason):
        skips.append(test.id())
        super().addSkip(test, reason)
class ObservedRunner(unittest.TextTestRunner):
    resultclass = ObservedResult
    def run(self, test):
        offset = len(starts)
        try:
            return super().run(test)
        finally:
            batches.append(starts[offset:])
unittest.TextTestRunner = ObservedRunner
sys.argv = ["run_tests.py", *sys.argv[1:]]
code = 0
try:
    runpy.run_path("run_tests.py", run_name="__main__")
except SystemExit as error:
    code = error.code if isinstance(error.code, int) else (0 if error.code is None else 1)
finally:
    print("SHIPLOOP_EXECUTION_OBSERVER=" + json.dumps({"starts": starts, "skips": skips, "batches": batches, "exit_code": code}, sort_keys=True))
raise SystemExit(code)
'''

ROUTE_PROBE = '''import unittest
class FullRouteProbe(unittest.TestCase):
    def test_full_executes_discovered_probe(self):
        self.fail("grader route probe")
'''

REASONS = {
    "price-format": "cents must retain two decimal digits",
    "sqlite-catalog": "a duplicate must be rejected without overwriting its existing value",
    "expected-red": "punctuation runs must collapse to one hyphen",
}


def _hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _immutable_bytes(case: str, root: Path) -> dict[str, bytes | None]:
    names = (*CASE_DATA[case]["production"], "SPEC.md")
    snapshot: dict[str, bytes | None] = {}
    for name in names:
        try:
            snapshot[name] = (root / name).read_bytes()
        except OSError:
            snapshot[name] = None
    return snapshot


def _snapshot_hashes(snapshot: Mapping[str, bytes | None]) -> dict[str, str | None]:
    return {name: hashlib.sha256(value).hexdigest() if value is not None else None for name, value in snapshot.items()}


def _fixture(case: str, root: Path) -> Path:
    root = Path(root).resolve()
    candidate = root / "fixtures" / case
    return candidate if candidate.is_dir() else root


def _output(value: Any) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else str(value or "")


def _study(fixture: Path) -> Path:
    return fixture.parents[1] if fixture.parent.name == "fixtures" else fixture.parent


def _run(command: list[str], cwd: Path) -> dict[str, Any]:
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, env=environment, timeout=45)
        return {"command": command, "returncode": result.returncode, "stdout": _output(result.stdout), "stderr": _output(result.stderr), "timed_out": False, "error": None, "elapsed_seconds": round(time.monotonic() - started, 6)}
    except subprocess.TimeoutExpired as error:
        return {"command": command, "returncode": None, "stdout": _output(error.stdout), "stderr": _output(error.stderr), "timed_out": True, "error": "timeout after 45 seconds; partial output is not a passing result", "elapsed_seconds": round(time.monotonic() - started, 6)}
    except OSError as error:
        return {"command": command, "returncode": None, "stdout": "", "stderr": "", "timed_out": False, "error": f"{type(error).__name__}: {error}", "elapsed_seconds": round(time.monotonic() - started, 6)}


def _guarded_run(case: str, cwd: Path, command: list[str], intended: Mapping[str, bytes | None]) -> dict[str, Any]:
    before = _immutable_bytes(case, cwd)
    result = _run(command, cwd)
    after = _immutable_bytes(case, cwd)
    result["immutable_guard"] = {
        "passed": before == intended and after == intended,
        "intended_sha256": _snapshot_hashes(intended),
        "before_sha256": _snapshot_hashes(before),
        "after_sha256": _snapshot_hashes(after),
        "residual_limit": "Endpoint snapshots cannot prove against an in-memory monkeypatch or a transient write restored before command exit; manual source audit remains required.",
    }
    return result


def _guard_passed(result: Mapping[str, Any]) -> bool:
    return bool(result.get("immutable_guard", {}).get("passed"))


def _clone(source: Path, target: Path) -> Path:
    return shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))


def _json_output(result: Mapping[str, Any]) -> Any:
    for line in reversed(str(result["stdout"]).splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            pass
    return None


def _execution_observer(result: Mapping[str, Any]) -> Mapping[str, Any] | None:
    prefix = "SHIPLOOP_EXECUTION_OBSERVER="
    for line in reversed(str(result["stdout"]).splitlines()):
        if line.startswith(prefix):
            try:
                payload = json.loads(line[len(prefix):])
            except json.JSONDecodeError:
                return None
            if isinstance(payload, dict) and all(isinstance(payload.get(name), list) for name in ("starts", "skips", "batches")):
                return payload
    return None


def _ids(result: Mapping[str, Any]) -> list[str]:
    payload = _json_output(result)
    return [row["id"] for row in payload] if isinstance(payload, list) and all(isinstance(row, dict) and isinstance(row.get("id"), str) for row in payload) else []


def _tags(result: Mapping[str, Any]) -> dict[str, set[str]]:
    payload = _json_output(result)
    if not isinstance(payload, list):
        return {}
    return {row["id"]: set(row.get("tags", ())) for row in payload if isinstance(row, dict) and isinstance(row.get("id"), str)}


def _failure_ids(result: Mapping[str, Any]) -> list[str]:
    text = str(result["stdout"]) + "\n" + str(result["stderr"])
    return [match.group(2).strip() for match in re.finditer(r"^(FAIL|ERROR): (.+)$", text, re.MULTILINE)]


def _ran(result: Mapping[str, Any]) -> int:
    values = re.findall(r"Ran (\d+) tests?", str(result["stdout"]) + "\n" + str(result["stderr"]))
    return int(values[-1]) if values else 0


def _ran_counts(result: Mapping[str, Any]) -> list[int]:
    return [int(value) for value in re.findall(r"Ran (\d+) tests?", str(result["stdout"]) + "\n" + str(result["stderr"]))]


def _suite_run(case: str, root: Path, args: list[str], intended: Mapping[str, bytes | None]) -> dict[str, Any]:
    return _guarded_run(case, root, [sys.executable, "-B", "-c", EXECUTION_OBSERVER, *args], intended)


def _execution(result: Mapping[str, Any], ids: list[str], *, repeats: int = 1, reverse: bool = False, expected_order: list[str] | None = None) -> dict[str, Any]:
    observer = _execution_observer(result)
    batches = observer.get("batches", []) if observer else []
    valid_batches = all(isinstance(batch, list) and all(isinstance(ident, str) for ident in batch) for batch in batches)
    starts = [ident for batch in batches for ident in batch] if valid_batches else []
    skipped = observer.get("skips", []) if observer and all(isinstance(ident, str) for ident in observer.get("skips", [])) else []
    expected_counts = Counter(ids)
    membership = len(batches) == repeats and all(Counter(batch) == expected_counts and len(batch) == len(ids) for batch in batches)
    order = True
    if expected_order is not None:
        wanted = list(reversed(expected_order)) if reverse else expected_order
        order = all(batch == wanted for batch in batches)
    unrun = sorted(set(ids).difference(starts))
    passed = _guard_passed(result) and result["error"] is None and valid_batches and membership and order and _ran_counts(result) == [len(ids)] * repeats and not skipped
    return {"passed": passed, "expected_ids": ids, "executed_ids": starts, "batches": batches, "unrun_ids": unrun, "skipped_ids": skipped, "ran_counts": _ran_counts(result), "observer": observer, "run": result}


def _baseline(value: Mapping[str, Any] | Path | str | None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, (Path, str)):
        try:
            return json.loads(Path(value).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return value


def _production_check(case: str, fixture: Path, baseline: Mapping[str, Any] | Path | str | None) -> dict[str, Any]:
    record = _baseline(baseline)
    supplied = record.get("immutable_hashes", record.get("initial_hashes")) if isinstance(record, Mapping) else None
    expected = {Path(name).name: digest for name, digest in supplied.items()} if isinstance(supplied, Mapping) else {}
    required = tuple(CASE_DATA[case]["production"]) + ("SPEC.md",)
    actual = {name: _hash(fixture / name) for name in required}
    passed = bool(expected) and all(actual.get(name) == expected.get(name) for name in required)
    return {"passed": passed, "baseline_supplied": bool(expected), "expected": expected, "actual": actual, "production_unchanged": all(actual.get(name) == expected.get(name) for name in CASE_DATA[case]["production"]), "spec_unchanged": actual.get("SPEC.md") == expected.get("SPEC.md")}


def _selection(case: str, fixture: Path, intended: Mapping[str, bytes | None]) -> dict[str, Any]:
    independent = _guarded_run(case, fixture, [sys.executable, "-B", "-c", DISCOVER], intended)
    listed = _guarded_run(case, fixture, [sys.executable, "-B", "run_tests.py", "--list"], intended)
    ids, tags, declared = _ids(independent), _tags(independent), _json_output(listed)
    suites: dict[str, Any] = {}
    full = set(ids)
    for name in ("focused", "smoke", "full"):
        selected = set(declared.get(name, ())) if isinstance(declared, Mapping) else set()
        expected = full if name == "full" else {ident for ident, values in tags.items() if name in values}
        ordered = [ident for ident in ids if ident in expected]
        proper = selected < full
        justified_equal = selected == full and bool(full) and all(name in values for values in tags.values())
        suites[name] = {"ids": sorted(selected), "expected_ids": sorted(expected), "execution_ids": ordered, "nonzero": bool(selected), "proper_subset": proper, "justified_equivalence": justified_equal, "passed": bool(selected) and selected == expected and (name == "full" or proper or justified_equal)}
    executions = {name: _execution(_suite_run(case, fixture, ["--suite", name], intended), suites[name]["execution_ids"]) for name in ("focused", "smoke")}
    return {"passed": bool(ids) and _guard_passed(independent) and _guard_passed(listed) and independent["returncode"] == 0 and listed["returncode"] == 0 and all(item["passed"] for item in suites.values()) and all(item["passed"] for item in executions.values()), "independent": independent, "list": listed, "discovered_ids": ids, "suites": suites, "executions": executions}


def _sequence(case: str, root: Path, ids: list[str], intended: Mapping[str, bytes | None], *, expected_green: bool) -> dict[str, Any]:
    commands = {
        "full": ["--suite", "full"],
        "repeat": ["--suite", "full", "--repeat", "2"],
        "reverse": ["--suite", "full", "--reverse"],
    }
    output = {name: _suite_run(case, root, command, intended) for name, command in commands.items()}
    full = _execution(output["full"], ids)
    normal_order = full["batches"][0] if full["batches"] else None
    executions = {"full": full, "repeat": _execution(output["repeat"], ids, repeats=2, expected_order=normal_order), "reverse": _execution(output["reverse"], ids, reverse=True, expected_order=normal_order)}
    status = all(result["returncode"] == 0 for result in output.values()) if expected_green else all(result["returncode"] not in (0, None) for result in output.values())
    return {"passed": status and all(item["passed"] for item in executions.values()), "expected_green": expected_green, "status_passed": status, "runs": output, "executions": executions}


def _route(case: str, fixture: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="shiploop-route-") as directory:
        cloned = _clone(fixture, Path(directory) / "fixture")
        probe = cloned / "test_route_probe.py"
        probe.write_text(ROUTE_PROBE, encoding="utf-8")
        intended = _immutable_bytes(case, cloned)
        discovery = _guarded_run(case, cloned, [sys.executable, "-B", "-c", DISCOVER], intended)
        result = _suite_run(case, cloned, ["--suite", "full"], intended)
        probe_id = "test_route_probe.FullRouteProbe.test_full_executes_discovered_probe"
        observed = _execution_observer(result)
        passed = _guard_passed(discovery) and _guard_passed(result) and probe_id in _ids(discovery) and result["returncode"] != 0 and observed is not None and probe_id in observed["starts"] and _ran(result) > 0
        return {"passed": passed, "probe_id": probe_id, "discovery": discovery, "full": result}


def _reference_root(case: str, fixture: Path, target: Path, variant: str) -> Path:
    cloned = _clone(fixture, target)
    source = _study(fixture) / "calibration" / case / variant
    for name in CASE_DATA[case]["production"]:
        shutil.copy2(source / name, cloned / name)
    return cloned


def _behavioral_failure(result: Mapping[str, Any]) -> tuple[bool, list[str]]:
    ids = _failure_ids(result)
    text = str(result["stdout"]) + "\n" + str(result["stderr"])
    bad = any("_FailedTest" in ident for ident in ids) or "SyntaxError" in text or "ImportError" in text
    return bool(ids) and not bad, ids


def calibrate(case: str, root: Path) -> dict[str, Any]:
    """Check a fixed reference, weak starter, and single known mutant outside workers."""
    fixture = _fixture(case, root)
    calibration = _study(fixture) / "calibration" / case
    with tempfile.TemporaryDirectory(prefix="shiploop-calibrate-") as directory:
        directory = Path(directory)
        reference = _reference_root(case, fixture, directory / "reference", "reference")
        mutant = _reference_root(case, fixture, directory / "mutant", "mutant")
        shutil.copy2(calibration / "test_reference.py", reference / "test_reference.py")
        mutant_reference = _clone(reference, directory / "mutant-reference")
        for name in CASE_DATA[case]["production"]:
            shutil.copy2(calibration / "mutant" / name, mutant_reference / name)
        reference_intended = _immutable_bytes(case, reference)
        mutant_intended = _immutable_bytes(case, mutant)
        mutant_reference_intended = _immutable_bytes(case, mutant_reference)
        outputs = {
            "reference": _guarded_run(case, reference, [sys.executable, "-B", "-m", "unittest", "-v", "test_reference"], reference_intended),
            "weak_starter_reference": _guarded_run(case, reference, [sys.executable, "-B", "-m", "unittest", "-v", "test_starter"], reference_intended),
            "weak_starter_mutant": _guarded_run(case, mutant, [sys.executable, "-B", "-m", "unittest", "-v", "test_starter"], mutant_intended),
            "reference_mutant": _guarded_run(case, mutant_reference, [sys.executable, "-B", "-m", "unittest", "-v", "test_reference"], mutant_reference_intended),
        }
    failure, ids = _behavioral_failure(outputs["reference_mutant"])
    passed = all(_guard_passed(output) for output in outputs.values()) and outputs["reference"]["returncode"] == 0 and outputs["weak_starter_reference"]["returncode"] == 0 and outputs["weak_starter_mutant"]["returncode"] == 0 and outputs["reference_mutant"]["returncode"] != 0 and failure
    return {"passed": passed, "reason": REASONS[case], "reference_mutant_failure_ids": ids, "runs": outputs}


def grade(case: str, root: Path, baseline: Mapping[str, Any] | Path | str | None = None) -> dict[str, Any]:
    """Grade one worker result without modifying its fixture directory."""
    if case not in CASES:
        raise ValueError(f"unknown case {case!r}")
    fixture = _fixture(case, root)
    source_before = _production_check(case, fixture, baseline)
    with tempfile.TemporaryDirectory(prefix="shiploop-grade-") as directory:
        directory = Path(directory)
        candidate = _clone(fixture, directory / "candidate")
        reference = _reference_root(case, fixture, directory / "reference", "reference")
        mutant = _reference_root(case, fixture, directory / "mutant", "mutant")
        candidate_intended = _immutable_bytes(case, candidate)
        reference_intended = _immutable_bytes(case, reference)
        mutant_intended = _immutable_bytes(case, mutant)
        selection = _selection(case, candidate, candidate_intended)
        candidate_sequence = _sequence(case, candidate, selection["discovered_ids"], candidate_intended, expected_green=case != "expected-red")
        reference_sequence = _sequence(case, reference, selection["discovered_ids"], reference_intended, expected_green=True)
        mutant_result = _suite_run(case, mutant, ["--suite", "full"], mutant_intended)
    failure, failure_ids = _behavioral_failure(mutant_result)
    mutant_execution = _execution(mutant_result, selection["discovered_ids"])
    mutant_ok = mutant_execution["passed"] and mutant_result["returncode"] != 0 and failure
    red = {"passed": True, "failure_ids": []}
    if case == "expected-red":
        current_failure, current_ids = _behavioral_failure(candidate_sequence["runs"]["full"])
        red = {"passed": current_failure and reference_sequence["passed"], "failure_ids": current_ids}
    route = _route(case, fixture)
    source_after = _production_check(case, fixture, baseline)
    calibration = calibrate(case, fixture)
    checks = {"immutable_scope": source_before["passed"] and source_after["passed"], "selection": selection["passed"], "full_route": route["passed"], "candidate_sequence": candidate_sequence["passed"], "reference_sequence": reference_sequence["passed"], "mutant_rejected": mutant_ok, "expected_red": red["passed"], "calibration": calibration["passed"]}
    mechanical_passed = all(checks.values())
    manual = [{"check": "whether authors chose the smallest useful suite membership", "status": "unverified"}, {"check": "whether every acquisition path has the intended teardown", "status": "unverified"}, {"check": "whether shared read setup remains noninterfering under future mutations", "status": "unverified"}, {"check": "whether tests use in-memory monkeypatching or transient write-and-restore to evade endpoint snapshots", "status": "unverified", "reason": "Each command compares immutable endpoint bytes in its disposable clone, but that cannot establish what happened only between those observations."}]
    status = "mechanical-pass-with-manual-pending" if mechanical_passed else "mechanical-fail"
    return {"case": case, "mechanical_passed": mechanical_passed, "status": status, "checks": checks, "production": {"before": source_before, "after": source_after}, "selection": selection, "full_route": route, "candidate_sequence": candidate_sequence, "reference_sequence": reference_sequence, "mutant": {"passed": mutant_ok, "reason": REASONS[case], "failure_ids": failure_ids, "execution": mutant_execution, "run": mutant_result}, "expected_red": red, "calibration": calibration, "manual": manual}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = grade(args.case, args.root, args.baseline)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"case": args.case, "mechanical_passed": result["mechanical_passed"], "status": result["status"], "checks": result["checks"]}, sort_keys=True))
    return 0 if result["mechanical_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
