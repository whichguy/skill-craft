#!/usr/bin/env python3
"""Collect and verify action-bound initial Plan quote evidence.

Collection reads a stopped run and its recorded Git snapshot. Verification of
linked files reads only a portable receipt and content pinned by the caller.
Neither operation runs ShipLoop.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import tempfile
from typing import Any

import planning_trace


SCHEMA = "shiploop-initial-plan-evidence/v1"
MANIFEST_NAME = "planning-evidence.json"
CAPTURE_BASIS = "automatic-producer-bind-git-snapshot"
RECEIPT_KIND = "derived-after-producer"
MAX_BLOB_BYTES = 2 * 1024 * 1024
_MAX_RECORD_BYTES = 2 * 1024 * 1024
_MAX_SET_BYTES = 16 * 1024 * 1024
_MAX_LOCATORS = 256
_MAX_LOCATOR_CHARS = 4096
_SHA256 = re.compile(r"[0-9a-f]{64}")
_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
_SUFFIX = re.compile(r"(#.*|::.*|:\d+(?::\d+)?)$")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


@dataclass(frozen=True)
class ExpectedPlan:
    """Caller-bound identities. producer_revision is the revision entering Improve."""

    run_id: str
    plan_action: str
    improve_action: str
    producer_revision: int
    seed_sha256: str
    repo: str
    repo_prefix: str
    phase: str = "initial"


class _EvidenceError(ValueError):
    def __init__(self, status: str, reason: str):
        super().__init__(reason)
        self.status = status


def _require(condition: Any, reason: str, status: str = "invalid") -> None:
    if not condition:
        raise _EvidenceError(status, reason)


def _result(status: str, reason: str | None = None, **fields: Any) -> dict[str, Any]:
    return {"status": status, "reason": reason, **fields}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _matches(pattern: re.Pattern[str], value: Any) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise _EvidenceError("invalid", f"non-JSON constant {value}")


def _json_dict(text: str) -> dict[str, Any]:
    value = json.loads(text, object_pairs_hook=_object, parse_constant=_reject_constant)
    _require(isinstance(value, dict), "expected a JSON object")
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def seed_digest(value: dict[str, Any]) -> str:
    """Digest of a parsed Plan seed in the producer's bind-record format."""
    return _sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8"))


def _state_record(data: bytes) -> dict[str, Any]:
    # ShipLoop writes exactly one Markdown fence with this tag and a JSON object.
    lines = data.decode("utf-8").replace("\r\n", "\n").split("\n")
    starts = [i for i, line in enumerate(lines) if line.rstrip(" \t") == "```shiploop-state"]
    _require(len(starts) == 1, "expected one shiploop-state fence")
    start = starts[0] + 1
    end = next((i for i in range(start, len(lines)) if lines[i].rstrip(" \t") == "```"), None)
    _require(end is not None, "unterminated shiploop-state fence")
    return _json_dict("\n".join(lines[start:end]))


def _read_file(root: Path, relative: str, limit: int) -> tuple[bytes, os.stat_result]:
    """Bounded read of one regular file without following internal symlinks."""
    parts = relative.split("/")
    _require(all(part and part not in (".", "..") for part in parts), "unsafe evidence path")
    directory = os.open(root, _DIR_FLAGS)
    try:
        for part in parts[:-1]:
            child = os.open(part, _DIR_FLAGS, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], _FILE_FLAGS, dir_fd=directory)
        with os.fdopen(fd, "rb") as handle:
            before = os.fstat(handle.fileno())
            _require(stat.S_ISREG(before.st_mode), "evidence source is not a regular file")
            _require(before.st_size <= limit, "evidence source exceeds size bound", "unsupported")
            data = handle.read(limit + 1)
            after = os.fstat(handle.fileno())
            named = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
            _require(len(data) == before.st_size and _fingerprint(before) == _fingerprint(after)
                     == _fingerprint(named), "evidence source changed during read", "unavailable")
            return data, before
    finally:
        os.close(directory)


def _fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
    return (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)


def _read_source(root: Path, relative: str) -> tuple[bytes, os.stat_result]:
    try:
        return _read_file(root, relative, _MAX_RECORD_BYTES)
    except OSError as exc:
        raise _EvidenceError("unavailable", f"cannot read {relative}: {exc.strerror}") from exc


def _parse_source(data: bytes, name: str, *, markdown: bool = True) -> dict[str, Any]:
    try:
        return _state_record(data) if markdown else _json_dict(data.decode("utf-8"))
    except (ValueError, RecursionError) as exc:
        raise _EvidenceError("unavailable", f"cannot parse {name}: {exc}") from exc


def _path_components(value: str) -> bool:
    return (len(value) <= _MAX_LOCATOR_CHARS and "\\" not in value and "\x00" not in value
            and all(part and part not in (".", "..", ".git") for part in value.split("/"))
            and not any(ord(char) < 32 or ord(char) == 127 for char in value))


