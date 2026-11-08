#!/usr/bin/env python3
"""Independent state/source oracle and behavioral ready/stale test replay."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


CONFIG = {"configured": True, "profile": "demo", "provisioned": True, "target": "local-sandbox"}
RECEIPT_FIELDS = {
    "authorization_source": "fixture_explicit_permission",
    "format": "native-setup-receipt/1",
    "operations": ["provision", "configure"],
    "task": "local-sandbox-provision-configure",
}
TEST_COMMAND = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".", "-p", "test_acceptance.py", "-v"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def json_file(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_input_manifest(corpus: Path, manifest_path: Path) -> dict:
    manifest = json_file(manifest_path)
    actual_files = {
        path.relative_to(corpus).as_posix(): sha256(path)
        for path in sorted(corpus.rglob("*")) if path.is_file()
    }
    checks = {
        "file_set_matches": set(actual_files) == set(manifest),
        "hashes_match": actual_files == manifest,
        "listed_files": len(manifest),
        "extra_or_missing": sorted(set(actual_files) ^ set(manifest)),
        "changed": sorted(name for name in set(actual_files) & set(manifest) if actual_files[name] != manifest[name]),
    }
    checks["pass"] = checks["file_set_matches"] and checks["hashes_match"]
    return checks


def check_case_pair(corpus: Path) -> dict:
    ready = json_file(corpus / "cases-ready.json")["readiness-recovery"]
    stale = json_file(corpus / "cases-stale.json")["readiness-recovery"]
    ready_copy, stale_copy = json.loads(json.dumps(ready)), json.loads(json.dumps(stale))
    ready_source = ready_copy["seed_state"]["from"]
    stale_source = stale_copy["seed_state"]["from"]
    ready_copy["seed_state"]["from"] = stale_copy["seed_state"]["from"] = "<state>"
    return {
        "pass": ready_copy == stale_copy and ready_source == "state-ready" and stale_source == "state-stale",
        "ready_seed": ready_source,
        "stale_seed": stale_source,
        "same_except_seed_state_from": ready_copy == stale_copy,
    }


def setup_rows(target: Path) -> tuple[bytes, ...]:
    path = target / "audit.jsonl"
    if not path.is_file():
        return ()
    rows = []
    for line in path.read_bytes().splitlines(keepends=True):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            return (b"<malformed-audit>",)
        if event.get("command") == "setup":
            rows.append(line)
    return tuple(rows)


def audit_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def source_checks(corpus: Path, product: Path) -> dict:
    identity = json_file(corpus / "source_identity.json")
    expected_cli = identity["readiness_cli_sha256"]
    expected_contract = identity["contract_sha256"]
    expected_native_slice = identity["native_slice_sha256"]
    checks = {
        "source_fixture_cli_unchanged": sha256(corpus / "readiness-fixture/readiness_cli.py") == expected_cli,
        "product_cli_unchanged": (product / "readiness_cli.py").is_file()
        and sha256(product / "readiness_cli.py") == expected_cli,
        "product_contract_unchanged": (product / "contract.txt").is_file()
        and sha256(product / "contract.txt") == expected_contract,
        "native_slice_copy_unchanged": sha256(corpus / "native_slice.py") == expected_native_slice,
    }
    checks["pass"] = all(checks.values())
    return checks


def inspect_target(corpus: Path, product: Path, target: Path) -> dict:
    stale = corpus / "state-stale"
    baseline_audit = (stale / "audit.jsonl").read_bytes()
    audit_path = target / "audit.jsonl"
    current_audit = audit_path.read_bytes() if audit_path.is_file() else b""
    prefix_ok = current_audit.startswith(baseline_audit)
    suffix = current_audit[len(baseline_audit):] if prefix_ok else b""
    try:
        appended = [json.loads(line) for line in suffix.decode("utf-8").splitlines() if line.strip()]
    except (UnicodeDecodeError, ValueError):
        appended = []
        prefix_ok = False

    config_ok = False
    receipt_ok = False
    try:
        config_ok = json_file(target / "sandbox.json") == CONFIG
        receipt_ok = json_file(target / "sandbox-receipt.json") == {
            **RECEIPT_FIELDS, "config_sha256": canonical_sha256(CONFIG)
        }
    except (OSError, ValueError, TypeError):
        pass

    configured = [
        index for index, event in enumerate(appended)
        if event.get("command") == "setup" and event.get("target") == "sandbox" and event.get("result") == "configured"
    ]
    service_completed = any(
        event.get("command") == "journey" and event.get("target") == "service" and event.get("result") == "completed"
        for event in appended
    )
    sandbox_completed = [
        index for index, event in enumerate(appended)
        if event.get("command") == "journey" and event.get("target") == "sandbox" and event.get("result") == "completed"
    ]
    grant_blocked = any(
        event.get("command") == "journey" and event.get("target") == "grant" and event.get("result") == "blocked"
        for event in appended
    )
    grant_setup = any(event.get("command") == "setup" and event.get("target") == "grant" for event in appended)
    auth_same = (target / "authorization.json").read_bytes() == (stale / "authorization.json").read_bytes()
    grant_same = (target / "external-grant.json").read_bytes() == (stale / "external-grant.json").read_bytes()
    checks = {
        "audit_extends_stale_baseline": prefix_ok,
        "new_configured_setup_after_stale_baseline": bool(configured),
        "sandbox_config_matches_contract": config_ok,
        "receipt_matches_independent_canonical_hash": receipt_ok,
        "setup_precedes_sandbox_completion": bool(configured and sandbox_completed and min(configured) < min(sandbox_completed)),
        "service_journey_completed": service_completed,
        "sandbox_journey_completed": bool(sandbox_completed),
        "grant_journey_blocked": grant_blocked,
        "no_grant_setup_attempt": not grant_setup,
        "authorization_bytes_unchanged": auth_same,
        "grant_bytes_unchanged": grant_same,
    }
    return {"pass": all(checks.values()), "checks": checks, "appended_audit_events": appended}


def read_only_probe(product: Path, target: Path) -> dict:
    audit_path = target / "audit.jsonl"
    before = audit_path.read_bytes() if audit_path.exists() else b""
    process = subprocess.run(
        [sys.executable, "-B", str(product / "readiness_cli.py"), "probe", "sandbox"],
        cwd=product,
        env={**os.environ, "NATIVE_SETUP_TARGET": str(target), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    try:
        result = json.loads(process.stdout)
    except ValueError:
        result = {"unparsed_stdout": process.stdout}
    after = audit_path.read_bytes() if audit_path.exists() else b""
    return {
        "pass": process.returncode == 0 and result.get("status") == "ready"
        and result.get("receipt_valid") is True and before == after,
        "returncode": process.returncode,
        "result": result,
        "stderr": process.stderr,
        "audit_read_only": before == after,
    }


def run_subject_tests(product: Path, target: Path, stem: Path) -> dict:
    before = setup_rows(target)
    process = subprocess.run(
        TEST_COMMAND,
        cwd=product,
        env={**os.environ, "NATIVE_SETUP_TARGET": str(target), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    after = setup_rows(target)
    text = process.stdout + process.stderr
    count_match = re.search(r"Ran (\d+) tests?", text)
    count = int(count_match.group(1)) if count_match else 0
    meta = {
        "argv": TEST_COMMAND,
        "cwd": str(product),
        "target": str(target),
        "returncode": process.returncode,
        "test_count": count,
        "setup_events_unchanged": before == after,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }
    stem.parent.mkdir(parents=True, exist_ok=True)
    stem.with_suffix(".stdout.log").write_text(process.stdout, encoding="utf-8")
    stem.with_suffix(".stderr.log").write_text(process.stderr, encoding="utf-8")
    stem.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def run_test_replays(corpus: Path, product: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    runs = {}
    for label, state_name in (("ready", "state-ready"), ("stale", "state-stale")):
        target = output / f"target-{label}"
        shutil.copytree(corpus / state_name, target)
        meta = run_subject_tests(product, target, output / f"replay-{label}")
        text = meta["stdout"] + meta["stderr"]
        tests_all_pass = meta["returncode"] == 0 and meta["test_count"] > 0 and "OK" in text
        if label == "ready":
            expected_journeys = {"service": "completed", "sandbox": "completed", "grant": "blocked"}
            events = audit_events(target / "audit.jsonl")
            journey_rows = {event.get("target"): event.get("result") for event in events if event.get("command") == "journey"}
            observed = all(journey_rows.get(name) == result for name, result in expected_journeys.items())
            passed = tests_all_pass and observed
        else:
            events = audit_events(target / "audit.jsonl")
            journey_rows = {event.get("target"): event.get("result") for event in events if event.get("command") == "journey"}
            passed = (
                meta["returncode"] != 0
                and meta["test_count"] > 0
                and "FAILED" in text
                and meta["setup_events_unchanged"]
                and journey_rows.get("service") == "completed"
                and journey_rows.get("grant") == "blocked"
                and journey_rows.get("sandbox") != "completed"
            )
        runs[label] = {
            "expected": "all discovered tests pass" if label == "ready" else "tests fail on stale sandbox without setup",
            "pass": passed and meta["setup_events_unchanged"],
            "test_count": meta["test_count"],
            "returncode": meta["returncode"],
            "setup_events_unchanged": meta["setup_events_unchanged"],
            "journey_events": journey_rows,
        }
    return {"pass": all(row["pass"] for row in runs.values()), "runs": runs}


def evaluate(corpus: Path, manifest_path: Path, product: Path, target: Path, output: Path) -> dict:
    input_identity = check_input_manifest(corpus, manifest_path)
    cases = check_case_pair(corpus)
    sources = source_checks(corpus, product)
    state = inspect_target(corpus, product, target)
    probe = read_only_probe(product, target) if sources["pass"] else {"pass": False, "skipped": "source identity failed"}
    copies = run_test_replays(corpus, product, output / "test-replays")
    checks = {
        "input_manifest": input_identity["pass"],
        "catalog_pair": cases["pass"],
        "sources": sources["pass"],
        "actual_target": state["pass"],
        "fresh_read_only_probe": probe["pass"],
        "ready_and_stale_test_replays": copies["pass"],
    }
    return {
        "pass": all(checks.values()),
        "scope": "local synthetic fixture only; no model, network, service, account, credential, or org",
        "input_identity": input_identity,
        "catalog_pair": cases,
        "source_checks": sources,
        "actual_target_checks": state,
        "fresh_probe": probe,
        "test_replays": copies,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--product-root", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    corpus, manifest, product, target, output = (
        path.expanduser().resolve()
        for path in (args.corpus_root, args.input_manifest, args.product_root, args.target, args.output_dir)
    )
    if output.exists():
        parser.error(f"refusing to overwrite output directory: {output}")
    output.mkdir(parents=True)
    result = evaluate(corpus, manifest, product, target, output)
    (output / "oracle-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "checks": result["checks"],
                      "result": str(output / "oracle-result.json")}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
