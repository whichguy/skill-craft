#!/usr/bin/env python3
"""Compact coordinator adapter. Plan Dispatcher remains the execution authority.

This program never launches a model. Native lifecycle and semantic judgements
are explicit coordinator attestations; filesystem and Git checks are separate.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any
import uuid
from delivery import DeliveryError
from harness_paths import (
    ASK_AGENT_TASK_SCRIPT, ASK_AGENT_WORKSPACE_SCRIPT, DELIVERY_DIRECTORY,
    DISPATCHER_SCRIPT, OPERATION_LOCK_NAME, RESULT_RECORD_NAME, RUN_RECORD_NAME,
    SKILL_CARD_NAME, is_write_scope, scopes_overlap,
)

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = str(ROOT / "references" / "contract.md")


class HarnessError(Exception):
    """A refused operation with the same diagnostic contract in Python and CLI."""
    def __init__(self, code, expected, observed, rationale, evidence=(), next_action=None):
        self.record = dict(status="BLOCKED", code=code, expected=expected, observed=observed,
                           rationale=rationale, reference=REFERENCE,
                           evidence=[str(x) for x in evidence],
                           next_action=next_action or "Inspect the cited evidence; preserve this attempt before correcting the cause.")
        super().__init__(rationale)


def require(condition, code, expected, observed, rationale, evidence=()):
    if not condition:
        raise HarnessError(code, expected, observed, rationale, evidence)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    p = Path(path)
    require(p.is_file() and not p.is_symlink(), "INVALID_ARTIFACT", "regular JSON file", str(p),
            "A missing or redirected artifact cannot establish a binding.", [p])
    value = json.loads(p.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "INVALID_OBJECT", "JSON object", type(value).__name__,
            "Commands use named fields, not an implicit positional interpretation.", [p])
    return value


def save(path, value):
    p = Path(path)
    temporary = p.with_name("." + p.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as out:
            out.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
            out.flush()
            os.fsync(out.fileno())
        os.link(temporary, p)  # Atomic publication without replacing retained evidence.
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(p), "sha256": digest(p.read_bytes())}


def save_or_reuse(path, value):
    """Resume publication of identical immutable evidence after interruption."""
    p = Path(path)
    if p.exists():
        require(read(p) == value, "IMMUTABLE_CONFLICT", "identical retained evidence", str(p),
                "Recovery cannot replace an earlier observation or judgement.", [p])
        return {"path": str(p), "sha256": digest(p.read_bytes())}
    return save(p, value)


def evidence(item):
    require(isinstance(item, dict) and set(item) == {"path", "sha256"}, "INVALID_EVIDENCE",
            "{path, sha256}", item, "Verification must identify the exact bytes inspected.")
    p = absolute_argument(item["path"], "evidence.path")
    require(isinstance(item["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]),
            "INVALID_EVIDENCE_HASH", "lowercase SHA-256", item["sha256"],
            "Evidence must bind exact bytes rather than a filename alone.")
    require(p.is_absolute() and p.is_file() and not p.is_symlink(), "MISSING_EVIDENCE",
            "absolute regular evidence file", str(p), "Evidence must remain inspectable.", [p])
    observed = digest(p.read_bytes())
    require(observed == item["sha256"], "EVIDENCE_CHANGED", item["sha256"],
            observed, "Changed evidence cannot support the saved judgement.", [p])


def absolute_argument(value, field):
    """Validate a locator without creating or resolving any filesystem entry."""
    require(isinstance(value, (str, Path)) and bool(str(value).strip())
            and not any(ord(char) < 32 or ord(char) == 127 for char in str(value)),
            "ARGUMENT_PATH", f"absolute path for {field}", str(value),
            "Explicit locators make the same call independent of the caller's cwd.")
    path = Path(value)
    require(path.is_absolute(), "ARGUMENT_PATH", f"absolute path for {field}", str(path),
            "Relative paths can select a different run or artifact in another caller.")
    return path


def attempt_id(value):
    """Reject path-shaped identifiers before looking up an attempt artifact."""
    require(isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_-]+", value)),
            "ATTEMPT_ID", "Dispatcher attempt id", value,
            "An attempt identifier must not select paths outside its run.")
    return value


def package(card):
    p = Path(card)
    require(p.is_absolute() and p.name == SKILL_CARD_NAME and p.is_file(), "PACKAGE_MISSING",
            "selected absolute SKILL.md", str(p), "Bind the loaded package, not an ambient executable.", [p])
    root = p.resolve().parent
    files = {}
    for f in sorted(root.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts and not f.name.endswith(".pyc"):
            require(f.resolve().is_relative_to(root), "PACKAGE_ESCAPE", str(root), str(f.resolve()),
                    "A portable selected package cannot depend on escaping symlinks.", [f])
            files[f.relative_to(root).as_posix()] = digest(f.read_bytes())
    return {"card": str(p), "root": str(root), "files": files}


def normalized_request(raw: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate a batch and return detached defaults plus actionable warnings.

    This performs path resolution but creates no files. Caller-owned task and
    argv lists remain untouched, including when validation later fails.
    """
    allowed = {"objective", "source", "workspace", "mode", "tasks", "capacity", "integration",
               "checks", "writers_quiescent", "exclusive_writer", "current_learnings", "authorization"}
    require(isinstance(raw, dict) and not set(raw) - allowed, "REQUEST_FIELDS", sorted(allowed),
            sorted(raw, key=str) if isinstance(raw, dict) else type(raw).__name__, "Unknown fields must not silently change the workflow.")
    r = deepcopy(raw)
    for field in ("objective", "source", "workspace", "mode"):
        require(isinstance(r.get(field), str) and bool(r[field].strip()), "REQUEST_REQUIRED", field,
                r.get(field), "State the goal, repository, workspace choice and operation before dispatch.")
    require(Path(r["source"]).is_absolute(), "SOURCE_ABSOLUTE", "absolute source", r["source"], "Avoid cwd-dependent repository selection.")
    try:
        r["source"] = str(absolute_argument(r["source"], "source").resolve(strict=True))
    except (OSError, RuntimeError, ValueError) as exc:
        raise HarnessError("SOURCE_UNAVAILABLE", "existing source directory", r["source"],
                           f"Source resolution failed: {exc}", [r["source"]]) from exc
    require(Path(r["source"]).is_dir(), "SOURCE_DIRECTORY", "source directory", r["source"],
            "Workers need a repository directory, not an arbitrary regular file.")
    require(r["workspace"] in ("current", "worktree") and r["mode"] in ("edit", "report-only", "ephemeral"),
            "UNSUPPORTED_MODE", "current|worktree; edit|report-only|ephemeral", [r["workspace"], r["mode"]], "Workspace isolation and result delivery are separate choices.")
    require(r["mode"] != "ephemeral" or r["workspace"] == "worktree", "EPHEMERAL_REQUIRES_WORKTREE",
            "worktree", r["workspace"], "Scratch edits cannot leak into the caller checkout.")
    if r["workspace"] == "worktree":
        require(r.get("writers_quiescent") is True, "WRITERS_NOT_QUIESCENT", True, r.get("writers_quiescent"), "Freeze caller writes while taking the shared input snapshot.")
    if r["workspace"] == "current" and r["mode"] == "edit":
        require(r.get("exclusive_writer") is True, "EXCLUSIVE_WRITER_REQUIRED", True, r.get("exclusive_writer"), "Current-workspace edits require the coordinator to exclude other writers.")
    tasks = r.get("tasks")
    require(isinstance(tasks, list) and bool(tasks), "TASKS_REQUIRED", "nonempty independent task list", tasks, "The coordinator plans bounded work before scheduling it.")
    ids, scopes = set(), []
    for task in tasks:
        require(isinstance(task, dict) and set(task) <= {"id", "objective", "expected_result", "write_set"},
                "TASK_FIELDS", "id, objective, expected_result, write_set", task, "Dependencies belong to a separately planned Dispatcher graph; this adapter owns independent batches.")
        for field in ("id", "objective", "expected_result"):
            require(isinstance(task.get(field), str) and bool(task[field].strip()), "TASK_REQUIRED", field, task.get(field), "Each worker needs an identifiable task and checkable expected result.")
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", task["id"]) and task["id"] not in ids,
                "TASK_ID", "unique alphanumeric id", task["id"], "Task identity must not collide or select filesystem paths.")
        ids.add(task["id"])
        task.setdefault("write_set", [])
        require(isinstance(task["write_set"], list) and all(isinstance(x, str) and x for x in task["write_set"]), "WRITE_SET", "path list", task["write_set"], "Use exact paths or directory prefixes.")
        require(len(set(task["write_set"])) == len(task["write_set"]), "WRITE_SET_DUPLICATE",
                "unique path scopes", task["write_set"], "Repeated ownership declarations add no work.")
        require(bool(task["write_set"]) == (r["mode"] != "report-only"), "WRITE_MODE", "empty for report-only; nonempty for edit or ephemeral", task["write_set"], "Read-only declarations cannot carry write authority.")
        for scope in task["write_set"]:
            require(is_write_scope(scope), "WRITE_PATH", "canonical repository-relative POSIX path", scope,
                    "Scope paths must be portable and unambiguous; absolute paths, drive prefixes and traversal are refused.")
            for old_id, old in scopes:
                require(not scopes_overlap(scope, old) or old_id == task["id"], "TASK_SCOPE_OVERLAP", "independent write sets", [old_id, old, task["id"], scope], "A coordinator cannot safely combine separately based edits with overlapping ownership.")
            scopes.append((task["id"], scope))
    r.setdefault("capacity", min(5, len(tasks)))
    require(type(r["capacity"]) is int and r["capacity"] > 0, "CAPACITY", "positive integer", r["capacity"], "Capacity bounds active reservations, including unconfirmed launches.")
    warnings = []
    if r["workspace"] == "current" and r["mode"] == "edit" and r["capacity"] != 1:
        warnings.append({"code": "CURRENT_EDIT_SERIALIZED", "requested_capacity": r["capacity"], "effective_capacity": 1, "rationale": "Ask Agent current edits require one exclusive writer.", "reference": str(ROOT.parent / "ask-agent" / "references" / "current-workspace.md")})
        r["capacity"] = 1
    r.setdefault("integration", "apply")
    require(r["integration"] in ("apply", "return-only"), "INTEGRATION_MODE", "apply|return-only", r["integration"], "Return-only retains contributions without importing them.")
    require(not (r["workspace"] == "current" and r["mode"] == "edit" and r["integration"] == "return-only"), "CURRENT_ALREADY_IN_PLACE", "apply for current edits", r["integration"], "Current edits are already in the caller; choose worktree to return without integrating.")
    r.setdefault("checks", [])
    require(isinstance(r["checks"], list) and all(isinstance(a, list) and a and all(isinstance(x, str) and x and "\0" not in x for x in a) for a in r["checks"]), "CHECK_COMMANDS", "list of argv arrays", r["checks"], "Checks execute without shell evaluation in the designated source repository.")
    require(r["mode"] != "edit" or r["integration"] != "apply" or bool(r["checks"]), "COMBINED_CHECK_REQUIRED", "at least one combined check for editing delivery", r["checks"], "Individual worker results do not establish combined behavior.")
    for key in ("current_learnings", "authorization"):
        r.setdefault(key, "")
        require(isinstance(r[key], str), "CONTEXT_TEXT", "string", r[key], "Carry explicit context and existing authority without inheriting the whole conversation.")
    return r, warnings


