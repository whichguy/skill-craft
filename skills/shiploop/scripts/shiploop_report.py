#!/usr/bin/env python3
"""Render a safe, deterministic, derived ShipLoop achievement report.

This module deliberately has no command-line entry point and makes no writes.
The Markdown records in a run directory remain authoritative; this renderer is
only an offline, human-oriented projection of a bounded set of those records.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any


REPORT_SCHEMA_VERSION = 1

_FIXED_SOURCES = (
    "state.md",
    "history.md",
    "lifecycle.md",
    "backchain/plan.md",
    "quality.md",
    "handoff.md",
    "shiploop-improvements.md",
)
_DISCOVERED_DIRECTORIES = (
    "results",
    "steps",
    "checks",
    "check-attempts",
    "objectives",
    "planning",
    "step-planning",
)
_SPECIALIST_RECEIPT_DIRECTORIES = {"objectives", "planning", "step-planning"}
_PLANNING_KINDS = ("research", "behavior", "spec")
_PLANNING_DIRECT_RECORDS = frozenset(
    f"{kind}{suffix}.md" for kind in _PLANNING_KINDS for suffix in ("", "-certificate")
)
_GENERATED_ARTIFACTS = {"report.html", "report-metadata.md"}
_STATE_FENCE_OPEN = re.compile(r"^```shiploop-state[ \t]*$")
_STATE_FENCE_PREFIX = re.compile(r"^```shiploop-state(?:\b|[ \t])")
_STATE_FENCE_CLOSE = re.compile(r"^```[ \t]*$")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_UNSAFE_SCHEME = re.compile(r"(?i)\b(?:javascript|data|vbscript)\s*:")
_SECRET_VALUE = re.compile(
    r"(?i)\b(?:api[ _-]?key|secret|token|password|authorization)\s*"
    r"(?:=|:)\s*(?:[^\s,;<>\"']+)"
)
_BEARER_VALUE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_URL_CREDENTIALS = re.compile(r"(?i)\bhttps?://[^\s/@:]+:[^\s/@]+@")
_LOCAL_PATH = re.compile(
    r"(?<![:A-Za-z0-9])/(?:private|users|home|tmp|var|volumes)"
    r"(?:/[^\s<>\"'`\]\)}]*)?",
    re.IGNORECASE,
)
_ACTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,160}$")
_SPECIALIST_RECEIPT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,240}\.md$")
_PLANNING_ITERATION_DIRECTORY = re.compile(r"^(?:research|behavior|spec)-iterations$")
_PLANNING_ITERATION_NAME = re.compile(r"^[A-Za-z0-9_-]+\.md$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_TEXT = 1800
_MAX_ROWS = 250

__all__ = ["REPORT_SCHEMA_VERSION", "ReportError", "render_report"]


class ReportError(ValueError):
    """Reserved for callers that need to distinguish report input failures."""


def render_report(
    run_dir: Path | str,
    *,
    overrides: Mapping[str, str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return ``(html, metadata)`` derived from effective run Markdown.

    ``overrides`` is for the protocol's write-ahead transaction: it may supply
    proposed text for the bounded, run-relative Markdown records this renderer
    reads.  It is never written by this function.  Invalid or missing evidence
    produces an unfinished report with ``evidence_errors`` rather than a green
    result.  ``state.report`` is excluded from both source identity and output,
    preventing a report's own metadata from recursively changing its digest.
    """
    errors: list[str] = []
    root = _resolve_run_dir(run_dir, errors)
    effective_overrides = _normalise_overrides(overrides, errors)
    texts: dict[str, str] = {}
    records: dict[str, Any] = {}

    if root is not None:
        candidates = _source_candidates(root, effective_overrides, errors)
        _load_source_records(
            root, candidates, effective_overrides, texts, records, errors
        )
    else:
        # Effective override text still belongs in the source identity even if a
        # bad run-dir prevents an actual report from being complete.
        candidates = {
            relative for relative in effective_overrides if _is_initial_source(relative)
        }
        _load_source_records(
            None, candidates, effective_overrides, texts, records, errors
        )

    # Planning receipts carry compact completion summaries only.  Follow a
    # receipt's exact immutable iteration references so their audit learnings
    # remain available without admitting candidate drafts, history pages, or
    # arbitrary recursive Markdown.
    planning_iterations = _referenced_planning_iterations(records, errors)
    _load_source_records(
        root,
        planning_iterations,
        effective_overrides,
        texts,
        records,
        errors,
    )
    for relative in planning_iterations:
        if relative not in texts:
            _add_error(errors, f"missing {relative}")

    source_digest = _source_digest(texts, records)
    model = _assess(records, texts, errors)
    metadata = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_digest": source_digest,
        "sources": sorted(texts),
        "outcome": model["outcome"],
        "evidence_complete": model["evidence_complete"],
        "evidence_errors": list(errors),
    }
    return _render_html(model, records, texts, metadata), metadata


def _resolve_run_dir(run_dir: Path | str, errors: list[str]) -> Path | None:
    try:
        root = Path(run_dir).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        _add_error(errors, "run directory is unavailable")
        return None
    try:
        mode = os.lstat(root).st_mode
    except OSError:
        _add_error(errors, "run directory is unavailable")
        return None
    if not stat.S_ISDIR(mode):
        _add_error(errors, "run directory is not a directory")
        return None
    return root


def _normalise_overrides(
    overrides: Mapping[str, str] | None, errors: list[str]
) -> dict[str, str]:
    if overrides is None:
        return {}
    if not isinstance(overrides, Mapping):
        _add_error(errors, "overrides are not a mapping")
        return {}
    result: dict[str, str] = {}
    for raw_relative, text in overrides.items():
        relative = _normalise_relative(raw_relative)
        if relative in _GENERATED_ARTIFACTS:
            # The caller may construct the complete write set before asking us
            # to render. Generated report artifacts must not feed themselves.
            continue
        if relative is None or not _is_allowed_source(relative):
            _add_error(errors, "an override path was rejected")
            continue
        if not isinstance(text, str):
            _add_error(errors, f"{relative} override is not text")
            continue
        if relative in result:
            _add_error(errors, f"duplicate override for {relative}")
            continue
        result[relative] = text
    return result


def _normalise_relative(value: object) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return None
    try:
        path = PurePosixPath(value)
    except (TypeError, ValueError):
        return None
    if path.is_absolute() or value != path.as_posix():
        return None
    parts = path.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        return None
    return "/".join(parts)


