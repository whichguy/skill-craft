#!/usr/bin/env python3
"""Build compact, binding-checked native worker arguments for a prepared run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import uuid

import diagnostics
import fixture

IDENTITY_FIELDS = (
    "schema", "status", "version", "skill_card", "resolved_skill_card",
    "resolved_helper", "skill_card_sha256", "helper_sha256",
)


class BriefError(RuntimeError):
    def __init__(self, code, message, expected, observed, evidence, phase="brief-preflight"):
        super().__init__(message)
        self.code = code
        self.phase = phase
        self.expected = expected
        self.observed = observed
        self.evidence = [Path(path) for path in evidence]


def _fail(code, message, expected, observed, evidence, phase="brief-preflight"):
    raise BriefError(code, message, expected, observed, evidence, phase)


def _read_json(path, code, evidence):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _fail(code, f"Cannot read {path}: {exc}", {"readable_json": str(path)},
              {"error": f"{type(exc).__name__}: {exc}"}, [*evidence, path])


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _absolute(value):
    return isinstance(value, str) and Path(value).is_absolute()


def _check(condition, code, message, expected, observed, evidence):
    if not condition:
        _fail(code, message, expected, observed, evidence)


def _fresh_prepared_inspection(run, inspection_dir, worker_id, helper, receipt, worktree,
                               branch, baseline, prior_inspection, evidence):
    path = inspection_dir / f"worker-{worker_id}.json"
    argv = [sys.executable, "-B", helper, "inspect", "--receipt", receipt, "--phase", "prepared"]
    record = {
        "schema": "ask-agent.prepared-inspection-evidence/v1",
        "attempt_id": inspection_dir.name,
        "worker_id": worker_id,
        "purpose": "fresh prepared-state inspection; patch delivery mode applies on returned inspection",
        "argv": argv,
        "cwd": str(worktree),
        "exit_code": None,
        "stdout": "",
        "stderr": "",
    }
    try:
        result = fixture.run_process(argv, cwd=worktree, check=False, timeout=20)
        record.update({"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    except fixture.FixtureError as exc:
        record["error"] = str(exc)
    parsed = None
    try:
        parsed = json.loads(record["stdout"])
    except ValueError as exc:
        record["parse_error"] = f"{type(exc).__name__}: {exc}"
    if isinstance(parsed, dict):
        record["result"] = parsed
    try:
        fixture.write_exclusive_json(path, record)
    except fixture.FixtureError as exc:
        _fail("WORKER_INSPECTION_EVIDENCE_FAILED", f"Could not retain worker {worker_id} inspection evidence",
              {"exclusive_evidence_path": str(path)}, {"error": str(exc)}, [*evidence, path])

    expected = {
        "status": "prepared", "phase": "prepared", "receipt": str(Path(receipt).resolve()),
        "worktree": str(worktree), "branch": branch, "baseline": str(Path(baseline).resolve()),
        "fingerprint": prior_inspection.get("fingerprint"),
        "changed_paths": [], "contribution_paths": [],
    }
    prior_keys_match = isinstance(prior_inspection, dict) and set(prior_inspection) == set(expected)
    prior_checks = ({key: prior_inspection.get(key) == value for key, value in expected.items()}
                    if isinstance(prior_inspection, dict) else {})
    result_keys_match = isinstance(parsed, dict) and set(parsed) == set(expected)
    field_checks = ({key: parsed.get(key) == value for key, value in expected.items()}
                    if isinstance(parsed, dict) else {})
    valid = (record["exit_code"] == 0 and isinstance(parsed, dict)
             and prior_keys_match and all(prior_checks.values())
             and result_keys_match and all(field_checks.values()))
    _check(valid, "WORKER_PREPARED_INSPECTION_FAILED",
           f"Worker {worker_id} fresh helper inspection did not confirm the complete prepared baseline",
           {"exit_code": 0, "exact_fields": expected},
           {"exit_code": record["exit_code"], "prior_keys_match": prior_keys_match,
            "prior_checks": prior_checks, "result_keys_match": result_keys_match,
            "field_checks": field_checks,
            "result": parsed, "stderr": record["stderr"], "error": record.get("error"),
            "parse_error": record.get("parse_error")}, [*evidence, path])
    return {"result": parsed, "evidence": str(path.resolve())}


def _validate_identity(identity, manifest, package, evidence):
    missing = [key for key in IDENTITY_FIELDS if not isinstance(identity.get(key), str) or not identity[key]]
    _check(not missing, "BRIEF_PACKAGE_IDENTITY_INVALID", "Prepared package identity is incomplete",
           {"required_fields": list(IDENTITY_FIELDS)}, {"missing_fields": missing}, evidence)
    _check(identity["schema"] == "ask-agent.skill.identity.v1" and identity["status"] == "verified",
           "BRIEF_PACKAGE_IDENTITY_INVALID", "Prepared package identity is not verified",
           {"schema": "ask-agent.skill.identity.v1", "status": "verified"},
           {"schema": identity["schema"], "status": identity["status"]}, evidence)
    card = Path(identity["resolved_skill_card"])
    helper = Path(identity["resolved_helper"])
    try:
        card_resolved = card.resolve(strict=True)
        helper_resolved = helper.resolve(strict=True)
        package_resolved = package.resolve(strict=True)
        card_resolved.relative_to(package_resolved)
        helper_resolved.relative_to(package_resolved)
    except (OSError, ValueError) as exc:
        _fail("BRIEF_PACKAGE_IDENTITY_INVALID", "Selected identity paths are outside the frozen package",
              {"resolved_card_and_helper_inside": str(package)}, {"error": f"{type(exc).__name__}: {exc}"},
              [*evidence, card, helper])
    selected_card = Path(identity["skill_card"])
    _check(selected_card.is_absolute() and selected_card.resolve() == card_resolved,
           "BRIEF_PACKAGE_IDENTITY_INVALID", "Selected and resolved card paths do not bind",
           {"selected_card_resolves_to": str(card_resolved)}, {"skill_card": identity["skill_card"]}, evidence)
    expected_card_name = manifest.get("source", {}).get("logical_card")
    card_hash = _digest(card_resolved)
    helper_hash = _digest(helper_resolved)
    _check(card_resolved.name == expected_card_name and card_hash == identity["skill_card_sha256"]
           and helper_hash == identity["helper_sha256"],
           "BRIEF_PACKAGE_IDENTITY_INVALID", "Card or helper bytes differ from their verified identity",
           {"logical_card": expected_card_name, "skill_card_sha256": identity["skill_card_sha256"],
            "helper_sha256": identity["helper_sha256"]},
           {"card_name": card_resolved.name, "skill_card_sha256": card_hash, "helper_sha256": helper_hash},
           [*evidence, card_resolved, helper_resolved])
    return identity


def _validate_worker(task, worker, manifest, identity, run, inspection_dir, evidence,
                     seen_roots, seen_indexes, *, fresh_inspection=True):
    worker_id = task["worker_id"]
    _check(task.get("task_index") == int(worker_id)
           and task.get("path") == f"src/step_{worker_id}.py",
           "BRIEF_MANIFEST_INVALID", f"Worker {worker_id} assignment does not own its expected module",
           {"task_index": int(worker_id), "path": f"src/step_{worker_id}.py"},
           {"task_index": task.get("task_index"), "path": task.get("path")}, evidence)
    receipt_value = worker.get("receipt")
    worktree_value = worker.get("worktree")
    _check(_absolute(receipt_value) and _absolute(worktree_value), "BRIEF_BINDING_INVALID",
           f"Worker {worker_id} receipt and worktree must be absolute setup bindings",
           {"absolute_receipt_and_worktree": True}, {"receipt": receipt_value, "worktree": worktree_value}, evidence)
    receipt_path = Path(receipt_value)
    _check(receipt_path.is_file() and not receipt_path.is_symlink(), "BRIEF_RECEIPT_INVALID",
           f"Worker {worker_id} helper receipt is missing or not a regular file",
           {"receipt_file": receipt_value}, {"exists": receipt_path.exists(), "symlink": receipt_path.is_symlink()},
           [*evidence, receipt_path])
    receipt = _read_json(receipt_path, "BRIEF_RECEIPT_INVALID", [*evidence, receipt_path])
    worktree = Path(worktree_value).resolve(strict=True)
    caller = Path(manifest["paths"]["caller"]).resolve(strict=True)
    primary = Path(manifest["paths"]["primary"]).resolve(strict=True)
    snapshot = manifest["caller_snapshot"]
    inspection = worker.get("prepared_inspection")
    expected_inspection = (
        isinstance(inspection, dict) and inspection.get("status") == "prepared"
        and inspection.get("phase") == "prepared" and inspection.get("receipt") == receipt_value
        and Path(str(inspection.get("worktree", ""))).resolve() == worktree
        and inspection.get("branch") == worker.get("branch")
        and inspection.get("changed_paths") == [] and inspection.get("contribution_paths") == []
    )
    _check(expected_inspection, "BRIEF_BINDING_INVALID", f"Worker {worker_id} prepared inspection is not bound",
           {"status": "prepared", "phase": "prepared", "receipt": receipt_value,
            "worktree": str(worktree), "branch": worker.get("branch"), "changed_paths": [],
            "contribution_paths": []}, {"prepared_inspection": inspection}, [*evidence, receipt_path])
    actual_root = Path(fixture.git(worktree, "rev-parse", "--show-toplevel")).resolve(strict=True)
    actual_branch = fixture.git(worktree, "symbolic-ref", "--quiet", "--short", "HEAD")
    actual_common = fixture.resolve_git_path(worktree, fixture.git(worktree, "rev-parse", "--git-common-dir"))
    actual_index = fixture.resolve_git_path(worktree, fixture.git(worktree, "rev-parse", "--git-path", "index"))
    receipt_source = receipt.get("source", {})
    worktree_ok = (
        receipt.get("schema") == "ask-agent.workspace.receipt.v1" and receipt.get("status") == "prepared"
        and Path(str(receipt.get("worktree", ""))).resolve() == worktree == actual_root
        and receipt.get("branch") == worker.get("branch") == actual_branch
        and Path(str(receipt_source.get("root", ""))).resolve() == caller
        and receipt_source.get("head") == snapshot.get("head")
        and Path(str(receipt_source.get("common_dir", ""))).resolve() == actual_common
        and actual_common == Path(manifest["primary_snapshot"]["common_dir"]).resolve()
        and actual_root not in {caller, primary} and actual_root not in seen_roots
        and actual_index not in seen_indexes
    )
    _check(worktree_ok, "BRIEF_WORKTREE_INVALID", f"Worker {worker_id} worktree root or index does not bind",
           {"root": str(worktree), "branch": worker.get("branch"),
            "source_root": str(caller), "source_head": snapshot.get("head"),
            "common_dir": manifest["primary_snapshot"]["common_dir"],
            "distinct_root_and_index": True},
           {"root": str(actual_root), "branch": actual_branch, "common_dir": str(actual_common),
            "index_path": str(actual_index), "receipt_source": receipt_source}, [*evidence, receipt_path])
    seen_roots.add(actual_root)
    seen_indexes.add(actual_index)
    baseline_value = receipt.get("baseline")
    _check(_absolute(baseline_value), "BRIEF_RECEIPT_INVALID", f"Worker {worker_id} receipt omits its actual baseline path",
           {"absolute_baseline_path_in_receipt": True}, {"baseline": baseline_value}, [*evidence, receipt_path])
    baseline_path = Path(baseline_value)
    baseline = _read_json(baseline_path, "BRIEF_RECEIPT_INVALID", [*evidence, receipt_path, baseline_path])
    baseline_hash = _digest(baseline_path)
    baseline_source = baseline.get("source", {})
    baseline_ok = (
        not baseline_path.is_symlink() and baseline_hash == receipt.get("baseline_sha256")
        and baseline.get("schema") == "ask-agent.workspace.baseline.v1"
        and Path(str(baseline_source.get("root", ""))).resolve() == caller
        and baseline_source.get("head") == snapshot.get("head")
        and baseline_source.get("branch") == snapshot.get("branch")
        and Path(str(baseline_source.get("common_dir", ""))).resolve() == actual_common
        and Path(str(receipt.get("store", ""))).resolve() in worktree.parents
    )
    _check(baseline_ok, "BRIEF_RECEIPT_INVALID", f"Worker {worker_id} helper baseline is not receipt-bound",
           {"schema": "ask-agent.workspace.baseline.v1", "sha256": receipt.get("baseline_sha256"),
            "source_root": str(caller), "source_head": snapshot.get("head")},
           {"schema": baseline.get("schema"), "sha256": baseline_hash,
            "source_capture": baseline_source, "store": receipt.get("store")},
           [*evidence, receipt_path, baseline_path])
    worker_identity = worker.get("package_identity")
    _check(worker_identity == identity, "BRIEF_PACKAGE_IDENTITY_INVALID",
           f"Worker {worker_id} identity differs from the setup identity",
           {"package_identity": identity}, {"package_identity": worker_identity}, [*evidence, receipt_path])
    if fresh_inspection:
        fresh = _fresh_prepared_inspection(
            run, inspection_dir, worker_id, identity["resolved_helper"], str(receipt_path.resolve()),
            actual_root, actual_branch, baseline_path, inspection, [*evidence, receipt_path, baseline_path],
        )
    else:
        fresh = {"result": inspection, "evidence": worker.get("compact_prepare_result_path")}
    return {
        "root": str(actual_root), "branch": actual_branch, "receipt": str(receipt_path.resolve()),
        "baseline": str(baseline_path.resolve()), "baseline_sha256": baseline_hash,
        "index_path": actual_index, "fresh_inspection": fresh["result"],
        "fresh_inspection_evidence": fresh["evidence"],
    }


def _prompt(run, task, binding, identity, target, dirty):
    worker_id = task["worker_id"]
    task_id = int(worker_id)
    cwd = binding["root"]
    phase_script = Path(__file__).with_name("worker_phase.py").resolve(strict=True)
    run_arg = os.path.relpath(run, cwd)
    script_arg = os.path.relpath(phase_script, cwd)
    start = f'cd {shlex.quote(cwd)} && PYTHONDONTWRITEBYTECODE=1 ' + shlex.join(
        ["python3", "-B", script_arg, "--run", run_arg, "--worker", worker_id, "--phase", "start"]
    )
    finish = f'cd {shlex.quote(cwd)} && PYTHONDONTWRITEBYTECODE=1 ' + shlex.join(
        ["python3", "-B", script_arg, "--run", run_arg, "--worker", worker_id, "--phase", "finish"]
    )
    status = json.dumps(dirty["status"], sort_keys=True, separators=(",", ":"))
    package_root = Path(identity["resolved_skill_card"]).parent
    package_identity = (
        f"{identity['schema']}/{identity['status']} v{identity['version']}; "
        f"card SKILL.md (selected=resolved; SHA-256 {identity['skill_card_sha256']}); "
        f"helper scripts/ask_agent_workspace.py (SHA-256 {identity['helper_sha256']})"
    )
    hold = " The start hold is overlap instrumentation, not useful work time." if dirty.get("hold_seconds", 0) > 0 else ""
    return f"""Fresh worker; do not rely on parent context. User authorized this fixture/patch experiment. Implement only `{task['path']}` as `transform(x)=({task_id}+1)*x+{task_id}²` for every integer. Only owned source edits; no other roots, staging, commits, integration, settings changes or external services. Retain worktree/evidence.

