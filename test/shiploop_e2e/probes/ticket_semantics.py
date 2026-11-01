#!/usr/bin/env python3
"""Measure two ticket behavior probes against frozen prior test outputs.

The caller supplies source roots and every base/original test file explicitly.
The runner creates disposable copies, writes a prospective protocol, seeds one
source-only fault per case, and records each single command attempt.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from typing import Any


CLOCK_PATH = "test/ticket-semantics-clock.probe.test.js"
SAVE_PATH = "test/ticket-semantics-precleanup.probe.test.js"
REPETITIONS = 3
TIMEOUT = 60
COUNT_RE = re.compile(r"^# (tests|pass|fail|cancelled|skipped|todo) (\d+)\s*$", re.M)
FAIL_RE = re.compile(r"^not ok \d+ - (.+)$", re.M)

CLOCK_TEST = r'''
'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { manualClock } = require('../src/clock');
const { ticketBody, withService } = require('./helpers');

test('SEM_CLOCK_1 same-agent no-op preserves updated after deterministic clock advance', async () => {
  const artifacts = process.env.PROBE_ARTIFACT_DIR;
  assert.ok(artifacts, 'an external artifact directory is required');
  const clock = manualClock();
  let firstUpdated;
  let repeatedUpdated;
  await withService({ clock, workerIntervalMs: 0 }, async (api) => {
    const created = await api.post('/tickets', ticketBody());
    assert.equal(created.status, 201);
    const first = await api.put(`/tickets/${created.body.id}/assignee`, { assignee: 'alice' });
    assert.equal(first.status, 200);
    firstUpdated = first.body.updated;
    clock.advance(1000);
    const repeated = await api.put(`/tickets/${created.body.id}/assignee`, { assignee: 'alice' });
    assert.equal(repeated.status, 200);
    repeatedUpdated = repeated.body.updated;
  });
  fs.mkdirSync(artifacts, { recursive: true });
  fs.writeFileSync(path.join(artifacts, 'clock-observation.json'), JSON.stringify({
    advancedMilliseconds: 1000, firstUpdated, repeatedUpdated,
  }, null, 2) + '\n');
  assert.equal(repeatedUpdated, firstUpdated, 'an unchanged assignment must not refresh updated');
});
'''

SAVE_TEST = r'''
'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { ticketBody, withService } = require('./helpers');

test('SEM_PERSISTENCE_1 assignment is in DATA_FILE before graceful cleanup', async () => {
  const artifacts = process.env.PROBE_ARTIFACT_DIR;
  assert.ok(artifacts, 'an external artifact directory is required');
  fs.mkdirSync(artifacts, { recursive: true });
  const dataFile = path.join(artifacts, 'DATA_FILE.json');
  let responseAssignee;
  let beforeCleanupAssignee;
  let beforeBytes;
  await withService({ dataFile, workerIntervalMs: 0 }, async (api) => {
    const created = await api.post('/tickets', ticketBody());
    assert.equal(created.status, 201);
    const assigned = await api.put(`/tickets/${created.body.id}/assignee`, { assignee: 'alice' });
    assert.equal(assigned.status, 200);
    responseAssignee = assigned.body.assignee;
    beforeBytes = fs.readFileSync(dataFile);
    beforeCleanupAssignee = JSON.parse(beforeBytes.toString('utf8')).tickets
      .find((ticket) => ticket.id === created.body.id).assignee;
    fs.writeFileSync(path.join(artifacts, 'DATA_FILE.before-cleanup.json'), beforeBytes);
  });
  const afterBytes = fs.readFileSync(dataFile);
  const afterCleanupAssignee = JSON.parse(afterBytes.toString('utf8')).tickets[0].assignee;
  fs.writeFileSync(path.join(artifacts, 'DATA_FILE.after-cleanup.json'), afterBytes);
  fs.writeFileSync(path.join(artifacts, 'persistence-observation.json'), JSON.stringify({
    responseAssignee, beforeCleanupAssignee, afterCleanupAssignee,
    beforeCleanupSha256: crypto.createHash('sha256').update(beforeBytes).digest('hex'),
    afterCleanupSha256: crypto.createHash('sha256').update(afterBytes).digest('hex'),
  }, null, 2) + '\n');
  assert.equal(responseAssignee, 'alice', 'the assignment response is correct');
  assert.equal(afterCleanupAssignee, 'alice', 'graceful cleanup retains the assignment');
  assert.equal(beforeCleanupAssignee, 'alice', 'each assignment must already be saved before cleanup');
});
'''


class SetupError(RuntimeError):
    """An input or copy failure; it must not be counted as a test detection."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(root: Path) -> dict[str, dict[str, Any]]:
    rows = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise SetupError(f"source contains symlink: {path.relative_to(root)}")
        if path.is_file():
            data = path.read_bytes()
            rows[path.relative_to(root).as_posix()] = {
                "sha256": digest(data), "bytes": len(data), "mode": path.stat().st_mode & 0o777,
            }
    return rows


