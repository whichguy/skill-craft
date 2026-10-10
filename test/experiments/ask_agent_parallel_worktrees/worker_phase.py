#!/usr/bin/env python3
"""Run one auditable native-worker phase against its prepared worktree."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import briefs
import diagnostics
import fixture


class PhaseError(RuntimeError):
    def __init__(self, code, message, expected, observed, evidence, *, phase):
        super().__init__(message)
        self.code = code
        self.expected = expected
        self.observed = observed
        self.evidence = [Path(path) for path in evidence]
        self.phase = phase


def _require(condition, code, message, expected, observed, evidence, phase):
    if not condition:
        raise PhaseError(code, message, expected, observed, evidence, phase=phase)


def _read_json(path, code, evidence, phase):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PhaseError(code, f"Cannot read {path}: {exc}", {"readable_json": str(path)},
                         {"error": f"{type(exc).__name__}: {exc}"},
                         [*evidence, path], phase=phase) from exc
    _require(isinstance(value, dict), code, f"Expected a JSON object in {path}",
             {"json_object": True}, {"type": type(value).__name__}, [*evidence, path], phase)
    return value


def _replace_json(path, value):
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _load_context(run, worker_id, phase, cwd, attempt_path):
    manifest_path = run / "manifest.json"
    setup_path = run / "operator" / "setup-result.json"
    evidence = [manifest_path, setup_path, attempt_path]
    manifest = fixture.load_manifest(run)
    count = manifest.get("workers")
    expected_ids = [str(i) for i in range(1, count + 1)] if type(count) is int and count in (3, 5) else []
    tasks = manifest.get("task_assignments")
    ids = [task.get("worker_id") for task in tasks] if isinstance(tasks, list) else []
    _require(manifest.get("schema_version") == 1 and manifest.get("worker_ids") == expected_ids
             and ids == expected_ids and worker_id in expected_ids,
             "MANIFEST_BINDING_INVALID", "Manifest does not define the exact worker assignments",
             {"worker_ids": expected_ids, "selected_worker": worker_id},
             {"worker_ids": manifest.get("worker_ids"), "assignment_ids": ids}, evidence, phase)
    task = fixture.task_for(manifest, worker_id)
    _require(task.get("task_index") == int(worker_id) and task.get("path") == f"src/step_{worker_id}.py",
             "MANIFEST_BINDING_INVALID", "Worker assignment does not own its exact task module",
             {"task_index": int(worker_id), "path": f"src/step_{worker_id}.py"},
             {"task_index": task.get("task_index"), "path": task.get("path")}, evidence, phase)
    setup = _read_json(setup_path, "SETUP_BINDING_INVALID", evidence, phase)
    paths = manifest.get("paths", {})
    run_path_ok = (Path(str(paths.get("run", ""))).is_absolute()
                   and Path(paths["run"]).resolve() == run)
    caller = Path(str(paths.get("caller", ""))).resolve(strict=True)
    primary = Path(str(paths.get("primary", ""))).resolve(strict=True)
    package = Path(str(paths.get("package", ""))).resolve(strict=True)
    snapshot = manifest.get("caller_snapshot", {})
    _require(run_path_ok and setup.get("status") == "PREPARED" and setup.get("phase") == "prepared"
             and setup.get("source") == str(caller) and setup.get("source_head") == snapshot.get("head"),
             "SETUP_BINDING_INVALID", "Setup result is not prepared against this exact manifest and caller",
             {"status": "PREPARED", "phase": "prepared", "source": str(caller),
              "source_head": snapshot.get("head")},
             {"status": setup.get("status"), "phase": setup.get("phase"),
              "source": setup.get("source"), "source_head": setup.get("source_head")}, evidence, phase)

    source_state = fixture.capture_repo_state(caller)
    source_fields = ("root", "branch", "head", "index_path", "index_entries", "index_tree",
                     "cached_diff_sha256", "unstaged_dirty_diffs", "status", "working_tree")
    changed_source = [key for key in source_fields if source_state.get(key) != snapshot.get(key)]
    _require(not changed_source and source_state["head"] == snapshot.get("head")
             and source_state["branch"] == snapshot.get("branch"),
             "CALLER_STATE_CHANGED", "Caller no longer matches the frozen target and dirty snapshot",
             {"unchanged_fields": list(source_fields)}, {"changed_fields": changed_source,
              "head": source_state["head"], "branch": source_state["branch"]}, evidence, phase)

    package_digest = fixture.package_tree_sha256(package)
    frozen_digests = (manifest.get("source", {}).get("package_tree_sha256"),
                      setup.get("frozen_package_tree_sha256_before_preparation"),
                      setup.get("frozen_package_tree_sha256_after_preparation"))
    _require(package_digest and all(value == package_digest for value in frozen_digests),
             "FROZEN_PACKAGE_CHANGED", "Package digest is not identical across manifest and setup receipts",
             {"all_digests": "one identical SHA-256"},
             {"manifest_setup_digests": frozen_digests, "actual": package_digest}, evidence, phase)
    identity = setup.get("package_identity")
    _require(isinstance(identity, dict), "PACKAGE_IDENTITY_INVALID", "Setup result has no package identity",
             {"verified_identity": True}, {"package_identity": identity}, evidence, phase)
    try:
        briefs._validate_identity(identity, manifest, package, evidence)
    except briefs.BriefError as exc:
        raise PhaseError(exc.code, str(exc), exc.expected, exc.observed, exc.evidence, phase=phase) from exc
    package_details = {"package_tree_sha256": package_digest}
    setup_workers = setup.get("workers")
    setup_ids = [item.get("worker_id") for item in setup_workers] if isinstance(setup_workers, list) else []
    _require(setup_ids == expected_ids, "SETUP_BINDING_INVALID", "Setup worker IDs differ from the manifest",
             {"worker_ids": expected_ids}, {"worker_ids": setup_ids}, evidence, phase)
    worker = next(item for item in setup_workers if item.get("worker_id") == worker_id)
    _require(worker.get("package_identity") == identity,
             "PACKAGE_IDENTITY_INVALID", "Worker package identity differs from the setup identity",
             {"package_identity": identity}, {"package_identity": worker.get("package_identity")}, evidence, phase)
    receipt_path = Path(str(worker.get("receipt", ""))).resolve(strict=True)
    receipt = _read_json(receipt_path, "RECEIPT_BINDING_INVALID", [*evidence, receipt_path], phase)
    worktree = Path(str(worker.get("worktree", ""))).resolve(strict=True)
    actual_root = Path(fixture.git(worktree, "rev-parse", "--show-toplevel")).resolve(strict=True)
    actual_branch = fixture.git(worktree, "symbolic-ref", "--quiet", "--short", "HEAD")
    actual_common = fixture.resolve_git_path(worktree, fixture.git(worktree, "rev-parse", "--git-common-dir"))
    expected_common = Path(manifest.get("primary_snapshot", {}).get("common_dir", "")).resolve(strict=True)
    actual_cwd = Path(cwd).resolve(strict=True)
    receipt_ok = (
        receipt.get("schema") == "ask-agent.workspace.receipt.v1" and receipt.get("status") == "prepared"
        and receipt.get("worktree") == str(worktree) and receipt.get("branch") == worker.get("branch") == actual_branch
        and Path(str(receipt.get("source", {}).get("root", ""))).resolve() == caller
        and receipt.get("source", {}).get("head") == snapshot.get("head")
        and Path(str(receipt.get("source", {}).get("common_dir", ""))).resolve() == expected_common
        and receipt.get("baseline") == worker.get("prepared_inspection", {}).get("baseline")
    )
    prepared = worker.get("prepared_inspection")
    prepared_ok = (isinstance(prepared, dict) and set(prepared) == {
        "status", "phase", "receipt", "worktree", "branch", "baseline", "fingerprint",
        "changed_paths", "contribution_paths"
    } and prepared.get("status") == "prepared" and prepared.get("phase") == "prepared"
        and prepared.get("receipt") == str(receipt_path) and prepared.get("worktree") == str(worktree)
        and prepared.get("branch") == actual_branch and prepared.get("baseline") == receipt.get("baseline")
        and prepared.get("changed_paths") == [] and prepared.get("contribution_paths") == [])
    _require(receipt_ok and prepared_ok and actual_root == worktree and actual_cwd == worktree
             and actual_root not in {caller, primary} and actual_common == expected_common,
             "WORKTREE_BINDING_INVALID", "Current process, receipt, helper inspection, and Git root do not bind",
             {"cwd": str(worktree), "root": str(worktree), "branch": worker.get("branch"),
              "common_dir": str(expected_common), "receipt": str(receipt_path),
              "prepared_inspection": True},
             {"cwd": str(actual_cwd), "root": str(actual_root), "branch": actual_branch,
              "common_dir": str(actual_common), "receipt_ok": receipt_ok, "prepared_ok": prepared_ok},
             [*evidence, receipt_path], phase)
    baseline_path = Path(str(receipt.get("baseline", ""))).resolve(strict=True)
    baseline = _read_json(baseline_path, "RECEIPT_BINDING_INVALID",
                          [*evidence, receipt_path, baseline_path], phase)
    baseline_source = baseline.get("source", {})
    baseline_ok = (
        baseline.get("schema") == "ask-agent.workspace.baseline.v1"
        and fixture.sha256_file(baseline_path) == receipt.get("baseline_sha256")
        and Path(str(baseline_source.get("root", ""))).resolve() == caller
        and baseline_source.get("head") == snapshot.get("head")
        and baseline_source.get("branch") == snapshot.get("branch")
        and Path(str(baseline_source.get("common_dir", ""))).resolve() == expected_common
    )
    _require(baseline_ok, "RECEIPT_BINDING_INVALID", "Helper baseline is not bound to the frozen caller",
             {"schema": "ask-agent.workspace.baseline.v1", "source_root": str(caller),
              "source_head": snapshot.get("head"), "sha256": receipt.get("baseline_sha256")},
             {"schema": baseline.get("schema"), "source": baseline_source,
              "sha256": fixture.sha256_file(baseline_path)}, [*evidence, receipt_path, baseline_path], phase)
    current = fixture.capture_repo_state(worktree, worker_mode=True)
    state_checks, state_details = fixture.state_checks(current, manifest, worker_id, phase)
    _require(all(state_checks.values()), "WORKER_STATE_INVALID", "Worktree is outside its allowed phase snapshot",
             {key: True for key in state_checks}, {"checks": state_checks, "details": state_details},
             [*evidence, receipt_path, baseline_path], phase)
    return {
        "manifest": manifest, "task": task, "setup": setup, "worker": worker,
        "identity": identity, "identity_details": package_details,
        "package": package, "receipt_path": receipt_path, "receipt": receipt,
        "baseline_path": baseline_path, "worktree": worktree, "root": actual_root,
        "branch": actual_branch, "target": {"root": str(caller), "head": snapshot["head"],
                                             "branch": snapshot["branch"]},
        "state_checks": state_checks,
    }


def _parse_json_output(call, required, evidence, phase):
    try:
        value = call.get("json")
        if not isinstance(value, dict):
            value = json.loads(call["stdout"])
    except json.JSONDecodeError as exc:
        raise PhaseError("PHASE_OUTPUT_INVALID", f"{call['label']} did not return JSON: {exc}",
                         {"json_object": True}, {"stdout": call["stdout"], "stderr": call["stderr"]},
                         evidence, phase=phase) from exc
    _require(isinstance(value, dict), "PHASE_OUTPUT_INVALID", f"{call['label']} returned non-object JSON",
             {"json_object": True}, {"type": type(value).__name__}, evidence, phase)
    call["json"] = value
    _replace_json(Path(call["evidence"]), call)
    if required:
        _require(call["exit_code"] == 0, "PHASE_COMMAND_FAILED", f"{call['label']} command failed",
                 {"exit_code": 0}, {"exit_code": call["exit_code"], "result": value,
                  "stderr": call["stderr"]}, evidence, phase)
    return value


def _run_command(record, label, argv, cwd, *, require_zero=True):
    calls_dir = Path(record["attempt_path"]) / "calls"
    calls_dir.mkdir(exist_ok=True)
    path = calls_dir / f"{len(record['calls']) + 1:02d}-{label}.json"
    started = time.monotonic()
    call = {
        "schema": "ask-agent.worker-phase-command/v1", "label": label,
        "argv": [str(value) for value in argv], "cwd": str(Path(cwd).resolve()),
        "started_at_utc": _timestamp(), "elapsed_seconds": None,
        "exit_code": None, "stdout": "", "stderr": "", "status": "RUNNING",
    }
    try:
        fixture.write_exclusive_json(path, call)
    except fixture.FixtureError as exc:
        raise PhaseError("PHASE_EVIDENCE_FAILED", f"Cannot reserve evidence for {label}",
                         {"exclusive_call_record": str(path)}, {"error": str(exc)},
                         [record["attempt_path"]], phase=record["phase"]) from exc
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, check=False)
        call.update({"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
                     "status": "COMPLETED"})
        try:
            call["json"] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            call["json_parse_error"] = f"{type(exc).__name__}: {exc}"
    except OSError as exc:
        call.update({"status": "FAILED_TO_START", "error": f"{type(exc).__name__}: {exc}"})
    finally:
        call["elapsed_seconds"] = round(time.monotonic() - started, 6)
        _replace_json(path, call)
    call["evidence"] = str(path.resolve())
    record["calls"].append({"label": label, "evidence": call["evidence"],
                            "exit_code": call["exit_code"], "status": call["status"]})
    _replace_json(Path(record["record_path"]), record)
    if require_zero and call["exit_code"] != 0:
        raise PhaseError("PHASE_COMMAND_FAILED", f"{label} command did not exit zero",
                         {"exit_code": 0}, {"label": label, "exit_code": call["exit_code"],
                          "error": call.get("error"), "stderr": call["stderr"],
                          "call_record": call["evidence"]},
                         [record["record_path"], path], phase=record["phase"])
    return call


def _check_probe(call, context, phase):
    value = _parse_json_output(call, True, [call["evidence"]], phase)
    worker_id = context["task"]["worker_id"]
    valid = (
        value.get("schema_version") == 1 and value.get("run_id") == context["manifest"].get("run_id")
        and value.get("worker_id") == worker_id and value.get("phase") == phase
        and value.get("root") == str(context["root"]) and value.get("cwd") == str(context["root"])
        and value.get("errors") == [] and value.get("marker_intact") is True
        and isinstance(value.get("checks"), dict) and bool(value["checks"])
        and all(flag is True for flag in value["checks"].values())
    )
    _require(valid, "PROBE_FAILED", f"The {phase} probe did not confirm its complete worker snapshot",
             {"run_id": context["manifest"].get("run_id"), "worker_id": worker_id, "phase": phase,
              "root": str(context["root"]), "all_checks_true": True},
             {"run_id": value.get("run_id"), "worker_id": value.get("worker_id"),
              "phase": value.get("phase"), "root": value.get("root"), "errors": value.get("errors"),
              "checks": value.get("checks")}, [call["evidence"]], phase)
    return value


def _compact_binding(context, worker_id, supplied_path, record_path, phase):
    setup = context["setup"]
    worker = context["worker"]
    evidence = [record_path, context["manifest"]["paths"]["package"]]
    _require(setup.get("treatment") == "compact" and isinstance(supplied_path, str),
             "COMPACT_BINDING_REQUIRED", "Compact phases require the compact setup and an explicit binding file",
             {"treatment": "compact", "binding_path": True},
             {"treatment": setup.get("treatment"), "binding_path": supplied_path}, evidence, phase)
    expected_path = Path(str(worker.get("compact_binding_path", ""))).resolve(strict=True)
    supplied = Path(supplied_path).expanduser()
    path = supplied.resolve(strict=True)
    _require(path == expected_path and path.is_file() and not supplied.is_symlink(),
             "COMPACT_BINDING_INVALID", "Worker phase must use its exact retained binding file",
             {"binding_path": str(expected_path)}, {"binding_path": str(path), "symlink": supplied.is_symlink()},
             [*evidence, path], phase)
    binding = _read_json(path, "COMPACT_BINDING_INVALID", [*evidence, path], phase)
    package = binding.get("package", {})
    workspace = binding.get("workspace", {})
    task = binding.get("task", {})
    task_script = Path(str(package.get("task_script", ""))).resolve(strict=True)
    frozen_package = Path(context["package"]).resolve(strict=True)
    identity = context["identity"]
    expected_result = (f"src/step_{worker_id}.py defines transform(x)=({int(worker_id)}+1)*x+"
                       f"{int(worker_id)}*{int(worker_id)} for every integer.")
    checks = {
        "stored_digest_matches": binding.get("binding_sha256") == worker.get("compact_binding_sha256"),
        "objective_matches": task.get("objective") == context["task"]["assignment"],
        "expected_result_matches": task.get("expected_result") == expected_result,
        "edit_mode_matches": task.get("mode") == "edit",
        "write_set_matches": task.get("write_set") == [context["task"]["path"]],
        "worktree_matches": workspace.get("root") == str(context["root"])
        and workspace.get("launch_cwd") == str(context["root"]),
        "receipt_matches": workspace.get("receipt") == str(context["receipt_path"]),
        "baseline_matches": workspace.get("baseline") == str(context["baseline_path"]),
        "branch_matches": workspace.get("branch") == context["branch"],
        "package_card_matches": package.get("resolved_skill_card") == identity.get("resolved_skill_card")
        and package.get("skill_card_sha256") == identity.get("skill_card_sha256"),
        "package_helper_matches": package.get("resolved_helper") == identity.get("resolved_helper")
        and package.get("helper_sha256") == identity.get("helper_sha256"),
        "task_script_inside_frozen_package": task_script == (frozen_package / "scripts" / "ask_agent_task.py").resolve(),
        "task_script_hash_matches": package.get("task_script_sha256") == fixture.sha256_file(task_script),
    }
    _require(all(checks.values()), "COMPACT_BINDING_INVALID",
             f"Compact binding for worker {worker_id} differs from its prepared workspace or package",
             {key: True for key in checks}, checks, [*evidence, path, task_script], phase)
    return path, binding


def _run_compact_worker_command(record, context, binding_path, binding, phase):
    command = "worker-start" if phase == "start" else "worker-finish"
    task_script = binding["package"]["task_script"]
    call = _run_command(record, f"compact-{command}",
                        [sys.executable, "-B", task_script, command, "--binding", str(binding_path)],
                        context["root"])
    result = _parse_json_output(call, True, [record["record_path"], call["evidence"]], phase)
    workspace = result.get("workspace_evidence", {})
    inspection = workspace.get("inspection", {}) if isinstance(workspace, dict) else {}
    inspection = inspection if isinstance(inspection, dict) else {}
    expected_status = "WORKER_CONTEXT_READY" if phase == "start" else "READY_FOR_PARENT_ACCEPTANCE"
    valid = (result.get("status") == expected_status
             and (phase == "start" or result.get("command") == "worker-finish")
             and result.get("binding_sha256") == binding["binding_sha256"]
             and inspection.get("status") == ("prepared" if phase == "start" else "returned")
             and inspection.get("worktree") == str(context["root"])
             and inspection.get("receipt") == str(context["receipt_path"])
             and (phase == "start" or inspection.get("contribution_paths") == [context["task"]["path"]]))
    _require(valid, "COMPACT_WORKER_RESULT_INVALID",
             f"Production {command} did not return the exact worker binding and expected inspection",
             {"status": expected_status, "binding_sha256": binding["binding_sha256"],
              "worktree": str(context["root"]), "receipt": str(context["receipt_path"])},
             {"status": result.get("status"), "command": result.get("command"),
              "binding_sha256": result.get("binding_sha256"), "inspection": inspection},
             [record["record_path"], call["evidence"]], phase)
    return result


def run_phase(run, worker_id, phase, *, cwd=None, compact_binding=None):
    run = Path(run).expanduser().resolve()
    if phase not in {"start", "finish"}:
        raise ValueError("phase must be start or finish")
    if not re.fullmatch(r"[1-5]", str(worker_id)):
        raise ValueError("worker ID must be one digit from 1 to 5")
    worker_id = str(worker_id)
    operator = run / "operator"
    attempt_path = operator / "worker-phases" / f"worker-{worker_id}-{phase}"
    try:
        attempt_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise PhaseError("PHASE_ALREADY_ATTEMPTED", "This worker phase already has a reserved attempt",
                         {"one_attempt_per_worker_phase": str(attempt_path)},
                         {"existing_attempt": str(attempt_path)}, [attempt_path], phase=phase) from exc
    except OSError as exc:
        raise PhaseError("PHASE_RESERVATION_FAILED", "Could not reserve this worker phase",
                         {"exclusive_attempt_directory": str(attempt_path)},
                         {"error": f"{type(exc).__name__}: {exc}"}, [operator], phase=phase) from exc

    record_path = attempt_path / "attempt.json"
    record = {
        "schema": "ask-agent.worker-phase/v1", "run_id": None, "worker_id": worker_id,
        "phase": phase, "status": "RUNNING", "started_at_utc": _timestamp(),
        "started_monotonic_seconds": time.monotonic(), "attempt_path": str(attempt_path),
        "record_path": str(record_path), "cwd": str(Path(cwd or Path.cwd()).resolve()),
        "calls": [], "checks": {}, "errors": [],
    }
    fixture.write_exclusive_json(record_path, record)
    phase_error = None
    try:
        context = _load_context(run, worker_id, phase, record["cwd"], record_path)
        record["run_id"] = context["manifest"]["run_id"]
        record.update({"root": str(context["root"]), "branch": context["branch"],
                       "receipt": str(context["receipt_path"]), "baseline": str(context["baseline_path"]),
                       "package_tree_sha256": context["identity_details"]["package_tree_sha256"],
                       "target": context["target"], "binding_checks": context["state_checks"]})
        _replace_json(record_path, record)
        compact_path = None
        compact_value = None
        if compact_binding is not None or context["setup"].get("treatment") == "compact":
            compact_path, compact_value = _compact_binding(
                context, worker_id, compact_binding, record_path, phase
            )
            record.update({"compact_binding_path": str(compact_path),
                           "compact_binding_sha256": compact_value["binding_sha256"]})
            _replace_json(record_path, record)
        helper = context["identity"]["resolved_helper"]
        receipt = str(context["receipt_path"])
        current_cwd = context["root"]
        if phase == "start":
            if compact_value is not None:
                compact_result = _run_compact_worker_command(
                    record, context, compact_path, compact_value, phase
                )
                record["compact_worker_result"] = compact_result
                record["checks"]["production_worker_start_passed"] = True
                _replace_json(record_path, record)
            check_call = _run_command(record, "check-context", [sys.executable, "-B", helper,
                                         "check-context", "--receipt", receipt], current_cwd)
            check_value = _parse_json_output(check_call, True, [record_path, check_call["evidence"]], phase)
            check_ok = (check_value.get("status") == "verified"
                        and check_value.get("actual_cwd") == str(context["root"])
                        and check_value.get("git_root") == str(context["root"])
                        and check_value.get("receipt") == receipt
                        and check_value.get("worktree") == str(context["root"])
                        and check_value.get("branch") == context["branch"]
                        and check_value.get("head") == context["target"]["head"])
            _require(check_ok, "FRESH_CONTEXT_INVALID", "Bound helper did not confirm the exact current worker context",
                     {"status": "verified", "actual_cwd": str(context["root"]),
                      "git_root": str(context["root"]), "receipt": receipt,
                      "head": context["target"]["head"]},
                     {key: check_value.get(key) for key in
                      ("status", "actual_cwd", "git_root", "receipt", "worktree", "branch", "head")},
                     [record_path, check_call["evidence"]], phase)
            record["checks"]["helper_context_verified"] = True
            _replace_json(record_path, record)
        else:
            check_call = _run_command(record, "worker-check", [sys.executable, "-B", "checks.py",
                                         "--worker", worker_id], current_cwd)
            record["checks"]["worker_check_passed"] = check_call["exit_code"] == 0
            _replace_json(record_path, record)
            if compact_value is not None:
                compact_result = _run_compact_worker_command(
                    record, context, compact_path, compact_value, phase
                )
                record["compact_worker_result"] = compact_result
                record["checks"]["production_worker_finish_passed"] = True
                _replace_json(record_path, record)
        probe_argv = [sys.executable, "-B", str(Path(fixture.__file__).resolve()), "probe",
                      "--run", str(run), "--worker", worker_id, "--phase", phase]
        probe_call = _run_command(record, "probe", probe_argv, current_cwd)
        probe = _check_probe(probe_call, context, phase)
        record["checks"]["fixture_probe_passed"] = True
        record["probe"] = probe
        _replace_json(record_path, record)
        patch_path = None
        patch_sha256 = None
        if phase == "finish":
            artifact = ".experiment-local/owner.txt"
            inspect_call = _run_command(record, "inspect-returned", [sys.executable, "-B", helper,
                                                "inspect", "--receipt", receipt, "--phase", "returned",
                                                "--delivery-mode", "patch", "--artifact", artifact], current_cwd)
            inspected = _parse_json_output(inspect_call, True, [record_path, inspect_call["evidence"]], phase)
            evidence_value = inspected.get("evidence")
            patch_value = evidence_value.get("contribution_patch") if isinstance(evidence_value, dict) else None
            delivery = inspected.get("delivery")
            valid_inspection = (
                inspected.get("status") == "returned" and inspected.get("phase") == "returned"
                and inspected.get("receipt") == receipt and inspected.get("worktree") == str(context["root"])
                and inspected.get("branch") == context["branch"]
                and inspected.get("contribution_paths") == [context["task"]["path"]]
                and context["task"]["path"] in inspected.get("changed_paths", [])
                and inspected.get("artifacts") == [artifact]
                and isinstance(delivery, dict) and delivery.get("mode") == "patch"
                and delivery.get("contribution_paths") == [context["task"]["path"]]
                and delivery.get("contribution_patch") == patch_value
                and isinstance(patch_value, str) and Path(patch_value).is_file()
            )
            _require(valid_inspection, "RETURNED_INSPECTION_INVALID",
                     "Returned helper inspection does not bind a sole owned-source patch",
                     {"status": "returned", "phase": "returned", "contribution_paths": [context["task"]["path"]],
                      "artifact": artifact, "patch_file": True},
                     {"inspection": inspected}, [record_path, inspect_call["evidence"]], phase)
            patch_path = str(Path(patch_value).resolve())
            patch_sha256 = fixture.sha256_file(Path(patch_path))
            record["checks"]["returned_patch_bound"] = True
            record["returned_inspection"] = inspected
        record["checks"]["phase_passed"] = all(record["checks"].values())
        record["status"] = "PASSED"
        record["finished_at_utc"] = _timestamp()
        record["elapsed_seconds"] = round(time.monotonic() - record["started_monotonic_seconds"], 6)
        record["patch_path"] = patch_path
        record["patch_sha256"] = patch_sha256
        _replace_json(record_path, record)
    except PhaseError as exc:
        phase_error = exc
    except Exception as exc:
        phase_error = PhaseError("WORKER_PHASE_FAILED", f"{type(exc).__name__}: {exc}",
                                 {"phase_passed": True},
                                 {"error": f"{type(exc).__name__}: {exc}"}, [record_path], phase=phase)
    if phase_error:
        record["status"] = "FAILED"
        record["errors"].append({"code": phase_error.code, "message": str(phase_error),
                                  "expected": phase_error.expected, "observed": phase_error.observed})
        record["finished_at_utc"] = _timestamp()
        record["elapsed_seconds"] = round(time.monotonic() - record["started_monotonic_seconds"], 6)
        try:
            _replace_json(record_path, record)
        except OSError:
            pass
        phase_error.evidence = list(dict.fromkeys([*phase_error.evidence, record_path]))
        raise phase_error
    return {
        "status": record["status"], "run_id": record["run_id"], "worker_id": worker_id,
        "phase": phase, "root": record.get("root"), "branch": record.get("branch"),
        "receipt": record.get("receipt"), "baseline": record.get("baseline"),
        "package_tree_sha256": record.get("package_tree_sha256"),
        "checks": record["checks"], "patch_path": record.get("patch_path"),
        "patch_sha256": record.get("patch_sha256"), "evidence": str(record_path.resolve()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--worker", required=True)
    parser.add_argument("--phase", required=True, choices=("start", "finish"))
    parser.add_argument("--compact-binding", help="exact retained production binding for compact treatment")
    args = parser.parse_args(argv)
    run = Path(args.run).expanduser().resolve()
    try:
        result = run_phase(run, args.worker, args.phase, compact_binding=args.compact_binding)
    except Exception as exc:
        if isinstance(exc, PhaseError):
            error = exc
        else:
            error = PhaseError("WORKER_PHASE_FAILED", f"{type(exc).__name__}: {exc}",
                               {"phase_passed": True}, {"error": f"{type(exc).__name__}: {exc}"},
                               [run / "manifest.json"], phase=args.phase)
        diagnostic = diagnostics.make_diagnostic(
            code=error.code, severity="error", phase=f"worker-{args.phase}",
            expected=error.expected, observed=error.observed,
            rationale="Worker evidence is accepted only when the current process, frozen run, helper receipt, probe, and owned task all agree.",
            rationale_ref="CONTRACT.md#evidence-references",
            evidence=[diagnostics.evidence_reference(path) for path in error.evidence],
            recovery="Preserve the attempt, child worktree, and all command outputs; reconcile the evidence before using a fresh run.",
            retry_safety="This worker phase is reserved once per run. Do not rerun it or overwrite its evidence; reconcile in a fresh run.",
        )
        diagnostics.exit_with_diagnostic(diagnostic)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
