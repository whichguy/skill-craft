#!/usr/bin/env python3
"""Capture parent Git state and deliver verified Ask Agent contributions.

This module never launches a worker. The caller supplies the native worker
records and the Ask Agent prepare/verify-return outputs that bind each return.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import time
from typing import Any, Mapping, NoReturn, Sequence


from harness_paths import (
    ATTEMPT_RECORD_NAME, DELIVERY_DIRECTORY, GIT_PATH_SEPARATOR,
    RESULT_RECORD_NAME, ROOT_CONTROL_FILES, is_git_relative_path,
    is_write_scope, scope_contains,
)


SCHEMA = "agent-harness.delivery.v1"
SNAPSHOT_SCHEMA = "agent-harness.git-snapshot.v1"
CONTRACT_PATH = Path(__file__).resolve().parents[1] / "references" / "contract.md"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")


def _contract_reference(label: str) -> str:
    """Return a selected-package reference with a stable contract heading."""
    section = "bind-the-run" if label in {"capture", "baseline"} else "follow-the-recorded-lifecycle"
    return f"{CONTRACT_PATH}#{section} [{label}]"


class DeliveryError(RuntimeError):
    """A delivery refusal with machine-readable evidence."""

    def __init__(self, code: str, expected: Any, observed: Any, rationale: str,
                 *, reference: str = "delivery", next_action: str = "Inspect the retained evidence and resolve the cause before retrying.") -> None:
        super().__init__(rationale)
        self.payload = {
            "code": code,
            "expected": expected,
            "observed": observed,
            "rationale": rationale,
            "reference": _contract_reference(reference),
            "evidence_paths": [],
            "safe_next_step": next_action,
        }


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(source: Path, *args: str, check: bool = True, attempt: _Attempt | None = None) -> bytes:
    argv = ["git", "-C", os.fspath(source), *args]
    if attempt is not None:
        record = attempt.command("git-" + (args[0] if args else "command"), argv, source)
        try:
            stdout = base64.b64decode(record.get("stdout_b64", ""), validate=True)
        except (ValueError, TypeError):
            stdout = b""
        if check and record.get("exit_code") != 0:
            raise DeliveryError(
                "git_snapshot_failed", 0, record.get("exit_code"),
                f"Git could not capture `{args[0] if args else 'command'}` for the selected source: {record.get('stderr', '').strip()}",
                reference="capture",
            )
        return stdout
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    proc = subprocess.run(
        argv,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode:
        raise DeliveryError(
            "git_snapshot_failed", 0, proc.returncode,
            f"Git could not capture `{args[0]}` for the selected source: {proc.stderr.decode(errors='replace').strip()}",
            reference="capture",
        )
    return proc.stdout


def _repo_root(source: Path, attempt: _Attempt | None = None) -> Path:
    raw = _git(source, "rev-parse", "--show-toplevel", attempt=attempt).rstrip(b"\n")
    return Path(os.fsdecode(raw)).resolve(strict=True)


def _branch(source: Path, attempt: _Attempt | None = None) -> str | None:
    if attempt is not None:
        record = attempt.command("git-symbolic-ref", ["git", "-C", os.fspath(source), "symbolic-ref", "--quiet", "--short", "HEAD"], source)
        if record.get("exit_code"):
            return None
        try:
            output = base64.b64decode(record.get("stdout_b64", ""), validate=True)
        except (ValueError, TypeError):
            return None
        return output.rstrip(b"\n").decode("utf-8", errors="surrogateescape")
    proc = subprocess.run(
        ["git", "-C", os.fspath(source), "symbolic-ref", "--quiet", "--short", "HEAD"],
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        return None
    return proc.stdout.rstrip(b"\n").decode("utf-8", errors="surrogateescape")


def _nul_paths(raw: bytes) -> list[str]:
    if raw and not raw.endswith(b"\0"):
        raise DeliveryError("malformed_git_paths", "NUL-terminated Git paths", raw[-32:].hex(),
                            "Git returned an incomplete path list.", reference="capture")
    return [os.fsdecode(item) for item in raw.split(b"\0") if item]


def _file_record(root: Path, relative: str) -> dict[str, Any]:
    path = root.joinpath(*PurePosixPath(relative).parts)
    record: dict[str, Any] = {"path": relative}
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {**record, "type": "missing"}
    record["mode"] = stat.S_IMODE(info.st_mode)
    if stat.S_ISREG(info.st_mode):
        content = path.read_bytes()
        record.update({"type": "file", "size": len(content), "sha256": _sha256(content)})
    elif stat.S_ISLNK(info.st_mode):
        target = os.fsencode(os.readlink(path))
        record.update({"type": "symlink", "target_b64": base64.b64encode(target).decode("ascii"),
                       "sha256": _sha256(target)})
    else:
        record["type"] = "other"
    return record


def _read_regular_nofollow(path: Path, *, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        _fail("unreadable_evidence_file", "a readable regular file", f"{path}: {exc}",
              f"The {label} could not be opened safely.", reference="worker-binding", evidence_paths=[os.fspath(path)])
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            _fail("invalid_evidence_file", "a regular file", os.fspath(path),
                  f"The {label} changed type while being opened.", reference="worker-binding",
                  evidence_paths=[os.fspath(path)])
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(fd)


def capture(source: str | Path, *, _attempt: _Attempt | None = None) -> dict[str, Any]:
    """Return a snapshot for an existing absolute Git checkout path.

    The snapshot includes HEAD and branch, index stages, the complete binary
    staged diff, and bytes/modes for tracked and non-ignored untracked paths.
    Root `.gitignore` and `.claspignore` are included even when Git ignores them.
    """
    try:
        source_value = os.fspath(source)
    except (TypeError, ValueError) as exc:
        _fail("invalid_source", "an existing absolute Git source directory",
              f"{type(exc).__name__}: {exc}", "The source path must be an explicit absolute path.",
              reference="capture")
    if (not isinstance(source_value, str) or not source_value
            or not Path(source_value).is_absolute()
            or any(ord(char) < 32 or ord(char) == 127 for char in source_value)):
        _fail("invalid_source", "an existing absolute Git source directory", source_value,
              "The source path must be an explicit absolute path.", reference="capture")
    try:
        source_path = Path(source_value).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        _fail("invalid_source", "an existing absolute Git source directory", f"{source_value}: {exc}",
              "The source path cannot be resolved.", reference="capture")
    if not source_path.is_dir():
        _fail("invalid_source", "an existing absolute Git source directory", os.fspath(source_path),
              "The source path is not a directory.", reference="capture")
    root = _repo_root(source_path, _attempt)
    head = _git(root, "rev-parse", "HEAD", attempt=_attempt).rstrip(b"\n").decode("ascii")
    index_raw = _git(root, "ls-files", "--stage", "-z", attempt=_attempt)
    entries: list[dict[str, Any]] = []
    for item in index_raw.split(b"\0"):
        if not item:
            continue
        try:
            metadata, raw_path = item.split(b"\t", 1)
            mode, object_id, stage = metadata.decode("ascii").split(" ")
        except (ValueError, UnicodeDecodeError) as exc:
            raise DeliveryError("malformed_git_index", "mode, object id, stage, and path entries", item.hex(),
                                "Git returned a malformed index entry.", reference="capture") from exc
        entries.append({"mode": mode, "oid": object_id, "stage": int(stage), "path": os.fsdecode(raw_path)})
    entries.sort(key=lambda entry: (entry["path"], entry["stage"], entry["mode"], entry["oid"]))

    head_paths = _nul_paths(_git(root, "ls-tree", "-rz", "--name-only", "HEAD", attempt=_attempt))
    index_paths = [entry["path"] for entry in entries]
    untracked_paths = _nul_paths(_git(root, "ls-files", "--others", "--exclude-standard", "-z", attempt=_attempt))
    file_paths = set(head_paths) | set(index_paths) | set(untracked_paths)
    for special in ROOT_CONTROL_FILES:
        candidate = root / special
        if candidate.exists() or candidate.is_symlink():
            file_paths.add(special)
    files = [_file_record(root, path) for path in sorted(file_paths)]
    cached_diff = _git(root, "diff", "--cached", "--binary", "--no-ext-diff", attempt=_attempt)
    status = _git(root, "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=all", attempt=_attempt)
    return {
        "schema": SNAPSHOT_SCHEMA,
        "source": os.fspath(source_path),
        "root": os.fspath(root),
        "branch": _branch(root, _attempt),
        "head": head,
        "index_entries": entries,
        "cached_diff_b64": base64.b64encode(cached_diff).decode("ascii"),
        "cached_diff_sha256": _sha256(cached_diff),
        "files": files,
        "status_b64": base64.b64encode(status).decode("ascii"),
        "status_sha256": _sha256(status),
    }


def _write_exclusive(path: Path, payload: bytes, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, mode)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_json_exclusive(path: Path, value: Any, *, mode: int = 0o600) -> None:
    _write_exclusive(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8") + b"\n", mode=mode)


class _Attempt:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.log_dir = root / "commands"
        self.sequence = 0
        self.log_dir.mkdir()

    def command(self, label: str, argv: Sequence[str], cwd: Path) -> dict[str, Any]:
        self.sequence += 1
        started = time.time()
        record: dict[str, Any] = {
            "label": label,
            "argv": list(argv),
            "cwd": os.fspath(cwd),
            "started_epoch": started,
            "exit_code": None,
            "status": "RUNNING",
        }
        path = self.log_dir / f"{self.sequence:04d}-{label}.json"
        try:
            proc = subprocess.run(
                list(argv), cwd=cwd, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            record.update({
                "exit_code": proc.returncode,
                "stdout": proc.stdout.decode("utf-8", errors="replace"),
                "stderr": proc.stderr.decode("utf-8", errors="replace"),
                "stdout_b64": base64.b64encode(proc.stdout).decode("ascii"),
                "stderr_b64": base64.b64encode(proc.stderr).decode("ascii"),
                "stdout_sha256": _sha256(proc.stdout),
                "stderr_sha256": _sha256(proc.stderr),
                "status": "COMPLETED",
            })
        except OSError as exc:
            record.update({"status": "FAILED_TO_START", "error": f"{type(exc).__name__}: {exc}"})
        record["elapsed_s"] = time.time() - started
        record["evidence_path"] = os.fspath(path.resolve())
        _write_json_exclusive(path, record)
        return record


def _fail(code: str, expected: Any, observed: Any, rationale: str,
          *, reference: str = "delivery", status: str = "BLOCKED",
          evidence_paths: Sequence[str] = (), next_action: str | None = None) -> NoReturn:
    error = DeliveryError(code, expected, observed, rationale, reference=reference,
                          next_action=next_action or "Inspect the retained evidence and resolve the cause before retrying.")
    error.payload["evidence_paths"] = list(dict.fromkeys(path for path in evidence_paths if path))
    error.payload["status"] = status
    raise error


def _absolute_path(value: Any, key: str, *, existing: bool = True) -> Path:
    if not isinstance(value, str) or not value or not Path(value).is_absolute() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        _fail("invalid_path", f"an absolute path for {key}", value, f"`{key}` must be an explicit absolute path.")
    try:
        return Path(value).resolve(strict=existing)
    except (OSError, RuntimeError, ValueError) as exc:
        _fail("invalid_path", f"a resolvable absolute path for {key}", f"{value}: {exc}",
              f"`{key}` cannot be resolved.")


def _write_set(binding: Mapping[str, Any], worker_id: str) -> list[str]:
    task = binding.get("task")
    patterns = task.get("write_set") if isinstance(task, dict) else None
    if not isinstance(patterns, list) or any(not is_write_scope(item) for item in patterns):
        _fail("invalid_worker_scope", "Ask Agent task.write_set with exact paths or slash-terminated prefixes", patterns,
              f"Worker {worker_id} has no safe, canonical write scope.", reference="worker-binding")
    if len(set(patterns)) != len(patterns):
        _fail("invalid_worker_scope", "unique write_set paths", patterns,
              f"Worker {worker_id} repeats a path in its scope.", reference="worker-binding")
    return sorted(patterns)


def _matches_scope(path: str, patterns: Sequence[str]) -> bool:
    return any(scope_contains(pattern, path) for pattern in patterns)


def _load_worker(request: Mapping[str, Any], source: Path, worker: Any) -> dict[str, Any]:
    if not isinstance(worker, dict):
        _fail("invalid_worker", "a worker object with id, prepared, and verified", type(worker).__name__,
              "The delivery input contains a malformed worker row.", reference="worker-binding")
    worker_id = worker.get("id")
    if not isinstance(worker_id, str) or not worker_id.strip() or any(ord(c) < 32 or ord(c) == 127 for c in worker_id):
        _fail("invalid_worker_id", "a non-empty printable worker id", worker_id,
              "Worker ids are coordinator-owned identifiers and must be stable text.", reference="worker-binding")
    prepared = worker.get("prepared")
    verified = worker.get("verified")
    if not isinstance(prepared, dict) or prepared.get("status") != "READY_TO_LAUNCH":
        _fail("invalid_prepared_result", "Ask Agent prepare output with status READY_TO_LAUNCH", prepared,
              f"Worker {worker_id} is not bound to a prepared Ask Agent packet.", reference="worker-binding")
    packet = prepared.get("packet")
    if not isinstance(packet, dict):
        _fail("missing_packet", "prepared.packet.path, sha256, and binding_sha256", packet,
              f"Worker {worker_id} has no pinned packet in its prepare result.", reference="worker-binding")
    packet_value = packet.get("path")
    raw_packet_path = Path(packet_value) if isinstance(packet_value, str) else None
    if raw_packet_path is None or raw_packet_path.is_symlink() or not raw_packet_path.is_file():
        _fail("invalid_packet_file", "a regular, non-symlink packet file", packet_value,
              f"Worker {worker_id}'s prepared packet is missing or is not a regular file.",
              reference="worker-binding", evidence_paths=[packet_value] if isinstance(packet_value, str) else [])
    packet_path = _absolute_path(packet_value, f"worker {worker_id} packet path")
    if not packet_path.is_file():
        _fail("invalid_packet_file", "a regular, non-symlink packet file", os.fspath(packet_path),
              f"Worker {worker_id}'s prepared packet is missing or is not a regular file.",
              reference="worker-binding", evidence_paths=[os.fspath(packet_path)])
    packet_bytes = _read_regular_nofollow(packet_path, label="pinned packet")
    packet_sha = _sha256(packet_bytes)
    if packet.get("sha256") != packet_sha:
        _fail("packet_hash_mismatch", packet.get("sha256"), packet_sha,
              f"Worker {worker_id}'s packet bytes no longer match the prepare result.",
              reference="worker-binding", evidence_paths=[os.fspath(packet_path)])
    try:
        binding = json.loads(packet_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("invalid_packet_json", "UTF-8 JSON Ask Agent binding", f"{type(exc).__name__}: {exc}",
              f"Worker {worker_id}'s pinned packet is not readable binding JSON.",
              reference="worker-binding", evidence_paths=[os.fspath(packet_path)])
    if not isinstance(binding, dict):
        _fail("invalid_packet_json", "a JSON object Ask Agent binding", type(binding).__name__,
              f"Worker {worker_id}'s pinned packet is not a JSON object.",
              reference="worker-binding", evidence_paths=[os.fspath(packet_path)])
    digest_payload = {key: value for key, value in binding.items() if key != "binding_sha256"}
    binding_sha = _sha256(_canonical_json(digest_payload))
    if (binding.get("binding_sha256") != binding_sha
            or packet.get("binding_sha256") != binding_sha):
        _fail("binding_hash_mismatch", packet.get("binding_sha256"), binding_sha,
              f"Worker {worker_id}'s binding digest does not match its pinned packet.",
              reference="worker-binding", evidence_paths=[os.fspath(packet_path)])
    if binding.get("schema") != "ask-agent.task.binding.v1" or binding.get("status") != "READY_TO_LAUNCH":
        _fail("invalid_binding", {"schema": "ask-agent.task.binding.v1", "status": "READY_TO_LAUNCH"},
              {"schema": binding.get("schema"), "status": binding.get("status")},
              f"Worker {worker_id}'s packet is not an Ask Agent task binding.", reference="worker-binding")
    task = binding.get("task")
    bound_workspace = binding.get("workspace")
    if not isinstance(task, dict) or not isinstance(bound_workspace, dict):
        _fail("invalid_binding", "task and workspace objects", binding,
              f"Worker {worker_id}'s packet is missing task or workspace scope.", reference="worker-binding")
    workspace = request.get("workspace")
    mode = request.get("mode")
    if (bound_workspace.get("route") != workspace
            or task.get("mode") != mode
            or Path(str(bound_workspace.get("source", ""))).resolve() != source):
        _fail("worker_binding_mismatch",
              {"workspace": workspace, "mode": mode, "source": os.fspath(source)},
              {"workspace": bound_workspace.get("route"), "mode": task.get("mode"),
               "source": bound_workspace.get("source")},
              f"Worker {worker_id}'s packet is bound to a different workspace, mode, or source.",
              reference="worker-binding", evidence_paths=[os.fspath(packet_path)])
    patterns = _write_set(binding, worker_id)
    delivery_mode = task.get("delivery_mode")
    if workspace == "worktree" and mode == "edit" and delivery_mode not in {"patch", "commits"}:
        _fail("invalid_worker_delivery_mode", ["patch", "commits"], delivery_mode,
              f"Worktree edit worker {worker_id} has no supported delivery mode.", reference="worker-binding")
    if (workspace == "current" or mode in {"report-only", "ephemeral"}) and delivery_mode is not None:
        _fail("invalid_worker_delivery_mode", None, delivery_mode,
              f"Worker {worker_id} carries a delivery mode outside worktree edit mode.", reference="worker-binding")
    if mode == "report-only" and patterns:
        _fail("invalid_worker_scope", [], patterns,
              f"Report-only worker {worker_id} must have an empty write_set.", reference="worker-binding")
    if mode in {"edit", "ephemeral"} and not patterns:
        _fail("invalid_worker_scope", "a non-empty write_set", patterns,
              f"Worker {worker_id} needs an explicit write_set for {mode} mode.", reference="worker-binding")
    if not isinstance(verified, dict):
        _fail("missing_verify_result", "the raw Ask Agent verify-return JSON object", verified,
              f"Worker {worker_id} has no collected verify-return result.", reference="worker-binding")
    if verified.get("status") != "READY_FOR_PARENT_ACCEPTANCE" or verified.get("command") != "verify-return":
        _fail("invalid_verify_result", {"status": "READY_FOR_PARENT_ACCEPTANCE", "command": "verify-return"},
              {"status": verified.get("status"), "command": verified.get("command")},
              f"Worker {worker_id}'s collected result is not a successful Ask Agent verify-return result.",
              reference="worker-binding")
    if verified.get("binding_sha256") != binding_sha:
        _fail("verify_binding_mismatch", binding_sha, verified.get("binding_sha256"),
              f"Worker {worker_id}'s verify-return JSON is not pinned to its prepared packet.",
              reference="worker-binding", evidence_paths=[os.fspath(packet_path)])
    if "worker_id" in verified and verified.get("worker_id") != worker_id:
        _fail("verify_worker_mismatch", worker_id, verified.get("worker_id"),
              f"Worker {worker_id}'s verify-return record names a different worker.", reference="worker-binding")
    row = {
        "id": worker_id,
        "prepared": prepared,
        "packet_path": packet_path,
        "packet_sha256": packet_sha,
        "binding_sha256": binding_sha,
        "binding": binding,
        "verified": verified,
        "write_set": patterns,
        "workspace": bound_workspace,
        "task": task,
    }
    if workspace == "worktree":
        command = prepared.get("commands", {}).get("verify-return") if isinstance(prepared.get("commands"), dict) else None
        argv = command.get("argv") if isinstance(command, dict) else None
        cwd_value = command.get("cwd") if isinstance(command, dict) else None
        if (not isinstance(argv, list) or not argv or any(not isinstance(part, str) for part in argv)
                or not isinstance(cwd_value, str) or not Path(cwd_value).is_absolute()):
            _fail("missing_verify_command", "the emitted commands.verify-return argv and cwd", command,
                  f"Worker {worker_id}'s prepare output does not contain its exact verify-return command.",
                  reference="worker-binding", evidence_paths=[os.fspath(packet_path)])
        if (str(cwd_value) != os.fspath(source)
                or argv.count("verify-return") != 1
                or argv.count("--binding") != 1
                or argv[argv.index("--binding") + 1:argv.index("--binding") + 2] != [os.fspath(packet_path)]
                or argv.count("--expected-binding-sha256") != 1
                or argv[argv.index("--expected-binding-sha256") + 1:argv.index("--expected-binding-sha256") + 2] != [binding_sha]):
            _fail("verify_command_mismatch",
                  {"cwd": os.fspath(source), "binding": os.fspath(packet_path), "binding_sha256": binding_sha},
                  {"cwd": cwd_value, "argv": argv},
                  f"Worker {worker_id}'s emitted verify-return command does not match its pinned packet.",
                  reference="worker-binding", evidence_paths=[os.fspath(packet_path)])
        row["verify_command"] = {"argv": argv, "cwd": Path(cwd_value)}
    return row


def _result_inspection(row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    verified = row["verified"]
    evidence = verified.get("workspace_evidence")
    if not isinstance(evidence, dict):
        _fail("invalid_workspace_evidence", "a workspace_evidence object", evidence,
              f"Worker {row['id']} has no Ask Agent workspace evidence.", reference="worker-return")
    if row["task"].get("mode") == "ephemeral":
        audit = evidence.get("ephemeral_audit")
        if (not isinstance(audit, dict) or audit.get("status") != "ephemeral-audit"
                or audit.get("findings_only") is not True or audit.get("scratch_retained") is not True):
            _fail("invalid_ephemeral_return", "a retained findings-only ephemeral audit", audit,
                  f"Worker {row['id']} did not return valid ephemeral workspace evidence.", reference="worker-return")
        changed = audit.get("changed_paths")
        if not isinstance(changed, list) or any(not isinstance(path, str) or not _matches_scope(path, row["write_set"]) for path in changed):
            _fail("ephemeral_scope_drift", row["write_set"], changed,
                  f"Worker {row['id']} returned ephemeral changes outside its write_set.", reference="worker-return")
        return None, audit
    inspection = evidence.get("inspection")
    if not isinstance(inspection, dict) or inspection.get("status") != "returned":
        _fail("invalid_return_inspection", "workspace_evidence.inspection.status returned", inspection,
              f"Worker {row['id']} did not return a checked worktree inspection.", reference="worker-return")
    if (inspection.get("receipt") != row["workspace"].get("receipt")
            or inspection.get("worktree") != row["workspace"].get("root")):
        _fail("return_workspace_mismatch",
              {"receipt": row["workspace"].get("receipt"), "worktree": row["workspace"].get("root")},
              {"receipt": inspection.get("receipt"), "worktree": inspection.get("worktree")},
              f"Worker {row['id']}'s return inspection is bound to a different helper workspace.",
              reference="worker-return")
    changed = inspection.get("contribution_paths")
    if not isinstance(changed, list) or any(not isinstance(path, str) or not is_write_scope(path) or path.endswith(GIT_PATH_SEPARATOR) for path in changed):
        _fail("invalid_contribution_paths", "exact relative contribution paths", changed,
              f"Worker {row['id']}'s returned inspection has invalid contribution paths.", reference="worker-return")
    if len(set(changed)) != len(changed) or any(not _matches_scope(path, row["write_set"]) for path in changed):
        _fail("worker_scope_drift", row["write_set"], changed,
              f"Worker {row['id']}'s returned contribution paths exceed or repeat its bound write_set.",
              reference="worker-return")
    delivery = inspection.get("delivery")
    delivery_paths = (delivery.get("commit_paths") if isinstance(delivery, dict) and delivery.get("mode") == "commits"
                      else delivery.get("contribution_paths") if isinstance(delivery, dict) else None)
    if not isinstance(delivery, dict) or delivery_paths != changed:
        _fail("invalid_delivery_evidence", {"contribution_paths": changed}, delivery,
              f"Worker {row['id']}'s delivery evidence does not match its returned inspection.",
              reference="worker-return")
    expected_delivery_mode = row["task"].get("delivery_mode") or "report-only"
    if delivery.get("mode") != expected_delivery_mode:
        _fail("delivery_mode_mismatch", expected_delivery_mode, delivery.get("mode"),
              f"Worker {row['id']}'s return uses a different delivery mode than its pinned packet.",
              reference="worker-return")
    if delivery.get("mode") == "commits":
        commits = delivery.get("commits")
        per_commit = delivery.get("per_commit_paths")
        if (not isinstance(commits, list) or not commits
                or any(not isinstance(sha, str) or not GIT_SHA_RE.fullmatch(sha) for sha in commits)
                or len(set(commits)) != len(commits)
                or not isinstance(per_commit, list) or len(per_commit) != len(commits)
                or delivery.get("base") != row["workspace"].get("commit_base")
                or delivery.get("commit_paths") != changed
                or delivery.get("residual_paths") != []):
            _fail("invalid_commit_delivery", "commit SHAs and paths bound to the prepared commit base", delivery,
                  f"Worker {row['id']}'s commit delivery evidence is incomplete.", reference="worker-return")
        committed_paths: set[str] = set()
        for commit, detail in zip(commits, per_commit):
            paths = detail.get("paths") if isinstance(detail, dict) else None
            if (not isinstance(detail, dict) or detail.get("commit") != commit
                    or not isinstance(paths, list) or not paths
                    or any(not isinstance(path, str) or path not in changed for path in paths)):
                _fail("invalid_commit_paths", changed, detail,
                      f"Worker {row['id']}'s per-commit paths do not match its contribution.", reference="worker-return")
            committed_paths.update(paths)
        if committed_paths != set(changed):
            _fail("invalid_commit_paths", sorted(changed), sorted(committed_paths),
                  f"Worker {row['id']}'s retained commits do not cover its complete contribution.",
                  reference="worker-return")
    return inspection, delivery


def _verify_worktree_rows(rows: Sequence[dict[str, Any]], attempt: _Attempt) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        command = row.get("verify_command")
        if command is None:
            continue
        record = attempt.command(f"verify-return-{index:02d}", command["argv"], command["cwd"])
        row["verify_command_record"] = record
        stdout_result: Any = None
        try:
            stdout_result = json.loads(record.get("stdout", ""))
        except (json.JSONDecodeError, TypeError):
            pass
        if (record.get("exit_code") != 0 or record.get("status") != "COMPLETED"
                or stdout_result != row["verified"]):
            problems.append({
                "worker_id": row["id"],
                "code": "verify_return_rerun_failed",
                "expected": {"exit_code": 0, "stdout_json": row["verified"]},
                "observed": {"exit_code": record.get("exit_code"), "stdout_json": stdout_result,
                             "status": record.get("status")},
                "evidence_paths": [record.get("evidence_path", "")],
            })
            continue
        try:
            inspection, delivery = _result_inspection(row)
            row["inspection"] = inspection
            row["delivery"] = delivery
        except DeliveryError as exc:
            problem = dict(exc.payload)
            problem["worker_id"] = row["id"]
            problems.append(problem)
    return problems


def _file_map(snapshot: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    files = snapshot.get("files")
    if not isinstance(files, list):
        _fail("invalid_snapshot", "snapshot.files array", type(files).__name__,
              "The supplied Git baseline does not contain file state.", reference="baseline")
    result: dict[str, dict[str, Any]] = {}
    for record in files:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            _fail("invalid_snapshot", "file records with relative paths", record,
                  "The supplied Git baseline has malformed file state.", reference="baseline")
        result[record["path"]] = record
    return result


def _changed_files(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    left, right = _file_map(before), _file_map(after)
    return sorted(path for path in left.keys() | right.keys() if left.get(path) != right.get(path))


def _index_head_fields(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {key: snapshot.get(key) for key in ("root", "branch", "head", "index_entries", "cached_diff_b64", "cached_diff_sha256")}


def _snapshot_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return _canonical_json(left) == _canonical_json(right)


def _scope_changes(paths: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> bool:
    union = [pattern for row in rows for pattern in row["write_set"]]
    return all(_matches_scope(path, union) for path in paths)


def _patch_paths(patch_path: Path, source: Path, attempt: _Attempt, label: str) -> tuple[set[str], dict[str, Any]]:
    argv = ["git", "-C", os.fspath(source), "-c", "core.autocrlf=false", "apply", "--numstat", "-z", os.fspath(patch_path)]
    record = attempt.command(label, argv, source)
    if record.get("exit_code") != 0:
        _fail("patch_inspection_failed", 0, record.get("exit_code"),
              "Git could not inspect a verified contribution patch.", reference="patch-inspection",
              evidence_paths=[record.get("evidence_path", "")])
    try:
        raw = base64.b64decode(record["stdout_b64"], validate=True)
    except (KeyError, ValueError) as exc:
        _fail("patch_inspection_failed", "binary numstat output", str(exc),
              "The retained patch inspection output is not readable.", reference="patch-inspection",
              evidence_paths=[record.get("evidence_path", "")])
    paths: set[str] = set()
    items = raw.split(b"\0")
    index = 0
    while index < len(items):
        item = items[index]
        index += 1
        if not item:
            continue
        fields = item.split(b"\t", 2)
        if len(fields) != 3:
            _fail("patch_inspection_failed", "Git numstat path records", item.hex(),
                  "The contribution patch produced malformed path evidence.", reference="patch-inspection",
                  evidence_paths=[record.get("evidence_path", "")])
        if fields[2]:
            paths.add(os.fsdecode(fields[2]))
            continue
        # With -z, a rename/copy has empty numstat path followed by old and new names.
        if index + 1 >= len(items) or not items[index] or not items[index + 1]:
            _fail("patch_inspection_failed", "two NUL-terminated rename paths", item.hex(),
                  "The contribution patch has an incomplete rename/copy path record.", reference="patch-inspection",
                  evidence_paths=[record.get("evidence_path", "")])
        paths.add(os.fsdecode(items[index]))
        paths.add(os.fsdecode(items[index + 1]))
        index += 2
    if not paths:
        _fail("empty_contribution_patch", "at least one changed contribution path", [],
              "The verified patch contains no applicable file contribution.", reference="patch-inspection",
              evidence_paths=[record.get("evidence_path", "")])
    return paths, record


def _verified_patch_source(row: Mapping[str, Any]) -> Path:
    delivery = row.get("delivery")
    inspection = row.get("inspection")
    nested_value = delivery.get("contribution_patch") if isinstance(delivery, dict) else None
    evidence = inspection.get("evidence") if isinstance(inspection, dict) else None
    evidence_value = evidence.get("contribution_patch") if isinstance(evidence, dict) else None
    nested_present, evidence_present = nested_value is not None, evidence_value is not None
    if nested_present and evidence_present and nested_value != evidence_value:
        _fail("conflicting_contribution_patch_paths", nested_value, evidence_value,
              f"Worker {row['id']}'s verified delivery and inspection evidence name different contribution patches.",
              reference="worker-return",
              evidence_paths=[value for value in (nested_value, evidence_value) if isinstance(value, str)])
    value = nested_value if nested_present else evidence_value
    if not isinstance(value, str) or not Path(value).is_absolute():
        _fail("missing_contribution_patch", "an absolute verified contribution patch in delivery or inspection evidence", value,
              f"Worker {row['id']} has no verified contribution patch to retain or apply.", reference="worker-return")
    source_path = Path(value)
    return source_path


def _read_verified_patch(row: Mapping[str, Any], attempt_root: Path) -> tuple[Path, str]:
    source_path = _verified_patch_source(row)
    value = os.fspath(source_path)
    try:
        info = source_path.lstat()
    except OSError as exc:
        _fail("missing_contribution_patch", "an existing regular contribution patch", f"{value}: {exc}",
              f"Worker {row['id']}'s verified contribution patch is unavailable.", reference="worker-return",
              evidence_paths=[value])
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        _fail("invalid_contribution_patch", "a regular non-symlink contribution patch", value,
              f"Worker {row['id']}'s verified contribution patch is not a regular file.", reference="worker-return",
              evidence_paths=[value])
    patch_bytes = _read_regular_nofollow(source_path, label=f"worker {row['id']} contribution patch")
    retained = attempt_root / "patches" / f"worker-{hashlib.sha256(row['id'].encode()).hexdigest()[:12]}.patch"
    _write_exclusive(retained, patch_bytes, mode=0o400)
    os.chmod(retained, 0o400)
    return retained, _sha256(patch_bytes)


def _record_verified_delivery(outcome: dict[str, Any], row: Mapping[str, Any],
                              inspection: Mapping[str, Any], delivery: Mapping[str, Any],
                              patch_path: Path, patch_sha256: str) -> None:
    mode = delivery.get("mode")
    paths = inspection.get("contribution_paths")
    summary = {
        "worker_id": row["id"],
        "binding_sha256": row["binding_sha256"],
        "mode": mode,
        "base": delivery.get("base"),
        "contribution_paths": list(paths) if isinstance(paths, list) else [],
        "commits": list(delivery.get("commits", [])),
        "per_commit_paths": list(delivery.get("per_commit_paths", [])),
        "source_patch_path": os.fspath(_verified_patch_source(row)),
        "patch_path": os.fspath(patch_path.resolve()),
        "patch_sha256": patch_sha256,
    }
    for worker_result in outcome.get("workers", []):
        if worker_result.get("id") == row["id"]:
            worker_result["delivery"] = summary
            break


def validate_request(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached five-field request or raise DeliveryError on invalid input."""
    if not isinstance(request, Mapping):
        _fail("invalid_request", "a request mapping", type(request).__name__,
              "Delivery needs an explicit request object.")
    try:
        raw = dict(request)
    except (TypeError, ValueError) as exc:
        _fail("invalid_request", "a request mapping", f"{type(exc).__name__}: {exc}",
              "Delivery could not read the request fields.")
    expected_keys = {"source", "workspace", "mode", "integration", "checks"}
    if set(raw) != expected_keys:
        _fail("invalid_request_fields", sorted(expected_keys), sorted(str(key) for key in raw),
              "Delivery accepts only the source, workspace, mode, integration, and checks fields.")
    source = _absolute_path(raw["source"], "request.source")
    if not source.is_dir():
        _fail("invalid_source", "an existing source directory", os.fspath(source),
              "The request source is not a directory.")
    if not isinstance(raw["workspace"], str) or raw["workspace"] not in {"current", "worktree"}:
        _fail("invalid_workspace", ["current", "worktree"], raw.get("workspace"),
              "Workspace must be current or worktree.")
    if not isinstance(raw["mode"], str) or raw["mode"] not in {"edit", "report-only", "ephemeral"}:
        _fail("invalid_mode", ["edit", "report-only", "ephemeral"], raw.get("mode"),
              "Mode must be edit, report-only, or ephemeral.")
    if not isinstance(raw["integration"], str) or raw["integration"] not in {"apply", "return-only"}:
        _fail("invalid_integration", ["apply", "return-only"], raw.get("integration"),
              "Integration must be apply or return-only.")
    checks = raw["checks"]
    if not isinstance(checks, list) or any(
            not isinstance(argv, list) or not argv
            or any(not isinstance(part, str) or not part or "\0" in part for part in argv)
            for argv in checks):
        _fail("invalid_checks", "an array of non-empty argv arrays without NUL bytes", checks,
              "Checks run as argv vectors without a shell.")
    if raw["workspace"] == "current" and raw["mode"] == "edit" and raw["integration"] != "apply":
        _fail("invalid_integration", "apply for an already-in-source current edit", raw["integration"],
              "Current edit contributions are already present in the parent checkout and cannot use return-only delivery.")
    if raw["workspace"] == "current" and raw["mode"] == "ephemeral":
        _fail("invalid_workspace_mode", "worktree for ephemeral mode", raw["workspace"],
              "Ephemeral findings must remain in a retained worktree.")
    if raw["mode"] == "edit" and raw["integration"] == "apply" and not checks:
        _fail("checks_required", "at least one check for edit/apply delivery", checks,
              "Edit contributions require a check after integration.")
    return {
        "source": os.fspath(source),
        "workspace": raw["workspace"],
        "mode": raw["mode"],
        "integration": raw["integration"],
        "checks": [list(argv) for argv in checks],
    }