def identity(root: Path) -> dict[str, Any]:
    rows = manifest(root)
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"path": str(root.resolve()), "files": len(rows),
            "bytes": sum(row["bytes"] for row in rows.values()), "tree_sha256": digest(canonical),
            "manifest": rows}


def explicit_files(root: Path, names: list[str], label: str) -> list[str]:
    if not names:
        raise SetupError(f"{label} has no explicit files")
    seen: set[str] = set()
    checked = []
    for name in names:
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or any(ch in name for ch in "*?[]"):
            raise SetupError(f"{label} requires explicit root-relative files: {name}")
        normalized = relative.as_posix()
        if normalized in seen:
            raise SetupError(f"{label} repeats {normalized}")
        seen.add(normalized)
        path = root / normalized
        if not path.is_file() or path.is_symlink():
            raise SetupError(f"{label} file missing or not regular: {normalized}")
        checked.append(normalized)
    return checked


def classify(stdout: str, returncode: int | None, expected: int,
             validity: str | None = None) -> dict[str, Any]:
    counts = {key: int(value) for key, value in COUNT_RE.findall(stdout)}
    failed = FAIL_RE.findall(stdout)
    if validity:
        return {"outcome": "UNKNOWN", "validity": validity, "counts": counts, "failed_names": failed}
    if counts.get("tests") != expected:
        return {"outcome": "UNKNOWN", "validity": "count_mismatch", "expected_tests": expected,
                "counts": counts, "failed_names": failed}
    if any(key not in counts for key in ("pass", "fail", "cancelled", "skipped", "todo")):
        return {"outcome": "UNKNOWN", "validity": "incomplete_tap", "expected_tests": expected,
                "counts": counts, "failed_names": failed}
    if any(counts[key] for key in ("cancelled", "skipped", "todo")):
        return {"outcome": "UNKNOWN", "validity": "skipped_or_incomplete", "expected_tests": expected,
                "counts": counts, "failed_names": failed}
    if counts["pass"] + counts["fail"] != expected or len(failed) != counts["fail"]:
        return {"outcome": "UNKNOWN", "validity": "inconsistent_tap", "expected_tests": expected,
                "counts": counts, "failed_names": failed}
    if returncode == 0 and counts["pass"] == expected and counts["fail"] == 0:
        outcome = "PASS"
    elif returncode == 1 and counts["fail"] > 0:
        outcome = "FAIL"
    else:
        return {"outcome": "UNKNOWN", "validity": "exit_count_mismatch", "expected_tests": expected,
                "returncode": returncode, "counts": counts, "failed_names": failed}
    return {"outcome": outcome, "validity": "valid", "expected_tests": expected,
            "counts": counts, "failed_names": failed}


FAULTS = {
    "clock": {
        "description": "Refresh only updated on a same-assignee no-op; other empty-change actions are untouched.",
        "before": "    if (Object.keys(changes).length === 0) return { ...ticket };",
        "after": "    if (Object.keys(changes).length === 0) {\n      if (action === 'ticket.assigned') ticket.updated = this.now();\n      return { ...ticket };\n    }",
    },
    "save": {
        "description": "Skip the ticket.assigned per-change save; graceful stop still saves the in-memory snapshot.",
        "before": "    effects(at);\n    this.save();\n    return { ...ticket };",
        "after": "    effects(at);\n    if (action !== 'ticket.assigned') this.save();\n    return { ...ticket };",
    },
}


def seed(arm: Path, kind: str) -> dict[str, Any]:
    path = arm / "src/store.js"
    before = path.read_text()
    patch = FAULTS[kind]
    if before.count(patch["before"]) != 1:
        raise SetupError(f"{kind} fault target was not unique in src/store.js")
    after = before.replace(patch["before"], patch["after"], 1)
    path.write_text(after)
    return {"description": patch["description"], "file": "src/store.js", "edits": 1,
            "before_sha256": digest(before.encode()), "after_sha256": digest(after.encode())}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def expected_attempt_count(plans: list[tuple[Any, ...]]) -> int:
    """A plan row's final value is its predeclared repetition count."""
    return sum(int(row[-1]) for row in plans)


