#!/usr/bin/env python3
"""Read-only planning-context collection for ShipLoop chain binding.

The navigator's accepted ledger is the authority for this inventory.  The
collector deliberately does not guess legacy planning paths, scan a project,
or write a run file.  Instead it returns a manifest plus the exact text files
that a caller may publish atomically after its own capability preflight.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import shiploop_navigator as navigator
import shiploop_store as store
import shiploop_planning_revision as planning_revision


SCHEMA = "shiploop-planning-artifacts/v1"
PROJECTION_SCHEMA = "shiploop-planning-projection/v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_CURRENT = "current"
_OTHER_ITEM = "other-item"
_HISTORY = "history"
_CLASSIFICATION_RANK = {_HISTORY: 0, _OTHER_ITEM: 1, _CURRENT: 2}

# These are the stages whose accepted summaries form the planning-only briefing.
# Collection still inventories every accepted result record and every declared
# evidence reference, so an older item's retained context is never discarded.
_PLANNING_STAGES = frozenset(
    (
        "intake",
        "discovery",
        "research",
        "spec",
        "test-strategy",
        "plan",
        "prepare",
        "select-work",
        "step-plan",
        "test-spec",
        "baseline",
        "test-author",
        "test-red",
        "test-refine",
        "regression",
        "document",
        "skill-assess",
        "skill-validate",
        "static-checks",
        "verify",
        "integration-verify",
        "carry-forward",
        "system-test-author",
        "system-test",
        "product-acceptance",
        "release-plan",
        "release-check",
        "release",
        "release-verify",
        "operations",
        "handoff",
    )
)


class PlanningContextError(ValueError):
    """Raised when a planning-context input cannot be safely collected."""


def _fail(message: str) -> None:
    raise PlanningContextError(message)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(label + " must be nonempty text")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_text(value: Any, label: str) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        _fail(label + " is not JSON serializable: " + str(exc))
    raise AssertionError("unreachable")


def _absolute_root(value: Path) -> Path:
    if not isinstance(value, Path) or not value.is_absolute():
        _fail("run root must be an absolute Path")
    try:
        root = value.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        _fail("run root cannot be resolved: " + str(exc))
    if not root.is_dir():
        _fail("run root must be a directory")
    return root


def _absolute_regular_file(value: Any, label: str) -> tuple[Path, bytes]:
    if not isinstance(value, str) or not value:
        _fail(label + " must be a nonempty absolute path")
    try:
        source = Path(value)
    except TypeError as exc:
        _fail(label + " must be a filesystem path: " + str(exc))
    if not source.is_absolute():
        _fail(label + " must be an absolute path")
    try:
        resolved = source.resolve(strict=True)
        info = resolved.stat()
        if not stat.S_ISREG(info.st_mode):
            _fail(label + " must be a regular file")
        return resolved, resolved.read_bytes()
    except PlanningContextError:
        raise
    except (OSError, RuntimeError) as exc:
        _fail("cannot read " + label + ": " + str(exc))
    raise AssertionError("unreachable")


def _run_regular_file(root: Path, relative: str, label: str) -> tuple[Path, bytes]:
    candidate = root / relative
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
        info = resolved.stat()
        if not stat.S_ISREG(info.st_mode):
            _fail(label + " must be a regular run file")
        return resolved, resolved.read_bytes()
    except PlanningContextError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        _fail("cannot read " + label + ": " + str(exc))
    raise AssertionError("unreachable")


def _live_run_dependency_reason(root: Path, path: Path) -> str | None:
    """Reject mutable navigator/dispatcher control files as planning inputs."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    parts = relative.parts
    name = path.name.lower()
    if relative == Path("state.md"):
        return "state.md must be projected as planning-only material, not bound directly"
    if parts and parts[0] == "inbox":
        return "navigator inbox material is mutable and cannot be a planning dependency"
    if name in {"state.json", "status.json", "status.md", "plan-dispatcher-state.json", "report.html"}:
        return "run-local status or dispatcher state cannot be a planning dependency"
    if len(parts) >= 3 and parts[0] == "chains" and parts[2] == "events":
        return "chain event history cannot be a planning dependency"
    return None


def _require_stable_dependency(root: Path, path: Path, label: str) -> None:
    reason = _live_run_dependency_reason(root, path)
    if reason is not None:
        _fail(label + ": " + reason)