class Run:
    """Selected-package bindings and recorded state; execute() owns mutation locks."""
    def __init__(self, path):
        self.path = Path(path).resolve(strict=True)
        self.meta = read(self.path / RUN_RECORD_NAME)
        require(self.meta.get("schema") == "agent-harness/v1", "RUN_SCHEMA", "agent-harness/v1", self.meta.get("schema"), "Inspect a supported harness run; do not adopt another workflow's state.")
        for role, pin in self.meta["packages"].items():
            current = package(pin["card"])
            changed = sorted(k for k in set(pin["files"]) | set(current["files"])
                             if pin["files"].get(k) != current["files"].get(k))
            require(current == pin, "PACKAGE_DRIFT", {"role": role, "root": pin["root"]},
                    {"root": current["root"], "changed_paths": changed},
                    "A prepared run must use the same selected implementation.", [pin["card"], self.path / RUN_RECORD_NAME])
        self.request = self.meta["request"]
        self.owner = self.meta["owner"]
        self.node = self.meta["node"]
        self.dispatcher = Path(self.meta["packages"]["dispatcher"]["root"]) / DISPATCHER_SCRIPT

    @contextmanager
    def lock(self):
        import fcntl
        with (self.path / OPERATION_LOCK_NAME).open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise HarnessError("OPERATION_BUSY", "one coordinator operation", "another operation holds the lock", "Serialize preparation and delivery without creating another scheduler.", [self.path / OPERATION_LOCK_NAME])
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def command(self, argv, value=None, cwd=None, record=True):
        """Invoke a pinned helper via argv and retain its response before using it."""
        require(isinstance(argv, (list, tuple)) and bool(argv)
                and all(isinstance(part, str) and part and "\0" not in part for part in argv),
                "HELPER_ARGV", "nonempty argv without NUL bytes", argv,
                "Reject malformed commands before publishing inputs or starting a process.")
        log = self.path / "calls" / uuid.uuid4().hex
        if value is not None:
            save(log.with_suffix(".input.json"), value)
            argv = [*argv, str(log.with_suffix(".input.json"))]
        start = time.time()
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_OPTIONAL_LOCKS": "0"})
        row = {"argv": argv, "cwd": str(cwd) if cwd else None, "started_epoch": start,
               "finished_epoch": time.time(), "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        if record:
            save(log.with_suffix(".json"), row)
        require(proc.returncode == 0, "HELPER_FAILED", "successful helper response",
                {"exit_code": proc.returncode, "diagnostic": (proc.stderr or proc.stdout)[-1600:]},
                "A failed mechanical check does not authorize fallback or another launch.", [log.with_suffix(".json")] if record else [])
        result = json.loads(proc.stdout)
        require(isinstance(result, dict), "HELPER_SHAPE", "JSON object", result, "A helper response must identify its action and evidence.")
        return result

    def call(self, operation, value=None, record=True):
        return self.command([self.node, str(self.dispatcher), operation, str(self.path / "dispatcher")], value, record=record)

    def view(self):
        return self.call("next", record=False)

    def preparation(self, attempt):
        attempt_id(attempt)
        return read(self.path / "prepared" / (attempt + ".json"))

    def packet(self, attempt):
        return self.call("packet", {"attempt": attempt}, record=False)["packet"]

    def status(self):
        v = self.view()
        final = self.path / RESULT_RECORD_NAME
        return {"status": "RECORDED_STATUS", "run": str(self.path), "owner": v["owner"],
                "observed_epoch": time.time(), "progress": v["progress"],
                "workers_accepted": v["complete"], "delivery": read(final) if final.exists() else "pending",
                "active": [{k: a[k] for k in ("step", "attempt", "status", "handle", "recovery") if k in a} for a in v["active"]],
                "actions": [{k: a[k] for k in ("action", "step", "attempt", "reason") if k in a} for a in v["actions"]],
                "native_freshness": "Recorded handles and reports; not a live host inventory.",
                "warnings": self.meta["warnings"]}


def initialize(run_path, *, request, ask_agent_card, dispatcher_card):
    """Create one pinned run; use execute() for validated paths and CLI parity."""
    request, warnings = normalized_request(read(request))
    run = Path(run_path)
    require(run.is_absolute() and not run.exists() and not run.is_symlink(), "RUN_DESTINATION", "new absolute external directory", str(run), "Never overwrite a previous run or use a repository as run storage.")
    run = run.resolve()
    pins = {"harness": package(ROOT / SKILL_CARD_NAME), "ask_agent": package(ask_agent_card), "dispatcher": package(dispatcher_card)}
    protected = [Path(request["source"]), *[Path(p["root"]) for p in pins.values()]]
    require(all(not run.is_relative_to(p) and not p.is_relative_to(run) for p in protected), "RUN_OVERLAP", "run disjoint from repositories and packages", str(run), "Workers must not edit coordinator state or evidence.", protected)
    node = shutil.which("node")
    require(bool(node), "NODE_MISSING", "Node.js for selected Plan Dispatcher", None, "Use the existing dispatcher runtime; do not install or substitute silently.")
    for role, script in (("ask_agent", ASK_AGENT_TASK_SCRIPT), ("dispatcher", DISPATCHER_SCRIPT)):
        require((Path(pins[role]["root"]) / script).is_file(), "INTERFACE_MISSING", str(script), pins[role]["root"], "The selected package must expose the required interface.")
    import delivery
    baseline = delivery.capture(request["source"])
    run.mkdir(parents=True)
    for name in ("calls", "prepared", "packets", "collected", "verified"):
        (run / name).mkdir()
    meta = {"schema": "agent-harness/v1", "owner": "coordinator-" + uuid.uuid4().hex,
            "created_epoch": time.time(), "request": request, "warnings": warnings,
            "packages": pins, "node": str(Path(node).resolve()), "baseline": baseline}
    save(run / RUN_RECORD_NAME, meta)
    runner = Run(run)
    graph = {"version": 1, "source": {"goal": request["objective"], "agent_harness": {"schema": "agent-harness/v1", "ask_agent_interface": "compact"}},
             "steps": [{"id": t["id"], "deps": [], "contract": {"task": t["objective"], "ready": ["Selected Ask Agent task preparation and scope checks pass"], "done": [t["expected_result"]]}} for t in request["tasks"]]}
    runner.call("init", {"owner": meta["owner"], "capacity": request["capacity"], "graph": graph})
    return {"status": "READY", "run": str(run), "warnings": warnings,
            "next": [sys.executable, str(Path(__file__).resolve()), "dispatch", "--run", str(run)],
            "instruction": "This coordinator owns the run. Dispatch eligible tasks through native agents, collect their terminal results, independently verify, accept, then finish delivery. The initiator receives compact status and the final evidence."}


def dispatch(run):
    launches = []
    while True:
        v = run.view()
        action = next((a for a in v["actions"] if a["action"] in ("claim", "start")), None)
        if action is None:
            break
        if action["action"] == "claim":
            run.call("claim", action["call"]["input"])
            continue
        attempt, step = action["attempt"], action["step"]
        target = run.path / "prepared" / (attempt + ".json")
        task = next(t for t in run.request["tasks"] if t["id"] == step)
        r = {k: run.request[k] for k in ("source", "workspace", "mode", "current_learnings", "authorization")}
        r.update({k: task[k] for k in ("objective", "expected_result", "write_set")})
        if r["workspace"] == "worktree":
            r["writers_quiescent"] = True
            r["store"] = str(run.path / "workspaces")
            # Every member of the batch must inherit the same original source.
            import delivery
            current = delivery.capture(r["source"])
            require(current == run.meta["baseline"], "SOURCE_DRIFT", "original caller snapshot",
                    "caller Git or file state changed", "Do not prepare workers from different caller snapshots.", [run.path / RUN_RECORD_NAME])
        elif r["mode"] == "edit":
            r["exclusive_writer"] = True
        request_path = run.path / "packets" / (attempt + "-request.json")
        save_or_reuse(request_path, r)
        pin = run.meta["packages"]["ask_agent"]
        prepare_argv = [sys.executable, "-B", str(Path(pin["root"]) / ASK_AGENT_TASK_SCRIPT), "prepare", "--skill-card", pin["card"], "--request", str(request_path), "--packet", str(run.path / "packets" / (attempt + ".json"))]
        prepared = read(target) if target.exists() else run.command(prepare_argv)
        require(prepared.get("status") == "READY_TO_LAUNCH", "NOT_PREPARED", "READY_TO_LAUNCH", prepared.get("status"), "Only validated preparation permits a native assignment.")
        ready = save_or_reuse(target, prepared)
        context = {"workspace": prepared["launch"]["cwd"], "read_only": r["mode"] == "report-only",
                   "write_scope": r["write_set"], "resources": [], "ready_evidence": ready}
        started = run.call("start", {"owner": run.owner, "attempt": attempt, "context": context})
        require(started["action"] == "launch", "LAUNCH_NOT_GRANTED", "first launch action", started["action"], "Replay and recovery cannot issue another worker.")
        launches.append({"task": step, "attempt": attempt, **prepared["launch"],
                         "result_contract": {"native_handle": "actual handle", "native_terminal": True,
                                             "status": "SUCCEEDED|FAILED|BLOCKED", "summary": "findings and limitations",
                                             "criteria": [{"criterion": task["expected_result"], "check": "actual check", "observed": "actual result", "level": "confirmed|inspected|failed|not_run"}],
                                             "evidence": []}})
    return {"status": "LAUNCH_REQUIRED" if launches else "NO_NEW_LAUNCH", "launches": launches,
            "progress": run.view()["progress"],
            "instruction": "Launch each returned assignment once with native background agents; record each returned handle using launched. Do not wait before issuing the other ready launches. Existing uncertain launches require host reconciliation, not another dispatch."}


def launched(run, *, attempt, handle):
    """Bind an actual host handle to its single prepared reservation."""
    require(isinstance(handle, str) and bool(handle.strip()) and "\0" not in handle,
            "NATIVE_HANDLE", "actual native handle", handle, "Retain the host's identity, not a task label.")
    run.preparation(attempt)
    run.call("launched", {"owner": run.owner, "attempt": attempt, "handle": handle})
    return run.status()


def collect(run, *, attempt, result):
    """Validate a terminal report before publishing immutable collection evidence."""
    result_path = result
    prepared, result = run.preparation(attempt), read(result_path)
    # Reject malformed report data before even issuing a recorded packet query.
    require(result.get("status") in ("SUCCEEDED", "FAILED", "BLOCKED") and isinstance(result.get("summary"), str) and result["summary"].strip(),
            "RESULT_REQUIRED", "terminal status and meaningful summary", result, "Failures and findings remain visible in the aggregate.")
    criteria = result.get("criteria")
    require(isinstance(criteria, list) and all(isinstance(x, dict) for x in criteria),
            "CRITERIA_MISMATCH", "array of criterion objects", criteria,
            "Each expected result needs a structured check and observation.")
    for item in criteria:
        require(item.get("level") in ("confirmed", "inspected", "failed", "not_run", "unconfirmable") and all(isinstance(item.get(k), str) and item[k].strip() for k in ("criterion", "check", "observed")),
                "CRITERIA_EVIDENCE", "actual check, observation and level", item, "A completion label cannot replace observed evidence.")
    require(isinstance(result.get("evidence", []), list), "RESULT_EVIDENCE", "array of pinned artifacts",
            type(result.get("evidence")).__name__, "Evidence references use one consistent inspectable format.")
    for item in result.get("evidence", []):
        evidence(item)
    for field in ("discrepancies", "recommendations"):
        require(isinstance(result.get(field, []), list), "RESULT_NOTES", f"array for {field}",
                result.get(field), "Result notes must keep their structured shape through publication.")
    packet = run.packet(attempt)
    require(result.get("native_terminal") is True and result.get("native_handle") == packet["native_handle"] and packet["native_handle"] is not None,
            "NATIVE_COLLECTION_REQUIRED", {"native_terminal": True, "native_handle": packet["native_handle"]},
            {k: result.get(k) for k in ("native_terminal", "native_handle")}, "A saved file or elapsed time does not prove native completion; collect the actual host result first.", [result_path])
    require([item["criterion"] for item in criteria] == packet["definition_of_done"],
            "CRITERIA_MISMATCH", packet["definition_of_done"], criteria,
            "Every frozen expected result must be addressed.")
    output = run.path / "collected" / (attempt + ".json")
    supplied_hash = digest(Path(result_path).read_bytes())
    if output.exists():
        # A crash can leave collection saved but not reported to Dispatcher.
        # Resume only those identical bytes; a duplicate terminal report is refused.
        active = next((a for a in run.view()["active"] if a["attempt"] == attempt), None)
        require(active is not None and active["status"] == "running", "RESULT_ALREADY_COLLECTED", "an unpublished retained collection", str(output), "Duplicate notifications must not rewrite evidence or deliver twice.", [output])
        record = read(output)
        require(record.get("input_sha256") == supplied_hash, "COLLECTION_CONFLICT", record.get("input_sha256"), supplied_hash, "Resume publication with the original result bytes.", [output, result_path])
        result, verification = record["result"], record["verified"]
    else:
        verification = None
        try:
            command = prepared["commands"]["verify-return"]
            verification = run.command(command["argv"], cwd=command["cwd"])
            require(verification.get("status") == "READY_FOR_PARENT_ACCEPTANCE", "RETURN_NOT_READY", "READY_FOR_PARENT_ACCEPTANCE", verification.get("status"), "Returned files must satisfy the prepared contract.")
        except HarnessError as exc:
            verification = None
            result = {**result, "status": "FAILED", "filesystem_failure": exc.record}
        record = {"result": result, "verified": verification, "input_sha256": supplied_hash, "native_evidence_kind": "coordinator_attestation", "collected_epoch": time.time()}
        save(output, record)
    artifact = {**result, "discrepancies": result.get("discrepancies", []), "recommendations": result.get("recommendations", [])}
    proof = save_or_reuse(packet["outputs"]["artifact"], artifact)
    envelope = {**packet["report_envelope"], "status": result["status"], "evidence": proof}
    save_or_reuse(packet["outputs"]["envelope"], envelope)
    run.command([run.node, str(run.dispatcher), "report", str(run.path / "dispatcher"), packet["outputs"]["envelope"]])
    return {"status": "AWAITING_VERIFICATION", "attempt": attempt, "worker_status": result["status"],
            "summary": result["summary"], "filesystem_verified": verification is not None, "evidence": str(output),
            "instruction": "Independently inspect or rerun each expected-result check, then accept with a pinned verification artifact. Native collection is an attestation, not script-authenticated host evidence."}


def accept(run, *, attempt, verification):
    """Publish an independent verdict and settle its Dispatcher reservation."""
    attempt_id(attempt)
    record = read(run.path / "collected" / (attempt + ".json"))
    verdict = read(verification)
    require(type(verdict.get("passed")) is bool and isinstance(verdict.get("reason"), str) and bool(verdict["reason"].strip()),
            "VERIFICATION_REQUIRED", "passed boolean and substantive reason", verdict, "Acceptance is a separate coordinator judgement.")
    items = verdict.get("evidence")
    require(isinstance(items, list) and bool(items), "VERIFICATION_EVIDENCE", "nonempty pinned evidence list", items, "An unexplained pass cannot release a worker reservation.")
    for item in items:
        evidence(item)
    if verdict["passed"]:
        require(record["result"]["status"] == "SUCCEEDED" and record["verified"] is not None and all(x["level"] in ("confirmed", "inspected") for x in record["result"]["criteria"]),
                "RESULT_NOT_ACCEPTABLE", "successful verified return and all criteria checked", record["result"], "Failed, unrun or unconfirmed work cannot become an accepted result.")
        command = run.preparation(attempt)["commands"]["verify-return"]
        run.command(command["argv"], cwd=command["cwd"])
    receipt = run.call("receipt", {"attempt": attempt})
    proof = save_or_reuse(run.path / "verified" / (attempt + ".json"), verdict)
    run.call("settle", {"owner": run.owner, "attempt": attempt,
                        "verification": {"receipt_sha256": receipt["sha256"], "passed": verdict["passed"], "reason": verdict["reason"], "evidence": proof}})
    return run.status()


def retry(run, *, attempt, reason, confirmed_stopped):
    """Retire only a rejected attempt whose native execution is known to have stopped."""
    attempt_id(attempt)
    require(confirmed_stopped is True and isinstance(reason, str) and bool(reason.strip()), "RETRY_CONFIRMATION",
            "confirmed native stop and explanation of what changes", reason,
            "Retire a known terminal attempt only after inspecting its effects.")
    action = next((a for a in run.view()["actions"] if a.get("attempt") == attempt and a["action"] == "retry"), None)
    require(action is not None, "RETRY_NOT_READY", "a rejected attempt with Dispatcher retry action", attempt,
            "Unknown launches stay reserved; retries cannot duplicate live or accepted work.")
    record = read(run.path / "collected" / (attempt + ".json"))
    require(record["result"]["native_terminal"] is True, "NATIVE_STOP_UNKNOWN", True, False,
            "The coordinator must have collected terminal native evidence before retiring an attempt.")
    require(not (run.request["workspace"] == "current" and run.request["mode"] == "edit"),
            "CURRENT_RETRY_REQUIRES_REPLAN", "review in-place edits and initialize a fresh run", "current edit retry",
            "A failed current writer may have changed the baseline; do not silently reuse that state.")
    run.call("retry", {"owner": run.owner, "attempt": attempt, "confirmed_stopped": True, "reason": reason})
    return run.status()


def _write_bytes_once(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.is_file() and not path.is_symlink() and path.read_bytes() == data,
                "CLEANUP_EVIDENCE_CONFLICT", digest(data), str(path),
                "A prior evidence copy must have the same bytes before it can be reused.", [path])
        return
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            require(path.is_file() and not path.is_symlink() and path.read_bytes() == data,
                    "CLEANUP_EVIDENCE_CONFLICT", digest(data), str(path),
                    "A concurrent evidence copy has different bytes.", [path])
    finally:
        temporary.unlink(missing_ok=True)


def _worker_evidence_references(record, verdict, delivery_worker):
    references = []
    native_result = record.get("result", {})
    for index, item in enumerate(native_result.get("evidence", []), start=1):
        require(isinstance(item, dict) and set(item) == {"path", "sha256"},
                "CLEANUP_EVIDENCE_REFERENCE", "{path, sha256}", item,
                "Native evidence must retain the exact file that was collected.")
        references.append({"purpose": f"native-result-{index}", "path": item["path"],
                           "sha256": item["sha256"]})

    for index, item in enumerate(verdict.get("evidence", []), start=1):
        require(isinstance(item, dict) and set(item) == {"path", "sha256"},
                "CLEANUP_EVIDENCE_REFERENCE", "{path, sha256}", item,
                "Accepted verification evidence must remain inspectable after close.")
        references.append({"purpose": f"verification-{index}", "path": item["path"],
                           "sha256": item["sha256"]})

    verified = record.get("verified")
    workspace_evidence = verified.get("workspace_evidence") if isinstance(verified, dict) else None
    inspection = workspace_evidence.get("inspection") if isinstance(workspace_evidence, dict) else None
    helper_evidence = inspection.get("evidence") if isinstance(inspection, dict) else None
    require(isinstance(helper_evidence, dict) and bool(helper_evidence),
            "CLEANUP_EVIDENCE_REFERENCE", "returned inspection evidence paths", helper_evidence,
            "The helper's inspection and contribution evidence must remain inspectable after close.")
    for name, path in sorted(helper_evidence.items()):
        references.append({"purpose": f"verify-return-{name}", "path": path, "sha256": None})

    delivery_evidence = delivery_worker.get("delivery") if isinstance(delivery_worker, dict) else None
    if isinstance(delivery_evidence, dict):
        for name in ("source_patch_path", "patch_path"):
            path = delivery_evidence.get(name)
            if path:
                references.append({"purpose": f"delivery-{name}", "path": path,
                                   "sha256": delivery_evidence.get("patch_sha256")})
    return references


def _preserve_worker_evidence(run, attempt, record, verdict, delivery_worker, worktree):
    """Retain bytes threatened by removal; keep external files as references.

    The manifest records both original and surviving paths, so a resumed close
    never needs to read a worktree that the first close already removed.
    """
    cleanup_root = run.path / DELIVERY_DIRECTORY / "cleanup"
    cleanup_root.mkdir(parents=True, exist_ok=True)
    manifest_path = cleanup_root / f"{attempt}-evidence.json"
    references = _worker_evidence_references(record, verdict, delivery_worker)
    worktree = Path(worktree)
    if manifest_path.exists():
        manifest = read(manifest_path)
        require(manifest.get("schema") == "agent-harness.cleanup-evidence/v1"
                and manifest.get("attempt") == attempt and manifest.get("worktree") == str(worktree)
                and isinstance(manifest.get("worktree_resolved"), str)
                and isinstance(manifest.get("files"), list),
                "CLEANUP_EVIDENCE_MANIFEST", "matching cleanup evidence manifest", manifest,
                "Resume must use the evidence retained before the first close attempt.", [manifest_path])
        rows = manifest["files"]
        for reference in references:
            matches = [row for row in rows if row.get("purpose") == reference["purpose"]
                       and row.get("original_path") == reference["path"]]
            require(len(matches) == 1, "CLEANUP_EVIDENCE_MANIFEST", "one retained mapping", reference,
                    "Every worker evidence reference must have a durable copy before removal.", [manifest_path])
            row = matches[0]
            if reference["sha256"] is not None:
                require(row.get("sha256") == reference["sha256"], "CLEANUP_EVIDENCE_MANIFEST",
                        reference["sha256"], row.get("sha256"),
                        "The preserved bytes must match the collected native evidence.", [manifest_path])
            retained = Path(row.get("retained_path", ""))
            require(retained.is_absolute() and retained.is_file() and not retained.is_symlink(),
                    "CLEANUP_EVIDENCE_MISSING", row.get("sha256"), str(retained),
                    "A resumed close requires the referenced evidence to remain inspectable.", [manifest_path, retained])
            resolved = retained.resolve(strict=True)
            require(str(resolved) == row.get("retained_resolved_path")
                    and digest(resolved.read_bytes()) == row.get("sha256"),
                    "CLEANUP_EVIDENCE_CHANGED", row.get("sha256"), str(retained),
                    "A resumed close requires the exact evidence bytes recorded before removal.", [manifest_path, retained])
            if row.get("path_status") == "external-reference":
                require(str(resolved) == row.get("source_resolved_path"), "CLEANUP_EVIDENCE_MANIFEST",
                        row.get("source_resolved_path"), str(resolved),
                        "An external evidence reference must still resolve to its original file.", [manifest_path, retained])
            else:
                require(row.get("path_status") == "preserved", "CLEANUP_EVIDENCE_MANIFEST",
                        "preserved or external-reference", row.get("path_status"),
                        "Unknown evidence mappings cannot authorize close.", [manifest_path])
        require(len(rows) == len(references), "CLEANUP_EVIDENCE_MANIFEST", len(references), len(rows),
                "The retained evidence manifest must exactly match the saved worker references.", [manifest_path])
        return {"path": str(manifest_path), "sha256": digest(manifest_path.read_bytes()), "files": rows}

    prepared = run.preparation(attempt)
    task_packet = read(prepared["packet"]["path"])
    workspace = task_packet.get("workspace", {})
    worktree = Path(workspace.get("root", ""))
    require(workspace.get("route") == "worktree" and str(worktree) == workspace.get("root")
            and worktree.is_absolute() and worktree.is_dir() and not worktree.is_symlink(),
            "CLEANUP_WORKSPACE", "an absolute helper-managed worktree", workspace,
            "Only the receipt-bound worker tree may be closed.")
    worktree_resolved = worktree.resolve(strict=True)
    archive = cleanup_root / "evidence" / attempt
    rows, by_hash = [], {}
    for reference in references:
        source = Path(reference["path"])
        require(source.is_absolute() and source.is_file() and not source.is_symlink(),
                "CLEANUP_EVIDENCE_MISSING", "absolute regular referenced evidence", str(source),
                "Referenced evidence must be readable before the worker tree is removed.", [source])
        actual = source.resolve(strict=True)
        lexical = Path(os.path.abspath(source))
        lexical_in_worktree = lexical == worktree or worktree in lexical.parents
        if lexical_in_worktree and not actual.is_relative_to(worktree_resolved):
            raise HarnessError("CLEANUP_EVIDENCE_ESCAPE", str(worktree_resolved), str(actual),
                               "A worker-tree evidence path resolves outside its assigned worktree.", [source])
        data = actual.read_bytes()
        sha = digest(data)
        require(reference["sha256"] is None or reference["sha256"] == sha,
                "CLEANUP_EVIDENCE_CHANGED", reference["sha256"], sha,
                "A changed evidence reference cannot authorize worktree removal.", [source])
        threatened = actual.is_relative_to(worktree_resolved)
        if threatened:
            target = by_hash.get(sha)
            if target is None:
                target = archive / sha
                _write_bytes_once(target, data)
                by_hash[sha] = target
            path_status = "preserved"
        else:
            target = actual
            path_status = "external-reference"
        rows.append({"purpose": reference["purpose"], "original_path": reference["path"],
                     "source_resolved_path": str(actual), "retained_path": str(target),
                     "retained_resolved_path": str(target.resolve(strict=True)),
                     "path_status": path_status, "sha256": sha})
    manifest = {"schema": "agent-harness.cleanup-evidence/v1", "attempt": attempt,
                "worktree": str(worktree), "worktree_resolved": str(worktree_resolved), "files": rows}
    proof = save_or_reuse(manifest_path, manifest)
    return {"path": proof["path"], "sha256": proof["sha256"], "files": rows}


def _git_reference_present(source, kind, value):
    if kind == "branch":
        if not isinstance(value, str) or not value or value.startswith("-"):
            return False
        reference = "refs/heads/" + value
        argv = ["git", "-C", str(source), "show-ref", "--verify", "--quiet", reference]
    else:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40,64}", value):
            return False
        argv = ["git", "-C", str(source), "cat-file", "-e", value + "^{commit}"]
    result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", check=False)
    return result.returncode == 0