def _absolute_path(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("/") and _path_components(value[1:])


def _check_ids(run_id: str, plan_action: str, improve_action: str, seed_sha256: str, phase: str) -> None:
    _require(phase == "initial", "only the initial phase is supported", "unsupported")
    _require(all(_matches(_ID, value) for value in (run_id, plan_action, improve_action))
             and plan_action != improve_action and _matches(_SHA256, seed_sha256),
             "invalid expected run, action or seed identity")


def _check_expected(expected: ExpectedPlan) -> None:
    _require(isinstance(expected, ExpectedPlan), "expected Plan identities are required")
    _check_ids(expected.run_id, expected.plan_action, expected.improve_action, expected.seed_sha256, expected.phase)
    _require(type(expected.producer_revision) is int and expected.producer_revision > 0,
             "invalid expected producer revision")
    _require(_absolute_path(expected.repo), "invalid expected repository path")
    _require(isinstance(expected.repo_prefix, str)
             and (expected.repo_prefix == "." or _path_components(expected.repo_prefix)),
             "invalid expected repository prefix")


def _initial_result(
    state: dict[str, Any], run_id: str, plan_action: str, improve_action: str, seed_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require(state.get("run_id") == run_id, "saved run identity differs from expectation")
    records = state.get("improve_results")
    _require(isinstance(records, dict), "saved Improve results are missing", "unavailable")
    record = records.get(plan_action)
    _require(isinstance(record, dict), "expected Plan has no saved Improve result", "unavailable")
    _require(type(record.get("version")) is int and record["version"] == 1
             and record.get("action_id") == plan_action and record.get("improve_action") == improve_action
             and record.get("binding_id") == f"{run_id}/{plan_action}" and record.get("stage") == "plan",
             "saved Plan/Improve binding differs from expectation")
    history = state.get("history")
    _require(isinstance(history, list) and all(isinstance(item, dict) for item in history), "invalid saved history")
    rows = [row for row in history if row.get("action") == plan_action]
    _require(len(rows) == 1 and rows[0].get("stage") == "plan" and rows[0].get("outcome") == "done"
             and rows[0].get("workitem") is None and record.get("runtime_phase") == "complete",
             "expected Plan lacks one completed Improve acceptance", "unavailable")
    seed = record.get("seed_result")
    _require(isinstance(seed, dict) and seed.get("outcome") == "done",
             "initial Plan result is missing", "unavailable")
    _require(seed_digest(seed) == seed_sha256, "saved initial Plan seed digest differs from expectation")
    return seed, record


def _complete(record: dict[str, Any], action: str) -> bool:
    return (record.get("verb") == "complete" and record.get("action") == action
            and type(record.get("exit")) is int and record["exit"] == 0
            and record.get("status") == "active" and not record.get("held") and not record.get("crashed"))


def _revisions(record: dict[str, Any], before: int, after: int) -> bool:
    pair = record.get("rev")
    return pair == [before, after] and all(type(value) is int for value in pair)


def _transition(rows: list[dict[str, Any]], expected: ExpectedPlan) -> tuple[dict, dict, dict]:
    """Find the original packet, producer command and accepting command by append order."""
    revision = expected.producer_revision
    plan, improve = expected.plan_action, expected.improve_action
    _require(all(type(row["record"].get("v")) is int and row["record"]["v"] == 1
                 and row["record"].get("kind") in ("command", "packet", "hook") for row in rows),
             "unsupported or malformed trace rows", "unavailable")
    commands = [row for row in rows if row["record"]["kind"] == "command"]
    producers = []
    acceptances = []
    for row in commands:
        record = row["record"]
        stages, cursors = record.get("stage"), record.get("cursor")
        if (record.get("verb") in ("improve-start", "improve-bind", "improve-reconcile")
                and (record.get("action") in (plan, improve)
                     or isinstance(cursors, list) and improve in cursors)):
            raise _EvidenceError("unavailable", "trace records restart, rebind or reconciliation of the expected Plan")
        if _complete(record, plan) and stages == ["plan", "improve"] and cursors == [plan, improve]:
            producers.append(row)
        accepted = record.get("accepted", [])
        _require(isinstance(accepted, list) and all(isinstance(item, dict) for item in accepted),
                 "malformed trace acceptance rows")
        if any(item.get("action") == plan for item in accepted):
            acceptances.append(row)
    _require(len(producers) == len(acceptances) == 1, "missing or ambiguous producer/acceptance transitions", "unavailable")
    producer, acceptance = producers[0], acceptances[0]
    pr, ar = producer["record"], acceptance["record"]
    _require(_revisions(pr, revision - 1, revision) and not pr.get("accepted"),
             "producer transition revision or acceptance differs from expectation")
    _require(producer["line"] < acceptance["line"] and _complete(ar, improve)
             and ar.get("stage") == ["improve", "prepare"] and _revisions(ar, revision, revision + 1)
             and isinstance(ar.get("cursor"), list) and len(ar["cursor"]) == 2
             and ar["cursor"][0] == improve and _matches(_ID, ar["cursor"][1])
             and ar["cursor"][1] not in (plan, improve)
             and ar["accepted"] == [{"action": plan, "stage": "plan", "item": None, "outcome": "done"}],
             "no unambiguous Improve-to-Prepare acceptance", "unavailable")
    for row in commands:
        if not producer["line"] < row["line"] < acceptance["line"]:
            continue
        record = row["record"]
        _require(_revisions(record, revision, revision)
                 and record.get("stage") == ["improve", "improve"]
                 and record.get("cursor") == [improve, improve]
                 and not record.get("accepted")
                 and record.get("verb") in ("next", "packet", "note", "improve-pass", "improve-commit", "complete"),
                 "unexplained command or revision within Plan Improve", "unavailable")
    # A command appends after its packet. Hooks can append independently.
    prior = next((row for row in reversed(rows[:producer["line"] - 1]) if row["record"]["kind"] != "hook"), None)
    _require(prior is not None, "producer packet is missing", "unavailable")
    packet = prior["record"]
    _require(packet.get("kind") == "packet" and packet.get("stage") == "improve"
             and packet.get("reviewed") == "plan" and type(packet.get("rev")) is int and packet["rev"] == revision
             and packet.get("action") == improve and packet.get("status") == "active" and packet.get("whole") is True,
             "producer's full Improve packet is missing", "unavailable")
    return prior, producer, acceptance


def _millis_ns(value: Any) -> int:
    _require(type(value) in (int, float) and 0 < value < 100_000_000_000,
             "missing or invalid trace clock", "unavailable")
    return round(value * 1000) * 1_000_000


def _producer_packet(
    root: Path, expected: ExpectedPlan, row: dict[str, Any], record: dict[str, Any],
    producer: dict[str, Any], bindings: dict[str, os.stat_result],
) -> tuple[bytes, str, os.stat_result]:
    packet = row["record"]
    sha = packet.get("sha")
    _require(_matches(re.compile(r"[0-9a-f]{16}"), sha)
             and packet.get("file") == f"packets/sent/{sha}.md", "unsafe or invalid producer packet locator")
    data, metadata = _read_source(root, packet["file"])
    _require(_sha256(data)[:16] == sha, "producer packet hash mismatch")
    text = data.decode("utf-8")
    _require(type(packet.get("chars")) is int and packet["chars"] == len(text), "producer packet length mismatch")
    lines = text.split("\n")
    revision = expected.producer_revision
    skill = record.get("skill")
    _require(isinstance(skill, dict) and _absolute_path(skill.get("skill_card")),
             "accepted Improve skill binding is missing", "unavailable")
    callback_prefix = "2. When the improve skill has completed, run: "
    callbacks = [line[len(callback_prefix):] for line in lines if line.startswith(callback_prefix)]
    _require(lines[0] == f"ShipLoop navigator | improve | revision {revision} | the plan result"
             and f"Keepalive marker: SHIPLOOP-RUN run={expected.run_id} rev={revision} dir={root}" in lines
             and any(line.startswith("1. Run the improve skill on the plan result with this argument,") for line in lines)
             and any(f"otherwise open {skill['skill_card']} and follow it" in line for line in lines)
             and len(callbacks) == 1 and shlex.split(callbacks[0])[-3:]
             == ["complete", f"--run-dir={root}", f"--action={expected.improve_action}"]
             and not any("start it again first:" in line or "bind the Improve skill's SKILL.md" in line for line in lines),
             "producer packet does not establish an automatically bound and started review", "unavailable")

    command = producer["record"]
    duration = command.get("ms")
    _require(type(duration) is int and duration > 0, "producer command has no measured interval", "unavailable")
    end, emitted = _millis_ns(command.get("ts")), _millis_ns(packet.get("ts"))
    start = end - duration * 1_000_000
    # Require the bind to be inside the interval even at the limits of clock rounding.
    _require(start - 1_000_000 <= emitted <= end + 1_000_000,
             "producer packet is outside the producer command interval", "unavailable")
    for name, bound in bindings.items():
        _require(all(start + 1_000_000 <= observed < emitted - 500_000
                     for observed in (bound.st_mtime_ns, bound.st_ctime_ns)),
                 f"{name} metadata does not corroborate producer-time binding", "unavailable")
    return data, packet["file"], metadata


def _git(repo: str, *args: str) -> bytes:
    # Ignore ambient Git path overrides, replacement objects, filters and lazy network fetching.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    try:
        completed = subprocess.run(
            ["git", "--no-replace-objects", "--literal-pathspecs", "-C", repo, *args],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=env, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise _EvidenceError("unavailable", f"Git {args[0]} is unavailable") from exc
    _require(completed.returncode == 0, f"Git {args[0]} could not read the recorded snapshot", "unavailable")
    return completed.stdout


def _declared_locators(seed: dict[str, Any]) -> set[str]:
    # These are the Plan evidence lists whose symbolic roots the producer expands.
    refs = seed.get("evidence_refs", [])
    assumptions = seed.get("assumptions", [])
    _require(isinstance(refs, list) and isinstance(assumptions, list)
             and all(isinstance(row, dict) for row in assumptions), "malformed initial Plan evidence lists")
    locators = set()
    for group in [refs, *(row.get("evidence", []) for row in assumptions)]:
        _require(isinstance(group, list) and all(isinstance(ref, str) and 0 < len(ref) <= _MAX_LOCATOR_CHARS
                                                for ref in group), "malformed declared Plan locators")
        locators.update(group)
        _require(len(locators) <= _MAX_LOCATORS, "too many declared Plan locators", "unsupported")
    return locators


def _locator_path(locator: str, expected: ExpectedPlan, top: str) -> str:
    path = _SUFFIX.sub("", locator)
    _require(not re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", path) and ":" not in path,
             "nonlocal or unsupported artifact locator", "unsupported")
    if path.startswith("/"):
        _require(_absolute_path(path), "unsafe artifact locator", "unsupported")
        prefix = expected.repo + "/"
        _require(path.startswith(prefix), "artifact locator is outside recorded repository scope", "unsupported")
        return path[len(top) + 1:]
    _require(_path_components(path), "unsafe artifact locator", "unsupported")
    return path if expected.repo_prefix == "." else expected.repo_prefix + "/" + path


def _text(data: bytes) -> str:
    _require(not any(byte < 32 and byte not in (9, 10, 13) or byte == 127 for byte in data),
             "artifact contains binary control bytes", "unsupported")
    try:
        return data.decode("utf-8")
    except UnicodeError as exc:
        raise _EvidenceError("unsupported", "artifact is not UTF-8 text") from exc


def _blob_oid(data: bytes, length: int) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    algorithm = "sha1" if length == 40 else "sha256"
    return hashlib.new(algorithm, header + data).hexdigest()


def _entry(top: str, tree: str, path: str) -> tuple[dict[str, Any], bytes]:
    result = _git(top, "ls-tree", "--full-tree", "-z", tree, "--", path)
    _require(bool(result), "declared path is absent from the producer tree", "unavailable")
    header, separator, name = result.partition(b"\t")
    parts = header.split()
    _require(separator and name == path.encode("utf-8") + b"\0" and len(parts) == 3,
             "ambiguous Git path in producer tree", "unavailable")
    mode, kind, blob_bytes = parts
    _require(mode in (b"100644", b"100755") and kind == b"blob",
             "declared artifact is not a regular Git blob", "unsupported")
    blob = blob_bytes.decode("ascii")
    _require(_matches(_OID, blob) and len(blob) == len(tree), "invalid Git blob object identity")
    size = _git(top, "cat-file", "-s", blob).strip()
    _require(size.isdigit(), "invalid Git blob size")
    _require(int(size) <= MAX_BLOB_BYTES, "declared artifact exceeds size bound", "unsupported")
    data = _git(top, "cat-file", "blob", blob)
    _require(len(data) == int(size) and _blob_oid(data, len(blob)) == blob,
             "Git blob bytes do not match object identity", "unavailable")
    _text(data)
    digest = _sha256(data)
    return {"status": "retained", "path": path, "mode": mode.decode("ascii"), "blob": blob,
            "sha256": digest, "size": len(data), "sidecar": f"blobs/{digest}.txt"}, data


def _binding(expected: ExpectedPlan, bind: dict[str, Any], bound_seed: dict[str, Any],
             seed: dict[str, Any]) -> tuple[str, str]:
    top, tree = bind.get("toplevel"), bind.get("tree")
    _require(_absolute_path(top) and _matches(_OID, tree), "bind has no supported Git snapshot", "unavailable")
    _require(bind.get("prefix") == expected.repo_prefix, "recorded Git prefix differs from expectation")
    _require(expected.repo == (top if expected.repo_prefix == "." else f"{top}/{expected.repo_prefix}"),
             "recorded Git scope differs from expected repository")
    _require(bind.get("result") == expected.seed_sha256 and seed_digest(bound_seed) == expected.seed_sha256
             and bound_seed == seed, "bind result does not match the expected canonical seed", "unavailable")
    _require(Path(expected.repo).resolve(strict=True) == Path(expected.repo)
             and _git(expected.repo, "rev-parse", "--show-toplevel").decode("utf-8").rstrip("\n") == top
             and _git(top, "cat-file", "-t", tree).strip() == b"tree",
             "recorded Git scope or tree is unavailable", "unavailable")
    return top, tree


def _capture_files(run: Path, expected: ExpectedPlan) -> dict[str, bytes]:
    state_bytes, state_stat = _read_source(run, "state.md")
    state = _parse_source(state_bytes, "saved state")
    seed, record = _initial_result(state, expected.run_id, expected.plan_action,
                                   expected.improve_action, expected.seed_sha256)
    _require(state.get("repo") == expected.repo and record.get("workspace") == expected.repo,
             "saved repository scope differs from expectation")
    trace_path = run / "trace.jsonl"
    trace_stat = trace_path.lstat()
    trace = planning_trace.read_trace(trace_path)
    _require(trace["status"] == "ok", f"strict trace: {trace['reason']}", "unavailable")
    packet, producer, acceptance = _transition(trace["rows"], expected)
    _require(type(state.get("revision")) is int and state["revision"] >= expected.producer_revision + 1,
             "saved state predates recorded acceptance", "unavailable")

    action = expected.plan_action
    bind_path = f"improve/{action}-bind.md"
    seed_path = f"improve/{action}-bind-result.json"
    bind_bytes, bind_stat = _read_source(run, bind_path)
    seed_bytes, seed_stat = _read_source(run, seed_path)
    bindings = {bind_path: bind_stat, seed_path: seed_stat}
    packet_bytes, packet_path, packet_stat = _producer_packet(run, expected, packet, record, producer, bindings)
    top, tree = _binding(expected, _parse_source(bind_bytes, "bind record"),
                         _parse_source(seed_bytes, "bind result", markdown=False), seed)

    entries = {}
    by_path = {}
    files = {}
    total = 0
    for locator in sorted(_declared_locators(seed)):
        path = None
        try:
            path = _locator_path(locator, expected, top)
            if path in by_path:
                entries[locator] = by_path[path]
                continue
            entry, data = _entry(top, tree, path)
            sidecar = entry["sidecar"]
            if sidecar not in files:
                _require(total + len(data) <= _MAX_SET_BYTES, "artifact set exceeds byte bound", "unsupported")
                files[sidecar] = data
                total += len(data)
        except _EvidenceError as exc:
            if exc.status == "invalid":
                raise
            entry = _result(exc.status, str(exc), path=path)
        entries[locator] = entry
        if path is not None:
            by_path[path] = entry

    sources = {
        "state": _sha256(state_bytes), "trace": trace["sha256"], "producer_packet": _sha256(packet_bytes),
        "bind": _sha256(bind_bytes), "bind_result": _sha256(seed_bytes),
    }
    for relative, before in {"state.md": state_stat, "trace.jsonl": trace_stat, packet_path: packet_stat,
                             **bindings}.items():
        _require(_fingerprint((run / relative).lstat()) == _fingerprint(before),
                 "source evidence changed during collection", "unavailable")
    manifest = {
        "schema": SCHEMA, "receipt_kind": RECEIPT_KIND, "capture_basis": CAPTURE_BASIS,
        "materialized_at": datetime.now(timezone.utc).isoformat(),
        "identity": asdict(expected), "git_toplevel": top, "tree": tree,
        "source_sha256": sources,
        "trace_lines": {"producer_packet": packet["line"], "producer": producer["line"],
                        "acceptance": acceptance["line"]},
        "producer_command": producer["record"], "acceptance_command": acceptance["record"],
        "bind_clock_ns": {"record": [bind_stat.st_mtime_ns, bind_stat.st_ctime_ns],
                          "result": [seed_stat.st_mtime_ns, seed_stat.st_ctime_ns]},
        "initial_result": seed, "entries": entries,
    }
    files[MANIFEST_NAME] = _json_bytes(manifest)
    _require(len(files[MANIFEST_NAME]) <= _MAX_RECORD_BYTES, "manifest exceeds size bound", "unsupported")
    return files


def _entry_bytes(root: Path, entry: dict[str, Any], tree: str) -> bytes:
    digest, blob, size = entry.get("sha256"), entry.get("blob"), entry.get("size")
    _require(_matches(_SHA256, digest) and entry.get("sidecar") == f"blobs/{digest}.txt",
             "unsafe or invalid artifact sidecar")
    _require(_matches(_OID, blob) and len(blob) == len(tree)
             and type(size) is int and 0 <= size <= MAX_BLOB_BYTES
             and entry.get("mode") in ("100644", "100755"), "invalid retained blob identity")
    try:
        data, _ = _read_file(root, entry["sidecar"], MAX_BLOB_BYTES)
    except FileNotFoundError as exc:
        raise _EvidenceError("unavailable", "referenced artifact sidecar is missing") from exc
    except OSError as exc:
        raise _EvidenceError("invalid", "unsafe or unreadable artifact sidecar") from exc
    _require(len(data) == size and _sha256(data) == digest and _blob_oid(data, len(blob)) == blob,
             "artifact bytes do not match the recorded size, digest and Git blob")
    _text(data)
    return data


def _load_bundle(
    root: Path, expected: ExpectedPlan | None = None, manifest_sha256: str | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    try:
        raw, _ = _read_file(root, MANIFEST_NAME, _MAX_RECORD_BYTES)
    except FileNotFoundError as exc:
        raise _EvidenceError("unavailable", "initial Plan artifact manifest is missing") from exc
    except OSError as exc:
        raise _EvidenceError("invalid", "unsafe or unreadable initial Plan artifact manifest") from exc
    if manifest_sha256 is not None:
        _require(_matches(_SHA256, manifest_sha256) and _sha256(raw) == manifest_sha256,
                 "manifest hash differs from the caller's receipt hash")
    manifest = _json_dict(raw.decode("utf-8"))
    _require(isinstance(manifest.get("schema"), str), "manifest schema is missing")
    _require(manifest["schema"] == SCHEMA, "unsupported artifact manifest schema", "unsupported")
    _require(manifest.get("receipt_kind") == RECEIPT_KIND and manifest.get("capture_basis") == CAPTURE_BASIS,
             "invalid artifact receipt kind or capture basis")
    materialized = manifest.get("materialized_at")
    _require(isinstance(materialized, str) and datetime.fromisoformat(materialized).utcoffset() is not None,
             "invalid artifact materialization time")
    identity = manifest.get("identity")
    _require(isinstance(identity, dict) and set(identity) == set(ExpectedPlan.__dataclass_fields__),
             "malformed artifact identity")
    actual = ExpectedPlan(**identity)
    _check_expected(actual)
    if expected is not None:
        _require(actual == expected, "artifact identity differs from expectation")

    top, tree = manifest.get("git_toplevel"), manifest.get("tree")
    _require(_absolute_path(top) and _matches(_OID, tree)
             and actual.repo == (top if actual.repo_prefix == "." else f"{top}/{actual.repo_prefix}"),
             "malformed artifact repository scope or Git tree")
    sources = manifest.get("source_sha256")
    _require(isinstance(sources, dict) and set(sources) == {"state", "trace", "producer_packet", "bind", "bind_result"}
             and all(_matches(_SHA256, value) for value in sources.values()), "malformed source evidence hashes")
    lines = manifest.get("trace_lines")
    _require(isinstance(lines, dict) and set(lines) == {"producer_packet", "producer", "acceptance"}
             and all(type(value) is int for value in lines.values())
             and 0 < lines["producer_packet"] < lines["producer"] < lines["acceptance"],
             "malformed producer and acceptance trace line identities")
    producer, acceptance = manifest.get("producer_command"), manifest.get("acceptance_command")
    revision = actual.producer_revision
    _require(isinstance(producer, dict) and isinstance(acceptance, dict)
             and _complete(producer, actual.plan_action) and _complete(acceptance, actual.improve_action)
             and _revisions(producer, revision - 1, revision)
             and producer.get("cursor") == [actual.plan_action, actual.improve_action]
             and producer.get("stage") == ["plan", "improve"]
             and not producer.get("accepted")
             and _revisions(acceptance, revision, revision + 1)
             and acceptance.get("stage") == ["improve", "prepare"]
             and acceptance.get("accepted") == [{"action": actual.plan_action, "stage": "plan",
                                                "item": None, "outcome": "done"}],
             "malformed producer or acceptance command identity")
    clocks = manifest.get("bind_clock_ns")
    _require(isinstance(clocks, dict) and set(clocks) == {"record", "result"}
             and all(isinstance(pair, list) and len(pair) == 2
                     and all(type(value) is int and value > 0 for value in pair) for pair in clocks.values()),
             "malformed bind source timestamps")
    seed = manifest.get("initial_result")
    _require(isinstance(seed, dict) and seed.get("outcome") == "done" and seed_digest(seed) == actual.seed_sha256,
             "invalid retained initial result or seed digest")
    entries = manifest.get("entries")
    _require(isinstance(entries, dict) and set(entries) == _declared_locators(seed),
             "artifact entries differ from the declared initial result locators")
    files = {MANIFEST_NAME: raw}
    total = 0
    by_path = {}
    for locator, entry in entries.items():
        _require(isinstance(entry, dict), "malformed artifact entry")
        try:
            path = _locator_path(locator, actual, top)
        except _EvidenceError:
            _require(entry.get("status") == "unsupported" and entry.get("path") is None,
                     "unsupported locator claims an artifact path")
            path = None
        _require(entry.get("path") == path, "artifact path differs from declared locator")
        if path is not None:
            _require(path not in by_path or entry == by_path[path], "conflicting entries for one Git path")
            if path in by_path:
                continue
            by_path[path] = entry
        if entry.get("status") in ("unsupported", "unavailable"):
            _require(set(entry) == {"status", "path", "reason"} and isinstance(entry["reason"], str)
                     and entry["reason"], "malformed unavailable artifact entry")
            continue
        _require(entry.get("status") == "retained" and path is not None
                 and set(entry) == {"status", "path", "mode", "blob", "sha256", "size", "sidecar"},
                 "malformed retained artifact entry")
        data = _entry_bytes(root, entry, tree)
        sidecar = entry["sidecar"]
        if sidecar not in files:
            total += len(data)
            _require(total <= _MAX_SET_BYTES, "artifact set exceeds byte bound", "unsupported")
            files[sidecar] = data
    return manifest, files


def _publish(root: Path, files: dict[str, bytes], *, capture_retry: bool = False) -> tuple[str, bool]:
    parent = root.parent.resolve(strict=True)
    root = parent / root.name
    _require(root.name not in ("", ".", ".."), "artifact output needs its own directory")
    # Serialize cooperating writers and publish the complete directory with one rename.
    lock = os.open(parent, _DIR_FLAGS)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.lexists(root):
            manifest, old = _load_bundle(root)
            if capture_retry:
                new = _json_dict(files[MANIFEST_NAME].decode("utf-8"))
                new["materialized_at"] = manifest["materialized_at"]
                files = {**files, MANIFEST_NAME: _json_bytes(new)}
            _require(files == old, "conflicting artifact receipt retry")
            return _sha256(old[MANIFEST_NAME]), True
        with tempfile.TemporaryDirectory(prefix=".planning-evidence-", dir=parent) as temporary:
            bundle = Path(temporary) / "bundle"
            bundle.mkdir(mode=0o700)
            for relative, data in files.items():
                path = bundle / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            bundle.rename(root)
        return _sha256(files[MANIFEST_NAME]), False
    finally:
        os.close(lock)


def _failure(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, _EvidenceError):
        return _result(exc.status, str(exc))
    if isinstance(exc, OSError):
        return _result("unavailable", f"evidence I/O failed: {exc.strerror}")
    return _result("invalid", f"malformed evidence or arguments: {exc}")


def collect_initial_artifacts(run_dir: Path, output_dir: Path, *, expected: ExpectedPlan) -> dict[str, Any]:
    """Materialize one derived receipt; output_dir is a new directory under an existing parent."""
    try:
        _check_expected(expected)
        run = Path(run_dir).resolve(strict=True)
        output = Path(output_dir).absolute()
        destination = output.resolve(strict=False)
        repo = Path(expected.repo)
        if expected.repo_prefix != ".":
            _require(repo.parts[-len(PurePosixPath(expected.repo_prefix).parts):]
                     == PurePosixPath(expected.repo_prefix).parts, "expected repository and prefix disagree")
            repo = repo.parents[len(PurePosixPath(expected.repo_prefix).parts) - 1]
        _require(not destination.is_relative_to(run) and not destination.is_relative_to(repo),
                 "derived artifact output must be separate from the source run and repository")
        files = _capture_files(run, expected)
        digest, reused = _publish(output, files, capture_retry=True)
        return _result("captured", manifest=str(output / MANIFEST_NAME), manifest_sha256=digest, reused=reused)
    except (OSError, ValueError, RecursionError) as exc:
        return _failure(exc)


def _quote_result(quote: str, selected: str, **source: Any) -> dict[str, Any]:
    normalized = " ".join(quote.split())
    _require(bool(normalized), "quote must contain non-whitespace text")
    if normalized in " ".join(selected.split()):
        return _result("matched", **source)
    return _result("not-found", "quote is absent from the selected source", **source)


def verify_linked_quote(bundle_dir: Path, *, expected: ExpectedPlan, manifest_sha256: str,
                        locator: str, quote: str, expected_tree: str | None = None) -> dict[str, Any]:
    """Check one exact declared locator from an independently pinned portable receipt."""
    try:
        _check_expected(expected)
        _require(_matches(_SHA256, manifest_sha256), "expected manifest SHA-256 is required")
        _require(isinstance(locator, str) and 0 < len(locator) <= _MAX_LOCATOR_CHARS, "invalid expected locator")
        _require(isinstance(quote, str) and bool(quote.strip()), "quote must contain non-whitespace text")
        manifest, files = _load_bundle(Path(bundle_dir), expected, manifest_sha256)
        if expected_tree is not None:
            _require(_matches(_OID, expected_tree) and manifest["tree"] == expected_tree,
                     "manifest Git tree differs from expectation")
        entry = manifest["entries"].get(locator)
        if entry is None:
            return _result("unsupported", "locator is not declared by the initial Plan", locator=locator)
        if entry["status"] != "retained":
            return _result(entry["status"], entry["reason"], locator=locator)
        return _quote_result(quote, _text(files[entry["sidecar"]]), locator=locator,
                             path=entry["path"], blob=entry["blob"], tree=manifest["tree"])
    except (OSError, ValueError, RecursionError) as exc:
        return _failure(exc)


def verify_initial_field(
    run_dir: Path, *, run_id: str, plan_action: str, improve_action: str, seed_sha256: str,
    field: str, quote: str, phase: str = "initial",
) -> dict[str, Any]:
    """Check one named top-level string in the saved canonical initial Plan result."""
    try:
        _check_ids(run_id, plan_action, improve_action, seed_sha256, phase)
        _require(isinstance(field, str) and bool(field), "an exact result field name is required")
        _require(isinstance(quote, str) and bool(quote.strip()), "quote must contain non-whitespace text")
        data, _ = _read_source(Path(run_dir).resolve(strict=True), "state.md")
        seed, _ = _initial_result(_parse_source(data, "saved state"), run_id, plan_action, improve_action, seed_sha256)
        # These are the narrative string fields of a completed Plan. Commands,
        # enums, locators and nested objects are separate evidence sources.
        selected = seed.get(field) if field in ("summary", "headline") else None
        if not isinstance(selected, str):
            return _result("unsupported", "selected initial result field is absent or is not a string", field=field)
        selected = _text(selected.encode("utf-8"))
        return _quote_result(quote, selected, field=field)
    except (OSError, ValueError, RecursionError) as exc:
        return _failure(exc)


def copy_artifact_bundle(source_dir: Path, output_dir: Path, *, manifest_sha256: str,
                         reject: Callable[[bytes], bool] | None = None) -> dict[str, Any]:
    """Archive exactly the validated manifest and its referenced content-addressed sidecars."""
    try:
        _require(_matches(_SHA256, manifest_sha256), "expected manifest SHA-256 is required")
        source = Path(source_dir).resolve(strict=True)
        output = Path(output_dir).absolute()
        _require(not output.resolve(strict=False).is_relative_to(source), "archive must be separate from the receipt")
        _, files = _load_bundle(source, manifest_sha256=manifest_sha256)
        if reject is not None:
            _require(not any(reject(data) for data in files.values()),
                     "artifact bundle contains content excluded by the archive policy", "unsupported")
        digest, reused = _publish(output, files)
        return _result("archived", manifest=str(output / MANIFEST_NAME), manifest_sha256=digest, reused=reused)
    except (OSError, ValueError, RecursionError) as exc:
        return _failure(exc)


def _identity_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--plan-action", required=True)
    parser.add_argument("--improve-action", required=True)
    parser.add_argument("--seed-sha256", required=True)
    parser.add_argument("--phase", required=True, help="supported phase: initial")


def _repository_args(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument("--producer-revision", type=int, required=required, help="revision entering Improve")
    parser.add_argument("--repo", required=required, help="recorded absolute repository path")
    parser.add_argument("--repo-prefix", required=required, help="recorded repository path under Git toplevel or '.'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture", help="collect a derived initial Plan artifact receipt")
    _identity_args(capture)
    _repository_args(capture, required=True)
    capture.add_argument("--run-dir", type=Path, required=True)
    capture.add_argument("--output-dir", type=Path, required=True)
    verify = commands.add_parser("verify", help="verify one quote from an initial Plan source")
    _identity_args(verify)
    _repository_args(verify, required=False)
    location = verify.add_mutually_exclusive_group(required=True)
    location.add_argument("--bundle-dir", type=Path)
    location.add_argument("--run-dir", type=Path)
    target = verify.add_mutually_exclusive_group(required=True)
    target.add_argument("--locator")
    target.add_argument("--field")
    verify.add_argument("--manifest-sha256")
    verify.add_argument("--tree", help="independently expected Git tree object ID, when available")
    verify.add_argument("--quote", required=True)

    args = parser.parse_args(argv)
    identity = {name: getattr(args, name) for name in ("run_id", "plan_action", "improve_action", "seed_sha256", "phase")}
    scope = {name: getattr(args, name) for name in ("producer_revision", "repo", "repo_prefix")}
    if args.command == "capture":
        result = collect_initial_artifacts(args.run_dir, args.output_dir, expected=ExpectedPlan(**identity, **scope))
    elif args.bundle_dir is not None:
        if args.locator is None or args.manifest_sha256 is None or any(value is None for value in scope.values()):
            result = _result("invalid", "bundle verification needs locator, manifest SHA-256 and repository identities")
        else:
            result = verify_linked_quote(args.bundle_dir, expected=ExpectedPlan(**identity, **scope),
                                         manifest_sha256=args.manifest_sha256, locator=args.locator, quote=args.quote,
                                         expected_tree=args.tree)
    elif (args.field is None or args.manifest_sha256 is not None or args.tree is not None
          or any(value is not None for value in scope.values())):
        result = _result("invalid", "run verification needs a named field and result identities")
    else:
        result = verify_initial_field(args.run_dir, **identity, field=args.field, quote=args.quote)
    print(json.dumps(result, sort_keys=True))
    return {"captured": 0, "matched": 0, "not-found": 1, "invalid": 2, "unsupported": 3, "unavailable": 4}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