def _graph_step_ids(graph: Any) -> tuple[str, ...]:
    if not isinstance(graph, dict) or not isinstance(graph.get("steps"), list):
        _fail("graph must contain a steps list")
    ids: list[str] = []
    for row in graph["steps"]:
        if not isinstance(row, Mapping):
            _fail("graph step must be an object")
        step_id = row.get("id")
        if not isinstance(step_id, str) or not step_id:
            _fail("graph step ID must be nonempty text")
        if step_id in ids:
            _fail("graph contains duplicate step ID: " + step_id)
        ids.append(step_id)
    if not ids:
        _fail("graph must contain at least one step")
    return tuple(ids)


def _graph_source(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"path", "sha256"}:
        _fail("graph_source must contain exactly path and sha256")
    path = value.get("path")
    digest = value.get("sha256")
    if not isinstance(path, str) or not Path(path).is_absolute():
        _fail("graph_source.path must be absolute")
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        _fail("graph_source.sha256 must be a lowercase SHA-256 digest")
    return {"path": path, "sha256": digest}


def _required_for(value: Any, graph_ids: tuple[str, ...], label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _fail(label + " must be a list of step IDs")
    if len(set(value)) != len(value):
        _fail(label + " must not contain duplicate step IDs")
    if "*" in value:
        if value != ["*"]:
            _fail(label + " must be exactly ['*'] when shared")
        return ["*"]
    unknown = [item for item in value if item not in graph_ids]
    if unknown:
        _fail(label + " names unknown graph step IDs: " + ", ".join(unknown))
    return [item for item in graph_ids if item in value]


def _merged_required_for(left: list[str], right: list[str], graph_ids: tuple[str, ...]) -> list[str]:
    if left == ["*"] or right == ["*"]:
        return ["*"]
    return [item for item in graph_ids if item in set(left) | set(right)]


def _current_workitem(state: Mapping[str, Any]) -> str:
    try:
        item = state["work_items"][state["work_index"]]
        value = item["id"]
    except (KeyError, IndexError, TypeError) as exc:
        _fail("navigator has no current work item: " + str(exc))
    if not isinstance(value, str) or not value:
        _fail("navigator current work item is invalid")
    return value


def _entry_classifications(state: Mapping[str, Any], current_workitem: str) -> dict[str, str]:
    """Separate active planning from other-item and superseded history entries."""
    latest_done = planning_revision.current_actions(state)

    output: dict[str, str] = {}
    for entry in state["history"]:
        action = entry["action"]
        workitem = entry["workitem"]
        if workitem not in (None, current_workitem):
            output[action] = _OTHER_ITEM if entry["outcome"] == "done" else _HISTORY
        elif (entry["stage"] in _PLANNING_STAGES and entry["outcome"] == "done"
              and latest_done.get((workitem, entry["stage"])) == action):
            output[action] = _CURRENT
        else:
            output[action] = _HISTORY
    return output


def _default_required_for(classification: str) -> list[str]:
    return ["*"] if classification == _CURRENT else []


def _resolution_map(
    value: Any,
    state: Mapping[str, Any],
    classifications: Mapping[str, str],
    graph_ids: tuple[str, ...],
) -> dict[tuple[str, int], dict[str, Any]]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or set(value) != {"references"}:
        _fail("resolutions must contain exactly references")
    rows = value.get("references")
    if not isinstance(rows, list):
        _fail("resolutions.references must be a list")
    accepted = state["accepted"]
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, Mapping):
            _fail("resolution must be an object")
        action = raw.get("action")
        index = raw.get("index")
        kind = raw.get("kind")
        if not isinstance(action, str) or action not in accepted:
            _fail("resolution action must name an accepted action")
        if type(index) is not int or index < 0 or index >= len(accepted[action]["evidence_refs"]):
            _fail("resolution index must name an accepted evidence_refs entry")
        if kind not in {"file", "url", "statement"}:
            _fail("resolution kind must be file, url, or statement")
        key = (action, index)
        if key in output:
            _fail("duplicate resolution for " + action + " evidence_refs[" + str(index) + "]")
        allowed = {"action", "index", "kind", "required_for", "rationale"}
        if kind == "file":
            allowed |= {"path", "snapshot"}
        else:
            allowed.add("value")
        if set(raw) - allowed:
            _fail("resolution has unsupported fields")
        if kind == "file":
            if not isinstance(raw.get("path"), str) or not Path(raw["path"]).is_absolute():
                _fail("file resolution path must be absolute")
            if "snapshot" in raw and type(raw["snapshot"]) is not bool:
                _fail("file resolution snapshot must be boolean")
        else:
            _text(raw.get("value"), "reference-only resolution value")
            if kind == "statement" and "rationale" not in raw:
                _fail("statement resolution requires rationale")
        if "rationale" in raw:
            _text(raw["rationale"], "resolution rationale")
        source_text = accepted[action]["evidence_refs"][index]
        if kind in {"url", "statement"}:
            if "rationale" not in raw:
                _fail("reference-only resolution requires rationale")
            if _apparent_local_file_reference(source_text):
                _fail("an apparent local file reference cannot be relabeled as reference-only")
            required = _required_for(
                raw.get("required_for", []), graph_ids, "reference-only resolution required_for"
            )
            if required:
                _fail("reference-only resolution must be catalog-only")
        else:
            required = _required_for(
                raw.get("required_for", _default_required_for(classifications[action])),
                graph_ids,
                "resolution required_for",
            )
            if classifications[action] == _CURRENT and not required:
                _fail("a current file reference cannot be downgraded to catalog-only")
        normalized = dict(raw)
        normalized["required_for"] = required
        output[key] = normalized
    return output


