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
from typing import Any, Mapping

import shiploop_context_index as context_index
import shiploop_knowledge_home as knowledge_home
import shiploop_navigator as navigator
import shiploop_planning_revision as planning_revision
import shiploop_privacy as privacy
import shiploop_store as store
import shiploop_workspace as workspace


SCHEMA = "shiploop-progress/v1"
# Guards and display bounds of the read-only progress view: the bytes it reads from each file and the rows it draws.
# It warns where it cuts and never refuses a run's records.
_MAX_STATE_BYTES = 4 * 1024 * 1024
_MAX_DOCUMENT_BYTES = 128 * 1024
_MAX_REPORT_BYTES = 1024 * 1024
_MAX_DOCUMENTS = 12
_MAX_ACTIVITIES = 100
_MAX_GRAPHS = 12
_MAX_GRAPH_NODES = 100
_DOCUMENT_NAME = re.compile(r"(?:^|[._-])(spec(?:ification)?|architecture|design|plan)(?:[._-]|$)", re.I)
_ALLOWED_TEXT_SUFFIXES = frozenset((".md", ".txt"))
_ARCHITECTURE_PATHS = (
    "docs/ARCHITECTURE.md",
    "ARCHITECTURE.md",
    "docs/architecture.md",
    "docs/shiploop/architecture.md",
)


from shiploop_observation_io import _UnsafeSource, _read_beneath, _relative_parts, _same_identity, _directory_fd, _parent_fd

def _mtime_text(stamp_ns: int | None) -> str | None:
    if stamp_ns is None:
        return None
    return datetime.fromtimestamp(stamp_ns / 1_000_000_000, timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sha256_hex(raw: bytes) -> str:
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


def _file_uri(path: Path) -> str:
    return Path(os.path.abspath(os.fspath(path))).as_uri()


def _doc_placeholder(
    *, doc_id: str, title: str, path: Path, observed_at: str,
    status: str, error: str, acceptance: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": doc_id, "title": title, "path": str(path), "uri": _file_uri(path),
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
    max_bytes: int = _MAX_DOCUMENT_BYTES, captures=None, previous=None,
) -> tuple[dict[str, Any], dict[str, str] | None]:
    """Read one run document safely beneath ``base``; returns its display record and a fingerprint entry, or a
    placeholder (missing or withheld) with a warning.
    """
    path = base / relative
    try:
        if captures is None:
            raw, mtime_ns = _read_beneath(base, relative, max_bytes)
        else:
            from shiploop_observation_io import capture
            key = "document:" + str(path)
            value = capture(base, relative, max_bytes, observed_at, (previous or {}).get(key))
            value["source"].update(id=key, path=str(path))
            captures[key] = value
            status = value["source"]["status"]
            if status == "missing":
                raise FileNotFoundError(relative)
            if status not in ("ok", "stale"):
                raise _UnsafeSource(value["source"]["message"])
            raw, mtime_ns = value["raw"], value.get("mtime_ns")
            observed_at = value["source"]["observed_at"]
            if status == "stale":
                warnings.append(f"Document stale: {doc_id}; retained its last successful read.")
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
    if mtime_ns is not None:
        mtimes.append(mtime_ns)
    digest = _sha256_hex(raw)
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
            record = store.observation_json(store.loads(content))
        except (store.StorageError, ValueError, RecursionError):
            record = None
            if captures is not None:
                captures["document:" + str(path)]["source"].update(
                    status="partial", message="Malformed optional structured document; accepted state remains authoritative.")
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
        "id": doc_id, "title": title, "path": str(path), "uri": _file_uri(path),
        "content": content, "summary": summary, "sha256": digest,
        "observed_at": observed_at, "status": status,
    }
    if captures is not None:
        document["freshness"] = captures["document:" + str(path)]["source"]["status"]
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
    import shiploop_story as story_data
    try:
        raw, mtime_ns = _read_beneath(root, "timeline.json", 1024 * 1024)
        value = store.observation_json(json.loads(raw.decode("utf-8")))
        value, malformed = story_data.normalise_timeline(value)
        mtimes.append(mtime_ns)
        if malformed:
            warnings.append("Timeline has malformed timestamps; unknown timestamps withheld.")
            value["_display_malformed"] = True
        return value
    except FileNotFoundError:
        return {}
    except (UnicodeError, ValueError, _UnsafeSource, RecursionError):
        warnings.append("Timeline is missing usable timestamps.")
        return {"started": None, "accepted": {}, "_display_malformed": True}


