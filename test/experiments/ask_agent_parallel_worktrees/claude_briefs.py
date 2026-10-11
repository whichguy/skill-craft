#!/usr/bin/env python3
"""Adapt common compact v4 worker assignments to Claude Code Agent arguments."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import briefs


class ClaudeBriefError(ValueError):
    pass


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()


def _write_json(path: Path, value) -> bytes:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _write_exclusive(path, payload)
    return payload


def _read_json(path: Path):
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ClaudeBriefError(f"Expected a regular non-symlink file: {source}")
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClaudeBriefError(f"Cannot read JSON {source}: {type(exc).__name__}: {exc}") from exc


def _failure_details(run):
    root = Path(run).expanduser().resolve()
    operator = root / "operator"
    native = operator / "claude-native"
    paths = {
        "run": root,
        "manifest": root / "manifest.json",
        "operator": operator,
        "common_dispatch_index": operator / "compact-dispatch" / "index.json",
        "claude_dispatch": operator / "claude-dispatch",
        "claude_dispatch_index": operator / "claude-dispatch" / "index.json",
        "operator_launch": operator / "launch.json",
        "settings": native / "settings.json",
        "hooks": native / "hooks",
    }
    return {
        "rationale_ref": "CONTRACT.md#claude-native-evidence",
        "evidence": {
            name: {"path": str(path), "exists": path.exists() or path.is_symlink()}
            for name, path in paths.items()
        },
        "recovery": (
            "Preserve this run and its attempt diagnostics; inspect the referenced evidence, "
            "then retry in a new run directory."
        ),
    }


def worker_prefix(worktree) -> str:
    root = Path(worktree)
    if not root.is_absolute():
        raise ClaudeBriefError(f"Claude worker worktree must be absolute: {worktree!r}")
    root = root.resolve()
    tick = chr(96)
    prefix = shlex.quote(str(root))
    return (
        "Claude Agent transport rules. The common compact v4 assignment follows exactly after this prefix; "
        "preserve and follow every task, binding, and fixture gate in it. Claude Agent has no cwd argument. "
        f"Every Bash tool invocation MUST start with {tick}cd {prefix} &&{tick}. "
        f"If an emitted wrapper command already starts with that exact prefix, run it unchanged. "
        f"For any other command, including task tests and each exact emitted commit-proof command, prepend "
        f"{tick}cd {prefix} && {tick}while keeping the remaining command unchanged. "
        "Use absolute paths for all file tools. Claude requires reading an existing file with Read "
        "before using Write or Edit on it. After worker-start, read and implement the owned file first; "
        "run the emitted task test only after the edit, not as a baseline against the unfinished stub. "
        "Do not create, call, or delegate to nested agents. "
        "Return the actual terminal result to the parent."
    )


def agent_arguments(common_arguments):
    expected = {"description", "prompt", "cwd", "background"}
    if not isinstance(common_arguments, dict) or set(common_arguments) != expected:
        raise ClaudeBriefError(
            f"Common compact arguments must have exactly {sorted(expected)}; "
            f"observed {sorted(common_arguments) if isinstance(common_arguments, dict) else type(common_arguments).__name__}"
        )
    if (not isinstance(common_arguments["description"], str)
            or not common_arguments["description"]
            or not isinstance(common_arguments["prompt"], str)
            or not common_arguments["prompt"]
            or common_arguments["background"] is not True):
        raise ClaudeBriefError("Common compact description, prompt, or background value is invalid")
    worktree = Path(common_arguments["cwd"])
    if not worktree.is_absolute():
        raise ClaudeBriefError(f"Common compact cwd is not absolute: {worktree}")
    return {
        "description": common_arguments["description"],
        "subagent_type": "general-purpose",
        "run_in_background": True,
        "prompt": worker_prefix(worktree) + "\n\n" + common_arguments["prompt"],
    }


def build_claude_briefs(run):
    """Call the shared compact brief builder, then freeze Claude-specific argument mappings."""
    run = Path(run).expanduser().resolve()
    operator = run / "operator"
    common_index_path = operator / "compact-dispatch" / "index.json"
    common_summary = briefs.build_compact_briefs(run)
    common_index = _read_json(common_index_path)
    if common_index.get("schema") != "ask-agent.compact-dispatch/v1":
        raise ClaudeBriefError(f"Unexpected common compact dispatch schema in {common_index_path}")
    manifest = _read_json(run / "manifest.json")
    worker_count = manifest.get("workers")
    expected_ids = [str(index) for index in range(1, worker_count + 1)] if type(worker_count) is int and worker_count > 0 else []
    common_rows = common_index.get("assignments")
    if not expected_ids or not isinstance(common_rows, list):
        raise ClaudeBriefError("Frozen manifest or common compact dispatch has invalid worker assignments")
    common_by_id = {}
    for row in common_rows:
        worker_id = str(row.get("worker_id")) if isinstance(row, dict) else None
        if worker_id in common_by_id:
            raise ClaudeBriefError(f"Duplicate common compact assignment for worker {worker_id}")
        common_by_id[worker_id] = row
    if list(common_by_id) != expected_ids:
        raise ClaudeBriefError(f"Common assignment order/IDs differ from manifest: {list(common_by_id)}")

    directory = operator / "claude-dispatch"
    directory.mkdir(parents=False, exist_ok=False)
    common_index_sha256 = _sha(common_index_path.read_bytes())
    assignments = []
    for worker_id in expected_ids:
        common_row = common_by_id[worker_id]
        source_path = Path(common_row.get("path", ""))
        source_bytes = source_path.read_bytes()
        if source_path.is_symlink() or _sha(source_bytes) != common_row.get("sha256"):
            raise ClaudeBriefError(f"Common compact assignment hash mismatch for worker {worker_id}")
        source_entry = briefs.emit_compact_worker(run, worker_id)
        source_prompt = source_entry.get("native_arguments", {}).get("prompt")
        if not isinstance(source_prompt, str):
            raise ClaudeBriefError(f"Common assignment has no prompt for worker {worker_id}")
        if source_entry.get("worker_id") != worker_id:
            raise ClaudeBriefError(f"Common emitted assignment ID mismatch for worker {worker_id}")
        source_prompt_bytes = source_prompt.encode("utf-8")
        arguments = agent_arguments(source_entry["native_arguments"])
        prompt_sha256 = _sha(arguments["prompt"].encode("utf-8"))
        payload = {
            "schema": "ask-agent.claude-dispatch-assignment/v1",
            "worker_id": worker_id,
            "source_assignment_path": str(source_path.resolve()),
            "source_assignment_sha256": common_row["sha256"],
            "source_prompt_sha256": _sha(source_prompt_bytes),
            "prompt_sha256": prompt_sha256,
            "agent_arguments": arguments,
        }
        assignment_path = directory / f"worker-{worker_id}.json"
        assignment_bytes = _write_json(assignment_path, payload)
        assignments.append({
            "worker_id": worker_id,
            "assignment_path": str(assignment_path.resolve()),
            "sha256": _sha(assignment_bytes),
            "source_assignment_path": str(source_path.resolve()),
            "source_assignment_sha256": common_row["sha256"],
            "source_prompt_sha256": payload["source_prompt_sha256"],
            "prompt_sha256": prompt_sha256,
        })

    manifest_bytes = (run / "manifest.json").read_bytes()
    index = {
        "schema": "ask-agent.claude-dispatch-index/v1",
        "run_id": manifest.get("run_id"),
        "manifest_sha256": _sha(manifest_bytes),
        "common_index_path": str(common_index_path.resolve()),
        "common_index_sha256": common_index_sha256,
        "assignments": assignments,
    }
    index_path = directory / "index.json"
    index_bytes = _write_json(index_path, index)
    return {
        "schema": "ask-agent.claude-dispatch-summary/v1",
        "status": "PREPARED",
        "run_id": index["run_id"],
        "worker_ids": expected_ids,
        "index_path": str(index_path.resolve()),
        "index_sha256": _sha(index_bytes),
        "common_summary": common_summary,
    }


def emit_claude_worker(run, worker_id):
    run = Path(run).expanduser().resolve()
    worker_id = str(worker_id)
    index_path = run / "operator" / "claude-dispatch" / "index.json"
    index = _read_json(index_path)
    if index.get("schema") != "ask-agent.claude-dispatch-index/v1":
        raise ClaudeBriefError(f"Unexpected Claude dispatch index schema: {index_path}")
    rows = [row for row in index.get("assignments", []) if row.get("worker_id") == worker_id]
    if len(rows) != 1:
        raise ClaudeBriefError(f"Expected one Claude assignment for worker {worker_id}; found {len(rows)}")
    row = rows[0]
    path = Path(row["assignment_path"])
    payload = path.read_bytes()
    if path.is_symlink() or _sha(payload) != row.get("sha256"):
        raise ClaudeBriefError(f"Claude assignment hash mismatch for worker {worker_id}")
    assignment = _read_json(path)
    if assignment.get("worker_id") != worker_id:
        raise ClaudeBriefError(f"Claude assignment file ID mismatch for worker {worker_id}")
    common = _read_json(assignment["source_assignment_path"])
    if (_sha(Path(assignment["source_assignment_path"]).read_bytes())
            != assignment.get("source_assignment_sha256")
            or common.get("worker_id") != worker_id):
        raise ClaudeBriefError(f"Source common assignment no longer matches worker {worker_id}")
    expected_arguments = agent_arguments(common.get("native_arguments"))
    if assignment.get("agent_arguments") != expected_arguments:
        raise ClaudeBriefError(f"Claude prompt mapping differs from the deterministic adapter for worker {worker_id}")
    prompt_hash = _sha(expected_arguments["prompt"].encode("utf-8"))
    if assignment.get("prompt_sha256") != prompt_hash or row.get("prompt_sha256") != prompt_hash:
        raise ClaudeBriefError(f"Transformed prompt hash mismatch for worker {worker_id}")
    return {
        "worker_id": worker_id,
        "agent_arguments": expected_arguments,
        "source_prompt_sha256": assignment["source_prompt_sha256"],
        "prompt_sha256": prompt_hash,
        "assignment_path": str(path.resolve()),
        "assignment_sha256": row["sha256"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--emit-worker", choices=("1", "2", "3", "4", "5"))
    args = parser.parse_args(argv)
    if args.compact == (args.emit_worker is not None):
        parser.error("choose exactly one of --compact or --emit-worker")
    try:
        result = (build_claude_briefs(args.run) if args.compact
                  else emit_claude_worker(args.run, args.emit_worker))
    except (OSError, KeyError, TypeError, ClaudeBriefError) as exc:
        print(json.dumps({
            "schema": "ask-agent.claude-brief-error/v1",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            **_failure_details(args.run),
        }, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