def _local_reference(text: str) -> tuple[str, Path | None]:
    """Classify an explicit raw reference without a cwd or legacy-path fallback."""
    if text.startswith("file://"):
        parsed = urlsplit(text)
        if parsed.netloc not in ("", "localhost") or parsed.query:
            return "unresolved", None
        candidate = Path(unquote(parsed.path))
        return ("file", candidate) if candidate.is_absolute() else ("unresolved", None)
    if _URI_SCHEME.match(text):
        return "url", None
    try:
        exact = Path(text)
    except (TypeError, ValueError):
        return "unresolved", None
    if not exact.is_absolute():
        return "unresolved", None
    if exact.exists() or exact.is_symlink():
        return "file", exact
    if "#" in text:
        candidate = Path(text.split("#", 1)[0])
        if candidate.is_absolute():
            return "file", candidate
    return "file", exact


def _apparent_local_file_reference(text: str) -> bool:
    """Keep a missing pathname from being waived as a free-text statement."""
    kind, _candidate = _local_reference(text)
    if kind == "file":
        return True
    if _URI_SCHEME.match(text):
        return False
    return text.startswith(("./", "../")) or "/" in text or bool(Path(text).suffix)


def _strip_statuses(value: Any) -> Any:
    """Retain planning evidence while excluding runtime status fields recursively."""
    if isinstance(value, Mapping):
        return {
            str(key): _strip_statuses(item)
            for key, item in value.items()
            if key not in {"status", "status_reason"}
        }
    if isinstance(value, list):
        return [_strip_statuses(item) for item in value]
    return deepcopy(value)


def _improve_summary(record: Any) -> dict[str, Any]:
    projected = _improve_projection(record)
    receipt = projected.get("receipt")
    return dict(receipt) if isinstance(receipt, Mapping) else {}


def _improve_projection(record: Any) -> dict[str, Any]:
    """Project only accepted Improve planning evidence, never child runtime state."""
    if not isinstance(record, Mapping):
        return {}
    raw_receipt = record.get("receipt", record)
    output: dict[str, Any] = {}
    if isinstance(raw_receipt, Mapping):
        receipt = {
            key: _strip_statuses(raw_receipt[key])
            for key in ("summary", "lessons", "review_refs", "check_refs", "final_result")
            if key in raw_receipt
        }
        if receipt:
            output["receipt"] = receipt
    evidence = record.get("evidence")
    if isinstance(evidence, list):
        rows: list[dict[str, str]] = []
        for item in evidence:
            if not isinstance(item, Mapping):
                continue
            if all(isinstance(item.get(key), str) and item[key] for key in ("source", "archive", "sha256")):
                rows.append({key: item[key] for key in ("source", "archive", "sha256")})
        if rows:
            output["evidence"] = rows
    return output


def _fence(value: str) -> str:
    runs = re.findall(r"`+", value)
    marker = "`" * max(3, 1 + max((len(run) for run in runs), default=0))
    return marker + "text\n" + value + ("" if value.endswith("\n") else "\n") + marker