def _safe_summary(value: Any) -> str:
    text = " ".join(value.split()) if isinstance(value, str) else ""
    if privacy.sensitive_text(text):
        return "Credential-like event content withheld."
    return text[:280] + ("…" if len(text) > 280 else "")


def _activity(state: Mapping[str, Any], root: Path, timeline: Mapping[str, Any],
              warnings: list[str], mtimes: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the timeline rows of accepted activity for the run, plus the fingerprints that
    detect change; warnings note withheld data.
    """
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
    return rows, [{"parent": parent_fingerprint}]


def _implementation_graphs(
    state: Mapping[str, Any], root: Path, current: Mapping[tuple[str | None, str], str],
    warnings: list[str], mtimes: list[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Project accepted step plans without running helpers."""
    graphs: list[dict[str, Any]] = []
    identities: list[dict[str, Any]] = []

    for item in state.get("work_items", []):
        item_id = item.get("id") if isinstance(item, Mapping) else None
        if not isinstance(item_id, str):
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
                status = "done" if index < done else "active" if is_current and index == done else "queued"
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
        return {"status": "verified", "sha256": _sha256_hex(_canonical(receipt))}
    except (OSError, ValueError, workspace.WorkspaceError, _UnsafeSource):
        warnings.append("Terminal workspace return receipt is unreadable or stale; source delivery is unverified.")
        return {"status": "unverified"}


class Snapshot(dict):
    """Public JSON-compatible snapshot with observer-only capture handles."""


def build_snapshot(root: Path, *, core=None, optional_cache=None) -> dict[str, Any]:
    """Return a credential-screened snapshot without changing run or repository state."""
    run_root = Path(os.path.abspath(os.fspath(root)))
    observed_at = core["observed_at"] if core else _now()
    warnings: list[str] = []
    mtimes: list[int] = []

    try:
        state_raw, state_mtime = (core["state_raw"], core["state_mtime"]) if core else _read_beneath(run_root, "state.md", _MAX_STATE_BYTES)
    except (_UnsafeSource, FileNotFoundError) as exc:
        raise ValueError("authoritative state.md is missing or unsafe") from exc
    except OSError:
        raise
    mtimes.append(state_mtime)
    try:
        state = store.loads(state_raw.decode("utf-8"))
    except (UnicodeError, store.StorageError, RecursionError) as exc:
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

    if core:
        import shiploop_story as story_data
        _, timeline = story_data.core_values(core)
    else:
        timeline = _decode_timeline(run_root, warnings, mtimes)
    document_captures = {}
    docs: list[dict[str, Any]] = []
    doc_identity: list[dict[str, str]] = []

    repo = Path(os.path.abspath(os.fspath(state["repo"])))
    # The living spec; the run's other records are result fields (consumer contract 6.2), shown by the report.
    fixed_docs = (
        ("living-spec", "Living specification", knowledge_home.HOME + "/spec.md"),
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
            doc_id = "evidence-" + _sha256_hex(key_path.encode("utf-8"))[:12]
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
                                            max_bytes=_MAX_DOCUMENT_BYTES, captures=document_captures, previous=optional_cache)
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
            terminal_report = _file_uri(run_root / "report.html")
            report_identity = {"path": str(run_root / "report.html"), "sha256": _sha256_hex(report_raw)}
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
    display_status, display_label = navigator.display_status(state)
    inflight = inflight_activity(run_root, state, timeline=timeline)

    source_changed_at = _mtime_text(max(mtimes) if mtimes else None)
    state_digest = _sha256_hex(state_raw)
    fingerprint_value = {
        "schema": SCHEMA,
        "run": {"id": state["run_id"], "revision": state["revision"],
                "status": state["status"], "display_status": display_status,
                "stage": stage, "owner": owner,
                "reason": reason, "prompt": prompt},
        "state_sha256": state_digest,
        "plan_accepted": plan_accepted,
        "documents": doc_identity,
        "activity": activity_identity,
        "graphs": graph_identity,
        "inflight": inflight,
        "terminal_report": report_identity,
        "workspace_return": receipt_identity,
    }
    snapshot = {
        "schema": SCHEMA,
        "observed_at": observed_at,
        "source_changed_at": source_changed_at,
        "run": {"id": state["run_id"], "prompt": prompt, "revision": state["revision"],
                "status": state["status"], "display_status": display_status,
                "display_label": display_label, "stage": stage, "owner": owner,
                "reason": reason, "inflight": inflight},
        "facts": facts,
        "status_block": status_block,
        "plan_accepted": plan_accepted,
        "work_items": items,
        "graphs": graphs,
        "documents": docs,
        "activity": activity,
        "warnings": list(dict.fromkeys(warnings)),
        "terminal_ready": terminal,
        "source_fingerprint": _sha256_hex(_canonical(fingerprint_value)),
    }
    if terminal_report:
        snapshot["terminal_report"] = terminal_report
    import shiploop_story as story_data
    story, captures = story_data.build(run_root, state, timeline, previous=optional_cache, observed_at=observed_at, core=core, captured=document_captures)
    snapshot["story"] = story
    snapshot["activity_fingerprint"] = _sha256_hex(_canonical([_redact_tree(state), story["activity_fingerprint"], inflight]))
    snapshot["source_fingerprint"] = _sha256_hex(_canonical([snapshot["source_fingerprint"], story["content_fingerprint"]]))
    from shiploop_observation_io import screen
    snapshot = Snapshot(screen(snapshot))
    # Internal capture handles are stripped by publish and never serialized.
    snapshot.core = core or {"state_raw": state_raw, "state_mtime": state_mtime,
                                 "timeline_raw": json.dumps(timeline).encode(), "observed_at": observed_at}
    snapshot.captures = captures
    return snapshot


def _trace_tail_at(run_root: Path) -> str | None:
    """Best-effort timestamp of the newest complete line in ``trace.jsonl`` without reading the whole file."""
    path = run_root / "trace.jsonl"
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if info.st_nlink != 1:
                return None
            size = info.st_size
            if size <= 0:
                return None
            offset = max(0, size - 16_384)
            handle.seek(offset)
            chunk = handle.read(16_384)
            if offset > 0:
                _, _, chunk = chunk.partition(b"\n")
            for raw_line in reversed(chunk.splitlines()):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line.decode("utf-8"))
                except (UnicodeError, ValueError):
                    continue
                if isinstance(row, Mapping) and isinstance(row.get("at"), str):
                    return row["at"]
    except OSError:
        return None
    return None


