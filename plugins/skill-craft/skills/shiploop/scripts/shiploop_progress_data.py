#!/usr/bin/env python3
"""Read-only, bounded data projection for the ShipLoop progress observer."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import heapq
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping

import shiploop_chain_ledger as chain_ledger
import shiploop_context_index as context_index
import shiploop_knowledge_home as knowledge_home
import shiploop_navigator as navigator
import shiploop_planning_revision as planning_revision
import shiploop_privacy as privacy
import shiploop_store as store
import shiploop_workspace as workspace


SCHEMA = "shiploop-progress/v1"
_MAX_STATE_BYTES = 4 * 1024 * 1024
_MAX_DOCUMENT_BYTES = 128 * 1024
_MAX_REPORT_BYTES = 1024 * 1024
_MAX_DOCUMENTS = 12
_MAX_ACTIVITIES = 100
_MAX_LEDGER_ENTRIES = 500
_MAX_LEDGER_BYTES = 8 * 1024 * 1024
_MAX_GRAPHS = 12
_MAX_GRAPH_NODES = 100
_MAX_BINDING_BYTES = 1024 * 1024
_MAX_DISPATCHER_BYTES = 4 * 1024 * 1024
_DOCUMENT_NAME = re.compile(r"(?:^|[._-])(spec(?:ification)?|architecture|design|plan)(?:[._-]|$)", re.I)
_ALLOWED_TEXT_SUFFIXES = frozenset((".md", ".txt"))
_ARCHITECTURE_PATHS = (
    "docs/ARCHITECTURE.md",
    "ARCHITECTURE.md",
    "docs/architecture.md",
    "docs/shiploop/architecture.md",
)


class _UnsafeSource(ValueError):
    """An optional source is unsafe, unstable, or outside its read bound."""


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return all(
        getattr(left, name, None) == getattr(right, name, None)
        for name in ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    )


def _directory_fd(path: Path) -> int:
    """Open one trusted base directory without following its final component."""
    target = Path(os.path.abspath(os.fspath(path)))
    try:
        before = os.lstat(target)
    except OSError as exc:
        raise _UnsafeSource("base directory is unavailable") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise _UnsafeSource("base path is not a regular directory")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(os.fspath(target), flags)
    except OSError as exc:
        raise _UnsafeSource("base directory cannot be opened safely") from exc
    after = os.fstat(descriptor)
    if not stat.S_ISDIR(after.st_mode) or not _same_identity(before, after):
        os.close(descriptor)
        raise _UnsafeSource("base directory changed while opening")
    return descriptor


def _relative_parts(relative: str | Path) -> tuple[str, ...]:
    value = os.fspath(relative)
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise _UnsafeSource("unsafe relative path")
    path = Path(value)
    parts = path.parts
    if path.is_absolute() or not parts or any(part in ("", ".", "..") for part in parts):
        raise _UnsafeSource("unsafe relative path")
    return parts


def _parent_fd(base: Path, parts: tuple[str, ...]) -> int:
    descriptor = _directory_fd(base)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        for part in parts:
            try:
                before = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
                if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
                    raise _UnsafeSource("parent component is not a regular directory")
                child = os.open(part, flags, dir_fd=descriptor)
            except FileNotFoundError:
                raise
            except _UnsafeSource:
                raise
            except OSError as exc:
                raise _UnsafeSource("parent component cannot be opened safely") from exc
            after = os.fstat(child)
            if not stat.S_ISDIR(after.st_mode) or not _same_identity(before, after):
                os.close(child)
                raise _UnsafeSource("parent component changed while opening")
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_beneath(base: Path, relative: str | Path, max_bytes: int) -> tuple[bytes, int]:
    """Read one stable, single-link regular file through no-follow dirfds."""
    parts = _relative_parts(relative)
    directory = _parent_fd(base, parts[:-1])
    descriptor = -1
    name = parts[-1]
    try:
        try:
            before = os.stat(name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise _UnsafeSource("file metadata is unavailable") from exc
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise _UnsafeSource("file is not a regular single-link file")
        if before.st_size > max_bytes:
            raise _UnsafeSource("file exceeds its read limit")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            descriptor = os.open(name, flags, dir_fd=directory)
        except OSError as exc:
            raise _UnsafeSource("file cannot be opened safely") from exc
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or not _same_identity(before, opened):
            raise _UnsafeSource("file changed while opening")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise _UnsafeSource("file exceeds its read limit")
        after = os.fstat(descriptor)
        try:
            named_after = os.stat(name, dir_fd=directory, follow_symlinks=False)
        except OSError as exc:
            raise _UnsafeSource("file changed while reading") from exc
        if (not stat.S_ISREG(after.st_mode) or after.st_nlink != 1
                or not _same_identity(opened, after) or not _same_identity(after, named_after)):
            raise _UnsafeSource("file changed while reading")
        return b"".join(chunks), after.st_mtime_ns
    finally:
        if descriptor != -1:
            os.close(descriptor)
        os.close(directory)


def _directory_exists_beneath(base: Path, relative: str | Path) -> bool:
    parts = _relative_parts(relative)
    descriptor = _directory_fd(base)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        for part in parts:
            try:
                before = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                return False
            if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
                raise _UnsafeSource("directory component is unsafe")
            try:
                child = os.open(part, flags, dir_fd=descriptor)
            except OSError as exc:
                raise _UnsafeSource("directory component cannot be opened safely") from exc
            after = os.fstat(child)
            if not _same_identity(before, after):
                os.close(child)
                raise _UnsafeSource("directory component changed while opening")
            os.close(descriptor)
            descriptor = child
        return True
    finally:
        os.close(descriptor)


def _mtime_text(stamp_ns: int | None) -> str | None:
    if stamp_ns is None:
        return None
    return datetime.fromtimestamp(stamp_ns / 1_000_000_000, timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _display_text(value: Any) -> str:
    return privacy.redact_text(value) if isinstance(value, str) else ""


def _summary(text: str, limit: int = 280) -> str:
    line = " ".join(text.split())
    if privacy.sensitive_text(line):
        return "Credential-like text withheld."
    return line if len(line) <= limit else line[: limit - 1] + "…"


def _uri(path: Path) -> str:
    return Path(os.path.abspath(os.fspath(path))).as_uri()


def _doc_placeholder(
    *, doc_id: str, title: str, path: Path, observed_at: str,
    status: str, error: str, acceptance: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": doc_id, "title": title, "path": str(path), "uri": _uri(path),
        "content": "", "summary": error, "sha256": None, "observed_at": observed_at,
        "status": status, "error": error,
    }
    if acceptance:
        result["acceptance"] = acceptance
    return result


def _read_document(
    *, base: Path, relative: str, doc_id: str, title: str, observed_at: str,
    warnings: list[str], mtimes: list[int], expected_record: Mapping[str, Any] | None = None,
    public_record: Mapping[str, Any] | None = None, acceptance: str | None = None,
    max_bytes: int = _MAX_DOCUMENT_BYTES,
) -> tuple[dict[str, Any], dict[str, str] | None]:
    path = base / relative
    try:
        raw, mtime_ns = _read_beneath(base, relative, max_bytes)
    except FileNotFoundError:
        warnings.append(f"Document missing: {doc_id}.")
        return _doc_placeholder(doc_id=doc_id, title=title, path=path, observed_at=observed_at,
                                status="missing", error="File is missing.", acceptance=acceptance), None
    except _UnsafeSource as exc:
        error = str(exc)
        warnings.append(f"Document withheld: {doc_id} ({error}).")
        return _doc_placeholder(doc_id=doc_id, title=title, path=path, observed_at=observed_at,
                                status="withheld", error=error, acceptance=acceptance), None
    except OSError:
        error = "File could not be read safely."
        warnings.append(f"Document withheld: {doc_id} (read failed).")
        return _doc_placeholder(doc_id=doc_id, title=title, path=path, observed_at=observed_at,
                                status="withheld", error=error, acceptance=acceptance), None
    mtimes.append(mtime_ns)
    digest = _sha(raw)
    try:
        content = raw.decode("utf-8")
    except UnicodeError:
        warnings.append(f"Document withheld: {doc_id} (invalid UTF-8).")
        return _doc_placeholder(doc_id=doc_id, title=title, path=path, observed_at=observed_at,
                                status="withheld", error="File is not valid UTF-8.",
                                acceptance=acceptance), {"id": doc_id, "path": str(path), "sha256": digest}
    if privacy.sensitive_text(content):
        error = "Credential-like content withheld."
        warnings.append(f"Document withheld: {doc_id} (credential screen matched).")
        document = _doc_placeholder(doc_id=doc_id, title=title, path=path, observed_at=observed_at,
                                    status="withheld", error=error, acceptance=acceptance)
        document["sha256"] = digest
        return document, {"id": doc_id, "path": str(path), "sha256": digest}
    if expected_record is not None:
        try:
            record = store.loads(content)
        except store.StorageError:
            record = None
        if record != dict(expected_record):
            error = "Record does not match the accepted navigator state."
            warnings.append(f"Document withheld: {doc_id} (record does not match state).")
            document = _doc_placeholder(doc_id=doc_id, title=title, path=path, observed_at=observed_at,
                                        status="withheld", error=error, acceptance=acceptance)
            document["sha256"] = digest
            return document, {"id": doc_id, "path": str(path), "sha256": digest}
        status = "accepted-result"
        summary = _summary(str(expected_record.get("result", {}).get("summary", "")))
        if public_record is not None:
            content = store.dumps(dict(public_record), "ShipLoop navigator result")
    else:
        status = "draft"
        summary = _summary(content)
    document = {
        "id": doc_id, "title": title, "path": str(path), "uri": _uri(path),
        "content": content, "summary": summary, "sha256": digest,
        "observed_at": observed_at, "status": status,
    }
    if acceptance:
        document["acceptance"] = acceptance
    return document, {"id": doc_id, "path": str(path), "sha256": digest}


def _evidence_path(reference: str, repo: Path, run_root: Path) -> tuple[Path, str] | None:
    if not isinstance(reference, str) or privacy.sensitive_text(reference):
        return None
    candidate = Path(reference)
    if not candidate.is_absolute():
        return None
    absolute = Path(os.path.abspath(os.fspath(candidate)))
    for base in (repo, run_root):
        try:
            relative = absolute.relative_to(Path(os.path.abspath(os.fspath(base))))
        except ValueError:
            continue
        if (relative.parts and all(part not in ("", ".", "..") for part in relative.parts)
                and absolute.suffix.lower() in _ALLOWED_TEXT_SUFFIXES
                and _DOCUMENT_NAME.search(absolute.stem)):
            return base, relative.as_posix()
        return None
    return None


def _public_result_record(record: Mapping[str, Any], repo: Path, run_root: Path) -> dict[str, Any]:
    """Hide evidence locators that are outside the two explicitly bound roots."""
    public = json.loads(json.dumps(record, ensure_ascii=False))
    result = public.get("result")
    refs = result.get("evidence_refs") if isinstance(result, dict) else None
    if isinstance(refs, list):
        safe_refs = []
        for ref in refs:
            try:
                local = (isinstance(ref, str) and bool(ref) and "\x00" not in ref
                         and Path(ref).is_absolute() and not privacy.sensitive_text(ref)
                         and any(_within(Path(os.path.abspath(ref)), Path(os.path.abspath(base)))
                                 for base in (repo, run_root)))
            except (OSError, TypeError, ValueError):
                local = False
            safe_refs.append(ref if local else "[external or unsafe evidence reference omitted]")
        result["evidence_refs"] = safe_refs
    return public


def _within(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _decode_timeline(root: Path, warnings: list[str], mtimes: list[int]) -> dict[str, Any]:
    try:
        raw, mtime_ns = _read_beneath(root, "timeline.json", 1024 * 1024)
        value = json.loads(raw.decode("utf-8"))
        if (not isinstance(value, dict) or not isinstance(value.get("accepted", {}), dict)
                or not isinstance(value.get("started"), str)):
            raise ValueError("invalid timeline shape")
        mtimes.append(mtime_ns)
        return value
    except FileNotFoundError:
        return {}
    except (UnicodeError, ValueError, _UnsafeSource):
        warnings.append("Timeline is missing usable timestamps.")
        return {}


def _safe_summary(value: Any) -> str:
    text = " ".join(value.split()) if isinstance(value, str) else ""
    if privacy.sensitive_text(text):
        return "Credential-like event content withheld."
    return text[:280] + ("…" if len(text) > 280 else "")


def _activity(state: Mapping[str, Any], root: Path, timeline: Mapping[str, Any],
              warnings: list[str], mtimes: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    parent_fingerprint: list[dict[str, Any]] = []
    accepted = state.get("accepted", {})
    history = state.get("history", [])
    work_by_action = {entry.get("action"): entry.get("workitem") for entry in history
                      if isinstance(entry, Mapping)}
    current_action = navigator.current_action(state)
    current_id = current_action.get("id") if isinstance(current_action, Mapping) else None
    if current_id and current_action.get("stage") == "implement":
        work_by_action[current_id] = state["work_items"][state["work_index"]]["id"]
    timestamps = timeline.get("accepted", {}) if isinstance(timeline.get("accepted"), Mapping) else {}
    for seq, entry in enumerate(history, 1):
        action_id = entry["action"]
        result = accepted.get(action_id, {})
        summary = _safe_summary(result.get("headline") or result.get("summary") or entry.get("summary"))
        stamp = timestamps.get(action_id)
        rows.append({"stream": "navigator", "seq": seq,
                     "time": stamp if isinstance(stamp, str) else None,
                     "stage": entry["stage"], "workitem": entry.get("workitem"),
                     "outcome": result.get("outcome", entry.get("outcome")), "summary": summary})
        parent_fingerprint.append({"stream": "navigator", "seq": seq,
                                   "stage": entry["stage"], "workitem": entry.get("workitem"),
                                   "outcome": result.get("outcome", entry.get("outcome")),
                                   "summary": summary})

    chain_fingerprint: list[dict[str, Any]] = []
    chain_actions = [entry["action"] for entry in history if entry.get("stage") == "implement"]
    if current_id and current_action.get("stage") == "implement":
        chain_actions.append(current_id)
    bindings = state.get("chain_bindings", {})
    for action_id in dict.fromkeys(chain_actions):
        if action_id not in bindings:
            continue
        relative = f"chains/{action_id}/events"
        try:
            if not _directory_exists_beneath(root, relative):
                continue
            directory = root / relative
            names = os.listdir(directory)
            if len(names) > _MAX_LEDGER_ENTRIES:
                warnings.append(f"Chain activity withheld for {action_id} (ledger entry bound exceeded).")
                continue
            total_size = 0
            for name in names:
                try:
                    metadata = os.lstat(directory / name)
                except OSError:
                    raise _UnsafeSource("ledger entry is unstable")
                if stat.S_ISREG(metadata.st_mode):
                    total_size += metadata.st_size
                    if metadata.st_nlink != 1:
                        raise _UnsafeSource("ledger entry has an unsafe link count")
            if total_size > _MAX_LEDGER_BYTES:
                warnings.append(f"Chain activity withheld for {action_id} (ledger byte bound exceeded).")
                continue
            events = chain_ledger.read_events(directory)
            for event_row in events:
                event = event_row["event"]
                data = event.get("data", {})
                message = next((data.get(key) for key in ("summary", "headline", "outcome", "status", "reason")
                                if isinstance(data, Mapping) and isinstance(data.get(key), str)), "")
                kind = event.get("kind", "event")
                summary = _safe_summary(message) or str(kind).replace("_", " ")
                event_seq = event.get("seq")
                rows.append({"stream": "chain:" + action_id, "seq": event_seq,
                             "time": event.get("occurred_at") or event.get("recorded_at"),
                             "stage": "implement", "workitem": work_by_action.get(action_id),
                             "outcome": kind, "summary": summary})
                chain_fingerprint.append({"stream": "chain:" + action_id, "seq": event_seq,
                                          "stage": "implement", "workitem": work_by_action.get(action_id),
                                          "outcome": kind, "summary": summary,
                                          "sha256": event_row.get("sha256")})
                event_path = Path(event_row.get("path", ""))
                try:
                    event_relative = event_path.relative_to(root)
                    _, mtime_ns = _read_beneath(root, event_relative, 256 * 1024)
                    mtimes.append(mtime_ns)
                except (ValueError, OSError, _UnsafeSource):
                    warnings.append(f"Chain activity timestamp unavailable for {action_id}.")
        except (OSError, ValueError, _UnsafeSource) as exc:
            warnings.append(f"Chain activity unavailable for {action_id} ({type(exc).__name__}).")
    # Sequence is authoritative within each stream; wall-clock timestamps may
    # be absent or skewed, so they must not reorder a stream's records.
    streams: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(rows, key=lambda row: (row["stream"], row["seq"])):
        streams.setdefault(row["stream"], []).append(row)
    pending = [(str(items[0].get("time") or ""), stream, 0)
               for stream, items in streams.items()]
    heapq.heapify(pending)
    rows = []
    while pending:
        _, stream, index = heapq.heappop(pending)
        rows.append(streams[stream][index])
        index += 1
        if index < len(streams[stream]):
            heapq.heappush(pending, (str(streams[stream][index].get("time") or ""), stream, index))
    if len(rows) > _MAX_ACTIVITIES:
        rows = rows[-_MAX_ACTIVITIES:]
        warnings.append("Activity is limited to the latest 100 recorded items.")
    return rows, [{"parent": parent_fingerprint, "chains": chain_fingerprint}]


def _valid_bound_graph(graph: Any) -> list[dict[str, Any]]:
    if not isinstance(graph, Mapping) or graph.get("version") != 1:
        raise ValueError("invalid bound graph")
    raw_steps = graph.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps or len(raw_steps) > _MAX_GRAPH_NODES:
        raise ValueError("invalid bound graph size")
    ids: set[str] = set()
    steps: list[dict[str, Any]] = []
    for row in raw_steps:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            raise ValueError("invalid bound graph step")
        step_id = row["id"]
        deps = row.get("deps")
        contract = row.get("contract")
        if (not step_id or len(step_id) > 200 or any(ord(ch) < 32 for ch in step_id)
                or step_id in ids or not isinstance(deps, list)
                or not all(isinstance(dep, str) and dep for dep in deps)
                or len(set(deps)) != len(deps)):
            raise ValueError("invalid bound graph step")
        if contract is not None and (not isinstance(contract, Mapping)
                                     or not isinstance(contract.get("task"), str)):
            raise ValueError("invalid bound graph contract")
        ids.add(step_id)
        steps.append({"id": step_id, "deps": list(deps), "contract": contract})
    if any(dep not in ids for row in steps for dep in row["deps"]):
        raise ValueError("bound graph dependency is missing")
    return steps


def _implementation_graphs(
    state: Mapping[str, Any], root: Path, current: Mapping[tuple[str | None, str], str],
    warnings: list[str], mtimes: list[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Project accepted step plans and bound chain graphs without running helpers."""
    graphs: list[dict[str, Any]] = []
    identities: list[dict[str, Any]] = []
    bound_workitems: set[str] = set()
    history = state.get("history", [])
    positions = {row.get("action"): index for index, row in enumerate(history)
                 if isinstance(row, Mapping)}
    # A revised plan retires its old execution graphs. Prefer the newest bound
    # action when the display bound cannot retain the whole current plan history.
    action_workitem = {}
    for index, row in reversed(list(enumerate(history))):
        if not isinstance(row, Mapping) or row.get("stage") != "implement":
            continue
        plan_action = current.get((row.get("workitem"), "step-plan"))
        if plan_action and index > positions.get(plan_action, -1):
            action_workitem.setdefault(row.get("action"), row.get("workitem"))
    active_action = navigator.current_action(state)
    if isinstance(active_action, Mapping) and active_action.get("stage") == "implement":
        action_workitem = {active_action.get("id"): state["work_items"][state["work_index"]]["id"],
                           **action_workitem}

    bindings = state.get("chain_bindings", {})
    if not isinstance(bindings, Mapping):
        bindings = {}
        warnings.append("Chain graph bindings are malformed; bound graphs are unavailable.")
    for action_id in dict.fromkeys(action_workitem):
        if not isinstance(action_id, str) or action_id not in bindings:
            continue
        if len(graphs) >= _MAX_GRAPHS:
            warnings.append("Additional implementation graphs were omitted at the graph bound.")
            break
        workitem = action_workitem.get(action_id)
        label = f"Bound implementation graph ({workitem or 'work item unknown'} · {action_id})"
        identity: dict[str, Any] = {"action": action_id, "binding_sha256": None,
                                    "dispatcher_sha256": None, "binding_status": "unavailable"}
        try:
            raw, binding_mtime = _read_beneath(root, f"chains/{action_id}/binding.md", _MAX_BINDING_BYTES)
            mtimes.append(binding_mtime)
            binding_digest = _sha(raw)
            identity["binding_sha256"] = binding_digest
            saved_digest = bindings.get(action_id)
            if (not isinstance(saved_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", saved_digest)
                    or binding_digest != saved_digest):
                raise ValueError("binding digest does not match navigator state")
            binding = store.loads(raw.decode("utf-8"))
            if (not isinstance(binding, Mapping)
                    or binding.get("schema") != "shiploop-chain-binding/v6"
                    or binding.get("run_id") != state.get("run_id")
                    or binding.get("action_id") != action_id
                    or not isinstance(binding.get("root"), str)
                    or Path(os.path.abspath(binding["root"])) != root):
                raise ValueError("binding scope does not match navigator state")
            dispatcher_root = root / "chains" / action_id / "dispatcher"
            dispatcher_text = binding.get("dispatcher_run")
            if (not isinstance(dispatcher_text, str)
                    or Path(os.path.abspath(dispatcher_text)) != dispatcher_root):
                raise ValueError("dispatcher scope does not match bound run")
            raw_graph = binding.get("graph")
            steps = _valid_bound_graph(raw_graph)
            identity["binding_status"] = "verified"
            statuses = {row["id"]: "unknown" for row in steps}
            try:
                if os.path.lexists(dispatcher_root / "state.json"):
                    raise ValueError("legacy dispatcher state is present")
                dispatcher_raw, dispatcher_mtime = _read_beneath(
                    root, f"chains/{action_id}/dispatcher/plan-dispatcher-state.json",
                    _MAX_DISPATCHER_BYTES)
                mtimes.append(dispatcher_mtime)
                dispatcher_digest = _sha(dispatcher_raw)
                identity["dispatcher_sha256"] = dispatcher_digest
                child = json.loads(dispatcher_raw.decode("utf-8"))
                child_graph = child.get("graph") if isinstance(child, Mapping) else None
                child_steps = child.get("steps") if isinstance(child, Mapping) else None
                graph_sha = child.get("graph_sha256") if isinstance(child, Mapping) else None
                step_ids = {row["id"] for row in steps}
                valid_statuses = {"pending", "claimed", "launching", "running",
                                  "rejected", "blocked", "accepted"}
                if (isinstance(child, Mapping) and child.get("version") in (1, 2)
                        and child.get("owner") == binding.get("owner")
                        and isinstance(child.get("run_id"), str) and child.get("run_id")
                        and child_graph == raw_graph
                        and isinstance(graph_sha, str) and re.fullmatch(r"[0-9a-f]{64}", graph_sha)
                        # A nonmatching canonical digest (including unsupported
                        # JS/Python number formatting) withholds status only.
                        # It is never compared with the raw graph-source file hash.
                        and graph_sha == _sha(_canonical(raw_graph))
                        and isinstance(child_steps, Mapping)
                        and set(child_steps) == step_ids
                        and all(isinstance(child_steps[step_id], Mapping)
                                and child_steps[step_id].get("status") in valid_statuses
                                for step_id in step_ids)):
                    statuses = {step_id: child_steps[step_id]["status"] for step_id in step_ids}
                    identity["dispatcher_status"] = "verified"
                else:
                    identity["dispatcher_status"] = "unverified"
                    warnings.append(f"Dispatcher progress withheld for {action_id} (graph identity or state mismatch).")
            except FileNotFoundError:
                identity["dispatcher_status"] = "missing"
                warnings.append(f"Dispatcher state is not yet available for {action_id}; bound steps have unknown status.")
            except (UnicodeError, ValueError, _UnsafeSource, OSError):
                identity["dispatcher_status"] = "unavailable"
                warnings.append(f"Dispatcher progress withheld for {action_id} (state is unreadable).")
            graphs.append({"id": action_id, "label": label, "status": "accepted",
                           "dependencies_known": True,
                           "nodes": [{"id": row["id"],
                                      "title": _display_text(
                                          row["contract"].get("task", row["id"])
                                          if isinstance(row.get("contract"), Mapping) else row["id"]),
                                      "status": statuses.get(row["id"], "unknown"), "plan": ""}
                                     for row in steps],
                           "edges": [{"from": dep, "to": row["id"]}
                                     for row in steps for dep in row["deps"]]})
            if isinstance(workitem, str):
                bound_workitems.add(workitem)
        except FileNotFoundError:
            identity["binding_status"] = "missing"
            warnings.append(f"Bound implementation graph is missing for {action_id}.")
            graphs.append({"id": action_id, "label": label, "status": "unavailable",
                           "dependencies_known": False, "nodes": [], "edges": [],
                           "reason": "Binding file is missing."})
        except (UnicodeError, ValueError, store.StorageError, _UnsafeSource, OSError):
            identity["binding_status"] = "unavailable"
            warnings.append(f"Bound implementation graph is unavailable for {action_id}.")
            graphs.append({"id": action_id, "label": label, "status": "unavailable",
                           "dependencies_known": False, "nodes": [], "edges": [],
                           "reason": "Binding could not be verified."})
        identities.append(identity)

    for item in state.get("work_items", []):
        item_id = item.get("id") if isinstance(item, Mapping) else None
        if not isinstance(item_id, str) or item_id in bound_workitems:
            continue
        action_id = current.get((item_id, "step-plan"))
        accepted = state.get("accepted", {}).get(action_id) if action_id else None
        accepted_steps = accepted.get("steps") if isinstance(accepted, Mapping) else None
        if not isinstance(accepted_steps, list) or not accepted_steps:
            continue
        if len(graphs) >= _MAX_GRAPHS:
            warnings.append("Additional implementation graphs were omitted at the graph bound.")
            break
        try:
            done, steps = navigator.implement_progress(state, item_id)
            if len(steps) > _MAX_GRAPH_NODES:
                warnings.append(f"Implementation plan {item_id} is limited to its first {_MAX_GRAPH_NODES} steps.")
            steps = steps[:_MAX_GRAPH_NODES]
            step_summary = accepted.get("summary", "")
            is_current = (navigator.current_stage(state) == "implement"
                          and state["work_index"] < len(state["work_items"])
                          and state["work_items"][state["work_index"]]["id"] == item_id)
            nodes = []
            for index, step in enumerate(steps):
                status = ("done" if index < done else "active" if is_current and index == done else "queued") \
                    if state.get("delegation") == "inline" else "unknown"
                nodes.append({"id": step["id"], "title": _display_text(step["task"]),
                              "status": status, "plan": _display_text(step_summary)})
            graphs.append({"id": action_id or item_id,
                           "label": f"Accepted implementation plan ({item_id})",
                           "status": "accepted", "dependencies_known": all("deps" in step for step in steps),
                           "nodes": nodes, "edges": [{"from": dep, "to": step["id"]}
                                                     for step in steps for dep in step.get("deps", [])]})
            identities.append({"step_plan_action": action_id, "nodes": steps, "accepted": True})
        except (KeyError, TypeError, ValueError):
            warnings.append(f"Accepted step plan could not be projected for {item_id}.")
    return graphs, identities


def _receipt_identity(root: Path, state: Mapping[str, Any], warnings: list[str]) -> dict[str, Any] | None:
    if state.get("execution_mode") != "navigator-worktree":
        return None
    workspace_root = root.parent
    try:
        if root.name != "run" or not _read_beneath(workspace_root, workspace.MANIFEST, 512 * 1024):
            warnings.append("Terminal workspace return receipt is missing; source delivery is unverified.")
            return {"status": "missing"}
        receipt = workspace.completed_receipt_snapshot(workspace_root, Path(state["repo"]))
        if receipt is None:
            warnings.append("Terminal workspace return receipt is missing or stale; source delivery is unverified.")
            return {"status": "unverified"}
        return {"status": "verified", "sha256": _sha(_canonical(receipt))}
    except (OSError, ValueError, workspace.WorkspaceError, _UnsafeSource):
        warnings.append("Terminal workspace return receipt is unreadable or stale; source delivery is unverified.")
        return {"status": "unverified"}


def build_snapshot(root: Path) -> dict[str, Any]:
    """Return a credential-screened snapshot without changing run or repository state."""
    run_root = Path(os.path.abspath(os.fspath(root)))
    observed_at = _now()
    warnings: list[str] = []
    mtimes: list[int] = []

    try:
        state_raw, state_mtime = _read_beneath(run_root, "state.md", _MAX_STATE_BYTES)
    except (_UnsafeSource, FileNotFoundError) as exc:
        raise ValueError("authoritative state.md is missing or unsafe") from exc
    except OSError:
        raise
    mtimes.append(state_mtime)
    try:
        state = store.loads(state_raw.decode("utf-8"))
    except (UnicodeError, store.StorageError) as exc:
        raise ValueError("authoritative state.md is malformed") from exc
    try:
        navigator.validate(state)
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError("authoritative state.md is malformed") from exc
    if not isinstance(state, Mapping):  # validate normally rejects this first.
        raise ValueError("authoritative state.md is not an object")

    current = planning_revision.current_actions(state)
    plan_action = current.get((None, "plan"))
    plan_accepted = isinstance(plan_action, str) and plan_action in state.get("accepted", {})
    stage = navigator.current_stage(state)
    action = navigator.current_action(state)
    workitem = None
    if stage in navigator.graph(state)[1] and state["work_index"] < len(state["work_items"]):
        workitem = state["work_items"][state["work_index"]]["id"]
    if state.get("active_improve"):
        owner = "Improve" + (f" ({workitem})" if workitem else "")
    elif workitem:
        owner = str(state.get("delegation", "inline")) + f" ({workitem})"
    else:
        owner = "ShipLoop"

    timeline = _decode_timeline(run_root, warnings, mtimes)
    docs: list[dict[str, Any]] = []
    doc_identity: list[dict[str, str]] = []

    repo = Path(os.path.abspath(os.fspath(state["repo"])))
    feature = knowledge_home.feature_dir(state)
    fixed_docs = (
        ("living-spec", "Living specification", "docs/shiploop/spec.md"),
        ("feature-spec", "Feature specification draft", f"{feature}/spec.md"),
        ("feature-plan", "Feature plan draft", f"{feature}/plan.md"),
        ("feature-test-spec", "Feature test specification draft", f"{feature}/test-spec.md"),
        ("test-strategy", "Test strategy", "docs/shiploop/test-strategy.md"),
    )
    candidates: list[tuple[str, str, Path, str, Mapping[str, Any] | None,
                           Mapping[str, Any] | None, str | None]] = []
    for doc_id, title, relative in fixed_docs:
        candidates.append((doc_id, title, repo, relative, None, None, None))

    for result_stage in ("spec", "plan"):
        result_action = current.get((None, result_stage))
        if not isinstance(result_action, str):
            continue
        result_payload = state["accepted"].get(result_action)
        if not isinstance(result_payload, Mapping):
            continue
        history_entry = next((entry for entry in state["history"]
                              if entry.get("action") == result_action), {})
        expected = {
            "navigator_protocol_version": state["navigator_protocol_version"],
            "run_id": state["run_id"], "action": result_action,
            "stage": result_stage, "workitem": history_entry.get("workitem"),
            "result": result_payload,
        }
        public_record = _public_result_record(expected, repo, run_root)
        acceptance = f"Current accepted navigator {result_stage} result ({result_action})."
        candidates.append((f"accepted-{result_stage}-result", f"Accepted {result_stage} result",
                           run_root, f"results/{result_action}.md", expected, public_record, acceptance))

    effective_action = action.get("id") if isinstance(action, Mapping) else None
    if isinstance(effective_action, str):
        pass_path = context_index.pass_log_path(run_root, effective_action)
        candidates.append(("current-action-notes", "Current action pass log (draft)", run_root,
                           pass_path.relative_to(run_root).as_posix(), None, None, None))
    architecture_candidates = []
    for index, relative in enumerate(_ARCHITECTURE_PATHS, 1):
        if os.path.lexists(repo / relative):
            architecture_candidates.append((f"architecture-{index}", "Architecture candidate",
                                            repo, relative, None, None, None))
    candidates.extend(architecture_candidates or [
        ("architecture-candidate", "Architecture candidate", repo, _ARCHITECTURE_PATHS[0], None, None, None)
    ])

    evidence_candidates: list[tuple[str, str, Path, str, Mapping[str, Any] | None,
                                    Mapping[str, Any] | None, str | None]] = []
    for action_id in current.values():
        result = state.get("accepted", {}).get(action_id, {})
        refs = result.get("evidence_refs", []) if isinstance(result, Mapping) else []
        if not isinstance(refs, list):
            continue
        for reference in refs:
            selected = _evidence_path(reference, repo, run_root)
            if selected is None:
                if isinstance(reference, str) and Path(reference).is_absolute() and _DOCUMENT_NAME.search(
                        Path(reference).stem) and Path(reference).suffix.lower() in _ALLOWED_TEXT_SUFFIXES:
                    warnings.append("An accepted evidence reference outside the repository/run root was ignored.")
                continue
            base, relative = selected
            key_path = str(base / relative)
            if any(str(row[2] / row[3]) == key_path for row in candidates + evidence_candidates):
                continue
            doc_id = "evidence-" + _sha(key_path.encode("utf-8"))[:12]
            evidence_candidates.append((doc_id, "Registered planning evidence", base, relative,
                                        None, None, None))
    candidates.extend(evidence_candidates)

    for doc_id, title, base, relative, expected, public_record, acceptance in candidates:
        if len(docs) >= _MAX_DOCUMENTS:
            warnings.append("Additional document candidates were omitted at the 12-document bound.")
            break
        document, identity = _read_document(base=base, relative=relative, doc_id=doc_id, title=title,
                                            observed_at=observed_at, warnings=warnings, mtimes=mtimes,
                                            expected_record=expected, public_record=public_record,
                                            acceptance=acceptance,
                                            max_bytes=_MAX_DOCUMENT_BYTES)
        docs.append(document)
        doc_identity.append(identity or {"id": document["id"], "path": document["path"],
                                         "status": document["status"], "error": document.get("error")})

    activity, activity_identity = _activity(state, run_root, timeline, warnings, mtimes)
    facts = navigator.narrative_facts(state)
    facts = _redact_tree(facts)
    try:
        status_block = navigator.status_block(state)
    except Exception as exc:
        raise ValueError("navigator status projection failed") from exc
    if privacy.sensitive_text(status_block):
        status_block = "Status details withheld because credential-like text was found."
        warnings.append("Status text was withheld by the credential screen.")

    terminal = state["status"] in ("done", "halted")
    terminal_report = None
    report_identity: dict[str, Any] | None = None
    if terminal:
        try:
            report_raw, report_mtime = _read_beneath(run_root, "report.html", _MAX_REPORT_BYTES)
            mtimes.append(report_mtime)
            terminal_report = _uri(run_root / "report.html")
            report_identity = {"path": str(run_root / "report.html"), "sha256": _sha(report_raw)}
        except FileNotFoundError:
            warnings.append("Terminal report is missing.")
        except _UnsafeSource as exc:
            warnings.append(f"Terminal report is withheld ({str(exc)}).")
    receipt_identity = _receipt_identity(run_root, state, warnings) if terminal else None

    prompt = _display_text(state.get("prompt"))
    reason = _display_text(state.get("status_reason")) if state.get("status_reason") else None
    items: list[dict[str, Any]] = []
    for index, item in enumerate(state["work_items"]):
        item_id = item["id"]
        if index < state["work_index"] or state["status"] == "done":
            item_status = "done"
        elif index == state["work_index"]:
            item_status = "current"
        else:
            item_status = "queued"
        step_action = current.get((item_id, "step-plan"))
        step_plan = state["accepted"].get(step_action, {}) if step_action else {}
        plan_text = step_plan.get("summary") if isinstance(step_plan, Mapping) else None
        if not isinstance(plan_text, str) or not plan_text.strip():
            plan_text = item.get("context", "")
        items.append({"id": item_id, "title": _display_text(item.get("title")),
                      "status": item_status, "plan": _display_text(plan_text), "dependencies": []})

    graphs, graph_identity = _implementation_graphs(state, run_root, current, warnings, mtimes)

    source_changed_at = _mtime_text(max(mtimes) if mtimes else None)
    state_digest = _sha(state_raw)
    fingerprint_value = {
        "schema": SCHEMA,
        "run": {"id": state["run_id"], "revision": state["revision"],
                "status": state["status"], "stage": stage, "owner": owner,
                "reason": reason, "prompt": prompt},
        "state_sha256": state_digest,
        "plan_accepted": plan_accepted,
        "documents": doc_identity,
        "activity": activity_identity,
        "graphs": graph_identity,
        "terminal_report": report_identity,
        "workspace_return": receipt_identity,
    }
    snapshot = {
        "schema": SCHEMA,
        "observed_at": observed_at,
        "source_changed_at": source_changed_at,
        "run": {"id": state["run_id"], "prompt": prompt, "revision": state["revision"],
                "status": state["status"], "stage": stage, "owner": owner, "reason": reason},
        "facts": facts,
        "status_block": status_block,
        "plan_accepted": plan_accepted,
        "work_items": items,
        "graphs": graphs,
        "documents": docs,
        "activity": activity,
        "warnings": list(dict.fromkeys(warnings)),
        "terminal_ready": terminal,
        "source_fingerprint": _sha(_canonical(fingerprint_value)),
    }
    if terminal_report:
        snapshot["terminal_report"] = terminal_report
    return snapshot


def _redact_tree(value: Any) -> Any:
    if isinstance(value, str):
        return privacy.redact_text(value)
    if isinstance(value, list):
        return [_redact_tree(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_tree(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _redact_tree(item) for key, item in value.items()}
    return value


__all__ = ["SCHEMA", "build_snapshot"]