def _close_worker(run, worker, delivery_worker, delivery_path, delivery_sha):
    """Bind terminal acceptance to the delivered worker before invoking close."""
    attempt = worker["attempt"]
    collected_path = run.path / "collected" / f"{attempt}.json"
    verified_path = run.path / "verified" / f"{attempt}.json"
    record = read(collected_path)
    verdict = read(verified_path)
    packet = run.packet(attempt)
    require(record.get("native_evidence_kind") == "coordinator_attestation"
            and record.get("result", {}).get("native_terminal") is True
            and record.get("result", {}).get("status") == "SUCCEEDED"
            and record.get("result", {}).get("native_handle") == packet.get("native_handle"),
            "CLEANUP_NATIVE_STOP", "accepted current attempt with matching native terminal attestation",
            {"native_evidence_kind": record.get("native_evidence_kind"),
             "native_terminal": record.get("result", {}).get("native_terminal"),
             "native_handle": record.get("result", {}).get("native_handle")},
            "The selected native worker must have returned terminal success before close.",
            [collected_path])
    require(verdict.get("passed") is True, "CLEANUP_ACCEPTANCE", True, verdict.get("passed"),
            "Only the accepted current attempt may be closed.", [verified_path])

    prepared = run.preparation(attempt)
    task_packet = read(prepared["packet"]["path"])
    workspace = task_packet.get("workspace", {})
    inspection = record.get("verified", {}).get("workspace_evidence", {}).get("inspection", {})
    receipt = workspace.get("receipt")
    worktree = workspace.get("root")
    branch = workspace.get("branch")
    require(workspace.get("route") == "worktree" and workspace.get("source") == run.request["source"]
            and isinstance(receipt, str) and Path(receipt).is_absolute()
            and isinstance(worktree, str) and Path(worktree).is_absolute()
            and inspection.get("status") == "returned" and inspection.get("phase") == "returned"
            and inspection.get("receipt") == receipt and inspection.get("worktree") == worktree
            and isinstance(inspection.get("fingerprint"), str)
            and re.fullmatch(r"[0-9a-f]{64}", inspection["fingerprint"]),
            "CLEANUP_INSPECTION", "accepted returned inspection bound to the prepared receipt",
            {"workspace": workspace, "inspection": inspection},
            "Close must use the exact saved returned inspection fingerprint.",
            [collected_path, verified_path, prepared["packet"]["path"]])
    require(delivery_worker.get("receipt") == receipt and delivery_worker.get("worktree") == worktree
            and delivery_worker.get("branch") == branch,
            "CLEANUP_DELIVERY_BINDING", {"receipt": receipt, "worktree": worktree, "branch": branch},
            {key: delivery_worker.get(key) for key in ("receipt", "worktree", "branch")},
            "The successful delivery row must name this accepted attempt's workspace.", [delivery_path])

    delivery_detail = delivery_worker.get("delivery", {})
    commits = delivery_detail.get("commits", []) if isinstance(delivery_detail, dict) else []
    require(_git_reference_present(run.request["source"], "branch", branch)
            and all(_git_reference_present(run.request["source"], "commit", commit) for commit in commits),
            "CLEANUP_GIT_REFS", "worker branch and delivered commits retained in source Git",
            {"branch": branch, "commits": commits},
            "Close must not discard a worker branch or any delivered commit.", [delivery_path])

    try:
        preserved = _preserve_worker_evidence(run, attempt, record, verdict, delivery_worker, worktree)
    except HarnessError as exc:
        return {"id": worker["id"], "attempt": attempt, "status": "cleanup-pending",
                "reason": exc.record["rationale"], "failure": exc.record,
                "receipt": receipt, "worktree": worktree, "branch": branch,
                "inspection_fingerprint": inspection["fingerprint"],
                "worktree_path_status": "retained" if Path(worktree).exists() else "unknown"}

    acceptance_path = run.path / DELIVERY_DIRECTORY / "cleanup" / f"{attempt}-acceptance.json"
    collected_hash = digest(collected_path.read_bytes())
    verified_hash = digest(verified_path.read_bytes())
    acceptance = {
        "schema": "ask-agent.acceptance.v1",
        "inspection_fingerprint": inspection["fingerprint"],
        "decision": "integrated",
        "workers_stopped": True,
        "completion_reference": f"native terminal handle {packet['native_handle']} in {collected_path} sha256={collected_hash}",
        "acceptance_reference": f"accepted verification {verified_path} sha256={verified_hash}; delivery {delivery_path} sha256={delivery_sha}; evidence {preserved['path']} sha256={preserved['sha256']}",
        "artifacts": [],
        "discard": [],
    }
    try:
        acceptance_record = save_or_reuse(acceptance_path, acceptance)
        helper = Path(run.meta["packages"]["ask_agent"]["root"]) / ASK_AGENT_WORKSPACE_SCRIPT
        outcome = run.command([sys.executable, "-B", str(helper), "close", "--receipt", receipt,
                               "--acceptance", acceptance_record["path"]])
    except HarnessError as exc:
        return {"id": worker["id"], "attempt": attempt, "status": "cleanup-pending",
                "reason": exc.record["rationale"], "failure": exc.record,
                "receipt": receipt, "worktree": worktree, "branch": branch,
                "inspection_fingerprint": inspection["fingerprint"],
                "acceptance": acceptance_record if "acceptance_record" in locals() else None,
                "evidence_manifest": preserved["path"], "preserved_evidence": preserved["files"],
                "worktree_path_status": "retained" if Path(worktree).exists() else "unknown"}

    status = "closed" if outcome.get("status") == "closed" and outcome.get("removed") is True else "cleanup-pending"
    reason = None if status == "closed" else outcome.get("reason", "the selected close helper did not confirm removal")
    if status == "closed" and (Path(worktree).exists()
                                or _git_worktree_registered(run.request["source"], worktree) is not False
                                or not _git_reference_present(run.request["source"], "branch", branch)
                                or not all(_git_reference_present(run.request["source"], "commit", commit) for commit in commits)):
        status = "cleanup-pending"
        reason = "the close helper reported removal but worktree registration or Git reference postconditions did not hold"
    close_record = Path(receipt).parent / "close.json"
    return {"id": worker["id"], "attempt": attempt, "status": status, "reason": reason,
            "receipt": receipt, "worktree": worktree, "branch": branch, "commits": commits,
            "inspection_fingerprint": inspection["fingerprint"], "acceptance": acceptance_record,
            "helper_outcome": outcome, "close_evidence": str(close_record) if close_record.is_file() else None,
            "evidence_manifest": preserved["path"], "preserved_evidence": preserved["files"],
            "worktree_path_status": "removed" if status == "closed" else
            ("retained" if Path(worktree).exists() else "unknown"),
            "historical_worktree_path": worktree if status == "closed" else None,
            "surviving_evidence_manifest": preserved["path"]}