def _briefing(
    root: Path,
    state: Mapping[str, Any],
    source: Mapping[str, Any],
    current_workitem: str,
    classifications: Mapping[str, str],
) -> str:
    current_item = next(item for item in state["work_items"] if item["id"] == current_workitem)
    lines = [
        "# Planning reference statements",
        "",
        "This is deterministic reference material from accepted navigator planning output.",
        "The assigned graph step contract is the sole task prompt. These reference statements do not redefine or expand it.",
        "It contains planner-authored material only; it does not carry runtime cursor or worker status.",
        "",
        "## Source identity",
        "",
        "- Run: " + source["run_id"],
        "- Bind action: " + source["action_id"],
        "- Work item: " + current_workitem,
        "- Planning capture revision: " + str(source["revision"]),
        "",
        "## Work-item context reference",
        "",
        "- Title: " + current_item["title"],
        "- This context is reference material only; it does not add to the graph step contract.",
    ]
    if "context" in current_item:
        lines.extend(["", _fence(current_item["context"])])
    lines.extend(["", "## Bound-plan reference", ""])
    if state["bound_plan"]:
        lines.append(_fence(state["bound_plan"]))
    else:
        lines.append("No bound-plan value was recorded.")
    lines.extend(["", "## Accepted planning reference statements", ""])

    count = 0
    for entry in state["history"]:
        if entry["stage"] not in _PLANNING_STAGES:
            continue
        count += 1
        action = entry["action"]
        result = state["accepted"][action]
        lines.extend(
            [
                "### " + entry["stage"] + " — " + action,
                "",
                "- Source action: " + action,
                "- Accepted result record: " + str(root / "results" / (action + ".md")),
                "- Classification: " + classifications[action],
                "- Outcome: " + entry["outcome"],
                "- Work item: " + (entry["workitem"] or "run-wide"),
                "",
                "Planner-authored statement:",
                "",
                _fence(result["summary"]),
                "",
                "Recorded evidence references:",
            ]
        )
        refs = result["evidence_refs"]
        if refs:
            lines.extend("- " + reference for reference in refs)
        else:
            lines.append("- none")
        if "choices" in result:
            lines.extend(["", "Recorded choices:", "", _fence(_json_text(result["choices"], "accepted choices"))])
        if "work_items" in result:
            lines.extend([
                "", "Recorded planning work items:", "",
                _fence(_json_text(result["work_items"], "accepted work_items")),
            ])
        improve = _improve_summary(state["improve_results"].get(action))
        if improve:
            lines.extend(["", "Accepted Improve material:"])
            for key in ("summary", "lessons"):
                value = improve.get(key)
                if isinstance(value, str) and value:
                    lines.extend(["", key.replace("_", " ").title() + ":", "", _fence(value)])
            for key in ("review_refs", "check_refs"):
                value = improve.get(key)
                if isinstance(value, list):
                    lines.append(key.replace("_", " ").title() + ":")
                    lines.extend("- " + str(item) for item in value)
        lines.append("")
    if not count:
        lines.append("No accepted planning records were found.")
    return "\n".join(lines).rstrip() + "\n"


