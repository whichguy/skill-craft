"""Measure whether a delivered ticket-assignment test suite catches source-only defects.

``assess(delivery, output)`` is the offline calibration API. It writes one JSON report,
full command logs, and per-run metadata below ``output``. The held-out ``CHECKS`` use
the same assessment path and cache one aggregate result per Product object. Mutant
tests run the complete delivered ``node --test`` suite; the baseline, three behavior-
preserving controls, and every defect therefore use the same command. A defect is
killed only by a valid non-zero run with counted failing tests. Timeouts, stale edits,
syntax errors, port refusals, missing summaries, and setup failures are invalid.
After each suite run the copied production files and original fixture tests are
fingerprinted again. This detects persistent edits, but does not sandbox untrusted
tests or detect a transient write-and-restore or concurrent write.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import weakref

HERE = Path(__file__).resolve().parents[1]
FIXTURE = HERE / "fixtures" / "node-tickets-assigned"
EXPECTED_BASE_TESTS = 117
RUN_SECONDS = 120
NETWORK_RERUNS = 2  # observation recovery only; every fresh-copy outcome is retained
TEST_SUFFIXES = {".js", ".cjs", ".mjs"}
SUMMARY_LINE = re.compile(r"^(?:ℹ|#)\s+(tests|pass|fail|skipped|todo|cancelled)\s+(\d+)\s*$", re.M)
SETUP_FAILURE = re.compile(
    r"(?:SyntaxError:|ERR_MODULE_NOT_FOUND|MODULE_NOT_FOUND|Cannot find module|Cannot find package|"
    r"Could not find|Failed to load|test file failed to load|No test files found|"
    r"not a test file|node: command not found)", re.I
)
NETWORK_FAILURE = re.compile(r"\b(?:ECONNRESET|ECONNREFUSED|EADDRINUSE|ETIMEDOUT)\b|socket hang up", re.I)


def _load_variants():
    path = Path(__file__).with_name("ticket_test_variants.py")
    spec = importlib.util.spec_from_file_location("shiploop_ticket_test_variants", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load vendored variants at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VARIANTS = _load_variants()


def _quality_module():
    """Load the existing quality runner for both held-out and direct assessment."""
    existing = sys.modules.get("quality")
    if existing is not None:
        return existing
    scripts = HERE.parents[1] / "skills" / "shiploop" / "scripts"
    for path in (scripts, HERE):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
    import quality  # pylint: disable=import-outside-toplevel

    return quality


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path_bytes(path: Path) -> bytes:
    return b"symlink\0" + os.readlink(path).encode("utf-8", "surrogateescape") if path.is_symlink() else path.read_bytes()


def _tree_files(root: Path, *, exclude: Path | None = None) -> dict[str, bytes]:
    result = {}
    if not root.is_dir():
        return result
    excluded = None
    if exclude is not None:
        try:
            excluded = Path(exclude).absolute().relative_to(root.absolute()).as_posix()
        except ValueError:
            pass
    for path in sorted(root.rglob("*")):
        if not (path.is_file() or path.is_symlink()):
            continue
        relative_path = path.relative_to(root)
        relative = relative_path.as_posix()
        if excluded and (relative == excluded or relative.startswith(excluded.rstrip("/") + "/")):
            continue
        if any(part in {".git", "node_modules", "__pycache__"} for part in relative_path.parts):
            continue
        result[relative] = _path_bytes(path)
    return result


def _tree_fingerprint(root: Path, *, exclude: Path | None = None) -> str:
    digest = hashlib.sha256()
    for relative, content in sorted(_tree_files(root, exclude=exclude).items()):
        digest.update(relative.encode("utf-8", "surrogateescape") + b"\0")
        digest.update(_sha256(content).encode("ascii") + b"\n")
    return digest.hexdigest()


def _protected_integrity(delivery: Path, *, exclude: Path | None = None) -> dict:
    fixture_files = _tree_files(FIXTURE)
    delivery_files = _tree_files(delivery, exclude=exclude)
    mismatches = []
    production_additions = []

    def protected(relative: str) -> bool:
        first = relative.split("/", 1)[0]
        return relative == "package.json" or first in {"src", "bin", "scripts"}

    expected_production = {name: data for name, data in fixture_files.items() if protected(name)}
    found_production = {name: data for name, data in delivery_files.items() if protected(name)}
    for name in sorted(set(expected_production) | set(found_production)):
        if expected_production.get(name) != found_production.get(name):
            mismatches.append(name)

    expected_names = set(fixture_files)
    for name in sorted(set(delivery_files) - expected_names):
        first = name.split("/", 1)[0]
        is_root_markdown = "/" not in name and name.lower().endswith(".md")
        is_metadata = first == ".github" or name in {".editorconfig", ".nvmrc", ".gitattributes"}
        if name == "package-lock.json":
            try:
                lock = json.loads(delivery_files[name])
                packages = lock.get("packages", {})
                root_package = packages.get("", {})
                is_metadata = (isinstance(packages, dict) and not set(packages) - {""}
                               and all(not lock.get(key) and not root_package.get(key)
                                       for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")))
            except (ValueError, TypeError, AttributeError):
                is_metadata = False
        is_test_or_docs = first in {"test", "docs"} or is_root_markdown
        if not (is_test_or_docs or is_metadata):
            production_additions.append(name)

    old_test_files = {name: data for name, data in fixture_files.items() if name.startswith("test/")}
    for name, data in sorted(old_test_files.items()):
        if delivery_files.get(name) != data:
            mismatches.append(name)

    return {
        "pass": not mismatches and not production_additions,
        "protected_production_files": len(expected_production),
        "protected_old_test_files": len(old_test_files),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:50],
        "production_addition_count": len(production_additions),
        "production_additions": production_additions[:50],
    }


def _new_test_files(delivery: Path, *, exclude: Path | None = None) -> list[str]:
    original = _tree_files(FIXTURE)
    old = {name for name in original if name.startswith("test/") and Path(name).suffix in TEST_SUFFIXES}
    found = []
    for name in sorted(_tree_files(delivery, exclude=exclude)):
        if not name.startswith("test/") or Path(name).suffix not in TEST_SUFFIXES or name in old:
            continue
        found.append(name)
    return found


def _source_read_hints(delivery: Path, added: list[str]) -> list[dict]:
    """Non-gating review hints, not a claim that arbitrary source detectors are excluded."""
    found = []
    for name in added:
        text = (delivery / name).read_text(errors="replace")
        direct = re.search(r"(?:readFile(?:Sync)?|createReadStream)\s*\([^;\n]*(?:src[/\\]|bin[/\\]|scripts[/\\]|package\.json)", text)
        hashed = "createHash" in text and re.search(r"(?:src[/\\]|bin[/\\]|scripts[/\\]|package\.json)", text)
        if direct or hashed:
            found.append({"file": name, "reason": "possible production-byte assertion; inspect the test's purpose"})
    return found


def _counts(output: str) -> dict | None:
    found = {}
    for name, raw in SUMMARY_LINE.findall(output):
        found[name] = int(raw)
    return found or None


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _failure_details(output: str) -> str:
    """Node's error diagnostics, excluding passing titles and failure titles."""
    marker = "✖ failing tests:"
    if marker in output:
        return "\n".join(line for line in output.rsplit(marker, 1)[1].splitlines()
                         if line[:1].isspace() and not line.lstrip().startswith(("✖", "✔", "▶")))
    # TAP reporters put diagnostics in YAML blocks; ordinary test names are outside.
    lines, inside = [], False
    for line in output.splitlines():
        if re.fullmatch(r"\s+---\s*", line):
            inside = True
        elif re.fullmatch(r"\s+\.\.\.\s*", line):
            inside = False
        elif inside:
            lines.append(line)
    return "\n".join(lines)