def inflight_activity(run_root: Path, state: Mapping[str, Any], *, timeline: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Read-only summary of live in-flight work between navigator transitions."""
    import shiploop_owner_notes as owner_notes

    stage, action, workitem = navigator._active_cursor(state)
    action_id = action.get("id") if isinstance(action, Mapping) else None
    child = state.get("active_improve")
    step_id: str | None = None
    step_number = 0
    step_total = 0
    if workitem and stage in ("implement", "test", "document"):
        view = navigator.step_view(state, workitem)
        if view is not None:
            step_id = str(view.step.get("id") or f"S{view.number}")
            step_number = int(view.number)
            step_total = len(view.steps)

    loop_iteration = 0
    loop_status = ""
    improve_active = isinstance(child, Mapping)
    improve_stage = str(child.get("stage") or "") if improve_active else ""
    improve_review_mode = ""
    improve_passes = 0
    if improve_active:
        if state.get("delegation") == "agents" and improve_stage:
            improve_review_mode = navigator.default_review_mode(state, improve_stage)
        elif state.get("delegation"):
            improve_review_mode = str(state["delegation"])
        if child.get("skill"):
            try:
                import shiploop_standalone_improve as standalone
                receipt_path = standalone.receipt_path(child)
                if not receipt_path.is_symlink() and receipt_path.is_file():
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                    if isinstance(receipt, Mapping):
                        loop_iteration = int((receipt.get("progress") or {}).get("action_number") or 0)
                        loop_status = str(receipt.get("status") or "")
                child_dir = receipt_path.parent
                if child_dir.is_dir() and not child_dir.is_symlink():
                    improve_passes = sum(
                        1 for item in child_dir.iterdir()
                        if item.name.startswith("review-") and item.name.endswith(".md") and not item.is_symlink()
                    )
            except (OSError, ValueError, TypeError):
                pass
    elif isinstance(action_id, str) and action_id:
        try:
            raw, _ = _read_beneath(run_root, f"loops/{action_id}-terminal.json", 512 * 1024)
            receipt = json.loads(raw.decode("utf-8"))
            if isinstance(receipt, Mapping):
                loop_iteration = int((receipt.get("progress") or {}).get("action_number") or 0)
                loop_status = str(receipt.get("status") or "")
        except (FileNotFoundError, OSError, UnicodeError, ValueError, TypeError, _UnsafeSource):
            pass

    last_check_yes: bool | None = None
    last_check_at: str | None = None
    if isinstance(action_id, str) and action_id and not improve_active:
        try:
            raw, _ = _read_beneath(run_root, f"checks/{action_id}.md", 256 * 1024)
            record = store.loads(raw.decode("utf-8"))
            if isinstance(record, Mapping):
                if isinstance(record.get("yes"), bool):
                    last_check_yes = record["yes"]
                if isinstance(record.get("created_at"), str):
                    last_check_at = record["created_at"]
        except (FileNotFoundError, OSError, UnicodeError, ValueError, store.StorageError, _UnsafeSource):
            pass

    open_notes = 0
    carried_notes = 0
    try:
        found_notes = owner_notes.notes(run_root)
        if found_notes:
            ledger = owner_notes.ledger(state)
            for note in found_notes:
                status_word = owner_notes.standing(ledger.get(note["id"], ()))
                if status_word == "open":
                    open_notes += 1
                elif status_word == "carried":
                    carried_notes += 1
    except (OSError, ValueError, TypeError, owner_notes.NoteError):
        pass

    callback_attempts = 0
    try:
        raw, _ = _read_beneath(run_root, "callback-attempts", 128)
        callback_attempts = int(raw.decode("utf-8").strip() or 0)
    except (FileNotFoundError, OSError, UnicodeError, ValueError, _UnsafeSource):
        pass

    last_event_at = _trace_tail_at(run_root)
    if not last_event_at and isinstance(timeline, Mapping):
        accepted = timeline.get("accepted")
        if isinstance(accepted, Mapping) and accepted:
            stamps = [v for v in accepted.values() if isinstance(v, str)]
            last_event_at = max(stamps) if stamps else None
        if not last_event_at and isinstance(timeline.get("started"), str):
            last_event_at = timeline["started"]

    return {
        "step_id": step_id,
        "step_number": step_number,
        "step_total": step_total,
        "loop_iteration": loop_iteration,
        "loop_status": loop_status,
        "improve_active": improve_active,
        "improve_stage": improve_stage,
        "improve_review_mode": improve_review_mode,
        "improve_passes": improve_passes,
        "last_check_yes": last_check_yes,
        "last_check_at": last_check_at,
        "open_notes": open_notes,
        "carried_notes": carried_notes,
        "callback_attempts": callback_attempts,
        "last_event_at": last_event_at,
    }


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


__all__ = ["SCHEMA", "build_snapshot", "inflight_activity"]