class _Artifacts:
    """Deduplicate canonical paths while retaining all source roles and refs."""

    def __init__(self, graph_ids: tuple[str, ...]):
        self._graph_ids = graph_ids
        self._rows: dict[str, dict[str, Any]] = {}

    def add(
        self,
        path: Path,
        data: bytes,
        *,
        role: str,
        producer: str,
        classification: str,
        required_for: list[str],
        reference: dict[str, Any] | None = None,
        origin: dict[str, str] | None = None,
        source_reference: str | None = None,
    ) -> None:
        key = str(path)
        digest = _sha256(data)
        if classification not in _CLASSIFICATION_RANK:
            _fail("unsupported artifact classification")
        current = self._rows.get(key)
        if current is None:
            current = {
                "path": key,
                "sha256": digest,
                "roles": set(),
                "producers": set(),
                "classification": classification,
                "required_for": list(required_for),
                "references": [],
                "origin": origin,
                "source_reference": source_reference,
            }
            self._rows[key] = current
        elif current["sha256"] != digest:
            _fail("same canonical artifact path changed during collection: " + key)
        else:
            if _CLASSIFICATION_RANK[classification] > _CLASSIFICATION_RANK[current["classification"]]:
                current["classification"] = classification
            current["required_for"] = _merged_required_for(
                current["required_for"], required_for, self._graph_ids
            )
            if origin is not None:
                if current["origin"] is not None and current["origin"] != origin:
                    _fail("artifact has conflicting snapshot origins: " + key)
                current["origin"] = origin
            if source_reference is not None:
                if (current["source_reference"] is not None
                        and current["source_reference"] != source_reference):
                    _fail("artifact has conflicting Improve source references: " + key)
                current["source_reference"] = source_reference
        current["roles"].add(role)
        current["producers"].add(producer)
        if reference is not None and reference not in current["references"]:
            current["references"].append(reference)

    def rows(self) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for path in sorted(self._rows):
            source = self._rows[path]
            row = {
                "path": source["path"],
                "sha256": source["sha256"],
                "roles": sorted(source["roles"]),
                "producers": sorted(source["producers"]),
                "classification": source["classification"],
                "required_for": source["required_for"],
            }
            if source["references"]:
                row["references"] = sorted(
                    source["references"], key=lambda item: (item["action"], item["index"], item["text"])
                )
            if source["origin"] is not None:
                row["origin"] = source["origin"]
            if source["source_reference"] is not None:
                row["source_reference"] = source["source_reference"]
            output.append(row)
        return output


def _diagnostic(
    kind: str,
    reason: str,
    required_for: list[str],
    *,
    action: str | None = None,
    index: int | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {"kind": kind, "reason": reason, "required_for": list(required_for)}
    if action is not None:
        output["action"] = action
    if index is not None:
        output["index"] = index
    if text is not None:
        output["text"] = text
    return output


def _add_missing(
    rows: list[dict[str, Any]],
    diagnostic: dict[str, Any],
) -> None:
    if diagnostic["required_for"] and diagnostic not in rows:
        rows.append(diagnostic)


def _snapshot_relative(bind_action: str, source_action: str, index: int, digest: str, source: Path) -> str:
    suffix = source.suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,16}", source.suffix) else ".txt"
    return ("chains/" + bind_action + "/planning-snapshots/" + source_action + "-"
            + str(index) + "-" + digest[:16] + suffix)


def _real_improve_record(record: Any, binding_id: str) -> bool:
    """Recognize the durable standalone-Improve import shape without guessing."""
    return (
        isinstance(record, Mapping)
        and type(record.get("version")) is int
        and record.get("binding_id") == binding_id
        and isinstance(record.get("receipt"), Mapping)
        and isinstance(record.get("evidence"), list)
    )