def predictions_match(results: list[dict[str, Any]], plans: list[tuple[Any, ...]],
                      *, source_unchanged: bool, runtime_unchanged: bool) -> bool:
    return (source_unchanged and runtime_unchanged
            and len(results) == expected_attempt_count(plans)
            and all(row.get("prediction_matched") is True for row in results))


def validate_positive_counts(base: int, clock: int, persistence: int, repetitions: int) -> None:
    values = {"base test count": base, "clock original test count": clock,
              "persistence original test count": persistence, "clock repetitions": repetitions}
    invalid = [f"{name}={value}" for name, value in values.items() if value <= 0]
    if invalid:
        raise SetupError("expected counts and repetitions must be positive: " + ", ".join(invalid))


def node_cwd(node: str, arm: Path) -> dict[str, Any]:
    argv = [node, "-p", "process.cwd()"]
    done = subprocess.run(argv, cwd=arm, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=10, check=False)
    actual = done.stdout.strip()
    okay = done.returncode == 0 and Path(actual).resolve() == arm.resolve()
    return {"argv": argv, "cwd": str(arm.resolve()), "actual_cwd": actual,
            "returncode": done.returncode, "outcome": "PASS" if okay else "INCOMPLETE",
            "stderr": done.stderr}


def run_command(node: str, out: Path, arm: Path, attempt: str, suite: str, files: list[str],
                expected_count: int, expected_outcome: str) -> dict[str, Any]:
    argv = [node, "--test", "--test-reporter=tap", *files]
    log_dir = out / "logs"
    artifact_dir = out / "observations" / attempt
    home = out / "isolated-home"
    tmp = out / "tmp"
    for folder in (log_dir, artifact_dir, home, tmp):
        folder.mkdir(parents=True, exist_ok=True)
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "TMPDIR": str(tmp),
           "TZ": "UTC", "LANG": "C", "LC_ALL": "C", "PROBE_ARTIFACT_DIR": str(artifact_dir)}
    before = identity(arm)
    start = time.monotonic_ns()
    timed_out, launch_error, code = False, None, None
    stdout = stderr = ""
    try:
        done = subprocess.run(argv, cwd=arm, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT, check=False)
        code, stdout, stderr = done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    except OSError as exc:
        launch_error = f"{type(exc).__name__}: {exc}"
    seconds = (time.monotonic_ns() - start) / 1_000_000_000
    stdout_path = log_dir / f"{attempt}.stdout.tap"
    stderr_path = log_dir / f"{attempt}.stderr.log"
    stdout_path.write_text(stdout)
    stderr_path.write_text(stderr)
    status = "timeout" if timed_out else ("setup_failure" if launch_error else None)
    actual = classify(stdout, code, expected_count, validity=status)
    after = identity(arm)
    unchanged = before["tree_sha256"] == after["tree_sha256"]
    if not unchanged:
        actual = {**actual, "raw_outcome": actual["outcome"], "outcome": "UNKNOWN", "validity": "arm_source_changed"}
    matched = actual["validity"] == "valid" and actual["outcome"] == expected_outcome
    suite_bytes = sum((arm / file).stat().st_size for file in files if (arm / file).is_file())
    return {
        "attempt_id": attempt, "suite": suite, "cwd": str(arm.resolve()), "argv": argv,
        "complete_test_files": files, "expected_tests": expected_count, "expected_outcome": expected_outcome,
        "actual": actual, "returncode": code, "launch_error": launch_error, "timed_out": timed_out,
        "wall_seconds": seconds, "stdout_path": str(stdout_path), "stderr_path": str(stderr_path),
        "stdout_bytes": len(stdout.encode()), "stderr_bytes": len(stderr.encode()),
        "output_bytes": len(stdout.encode()) + len(stderr.encode()), "suite_file_bytes": suite_bytes,
        "arm_files": before["files"], "arm_bytes": before["bytes"], "arm_unchanged": unchanged,
        "prediction_matched": matched, "model_calls": 0,
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clock-source", required=True)
    parser.add_argument("--clock-base-tests", nargs="+", required=True)
    parser.add_argument("--clock-original-tests", nargs="+", required=True)
    parser.add_argument("--persistence-source", required=True)
    parser.add_argument("--persistence-base-tests", nargs="+", required=True)
    parser.add_argument("--persistence-original-tests", nargs="+", required=True)
    parser.add_argument("--reference-source")
    parser.add_argument("--expected-base-count", required=True, type=int)
    parser.add_argument("--expected-clock-original-count", required=True, type=int)
    parser.add_argument("--expected-persistence-original-count", required=True, type=int)
    parser.add_argument("--clock-repetitions", type=int, default=REPETITIONS)
    parser.add_argument("--node", help="Node executable name or path; resolved and frozen once.")
    parser.add_argument("--prior-evidence", action="append", nargs=3, metavar=("ID", "STATUS", "PATH"))
    parser.add_argument("--contrary-evidence", action="append", default=[], metavar="PATH")
    parser.add_argument("--output", required=True, help="New, nonexistent evidence directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    out = Path(args.output).expanduser().resolve()
    if out.exists():
        print(f"INCOMPLETE setup: output exists; preserve it and choose a new path: {out}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=False)
    preflight_error = None
    try:
        validate_positive_counts(args.expected_base_count, args.expected_clock_original_count,
                                 args.expected_persistence_original_count, args.clock_repetitions)
    except (OSError, json.JSONDecodeError, SetupError) as exc:
        preflight_error = f"{type(exc).__name__}: {exc}"
    protocol: dict[str, Any] = {
        "schema": "ticket-semantics-probe/1", "registered_at": datetime.now(timezone.utc).isoformat(),
        "invocation": sys.argv if argv is None else [sys.argv[0], *argv],
        "hypothesis": "Timestamp and pre-cleanup observations distinguish only their matching seeded behavior fault in these retained outputs.",
        "scope": "offline copies; no model calls, live runs, live scorecard floor, or product qualification",
        "governing_requirements": {
            "no_op_assignment": "When the assigned agent is unchanged, the operation changes nothing; updated remains unchanged.",
            "durable_assignment": "Each change is saved to DATA_FILE before the service is stopped.",
        },
        "source_paths": {"clock": args.clock_source, "persistence": args.persistence_source,
                         "reference": args.reference_source},
        "explicit_test_files": {"clock_base": args.clock_base_tests, "clock_original": args.clock_original_tests,
                                "persistence_base": args.persistence_base_tests,
                                "persistence_original": args.persistence_original_tests},
        "expected_counts": {"base": args.expected_base_count,
                            "clock_original": args.expected_clock_original_count,
                            "persistence_original": args.expected_persistence_original_count,
                            "each_behavioral_probe": 1},
        "clock_repetitions": args.clock_repetitions, "other_suite_attempts": 1, "retries": 0,
        "timeout_seconds": TIMEOUT,
        "predictions": {
            "clock-correct": {"base": "PASS", "original": "PASS", "clock_probe": "PASS"},
            "clock-timestamp-fault": {"base": "PASS", "original": "PASS", "clock_probe": "FAIL"},
            "persistence-correct": {"base": "PASS", "original": "PASS", "precleanup_probe": "PASS"},
            "persistence-save-only-at-cleanup-fault": {"base": "PASS", "original": "PASS", "precleanup_probe": "FAIL"},
            "alternative-reference": {"clock_probe": "PASS", "precleanup_probe": "PASS"},
        },
        "faults": {key: value["description"] for key, value in FAULTS.items()},
        "prior_evidence": [{"id": row[0], "status": row[1], "path": row[2]} for row in args.prior_evidence or []],
        "contrary_evidence_locators": args.contrary_evidence,
        "contrary_evidence_note": "The later completed normal-workflow output includes a generated test that directly checks persistence; this probe reports the partial tests-only artifact's blind spot and does not generalize it to all generated suites.",
        "source_identity_rule": "Full file path, SHA-256, byte size and mode manifests are captured before and after; a changed input makes results unknown.",
        "cwd_rule": "Before tests, node -p process.cwd() must equal each absolute arm copy directory.",
        "failure_rule": "Setup errors, timeouts, TAP/count mismatch, skips, source mutation and unexpected outcomes remain visible; no retry.",
        "model_calls": 0, "live_runs": 0,
    }
    write_json(out / "protocol.json", protocol)

    setup_attempts: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    try:
        if preflight_error:
            raise SetupError(preflight_error)
        clock_source = Path(args.clock_source).expanduser().resolve(strict=True)
        persistence_source = Path(args.persistence_source).expanduser().resolve(strict=True)
        reference_source = Path(args.reference_source).expanduser().resolve(strict=True) if args.reference_source else None
        if not all(path.is_dir() for path in (clock_source, persistence_source, *([reference_source] if reference_source else []))):
            raise SetupError("every source must be a directory")
        source_before = {"clock": identity(clock_source), "persistence": identity(persistence_source)}
        if reference_source:
            source_before["reference"] = identity(reference_source)
        for label, root, base, original in (
            ("clock", clock_source, args.clock_base_tests, args.clock_original_tests),
            ("persistence", persistence_source, args.persistence_base_tests, args.persistence_original_tests),
        ):
            explicit_files(root, base, f"{label} base tests")
            explicit_files(root, original, f"{label} original tests")
        node = shutil.which(args.node) if args.node else shutil.which("node")
        if not node:
            raise SetupError("node executable not found")
        node = str(Path(node).resolve())
        node_version = subprocess.run([node, "--version"], stdin=subprocess.DEVNULL, capture_output=True,
                                      text=True, encoding="utf-8", errors="replace", timeout=10, check=False)
        if node_version.returncode != 0:
            raise SetupError(f"node --version failed: {node_version.stderr.strip()}")
        protocol["runtime"] = {"node_path": node, "node_version": node_version.stdout.strip(),
                               "python_version": sys.version.split()[0]}
        protocol["source_identity_before"] = {key: {k: v for k, v in row.items() if k != "manifest"}
                                              for key, row in source_before.items()}
        write_json(out / "protocol.json", protocol)
        write_json(out / "source-identities-before.json", source_before)
    except (OSError, SetupError, subprocess.TimeoutExpired) as exc:
        setup_attempts.append({"attempt_id": "preflight-001", "outcome": "INCOMPLETE",
                               "error": f"{type(exc).__name__}: {exc}", "node_commands_started": 0})
        write_json(out / "setup-attempts.json", setup_attempts)
        write_json(out / "results.json", {"status": "INCOMPLETE", "results": [], "model_calls": 0})
        return 2

    jobs = [
        ("clock-correct", clock_source, args.clock_base_tests, args.clock_original_tests,
         [(CLOCK_PATH, CLOCK_TEST)], None),
        ("clock-timestamp-fault", clock_source, args.clock_base_tests, args.clock_original_tests,
         [(CLOCK_PATH, CLOCK_TEST)], "clock"),
        ("persistence-correct", persistence_source, args.persistence_base_tests, args.persistence_original_tests,
         [(SAVE_PATH, SAVE_TEST)], None),
        ("persistence-save-only-at-cleanup-fault", persistence_source, args.persistence_base_tests,
         args.persistence_original_tests, [(SAVE_PATH, SAVE_TEST)], "save"),
    ]
    if reference_source:
        jobs += [
            ("alternative-reference", reference_source, [], [],
             [(CLOCK_PATH, CLOCK_TEST), (SAVE_PATH, SAVE_TEST)], None),
        ]

    arms: dict[str, Path] = {}
    arm_before: dict[str, dict[str, Any]] = {}
    for name, source, _base, _original, probes, fault in jobs:
        arm = out / "arms" / name
        try:
            shutil.copytree(source, arm)
            for rel, contents in probes:
                path = arm / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents)
            fault_record = seed(arm, fault) if fault else None
            arms[name] = arm
            arm_before[name] = identity(arm)
            write_json(out / "arm-manifests" / f"{name}.before.json", arm_before[name])
            setup = node_cwd(node, arm)
            setup_attempts.append({"attempt_id": f"cwd-{name}", "kind": "cwd-precheck", **setup})
            if setup["outcome"] != "PASS":
                continue
            if fault_record:
                write_json(out / "faults" / f"{name}.json", fault_record)
        except (OSError, SetupError, subprocess.TimeoutExpired) as exc:
            setup_attempts.append({"attempt_id": f"setup-{name}", "kind": "copy-or-fault", "outcome": "INCOMPLETE",
                                   "error": f"{type(exc).__name__}: {exc}"})

    plans: list[tuple[str, str, list[str], int, str, int]] = []
    for name, source, base, original, _probes, _fault in jobs[:4]:
        clock = name.startswith("clock-")
        faulty = name.endswith("fault")
        plans.append((name, "base", base, args.expected_base_count, "PASS", 1))
        plans.append((name, "original", original,
                      args.expected_clock_original_count if clock else args.expected_persistence_original_count,
                      "PASS", 1))
        if clock:
            plans.append((name, "clock_probe", [CLOCK_PATH], 1, "FAIL" if faulty else "PASS", args.clock_repetitions))
        else:
            plans.append((name, "precleanup_probe", [SAVE_PATH], 1, "FAIL" if faulty else "PASS", 1))
    if reference_source:
        plans.extend([
            ("alternative-reference", "clock_probe", [CLOCK_PATH], 1, "PASS", args.clock_repetitions),
            ("alternative-reference", "precleanup_probe", [SAVE_PATH], 1, "PASS", 1),
        ])

    number = 0
    cwd_ok = {row["attempt_id"].removeprefix("cwd-"): row.get("outcome") == "PASS"
              for row in setup_attempts if row.get("kind") == "cwd-precheck"}
    for name, suite, files, count, expected_outcome, reps in plans:
        for rep in range(1, reps + 1):
            number += 1
            attempt = f"{number:03d}-{name}-{suite}-r{rep}"
            if name not in arms or not cwd_ok.get(name, False):
                row = {"attempt_id": attempt, "suite": suite, "expected_outcome": expected_outcome,
                       "actual": {"outcome": "UNKNOWN", "validity": "setup_incomplete"},
                       "prediction_matched": False, "model_calls": 0}
            else:
                row = run_command(node, out, arms[name], attempt, suite, files, count, expected_outcome)
            results.append(row)
            with (out / "attempts.jsonl").open("a") as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\n")

    source_after = {"clock": identity(clock_source), "persistence": identity(persistence_source)}
    if reference_source:
        source_after["reference"] = identity(reference_source)
    unchanged = all(source_before[name]["tree_sha256"] == source_after[name]["tree_sha256"] for name in source_before)
    write_json(out / "source-identities-after.json", source_after)
    if not unchanged:
        for row in results:
            row["actual"] = {**row.get("actual", {}), "raw_outcome": row.get("actual", {}).get("outcome"),
                              "outcome": "UNKNOWN", "validity": "source_changed"}
            row["prediction_matched"] = False

    runtime_error = None
    try:
        node_version_result = subprocess.run([node, "--version"], stdin=subprocess.DEVNULL, capture_output=True,
                                             text=True, encoding="utf-8", errors="replace", timeout=10, check=False)
        node_version_after = node_version_result.stdout.strip()
        runtime_unchanged = (node_version_result.returncode == 0
                             and node_version_after == protocol["runtime"]["node_version"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        node_version_after = None
        runtime_unchanged = False
        runtime_error = f"{type(exc).__name__}: {exc}"
    if not runtime_unchanged:
        for row in results:
            row["actual"] = {**row.get("actual", {}), "raw_outcome": row.get("actual", {}).get("outcome"),
                              "outcome": "UNKNOWN", "validity": "node_version_changed"}
            row["prediction_matched"] = False
    write_json(out / "setup-attempts.json", setup_attempts)
    okay = predictions_match(results, plans, source_unchanged=unchanged,
                             runtime_unchanged=runtime_unchanged)
    summary = {
        "status": "PREDICTIONS_MATCHED" if okay else "UNKNOWN_OR_UNEXPECTED",
        "predictions_matched": okay, "source_unchanged": unchanged, "node_version_unchanged": runtime_unchanged,
        "node_version_before": protocol["runtime"]["node_version"], "node_version_after": node_version_after,
        "source_identity_before": {k: {key: v for key, v in row.items() if key != "manifest"}
                                   for k, row in source_before.items()},
        "source_identity_after": {k: {key: v for key, v in row.items() if key != "manifest"}
                                  for k, row in source_after.items()},
        "attempt_count": len(results), "expected_attempt_count": expected_attempt_count(plans),
        "setup_attempt_count": len(setup_attempts), "results": results,
        "total_wall_seconds": sum(float(row.get("wall_seconds", 0)) for row in results),
        "total_output_bytes": sum(int(row.get("output_bytes", 0)) for row in results),
        "runtime_error": runtime_error,
        "model_calls": 0, "live_runs": 0,
    }
    write_json(out / "results.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))
    return 0 if okay else 1


if __name__ == "__main__":
    raise SystemExit(main())