def _validate_run_directory(value: str | Path) -> Path:
    try:
        raw = os.fspath(value)
    except (TypeError, ValueError) as exc:
        _fail("invalid_run_directory", "an explicit absolute run path",
              f"{type(exc).__name__}: {exc}", "Delivery needs an absolute run directory.",
              reference="attempt-reservation")
    if not isinstance(raw, str):
        _fail("invalid_run_directory", "an explicit absolute run path", type(raw).__name__,
              "Delivery needs an absolute run directory.", reference="attempt-reservation")
    if not raw or not Path(raw).is_absolute() or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        _fail("invalid_run_directory", "an explicit absolute printable run path", raw,
              "Delivery needs an absolute run directory.", reference="attempt-reservation")
    try:
        path = Path(raw).resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        _fail("invalid_run_directory", "a resolvable absolute run path", f"{raw}: {exc}",
              "The run directory cannot be resolved.", reference="attempt-reservation")
    if path.exists() and not path.is_dir():
        _fail("invalid_run_directory", "a directory path", os.fspath(path),
              "The run path names an existing non-directory.", reference="attempt-reservation")
    return path


def _validate_baseline_shape(value: Mapping[str, Any], source: Path) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail("invalid_baseline", SNAPSHOT_SCHEMA, type(value).__name__,
              "Delivery needs the parent Git snapshot produced by capture().", reference="baseline")
    try:
        baseline = json.loads(_canonical_json(dict(value)))
    except (TypeError, ValueError, OverflowError) as exc:
        _fail("invalid_baseline", "a JSON-safe Git snapshot",
              f"{type(exc).__name__}: {exc}", "The supplied baseline is not a JSON-safe snapshot.",
              reference="baseline")
    required = {
        "schema", "source", "root", "branch", "head", "index_entries",
        "cached_diff_b64", "cached_diff_sha256", "files", "status_b64", "status_sha256",
    }
    if not isinstance(baseline, dict) or set(baseline) != required or baseline.get("schema") != SNAPSHOT_SCHEMA:
        _fail("invalid_baseline", {"schema": SNAPSHOT_SCHEMA, "fields": sorted(required)},
              {"schema": baseline.get("schema") if isinstance(baseline, dict) else type(baseline).__name__,
               "fields": sorted(str(key) for key in baseline) if isinstance(baseline, dict) else []},
              "Delivery needs the complete parent Git snapshot produced by capture().", reference="baseline")
    if baseline["source"] != os.fspath(source):
        _fail("baseline_source_mismatch", os.fspath(source), baseline["source"],
              "The supplied baseline belongs to a different source path.", reference="baseline")
    root = _absolute_path(baseline["root"], "baseline.root")
    if not root.is_dir():
        _fail("invalid_baseline", "an existing Git root directory", os.fspath(root),
              "The supplied baseline root is not a directory.", reference="baseline")
    baseline["root"] = os.fspath(root)
    if (baseline["branch"] is not None and not isinstance(baseline["branch"], str)
            or not isinstance(baseline["head"], str) or not GIT_SHA_RE.fullmatch(baseline["head"])
            or len(baseline["head"]) not in {40, 64}):
        _fail("invalid_baseline", "a nullable branch and full Git HEAD", "branch/head fields",
              "The supplied baseline has malformed Git identity fields.", reference="baseline")
    index_entries = baseline["index_entries"]
    if not isinstance(index_entries, list):
        _fail("invalid_baseline", "an array of Git index entry objects", type(index_entries).__name__,
              "The supplied baseline has malformed index entries.", reference="baseline")
    index_identities: set[tuple[str, int]] = set()
    for entry in index_entries:
        if (not isinstance(entry, dict) or set(entry) != {"mode", "oid", "stage", "path"}
                or not isinstance(entry.get("mode"), str)
                or re.fullmatch(r"[0-7]{6}", entry["mode"]) is None
                or not isinstance(entry.get("oid"), str)
                or not GIT_SHA_RE.fullmatch(entry["oid"])
                or len(entry["oid"]) not in {40, 64}
                or type(entry.get("stage")) is not int or entry["stage"] not in {0, 1, 2, 3}
                or not is_git_relative_path(entry.get("path"))):
            _fail("invalid_baseline", "index entries with mode, oid, stage, and path", entry,
                  "The supplied baseline has a malformed Git index entry.", reference="baseline")
        identity = (entry["path"], entry["stage"])
        if identity in index_identities:
            _fail("invalid_baseline", "unique Git path and stage pairs", identity,
                  "The supplied baseline repeats a Git index entry identity.", reference="baseline")
        index_identities.add(identity)
    files = baseline["files"]
    if not isinstance(files, list):
        _fail("invalid_baseline", "an array of file records", type(files).__name__,
              "The supplied baseline has malformed file state.", reference="baseline")
    file_paths: set[str] = set()
    for record in files:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            _fail("invalid_baseline", "file records with a path and type", record,
                  "The supplied baseline has malformed file state.", reference="baseline")
        path, kind = record["path"], record.get("type")
        if not is_git_relative_path(path) or path in file_paths:
            _fail("invalid_baseline", "unique non-empty Git file paths", path,
                  "The supplied baseline repeats or invalidly encodes a file path.", reference="baseline")
        file_paths.add(path)
        if kind == "missing":
            valid_record = set(record) == {"path", "type"}
        elif kind == "file":
            valid_record = (
                set(record) == {"path", "mode", "type", "size", "sha256"}
                and type(record.get("mode")) is int and 0 <= record["mode"] <= 0o7777
                and type(record.get("size")) is int and record["size"] >= 0
                and isinstance(record.get("sha256"), str) and SHA256_RE.fullmatch(record["sha256"]) is not None
            )
        elif kind == "symlink":
            target_value = record.get("target_b64")
            try:
                target = base64.b64decode(target_value, validate=True) if isinstance(target_value, str) else None
            except (ValueError, TypeError):
                target = None
            valid_record = (
                set(record) == {"path", "mode", "type", "target_b64", "sha256"}
                and type(record.get("mode")) is int and 0 <= record["mode"] <= 0o7777
                and target is not None
                and isinstance(record.get("sha256"), str) and SHA256_RE.fullmatch(record["sha256"]) is not None
                and _sha256(target) == record["sha256"]
            )
        elif kind == "other":
            valid_record = (
                set(record) == {"path", "mode", "type"}
                and type(record.get("mode")) is int and 0 <= record["mode"] <= 0o7777
            )
        else:
            valid_record = False
        if not valid_record:
            _fail("invalid_baseline", "a complete capture() file record variant", record,
                  "The supplied baseline has a malformed file record.", reference="baseline")
    for data_key, digest_key in (("cached_diff_b64", "cached_diff_sha256"),
                                 ("status_b64", "status_sha256")):
        data, digest = baseline[data_key], baseline[digest_key]
        try:
            decoded = base64.b64decode(data, validate=True) if isinstance(data, str) else None
        except (ValueError, TypeError):
            decoded = None
        if (decoded is None or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)
                or _sha256(decoded) != digest):
            _fail("invalid_baseline", "base64 Git bytes with matching SHA-256",
                  {"field": data_key, "digest_field": digest_key},
                  "The supplied baseline has malformed or inconsistent Git byte evidence.", reference="baseline")
    return baseline


