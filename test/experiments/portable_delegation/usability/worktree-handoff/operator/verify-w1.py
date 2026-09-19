#!/usr/bin/env python3
"""Offline operator guards for the U18 W1 worktree-handoff fixture.

This module is deliberately test-only.  It never launches an agent, waits for a
process, polls a host, removes a worktree, or treats a model/worker boolean as
independent evidence.

The JSON contracts are intentionally small and explicit:

* ``snapshot`` returns ``ask-agent-w1.snapshot.v1`` with the canonical checkout,
  Git identity, semantic staged/unstaged diff hashes, status records, and a
  per-file type/mode/content-hash manifest.
* ``preflight`` consumes a prepared ``paths.json`` plus a native observation of
  the form ``{"cwd": ..., "project_path": ..., "argv": [...],
  "prompt_sha256": ..., "skill_sha256": ...}`` and returns ``READY`` only
  when the source, launch paths, frozen hashes, and baseline still agree.
* ``public-opencode`` reads SQLite through a read-only URI and emits only
  whitelisted scalar fields from ``session``, ``message``, and text/tool
  ``part`` rows.  It never selects data, metadata, reasoning, result, or tool
  output columns.  The output path must be outside the source, worktrees, and
  durable inbox.
* ``complete`` consumes normalized native observations and the actual source and
  inbox filesystem.  It emits ``COMPLETE`` only for two returned, terminal,
  successful workers, a parent final after both returns, pricing-only source
  integration, durable reports, and removed worktrees.  ``finish``/``stop`` by
  itself is insufficient.  ``INCOMPLETE``, ``FAILED``, and ``UNSUPPORTED`` are
  retained as honest boundaries.

All command output is JSON.  A contract violation exits non-zero; no command
performs cleanup or creates worker worktrees.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import sqlite3
import stat
import subprocess
import sys
from typing import Any, Iterable


SCHEMA_SNAPSHOT = "ask-agent-w1.snapshot.v1"
SCHEMA_PATHS = "ask-agent-w1.paths.v1"
SCHEMA_PUBLIC = "ask-agent-w1.public-opencode.v2"
SCHEMA_VERDICT = "ask-agent-w1.verdict.v1"


class ContractError(ValueError):
    """A deterministic fixture-contract violation."""


def _canonical(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_dump(value: Any, path: Path | None = None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(text, end="")
        return
    path = _canonical(path)
    if not path.parent.exists():
        raise ContractError(f"output parent does not exist: {path.parent}")
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)
    except OSError as exc:
        raise ContractError(f"cannot create new evidence file {path}: {exc}") from exc


def _json_load(path: str | os.PathLike[str]) -> Any:
    try:
        return json.loads(_canonical(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read JSON {path}: {exc}") from exc


def _run(argv: list[str], cwd: Path, *, check: bool = True) -> bytes:
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        stderr = result.stderr.decode("utf-8", "replace").strip()
        raise ContractError(f"command failed ({result.returncode}): {shlex.join(argv)}: {stderr}")
    return result.stdout


def _git(source: Path, *args: str, check: bool = True) -> bytes:
    return _run(["git", *args], source, check=check)


def _decode_zlist(raw: bytes) -> list[str]:
    return [item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item]


def _index_entries(source: Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for item in _git(source, "ls-files", "-s", "-z").split(b"\0"):
        if not item:
            continue
        header, raw_path = item.split(b"\t", 1)
        # ``git ls-files -s`` emits ``mode object stage<TAB>path``.
        mode, object_id, stage = header.decode("ascii").split()
        rel = raw_path.decode("utf-8", "surrogateescape")
        entries[rel] = {"mode": mode, "stage": int(stage), "object": object_id}
    return entries


def _status_records(raw: bytes) -> list[dict[str, str]]:
    parts = raw.split(b"\0")
    records: list[dict[str, str]] = []
    index = 0
    while index < len(parts):
        item = parts[index]
        index += 1
        if not item:
            continue
        decoded = item.decode("utf-8", "surrogateescape")
        if len(decoded) < 3:
            continue
        record: dict[str, str] = {"xy": decoded[:2], "path": decoded[3:]}
        if decoded[0] in "RC" or decoded[1] in "RC":
            if index < len(parts) and parts[index]:
                record["previous_path"] = parts[index].decode("utf-8", "surrogateescape")
                index += 1
        records.append(record)
    return records


def _file_entry(path: Path, index: dict[str, Any] | None) -> dict[str, Any]:
    entry: dict[str, Any] = {"type": "missing", "mode": None, "content_sha256": None}
    if index is not None:
        entry["index"] = index
    try:
        info = path.lstat()
    except FileNotFoundError:
        return entry
    entry["mode"] = format(stat.S_IMODE(info.st_mode), "04o")
    if stat.S_ISLNK(info.st_mode):
        entry["type"] = "symlink"
        entry["content_sha256"] = _sha256(os.readlink(path).encode("utf-8", "surrogateescape"))
    elif stat.S_ISREG(info.st_mode):
        entry["type"] = "file"
        entry["content_sha256"] = _sha256_file(path)
    elif stat.S_ISDIR(info.st_mode):
        entry["type"] = "directory"
    else:
        entry["type"] = "other"
    return entry


def snapshot(source: str | os.PathLike[str]) -> dict[str, Any]:
    """Capture a semantic, hash-only snapshot of a Git checkout."""

    checkout = _canonical(source)
    if not checkout.is_dir():
        raise ContractError(f"source checkout is not a directory: {checkout}")
    root = _canonical(_git(checkout, "rev-parse", "--show-toplevel").decode().strip())
    head = _git(checkout, "rev-parse", "HEAD").decode().strip()
    branch = _git(checkout, "branch", "--show-current").decode().strip() or "(detached)"
    git_dir_text = _git(checkout, "rev-parse", "--git-dir").decode().strip()
    common_dir_text = _git(checkout, "rev-parse", "--git-common-dir").decode().strip()
    git_dir = _canonical(checkout / git_dir_text) if not os.path.isabs(git_dir_text) else _canonical(git_dir_text)
    common_dir = _canonical(checkout / common_dir_text) if not os.path.isabs(common_dir_text) else _canonical(common_dir_text)
    status_raw = _git(checkout, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    staged_diff = _git(checkout, "-c", "diff.autoRefreshIndex=false", "diff", "--binary", "--no-ext-diff", "--no-textconv")
    index_diff = _git(checkout, "-c", "diff.autoRefreshIndex=false", "diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv")
    tracked = _decode_zlist(_git(checkout, "ls-files", "-z"))
    untracked = _decode_zlist(_git(checkout, "ls-files", "-z", "--others", "--exclude-standard"))
    ignored = _decode_zlist(_git(checkout, "ls-files", "-z", "--others", "--ignored", "--exclude-standard"))
    index = _index_entries(checkout)
    files = {
        rel: _file_entry(checkout / rel, index.get(rel))
        for rel in sorted(set(tracked) | set(untracked) | set(ignored))
    }
    return {
        "schema": SCHEMA_SNAPSHOT,
        "source_checkout": str(checkout),
        "git_root": str(root),
        "git_dir": str(git_dir),
        "git_common_dir": str(common_dir),
        "branch": branch,
        "head": head,
        "status_sha256": _sha256(status_raw),
        "status_records": _status_records(status_raw),
        "staged_diff_sha256": _sha256(index_diff),
        "unstaged_diff_sha256": _sha256(staged_diff),
        "untracked_paths": sorted(untracked),
        "ignored_paths": sorted(ignored),
        "files": files,
    }


def _write_fixture_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def prepare_fixture(
    run_dir: str | os.PathLike[str],
    prompt: str | None = None,
    skill: str | None = None,
    reference: str | None = None,
) -> dict[str, Any]:
    """Create the README's dirty linked worktree and no worker worktrees."""

    run = _canonical(run_dir)
    if run.exists():
        raise ContractError(f"prepare requires a non-existing owned root: {run}")
    run.mkdir(parents=True)
    primary = run / "w1-primary"
    source = run / "w1-feature"
    inbox = run / "w1-inbox"
    _run(["git", "init", "-b", "main", str(primary)], run)
    _git(primary, "config", "user.name", "W1 fixture")
    _git(primary, "config", "user.email", "w1-fixture@example.invalid")
    # Keep fixture commits deterministic without mutating global Git config.
    hooks = run / "fixture-hooks"
    hooks.mkdir()
    _git(primary, "config", "commit.gpgSign", "false")
    _git(primary, "config", "core.hooksPath", str(hooks))
    _write_fixture_file(primary / "dual.txt", "base\n")
    _write_fixture_file(primary / "deleted.txt", "delete me\n")
    _write_fixture_file(primary / "unstaged.txt", "original\n")
    _write_fixture_file(primary / "pricing.json", '{"currency":"USD","base_price":100}\n')
    _git(primary, "add", "dual.txt", "deleted.txt", "unstaged.txt", "pricing.json")
    _git(primary, "commit", "-m", "w1 baseline")
    _run(["git", "worktree", "add", "-b", "feature", str(source)], primary)
    _write_fixture_file(source / "feature.txt", "feature parent commit\n")
    _git(source, "add", "feature.txt")
    _git(source, "commit", "-m", "feature is ahead of main")
    _write_fixture_file(source / "dual.txt", "staged layer\n")
    _git(source, "add", "dual.txt")
    _write_fixture_file(source / "dual.txt", "staged layer\nunstaged layer\n")
    _write_fixture_file(source / "staged-add.txt", "staged addition\n")
    _git(source, "add", "staged-add.txt")
    (source / "deleted.txt").unlink()
    _write_fixture_file(source / "unstaged.txt", "changed but unstaged\n")
    _write_fixture_file(source / "notes.txt", "untracked input\n")
    inbox.mkdir()
    source_snapshot = snapshot(source)
    paths: dict[str, Any] = {
        "schema": SCHEMA_PATHS,
        "run_dir": str(run),
        "primary": str(primary),
        "source": str(source),
        "inbox": str(inbox),
        "source_snapshot": str(run / "source-before.json"),
        "frozen_prompt_sha256": _sha256_file(_canonical(prompt)) if prompt else None,
        "frozen_skill_sha256": _sha256_file(_canonical(skill)) if skill else None,
        "frozen_reference_sha256": _sha256_file(_canonical(reference)) if reference else None,
    }
    _json_dump(source_snapshot, run / "source-before.json")
    _json_dump(paths, run / "paths.json")
    return paths