def _cross_worker_evidence_issue(run, workers, delivery_workers):
    """Preflight the whole batch so closing one tree cannot break a later proof."""
    roots = {}
    references_by_worker = {}
    for worker in workers:
        attempt = worker["attempt"]
        prepared = run.preparation(attempt)
        task_packet = read(prepared["packet"]["path"])
        workspace = task_packet.get("workspace", {})
        root = workspace.get("root")
        if workspace.get("route") == "worktree" and isinstance(root, str) and Path(root).is_absolute():
            lexical_root = Path(os.path.abspath(root))
            roots[worker["id"]] = {"lexical": lexical_root,
                                    "resolved": Path(root).resolve(strict=False)}
            record = read(run.path / "collected" / f"{attempt}.json")
            verdict = read(run.path / "verified" / f"{attempt}.json")
            references_by_worker[worker["id"]] = _worker_evidence_references(
                record, verdict, delivery_workers.get(worker["id"], {}))
    for worker_id, references in references_by_worker.items():
        for reference in references:
            path = Path(reference["path"])
            if not path.is_absolute():
                continue
            lexical = Path(os.path.abspath(path))
            resolved = path.resolve(strict=False)
            for other_id, root in roots.items():
                lexical_root, resolved_root = root["lexical"], root["resolved"]
                points_into_other = (lexical == lexical_root or lexical_root in lexical.parents
                                     or resolved == resolved_root or resolved_root in resolved.parents)
                if other_id != worker_id and points_into_other:
                    return {"worker_id": worker_id, "other_worker_id": other_id,
                            "path": str(path), "resolved_path": str(resolved),
                            "other_worktree": str(lexical_root)}
    return None