def _stored_improve_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Navigator-only import additions are not present in the archived receipt."""
    output = dict(record)
    if record.get("runtime_phase") != "stopped":
        output.pop("seed_result", None)
        output.pop("submission", None)
    return output


def _collect_improve_artifacts(
    root: Path,
    state: Mapping[str, Any],
    classifications: Mapping[str, str],
    artifacts: _Artifacts,
    missing_required: list[dict[str, Any]],
    reference_only: list[dict[str, Any]],
) -> None:
    """Inventory stable Improve archives; never reread the child workspace."""
    for entry in state["history"]:
        action = entry["action"]
        record = state["improve_results"].get(action)
        required_for = _default_required_for(classifications[action])
        if _real_improve_record(record, state["run_id"] + "/" + action):
            assert isinstance(record, Mapping)
            receipt_relative = "improve/" + action + "/receipt.md"
            try:
                receipt_path, receipt_data = _run_regular_file(
                    root, receipt_relative, "Improve receipt " + action
                )
                try:
                    stored = store.loads(receipt_data.decode("utf-8"))
                except (UnicodeDecodeError, store.StorageError) as exc:
                    _fail("malformed Improve receipt " + action + ": " + str(exc))
                if stored != _stored_improve_record(record):
                    _fail("Improve receipt " + action + " does not match imported Improve record")
                artifacts.add(
                    receipt_path,
                    receipt_data,
                    role="improve-receipt",
                    producer=action,
                    classification=classifications[action],
                    required_for=required_for,
                )
            except PlanningContextError as exc:
                _add_missing(
                    missing_required,
                    _diagnostic("improve-receipt", str(exc), required_for, action=action),
                )
            for index, evidence in enumerate(record["evidence"]):
                if not isinstance(evidence, Mapping):
                    _add_missing(
                        missing_required,
                        _diagnostic("improve-evidence", "Improve evidence entry must be an object", required_for,
                                    action=action, index=index),
                    )
                    continue
                source_reference = evidence.get("source")
                archive = evidence.get("archive")
                expected_digest = evidence.get("sha256")
                if (not isinstance(source_reference, str) or not source_reference
                        or not isinstance(archive, str) or not archive
                        or not isinstance(expected_digest, str) or _SHA256.fullmatch(expected_digest) is None):
                    _add_missing(
                        missing_required,
                        _diagnostic("improve-evidence", "Improve evidence identity is invalid", required_for,
                                    action=action, index=index),
                    )
                    continue
                try:
                    archive_path, archive_data = _run_regular_file(
                        root, archive, "Improve evidence " + action + "/" + str(index)
                    )
                    if _sha256(archive_data) != expected_digest:
                        _fail("Improve evidence " + action + "/" + str(index) + " digest does not match import")
                    artifacts.add(
                        archive_path,
                        archive_data,
                        role="improve-evidence",
                        producer=action,
                        classification=classifications[action],
                        required_for=required_for,
                        source_reference=source_reference,
                    )
                except PlanningContextError as exc:
                    _add_missing(
                        missing_required,
                        _diagnostic("improve-evidence", str(exc), required_for, action=action,
                                    index=index, text=source_reference),
                    )
            continue

        # Pure navigator fixtures predate the importer.  Preserve explicit
        # absolute file references if they exist, but do not invent a durable
        # archive contract for a synthetic record.
        if not isinstance(record, Mapping):
            continue
        synthetic_refs: list[str] = []
        for key in ("evidence_refs", "review_refs", "check_refs"):
            value = record.get(key)
            if isinstance(value, list):
                synthetic_refs.extend(item for item in value if isinstance(item, str))
        for index, raw in enumerate(synthetic_refs):
            kind, candidate = _local_reference(raw)
            if kind == "url":
                reference_only.append({
                    "action": action,
                    "index": index,
                    "text": raw,
                    "kind": "url",
                    "value": raw,
                    "required_for": [],
                })
                continue
            if kind != "file" or candidate is None:
                continue
            try:
                source_path, source_data = _absolute_regular_file(str(candidate), "synthetic Improve evidence")
                _require_stable_dependency(root, source_path, "synthetic Improve evidence")
                artifacts.add(
                    source_path,
                    source_data,
                    role="improve-evidence",
                    producer=action,
                    classification=classifications[action],
                    required_for=required_for,
                    source_reference=raw,
                )
            except PlanningContextError as exc:
                _add_missing(
                    missing_required,
                    _diagnostic("improve-evidence", str(exc), required_for, action=action,
                                index=index, text=raw),
                )


def collect(
    root: Path,
    state: Mapping[str, Any],
    graph: dict,
    graph_source: dict,
    resolutions: dict | None = None,
) -> dict[str, Any]:
    """Collect a planning manifest without creating or modifying any file.

    ``resolutions`` is intentionally narrow and explicit::

        {"references": [{
            "action": "accepted-action-id", "index": 0,
            "kind": "file" | "url" | "statement",
            "path": "/absolute/file" | "value": "citation or statement",
            "rationale": "required for statements",
            "snapshot": false,
            "required_for": ["*"] | ["graph-step-id"] | [],
        }]}

    A resolution cannot delete or rewrite the original accepted ``evidence_refs``
    text.  A current reference cannot become a URL or statement merely to avoid
    a required local input.  File snapshots are produced only for an explicit
    ``snapshot: true`` selection.
    """
    run_root = _absolute_root(root)
    try:
        navigator.validate(state)
        planning_revision.validate_archives(state, run_root)
    except ValueError as exc:
        _fail("invalid navigator state: " + str(exc))
    if state.get("navigator_protocol_version") != 4:
        _fail("planning context requires a navigator protocol 4 state")
    try:
        action = navigator.current_action(state)
        stage = navigator.current_stage(state)
    except ValueError as exc:
        _fail("cannot resolve current navigator action: " + str(exc))
    if stage != "implement":
        _fail("planning context binds only the current navigator implement action")
    action_id = action["id"]
    current_workitem = _current_workitem(state)
    graph_ids = _graph_step_ids(graph)
    frozen_graph = _graph_source(graph_source)
    source = {
        "run_id": state["run_id"],
        "action_id": action_id,
        "workitem": current_workitem,
        "revision": state["revision"],
    }
    classifications = _entry_classifications(state, current_workitem)
    resolution_rows = _resolution_map(resolutions, state, classifications, graph_ids)
    artifacts = _Artifacts(graph_ids)
    missing_required: list[dict[str, Any]] = []
    unresolved_refs: list[dict[str, Any]] = []
    reference_only: list[dict[str, Any]] = []
    files: dict[str, str] = {}

    # Every accepted result record is stable planning provenance.  This catches
    # missing/tampered records without using any older planning directory.
    for entry in state["history"]:
        accepted_action = entry["action"]
        classification = classifications[accepted_action]
        required_for = _default_required_for(classification)
        relative = "results/" + accepted_action + ".md"
        expected = {
            "navigator_protocol_version": state["navigator_protocol_version"],
            "run_id": state["run_id"],
            "action": accepted_action,
            "stage": entry["stage"],
            "workitem": entry["workitem"],
            "result": state["accepted"][accepted_action],
        }
        try:
            result_path, result_data = _run_regular_file(run_root, relative, "accepted result " + accepted_action)
            try:
                recorded = store.loads(result_data.decode("utf-8"))
            except (UnicodeDecodeError, store.StorageError) as exc:
                _fail("malformed accepted result " + accepted_action + ": " + str(exc))
            if recorded != expected:
                _fail("accepted result " + accepted_action + " does not match navigator state")
            artifacts.add(
                result_path,
                result_data,
                role="accepted-result",
                producer=accepted_action,
                classification=classification,
                required_for=required_for,
            )
        except PlanningContextError as exc:
            _add_missing(
                missing_required,
                _diagnostic("accepted-result", str(exc), required_for, action=accepted_action),
            )

        for index, raw_reference in enumerate(state["accepted"][accepted_action]["evidence_refs"]):
            reference = {"action": accepted_action, "index": index, "text": raw_reference}
            resolved = resolution_rows.get((accepted_action, index))
            ref_required = required_for if resolved is None else resolved["required_for"]
            if resolved is not None and resolved["kind"] in {"url", "statement"}:
                row = {
                    **reference,
                    "kind": resolved["kind"],
                    "value": resolved["value"],
                    "required_for": ref_required,
                }
                if "rationale" in resolved:
                    row["rationale"] = resolved["rationale"]
                reference_only.append(row)
                continue
            if resolved is not None:
                kind, candidate = "file", Path(resolved["path"])
            else:
                kind, candidate = _local_reference(raw_reference)
            if kind == "url":
                reference_only.append(
                    {**reference, "kind": "url", "value": raw_reference, "required_for": []}
                )
                continue
            if kind != "file" or candidate is None:
                unresolved = {**reference, "required_for": ref_required}
                unresolved_refs.append(unresolved)
                _add_missing(
                    missing_required,
                    _diagnostic("reference", "reference requires explicit resolution", ref_required,
                                action=accepted_action, index=index, text=raw_reference),
                )
                continue
            try:
                file_path, file_data = _absolute_regular_file(str(candidate), "planning reference")
                _require_stable_dependency(run_root, file_path, "planning reference")
                if resolved is not None and resolved.get("snapshot"):
                    try:
                        snapshot_text = file_data.decode("utf-8")
                    except UnicodeDecodeError as exc:
                        _fail("snapshot source must be UTF-8 text: " + str(exc))
                    digest = _sha256(file_data)
                    snapshot_relative = _snapshot_relative(
                        action_id, accepted_action, index, digest, file_path
                    )
                    snapshot_path = run_root / snapshot_relative
                    files[snapshot_relative] = snapshot_text
                    artifacts.add(
                        snapshot_path,
                        file_data,
                        role="planning-snapshot",
                        producer=accepted_action,
                        classification=classification,
                        required_for=ref_required,
                        reference=reference,
                        origin={"path": str(file_path), "sha256": digest},
                    )
                else:
                    artifacts.add(
                        file_path,
                        file_data,
                        role="evidence-reference",
                        producer=accepted_action,
                        classification=classification,
                        required_for=ref_required,
                        reference=reference,
                    )
            except PlanningContextError as exc:
                unresolved = {**reference, "required_for": ref_required}
                unresolved_refs.append(unresolved)
                _add_missing(
                    missing_required,
                    _diagnostic("reference", str(exc), ref_required, action=accepted_action,
                                index=index, text=raw_reference),
                )

    _collect_improve_artifacts(
        run_root, state, classifications, artifacts, missing_required, reference_only
    )

    # ``bound_plan`` may be an inline planner value.  Only an explicit absolute
    # locator becomes a file dependency; relative text is retained in the
    # projection/brief rather than guessed from cwd.
    bound_plan = state["bound_plan"]
    if bound_plan:
        bound_kind, bound_candidate = _local_reference(bound_plan)
        if bound_kind == "file" and bound_candidate is not None:
            try:
                path, data = _absolute_regular_file(str(bound_candidate), "bound_plan")
                _require_stable_dependency(run_root, path, "bound_plan")
                artifacts.add(
                    path,
                    data,
                    role="bound-plan",
                    producer="planning-context",
                    classification=_CURRENT,
                    required_for=["*"],
                )
            except PlanningContextError as exc:
                _add_missing(
                    missing_required,
                    _diagnostic("bound-plan", str(exc), ["*"], text=bound_plan),
                )
        elif bound_kind == "url":
            reference_only.append(
                {
                    "action": "planning-context",
                    "index": 0,
                    "text": bound_plan,
                    "kind": "url",
                    "value": bound_plan,
                    "rationale": "bound_plan locator",
                    "required_for": [],
                }
            )

    projection_records: list[dict[str, Any]] = []
    for entry in state["history"]:
        if entry["stage"] not in _PLANNING_STAGES:
            continue
        accepted_action = entry["action"]
        row = {
            "action": accepted_action,
            "stage": entry["stage"],
            "workitem": entry["workitem"],
            "outcome": entry["outcome"],
            "summary": state["accepted"][accepted_action]["summary"],
            "evidence_refs": deepcopy(state["accepted"][accepted_action]["evidence_refs"]),
            "classification": classifications[accepted_action],
        }
        result = state["accepted"][accepted_action]
        if "choices" in result:
            row["choices"] = deepcopy(result["choices"])
        if "work_items" in result:
            row["work_items"] = deepcopy(result["work_items"])
        improve = _improve_projection(state["improve_results"].get(accepted_action, {}))
        if improve:
            row["improve"] = improve
        projection_records.append(row)
    projection = {
        "schema": PROJECTION_SCHEMA,
        "source": source,
        "bound_plan": bound_plan,
        "work_items": deepcopy(state["work_items"]),
        "planning_records": projection_records,
    }
    projection_relative = "chains/" + action_id + "/planning-projection.json"
    projection_text = _json_text(projection, "planning projection")
    projection_data = projection_text.encode("utf-8")
    files[projection_relative] = projection_text
    artifacts.add(
        run_root / projection_relative,
        projection_data,
        role="planning-projection",
        producer="planning-context",
        classification=_CURRENT,
        required_for=["*"],
    )

    briefing_relative = "chains/" + action_id + "/planning-brief.md"
    briefing_text = _briefing(run_root, state, source, current_workitem, classifications)
    briefing_data = briefing_text.encode("utf-8")
    files[briefing_relative] = briefing_text
    briefing_path = run_root / briefing_relative
    artifacts.add(
        briefing_path,
        briefing_data,
        role="planning-brief",
        producer="planning-context",
        classification=_CURRENT,
        required_for=["*"],
    )

    manifest = {
        "schema": SCHEMA,
        "source": source,
        "graph": frozen_graph,
        "briefing": {"path": str(briefing_path), "sha256": _sha256(briefing_data)},
        "artifacts": artifacts.rows(),
        "unresolved_refs": sorted(
            unresolved_refs, key=lambda item: (item["action"], item["index"], item["text"])
        ),
        "reference_only": sorted(
            reference_only, key=lambda item: (item["action"], item["index"], item["text"])
        ),
    }
    return {
        "manifest": manifest,
        "files": {path: files[path] for path in sorted(files)},
        "missing_required": sorted(
            missing_required,
            key=lambda item: (item.get("action", ""), item.get("index", -1), item["kind"], item["reason"]),
        ),
    }


__all__ = ["PlanningContextError", "SCHEMA", "collect"]