def _run_command(folder: Path, run_dir: Path, command: list[str], *, product=None) -> dict:
    quality = _quality_module()
    run_dir.mkdir(parents=True, exist_ok=True)
    log = run_dir / "stdout.log"
    refusal_log = run_dir / "port-refusals.log"
    ports = list(getattr(product, "_ports", (4180,))) if product is not None else [4180]
    guard = quality.JS.guard_env(ports, refusal_log) if ports else {}
    env = quality.child_env(guard)
    groups = product._groups if product is not None else set()
    result = quality.run_once(command, folder, env, log, RUN_SECONDS, groups)
    try:
        refusal_count = quality.count_refusals(refusal_log)
    except OSError:
        refusal_count = 0
    if not log.exists():
        log.write_bytes(b"")
    output = result.get("output", "")
    record = {
        "command": command,
        "code": result.get("returncode"),
        "timeout": bool(result.get("timeout")),
        "seconds": result.get("seconds"),
        "counts": _counts(output),
        "port_refusals": refusal_count,
        "log": str(log),
        "log_sha256": _sha256(log.read_bytes()),
        "output_tail": output[-4000:],
        "failure_details": _failure_details(output),
    }
    _write_json(run_dir / "run.json", record)
    return record


def _invalid_reason(record: dict) -> str | None:
    if record["timeout"]:
        return f"command timed out after {RUN_SECONDS} seconds"
    if record["code"] is None:
        return "command returned no exit code"
    if record["code"] == 127:
        return "node command could not start"
    if record["port_refusals"]:
        return f"port guard refused {record['port_refusals']} fixed-port bind(s)"
    counts = record["counts"]
    if counts is None:
        return "node --test produced no readable test summary"
    if counts.get("tests", 0) == 0:
        return "node --test counted zero tests"
    details = record.get("failure_details", _failure_details(record["output_tail"]))
    if SETUP_FAILURE.search(details):
        return "node --test reported a syntax, module-load, or setup failure"
    if NETWORK_FAILURE.search(details):
        return "node --test reported a network/socket infrastructure failure"
    if record["code"] not in (0, None) and counts.get("fail", 0) == 0:
        return f"node --test exited {record['code']} without counted test failures"
    if record["code"] == 0 and counts.get("fail", 0) > 0:
        return "node --test reported failures but exited zero"
    return None