def _git_worktree_registered(source, worktree):
    result = subprocess.run(["git", "-C", str(source), "worktree", "list", "--porcelain"],
                            capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode != 0:
        return None
    path = str(Path(os.path.abspath(worktree)))
    return any(line == "worktree " + path for line in result.stdout.splitlines())


def _cleanup(run, delivery_result, workers, delivery_path):
    """Return cleanup outcomes without rewriting the successful delivery record."""
    request = run.request
    eligible_request = (request["workspace"] == "worktree" and request["mode"] == "edit"
                        and request["integration"] == "apply")
    if not eligible_request:
        reason = "this workspace and delivery mode are retained by policy"
        return "not-applicable", reason, [{"id": worker["id"], "attempt": worker["attempt"],
                                           "status": "not-applicable", "reason": reason} for worker in workers]
    check_rows = delivery_result.get("checks", [])
    checks_passed = (len(check_rows) == len(request["checks"])
                     and all(item.get("exit_code") == 0 and item.get("status") == "PASSED"
                             for item in check_rows)
                     and delivery_result.get("check_postcondition", {}).get("exact_snapshot_unchanged") is True)
    delivery_workers = {row["id"]: row for row in delivery_result.get("workers", [])}
    applied = delivery_result.get("status") == "SUCCEEDED" and delivery_result.get("integration", {}).get("outcome") == "applied" and checks_passed
    if not applied:
        reason = "successful applied delivery and passing combined checks are required; worker worktrees were retained"
        return "retained", reason, [{"id": worker["id"], "attempt": worker["attempt"],
                                     "status": "retained", "reason": reason,
                                     "worktree": delivery_workers.get(worker["id"], {}).get("worktree"),
                                     "worktree_path_status": ("retained" if isinstance(delivery_workers.get(worker["id"], {}).get("worktree"), str)
                                                               and Path(delivery_workers[worker["id"]]["worktree"]).is_dir()
                                                               else "unknown")}
                                    for worker in workers]

    current = {row["step"]: row["attempt"] for row in run.view()["progress"]["completed"]}
    require({worker["id"]: worker["attempt"] for worker in workers} == current,
            "CLEANUP_CURRENT_ATTEMPT", current,
            {worker["id"]: worker["attempt"] for worker in workers},
            "Cleanup applies only to each step's accepted current attempt.")
    delivery_sha = digest(Path(delivery_path).read_bytes())
    cross_worker_issue = _cross_worker_evidence_issue(run, workers, delivery_workers)
    if cross_worker_issue:
        reason = "worker evidence points into another worker tree; all trees were retained to preserve the reference"
        return "cleanup-pending", reason, [{"id": worker["id"], "attempt": worker["attempt"],
                                            "status": "cleanup-pending", "reason": reason,
                                            "failure": {"code": "CLEANUP_CROSS_WORKTREE_EVIDENCE",
                                                        "observed": cross_worker_issue},
                                            "worktree": delivery_workers.get(worker["id"], {}).get("worktree"),
                                            "worktree_path_status": "retained"} for worker in workers]
    outcomes = []
    for worker in workers:
        try:
            delivered = delivery_workers.get(worker["id"])
            require(isinstance(delivered, dict), "CLEANUP_DELIVERY_WORKER", "one saved delivery row", worker["id"],
                    "Every accepted current worker must be represented in the immutable delivery.", [delivery_path])
            outcome = _close_worker(run, worker, delivered, delivery_path, delivery_sha)
        except HarnessError as exc:
            outcome = {"id": worker["id"], "attempt": worker["attempt"], "status": "cleanup-pending",
                       "reason": exc.record["rationale"], "failure": exc.record}
        except Exception as exc:
            outcome = {"id": worker["id"], "attempt": worker["attempt"], "status": "cleanup-pending",
                       "reason": f"cleanup could not complete safely: {type(exc).__name__}: {exc}",
                       "worktree_path_status": "unknown"}
        outcomes.append(outcome)
    status = "complete" if all(item["status"] == "closed" for item in outcomes) else "cleanup-pending"
    reason = None if status == "complete" else "one or more helper-bound worktrees were retained; inspect per-worker cleanup evidence"
    return status, reason, outcomes


def finish(run):
    """Deliver once, then close eligible worktrees and publish the aggregate."""
    view = run.view()
    require(view["complete"], "WORKERS_NOT_ACCEPTED", "every worker accepted with no active reservation", view["progress"], "A run cannot deliver while workers are active, unknown, failed or awaiting verification.")
    require(not (run.path / RESULT_RECORD_NAME).exists(), "DELIVERY_ALREADY_FINAL", "one delivery outcome", str(run.path / RESULT_RECORD_NAME), "Inspect the retained outcome instead of applying contributions twice.")
    workers = []
    for p in sorted((run.path / "collected").glob("*.json")):
        verdict = run.path / "verified" / p.name
        if verdict.exists() and read(verdict).get("passed") is False:
            continue  # Retried rejected attempts retain their evidence but never contribute.
        record = read(p)
        packet = run.packet(p.stem)
        prepared = run.preparation(p.stem)
        workers.append({"id": packet["step"], "attempt": p.stem, "prepared": prepared,
                        "verified": record["verified"], "summary": record["result"]["summary"]})
    require({w["id"] for w in workers} == {t["id"] for t in run.request["tasks"]} and len(workers) == len(run.request["tasks"]),
            "DELIVERY_MEMBERSHIP", [t["id"] for t in run.request["tasks"]], [w["id"] for w in workers], "Only the accepted current attempt for each required task may contribute.")
    import delivery
    saved_delivery = run.path / DELIVERY_DIRECTORY / RESULT_RECORD_NAME
    delivery_request = {key: run.request[key] for key in ("source", "workspace", "mode", "integration", "checks")}
    # Delivery is immutable before cleanup starts. Interrupted finish can resume
    # removal and aggregate publication without importing contributions twice.
    result = read(saved_delivery) if saved_delivery.exists() else delivery.deliver(run.path, delivery_request, run.meta["baseline"], workers)
    summaries = {w["id"]: w["summary"] for w in workers}
    attempts = {w["id"]: w["attempt"] for w in workers}
    final_workers = []
    for row in result.get("workers", [{"id": w["id"]} for w in workers]):
        final_workers.append({**row, "attempt": attempts.get(row["id"]),
                              "summary": summaries.get(row["id"], "")})
    result["workers"] = final_workers
    delivery_status = result.get("status")
    result["delivery_status"] = delivery_status
    result["delivery_success"] = delivery_status == "SUCCEEDED"
    try:
        cleanup_status, cleanup_reason, cleanup_workers = _cleanup(run, result, workers, saved_delivery)
    except HarnessError as exc:
        cleanup_status = "cleanup-pending" if result["delivery_success"] else "retained"
        cleanup_reason = exc.record["rationale"]
        cleanup_workers = [{"id": worker["id"], "attempt": worker["attempt"],
                            "status": cleanup_status, "reason": cleanup_reason,
                            "failure": exc.record} for worker in workers]
    except Exception as exc:
        cleanup_status = "cleanup-pending" if result["delivery_success"] else "retained"
        cleanup_reason = f"cleanup could not complete safely: {type(exc).__name__}: {exc}"
        cleanup_workers = [{"id": worker["id"], "attempt": worker["attempt"],
                            "status": cleanup_status, "reason": cleanup_reason} for worker in workers]
    result["cleanup_status"] = cleanup_status
    result["cleanup"] = {"status": cleanup_status, "reason": cleanup_reason, "workers": cleanup_workers}
    cleanup_by_id = {item["id"]: item for item in cleanup_workers}
    for row in result["workers"]:
        if row.get("id") in cleanup_by_id:
            row["cleanup"] = cleanup_by_id[row["id"]]
    removed_worktrees = {os.path.normpath(item.get("worktree", "")) for item in cleanup_workers
                         if item.get("status") == "closed" and item.get("worktree")}
    if removed_worktrees:
        result["retained_locations"] = [location for location in result.get("retained_locations", [])
                                        if os.path.normpath(location) not in removed_worktrees]
    if cleanup_status == "cleanup-pending" and result["delivery_success"]:
        result["status"] = "CLEANUP_PENDING"
    result.update({"run": str(run.path), "owner": run.owner,
                   "native_lifecycle": "coordinator-attested; experiment host traces are separate evidence", "finished_epoch": time.time()})
    save(run.path / RESULT_RECORD_NAME, result)
    return result


def execute(command: str, *, run: str | Path, **arguments: Any) -> dict[str, Any]:
    """Run one coordinator operation, returning JSON-compatible data without printing.

    Use the CLI's operation names and underscore-separated option names. All
    locators must be absolute. Validation and the mutation lock are shared with
    the CLI; expected refusals raise HarnessError or DeliveryError. Returned
    FAILED/BLOCKED/CLEANUP_PENDING outcomes still require caller inspection.
    Native agents are launched by the caller, never by this API.
    """
    required = {
        "init": {"request", "ask_agent_card", "dispatcher_card"},
        "status": set(), "dispatch": set(), "finish": set(),
        "launched": {"attempt", "handle"}, "collect": {"attempt", "result"},
        "accept": {"attempt", "verification"},
        "retry": {"attempt", "reason", "confirmed_stopped"},
    }
    require(isinstance(command, str) and command in required, "COMMAND",
            sorted(required), command, "Choose one explicit coordinator operation.")
    require(set(arguments) == required[command], "COMMAND_ARGUMENTS", sorted(required[command]),
            sorted(arguments), "Missing or unknown arguments must not silently change an operation.")
    run_path = absolute_argument(run, "run")
    options = dict(arguments)
    for name in ("request", "ask_agent_card", "dispatcher_card", "result", "verification"):
        if name in options:
            options[name] = str(absolute_argument(options[name], name))
    if "attempt" in options:
        attempt_id(options["attempt"])
    if command == "launched":
        handle = options["handle"]
        require(isinstance(handle, str) and bool(handle.strip()) and "\0" not in handle,
                "NATIVE_HANDLE", "actual native handle", handle,
                "Validate host identity before opening or changing a run.")
    if command == "retry":
        require(options["confirmed_stopped"] is True and isinstance(options["reason"], str)
                and bool(options["reason"].strip()) and "\0" not in options["reason"],
                "RETRY_CONFIRMATION", "true stop attestation and nonempty reason", options,
                "Truth-like strings or numbers do not establish native stop.")
    try:
        if command == "init":
            return initialize(run_path, **options)
        selected = Run(run_path)
        if command == "status":
            return selected.status()  # Observing state must not create the mutation lock.
        operations = {"dispatch": dispatch, "finish": finish, "launched": launched,
                      "collect": collect, "accept": accept, "retry": retry}
        with selected.lock():
            return operations[command](selected, **options)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, DeliveryError):
            raise
        raise HarnessError("INVALID_OPERATION", "valid request and intact artifacts",
                           f"{type(exc).__name__}: {exc}",
                           "The operation stopped without treating incomplete evidence as success.", [run_path]) from exc


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise HarnessError("COMMAND_ARGUMENTS", "documented command and complete options", message,
                           "Argument parsing failed before accessing run state; use --help for syntax.")