def _snapshot_differences(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    differences: list[str] = []
    for key in ("git_root", "git_dir", "git_common_dir", "branch", "head", "status_sha256", "staged_diff_sha256", "unstaged_diff_sha256", "untracked_paths", "files"):
        if left.get(key) != right.get(key):
            differences.append(key)
    return differences


def _argv_paths(argv: Iterable[str]) -> list[str]:
    values: list[str] = []
    flags = {"--project", "--project-path", "--cwd", "--workdir", "--directory", "--cd", "-C"}
    args = list(argv)
    for index, value in enumerate(args):
        if value in flags and index + 1 < len(args):
            values.append(args[index + 1])
        elif any(value.startswith(flag + "=") for flag in flags):
            values.append(value.split("=", 1)[1])
    return values


def preflight(
    source: str | os.PathLike[str],
    manifest: str | os.PathLike[str],
    parent_cwd: str | os.PathLike[str],
    launch: dict[str, Any],
    *,
    prompt: str | None = None,
    skill: str | None = None,
    reference: str | None = None,
) -> dict[str, Any]:
    """Verify native launch paths, frozen hashes, and an unchanged baseline."""

    paths = _json_load(manifest)
    expected_source = _canonical(paths.get("source", ""))
    actual_source = _canonical(source)
    errors: list[str] = []
    if expected_source != actual_source:
        errors.append(f"manifest source {expected_source} != supplied source {actual_source}")
    if _canonical(parent_cwd) != actual_source:
        errors.append(f"parent cwd {_canonical(parent_cwd)} != source {actual_source}")
    if _canonical(launch.get("cwd", "")) != actual_source:
        errors.append("native launch cwd does not equal source checkout")
    project = launch.get("project_path", launch.get("project"))
    if project is None or _canonical(project) != actual_source:
        errors.append("native launch project path does not equal source checkout")
    raw_argv = launch.get("argv", [])
    if not isinstance(raw_argv, list) or not raw_argv or not all(isinstance(item, str) for item in raw_argv):
        raise ContractError("native launch argv must be a non-empty string array")
    argv_paths = [_canonical(item) for item in _argv_paths(raw_argv)]
    if Path(raw_argv[0]).name == "opencode" and len(raw_argv) > 1 and not raw_argv[1].startswith("-"):
        argv_paths.append(_canonical(raw_argv[1]))
    cwd_only = launch.get("argv_cwd_only") is True or launch.get("argv_mode") == "cwd-only"
    if any(path != actual_source for path in argv_paths):
        errors.append("native launch argv contains a conflicting project/cwd path")
    if actual_source not in argv_paths and not cwd_only:
        errors.append("native launch argv has no project/cwd path matching source checkout")
    baseline_path = _canonical(paths.get("source_snapshot", ""))
    if not baseline_path.is_file():
        errors.append(f"missing expected source baseline: {baseline_path}")
    else:
        baseline = _json_load(baseline_path)
        current = snapshot(actual_source)
        differences = _snapshot_differences(baseline, current)
        if differences:
            errors.append("source baseline drift: " + ", ".join(differences))
    required_frozen = (("frozen_prompt_sha256", prompt, "prompt_sha256"), ("frozen_skill_sha256", skill, "skill_sha256"))
    for field, supplied_path, launch_field in required_frozen + (("frozen_reference_sha256", reference, "reference_sha256"),):
        expected = paths.get(field)
        if not expected:
            errors.append(f"missing {field} for native preflight")
            continue
        if expected:
            actual = launch.get(launch_field)
            if not supplied_path:
                errors.append(f"{field} requires the actual frozen file path")
            else:
                actual_file_hash = _sha256_file(_canonical(supplied_path))
                if actual_file_hash != expected:
                    errors.append(f"{field} file digest drift")
            if actual != expected:
                errors.append(f"native launch {launch_field} does not match frozen digest")
    if errors:
        raise ContractError("; ".join(errors))
    return {
        "schema": "ask-agent-w1.preflight.v1",
        "status": "READY",
        "source": str(actual_source),
        "baseline": str(baseline_path),
        "checks": ["source-root", "parent-cwd", "native-project", "native-argv", "frozen-digests", "baseline"],
    }


_COMMON_PUBLIC_FIELDS = {
    "id", "session_id", "message_id", "task_id", "parent_id", "role", "type",
    "status", "cwd", "workdir", "directory", "project_path", "command",
    "file_path", "path", "prompt", "description", "subagent_type", "background",
    "created_at", "updated_at", "time_created", "time_updated", "started_at", "completed_at", "timestamp",
}
_TABLE_FIELDS = {
    "session": _COMMON_PUBLIC_FIELDS - {"message_id", "prompt", "description", "subagent_type", "background", "command", "file_path"},
    "message": _COMMON_PUBLIC_FIELDS,
    "part": _COMMON_PUBLIC_FIELDS,
}
_REASONING_VALUES = {"reasoning", "analysis", "thinking", "chain_of_thought"}

# OpenCode 1.18 stores the public values below inside a JSON ``data`` column.
# The adapter may use json_extract for these individual paths, but it never
# selects ``data`` itself.  Direct scalar columns remain supported for the
# hermetic fixture schema.
_JSON_FIELDS = {
    "message": {
        "role": "$.role",
        "finish": "$.finish",
        "model_id": "$.modelID",
        "provider_id": "$.providerID",
        "completed_at": "$.time.completed",
    },
    "part": {
        "type": "$.type",
        "text": "$.text",
        "tool": "$.tool",
        "status": "$.state.status",
        "prompt": "$.state.input.prompt",
        "description": "$.state.input.description",
        "subagent_type": "$.state.input.subagent_type",
        "background": "$.state.input.background",
        "task_id": "$.state.input.task_id",
        "task_id_present": "$.state.input.task_id",
        "command": "$.state.input.command",
        "workdir": "$.state.input.workdir",
        "file_path": "$.state.input.filePath",
        "path": "$.state.input.path",
    },
}


def _quote_identifier(value: str) -> str:
    if not value or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for character in value):
        raise ContractError(f"unsafe SQLite identifier: {value!r}")
    return '"' + value.replace('"', '""') + '"'


def _public_db_path(output: Path, known_paths: Iterable[str | os.PathLike[str]]) -> None:
    for known in known_paths:
        if not known:
            continue
        for root in {_canonical(known), Path(known).expanduser().absolute()}:
            if output == root or root in output.parents:
                raise ContractError(f"operator evidence must be outside participant path: {output}")


def _operator_output(output: str | os.PathLike[str], known_paths: Iterable[str | os.PathLike[str]]) -> Path:
    lexical = Path(output).expanduser().absolute()
    resolved = _canonical(output)
    paths = list(known_paths)
    _public_db_path(lexical, paths)
    _public_db_path(resolved, paths)
    if lexical.exists() or lexical.is_symlink() or resolved.exists():
        raise ContractError(f"operator evidence requires a new output file: {output}")
    return resolved


def public_opencode(
    db: str | os.PathLike[str],
    session: str,
    output: str | os.PathLike[str],
    *,
    source: str,
    worktree: str | Iterable[str],
    inbox: str,
) -> dict[str, Any]:
    """Project supported scalar OpenCode records without reading private payloads."""

    # Check both the lexical destination and its resolved destination.  A
    # symlink inside a participant directory must not become an escape hatch.
    worktrees = [worktree] if isinstance(worktree, (str, os.PathLike)) else list(worktree)
    output_path = _operator_output(output, [source, inbox, *worktrees])
    if not output_path.parent.is_dir():
        raise ContractError(f"public projection parent does not exist: {output_path.parent}")
    db_path = _canonical(db)
    if not db_path.is_file():
        raise ContractError(f"SQLite database does not exist: {db_path}")
    uri = db_path.as_uri() + "?mode=ro"
    records: list[dict[str, Any]] = []
    tables: list[str] = []
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        table_rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        tables = [str(row[0]) for row in table_rows]
        for table in sorted(tables, key=str.lower):
            lower = table.lower()
            if lower not in _TABLE_FIELDS:
                continue
            columns = [str(row[1]) for row in connection.execute(f"PRAGMA table_info({_quote_identifier(table)})").fetchall()]
            column_by_lower = {column.lower(): column for column in columns}
            allowed = [column for column in columns if column.lower() in _TABLE_FIELDS[lower]]
            data_column = column_by_lower.get("data")
            json_fields = _JSON_FIELDS.get(lower, {}) if data_column else {}
            if not allowed and not json_fields:
                continue
            # No raw text/data/metadata/result columns are selected.  For the
            # real OpenCode schema only individual JSON paths are selected.
            expressions = [_quote_identifier(column) + " AS " + _quote_identifier(column.lower()) for column in allowed]
            aliases = {column.lower() for column in allowed}
            if data_column:
                for alias, json_path in json_fields.items():
                    if alias in aliases or (lower == "part" and alias == "text"):
                        # Tool parts may contain output in this field; text is
                        # selected only by the text-part query below.
                        continue
                    if alias == "task_id_present":
                        expressions.append(f"CASE WHEN json_type({_quote_identifier(data_column)}, {json.dumps(json_path)}) IS NOT NULL THEN 1 ELSE 0 END AS {_quote_identifier(alias)}")
                    else:
                        expressions.append(f"json_extract({_quote_identifier(data_column)}, {json.dumps(json_path)}) AS {_quote_identifier(alias)}")
            if not expressions:
                continue
            select = ", ".join(expressions)
            clauses: list[str] = []
            params: list[Any] = []
            session_column = column_by_lower.get("session_id")
            if session_column:
                clauses.append(f"{_quote_identifier(session_column)} = ?")
                params.append(session)
            elif lower == "session" and "id" in column_by_lower:
                clauses.append(f"{_quote_identifier(column_by_lower['id'])} = ?")
                params.append(session)
            elif lower == "part" and "message_id" in column_by_lower:
                message_table = next((name for name in tables if name.lower() == "message"), None)
                message_columns = set()
                if message_table:
                    message_columns = {str(row[1]).lower() for row in connection.execute(f"PRAGMA table_info({_quote_identifier(message_table)})").fetchall()}
                if message_table and "session_id" in message_columns:
                    clauses.append(f"{_quote_identifier(column_by_lower['message_id'])} IN (SELECT {_quote_identifier('id')} FROM {_quote_identifier(message_table)} WHERE {_quote_identifier('session_id')} = ?)")
                    params.append(session)
                else:
                    continue
            elif lower != "session":
                # Do not emit unrelated public records when the table cannot be
                # tied to the requested session.
                continue
            type_expr = None
            if lower == "part":
                if "type" in column_by_lower:
                    type_expr = _quote_identifier(column_by_lower["type"])
                elif data_column:
                    type_expr = f"json_extract({_quote_identifier(data_column)}, '$.type')"
                else:
                    continue
                clauses.append(f"{type_expr} IN (?, ?)")
                params.extend(("text", "tool"))
            for column in ("type", "role", "part_type"):
                direct = column_by_lower.get(column)
                expression = _quote_identifier(direct) if direct else (f"json_extract({_quote_identifier(data_column)}, {json.dumps(_JSON_FIELDS[lower][column])})" if data_column and column in _JSON_FIELDS.get(lower, {}) else None)
                if expression:
                    clauses.append(f"LOWER(COALESCE({expression}, '')) NOT IN (?, ?, ?, ?)")
                    params.extend(sorted(_REASONING_VALUES))
            if lower == "part" and data_column:
                # The text path is public only for text parts.  A CASE keeps
                # tool output out of the SELECT result instead of selecting it
                # and attempting to redact it afterwards.
                expressions.append(
                    f"CASE WHEN {type_expr} = 'text' THEN json_extract({_quote_identifier(data_column)}, '$.text') END AS \"text\""
                )
                select = ", ".join(expressions)
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            query = f"SELECT {select} FROM {_quote_identifier(table)}{where}"
            for row in connection.execute(query, params).fetchall():
                values: dict[str, Any] = {}
                for key in row.keys():
                    value = row[key]
                    if isinstance(value, (bytes, bytearray, memoryview)):
                        continue
                    if value is not None:
                        values[key] = value
                if lower == "part" and values.get("type") == "tool":
                    values.pop("text", None)
                if values:
                    records.append({"table": table, "fields": values})
        connection.close()
    except sqlite3.Error as exc:
        raise ContractError(f"unsupported/read-only OpenCode SQLite schema: {exc}") from exc
    usable = (
        any(item["table"].lower() == "session" and item["fields"].get("id") == session for item in records)
        and any(item["table"].lower() == "message" and item["fields"].get("role") in {"user", "assistant"} for item in records)
        and any(item["table"].lower() == "part" and item["fields"].get("type") in {"text", "tool"} for item in records)
    )
    if not usable:
        result = {
            "schema": SCHEMA_PUBLIC,
            "status": "UNSUPPORTED",
            "session": session,
            "records": [],
            "reason": "requested session lacks supported session, message-role and public-part records",
        }
    else:
        records.sort(key=lambda item: (item["table"].lower(), str(item["fields"].get("created_at", "")), str(item["fields"].get("id", ""))))
        task_calls = [record["fields"] for record in records
                      if record["table"].lower() == "part" and record["fields"].get("tool") == "task"]
        result = {
            "schema": SCHEMA_PUBLIC,
            "status": "PROJECTED",
            "session": session,
            "task_calls": task_calls,
            "records": records,
            "excluded": ["data", "metadata", "reasoning", "content", "output", "result", "tool_output", "arbitrary_columns"],
        }
    _json_dump(result, output_path)
    return result


_TERMINAL = {"completed", "failed", "cancelled", "blocked", "unsupported"}


def _event_time(event: dict[str, Any], position: int) -> tuple[int, float | str]:
    value = event.get("timestamp", event.get("time"))
    if isinstance(value, (int, float)):
        return (0, float(value))
    if isinstance(value, str) and value:
        return (1, value)
    return (2, position)


def _required_report_paths(worker: dict[str, Any], inbox: Path) -> list[Path]:
    prefix = str(worker.get("inbox_prefix", worker.get("id", "")))
    names = worker.get("required_reports", ["reports/handoff-index.md", "reports/validation.md"])
    if not prefix or Path(prefix).is_absolute() or ".." in Path(prefix).parts:
        raise ContractError(f"unsafe durable inbox prefix for {worker.get('role', 'worker')}")
    result: list[Path] = []
    for name in names:
        relative = Path(str(name))
        if relative.is_absolute() or ".." in relative.parts:
            raise ContractError(f"unsafe durable report path: {name}")
        candidate = (inbox / prefix / relative).resolve(strict=False)
        if inbox not in candidate.parents:
            raise ContractError(f"durable report escapes inbox: {name}")
        result.append(candidate)
    return result


def _source_final_check(source: Path, baseline: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    current = snapshot(source)
    if baseline.get("source_checkout") != str(source) or baseline.get("git_root") != current.get("git_root"):
        errors.append("source checkout/root does not match the recorded baseline")
    if any(baseline.get(field) != current.get(field) for field in ("git_dir", "git_common_dir")):
        errors.append("source Git directory identity changed from the recorded baseline")
    if current.get("branch") != baseline.get("branch"):
        errors.append("source branch changed during parent integration")
    if current.get("head") != baseline.get("head"):
        try:
            _run(["git", "merge-base", "--is-ancestor", str(baseline.get("head")), str(current.get("head"))], source)
        except ContractError:
            errors.append("source HEAD is not a descendant of the recorded baseline")
        else:
            changed_since_head = _git(source, "diff", "--name-only", f"{baseline.get('head')}..{current.get('head')}").decode().splitlines()
            if any(path != "pricing.json" for path in changed_since_head):
                errors.append("source commit integration changed a non-pricing path")
    before_files = baseline.get("files", {})
    after_files = current.get("files", {})
    for rel in sorted(set(before_files) | set(after_files)):
        if rel == "pricing.json":
            continue
        if before_files.get(rel) != after_files.get(rel):
            errors.append(f"unexpected source artifact or inherited sentinel change: {rel}")
    pricing = source / "pricing.json"
    try:
        data = json.loads(pricing.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"pricing.json is not valid JSON: {exc}")
        return errors
    if data != {"currency": "USD", "base_price": 100, "discount_rate": 0.10}:
        errors.append("pricing.json contains more than the intended discount_rate integration")
    if before_files.get("pricing.json", {}).get("content_sha256") == after_files.get("pricing.json", {}).get("content_sha256"):
        errors.append("pricing.json has no worker contribution")
    return errors


def _registered_git_worktree_paths(source: Path) -> set[Path]:
    paths: set[Path] = set()
    for line in _git(source, "worktree", "list", "--porcelain").decode("utf-8", "replace").splitlines():
        if line.startswith("worktree "):
            paths.add(_canonical(line[len("worktree "):]))
    return paths


def complete_w1(
    source: str | os.PathLike[str],
    baseline: str | os.PathLike[str],
    observations: dict[str, Any],
    inbox: str | os.PathLike[str],
) -> dict[str, Any]:
    """Grade actual W1 filesystem plus normalized native observations."""

    source_path = _canonical(source)
    inbox_path = _canonical(inbox)
    errors: list[str] = []
    unsupported: list[str] = []
    checks: dict[str, str] = {}
    baseline_data = _json_load(baseline)
    if baseline_data.get("schema") != SCHEMA_SNAPSHOT:
        raise ContractError("baseline is not an ask-agent-w1.snapshot.v1 document")
    errors.extend(_source_final_check(source_path, baseline_data))
    checks["source_pricing_only"] = "PASS" if not errors else "FAIL"

    workers = observations.get("workers")
    if not isinstance(workers, list) or not all(isinstance(worker, dict) for worker in workers):
        raise ContractError("observations.workers must be a list of objects")
    events = observations.get("events", [])
    if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
        raise ContractError("observations.events must be a list of objects")
    by_role = {str(item.get("role")): item for item in workers if isinstance(item, dict)}
    worker_ids = [str(item.get("id", "")) for item in workers if isinstance(item, dict)]
    worker_paths = [str(item.get("worktree", "")) for item in workers if isinstance(item, dict)]
    if any(not value for value in worker_ids) or len(set(worker_ids)) != len(worker_ids):
        errors.append("worker IDs are missing or not distinct")
    if any(not value for value in worker_paths) or len({_canonical(value) for value in worker_paths if value}) != len(worker_paths):
        errors.append("worker worktree paths are missing or not distinct")
    registered = observations.get("registered_worktrees")
    if not isinstance(registered, list) or not registered:
        unsupported.append("registered native worktree list is unavailable")
        registered_by_path: dict[Path, dict[str, Any]] = {}
    else:
        registered_by_path = {
            _canonical(item.get("path", "")): item
            for item in registered
            if isinstance(item, dict) and item.get("path")
        }
    for role in ("code", "report"):
        if role not in by_role:
            errors.append(f"required {role} worker observation is absent")
    if len(by_role) != len(workers):
        errors.append("worker roles are missing or duplicated")
    if set(by_role) != {"code", "report"}:
        errors.append("W1 requires exactly code and report worker roles")
    parent_state = str(observations.get("parent_state", "")).lower()
    if parent_state not in {"completed", "finished"}:
        unsupported.append("successful parent terminal state is unavailable")
    parent_tools = observations.get("parent_tool_states")
    if not isinstance(parent_tools, list) or not parent_tools:
        unsupported.append("parent tool terminal states are unavailable")
    elif any(str(state).lower() not in _TERMINAL for state in parent_tools):
        errors.append("parent has a non-terminal tool state")
    try:
        current_git_worktrees = _registered_git_worktree_paths(source_path)
    except ContractError as exc:
        unsupported.append(f"current Git worktree registry unavailable: {exc}")
        current_git_worktrees = set()
    for worker in workers:
        role = str(worker.get("role", ""))
        worker_id = str(worker.get("id", role))
        state = str(worker.get("state", "")).lower()
        if state not in _TERMINAL:
            errors.append(f"{role or 'unknown'} worker is not terminal: {state or 'missing state'}")
        if worker.get("returned") is not True:
            errors.append(f"{role or 'unknown'} worker has no native return")
        terminal_events = [
            event for event in observations.get("events", [])
            if isinstance(event, dict) and event.get("kind") == "worker_terminal" and str(event.get("worker", "")) == worker_id
        ]
        if not terminal_events:
            errors.append(f"native terminal event is absent for {role or worker_id}")
        tool_states = worker.get("tool_states")
        if not isinstance(tool_states, list) or not tool_states:
            unsupported.append(f"{role or worker_id} tool terminal states are unavailable")
        elif any(str(item).lower() not in _TERMINAL for item in tool_states):
            errors.append(f"{role or worker_id} has a non-terminal tool state")
        changed = set(str(item) for item in worker.get("changed_files", []))
        if role == "code" and changed != {"pricing.json"}:
            errors.append("code worker changed files are not pricing.json only")
        if role == "report" and any(not item.startswith("reports/") or ".." in Path(item).parts for item in changed):
            errors.append("report worker changed a non-report file")
        worktree_value = worker.get("worktree")
        if not worktree_value:
            unsupported.append(f"{role or 'unknown'} worker worktree path unavailable")
        else:
            worktree = _canonical(worktree_value)
            if registered and worktree not in registered_by_path:
                errors.append(f"{role or worker_id} worktree is not in the registered native worktree list")
            if worktree.exists():
                if current_git_worktrees and worktree not in current_git_worktrees:
                    errors.append(f"retained {role or worker_id} worktree is absent from current Git registry")
                retention = worker.get("retention", {})
                reason = str(retention.get("reason", "")).strip() if isinstance(retention, dict) else ""
                if not reason or str(retention.get("state", "")).lower() not in {"blocked", "active", "retained"}:
                    errors.append(f"{role or 'unknown'} worktree remains without justified retention")
                else:
                    unsupported.append(f"{role or 'unknown'} worktree retained: {reason}")
            else:
                if current_git_worktrees and worktree in current_git_worktrees:
                    errors.append(f"removed {role or worker_id} worktree remains in current Git registry")
                if registered and not any(_canonical(item.get("path", "")) == worktree and item.get("worker_id", item.get("id", "")) == worker_id for item in registered if isinstance(item, dict) and item.get("path")):
                    errors.append(f"{role or worker_id} removed path lacks registered worker identity")
                checks[f"{role}_worktree_removed"] = "PASS"
        declared_reports = worker.get("required_reports")
        index_ref = worker.get("handoff_index")
        if not isinstance(declared_reports, list) or not declared_reports or not index_ref or index_ref not in declared_reports:
            errors.append(f"{role or worker_id} lacks a non-empty required report list with handoff index")
            continue
        required = _required_report_paths(worker, inbox_path)
        if len(set(required)) < 2:
            errors.append(f"{role or worker_id} requires distinct handoff index and detail report files")
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            errors.append(f"{role or 'unknown'} durable reports missing: {', '.join(missing)}")
        else:
            checks[f"{role}_durable_reports"] = "PASS"
        archived_hashes = worker.get("report_sha256", {})
        for name, path in zip(declared_reports, required):
            if path.is_file() and archived_hashes.get(name) != _sha256_file(path):
                errors.append(f"{role or worker_id} durable report hash missing or mismatched: {name}")

    events = observations.get("events", [])
    if not isinstance(events, list):
        raise ContractError("observations.events must be a list")
    worker_keys = {str(item.get("id", item.get("role", ""))): item for item in workers}
    return_events = [
        (index, event)
        for index, event in enumerate(events)
        if isinstance(event, dict) and event.get("kind") == "worker_return"
    ]
    returned_ids = {str(event.get("worker", "")) for _, event in return_events}
    actual_returns = returned_ids & set(worker_keys)
    if returned_ids - set(worker_keys):
        errors.append("native return event names an unknown worker")
    for worker in workers:
        key = str(worker.get("id", worker.get("role", "")))
        if key not in actual_returns:
            errors.append(f"native return event is absent for {worker.get('role', key)}")
    final_events = [
        (index, event)
        for index, event in enumerate(events)
        if isinstance(event, dict) and event.get("kind") in {"parent_final", "parent_finish"}
    ]
    final_after_returns = True
    if len(final_events) > 1:
        errors.append("ambiguous duplicate native parent final events")
        final_after_returns = False
    if not final_events:
        errors.append("native parent final event is absent")
        final_after_returns = False
    else:
        final_position, final_event = final_events[-1]
        if final_event.get("status") not in {None, "completed", "finished", "finish", "stop"}:
            errors.append("native parent final event reports an unsuccessful state")
            final_after_returns = False
        final_time = _event_time(final_event, final_position)
        for index, event in return_events:
            if str(event.get("worker", "")) in actual_returns and (index >= final_position or _event_time(event, index) > final_time):
                errors.append("parent final/finish occurred before all worker returns")
                final_after_returns = False
        if len(actual_returns) != 2:
            errors.append("parent final does not follow both required worker returns")
            final_after_returns = False
    checks["parent_final_after_returns"] = "PASS" if final_after_returns else "FAIL"
    for worker in workers:
        key = str(worker.get("id", worker.get("role", "")))
        archive_events = [index for index, event in enumerate(events) if isinstance(event, dict) and event.get("kind") == "reports_archived" and str(event.get("worker", "")) == key]
        removal_events = [index for index, event in enumerate(events) if isinstance(event, dict) and event.get("kind") == "worktree_removed" and str(event.get("worker", "")) == key]
        worktree = _canonical(worker.get("worktree", "")) if worker.get("worktree") else None
        if worktree and not worktree.exists():
            if not archive_events:
                errors.append(f"{worker.get('role', key)} removal has no prior report-archival event")
            if not removal_events:
                errors.append(f"{worker.get('role', key)} worktree disappearance has no native removal event")
            if archive_events and removal_events and min(removal_events) <= min(archive_events):
                errors.append(f"{worker.get('role', key)} worktree was removed before report archival")
            required_kinds = ("worker_terminal", "worker_return", "reports_archived", "worktree_removed")
            per_worker = [[(index, event) for index, event in enumerate(events)
                           if event.get("kind") == kind and str(event.get("worker", "")) == key]
                          for kind in required_kinds]
            if all(per_worker) and final_events:
                ordered = [items[0] for items in per_worker] + [final_events[-1]]
                for (before_i, before), (after_i, after) in zip(ordered, ordered[1:]):
                    if before_i >= after_i or _event_time(before, before_i) > _event_time(after, after_i):
                        errors.append(f"{worker.get('role', key)} lifecycle events are out of order")
    if observations.get("parent_final_after_returns") is True and not return_events:
        unsupported.append("parent_final_after_returns boolean lacks native event provenance")
    if str(observations.get("parent_status", "")).lower() in {"finish", "stop"} and len(actual_returns) != 2:
        errors.append("finish/stop alone cannot complete W1 while a worker is pending")

    if errors:
        status = "FAILED" if any("unexpected" in error or "changed" in error or "pricing.json" in error or "removed before" in error for error in errors) else "INCOMPLETE"
    elif unsupported:
        status = "INCOMPLETE"
    elif all(str(item.get("state", "")).lower() == "completed" for item in workers):
        status = "COMPLETE"
    else:
        status = "INCOMPLETE"
    return {
        "schema": SCHEMA_VERDICT,
        "status": status,
        "checks": checks,
        "errors": errors,
        "unsupported_or_unobserved": unsupported,
        "provenance_note": "Normalized observations are checked for consistency; this helper cannot independently prove that a host boolean or self-reported receipt came from the native host.",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="No-model U18 W1 operator guards; never launches or removes workers.")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare", help="create the disposable dirty linked fixture")
    prepare_parser.add_argument("--run-dir", required=True)
    prepare_parser.add_argument("--prompt")
    prepare_parser.add_argument("--skill")
    prepare_parser.add_argument("--reference")
    snap_parser = sub.add_parser("snapshot", help="write a semantic Git/worktree snapshot")
    snap_parser.add_argument("--source", required=True)
    snap_parser.add_argument("--output", required=True)
    pre_parser = sub.add_parser("preflight", help="validate source, native launch paths, hashes, and baseline")
    pre_parser.add_argument("--source", required=True)
    pre_parser.add_argument("--manifest", required=True)
    pre_parser.add_argument("--parent-cwd", required=True)
    pre_parser.add_argument("--launch", required=True, help="JSON native observation file")
    pre_parser.add_argument("--prompt")
    pre_parser.add_argument("--skill")
    pre_parser.add_argument("--reference")
    public_parser = sub.add_parser("public-opencode", help="project whitelisted OpenCode SQLite records")
    public_parser.add_argument("--db", required=True)
    public_parser.add_argument("--session", required=True)
    public_parser.add_argument("--output", required=True)
    public_parser.add_argument("--source", required=True)
    public_parser.add_argument("--worktree", action="append", required=True, help="worker worktree; repeat for every worker")
    public_parser.add_argument("--inbox", required=True)
    complete_parser = sub.add_parser("complete", help="grade native observations and actual W1 filesystem")
    complete_parser.add_argument("--source", required=True)
    complete_parser.add_argument("--baseline", required=True)
    complete_parser.add_argument("--observations", required=True)
    complete_parser.add_argument("--inbox", required=True)
    complete_parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_fixture(args.run_dir, args.prompt, args.skill, args.reference)
        elif args.command == "snapshot":
            result = snapshot(args.source)
            _json_dump(result, _operator_output(args.output, [args.source, result["git_root"]]))
        elif args.command == "preflight":
            result = preflight(args.source, args.manifest, args.parent_cwd, _json_load(args.launch), prompt=args.prompt, skill=args.skill, reference=args.reference)
        elif args.command == "public-opencode":
            result = public_opencode(args.db, args.session, args.output, source=args.source, worktree=args.worktree, inbox=args.inbox)
        elif args.command == "complete":
            observations = _json_load(args.observations)
            result = complete_w1(args.source, args.baseline, observations, args.inbox)
            if args.output:
                worker_paths = [worker["worktree"] for worker in observations["workers"] if worker.get("worktree")]
                _json_dump(result, _operator_output(args.output, [args.source, args.inbox, *worker_paths]))
        else:  # pragma: no cover - argparse enforces this
            raise ContractError(f"unknown command: {args.command}")
        if args.command not in {"snapshot", "public-opencode"}:
            _json_dump(result)
        return 0 if result.get("status") in {None, "READY", "PROJECTED", "COMPLETE"} else 1
    except ContractError as exc:
        _json_dump({"schema": SCHEMA_VERDICT, "status": "FAILED", "errors": [str(exc)]})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