def _validate_workers_shape(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        _fail("invalid_workers", "an array of worker rows", type(value).__name__,
              "Workers must be supplied as a sequence.", reference="worker-binding")
    workers = list(value)
    if not workers:
        _fail("missing_workers", "at least one collected worker", [],
              "Delivery cannot validate an empty worker set.", reference="worker-binding")
    for worker in workers:
        if not isinstance(worker, dict):
            _fail("invalid_worker", "a worker object with id, prepared, and verified", type(worker).__name__,
                  "The delivery input contains a malformed worker row.", reference="worker-binding")
        if (not isinstance(worker.get("id"), str) or not worker["id"].strip()
                or any(ord(char) < 32 or ord(char) == 127 for char in worker["id"])
                or not isinstance(worker.get("prepared"), dict)
                or not isinstance(worker.get("verified"), dict)):
            _fail("invalid_worker", "a worker object with printable id, prepared, and verified objects",
                  worker.get("id"), "The delivery input contains a malformed worker row.",
                  reference="worker-binding")
    return workers


def _blocked_preflight(error: DeliveryError) -> dict[str, Any]:
    failure = dict(error.payload)
    failure.pop("status", None)
    return {
        "schema": SCHEMA,
        "status": "BLOCKED",
        "integration": {"outcome": "not-started"},
        "retained_locations": [],
        "checks": [],
        "failure": failure,
    }


def deliver(run_dir: str | Path, request: Mapping[str, Any], baseline: Mapping[str, Any], workers: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate and, when requested, apply bound worker contributions.

    One exclusive `run_dir/delivery` attempt is allowed. All command output and
    final outcomes are immutable JSON evidence. Failed or partial integrations
    are retained for inspection; this function never rolls them back or retries.
    """
    try:
        run = _validate_run_directory(run_dir)
        checked_request = validate_request(request)
        source = Path(checked_request["source"])
        baseline_obj = _validate_baseline_shape(baseline, source)
        worker_inputs = _validate_workers_shape(workers)
    except DeliveryError as exc:
        return _blocked_preflight(exc)

    try:
        run.mkdir(parents=True, exist_ok=True)
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "schema": SCHEMA, "status": "BLOCKED",
            "integration": {"outcome": "not-started"}, "retained_locations": [], "checks": [],
            "failure": {"code": "invalid_run_directory", "expected": "a writable run directory",
                        "observed": f"{type(exc).__name__}: {exc}", "rationale": "Delivery evidence cannot be reserved.",
                        "reference": _contract_reference("attempt-reservation"), "evidence_paths": [],
                        "safe_next_step": "Select a writable run directory and retry."},
        }
    attempt_root = run / DELIVERY_DIRECTORY
    try:
        attempt_root.mkdir()
    except FileExistsError:
        evidence = os.fspath(attempt_root / ATTEMPT_RECORD_NAME)
        return {
            "schema": SCHEMA, "status": "BLOCKED",
            "integration": {"outcome": "not-started"},
            "retained_locations": [os.fspath(attempt_root), evidence], "checks": [],
            "failure": {"code": "delivery_attempt_already_reserved", "expected": "one delivery attempt per run",
                        "observed": evidence, "rationale": "An earlier delivery attempt is already retained; it is never overwritten or replayed.",
                        "reference": _contract_reference("attempt-reservation"), "evidence_paths": [evidence],
                        "safe_next_step": "Inspect the existing delivery evidence and start a fresh run only after resolving its outcome."},
        }
    except OSError as exc:
        return {
            "schema": SCHEMA, "status": "BLOCKED",
            "integration": {"outcome": "not-started"}, "retained_locations": [os.fspath(attempt_root)], "checks": [],
            "failure": {"code": "delivery_attempt_reservation_failed", "expected": "exclusive delivery directory",
                        "observed": f"{type(exc).__name__}: {exc}", "rationale": "Delivery evidence could not be reserved.",
                        "reference": _contract_reference("attempt-reservation"), "evidence_paths": [os.fspath(attempt_root)],
                        "safe_next_step": "Inspect the run directory and retry in a fresh run."},
        }
    reservation = {
        "schema": SCHEMA,
        "status": "RUNNING",
        "run_dir": os.fspath(run),
        "started_epoch": time.time(),
        "request": checked_request,
        "baseline_sha256": _sha256(_canonical_json(baseline_obj)),
        "retry_semantics": "One attempt per run; command logs and partial source changes are retained without rollback.",
    }
    try:
        _write_json_exclusive(attempt_root / ATTEMPT_RECORD_NAME, reservation)
    except OSError as exc:
        return {
            "schema": SCHEMA, "status": "BLOCKED",
            "integration": {"outcome": "not-started"}, "retained_locations": [os.fspath(attempt_root)], "checks": [],
            "failure": {"code": "delivery_attempt_reservation_failed", "expected": "exclusive attempt.json",
                        "observed": f"{type(exc).__name__}: {exc}", "rationale": "Delivery evidence could not be reserved.",
                        "reference": _contract_reference("attempt-reservation"), "evidence_paths": [os.fspath(attempt_root)],
                        "safe_next_step": "Inspect the run directory and retry in a fresh run."},
        }
    try:
        attempt = _Attempt(attempt_root)
    except OSError as exc:
        outcome = {
            "schema": SCHEMA, "status": "FAILED",
            "integration": {"outcome": "not-started", "applied_paths": [], "application_attempted": False},
            "retained_locations": [os.fspath(attempt_root), os.fspath(attempt_root / ATTEMPT_RECORD_NAME)],
            "checks": [], "result_path": os.fspath(attempt_root / RESULT_RECORD_NAME),
            "failure": {"code": "delivery_log_directory_failed", "expected": "exclusive commands directory",
                        "observed": f"{type(exc).__name__}: {exc}",
                        "rationale": "The delivery attempt was reserved, but immutable command logs could not be created.",
                        "reference": _contract_reference("attempt-reservation"), "evidence_paths": [os.fspath(attempt_root / ATTEMPT_RECORD_NAME)],
                        "safe_next_step": "Inspect the retained reservation and start a fresh run after resolving the filesystem issue."},
        }
        try:
            _write_json_exclusive(attempt_root / RESULT_RECORD_NAME, outcome)
        except OSError:
            pass
        return outcome
    outcome: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "FAILED",
        "integration": {"outcome": "not-started", "applied_paths": [], "application_attempted": False},
        "retained_locations": [os.fspath(attempt_root)],
        "checks": [],
        "started_epoch": reservation["started_epoch"],
    }
    try:
        baseline_root = _repo_root(source, attempt)
        if baseline_obj.get("root") != os.fspath(baseline_root):
            _fail("baseline_source_mismatch", {"source": os.fspath(source), "root": os.fspath(baseline_root)},
                  {"source": baseline_obj.get("source"), "root": baseline_obj.get("root")},
                  "The supplied baseline belongs to a different source checkout.", reference="baseline")
        rows: list[dict[str, Any]] = []
        binding_problems: list[dict[str, Any]] = []
        for worker in worker_inputs:
            try:
                rows.append(_load_worker(checked_request, source, worker))
            except DeliveryError as exc:
                problem = dict(exc.payload)
                if isinstance(worker, dict) and isinstance(worker.get("id"), str):
                    problem["worker_id"] = worker["id"]
                binding_problems.append(problem)
        ids = [row["id"] for row in rows]
        if len(set(ids)) != len(ids):
            _fail("duplicate_worker_id", "unique worker ids", ids,
                  "A worker id can be bound to only one prepared packet.", reference="worker-binding")
        packet_paths = [os.fspath(row["packet_path"]) for row in rows]
        if len(set(packet_paths)) != len(packet_paths):
            _fail("duplicate_worker_packet", "one unique prepared packet per worker", packet_paths,
                  "Two worker rows point to the same pinned Ask Agent packet.", reference="worker-binding")
        outcome["workers"] = [{"id": row["id"], "packet_path": os.fspath(row["packet_path"]),
                               "packet_sha256": row["packet_sha256"], "binding_sha256": row["binding_sha256"],
                               "write_set": row["write_set"],
                               "worktree": row["workspace"].get("root") if row["workspace"].get("route") == "worktree" else None,
                               "branch": row["workspace"].get("branch"),
                               "receipt": row["workspace"].get("receipt")} for row in rows]

        # The exact emitted command is rerun for every worktree return before any import.
        verification_problems = _verify_worktree_rows(rows, attempt) if checked_request["workspace"] == "worktree" else []
        verification_problems = [*binding_problems, *verification_problems]
        for row in rows:
            workspace = row["workspace"]
            if workspace.get("route") == "worktree":
                for key in ("root", "receipt"):
                    value = workspace.get(key)
                    if not isinstance(value, str) or not Path(value).is_absolute():
                        verification_problems.append({"worker_id": row["id"], "code": "invalid_worktree_location",
                                                      "expected": f"absolute workspace.{key}", "observed": value,
                                                      "evidence_paths": [os.fspath(row["packet_path"])]})
                        continue
                    outcome["retained_locations"].append(value)
                    path = Path(value)
                    if key == "root" and not path.is_dir():
                        verification_problems.append({"worker_id": row["id"], "code": "missing_worktree",
                                                      "expected": "an existing retained worktree directory", "observed": value,
                                                      "evidence_paths": [os.fspath(row["packet_path"])]})
                    if key == "receipt" and (path.is_symlink() or not path.is_file()):
                        verification_problems.append({"worker_id": row["id"], "code": "missing_receipt",
                                                      "expected": "an existing regular helper receipt", "observed": value,
                                                      "evidence_paths": [os.fspath(row["packet_path"])]})
                if workspace.get("root") == os.fspath(source):
                    verification_problems.append({"worker_id": row["id"], "code": "worktree_is_source",
                                                  "expected": "a separate retained worktree", "observed": workspace.get("root"),
                                                  "evidence_paths": [os.fspath(row["packet_path"])]})
        if verification_problems:
            _fail("worktree_return_verification_failed", "every worktree return passes its pinned verify-return command and binding checks",
                  verification_problems, "At least one worktree return could not be revalidated; no contribution was imported.",
                  reference="verify-return", evidence_paths=[item for problem in verification_problems for item in problem.get("evidence_paths", [])])

        current = capture(source, _attempt=attempt)
        integration = checked_request["integration"]
        mode = checked_request["mode"]
        workspace_kind = checked_request["workspace"]
        if workspace_kind == "worktree":
            if not _snapshot_equal(current, baseline_obj):
                _fail("parent_source_drift", baseline_obj, current,
                      "The parent checkout changed after its captured baseline; no worker patch will be applied.",
                      reference="integration-preflight", evidence_paths=[os.fspath(attempt_root / ATTEMPT_RECORD_NAME)])
            if mode == "edit":
                for row in rows:
                    inspection, delivery = _result_inspection(row)
                    row["inspection"], row["delivery"] = inspection, delivery
                    expected_base = (row["workspace"].get("commit_base")
                                     if delivery.get("mode") == "commits" else baseline_obj.get("head"))
                    if delivery.get("base") != expected_base:
                        _fail("contribution_base_mismatch", expected_base, delivery.get("base"),
                              f"Worker {row['id']}'s patch is based on a different parent snapshot.",
                              reference="patch-preflight")
                    if isinstance(delivery.get("commits"), list):
                        outcome["retained_locations"].extend(delivery["commits"])
                    patch_value = delivery.get("contribution_patch")
                    if isinstance(patch_value, str) and Path(patch_value).is_absolute():
                        outcome["retained_locations"].append(patch_value)
            if mode == "edit" and integration == "apply":
                contributions: list[dict[str, Any]] = []
                all_paths: set[str] = set()
                for row in rows:
                    inspection, delivery = _result_inspection(row)
                    row["inspection"], row["delivery"] = inspection, delivery
                    if not isinstance(delivery, dict) or delivery.get("mode") not in {"patch", "commits"}:
                        _fail("invalid_delivery_mode", ["patch", "commits"], delivery,
                              f"Worker {row['id']} returned an unsupported edit delivery mode.", reference="worker-return")
                    if not isinstance(inspection, dict):
                        _fail("invalid_return_inspection", "a verified worktree inspection object", inspection,
                              f"Worker {row['id']} has no verified contribution path list.", reference="worker-return")
                    patch_path, patch_sha = _read_verified_patch(row, attempt_root)
                    _record_verified_delivery(outcome, row, inspection, delivery, patch_path, patch_sha)
                    patch_paths, numstat_record = _patch_paths(patch_path, source, attempt, f"patch-paths-{len(contributions) + 1:02d}")
                    declared_paths = inspection.get("contribution_paths")
                    if not isinstance(declared_paths, list):
                        _fail("invalid_contribution_paths", "inspection.contribution_paths array", declared_paths,
                              f"Worker {row['id']}'s verified inspection has no contribution path list.",
                              reference="worker-return")
                    declared = set(declared_paths)
                    if patch_paths != declared:
                        _fail("patch_path_mismatch", sorted(declared), sorted(patch_paths),
                              f"Worker {row['id']}'s immutable patch paths differ from its verified contribution paths.",
                              reference="patch-preflight", evidence_paths=[os.fspath(patch_path), numstat_record.get("evidence_path", "")])
                    overlap = sorted(path for path in patch_paths if any(path == prior or path.startswith(prior + "/") or prior.startswith(path + "/") for prior in all_paths))
                    if overlap:
                        _fail("overlapping_contributions", "disjoint worker contribution paths", overlap,
                              "Worker patches overlap by path or ancestor; no patch was applied.",
                              reference="integration-preflight", evidence_paths=[os.fspath(patch_path)])
                    all_paths.update(patch_paths)
                    commits = delivery.get("commits", []) if delivery.get("mode") == "commits" else []
                    if delivery.get("mode") == "commits":
                        if (not isinstance(commits, list) or not commits
                                or any(not isinstance(sha, str) or not GIT_SHA_RE.fullmatch(sha) for sha in commits)
                                or len(set(commits)) != len(commits)
                                or delivery.get("base") != row["workspace"].get("commit_base")
                                or delivery.get("commit_paths") != sorted(declared)
                                or delivery.get("residual_paths") != []):
                            _fail("invalid_commit_delivery", "verified commit SHAs and paths bound to the prepared commit base",
                                  delivery, f"Worker {row['id']}'s commit delivery evidence is incomplete.", reference="worker-return")
                        outcome["retained_locations"].extend(commits)
                    contributions.append({"row": row, "patch": patch_path, "patch_sha256": patch_sha,
                                          "paths": sorted(patch_paths), "commits": commits})
                if not contributions:
                    integration_result = {"outcome": "applied", "applied_paths": [], "application_attempted": False}
                else:
                    # Combine only exact verified patch bytes so Git validates and applies one batch.
                    batch_path = attempt_root / "patches" / "batch.patch"
                    patch_chunks: list[bytes] = []
                    for item in contributions:
                        patch_bytes = _read_regular_nofollow(item["patch"], label="retained contribution patch")
                        if _sha256(patch_bytes) != item["patch_sha256"]:
                            _fail("retained_patch_changed", item["patch_sha256"], _sha256(patch_bytes),
                                  "A retained verified patch changed after its immutable copy was saved.",
                                  reference="patch-preflight", evidence_paths=[os.fspath(item["patch"])])
                        patch_chunks.append(patch_bytes + (b"" if patch_bytes.endswith(b"\n") else b"\n"))
                    combined = b"".join(patch_chunks)
                    _write_exclusive(batch_path, combined, mode=0o400)
                    os.chmod(batch_path, 0o400)
                    pre_apply = capture(source, _attempt=attempt)
                    if not _snapshot_equal(pre_apply, baseline_obj):
                        _fail("parent_source_drift", baseline_obj, pre_apply,
                              "The parent checkout changed during patch preparation; no patch was applied.",
                              reference="integration-preflight", evidence_paths=[os.fspath(batch_path)])
                    apply_prefix = ["git", "-C", os.fspath(source), "-c", "core.autocrlf=false", "apply"]
                    check_record = attempt.command("apply-check-batch", [*apply_prefix, "--check", "--binary", "--whitespace=nowarn", os.fspath(batch_path)], source)
                    if check_record.get("exit_code") != 0:
                        _fail("patch_apply_check_failed", 0, check_record.get("exit_code"),
                              "Git rejected the complete verified patch batch; no apply command was issued.",
                              reference="patch-preflight", evidence_paths=[check_record.get("evidence_path", ""), os.fspath(batch_path)])
                    if _sha256(_read_regular_nofollow(batch_path, label="retained batch patch")) != _sha256(combined):
                        _fail("retained_batch_changed", _sha256(combined), "changed",
                              "The retained batch patch changed after Git checked it; no apply command was issued.",
                              reference="patch-preflight", evidence_paths=[os.fspath(batch_path)])
                    immediately_before_apply = capture(source, _attempt=attempt)
                    if not _snapshot_equal(immediately_before_apply, baseline_obj):
                        _fail("parent_source_drift", baseline_obj, immediately_before_apply,
                              "The parent checkout changed after patch validation; no patch was applied.",
                              reference="integration-preflight", evidence_paths=[os.fspath(batch_path)])
                    apply_record = attempt.command("apply-batch", [*apply_prefix, "--binary", "--whitespace=nowarn", os.fspath(batch_path)], source)
                    integration_result = {"outcome": "apply-command-failed" if apply_record.get("exit_code") != 0 else "applied",
                                          "applied_paths": sorted(all_paths), "application_attempted": True,
                                          "batch_patch": os.fspath(batch_path), "batch_sha256": _sha256(combined),
                                          "apply_check_evidence": check_record["evidence_path"],
                                          "apply_evidence": apply_record["evidence_path"],
                                          "workers": [{"id": item["row"]["id"], "paths": item["paths"],
                                                       "patch": os.fspath(item["patch"]), "patch_sha256": item["patch_sha256"],
                                                       "commits": item["commits"]} for item in contributions]}
                    outcome["integration"] = integration_result
                    outcome["retained_locations"].extend([os.fspath(item["patch"]) for item in contributions])
                    outcome["retained_locations"].append(os.fspath(batch_path))
                    if apply_record.get("exit_code") != 0:
                        _fail("patch_apply_failed", 0, apply_record.get("exit_code"),
                              "Git's batch apply command failed. Any partial filesystem changes are retained without rollback.",
                              reference="integration", status="FAILED", evidence_paths=[apply_record.get("evidence_path", ""), os.fspath(batch_path)])
                    after_apply = capture(source, _attempt=attempt)
                    changed = _changed_files(baseline_obj, after_apply)
                    if not set(changed).issubset(all_paths):
                        _fail("post_apply_scope_drift", sorted(all_paths), changed,
                              "The parent checkout contains changes outside the verified contribution paths after apply.",
                              reference="post-integration", status="FAILED", evidence_paths=[os.fspath(batch_path)])
                    if _index_head_fields(after_apply) != _index_head_fields(baseline_obj):
                        _fail("post_apply_git_state_changed", _index_head_fields(baseline_obj), _index_head_fields(after_apply),
                              "Patch application changed parent HEAD, branch, or index state.",
                              reference="post-integration", status="FAILED", evidence_paths=[os.fspath(batch_path)])
                    for item in contributions:
                        worker_root = Path(item["row"]["workspace"]["root"])
                        for relative in item["paths"]:
                            source_record = _file_record(source, relative)
                            worker_record = _file_record(worker_root, relative)
                            if source_record != worker_record:
                                _fail("worker_file_mismatch", worker_record, source_record,
                                      f"Parent file `{relative}` differs from worker {item['row']['id']}'s retained file after apply.",
                                      reference="post-integration", status="FAILED", evidence_paths=[os.fspath(batch_path)])
                    integration_result["postcondition"] = {"changed_paths": changed, "allowed_paths": sorted(all_paths),
                                                            "head_and_index_preserved": True, "worker_files_match": True}
            elif mode == "edit":
                # Return-only validates and retains returns without importing them.
                for row in rows:
                    inspection, delivery = _result_inspection(row)
                    row["inspection"], row["delivery"] = inspection, delivery
                    if not isinstance(inspection, dict):
                        _fail("invalid_return_inspection", "a verified worktree inspection object", inspection,
                              f"Worker {row['id']} has no verified contribution path list.", reference="worker-return")
                    patch_path, patch_sha = _read_verified_patch(row, attempt_root)
                    _record_verified_delivery(outcome, row, inspection, delivery, patch_path, patch_sha)
                    if isinstance(delivery, dict) and isinstance(delivery.get("commits"), list):
                        outcome["retained_locations"].extend(delivery["commits"])
                    if isinstance(delivery, dict) and isinstance(delivery.get("contribution_patch"), str):
                        outcome["retained_locations"].append(delivery["contribution_patch"])
                    outcome["retained_locations"].append(os.fspath(patch_path))
                integration_result = {"outcome": "return-only", "applied_paths": [], "application_attempted": False}
            else:
                for row in rows:
                    _result_inspection(row)
                integration_result = {"outcome": "not-applicable", "applied_paths": [], "application_attempted": False}
            outcome["integration"] = integration_result
        elif mode == "edit":
            for row in rows:
                evidence = row["verified"].get("workspace_evidence")
                if not isinstance(evidence, dict):
                    _fail("invalid_workspace_evidence", "workspace_evidence object", evidence,
                          f"Current worker {row['id']} has no verify-return evidence.", reference="worker-return")
                changed_by_worker = evidence.get("changed_paths", [])
                if (not isinstance(changed_by_worker, list)
                        or any(not isinstance(path, str) or not _matches_scope(path, row["write_set"]) for path in changed_by_worker)
                        or evidence.get("outside_write_set") != []):
                    _fail("current_worker_scope_drift", row["write_set"], evidence,
                          f"Current worker {row['id']}'s verified changes exceed its prepared write_set.",
                          reference="worker-return")
                if evidence.get("write_set") != row["write_set"]:
                    _fail("current_worker_scope_mismatch", row["write_set"], evidence.get("write_set"),
                          f"Current worker {row['id']}'s verify-return scope differs from its pinned packet.",
                          reference="worker-return")
            changed = _changed_files(baseline_obj, current)
            if not _scope_changes(changed, rows):
                _fail("current_parent_scope_drift", [row["write_set"] for row in rows], changed,
                      "Current edit changes exceed the union of the worker write sets.", reference="post-integration")
            if _index_head_fields(current) != _index_head_fields(baseline_obj):
                _fail("current_parent_git_state_changed", _index_head_fields(baseline_obj), _index_head_fields(current),
                      "Current edit changed parent HEAD, branch, or index state.", reference="post-integration")
            outcome["integration"] = {"outcome": "current-workspace-validated", "applied_paths": changed,
                                      "application_attempted": False,
                                      "postcondition": {"changed_paths": changed, "allowed_paths": changed,
                                                        "head_and_index_preserved": True}}
        else:
            if not _snapshot_equal(current, baseline_obj):
                _fail("current_parent_changed", baseline_obj, current,
                      f"Current {mode} work must leave the parent checkout unchanged.", reference="post-integration")
            outcome["integration"] = {"outcome": "current-workspace-unchanged", "applied_paths": [],
                                      "application_attempted": False}

        # Findings and return-only requests may omit checks. Supplied checks always run
        # after the integration decision and must leave the source snapshot unchanged.
        check_failure: tuple[int, dict[str, Any]] | None = None
        check_snapshot_before: dict[str, Any] | None = None
        if checked_request["checks"]:
            check_snapshot_before = capture(source, _attempt=attempt)
            check_snapshot_before_path = attempt_root / "check-snapshots" / "before.json"
            _write_json_exclusive(check_snapshot_before_path, check_snapshot_before)
        for index, argv in enumerate(checked_request["checks"], start=1):
            record = attempt.command(f"check-{index:02d}", argv, source)
            outcome["checks"].append({"argv": argv, "exit_code": record.get("exit_code"),
                                      "status": "PASSED" if record.get("exit_code") == 0 else "FAILED",
                                      "evidence_path": record.get("evidence_path"),
                                      "stdout": record.get("stdout", ""), "stderr": record.get("stderr", "")})
            if record.get("exit_code") != 0:
                check_failure = (index, record)
                break
        if check_snapshot_before is not None:
            check_snapshot_after = capture(source, _attempt=attempt)
            check_snapshot_after_path = attempt_root / "check-snapshots" / "after.json"
            _write_json_exclusive(check_snapshot_after_path, check_snapshot_after)
            check_snapshot_equal = _snapshot_equal(check_snapshot_before, check_snapshot_after)
            changed_by_checks = _changed_files(check_snapshot_before, check_snapshot_after)
            check_git_state_preserved = _index_head_fields(check_snapshot_before) == _index_head_fields(check_snapshot_after)
            outcome["check_postcondition"] = {
                "exact_snapshot_unchanged": check_snapshot_equal,
                "changed_paths": changed_by_checks,
                "head_and_index_preserved": check_git_state_preserved,
                "before_snapshot": os.fspath(check_snapshot_before_path.resolve()),
                "after_snapshot": os.fspath(check_snapshot_after_path.resolve()),
            }
            if not check_snapshot_equal:
                _fail("post_check_source_drift",
                      {"snapshot_sha256": _sha256(_canonical_json(check_snapshot_before)), "unchanged": True},
                      {"snapshot_sha256": _sha256(_canonical_json(check_snapshot_after)),
                       "changed_paths": changed_by_checks,
                       "head_and_index_preserved": check_git_state_preserved,
                       "status_changed": check_snapshot_before.get("status_sha256") != check_snapshot_after.get("status_sha256")},
                      "A delivery check changed the source checkout after integration; the change and evidence are retained without rollback.",
                      reference="post-check", status="FAILED",
                      evidence_paths=[os.fspath(check_snapshot_before_path), os.fspath(check_snapshot_after_path),
                                      *[item.get("evidence_path", "") for item in outcome["checks"]]])
        if check_failure is not None:
            failed_index, record = check_failure
            _fail("delivery_check_failed", 0, record.get("exit_code"),
                  f"Check {failed_index} failed after the integration decision; source changes and evidence are retained.",
                  reference="checks", status="FAILED", evidence_paths=[record.get("evidence_path", "")])
        outcome["status"] = "SUCCEEDED"
        outcome["finished_epoch"] = time.time()
    except DeliveryError as exc:
        outcome["status"] = exc.payload.pop("status", "BLOCKED")
        outcome["failure"] = dict(exc.payload)
        outcome["failure"]["evidence_paths"] = list(dict.fromkeys(
            [*outcome["failure"].get("evidence_paths", []), os.fspath(attempt_root / ATTEMPT_RECORD_NAME)]))
        outcome["finished_epoch"] = time.time()
    except Exception as exc:  # retain unexpected failures as evidence too
        outcome["status"] = "FAILED"
        outcome["failure"] = {
            "code": "delivery_internal_error",
            "expected": "a completed delivery decision",
            "observed": f"{type(exc).__name__}: {exc}",
            "rationale": "Delivery stopped unexpectedly; any partial filesystem changes are retained without rollback.",
            "reference": _contract_reference("delivery"),
            "evidence_paths": [os.fspath(attempt_root / ATTEMPT_RECORD_NAME)],
            "safe_next_step": "Inspect retained command and source evidence before taking any follow-up action.",
        }
        outcome["finished_epoch"] = time.time()
    outcome["retained_locations"] = list(dict.fromkeys(outcome["retained_locations"]))
    outcome["result_path"] = os.fspath(attempt_root / RESULT_RECORD_NAME)
    try:
        _write_json_exclusive(attempt_root / RESULT_RECORD_NAME, outcome)
    except OSError as exc:
        outcome["status"] = "FAILED"
        outcome["failure"] = {
            "code": "delivery_result_write_failed", "expected": "exclusive immutable result.json",
            "observed": f"{type(exc).__name__}: {exc}",
            "rationale": "The attempt and command logs are retained, but the final result could not be written.",
            "reference": _contract_reference("result-write"), "evidence_paths": [os.fspath(attempt_root / ATTEMPT_RECORD_NAME)],
            "safe_next_step": "Inspect the retained attempt and command logs; do not replay this run.",
        }
    return outcome