def parser():
    p = _ArgumentParser(description=__doc__, allow_abbrev=False)
    subs = p.add_subparsers(dest="command", required=True)
    init = subs.add_parser("init", allow_abbrev=False)
    for name in ("run", "request", "ask-agent-card", "dispatcher-card"):
        init.add_argument("--" + name, required=True)
    for name in ("dispatch", "status", "finish", "launched", "collect", "accept", "retry"):
        s = subs.add_parser(name, allow_abbrev=False)
        s.add_argument("--run", required=True)
        if name in ("launched", "collect", "accept", "retry"):
            s.add_argument("--attempt", required=True)
        if name == "launched": s.add_argument("--handle", required=True)
        if name == "collect": s.add_argument("--result", required=True)
        if name == "accept": s.add_argument("--verification", required=True)
        if name == "retry":
            s.add_argument("--reason", required=True)
            s.add_argument("--confirmed-stopped", action="store_true", required=True)
    return p


def main(argv=None):
    """Translate argv and structured API outcomes to JSON streams and exit codes."""
    try:
        result = execute(**vars(parser().parse_args(argv)))
        failed = result.get("status") in ("FAILED", "BLOCKED", "CLEANUP_PENDING")
        print(json.dumps(result), file=sys.stderr if failed else sys.stdout)
        return 2 if failed else 0
    except HarnessError as exc:
        print(json.dumps(exc.record), file=sys.stderr)
        return 2
    except DeliveryError as exc:
        print(json.dumps({"status": "BLOCKED", **exc.payload}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