Frozen package root `{package_root}` tree SHA-256 `{identity['package_tree_sha256']}`; identity `{package_identity}`. Worker Git root `{cwd}`, branch `{binding['branch']}`, receipt `{binding['receipt']}`, baseline `{binding['baseline']}` (SHA-256 `{binding['baseline_sha256']}`). Parent target `{target['root']}` / `{target['branch']}` at pinned HEAD `{target['head']}`. Preserve inherited staged/unstaged/untracked/deleted state `{status}` and index tree `{dirty['index_tree']}`. Delivery is a patch; integration remains pending parent review and combined validation.{hold}

Run start before editing and finish after from bound cwd. Wrappers enforce bindings/cwd and retain exact helper, probe, check and inspect outputs. Start runs helper `check-context`; finish runs your assigned check and inspects the returned patch with `--delivery-mode patch --artifact .experiment-local/owner.txt`. Stop on failure. Use the absolute file-tool path for `{task['path']}` under the bound root.

Start probe: `{start}`
Finish probe: `{finish}`

Report checks, identity, root/branch, receipt/baseline, actual patch path and changed paths, pinned target, pending integration, and blockers. Parent validates/applies the patch; do not propose a branch merge."""


def build_briefs(run, *, compact_prepared=False):
    run = Path(run).expanduser().resolve()
    manifest_path = run / "manifest.json"
    setup_path = run / "operator" / "setup-result.json"
    evidence = [manifest_path, setup_path]
    manifest = _read_json(manifest_path, "BRIEF_MANIFEST_INVALID", evidence)
    setup = _read_json(setup_path, "BRIEF_SETUP_NOT_PREPARED", evidence)
    _check((setup.get("treatment") == "compact") == compact_prepared,
           "BRIEF_SETUP_NOT_PREPARED", "Prepared setup treatment must match the requested brief mode",
           {"compact_prepared": compact_prepared}, {"treatment": setup.get("treatment")}, evidence)
    paths = manifest.get("paths", {})
    caller_value, primary_value, package_value = (paths.get(key) for key in ("caller", "primary", "package"))
    expected_run = str(run)
    ids = manifest.get("worker_ids")
    assignments = manifest.get("task_assignments")
    count = manifest.get("workers")
    expected_ids = [str(i) for i in range(1, count + 1)] if isinstance(count, int) and count in (3, 5) else []
    assignment_ids = [task.get("worker_id") for task in assignments] if isinstance(assignments, list) else []
    assignment_paths = [task.get("path") for task in assignments] if isinstance(assignments, list) else []
    _check(manifest.get("schema_version") == 1 and ids == expected_ids and assignment_ids == expected_ids
           and assignment_paths == [f"src/step_{worker_id}.py" for worker_id in expected_ids]
           and all(_absolute(value) for value in (paths.get("run"), caller_value, primary_value, package_value))
           and Path(paths["run"]).resolve() == run,
           "BRIEF_MANIFEST_INVALID", "Manifest schema, worker assignments, or absolute run paths are invalid",
           {"schema_version": 1, "worker_ids": expected_ids,
            "paths": {"run": expected_run, "caller": "absolute", "primary": "absolute", "package": "absolute"}},
           {"schema_version": manifest.get("schema_version"), "worker_ids": ids,
            "assignment_ids": assignment_ids, "assignment_paths": assignment_paths, "paths": paths}, evidence)
    snapshot = manifest.get("caller_snapshot", {})
    target_root = Path(caller_value).resolve(strict=True)
    target_head = snapshot.get("head")
    target_branch = snapshot.get("branch")
    try:
        current_head = fixture.git(target_root, "rev-parse", "HEAD")
        current_branch = fixture.git(target_root, "symbolic-ref", "--quiet", "--short", "HEAD")
    except fixture.FixtureError as exc:
        _fail("BRIEF_TARGET_MOVED", "Cannot verify the frozen integration target", {"root": caller_value},
              {"error": str(exc)}, evidence)
    _check(current_head == target_head and current_branch == target_branch,
           "BRIEF_TARGET_MOVED", "Integration target no longer matches the manifest pin",
           {"head": target_head, "branch": target_branch},
           {"head": current_head, "branch": current_branch}, evidence)
    _check(setup.get("status") == "PREPARED" and setup.get("phase") == "prepared"
           and setup.get("source") == str(target_root) and setup.get("source_head") == target_head,
           "BRIEF_SETUP_NOT_PREPARED", "Setup result is not prepared against this exact caller target",
           {"status": "PREPARED", "phase": "prepared", "source": str(target_root), "source_head": target_head},
           {key: setup.get(key) for key in ("status", "phase", "source", "source_head")}, evidence)
    state = fixture.capture_repo_state(target_root)
    source_fields = ("root", "branch", "head", "index_path", "index_entries", "index_tree",
                     "cached_diff_sha256", "unstaged_dirty_diffs", "status", "working_tree")
    changed_fields = [key for key in source_fields if state.get(key) != snapshot.get(key)]
    _check(not changed_fields, "BRIEF_TARGET_MOVED", "Caller dirty snapshot changed after preparation",
           {"unchanged_fields": list(source_fields)}, {"changed_fields": changed_fields}, evidence)
    package = Path(package_value).resolve(strict=True)
    package_hash = fixture.package_tree_sha256(package)
    identity = setup.get("package_identity")
    _check(isinstance(identity, dict), "BRIEF_PACKAGE_IDENTITY_INVALID", "Setup has no package identity",
           {"verified_package_identity": True}, {"package_identity": identity}, evidence)
    _validate_identity(identity, manifest, package, evidence)
    expected_package_hash = manifest.get("source", {}).get("package_tree_sha256")
    _check(package_hash == expected_package_hash
           and setup.get("frozen_package_tree_sha256_before_preparation") == package_hash
           and setup.get("frozen_package_tree_sha256_after_preparation") == package_hash,
           "BRIEF_PACKAGE_IDENTITY_INVALID", "Frozen package tree differs from manifest or setup hashes",
           {"package_tree_sha256": expected_package_hash},
           {"actual": package_hash, "setup_before": setup.get("frozen_package_tree_sha256_before_preparation"),
            "setup_after": setup.get("frozen_package_tree_sha256_after_preparation")}, evidence)
    workers = setup.get("workers")
    worker_ids = [worker.get("worker_id") for worker in workers] if isinstance(workers, list) else []
    _check(all(isinstance(worker_id, str) for worker_id in worker_ids)
           and len(worker_ids) == len(expected_ids) and len(set(worker_ids)) == len(worker_ids)
           and set(worker_ids) == set(expected_ids), "BRIEF_SETUP_NOT_PREPARED",
           "Setup worker IDs do not match the unique manifest assignments",
           {"worker_ids": expected_ids}, {"worker_ids": worker_ids}, evidence)
    worker_by_id = {worker["worker_id"]: worker for worker in workers}
    for worker in workers:
        worker_identity = worker.get("package_identity")
        missing = [key for key in IDENTITY_FIELDS
                   if not isinstance(worker_identity, dict)
                   or not isinstance(worker_identity.get(key), str) or not worker_identity[key]]
        _check(not missing, "BRIEF_PACKAGE_IDENTITY_INVALID",
               f"Worker {worker.get('worker_id')} package identity is incomplete",
               {"required_fields": list(IDENTITY_FIELDS)}, {"missing_fields": missing}, evidence)
        _check(worker_identity == identity, "BRIEF_PACKAGE_IDENTITY_INVALID",
               f"Worker {worker.get('worker_id')} identity differs from the verified setup identity",
               {"package_identity": identity}, {"package_identity": worker_identity}, evidence)
    target = {"root": str(target_root), "branch": target_branch, "head": target_head}
    dirty = {"status": snapshot["status"], "index_tree": snapshot["index_tree"],
             "hold_seconds": manifest.get("hold_seconds", 0)}
    inspection_dir = run / "operator" / "prepared-inspection-calls" / uuid.uuid4().hex
    if not compact_prepared:
        try:
            inspection_dir.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            _fail("WORKER_INSPECTION_EVIDENCE_FAILED", "Could not reserve an inspection evidence directory",
                  {"exclusive_directory": str(inspection_dir)}, {"error": f"{type(exc).__name__}: {exc}"}, evidence)
    bindings = {}
    seen_roots, seen_indexes = set(), set()
    for task in assignments:
        worker = worker_by_id[task["worker_id"]]
        bindings[task["worker_id"]] = _validate_worker(
            task, worker, manifest, identity, run, inspection_dir, evidence, seen_roots, seen_indexes,
            fresh_inspection=not compact_prepared,
        )
    prompt_identity = {**identity, "logical_card": manifest["source"]["logical_card"]}
    prompt_identity["package_tree_sha256"] = package_hash
    return [{
        "worker_id": task["worker_id"],
        "native_arguments": {
            "description": f"Implement only {task['path']}: transform(x)=({int(task['worker_id'])}+1)*x+{int(task['worker_id'])}².",
            "prompt": _prompt(run, task, bindings[task["worker_id"]], prompt_identity,
                              target, dirty),
            "cwd": bindings[task["worker_id"]]["root"],
            "background": True,
        },
    } for task in assignments]


def _compact_assignment_prompt(run, task, worker, result, binding):
    worker_id = task["worker_id"]
    binding_path = Path(worker["compact_binding_path"]).resolve(strict=True)
    worktree = Path(worker["worktree"]).resolve(strict=True)
    phase_script = Path(__file__).with_name("worker_phase.py").resolve(strict=True)
    run_arg = os.path.relpath(run, worktree)
    phase_arg = os.path.relpath(phase_script, worktree)
    commands = {}
    for phase in ("start", "finish"):
        commands[phase] = "cd " + shlex.quote(str(worktree)) + " && PYTHONDONTWRITEBYTECODE=1 " + shlex.join(
            ["python3", "-B", phase_arg, "--run", run_arg, "--worker", worker_id,
             "--phase", phase, "--compact-binding", str(binding_path)]
        )
    prompt = result.get("launch", {}).get("prompt")
    script = binding.get("package", {}).get("task_script")
    if not isinstance(prompt, str) or not isinstance(script, str):
        _fail("COMPACT_PREPARE_RESULT_INVALID", "Compact prepare result has an emitted prompt and task script",
              {"launch_prompt": True, "task_script": True},
              {"prompt_type": type(prompt).__name__, "task_script": script},
              [Path(worker["compact_prepare_result_path"]), binding_path])
    direct_commands = {
        phase: shlex.join(["python3", script, f"worker-{phase}", "--binding", "-"])
        for phase in ("start", "finish")
    }
    old_binding_instruction = (
        f"Before any task operation, run `{direct_commands['start']}` from the assigned directory. "
        f"After the work, run `{direct_commands['finish']}` there, supplying the exact binding JSON below to both commands."
    )
    new_binding_instruction = (
        f"Before any task operation, run the start wrapper `{commands['start']}` from the assigned directory. "
        f"After the work and required task test, run the finish wrapper `{commands['finish']}` there. Run the "
        "start wrapper, required task test, and finish wrapper in separate terminal tool invocations. Do not "
        "combine a wrapper with a test, file operation, echo, diagnostics, or another command; the wrapper's "
        "own bound `cd ... &&` prefix is part of that one invocation. The finish wrapper runs its fixture checks "
        "itself, so do not prepend `checks.py` to it. Each wrapper reads the unchanged binding file "
        f"`{binding_path}` and invokes the production task command once; do not execute worker-start or "
        "worker-finish separately."
    )
    _check(prompt.count(old_binding_instruction) == 1, "COMPACT_PREPARE_RESULT_INVALID",
           "Production prompt has one exact stdin-binding instruction to adapt",
           {"instruction_count": 1}, {"instruction_count": prompt.count(old_binding_instruction)},
           [Path(worker["compact_prepare_result_path"]), binding_path])
    for phase in ("start", "finish"):
        direct = direct_commands[phase]
        _check(prompt.count(direct) == 1, "COMPACT_PREPARE_RESULT_INVALID",
               f"Compact prepare prompt must contain exactly one worker-{phase} command",
               {"command": direct, "count": 1}, {"count": prompt.count(direct)},
               [Path(worker["compact_prepare_result_path"]), binding_path])
    prompt = prompt.replace(old_binding_instruction, new_binding_instruction)
    binding_heading = "\n\nBinding JSON (use this exact object on stdin; do not edit it):"
    _check(binding_heading in prompt, "COMPACT_PREPARE_RESULT_INVALID",
           "Compact prompt exposes the complete binding object for durable handoff",
           {"binding_section": True}, {"binding_section": False},
           [Path(worker["compact_prepare_result_path"]), binding_path])
    prompt = prompt.split(binding_heading, 1)[0]
    prompt += (f"\n\nThe exact binding is retained at `{binding_path}` with SHA-256 "
              f"`{binding['binding_sha256']}`. Run the start and finish wrappers as separate single-command "
              "terminal tool invocations. Run the required task test separately before finish; the finish "
              "wrapper runs its fixture checks itself. Each phase wrapper runs the "
              "actual ask_agent_task.py worker-start or worker-finish command exactly once with "
              "`--binding BINDING_PATH` and retains its raw command result. Do not run those production commands "
              f"separately. The wrapper also retains the fixture probes for worker {worker_id}; "
              "finish must run after the edit. Do not add shell commands or debug output to either wrapper call.")
    return prompt


def build_compact_briefs(run):
    """Build small per-worker assignments from production prepare results."""
    run = Path(run).expanduser().resolve()
    setup = _read_json(run / "operator" / "setup-result.json", "BRIEF_SETUP_NOT_PREPARED", [run / "manifest.json"])
    _check(setup.get("treatment") == "compact", "BRIEF_SETUP_NOT_PREPARED",
           "Compact assignments require a setup produced by compact prepare",
           {"treatment": "compact"}, {"treatment": setup.get("treatment")},
           [run / "operator" / "setup-result.json"])
    regular = build_briefs(run, compact_prepared=True)
    manifest = fixture.load_manifest(run)
    setup_workers = {item["worker_id"]: item for item in setup["workers"]}
    regular_by_id = {item["worker_id"]: item["native_arguments"] for item in regular}
    directory = run / "operator" / "compact-dispatch"
    directory.mkdir(exist_ok=False)
    assignments = []
    for task in manifest["task_assignments"]:
        worker_id = task["worker_id"]
        worker = setup_workers[worker_id]
        binding_path = Path(worker["compact_binding_path"])
        result_path = Path(worker["compact_prepare_result_path"])
        binding = _read_json(binding_path, "COMPACT_BINDING_INVALID", [binding_path, result_path])
        result = _read_json(result_path, "COMPACT_PREPARE_RESULT_INVALID", [binding_path, result_path])
        native_arguments = dict(regular_by_id[worker_id])
        _check(binding.get("binding_sha256") == worker.get("compact_binding_sha256")
               and result.get("binding") == binding
               and result.get("status") == "READY_TO_LAUNCH"
               and result.get("launch", {}).get("cwd") == worker.get("worktree")
               and binding.get("task", {}).get("write_set") == [task["path"]]
               and binding.get("workspace", {}).get("root") == worker.get("worktree"),
               "COMPACT_BINDING_INVALID", f"Worker {worker_id} compact binding does not match its prepared assignment",
               {"worker_id": worker_id, "write_set": [task["path"]], "worktree": worker.get("worktree")},
               {"binding_sha256": binding.get("binding_sha256"), "setup_sha256": worker.get("compact_binding_sha256"),
                "write_set": binding.get("task", {}).get("write_set"),
                "worktree": binding.get("workspace", {}).get("root")}, [binding_path, result_path])
        native_arguments["prompt"] = _compact_assignment_prompt(run, task, worker, result, binding)
        native_arguments["cwd"] = worker["worktree"]
        entry = {"worker_id": worker_id, "native_arguments": native_arguments,
                 "binding_sha256": binding["binding_sha256"],
                 "prepare_result_path": str(result_path.resolve())}
        payload = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
        _check(len(payload) <= 20_000, "COMPACT_ASSIGNMENT_TOO_LARGE",
               "One compact native assignment must fit the observed complete tool-output budget",
               {"max_bytes": 20_000}, {"worker_id": worker_id, "bytes": len(payload)},
               [binding_path, result_path])
        path = directory / f"worker-{worker_id}.json"
        fixture.write_exclusive_json(path, entry)
        assignments.append({"worker_id": worker_id, "path": str(path.resolve()),
                            "sha256": fixture.sha256_file(path), "binding_sha256": binding["binding_sha256"]})
    index = {"schema": "ask-agent.compact-dispatch/v1", "run_id": manifest["run_id"],
             "assignments": assignments, "max_emitted_bytes": 20_000}
    fixture.write_exclusive_json(directory / "index.json", index)
    return {"status": "PREPARED", "worker_ids": [item["worker_id"] for item in assignments],
            "assignment_paths": [item["path"] for item in assignments],
            "index_path": str((directory / "index.json").resolve())}


def emit_compact_worker(run, worker_id):
    run = Path(run).expanduser().resolve()
    worker_id = str(worker_id)
    index_path = run / "operator" / "compact-dispatch" / "index.json"
    index = _read_json(index_path, "COMPACT_DISPATCH_MISSING", [index_path])
    row = next((item for item in index.get("assignments", []) if item.get("worker_id") == worker_id), None)
    _check(row is not None, "COMPACT_DISPATCH_WORKER_UNKNOWN", "Worker has one retained compact assignment",
           {"worker_ids": [item.get("worker_id") for item in index.get("assignments", [])]},
           {"worker_id": worker_id}, [index_path])
    path = Path(row["path"])
    try:
        payload = path.read_bytes()
    except OSError as exc:
        _fail("COMPACT_DISPATCH_MISSING", f"Cannot read compact assignment {path}",
              {"assignment_path": str(path)}, {"error": f"{type(exc).__name__}: {exc}"}, [index_path, path])
    _check(fixture.sha256_bytes(payload) == row.get("sha256") and not path.is_symlink(),
           "COMPACT_DISPATCH_BINDING_INVALID", "Stored assignment matches its prepared digest",
           {"sha256": row.get("sha256")}, {"sha256": fixture.sha256_bytes(payload), "symlink": path.is_symlink()},
           [index_path, path])
    entry = _read_json(path, "COMPACT_DISPATCH_INVALID", [index_path, path])
    encoded = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _check(len(encoded) <= 20_000, "COMPACT_ASSIGNMENT_TOO_LARGE",
           "One compact native assignment must fit the observed complete tool-output budget",
           {"max_bytes": 20_000}, {"worker_id": worker_id, "bytes": len(encoded)}, [index_path, path])
    return entry


def build_parent_oracle(run):
    """Write a parent-only expected pipeline result without importing child code."""
    run = Path(run).expanduser().resolve()
    manifest_path = run / "manifest.json"
    output = run / "operator" / "parent-expected.json"
    manifest = _read_json(manifest_path, "BRIEF_MANIFEST_INVALID", [manifest_path, output])
    count = manifest.get("workers")
    assignments = manifest.get("task_assignments")
    expected_ids = [str(i) for i in range(1, count + 1)] if type(count) is int and count in (3, 5) else []
    rows_valid = isinstance(assignments, list) and all(isinstance(row, dict) for row in assignments)
    ordered = sorted(assignments, key=lambda row: row.get("task_index", -1)) if rows_valid else []
    observed_ids = [row.get("worker_id") for row in ordered]
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    valid_tasks = (
        count in (3, 5) and manifest.get("schema_version") == 1 and observed_ids == expected_ids
        and [row.get("task_index") for row in ordered] == list(range(1, count + 1))
        and [row.get("path") for row in ordered] == [f"src/step_{worker_id}.py" for worker_id in expected_ids]
        and _absolute(paths.get("run")) and Path(paths["run"]).resolve() == run
    )
    _check(valid_tasks, "BRIEF_MANIFEST_INVALID", "Parent oracle requires the exact manifest task order",
           {"workers": "3 or 5", "worker_ids": expected_ids,
            "paths": [f"src/step_{worker_id}.py" for worker_id in expected_ids]},
           {"workers": count, "worker_ids": observed_ids,
            "paths": [row.get("path") for row in ordered]}, [manifest_path, output])
    inputs = [-7, -1, 0, 1, 9, 100]
    formulas = {f"step_{row['worker_id']}":
                f"{int(row['worker_id']) + 1}*x+{int(row['worker_id']) ** 2}" for row in ordered}
    traces, outputs = [], []
    for original in inputs:
        value = original
        trace = {"input": original}
        for row in ordered:
            worker_id = row["worker_id"]
            value = (int(worker_id) + 1) * value + int(worker_id) ** 2
            trace[f"after_step_{worker_id}"] = value
        traces.append(trace)
        outputs.append(value)
    multiplier, offset = 1, 0
    for row in ordered:
        worker_id = int(row["worker_id"])
        multiplier, offset = (worker_id + 1) * multiplier, (worker_id + 1) * offset + worker_id**2
    payload = {
        "inputs": inputs,
        "order": [f"step_{row['worker_id']}" for row in ordered],
        "formulas": formulas,
        "closed_form": f"{multiplier}*x+{offset}",
        "expected_outputs": outputs,
        "traces": traces,
    }
    try:
        fixture.write_exclusive_json(output, payload)
    except fixture.FixtureError as exc:
        exists = output.exists()
        _fail("PARENT_ORACLE_ALREADY_EXISTS" if exists else "PARENT_ORACLE_WRITE_FAILED",
              "Parent oracle evidence already exists and was not replaced" if exists
              else "Parent oracle could not be published",
              {"new_file_only": str(output)}, {"exists": exists, "error": str(exc)},
              [manifest_path, output], phase="parent-oracle")
    return {"path": str(output), "sha256": _digest(output), "worker_count": count,
            "inputs": inputs, "expected_outputs": outputs}


def _serialize_dispatch_packet(packets):
    return (json.dumps(packets, indent=2, sort_keys=True) + "\n").encode("utf-8")


def publish_dispatch_packet(run, packets):
    """Publish the exact packet array once so the controller can compare dispatch arguments."""
    path = Path(run).expanduser().resolve() / "operator" / "dispatch-packet.json"
    payload = _serialize_dispatch_packet(packets)
    # Grok 1.0.46 truncated the measured 23,046-byte packet at 20,000 content bytes.
    # Bound this Grok-specific experiment before dispatch; preserve setup for diagnosis.
    _check(len(payload) <= 20_000, "DISPATCH_PACKET_TOO_LARGE",
           "The generated packet exceeds this Grok adapter's measured complete-output budget",
           {"max_packet_bytes": 20_000}, {"packet_bytes": len(payload)},
           [Path(run).resolve() / "manifest.json", Path(run).resolve() / "operator" / "setup-result.json"])
    try:
        fixture.write_exclusive(path, payload)
    except fixture.FixtureError as exc:
        exists = path.exists()
        _fail("DISPATCH_PACKET_ALREADY_EXISTS" if exists else "DISPATCH_PACKET_WRITE_FAILED",
              "A dispatch packet already exists and was not replaced" if exists
              else "The dispatch packet could not be published",
              {"new_file_only": str(path)}, {"exists": exists, "error": str(exc)}, [path],
              phase="dispatch-packet")
    return {"path": str(path), "sha256": hashlib.sha256(payload).hexdigest(),
            "packet_count": len(packets)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--parent-oracle", action="store_true",
                        help="write independent expected pipeline results without executing worker code")
    parser.add_argument("--compact", action="store_true",
                        help="prepare compact worker assignments from retained production bindings")
    parser.add_argument("--emit-worker", choices=("1", "2", "3", "4", "5"),
                        help="emit one exact compact native assignment")
    args = parser.parse_args(argv)
    if sum((args.parent_oracle, args.compact, args.emit_worker is not None)) > 1:
        parser.error("--parent-oracle, --compact, and --emit-worker are mutually exclusive")
    run = Path(args.run).expanduser().resolve()
    try:
        if args.parent_oracle:
            result = build_parent_oracle(run)
        elif args.emit_worker is not None:
            result = emit_compact_worker(run, args.emit_worker)
        elif args.compact:
            result = build_compact_briefs(run)
        else:
            existing_packet = run / "operator" / "dispatch-packet.json"
            _check(not existing_packet.exists(), "DISPATCH_PACKET_ALREADY_EXISTS",
                   "This run already has a dispatch packet; retain it and do not dispatch again",
                   {"new_file_only": str(existing_packet)}, {"exists": existing_packet.exists()},
                   [run / "manifest.json", run / "operator" / "setup-result.json", existing_packet])
            result = build_briefs(run)
            publish_dispatch_packet(run, result)
    except Exception as exc:
        if isinstance(exc, BriefError):
            error = exc
        else:
            compact_mode = args.compact or args.emit_worker is not None
            code = ("PARENT_ORACLE_INVALID" if args.parent_oracle else
                    "COMPACT_DISPATCH_INVALID" if compact_mode else "BRIEF_PACKET_INVALID")
            evidence = [run / "manifest.json"]
            if not args.parent_oracle:
                evidence.append(run / "operator" / "setup-result.json")
            error = BriefError(code, "Could not build parent oracle" if args.parent_oracle else "Could not build worker arguments",
                               {"valid_manifest": True} if args.parent_oracle else
                               {"valid_compact_prepared_run": True} if compact_mode else {"valid_prepared_run": True},
                               {"error": f"{type(exc).__name__}: {exc}"}, evidence,
                               "parent-oracle" if args.parent_oracle else
                               "compact-dispatch" if compact_mode else "brief-preflight")
        parent_oracle = args.parent_oracle
        compact_mode = args.compact or args.emit_worker is not None
        packet_error = error.code.startswith("DISPATCH_PACKET_")
        diagnostic = diagnostics.make_diagnostic(
            code=error.code, severity="error", phase=error.phase,
            expected=error.expected, observed=error.observed,
            rationale=("The parent oracle must be derived from the frozen manifest and published once without executing worker code."
                       if parent_oracle else
                       "A run may publish only one immutable dispatch packet so native arguments remain attributable."
                       if packet_error else
                       "Compact assignments must remain bound to the exact prepared task and per-worker binding."
                       if compact_mode else
                       "Native worker arguments must bind every assignment to the frozen package, caller, and helper receipt."),
            rationale_ref="CONTRACT.md#phase-sequence",
            evidence=[diagnostics.evidence_reference(path) for path in error.evidence],
            recovery=("Preserve the manifest and existing oracle bytes; reconcile before using a fresh run."
                      if parent_oracle else
                      "Preserve the existing packet and run evidence; use a fresh run after reconciliation."
                      if packet_error else
                      "Preserve compact bindings and assignment evidence; use a fresh run after reconciliation."
                      if compact_mode else
                      "Preserve manifest, setup, receipts, and baselines; correct the binding before dispatch."),
            retry_safety=("Never overwrite parent-expected.json; retain existing evidence and use a fresh run after reconciliation."
                          if parent_oracle else
                          "Do not emit from an invalid or previously launched run; retain evidence and use a fresh prepared run after reconciliation."
                          if compact_mode else
                          "Do not dispatch from an invalid or previously launched run; retain evidence and use a fresh prepared run after reconciliation."),
        )
        operator = run / "operator"
        diagnostics.exit_with_diagnostic(
            diagnostic, jsonl_path=operator / "diagnostics.jsonl" if operator.is_dir() else None
        )
    if args.parent_oracle or args.compact:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    elif args.emit_worker is not None:
        sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    else:
        sys.stdout.write(_serialize_dispatch_packet(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