def _is_allowed_source(relative: str) -> bool:
    if relative in _FIXED_SOURCES:
        return True
    parts = relative.split("/")
    if len(parts) == 2:
        directory, filename = parts
        if directory in {"results", "steps", "checks", "check-attempts"}:
            return filename.endswith(".md")
        if directory in {"objectives", "step-planning"}:
            return _SPECIALIST_RECEIPT_NAME.fullmatch(filename) is not None
        if directory == "planning":
            return filename in _PLANNING_DIRECT_RECORDS
    return _is_planning_iteration_source(relative)


def _is_initial_source(relative: str) -> bool:
    """Return whether a record can be discovered without a receipt reference."""
    return _is_allowed_source(relative) and not _is_planning_iteration_source(relative)


def _is_planning_iteration_source(relative: str) -> bool:
    parts = relative.split("/")
    return (
        len(parts) == 3
        and parts[0] == "planning"
        and _PLANNING_ITERATION_DIRECTORY.fullmatch(parts[1]) is not None
        and _PLANNING_ITERATION_NAME.fullmatch(parts[2]) is not None
    )


def _source_candidates(
    root: Path, overrides: Mapping[str, str], errors: list[str]
) -> list[str]:
    candidates = set(_FIXED_SOURCES)
    for directory in _DISCOVERED_DIRECTORIES:
        path = root / directory
        try:
            status = os.lstat(path)
        except FileNotFoundError:
            continue
        except OSError:
            _add_error(errors, f"cannot inspect {directory} evidence")
            continue
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
            _add_error(errors, f"{directory} evidence directory is unsafe")
            continue
        try:
            children = sorted(path.iterdir(), key=lambda item: item.name)
        except OSError:
            _add_error(errors, f"cannot enumerate {directory} evidence")
            continue
        for child in children:
            try:
                child_status = os.lstat(child)
            except OSError:
                _add_error(errors, f"cannot inspect {directory} evidence entry")
                continue
            relative = _normalise_relative(f"{directory}/{child.name}")
            if stat.S_ISDIR(child_status.st_mode) and not stat.S_ISLNK(
                child_status.st_mode
            ):
                # Specialist directories necessarily contain candidate drafts
                # and immutable archives.  They are not report sources unless
                # a planning receipt explicitly names an iteration archive.
                if directory in _SPECIALIST_RECEIPT_DIRECTORIES:
                    continue
                _add_error(errors, f"unsafe source name in {directory} evidence")
                continue
            if (
                stat.S_ISLNK(child_status.st_mode)
                or not stat.S_ISREG(child_status.st_mode)
                or relative is None
                or not _is_initial_source(relative)
            ):
                _add_error(errors, f"unsafe source name in {directory} evidence")
                continue
            candidates.add(relative)
    candidates.update(
        relative for relative in overrides if _is_initial_source(relative)
    )
    return sorted(candidates)