def _syntax_checks(folder: Path, run_dir: Path, changed: set[str], *, product=None) -> tuple[list[dict], str | None]:
    results = []
    for relative in sorted(changed):
        path = Path(relative)
        if path.suffix not in TEST_SUFFIXES:
            continue
        record = _run_command(folder, run_dir / path.as_posix().replace("/", "_").replace(".", "_"),
                              ["node", "--check", relative], product=product)
        record = {"file": relative, **record}
        _write_json(Path(record["log"]).parent / "run.json", record)
        results.append(record)
        if record["timeout"] or record["code"] == 127 or record["code"] != 0 or record["port_refusals"]:
            reason = "syntax/setup validation failed for " + relative
            return results, reason
    return results, None


def _copy_delivery(delivery: Path, dest: Path, *, exclude: Path | None = None) -> None:
    excluded_root = None
    if exclude is not None:
        try:
            excluded_root = exclude.absolute().relative_to(delivery.absolute())
        except ValueError:
            pass

    def ignore(directory, names):
        ignored = {name for name in names if name in {".git", "node_modules", "__pycache__"}}
        if excluded_root is not None:
            exclude_path = delivery.absolute() / excluded_root
            current = Path(directory).absolute()
            for name in names:
                child = current / name
                try:
                    child.relative_to(exclude_path)
                except ValueError:
                    continue
                ignored.add(name)
        return ignored

    shutil.copytree(delivery, dest, symlinks=True, ignore=ignore)


def _immutable_snapshot(folder: Path) -> dict[str, bytes]:
    """Source/package/bin/scripts and the original fixture tests, frozen for one test command."""
    files = _tree_files(folder)
    base_tests = {name for name in _tree_files(FIXTURE) if name.startswith("test/")}
    return {name: content for name, content in files.items()
            if name == "package.json" or name.startswith(("src/", "bin/", "scripts/"))
            or "/" not in name and Path(name).suffix in TEST_SUFFIXES or name in base_tests}


def _snapshot_result(before: dict[str, bytes], after: dict[str, bytes]) -> dict:
    changed = [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
    return {"pass": not changed, "changed": changed[:50],
            "before_sha256": _sha256(b"".join(name.encode() + b"\0" + _sha256(content).encode() + b"\n"
                                               for name, content in sorted(before.items()))),
            "after_sha256": _sha256(b"".join(name.encode() + b"\0" + _sha256(content).encode() + b"\n"
                                              for name, content in sorted(after.items())))}


def _apply_run_once(delivery: Path, output: Path, label: str, edits: tuple, *, product=None) -> dict:
    root = output / label / "delivery"
    run_dir = output / label / "node-test"
    output.mkdir(parents=True, exist_ok=True)
    try:
        _copy_delivery(delivery, root, exclude=output)
    except OSError as exc:
        log = run_dir / "stdout.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(b"")
        reason = f"could not make fresh delivery copy: {exc}"
        record = {"command": ["node", "--test"], "code": None, "timeout": False, "seconds": 0.0,
                  "counts": None, "port_refusals": 0, "log": str(log), "log_sha256": _sha256(b""),
                  "output_tail": ""}
        record = {
            **record, "status": "invalid", "reason": reason,
            "tests": None, "pass": None, "fail": None, "syntax_checks": [],
            "post_run_integrity": {"pass": False, "changed": []},
        }
        _write_json(run_dir / "run.json", record)
        return record
    try:
        VARIANTS.apply_edits(root, edits, label)
    except VARIANTS.StalePatch as exc:
        (run_dir / "stdout.log").parent.mkdir(parents=True, exist_ok=True)
        (run_dir / "stdout.log").write_bytes(b"")
        record = {
            "status": "invalid", "reason": str(exc), "code": None, "tests": None,
            "pass": None, "fail": None, "seconds": 0.0, "log": str(run_dir / "stdout.log"),
            "log_sha256": _sha256(b""), "syntax_checks": [],
        }
        _write_json(run_dir / "run.json", record)
        record = {**record, "post_run_integrity": {"pass": False, "changed": []}}
        _write_json(run_dir / "run.json", record)
        return record
    changed = {relative for relative, _old, _new in edits}
    syntax, syntax_error = _syntax_checks(root, output / label / "syntax", changed, product=product)
    if syntax_error:
        record = {
            "status": "invalid", "reason": syntax_error, "code": None, "tests": None,
            "pass": None, "fail": None, "seconds": 0.0, "log": None,
            "log_sha256": _sha256(b""), "syntax_checks": syntax,
            "post_run_integrity": {"pass": False, "changed": []},
        }
        test_log = run_dir / "stdout.log"
        test_log.parent.mkdir(parents=True, exist_ok=True)
        test_log.write_bytes(b"")
        record["log"] = str(test_log)
        record["log_sha256"] = _sha256(b"")
        _write_json(run_dir / "run.json", record)
        return record
    before = _immutable_snapshot(root)
    result = _run_command(root, run_dir, ["node", "--test"], product=product)
    after = _immutable_snapshot(root)
    post_run_integrity = _snapshot_result(before, after)
    counts = result["counts"] or {}
    reason = _invalid_reason(result)
    if not post_run_integrity["pass"]:
        status = "invalid"
        reason = "the test command changed protected source or original test bytes"
    elif reason:
        status = "invalid"
    elif result["code"] == 0 and counts.get("fail", 0) == 0:
        status = "passed"
        reason = "the delivered suite passed the variant"
    else:
        status = "failed"
        reason = "the delivered suite failed the variant"
    final = {
        **result,
        "status": status,
        "reason": reason,
        "tests": counts.get("tests"),
        "pass": counts.get("pass"),
        "fail": counts.get("fail"),
        "syntax_checks": syntax,
        "post_run_integrity": post_run_integrity,
    }
    _write_json(run_dir / "run.json", final)
    return final


def _apply_run(delivery: Path, output: Path, label: str, edits: tuple, *, product=None) -> dict:
    attempts = []
    for number in range(NETWORK_RERUNS + 1):
        location = label if number == 0 else f"{label}/network-rerun-{number}"
        result = _apply_run_once(delivery, output, location, edits, product=product)
        attempts.append(dict(result))
        if not (result["status"] == "invalid"
                and result["reason"] == "node --test reported a network/socket infrastructure failure"):
            break  # the first valid failure is selected just as a valid pass is
    result = {**result, "observation_attempts": attempts, "network_reruns": len(attempts) - 1,
              "observation_seconds": sum(float(row.get("seconds") or 0) for row in attempts)}
    _write_json(output / label / "observation.json", result)
    return result


def _assess(delivery: Path, output: Path, *, product=None) -> dict:
    delivery = Path(delivery).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    if not delivery.is_dir():
        raise ValueError(f"delivery is not a directory: {delivery}")
    if output == delivery:
        raise ValueError("assessment output must be a directory distinct from the delivery")
    output.mkdir(parents=True, exist_ok=True)

    fingerprint = _tree_fingerprint(delivery, exclude=output)
    fixture_fingerprint = _tree_fingerprint(FIXTURE)
    integrity = _protected_integrity(delivery, exclude=output)
    new_tests = _new_test_files(delivery, exclude=output)

    baseline = _apply_run(delivery, output, "baseline", (), product=product)
    baseline_valid = baseline["status"] == "passed"
    baseline_counts = baseline.get("counts") or {}
    tests = baseline_counts.get("tests")
    passed = baseline_counts.get("pass")
    added_tests = bool(baseline_valid and tests and tests > EXPECTED_BASE_TESTS and passed and passed > EXPECTED_BASE_TESTS
                       and new_tests)

    controls = {}
    for name, edits in VARIANTS.CONTROLS.items():
        result = _apply_run(delivery, output, f"controls/{name}", edits, product=product)
        if result["status"] == "passed" and baseline_valid:
            result["same_counts_as_baseline"] = (result.get("tests") == tests and result.get("pass") == passed
                                                   and result.get("fail") == baseline_counts.get("fail"))
            if not result["same_counts_as_baseline"]:
                result["status"] = "failed"
                result["reason"] = "behavior control changed the suite's observed test counts"
        else:
            result["same_counts_as_baseline"] = False
        if result.get("log"):
            _write_json(Path(result["log"]).parent / "run.json", result)
        controls[name] = result

    defects = {}
    for name, edits in VARIANTS.DEFECTS.items():
        result = _apply_run(delivery, output, f"defects/{name}", edits, product=product)
        if result["status"] != "invalid" and not baseline_valid:
            result["status"] = "invalid"
            result["reason"] = "baseline was not validly passing; mutant outcome is not attributable"
        elif result["status"] == "failed":
            result["status"] = "killed"
        elif result["status"] == "passed":
            result["status"] = "survived"
        if result.get("log"):
            _write_json(Path(result["log"]).parent / "run.json", result)
        defects[name] = result

    control_ok = (len(controls) == 3 and all(row["status"] == "passed" and row.get("same_counts_as_baseline")
                                              for row in controls.values()))
    guard_rows = {
        "suite-baseline": baseline_valid,
        "preserve-fixture": integrity["pass"],
        "added-tests": added_tests,
        "behavior-controls": control_ok,
    }
    defect_rows_eligible = baseline_valid and integrity["pass"] and control_ok
    raw_defect_rows = {name: row["status"] == "killed" for name, row in defects.items()}
    checks = {**guard_rows, **{name: defect_rows_eligible and raw for name, raw in raw_defect_rows.items()}}
    killed = sum(row["status"] == "killed" for row in defects.values())
    survived = sum(row["status"] == "survived" for row in defects.values())
    invalid_defects = sum(row["status"] == "invalid" for row in defects.values())
    invalid_controls = sum(row["status"] == "invalid" for row in controls.values())
    invalid_baseline = int(baseline["status"] == "invalid")
    invalid_count = invalid_defects + invalid_controls + invalid_baseline
    invalid_reasons = ([{"variant": "baseline", "reason": baseline["reason"]}]
                       if baseline["status"] == "invalid" else [])
    invalid_reasons += [{"variant": name, "reason": row["reason"]} for name, row in controls.items()
                        if row["status"] == "invalid"]
    invalid_reasons += [{"variant": name, "reason": row["reason"]} for name, row in defects.items()
                        if row["status"] == "invalid"]

    report_path = output / "report.json"
    quality_root = Path(getattr(product, "_logs", output)).resolve() if product is not None else output
    if product is not None:
        # Reports live below <quality>/logs/<product>/scratch-N; callers know the run output root.
        run_root = quality_root.parents[2]
        display_path = report_path.relative_to(run_root).as_posix()
    else:
        display_path = str(report_path)
    report = {
        "schema": "ticket-test-adequacy/1",
        "assessment": "tests-only brownfield ticket-assignment adequacy",
        "alternative_policy": "The reference ALTERNATIVE is diagnostic only; this observer does not require its implementation shape.",
        "source_provenance": {"commit": VARIANTS.SOURCE_COMMIT, "path": VARIANTS.SOURCE_PATH,
                              "defect_count": len(VARIANTS.DEFECTS), "excluded_test_edit_defects": ["backoff-linear", "validate-renamed"]},
        "delivery": str(delivery),
        "delivery_fingerprint_sha256": fingerprint,
        "fixture": {"path": str(FIXTURE), "fingerprint_sha256": fixture_fingerprint,
                    "expected_original_tests": EXPECTED_BASE_TESTS},
        "baseline": baseline,
        "protected_fixture": integrity,
        "post_run_integrity_limit": "Snapshots detect persistent source/original-test edits, not transient write-and-restore or concurrent writes; runs are not sandboxed.",
        "added_test_files": new_tests,
        "source_read_hints": _source_read_hints(delivery, new_tests),
        "network_observation_policy": {"max_reruns": NETWORK_RERUNS,
                                       "trigger": "network-only invalid observation",
                                       "selection": "first non-network-invalid result, including any valid failure",
                                       "fresh_copy_per_attempt": True},
        "guards": guard_rows,
        "defect_rows_eligible": defect_rows_eligible,
        "controls": controls,
        "defects": defects,
        "raw_defect_rows": raw_defect_rows,
        "invalid_reasons": invalid_reasons,
        "checks": checks,
        "summary": {
            "killed": killed,
            "total": len(VARIANTS.DEFECTS),
            "survived": survived,
            "invalid": invalid_defects,
            "invalid_controls": invalid_controls,
            "invalid_baseline": invalid_baseline,
            "invalid_count": invalid_count,
            "kill_share": round(killed / len(VARIANTS.DEFECTS), 6) if VARIANTS.DEFECTS else None,
            "valid_kill_share": round(killed / (killed + survived), 6) if killed + survived else None,
            "network_reruns": sum(row.get("network_reruns", 0)
                                   for row in [baseline, *controls.values(), *defects.values()]),
            "network_invalid_observations": sum(attempt["status"] == "invalid"
                                                and attempt["reason"] == "node --test reported a network/socket infrastructure failure"
                                                for row in [baseline, *controls.values(), *defects.values()]
                                                for attempt in row.get("observation_attempts", [])),
            "defect_rows_eligible": defect_rows_eligible,
            "eligible_killed": sum(checks[name] for name in defects),
            "eligible_total": len(VARIANTS.DEFECTS) if defect_rows_eligible else 0,
            "eligible_kill_share": (round(sum(checks[name] for name in defects) / len(VARIANTS.DEFECTS), 6)
                                     if defect_rows_eligible and VARIANTS.DEFECTS else None),
        },
        "report_path": str(report_path),
        "display_report_path": display_path,
    }
    _write_json(report_path, report)
    report["report_sha256"] = _sha256(report_path.read_bytes())
    return report


def assess(delivery: Path, output: Path) -> dict:
    """Assess a delivery offline and return the report object.

    ``delivery`` is a product tree with the existing 117-test fixture in place;
    ``output`` is a separate logs-owned directory. When nested under the delivery,
    it is excluded from fingerprints and variant copies. The report is written to
    ``output/report.json`` and full stdout logs and run metadata stay below it. This
    is the same evaluator used by ``CHECKS``, without a live run.
    """
    return _assess(Path(delivery), Path(output))


_CACHE: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_CACHE_LOCK = threading.Lock()


def _assessment_for_product(product) -> dict:
    with _CACHE_LOCK:
        cached = _CACHE.get(product)
        if cached is not None:
            return cached
        output = product.scratch()
        report = _assess(product.folder, output, product=product)
        _CACHE[product] = report
        return report


def _check_note(row: str, ok: bool | None, report: dict) -> str:
    path = report.get("display_report_path", report["report_path"])
    outcome = "unobserved" if ok is None else "pass" if ok else "fail"
    if row in report["defects"]:
        raw = report["defects"][row]["status"]
        eligibility = "pass" if report["defect_rows_eligible"] else "blocked-by-guards"
        note = f"{row}={outcome}; raw={raw}; gate={eligibility}; report={path}; sha256={report['report_sha256']}"
    else:
        note = f"{row}={outcome}; report={path}; sha256={report['report_sha256']}"
    if len(note) > 300:
        # The display path is relative for run-owned assessments and the hash remains complete.
        note = f"{row}={outcome}; report={Path(path).name}; sha256={report['report_sha256']}"
    if ok is None and len(note) < 275:
        note = f"invalid_obs={report['summary']['invalid_count']}; " + note
    return note


def _make_check(row: str):
    def check(_base: str, product) -> tuple[bool | None, str]:
        report = _assessment_for_product(product)
        if report["summary"]["invalid_count"]:
            return None, _check_note(row, None, report)
        ok = bool(report["checks"].get(row, False))
        return ok, _check_note(row, ok, report)

    check.__name__ = "check_" + row.replace("-", "_")
    return check


CHECKS = {
    "suite-baseline": _make_check("suite-baseline"),
    "preserve-fixture": _make_check("preserve-fixture"),
    "added-tests": _make_check("added-tests"),
    "behavior-controls": _make_check("behavior-controls"),
    **{name: _make_check(name) for name in VARIANTS.DEFECTS},
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Assess ticket-assignment test adequacy without a live ShipLoop run.")
    parser.add_argument("delivery", type=Path, help="the delivered product folder")
    parser.add_argument("output", type=Path, help="separate logs-owned output directory")
    args = parser.parse_args(argv)
    report = assess(args.delivery, args.output)
    print(json.dumps({"report_path": report["report_path"], "report_sha256": report["report_sha256"],
                      "summary": report["summary"], "guards": report["guards"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
