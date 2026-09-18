#!/usr/bin/env python3
"""Independent deterministic checks for generalized-discovery fixtures.

This module calibrates public fixture observations and records arm evidence. It
does not grade report prose; a blinded reviewer owns that semantic judgement.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Mapping


PROBES = {
    "f1": ("dependency", "permissions", "export"),
    "f2": ("runtime", "retry"),
    "f3": ("metadata", "task-data", "connectors"),
    "f4": ("completion-order", "storage", "component"),
}
ALTERED_CHECK = {
    "f1": "active_differs_from_manifest",
    "f2": "single_recorded_effect_after_retry",
    "f3": "task_data_denied",
    "f4": "old_response_rejected",
}

# Frozen into calibration output outside worker roots. grade_arm does not search
# report text for these facts; blind reviewers own that semantic judgement.
RUBRIC = {
    "f1": {
        "expected": ["selected bundled parser differs from manifest", "atomic export wrapper", "local file boundary"],
        "evidence": ["pyproject.toml", "bin/run_export.py", "runtime/parser.py", "app/export_writer.py", "probe.py dependency/export/permissions"],
        "allowed_unresolved": ["No remote service, browser, or MCP application role is supplied."],
    },
    "f2": {
        "expected": ["receipt.created producer to selected consumer", "schema-2 compatibility", "producer acknowledgement differs from modeled retry completion"],
        "evidence": ["producer/manifest.json", "host/selection.json", "worker.py", "probe.py runtime/retry"],
        "allowed_unresolved": ["Configured consumerRuntime is not proof of the probe interpreter or deployed host.", "The in-memory effect model is not proof of persistent storage."],
    },
    "f3": {
        "expected": ["metadata operation succeeds", "task-data operation is denied for scope_required", "advertised connector is unrelated"],
        "evidence": ["target_simulator.py", "connectors/catalog.json", "probe.py metadata/task-data/connectors"],
        "allowed_unresolved": ["The local simulation proves no real account, identity, permission, or hosted target behavior."],
    },
    "f4": {
        "expected": ["sequence guard rejects older completion in the local model", "BoardPanel is the existing presentation component", "store and one local cache-hit model have distinct roles"],
        "evidence": ["web/client.js", "client_model.py", "web/components/board_panel.js", "service/store.py", "service/cache.py", "probe.py completion-order/storage/component"],
        "allowed_unresolved": ["No browser rendering, network timing, deployed service, cache expiry, or user access is established."],
    },
}


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hashes(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): _sha_bytes(p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file()}


def _tree_hash(hashes: Mapping[str, str]) -> str:
    payload = "".join(f"{name}\0{digest}\n" for name, digest in sorted(hashes.items()))
    return _sha_bytes(payload.encode())


def _load_fixtures(path: Path):
    spec = importlib.util.spec_from_file_location("generalized_discovery_fixtures", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load fixtures from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_probes(root: Path, family: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    observations: dict[str, Any] = {}
    records: dict[str, dict[str, Any]] = {}
    for name in PROBES[family]:
        argv = [sys.executable, "probe.py", name]
        completed = subprocess.run(argv, cwd=root, text=True, capture_output=True, timeout=15, check=False)
        parsed: Any = None
        error = None
        try:
            parsed = json.loads(completed.stdout)
            if not isinstance(parsed, dict):
                error = "stdout_json_is_not_object"
        except json.JSONDecodeError as exc:
            error = f"invalid_json: {exc.msg}"
        records[name] = {
            "argv": argv,
            "cwd": str(root),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "stdout_sha256": _sha_bytes(completed.stdout.encode()),
            "json": parsed,
            "parse_error": error,
        }
        if completed.returncode == 0 and error is None:
            observations[name] = parsed
    return observations, records


def _checks(family: str, observation: Mapping[str, Any], root: Path) -> dict[str, bool]:
    get = lambda name: observation.get(name) if isinstance(observation.get(name), dict) else {}
    if family == "f1":
        declared = re.search(r"record-parser==([^\"\s]+)", (root / "pyproject.toml").read_text())
        dependency, permissions, export = get("dependency"), get("permissions"), get("export")
        return {
            "selected_launcher": dependency.get("launcher") == "bin/run_export.py",
            "active_differs_from_manifest": bool(declared) and dependency.get("active_parser_version") != declared.group(1),
            "atomic_dry_run_wrapper": export.get("write_mode") == "atomic_wrapper" and export.get("committed") is False,
            "local_permission_observation": permissions.get("directory_mode") == "0o750" and permissions.get("writable") is True,
        }
    if family == "f2":
        selected = json.loads((root / "host" / "selection.json").read_text())
        producer = json.loads((root / "producer" / "manifest.json").read_text())
        runtime, retry = get("runtime"), get("retry")
        return {
            "host_selection_observed": runtime.get("consumer_runtime") == selected.get("consumerRuntime") and runtime.get("selected_component") == selected.get("component"),
            "schema_compatible": runtime.get("supported_schema") == producer.get("payloadSchema"),
            "producer_ack_is_distinct_from_local_recording": retry.get("producer_ack") == "accepted" and retry.get("consumer_completion") == "recorded_locally" and retry.get("consumer_attempts") == 2,
            "single_recorded_effect_after_retry": retry.get("recorded_effects") == 1,
        }
    if family == "f3":
        metadata, data, connectors = get("metadata"), get("task-data"), get("connectors")
        target = metadata.get("target")
        listed = connectors.get("connectors") if isinstance(connectors.get("connectors"), list) else []
        return {
            "metadata_available": metadata.get("status") == "ok" and bool(target),
            "task_data_denied": data.get("status") == "denied" and data.get("reason") == "scope_required" and data.get("target") == target,
            "connector_is_unrelated": bool(listed) and all(item.get("target") != target for item in listed if isinstance(item, dict)),
        }
    completion, storage, component = get("completion-order"), get("storage"), get("component")
    order = completion.get("completion_order") if isinstance(completion.get("completion_order"), list) else []
    newer, older = (order + [{}, {}])[:2]
    return {
        "old_response_rejected": newer.get("applied") is True and older.get("applied") is False and completion.get("rendered_version") == newer.get("rendered_version"),
        "store_cache_roles_observed": storage.get("first_read_cache_hit") is False and storage.get("second_read_cache_hit") is True and storage.get("cache_ttl_seconds") == 30,
        "existing_component_observed": component.get("component") == "BoardPanel" and component.get("stylesheet") == "web/styles/board-panel.css",
    }


def calibrate(fixtures_path: Path, contracts_path: Path) -> dict[str, Any]:
    fixtures = _load_fixtures(fixtures_path)
    bindings = {str(path.name): _sha_bytes(path.read_bytes()) for path in (fixtures_path, contracts_path, Path(__file__))}
    families: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="shiploop-generalized-oracle-") as temporary:
        base = Path(temporary)
        for family in PROBES:
            reference_root, altered_root = base / f"{family}-reference", base / f"{family}-altered"
            try:
                fixtures.materialize(family, reference_root, mutant=False)
                reference_hashes = _hashes(reference_root)
                reference_observations, reference_records = _run_probes(reference_root, family)
                reference_checks = _checks(family, reference_observations, reference_root)
                fixtures.materialize(family, altered_root, mutant=True)
                altered_hashes = _hashes(altered_root)
                altered_observations, altered_records = _run_probes(altered_root, family)
                altered_checks = _checks(family, altered_observations, altered_root)
                families[family] = {
                    "reference": {"tree_sha256": _tree_hash(reference_hashes), "file_hashes": reference_hashes, "observations": reference_records, "checks": reference_checks, "passed": all(reference_checks.values())},
                    "altered_variant": {"tree_sha256": _tree_hash(altered_hashes), "file_hashes": altered_hashes, "observations": altered_records, "checks": altered_checks, "changed_observation": ALTERED_CHECK[family], "changed_observation_detected": not altered_checks.get(ALTERED_CHECK[family], False)},
                }
            except Exception as exc:
                families[family] = {"error": f"{type(exc).__name__}: {exc}", "reference": {"passed": False}, "altered_variant": {"changed_observation_detected": False}}
    passed = all(entry.get("reference", {}).get("passed") and entry.get("altered_variant", {}).get("changed_observation_detected") for entry in families.values())
    return {"schema": "generalized-discovery-oracle/1", "mode": "calibration", "bindings": bindings, "rubric": RUBRIC, "families": families, "passed": passed, "interpretation": "Altered variants demonstrate observable-state discrimination only; they do not establish universal correctness or report quality."}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _hash_map(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        return value
    if isinstance(value, dict):
        for key in ("files", "hashes"):
            found = _hash_map(value.get(key))
            if found is not None:
                return found
    return None


def _context_outcome(context: Any) -> dict[str, Any]:
    value = context if isinstance(context, dict) else {}
    exit_code = value.get("exit_code")
    termination_reason = value.get("termination_reason")
    elapsed_seconds = value.get("elapsed_seconds")
    final_present = value.get("final_present")
    return {
        "present": isinstance(context, dict),
        "exit_code": exit_code,
        "termination_reason": termination_reason,
        "elapsed_seconds": elapsed_seconds,
        "final_present": final_present,
        "successful": isinstance(exit_code, int) and not isinstance(exit_code, bool) and exit_code == 0 and termination_reason is None and final_present is True,
    }


def _frozen_input_validation(study: Path) -> dict[str, Any]:
    helper_path = Path(__file__).with_name("study_inputs.py")
    try:
        spec = importlib.util.spec_from_file_location("generalized_discovery_study_inputs", helper_path)
        if spec is None or spec.loader is None:
            raise ValueError("study input validator is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = module.validate_study_inputs(study)
        if not isinstance(manifest, dict) or not manifest or any(not isinstance(path, str) or not isinstance(digest, str) for path, digest in manifest.items()):
            raise ValueError("study input validator returned an invalid manifest")
        return {"passed": True, "validated_file_count": len(manifest), "manifest": manifest}
    except Exception as exc:
        return {"passed": False, "input_validation_error": f"{type(exc).__name__}: {exc}"}


def _matching_probe(family: str, command: str | None, actual: Any, expected: Any, workspace: Path) -> bool | None:
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return None
    if family == "f1" and command == "export":
        target = actual.get("target")
        try:
            target_in_workspace = Path(target).resolve().is_relative_to(workspace.resolve()) if isinstance(target, str) else False
        except OSError:
            target_in_workspace = False
        return target_in_workspace and all(actual.get(key) == expected.get(key) for key in ("operation", "rows", "write_mode", "committed"))
    keys = ("operation", "directory_mode", "writable") if family == "f1" and command == "permissions" else tuple(expected)
    return all(actual.get(key) == expected.get(key) for key in keys)


def _documented_probe(argv: Any, family: str) -> str | None:
    if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv) or not argv:
        return None
    executable = Path(argv[0]).name.lower()
    if not executable.startswith("python"):
        return None
    index = 1
    while index < len(argv) and argv[index] == "-B":
        index += 1
    if len(argv) != index + 2 or argv[index] not in {"probe.py", "./probe.py"}:
        return None
    command = argv[index + 1]
    return command if command in PROBES.get(family, ()) else None


def _receipt_probes(receipts: Path, arm: str, family: str | None, expected: Mapping[str, Any], workspace: Path) -> dict[str, Any]:
    observed: list[dict[str, Any]] = []
    unrecognized: list[dict[str, Any]] = []
    errors: list[str] = []
    arm_receipt_count = 0
    if not receipts.is_file():
        return {"available": False, "observed": observed, "unrecognized_execs": unrecognized, "errors": ["receipt_file_missing"], "all_observed_match_calibration": None, "receipt_evidence_ok": False}
    for number, line in enumerate(receipts.read_text().splitlines(), 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"line_{number}: invalid_json")
            continue
        if not isinstance(record, dict) or record.get("arm") != arm or record.get("event") != "workspace_call":
            continue
        arm_receipt_count += 1
        arguments = record.get("request", {}).get("arguments", {})
        argv = arguments.get("argv") if isinstance(arguments, dict) else None
        if not isinstance(argv, list) or arguments.get("operation") != "exec":
            continue
        command = _documented_probe(argv, family or "")
        if command is None:
            executable = Path(argv[0]).name if argv and isinstance(argv[0], str) else None
            unrecognized.append({"line": number, "classification": "unrecognized_exec_not_scored", "executable": executable, "argc": len(argv)})
            continue
        result = record.get("result") if isinstance(record.get("result"), dict) else {}
        stdout = result.get("stdout")
        failed = record.get("is_error") is True or (isinstance(result.get("exit_code"), int) and not isinstance(result.get("exit_code"), bool) and result["exit_code"] != 0)
        try:
            payload = json.loads(stdout) if isinstance(stdout, str) else None
        except json.JSONDecodeError:
            payload = None
        expected_payload = expected.get(command, {}).get("json")
        matched = _matching_probe(family or "", command, payload, expected_payload, workspace) if expected_payload is not None and not failed else False
        if failed:
            errors.append(f"line_{number}: probe_execution_error")
        elif payload is None:
            errors.append(f"line_{number}: probe_output_unavailable")
        elif expected_payload is None:
            errors.append(f"line_{number}: calibration_observation_missing")
        elif matched is False:
            errors.append(f"line_{number}: probe_output_mismatch")
        observed.append({"line": number, "command": command, "stdout_json": payload, "execution_error": failed, "matches_calibration": matched})
    matches = [entry["matches_calibration"] for entry in observed if entry["matches_calibration"] is not None]
    if not arm_receipt_count:
        errors.append("arm_receipts_missing")
    return {"available": True, "arm_receipt_count": arm_receipt_count, "observed": observed, "unrecognized_execs": unrecognized, "errors": errors, "all_observed_match_calibration": all(matches) if matches else None, "receipt_evidence_ok": not errors, "not_required_to_run_every_probe": True}


def grade_arm(study: str | Path, arm: str, receipt_path: str | Path | None = None) -> dict[str, Any]:
    study_path, arm_path = Path(study).resolve(), Path(study).resolve() / "arms" / arm
    workspace, run = arm_path / "workspace", arm_path / "run"
    initial = _hash_map(_read_json(arm_path / "input-hashes.json"))
    pre = _hash_map(_read_json(run / "input-hashes-pre.json"))
    post = _hash_map(_read_json(run / "input-hashes-post.json"))
    unchanged = {name: post.get(name) == digest for name, digest in initial.items()} if initial is not None and post is not None else {}
    metadata = _read_json(run / "metadata.json")
    family = metadata.get("family") if isinstance(metadata, dict) else None
    if family not in PROBES:
        state = _read_json(study_path / "study.json") or {}
        family = (state.get("arms", {}).get(arm, {}) if isinstance(state, dict) else {}).get("family")
    calibration = _read_json(study_path / "private" / "oracle-calibration.json") or {}
    expected = calibration.get("families", {}).get(family, {}).get("reference", {}).get("observations", {}) if isinstance(calibration, dict) else {}
    receipts = Path(receipt_path) if receipt_path else study_path / "receipts.jsonl"
    report = workspace / "REPORT.md"
    contexts = metadata.get("contexts") if isinstance(metadata, dict) and isinstance(metadata.get("contexts"), list) else []
    runtime = _context_outcome(contexts[0] if contexts else None)
    source_integrity_ok = bool(initial) and pre == initial and post is not None and all(unchanged.values()) and not bool(metadata.get("fixture_edits_flagged")) if isinstance(metadata, dict) else False
    receipts_result = _receipt_probes(receipts, arm, family, expected, workspace)
    frozen_input_validation = _frozen_input_validation(study_path)
    calibration_ready = calibration.get("passed") is True and family in PROBES and bool(expected)
    report_present = report.is_file() and not report.is_symlink() and bool(report.read_text().strip())
    return {
        "schema": "generalized-discovery-oracle-arm/1",
        "arm": arm,
        "family": family,
        "completion": {"metadata_present": isinstance(metadata, dict), "report_present": report_present, "runner_report": metadata.get("report") if isinstance(metadata, dict) else None, "runtime": runtime, "report_is_not_execution_success": True},
        "source_integrity": {"initial_matches_pre": pre == initial if initial is not None and pre is not None else None, "provided_files_unchanged": all(unchanged.values()) if initial is not None and post is not None else None, "changed_files": [name for name, same in unchanged.items() if not same], "runner_fixture_edits": metadata.get("fixture_edits") if isinstance(metadata, dict) else None, "successful": source_integrity_ok},
        "coordinator_receipts": receipts_result,
        "frozen_input_validation": frozen_input_validation,
        "calibration_ready": calibration_ready,
        "deterministic_evidence_ready": runtime["successful"] and source_integrity_ok and receipts_result["receipt_evidence_ok"] and frozen_input_validation["passed"] and calibration_ready and report_present,
        "semantic_report_judgement": "not performed here; blinded review must assess evidence, N/A decisions, reuse, and bounded stopping without arm/variant labels.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--study", type=Path)
    parser.add_argument("--arm")
    parser.add_argument("--receipts", type=Path)
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).with_name("fixtures.py"))
    parser.add_argument("--contracts", type=Path, default=Path(__file__).with_name("PUBLIC_CONTRACTS.md"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.calibrate:
        result = calibrate(args.fixtures.resolve(), args.contracts.resolve())
        status = 0 if result["passed"] else 1
    elif args.study and args.arm:
        result = grade_arm(args.study, args.arm, args.receipts)
        status = 0 if result["deterministic_evidence_ready"] else 2
    else:
        parser.error("use --calibrate or both --study and --arm")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "passed": result.get("passed", result.get("deterministic_evidence_ready"))}))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