def _load_source_records(
    root: Path | None,
    candidates: set[str] | list[str],
    overrides: Mapping[str, str],
    texts: dict[str, str],
    records: dict[str, Any],
    errors: list[str],
) -> None:
    """Read only allowlisted sources, with overrides taking transaction precedence."""
    for relative in sorted(candidates):
        if relative in texts:
            continue
        text = overrides.get(relative)
        if text is None and root is not None:
            text = _read_regular_text(root, relative, errors)
        if text is None:
            continue
        texts[relative] = text
        try:
            records[relative] = _load_markdown_record(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            _add_error(errors, f"{relative} is corrupt or not a ShipLoop record")


def _referenced_planning_iterations(
    records: Mapping[str, Any], errors: list[str]
) -> set[str]:
    """Select only immutable iteration records named by a planning receipt."""
    selected: set[str] = set()
    for kind in _PLANNING_KINDS:
        receipt_path = f"planning/{kind}.md"
        receipt = records.get(receipt_path)
        if receipt is None:
            continue
        if not isinstance(receipt, Mapping):
            continue
        completed = receipt.get("completed_iterations")
        if not isinstance(completed, list):
            _add_error(
                errors, f"{receipt_path} has invalid completed iteration evidence"
            )
            continue
        expected_directory = f"planning/{kind}-iterations/"
        for index, row in enumerate(completed, start=1):
            if not isinstance(row, Mapping):
                _add_error(
                    errors,
                    f"{receipt_path} completed iteration {index} is malformed",
                )
                continue
            relative = _normalise_relative(row.get("path"))
            if (
                relative is None
                or not _is_planning_iteration_source(relative)
                or not relative.startswith(expected_directory)
            ):
                _add_error(
                    errors,
                    f"{receipt_path} completed iteration {index} has an unsafe archive path",
                )
                continue
            selected.add(relative)
    return selected


def _read_regular_text(root: Path, relative: str, errors: list[str]) -> str | None:
    path = root
    components = relative.split("/")
    for index, component in enumerate(components):
        path = path / component
        try:
            status = os.lstat(path)
        except FileNotFoundError:
            return None
        except OSError:
            _add_error(errors, f"cannot read {relative}")
            return None
        if stat.S_ISLNK(status.st_mode):
            _add_error(errors, f"{relative} has an unsafe symlinked path")
            return None
        if index < len(components) - 1 and not stat.S_ISDIR(status.st_mode):
            _add_error(errors, f"{relative} has an unsafe parent path")
            return None
        if index == len(components) - 1 and not stat.S_ISREG(status.st_mode):
            _add_error(errors, f"{relative} is not a safe regular file")
            return None
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        _add_error(errors, f"cannot read {relative}")
        return None
    try:
        current = os.fstat(descriptor)
        if not stat.S_ISREG(current.st_mode):
            _add_error(errors, f"{relative} changed while being read")
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        try:
            return b"".join(chunks).decode("utf-8")
        except UnicodeDecodeError:
            _add_error(errors, f"{relative} is not UTF-8 text")
            return None
    finally:
        os.close(descriptor)


def _load_markdown_record(text: str) -> Any:
    """Parse the one strict ``shiploop-state`` fence used by durable records."""
    if not isinstance(text, str):
        raise ValueError("record is not text")
    lines = text.splitlines()
    openings: list[int] = []
    for index, line in enumerate(lines):
        if _STATE_FENCE_OPEN.match(line):
            openings.append(index)
        elif _STATE_FENCE_PREFIX.match(line):
            raise ValueError("malformed fence")
    if len(openings) != 1:
        raise ValueError("record must contain exactly one state fence")
    closing = None
    for index in range(openings[0] + 1, len(lines)):
        if _STATE_FENCE_CLOSE.match(lines[index]):
            closing = index
            break
    if closing is None:
        raise ValueError("unterminated state fence")

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(_: str) -> None:
        raise ValueError("nonstandard JSON constant")

    return json.loads(
        "\n".join(lines[openings[0] + 1 : closing]),
        object_pairs_hook=reject_duplicate,
        parse_constant=reject_constant,
    )


def _source_digest(texts: Mapping[str, str], records: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(b"shiploop-achievement-report-sources-v1\0")
    for relative in sorted(texts):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        payload = texts[relative].encode("utf-8")
        if relative == "state.md" and isinstance(records.get(relative), dict):
            state = dict(records[relative])
            state.pop("report", None)
            payload = json.dumps(
                state,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        digest.update(payload)
        digest.update(b"\0")
    return digest.hexdigest()


def _assess(
    records: Mapping[str, Any], texts: Mapping[str, str], errors: list[str]
) -> dict[str, Any]:
    state = _mapping_record(records, texts, errors, "state.md")
    phase = _plain(state.get("phase"), limit=80)
    stage = _plain(state.get("stage"), limit=80)
    terminal = state.get("phase") == "done" and state.get("stage") == "done"
    if not terminal:
        _add_error(errors, "terminal state is not done/done")

    history = _list_record(records, texts, errors, "history.md")
    lifecycle = _mapping_record(records, texts, errors, "lifecycle.md")
    plan = _mapping_record(records, texts, errors, "backchain/plan.md")
    quality = _mapping_record(records, texts, errors, "quality.md")
    handoff = _mapping_record(records, texts, errors, "handoff.md")
    journal = _list_record(records, texts, errors, "shiploop-improvements.md")
    final_check_valid = False

    if terminal:
        acceptance = _string_list(lifecycle.get("acceptance"))
        if not acceptance:
            _add_error(errors, "lifecycle.md has no valid acceptance list")
        steps = plan.get("steps")
        if not isinstance(steps, list) or not steps:
            _add_error(errors, "backchain/plan.md has no valid steps")
            steps = []
        for row in steps:
            if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
                _add_error(errors, "backchain/plan.md has an invalid step")
                continue
            sid = row["id"]
            receipt_path = f"steps/{sid}.md"
            receipt = _mapping_record(records, texts, errors, receipt_path)
            if receipt.get("status") != "complete":
                _add_error(errors, f"{receipt_path} is not complete")
        action = state.get("outer_check_action")
        if not isinstance(action, str) or not _ACTION_ID.fullmatch(action):
            _add_error(errors, "state.md has no final outer check action")
        else:
            final_check = _mapping_record(records, texts, errors, f"checks/{action}.md")
            final_result = _mapping_record(
                records, texts, errors, f"results/{action}.md"
            )
            final_errors = _final_check_errors(final_check, action, acceptance)
            final_errors.extend(_completed_result_errors(state, action, final_result))
            for message in final_errors:
                _add_error(errors, message)
            final_check_valid = not final_errors
        _last_completion_errors(state, records, texts, errors)

    # A valid final row is not enough to label the report machine-verified if
    # any selected durable evidence is missing, corrupt, or unbound.
    final_check_valid = final_check_valid and not errors
    evidence_complete = not errors
    return {
        "state": state,
        "phase": phase,
        "stage": stage,
        "terminal": terminal,
        "outcome": "complete" if evidence_complete and terminal else "unfinished",
        "evidence_complete": evidence_complete and terminal,
        "history": history,
        "lifecycle": lifecycle,
        "plan": plan,
        "quality": quality,
        "handoff": handoff,
        "journal": journal,
        "final_check_valid": final_check_valid,
    }


def _mapping_record(
    records: Mapping[str, Any],
    texts: Mapping[str, str],
    errors: list[str],
    relative: str,
) -> dict[str, Any]:
    if relative not in texts:
        _add_error(errors, f"missing {relative}")
        return {}
    value = records.get(relative)
    if not isinstance(value, dict):
        _add_error(errors, f"{relative} is not an object record")
        return {}
    return value


def _list_record(
    records: Mapping[str, Any],
    texts: Mapping[str, str],
    errors: list[str],
    relative: str,
) -> list[Any]:
    if relative not in texts:
        _add_error(errors, f"missing {relative}")
        return []
    value = records.get(relative)
    if not isinstance(value, list):
        _add_error(errors, f"{relative} is not a list record")
        return []
    return value


def _final_check_errors(
    record: Mapping[str, Any], action: str, lifecycle_acceptance: list[str]
) -> list[str]:
    """Validate compact final-check metadata without reading private raw logs."""
    errors: list[str] = []
    manifest = record.get("manifest")
    results = record.get("results")
    if not isinstance(manifest, Mapping) or not isinstance(results, Mapping):
        return [f"checks/{action}.md lacks manifest or result metadata"]
    expected = manifest.get("checks")
    observed = results.get("checks")
    if results.get("action") != action or results.get("action_id") != action:
        errors.append(f"checks/{action}.md result action does not match final action")
    if (
        results.get("all_passed") is not True
        or results.get("content_changed") is not False
        or not isinstance(expected, list)
        or not expected
        or not isinstance(observed, list)
        or len(expected) != len(observed)
    ):
        errors.append(f"checks/{action}.md does not record a stable passed final check")
        return errors
    if not _unchanged_fingerprint_metadata(results):
        errors.append(f"checks/{action}.md has missing or changed source fingerprints")
    if not isinstance(results.get("manifest_digest"), str) or not _SHA256.fullmatch(
        results["manifest_digest"]
    ):
        errors.append(f"checks/{action}.md has no valid manifest digest")
    seen_ids: set[str] = set()
    test_acceptance: set[str] = set()
    lint_found = False
    test_found = False
    for expected_row, observed_row in zip(expected, observed):
        if not isinstance(expected_row, Mapping) or not isinstance(
            observed_row, Mapping
        ):
            errors.append(f"checks/{action}.md has malformed check rows")
            continue
        check_id = expected_row.get("id")
        kind = expected_row.get("kind")
        argv = expected_row.get("argv")
        acceptance = expected_row.get("acceptance")
        if (
            not isinstance(check_id, str)
            or not check_id
            or check_id in seen_ids
            or kind not in {"lint", "test"}
            or not isinstance(argv, list)
            or not argv
            or any(not isinstance(part, str) or not part for part in argv)
            or not isinstance(acceptance, list)
            or any(not isinstance(item, str) or not item for item in acceptance)
        ):
            errors.append(f"checks/{action}.md has an invalid manifest check")
            continue
        seen_ids.add(check_id)
        lint_found = lint_found or kind == "lint"
        test_found = test_found or kind == "test"
        if kind == "test":
            test_acceptance.update(acceptance)
        if (
            observed_row.get("id") != check_id
            or observed_row.get("kind") != kind
            or observed_row.get("acceptance") != acceptance
        ):
            errors.append(
                f"checks/{action}.md result row does not match manifest {check_id}"
            )
        if observed_row.get("status") != "passed" or observed_row.get("exit") != 0:
            errors.append(f"checks/{action}.md check {check_id} did not pass")
        if not _log_metadata_available(observed_row):
            errors.append(
                f"checks/{action}.md check {check_id} log metadata is unavailable"
            )
    if not lint_found or not test_found:
        errors.append(f"checks/{action}.md requires concrete lint and test checks")
    uncovered = sorted(set(lifecycle_acceptance) - test_acceptance)
    if uncovered:
        errors.append(f"checks/{action}.md does not cover all lifecycle acceptance")
    return errors


def _unchanged_fingerprint_metadata(results: Mapping[str, Any]) -> bool:
    before = results.get("before_fingerprint")
    after = results.get("after_fingerprint")
    return (
        isinstance(before, str)
        and isinstance(after, str)
        and _SHA256.fullmatch(before) is not None
        and before == after
        and results.get("before") == before
        and results.get("after") == after
    )


def _log_metadata_available(row: Mapping[str, Any]) -> bool:
    paths = row.get("log_paths")
    return (
        all(
            isinstance(row.get(key), str) and row[key]
            for key in ("log_path", "stdout_log", "stderr_log")
        )
        and isinstance(paths, Mapping)
        and all(
            isinstance(paths.get(key), str) and paths[key]
            for key in ("stdout", "stderr")
        )
    )


def _completed_result_errors(
    state: Mapping[str, Any], action: str, result: Mapping[str, Any]
) -> list[str]:
    completed = state.get("completed_actions")
    if not isinstance(completed, Mapping):
        return ["state.md has no completed-action result fingerprint ledger"]
    expected = completed.get(action)
    if not isinstance(expected, str) or not _SHA256.fullmatch(expected):
        return [f"state.md has no valid result fingerprint for {action}"]
    if not result:
        return [f"results/{action}.md is unavailable for final action binding"]
    if _result_digest(result) != expected:
        return [f"results/{action}.md does not match its completed-action fingerprint"]
    return []


def _last_completion_errors(
    state: Mapping[str, Any],
    records: Mapping[str, Any],
    texts: Mapping[str, str],
    errors: list[str],
) -> None:
    """Bind a newer terminal result when the protocol records one explicitly."""
    last = state.get("last_completion")
    if last is None:
        return
    if not isinstance(last, Mapping):
        _add_error(errors, "state.md last completion binding is malformed")
        return
    action = last.get("action")
    digest = last.get("result_digest")
    if not isinstance(action, str) or not _ACTION_ID.fullmatch(action):
        _add_error(errors, "state.md last completion action is invalid")
        return
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        _add_error(errors, "state.md last completion result fingerprint is invalid")
        return
    result = _mapping_record(records, texts, errors, f"results/{action}.md")
    if not result or _result_digest(result) != digest:
        _add_error(errors, f"results/{action}.md does not match last completion")
    completed = state.get("completed_actions")
    if isinstance(completed, Mapping) and completed.get(action) != digest:
        _add_error(errors, "last completion does not match completed-action ledger")


def _result_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _add_error(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def _plain(value: Any, *, limit: int = _MAX_TEXT) -> str:
    if not isinstance(value, str):
        return "Not recorded"
    text = _CONTROL.sub(" ", value).strip()
    text = _UNSAFE_SCHEME.sub("[unsafe scheme omitted]", text)
    text = _SECRET_VALUE.sub("[secret redacted]", text)
    text = _BEARER_VALUE.sub("[secret redacted]", text)
    text = _URL_CREDENTIALS.sub("https://[credentials redacted]@", text)
    text = _LOCAL_PATH.sub("[local path redacted]", text)
    if not text:
        return "Not recorded"
    if len(text) > limit:
        return text[:limit].rstrip() + "… [truncated]"
    return text


def _esc(value: Any, *, limit: int = _MAX_TEXT) -> str:
    return html.escape(_plain(value, limit=limit), quote=True).replace("\n", "<br>")


def _internal_link(anchor: str, label: str) -> str:
    safe_anchor = re.sub(r"[^a-z0-9-]", "", anchor.lower())
    return f'<a href="#{safe_anchor}">{html.escape(label, quote=True)}</a>'


def _render_html(
    model: Mapping[str, Any],
    records: Mapping[str, Any],
    texts: Mapping[str, str],
    metadata: Mapping[str, Any],
) -> str:
    outcome = str(model["outcome"])
    outcome_title = "Complete" if outcome == "complete" else "Unfinished"
    nav = "".join(
        _internal_link(anchor, label)
        for anchor, label in (
            ("overview", "Overview"),
            ("timeline", "Timeline"),
            ("outputs", "Outputs"),
            ("tests", "Tests"),
            ("learnings", "Learnings"),
            ("limits", "Limits"),
        )
    )
    sections = [
        _overview(model, metadata),
        _timeline(model.get("history", [])),
        _outputs(model, records),
        _tests(model, records),
        _learnings_and_plan(records),
        _limits_and_proposals(model, records, metadata),
        _source_inventory(metadata),
    ]
    stylesheet = """
    :root { color-scheme: light; --ink:#1e293b; --muted:#526174; --paper:#f7f8fb;
      --card:#fff; --line:#dce3ec; --accent:#255bd6; --good:#087443; --warn:#aa5800;
      --bad:#b42318; --soft-blue:#edf3ff; --soft-green:#edf9f1; --soft-warn:#fff5e8; }
    * { box-sizing:border-box; } body { margin:0; color:var(--ink); background:var(--paper);
      font:15px/1.5 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    .wrap { width:min(1120px, calc(100% - 32px)); margin:0 auto; }
    header { color:#fff; background:linear-gradient(125deg,#132a5e,#2863df); padding:36px 0 26px; }
    .eyebrow { margin:0 0 7px; font-size:.78rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; opacity:.82; }
    h1 { margin:0; font-size:clamp(1.8rem,4vw,2.7rem); line-height:1.12; } h2 { margin:0 0 14px; font-size:1.22rem; }
    h3 { margin:0 0 6px; font-size:1rem; } .subhead { max-width:760px; margin:10px 0 0; color:#dde8ff; }
    nav { display:flex; flex-wrap:wrap; gap:10px 18px; margin-top:22px; } nav a { color:#fff; font-size:.9rem; text-decoration:none; }
    nav a:hover, nav a:focus { text-decoration:underline; } main { padding:26px 0 44px; }
    section { margin:18px 0; padding:22px; background:var(--card); border:1px solid var(--line); border-radius:14px; box-shadow:0 1px 2px rgba(15,23,42,.04); }
    .notice { margin:0 0 16px; padding:10px 12px; border-left:4px solid var(--accent); background:var(--soft-blue); color:#263b67; }
    .facts { display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:10px; }
    .fact { padding:12px; border:1px solid var(--line); border-radius:10px; background:#fcfdff; }
    .fact dt { color:var(--muted); font-size:.78rem; font-weight:700; letter-spacing:.03em; text-transform:uppercase; }
    .fact dd { margin:4px 0 0; font-weight:650; overflow-wrap:anywhere; }
    .badge { display:inline-block; padding:3px 8px; border-radius:999px; font-size:.79rem; font-weight:750; }
    .complete { color:var(--good); background:var(--soft-green); } .unfinished { color:var(--warn); background:var(--soft-warn); }
    .machine { color:var(--good); font-weight:700; } .host { color:var(--muted); font-weight:700; }
    .table-wrap { overflow-x:auto; } .scroll-hint { display:none; margin:0 0 7px; color:var(--muted); font-size:.82rem; }
    table { width:100%; border-collapse:collapse; min-width:610px; }
    th,td { padding:10px; vertical-align:top; text-align:left; border-bottom:1px solid var(--line); overflow-wrap:anywhere; }
    th { color:var(--muted); font-size:.76rem; letter-spacing:.04em; text-transform:uppercase; } tr:last-child td { border-bottom:0; }
    .timeline { list-style:none; margin:0; padding:0; } .timeline li { position:relative; padding:0 0 14px 24px; border-left:2px solid #d8e3ff; }
    .timeline li:last-child { padding-bottom:0; } .timeline li::before { content:""; position:absolute; left:-6px; top:4px; width:10px; height:10px; border-radius:50%; background:var(--accent); }
    .muted { color:var(--muted); } .error-list { margin:0; padding-left:20px; color:var(--bad); }
    .proposals { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:12px; } .proposal { padding:14px; border:1px solid var(--line); border-radius:10px; }
    code { font:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.88em; overflow-wrap:anywhere; }
    details summary { cursor:pointer; font-weight:700; } .source-list { columns:2 220px; margin:10px 0 0; padding-left:20px; }
    @media (max-width:620px) { .wrap { width:min(100% - 22px,1120px); } header { padding-top:26px; } section { padding:16px; } .source-list { columns:1; } .scroll-hint { display:block; } }
    @media print { body { background:#fff; font-size:10pt; } header { color:#000; background:#fff; padding:0 0 12px; } .subhead { color:#333; } nav { display:none; } .wrap { width:100%; } section { break-inside:avoid; box-shadow:none; border-color:#bbb; } a { color:inherit; text-decoration:none; } }
    """
    body_attributes = (
        f'data-outcome="{html.escape(outcome, quote=True)}" '
        f'data-source-digest="{html.escape(str(metadata["source_digest"]), quote=True)}"'
    )
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>ShipLoop achievement report</title>\n<style>"
        + stylesheet
        + "</style>\n</head>\n<body "
        + body_attributes
        + '>\n<header><div class="wrap">\n'
        '<p class="eyebrow">ShipLoop derived achievement report</p>\n<h1>'
        + outcome_title
        + "</h1>\n"
        '<p class="subhead">An offline summary of selected durable Markdown evidence. '
        "It does not replace the authoritative run records.</p>\n<nav>"
        + nav
        + '</nav>\n</div></header>\n<main class="wrap">'
        + "".join(sections)
        + "\n</main>\n</body></html>\n"
    )


def _overview(model: Mapping[str, Any], metadata: Mapping[str, Any]) -> str:
    outcome = str(model["outcome"])
    label = "Complete" if outcome == "complete" else "Unfinished"
    summary = _plain(model.get("handoff", {}).get("summary"))
    facts = (
        ("Outcome", f'<span class="badge {outcome}">{label}</span>'),
        (
            "Run phase / stage",
            _esc(f"{model.get('phase')} / {model.get('stage')}", limit=160),
        ),
        (
            "Evidence",
            "Complete" if metadata["evidence_complete"] else "Evidence incomplete",
        ),
        (
            "Source digest",
            "<code>" + _esc(metadata["source_digest"], limit=80) + "</code>",
        ),
        ("Authoritative sources", str(len(metadata["sources"]))),
    )
    fact_html = "".join(
        f'<div class="fact"><dt>{html.escape(name)}</dt><dd>{value}</dd></div>'
        for name, value in facts
    )
    return f"""<section id="overview">
<h2>Outcome at a glance</h2>
<p class="notice"><strong>Derived report — not authoritative state.</strong> Read the durable Markdown records for decisions, recovery, and any mutation.</p>
<div class="facts">{fact_html}</div>
<h3 style="margin-top:18px">Final handoff summary <span class="host">Host-reported</span></h3>
<p>{_esc(summary)}</p>
</section>"""


def _timeline(history: Any) -> str:
    rows: list[str] = []
    summary = ""
    if isinstance(history, list):
        total = len(history)
        entries: list[tuple[int | None, Any]]
        if total > _MAX_ROWS:
            leading = 20
            trailing = _MAX_ROWS - leading
            entries = list(enumerate(history[:leading], start=1))
            entries.append((None, total - _MAX_ROWS))
            entries.extend(enumerate(history[-trailing:], start=total - trailing + 1))
            summary = (
                f'<p class="muted">Timeline truncated: showing the first {leading} '
                f"and latest {trailing} of {total} recorded events.</p>"
            )
        else:
            entries = list(enumerate(history, start=1))
            summary = f'<p class="muted">{total} recorded event{"" if total == 1 else "s"}.</p>'
        for index, entry in entries:
            if index is None:
                rows.append(
                    f'<li><strong>{entry} events omitted</strong><br><span class="muted">See authoritative history.md for the complete sequence.</span></li>'
                )
                continue
            if not isinstance(entry, Mapping):
                rows.append(
                    f'<li><strong>Event {index}</strong><br><span class="muted">Malformed history entry</span></li>'
                )
                continue
            event = _esc(entry.get("event"), limit=200)
            action = entry.get("action")
            stage = (
                action.get("stage") if isinstance(action, Mapping) else "Not recorded"
            )
            revision = entry.get("revision")
            detail = f"stage {_esc(stage, limit=100)}"
            if isinstance(revision, int):
                detail += f" · revision {revision}"
            rows.append(
                f'<li><strong>{event}</strong><br><span class="muted">{detail}</span></li>'
            )
    if not rows:
        rows.append(
            '<li><strong>No readable history</strong><br><span class="muted">The report cannot infer an actual sequence.</span></li>'
        )
        summary = '<p class="muted">No recorded event count is available.</p>'
    return (
        '<section id="timeline"><h2>Actual sequence</h2>'
        + summary
        + '<ol class="timeline">'
        + "".join(rows)
        + "</ol></section>"
    )


def _outputs(model: Mapping[str, Any], records: Mapping[str, Any]) -> str:
    lifecycle = model.get("lifecycle", {})
    plan = model.get("plan", {})
    required = _string_list(
        lifecycle.get("acceptance") if isinstance(lifecycle, Mapping) else None
    )
    final_check = _final_check(model, records)
    coverage = _covered_acceptance(final_check)
    rows: list[list[str]] = []
    for criterion in required:
        observed = (
            "Covered by final check"
            if criterion in coverage
            else "No final check evidence"
        )
        rows.append(["Lifecycle acceptance", _esc(criterion), observed])
    steps = plan.get("steps") if isinstance(plan, Mapping) else []
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, Mapping):
                continue
            sid = step.get("id") if isinstance(step.get("id"), str) else "Unknown step"
            receipt = records.get(f"steps/{sid}.md")
            status = (
                receipt.get("status")
                if isinstance(receipt, Mapping)
                else "missing receipt"
            )
            contract = step.get("contract")
            done_rows = contract.get("done") if isinstance(contract, Mapping) else None
            if isinstance(done_rows, list) and done_rows:
                for criterion in done_rows:
                    if not isinstance(criterion, Mapping):
                        continue
                    criterion_id = criterion.get("id", "contract DoD")
                    produced = "; ".join(_string_list(criterion.get("produces")))
                    condition = criterion.get("condition")
                    expected = _plain(condition)
                    if produced:
                        expected += f" Outputs: {produced}"
                    observed = _contract_observation(
                        receipt, "done", criterion_id, status
                    )
                    rows.append(
                        [
                            f"Step {sid} / {criterion_id}",
                            _esc(expected),
                            _esc(observed, limit=300),
                        ]
                    )
            else:
                produced = _string_list(step.get("produces"))
                expected = "; ".join(produced) if produced else step.get("statement")
                rows.append([f"Step {sid}", _esc(expected), _esc(status, limit=160)])
    if not rows:
        rows.append(
            ["Not recorded", "No readable required outputs", "No achievement evidence"]
        )
    return (
        '<section id="outputs"><h2>Required and achieved outputs / DoD</h2>'
        + _table(("Source", "Required", "Achieved / observed"), rows)
        + "</section>"
    )


def _contract_observation(
    receipt: Any, section: str, criterion_id: Any, fallback: Any
) -> Any:
    """Read a public contract evidence row if an evolving receipt supplies one."""
    if not isinstance(receipt, Mapping) or not isinstance(criterion_id, str):
        return fallback
    for evidence_key in ("done_evidence", "contract_evidence", "evidence"):
        evidence = receipt.get(evidence_key)
        if not isinstance(evidence, Mapping):
            continue
        rows = evidence.get(section)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping) or row.get("id") != criterion_id:
                continue
            for observed_key in ("observed", "observed_outcome"):
                if isinstance(row.get(observed_key), str) and row[observed_key].strip():
                    return row[observed_key]
    return fallback


def _tests(model: Mapping[str, Any], records: Mapping[str, Any]) -> str:
    final_check = _final_check(model, records)
    rows: list[list[str]] = []
    if isinstance(final_check, Mapping):
        manifest = final_check.get("manifest")
        results = final_check.get("results")
        expected = manifest.get("checks") if isinstance(manifest, Mapping) else []
        observed = results.get("checks") if isinstance(results, Mapping) else []
        observed_by_id = (
            {
                row.get("id"): row
                for row in observed
                if isinstance(row, Mapping) and isinstance(row.get("id"), str)
            }
            if isinstance(observed, list)
            else {}
        )
        if isinstance(expected, list):
            for check in expected:
                if not isinstance(check, Mapping):
                    continue
                cid = check.get("id") if isinstance(check.get("id"), str) else "unknown"
                actual = observed_by_id.get(cid, {})
                expected_text = (
                    "; ".join(_string_list(check.get("acceptance")))
                    or "Declared check passes"
                )
                status = (
                    actual.get("status")
                    if isinstance(actual, Mapping)
                    else "not recorded"
                )
                exit_code = actual.get("exit") if isinstance(actual, Mapping) else None
                observed_text = _plain(status, limit=100)
                if isinstance(exit_code, int):
                    observed_text += f" (exit {exit_code})"
                log_metadata = (
                    "Recorded; raw logs intentionally omitted"
                    if isinstance(actual, Mapping) and _log_metadata_available(actual)
                    else "Unavailable; raw logs were not read or exported"
                )
                rows.append(
                    [
                        _esc(cid, limit=160),
                        _esc(expected_text),
                        _esc(observed_text),
                        log_metadata,
                    ]
                )
    rows.extend(_contract_test_rows(model, records))
    if not rows:
        rows.append(
            [
                "No final check",
                "No expected outcome recorded",
                "No observed outcome recorded",
                "No log metadata",
            ]
        )
    quality = model.get("quality", {})
    quality_review = (
        quality.get("test_review") if isinstance(quality, Mapping) else None
    )
    attempts = _attempt_rows(records)
    attempts_html = _table(("Attempt", "Observed result", "Evidence note"), attempts)
    verification_label = (
        '<span class="machine">Machine-verified</span> means a compact final check '
        "record with matched action, fingerprints, manifest/result rows, and log metadata; "
        "this report does not rerun commands."
        if model.get("final_check_valid")
        else '<span class="badge unfinished">Verification unavailable</span> Final check metadata is missing or malformed; raw logs were not read or exported.'
    )
    return f"""<section id="tests">
<h2>Test evidence</h2>
<p>{verification_label} <span class="host">Host-reported</span> narrative is shown separately.</p>
{_table(("Check", "Expected", "Observed", "Log metadata"), rows)}
<h3 style="margin-top:18px">Quality review <span class="host">Host-reported</span></h3>
<p>{_esc(quality_review)}</p>
<h3 style="margin-top:18px">Checks failures and retries</h3>
{attempts_html}
</section>"""


def _final_check(
    model: Mapping[str, Any], records: Mapping[str, Any]
) -> Mapping[str, Any]:
    state = model.get("state")
    action = state.get("outer_check_action") if isinstance(state, Mapping) else None
    record = records.get(f"checks/{action}.md") if isinstance(action, str) else None
    return record if isinstance(record, Mapping) else {}


def _contract_test_rows(
    model: Mapping[str, Any], records: Mapping[str, Any]
) -> list[list[str]]:
    """Render expected/observed rows from the opt-in nested step.contract schema."""
    output: list[list[str]] = []
    plan = model.get("plan")
    steps = plan.get("steps") if isinstance(plan, Mapping) else []
    if not isinstance(steps, list):
        return output
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        sid = step.get("id") if isinstance(step.get("id"), str) else "Unknown step"
        receipt = records.get(f"steps/{sid}.md")
        step_contract = step.get("contract")
        if not isinstance(step_contract, Mapping):
            continue
        criteria = step_contract.get("tests")
        if not isinstance(criteria, list):
            continue
        for criterion in criteria:
            if not isinstance(criterion, Mapping):
                continue
            criterion_id = criterion.get("id")
            expected = criterion.get("expected_outcome")
            if not isinstance(criterion_id, str) or not isinstance(expected, str):
                continue
            observed = _contract_observation(
                receipt, "tests", criterion_id, "No observed contract test outcome"
            )
            output.append(
                [
                    _esc(f"{sid} / {criterion_id}", limit=180),
                    _esc(expected),
                    _esc(observed),
                    "Host-reported contract evidence",
                ]
            )
    return output


def _covered_acceptance(final_check: Mapping[str, Any]) -> set[str]:
    results = final_check.get("results")
    rows = results.get("checks") if isinstance(results, Mapping) else []
    covered: set[str] = set()
    if isinstance(rows, list):
        for row in rows:
            if (
                isinstance(row, Mapping)
                and row.get("status") == "passed"
                and row.get("exit") == 0
            ):
                covered.update(_string_list(row.get("acceptance")))
    return covered


def _attempt_rows(records: Mapping[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for relative in sorted(key for key in records if key.startswith("check-attempts/"))[
        :_MAX_ROWS
    ]:
        record = records[relative]
        results = record.get("results") if isinstance(record, Mapping) else None
        passed = (
            results.get("all_passed") is True if isinstance(results, Mapping) else False
        )
        outcome = "Passed" if passed else "Failed or incomplete"
        note = "Retry record" if not passed else "Passing attempt"
        rows.append([_esc(relative, limit=240), outcome, note])
    if not rows:
        rows.append(["No attempts recorded", "Not recorded", "No retry evidence"])
    return rows


def _learnings_and_plan(records: Mapping[str, Any]) -> str:
    learning_rows: list[list[str]] = []
    plan_rows: list[list[str]] = []
    seen_learning: set[tuple[str, str]] = set()

    def add_pass(
        scope: Any, commit: Any, outcome: Any, pass_record: Mapping[str, Any]
    ) -> None:
        if len(learning_rows) >= _MAX_ROWS:
            return
        learnings = _pass_learnings(pass_record)
        if not learnings:
            learnings = ["No learning text recorded"]
        for learning in learnings:
            if len(learning_rows) >= _MAX_ROWS:
                return
            key = (str(commit), learning)
            if key in seen_learning:
                continue
            seen_learning.add(key)
            learning_rows.append(
                [
                    _esc(scope, limit=160),
                    _esc(commit, limit=96),
                    _esc(outcome, limit=100),
                    _esc(learning),
                ]
            )

    for relative in sorted(key for key in records if key.startswith("steps/")):
        if len(learning_rows) >= _MAX_ROWS:
            break
        receipt = records[relative]
        if not isinstance(receipt, Mapping):
            continue
        sid = receipt.get("id") if isinstance(receipt.get("id"), str) else relative
        cycles = receipt.get("improve_cycles")
        if isinstance(cycles, list):
            for index, cycle in enumerate(cycles, start=1):
                if not isinstance(cycle, Mapping):
                    continue
                commit = cycle.get(
                    "primary_commit", cycle.get("commit", "Not recorded")
                )
                outcome = cycle.get("outcome", "Not recorded")
                add_pass(f"Step {sid} pass {index}", commit, outcome, cycle)
        review = receipt.get("plan_review")
        if isinstance(review, Mapping) and review.get("plan_decision"):
            plan_rows.append(
                [
                    _esc(sid, limit=120),
                    _esc(review.get("plan_decision"), limit=120),
                    _esc(review.get("plan_reason")),
                ]
            )

    # Objective and step-plan receipts preserve their completed pass objects
    # directly.  Read only the durable learning fields; never expose their
    # candidate or plan bodies.
    for relative in sorted(
        key for key in records if key.startswith("objectives/") and key.count("/") == 1
    ):
        if len(learning_rows) >= _MAX_ROWS:
            break
        receipt = records[relative]
        if not isinstance(receipt, Mapping):
            continue
        kind = _plain(receipt.get("kind"), limit=64)
        loop = _plain(receipt.get("loop_id"), limit=96)
        completed = receipt.get("completed_passes")
        if not isinstance(completed, list):
            continue
        for row in completed:
            if not isinstance(row, Mapping):
                continue
            pass_id = row.get("id", "completed pass")
            add_pass(
                f"Objective {kind} ({loop}) / {pass_id}",
                row.get("commit", "Not recorded"),
                row.get("outcome", "Not recorded"),
                row,
            )

    for relative in sorted(
        key
        for key in records
        if key.startswith("step-planning/") and key.count("/") == 1
    ):
        if len(learning_rows) >= _MAX_ROWS:
            break
        receipt = records[relative]
        if not isinstance(receipt, Mapping):
            continue
        step_id = _plain(receipt.get("step_id"), limit=96)
        loop = _plain(receipt.get("loop_id"), limit=96)
        completed = receipt.get("completed_passes")
        if not isinstance(completed, list):
            continue
        for row in completed:
            if not isinstance(row, Mapping):
                continue
            pass_id = row.get("id", "completed pass")
            add_pass(
                f"Step plan {step_id} ({loop}) / {pass_id}",
                row.get("commit", "Not recorded"),
                row.get("outcome", "Not recorded"),
                row,
            )

    # Planning receipts intentionally summarize their completed iterations.
    # The source selector above admits only their named immutable archives,
    # whose review/apply learnings are the actual audit evidence.
    for relative in sorted(
        key for key in records if _is_planning_iteration_source(key)
    ):
        if len(learning_rows) >= _MAX_ROWS:
            break
        iteration = records[relative]
        if not isinstance(iteration, Mapping):
            continue
        parts = relative.split("/")
        kind = parts[1].removesuffix("-iterations")
        iteration_id = iteration.get("id", parts[2].removesuffix(".md"))
        add_pass(
            f"Planning {kind} / {iteration_id}",
            iteration.get("primary_commit", iteration.get("commit", "Not recorded")),
            iteration.get("outcome", "Not recorded"),
            iteration,
        )

    for relative in sorted(key for key in records if key.startswith("results/")):
        result = records[relative]
        if not isinstance(result, Mapping) or not result.get("plan_decision"):
            continue
        plan_rows.append(
            [
                _esc(relative, limit=240),
                _esc(result.get("plan_decision"), limit=120),
                _esc(result.get("plan_reason")),
            ]
        )
    if not learning_rows:
        learning_rows.append(
            [
                "No learning commits recorded",
                "Not recorded",
                "Not recorded",
                "No durable learning text",
            ]
        )
    if not plan_rows:
        plan_rows.append(
            [
                "No broader-plan decision recorded",
                "Not recorded",
                "No broader-plan change evidence",
            ]
        )
    return f"""<section id="learnings">
<h2>Learning commits</h2>
{_table(("Loop / pass", "Commit", "Outcome", "Learning"), learning_rows)}
<h3 style="margin-top:18px">Broader-plan changes</h3>
{_table(("Source", "Decision", "Reason"), plan_rows)}
</section>"""


def _cycle_learnings(cycle: Mapping[str, Any]) -> list[str]:
    """Backward-compatible alias for generic bounded pass learnings."""
    return _pass_learnings(cycle)


def _pass_learnings(pass_record: Mapping[str, Any]) -> list[str]:
    """Project compact learning fields without rendering plan/candidate bodies."""
    values: list[str] = []
    top_level = pass_record.get("learnings")
    if isinstance(top_level, str):
        values.append(top_level)
    for key in (
        "review",
        "plan",
        "apply",
        "applied",
        "revise",
        "carry_forward",
    ):
        nested = pass_record.get(key)
        if isinstance(nested, Mapping) and isinstance(nested.get("learnings"), str):
            values.append(nested["learnings"])
    plan_learnings = pass_record.get("plan_learnings")
    if isinstance(plan_learnings, list):
        values.extend(item for item in plan_learnings if isinstance(item, str))
    return list(dict.fromkeys(value for value in values if value.strip()))


def _limits_and_proposals(
    model: Mapping[str, Any], records: Mapping[str, Any], metadata: Mapping[str, Any]
) -> str:
    limitations: list[str] = list(metadata.get("evidence_errors", []))
    state = model.get("state")
    if isinstance(state, Mapping):
        for key in ("paused", "blocked_reason", "halt_reason", "ask_user"):
            if isinstance(state.get(key), str) and state[key].strip():
                limitations.append(state[key])
    plan = model.get("plan")
    if isinstance(plan, Mapping) and isinstance(plan.get("unresolved"), list):
        limitations.extend(str(item) for item in plan["unresolved"] if item)
    limitations = list(
        dict.fromkeys(
            _plain(item) for item in limitations if _plain(item) != "Not recorded"
        )
    )
    if limitations:
        limit_html = (
            '<ul class="error-list">'
            + "".join(f"<li>{_esc(item)}</li>" for item in limitations)
            + "</ul>"
        )
    else:
        limit_html = (
            "<p>No unresolved limitation is recorded in the selected evidence.</p>"
        )

    journal = model.get("journal", [])
    cards: list[str] = []
    if isinstance(journal, list):
        for entry in journal[:_MAX_ROWS]:
            if not isinstance(entry, Mapping):
                continue
            cards.append(
                '<article class="proposal"><h3>'
                + _esc(entry.get("title"), limit=240)
                + "</h3><p><strong>Impact:</strong> "
                + _esc(entry.get("impact"))
                + "</p><p><strong>Proposal:</strong> "
                + _esc(entry.get("proposal"))
                + "</p><p><strong>Test idea:</strong> "
                + _esc(entry.get("test_idea"))
                + "</p></article>"
            )
    if not cards:
        cards.append("<p>No ShipLoop improvement proposal is recorded.</p>")
    return f"""<section id="limits">
<h2>Unresolved limitations</h2>
{limit_html}
<h3 style="margin-top:18px">ShipLoop improvement proposals</h3>
<div class="proposals">{"".join(cards)}</div>
</section>"""


def _source_inventory(metadata: Mapping[str, Any]) -> str:
    sources = metadata.get("sources", [])
    items = "".join(
        f"<li><code>{_esc(source, limit=300)}</code></li>" for source in sources
    )
    if not items:
        items = "<li>No readable source records</li>"
    return f"""<section id="sources">
<details>
<summary>Source inventory and derivation boundary</summary>
<p>This report reads a bounded set of run-relative Markdown records, does not execute checks, and intentionally omits raw logs, command arguments, host paths, and secret-like values.</p>
<p>Source digest: <code>{_esc(metadata.get("source_digest"), limit=80)}</code></p>
<ul class="source-list">{items}</ul>
</details>
</section>"""


def _table(headers: tuple[str, ...], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows[:_MAX_ROWS]
    )
    return (
        '<p class="scroll-hint" role="note">Wide table — scroll horizontally '
        'to view all columns.</p><div class="table-wrap"><table><thead><tr>'
        f"{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )
