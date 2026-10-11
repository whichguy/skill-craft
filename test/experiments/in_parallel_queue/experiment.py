#!/usr/bin/env python3
"""Prepare and audit offline evidence for a prompt-led native queue trial.

This apparatus never launches a model. The coordinator uses the selected
native agent tools; this CLI only creates the synthetic case and checks retained
evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


CASE_SCHEMA = "in-parallel-native-queue-case/v1"
AGGREGATE_SCHEMA = "in-parallel-native-queue-aggregate/v1"
SKILL_NAMES = ("in-parallel", "ask-agent", "plan-dispatcher")
DEFAULT_CAPACITY = 5
APPARATUS_REPO = Path(__file__).resolve().parents[3]
PROOF_SCOPE = {
    "oracle": {
        "separate_parent_side_file": True,
        "access_restricted": False,
        "non_reading_proven": False,
        "limitation": "The prompt instructs the coordinator not to read expected.json; shared-filesystem access is not blocked, so the audit cannot prove it remained unread.",
    },
    "fixture_git": {
        "checks": ["HEAD", "index bytes", "non-.git fixture file bytes", "git porcelain status"],
        "all_git_metadata_checked": False,
        "limitation": "Other .git metadata, such as config, refs, reflogs, and hooks, is outside this preservation check.",
    },
    "native_overlap": {
        "source": "typed native lifecycle events in the specified coordinator JSONL",
        "cpu_parallelism_proven": False,
        "speedup_proven": False,
    },
}


class ExperimentError(RuntimeError):
    """Invalid input or retained evidence that cannot support a verdict."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _write_json_new(path: Path, value: object) -> None:
    _write_new(path, _json_bytes(value))


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _read_json(path: Path) -> object:
    if path.is_symlink() or not path.is_file():
        raise ExperimentError(f"Expected a regular evidence file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExperimentError(f"Cannot read JSON evidence at {path}: {exc}") from exc


def _absolute(value: str, label: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ExperimentError(f"{label} must be an absolute path; received {value!r}")
    return path.resolve(strict=False)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _git(root: Path, *args: str) -> str:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1"}
    proc = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, env=env)
    if proc.returncode:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise ExperimentError(f"git {' '.join(args)} failed at {root}: {detail}")
    return proc.stdout.strip()


def _tree_pin(package: Path) -> dict:
    files: dict[str, str] = {}
    for path in sorted(package.rglob("*")):
        if path.is_symlink():
            raise ExperimentError(f"Selected skill package contains a symlink: {path}")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            files[str(path.relative_to(package))] = _sha(path.read_bytes())
    if "SKILL.md" not in files:
        raise ExperimentError(f"Selected skill package lacks SKILL.md: {package}")
    return {"root": str(package), "files": files, "tree_sha256": _sha(_canonical(files))}


def _selected_skills(skill_root: Path) -> dict:
    if not skill_root.is_dir():
        raise ExperimentError(f"--skill-root must be an existing skills directory: {skill_root}")
    selected = {}
    for name in SKILL_NAMES:
        package = skill_root / name
        if package.is_symlink() or not package.is_dir():
            raise ExperimentError(f"Selected skill package is missing or redirected: {package}")
        selected[name] = _tree_pin(package.resolve(strict=True))
    return selected


def _fixture_files(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path == root / ".git" or _is_within(path, root / ".git"):
            continue
        if path.is_symlink():
            raise ExperimentError(f"Synthetic source contains a symlink: {path}")
        if path.is_file():
            files[str(path.relative_to(root))] = _sha(path.read_bytes())
    return files


def _fixture_snapshot(root: Path) -> dict:
    index = root / ".git" / "index"
    if not index.is_file() or index.is_symlink():
        raise ExperimentError(f"Synthetic Git index is missing or redirected: {index}")
    return {
        "head": _git(root, "rev-parse", "HEAD"),
        "index_sha256": _sha(index.read_bytes()),
        "files": _fixture_files(root),
        "status": _git(root, "status", "--porcelain=v1", "--untracked-files=all"),
    }


def _formula(index: int) -> tuple[int, int]:
    return index + 1, 2 * index + 3


def _make_fixture(root: Path, task_count: int) -> dict:
    root.mkdir()
    (root / ".gitignore").write_text("__pycache__/\n*.py[cod]\n", encoding="utf-8")
    (root / ".claspignore").write_text("node_modules/\n", encoding="utf-8")
    modules = root / "modules"
    modules.mkdir()
    (modules / "README.md").write_text("Synthetic independent report-only tasks.\n", encoding="utf-8")
    expected_modules = []
    for index in range(1, task_count + 1):
        a, b = _formula(index)
        relative = f"modules/module_{index:02}.py"
        (root / relative).write_text(
            f'"""Synthetic deterministic module {index:02}."""\n\n'
            f"def transform(value):\n    return value * {a} + {b}\n",
            encoding="utf-8",
        )
        expected_modules.append({
            "module": relative,
            "a": a,
            "b": b,
            "zero": b,
            "four": 4 * a + b,
        })

    _git(root, "init", "-q")
    _git(root, "config", "--local", "user.name", "Queue Experiment Fixture")
    _git(root, "config", "--local", "user.email", "queue-fixture.invalid")
    _git(root, "add", "--", ".gitignore", ".claspignore", "modules")
    _git(root, "commit", "-qm", "synthetic queue fixture baseline")
    snapshot = _fixture_snapshot(root)
    if snapshot["status"]:
        raise ExperimentError(f"Synthetic fixture is unexpectedly dirty after its baseline commit: {snapshot['status']}")
    return {"baseline": snapshot, "modules": expected_modules}


def _prompt(case_dir: Path, fixture: Path, task_count: int, capacity: int,
            capacity_explicit: bool, skills: dict) -> str:
    skill_lines = "\n".join(
        f"- {name}: {pin['root']}/SKILL.md" for name, pin in skills.items()
    )
    cap_text = (f"Request at most {capacity} concurrent workers from the Dispatcher."
                if capacity_explicit else
                f"Omit capacity entirely from the in-parallel request and use the selected skill's default. "
                f"For this case, record its normalized effective capacity as {capacity} in the aggregate.")
    return f"""# Goal

Use the selected `in-parallel` skill to complete one goal by discovering and
reporting every independent Python module under `{fixture}/modules/`. There are
{task_count} module files. Read their implementations, then create exactly one
report-only task per discovered module. Each task must report that module's
`transform(value) = a * value + b`, plus its results at 0 and 4. Return a
human-readable table and the sums of `a`, `b`, `transform(0)`, and
`transform(4)` across all modules.

Plan the complete finite module set first. Let the single Dispatcher remain the
queue authority: pull and prepare only currently eligible items, up to the
effective capacity; when a worker completes, refill that freed slot until the
queue is empty. Launch one fresh native agent context for every item. Do not
reuse a worker pool, create a second coordinator, or impose a batch barrier.

# Run conditions

Read the selected skills below, including their relevant references, and use
their current native lifecycle. The coordinator is the only dispatcher and the
only coordinator. Use fresh native workers for queued tasks; workers do not
delegate or resume other workers. Keep the entire run in the current workspace,
use `report-only` with empty write sets, and fully drain the queue through the
same Dispatcher run. {cap_text} The task count exceeds the worker capacity, so
continue until every module has an accepted result. Do not edit the synthetic
repository or its Git metadata. Avoid Python bytecode side effects: use `python3 -B`,
`PYTHONDONTWRITEBYTECODE=1`, or `sys.dont_write_bytecode = True` for any Python
probe so no `__pycache__` files appear. Carry this requirement into
every generated task objective/current_learnings. Prefer AST inspection; if a
module must be executed, run it with bytecode writing disabled and keep any
evidence outside the synthetic repository. No model launcher is part of this
experiment.

Selected skills:
{skill_lines}

Synthetic source: `{fixture}`
Coordinator evidence directory: `{case_dir}/coordinator`
Parent verification oracle: `{case_dir}/expected.json`. It is a separate file,
not access-controlled from the coordinator. Do not open, search, or copy it;
the offline audit cannot prove that it remained unread.

# Retained aggregate contract

Write `{case_dir}/coordinator/aggregate.json` as UTF-8 JSON with this exact
shape (replace examples with observed values; keep every required field):

```json
{{
  "schema": "{AGGREGATE_SCHEMA}",
  "request": {{
    "task_count": {task_count}, "capacity": {capacity},
    "mode": "report-only", "workspace": "current",
    "tasks": [{{"task_id": "actual-dispatcher-task-id", "module": "modules/module_XX.py"}}]
  }},
  "run": {{
    "status": "SUCCEEDED", "mode": "report-only", "workspace": "current",
    "final_run_path": "/absolute/path/to/the/harness/run-root"
  }},
  "tasks": [{{
    "task_id": "actual-dispatcher-task-id", "attempt_id": "actual-attempt-id",
    "native_handle": "actual-native-agent-path",
    "module": "modules/module_XX.py", "a": 0, "b": 0,
    "zero": 0, "four": 0, "state": "accepted",
    "evidence": {{
      "packet": {{"state": "prepared", "task_id": "actual-dispatcher-task-id", "attempt_id": "actual-attempt-id", "native_handle": "actual-native-agent-path", "locator": "/absolute/harness-run-root/packets/actual-attempt-id.json", "sha256": "..."}},
      "collected": {{"state": "collected", "task_id": "actual-dispatcher-task-id", "attempt_id": "actual-attempt-id", "native_handle": "actual-native-agent-path", "locator": "/absolute/harness-run-root/collected/actual-attempt-id.json", "sha256": "..."}},
      "verified": {{"state": "verified", "task_id": "actual-dispatcher-task-id", "attempt_id": "actual-attempt-id", "native_handle": "actual-native-agent-path", "locator": "/absolute/harness-run-root/verified/actual-attempt-id.json", "sha256": "..."}}
    }},
    "raw_result_path": "/absolute/coordinator/raw-results/actual-task-id.json",
    "raw_result_sha256": "..."
  }}],
  "totals": {{"a": 0, "b": 0, "zero": 0, "four": 0}},
  "diagnostics": []
}}
```

The JSON zeros and `XX` values above are type/shape placeholders, not expected
module values. Replace them with observed values, and list all tasks in
`request.tasks` and `tasks`, one each. For the default-capacity case, `request.capacity`
records the helper's normalized effective default even though the actual
in-parallel request omitted capacity; for the explicit case, it records the
requested bound. `final_run_path` is the harness run root, containing
`run.json`, `result.json`, `packets/`, `collected/`, `verified/`, and `dispatcher/`.
Choose a unique task ID for every module; aggregate IDs must match the IDs in
`run.json`. Native worker names are independent of task IDs; each aggregate
native handle must match the typed native lifecycle and the collected result.
The module field must enumerate the exact discovered module set. Point packet,
collected, and verified records at the actual files
under this harness run root. This case pins
`result_evidence_role=coordinator-response`, so point `raw_result_path` at the
actual worker response file under `coordinator/raw-results/`. The Dispatcher inbox
separately pins its accepted result at
`dispatcher/artifacts/<attempt>/result.json`. The verifier's actual `passed`, `reason`, and nonempty
`evidence` list are required; every evidence path/hash must resolve to retained
bytes. Preserve raw worker responses separately and pin each at
`raw_result_path`/`raw_result_sha256`. The offline auditor opens the packet,
collected record, verifier record, every pinned verifier evidence file,
Dispatcher inbox, accepted Dispatcher result, and raw worker result, then joins
each attempt to its task, module, and native handle; evidence wrapper labels
alone are insufficient. Filesystem verification is checked in the collected record's
`verified.workspace_evidence` status and verdict.
Preserve any diagnostic files under
`coordinator/diagnostics/` and reference each in the aggregate with its
absolute `path` and `sha256`. Include a concise `summary` when the retained
diagnostic has one; do not invent one. A missing
result, duplicate, retry ambiguity, rejected task, or incomplete run must stay
visible as a failure; do not report success. Do not include unrelated rollout
history or encrypted messages in retained evidence.
"""


def prepare_case(case_arg: str, skill_root_arg: str, task_count: int,
                 requested_capacity: int | None) -> dict:
    if type(task_count) is not int or task_count < 2:
        raise ExperimentError("--tasks must be an integer of at least 2")
    if requested_capacity is not None and (type(requested_capacity) is not int or requested_capacity < 1):
        raise ExperimentError("--capacity must be a positive integer")
    skill_root = _absolute(skill_root_arg, "--skill-root")
    if not skill_root.is_dir():
        raise ExperimentError(f"--skill-root is not a directory: {skill_root}")
    repo_root_text = _git(skill_root, "rev-parse", "--show-toplevel")
    repo_root = Path(repo_root_text).resolve(strict=True)
    case_dir = _absolute(case_arg, "--case")
    if case_dir.exists() or case_dir.is_symlink():
        raise ExperimentError(f"--case must name a new output directory; already exists: {case_dir}")
    if not case_dir.parent.is_dir():
        raise ExperimentError(f"--case parent directory must already exist: {case_dir.parent}")
    if _is_within(case_dir, skill_root) or _is_within(case_dir, repo_root):
        raise ExperimentError(
            f"--case must be external to the selected skill source and its Git checkout; "
            f"skill-root={skill_root}, repository={repo_root}, case={case_dir}"
        )
    capacity = requested_capacity if requested_capacity is not None else min(DEFAULT_CAPACITY, task_count)
    if capacity >= task_count:
        raise ExperimentError(
            f"--tasks must exceed effective worker capacity to exercise queue refill; "
            f"tasks={task_count}, capacity={capacity}"
        )
    selected = _selected_skills(skill_root)

    case_dir.mkdir()
    try:
        fixture = case_dir / "fixture"
        made = _make_fixture(fixture, task_count)
        expected = {
            "schema": "in-parallel-native-queue-oracle/v1",
            "case_id": str(uuid.uuid4()),
            "modules": made["modules"],
            "totals": {key: sum(row[key] for row in made["modules"])
                       for key in ("a", "b", "zero", "four")},
        }
        prompt = _prompt(case_dir, fixture, task_count, capacity,
                         requested_capacity is not None, selected)
        prompt_bytes = prompt.encode("utf-8")
        case = {
            "schema": CASE_SCHEMA,
            "case_id": expected["case_id"],
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "configuration": {
                "task_count": task_count,
                "requested_capacity": requested_capacity,
                "capacity_explicit": requested_capacity is not None,
                "effective_capacity": capacity,
                "result_evidence_role": "coordinator-response",
                "mode": "report-only",
                "workspace": "current",
            },
            "prompt_sha256": _sha(prompt_bytes),
            "oracle_sha256": _sha(_json_bytes(expected)),
            "source": {
                "skill_root": str(skill_root),
                "repository_root": str(repo_root),
                "skills": selected,
                "fixture_root": str(fixture),
                **made["baseline"],
            },
        }
        case["integrity_sha256"] = _sha(_canonical(case))
        _write_new(case_dir / "expected.json", _json_bytes(expected))
        _write_json_new(case_dir / "case.json", case)
        (case_dir / "case.json").chmod(0o444)
        _write_new(case_dir / "prompt.txt", prompt_bytes)
        return {
            "status": "PREPARED",
            "case": str(case_dir),
            "case_file": str(case_dir / "case.json"),
            "prompt_file": str(case_dir / "prompt.txt"),
            "fixture": str(fixture),
            "expected_capacity": capacity,
            "result_evidence_role": "coordinator-response",
            "expected_tasks": task_count,
            "case_id": expected["case_id"],
        }
    except Exception:
        # The directory was created exclusively by this invocation. Do not leave
        # a partial case that could be mistaken for a prepared experiment.
        import shutil
        shutil.rmtree(case_dir, ignore_errors=True)
        raise


def _require_object(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ExperimentError(f"{label} must be a JSON object")
    return value


def _require_int(value: object, label: str) -> int:
    if type(value) is not int:
        raise ExperimentError(f"{label} must be an integer")
    return value


def _timestamp(value: object, label: str) -> tuple[float, str]:
    if not isinstance(value, str) or not value:
        raise ExperimentError(f"{label} is missing an ISO-8601 outer timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExperimentError(f"{label} has an invalid ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ExperimentError(f"{label} timestamp must include a UTC offset: {value!r}")
    return parsed.timestamp(), value


def audit_native_rollout(rollout_arg: str, task_count: int, capacity: int) -> dict:
    """Prove direct native starts, completions, overlap, and fresh spawn inputs.

    Only typed Codex event fields are retained. Function-call arguments are
    parsed solely for task_name and fork_turns; their message field is never
    read, copied, or emitted.
    """
    rollout = _absolute(rollout_arg, "--coordinator-rollout")
    if rollout.is_symlink() or not rollout.is_file():
        raise ExperimentError(f"Coordinator rollout must be a regular JSONL file: {rollout}")
    snapshot = rollout.read_bytes()
    snapshot_sha256 = _sha(snapshot)
    starts = []
    completions = []
    spawns = []
    forbidden = []
    task_started = []
    task_complete = []
    final_messages = []
    root_threads = set()
    root_turns = set()

    for line_number, raw_line in enumerate(snapshot.splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ExperimentError(f"Coordinator rollout has invalid JSON at line {line_number}: {exc}") from exc
        if not isinstance(record, dict):
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        kind = record.get("type")
        if kind == "event_msg":
            item = payload.get("item")
            if payload.get("type") == "item_completed" and isinstance(item, dict):
                if item.get("type") == "SubAgentActivity" and item.get("kind") in {"started", "completed"}:
                    thread_id = payload.get("thread_id")
                    turn_id = payload.get("turn_id")
                    if not isinstance(thread_id, str) or not thread_id:
                        raise ExperimentError(f"Native child event at line {line_number} lacks payload.thread_id")
                    root_threads.add(thread_id)
                    if isinstance(turn_id, str) and turn_id:
                        root_turns.add(turn_id)
                    event = {
                        "line": line_number,
                        "timestamp": record.get("timestamp"),
                        "kind": item.get("kind"),
                        "id": item.get("id"),
                        "turn_id": payload.get("turn_id"),
                        "agent_thread_id": item.get("agent_thread_id"),
                        "agent_path": item.get("agent_path"),
                        "thread_id": thread_id,
                    }
                    if item["kind"] == "started":
                        starts.append(event)
                    else:
                        completions.append(event)
                elif item.get("type") == "AgentMessage" and item.get("phase") == "final_answer":
                    final_messages.append({
                        "line": line_number,
                        "timestamp": record.get("timestamp"),
                        "id": item.get("id"),
                        "thread_id": payload.get("thread_id"),
                        "turn_id": payload.get("turn_id"),
                    })
            elif payload.get("type") == "task_started":
                task_started.append({"line": line_number, "timestamp": record.get("timestamp"),
                                     "thread_id": payload.get("thread_id"), "turn_id": payload.get("turn_id")})
            elif payload.get("type") == "task_complete":
                task_complete.append({"line": line_number, "timestamp": record.get("timestamp"),
                                      "root_turn_id": payload.get("root_turn_id"),
                                      "turn_id": payload.get("turn_id")})
        elif kind == "response_item" and payload.get("type") == "function_call":
            namespace, name = payload.get("namespace"), payload.get("name")
            if namespace == "collaboration" and name in {"followup_task", "resume_agent", "resume", "resume_thread"}:
                forbidden.append({"line": line_number, "name": name, "namespace": namespace})
            if namespace == "collaboration" and name == "spawn_agent":
                call_id = payload.get("call_id")
                raw_arguments = payload.get("arguments")
                if not isinstance(raw_arguments, str):
                    raise ExperimentError(f"spawn_agent arguments at line {line_number} are not a JSON string")
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError as exc:
                    raise ExperimentError(f"spawn_agent arguments at line {line_number} are invalid JSON") from exc
                if not isinstance(arguments, dict):
                    raise ExperimentError(f"spawn_agent arguments at line {line_number} must decode to an object")
                # Deliberately inspect only these non-message fields.
                spawns.append({
                    "line": line_number,
                    "call_id": call_id,
                    "task_name": arguments.get("task_name"),
                    "fork_turns": arguments.get("fork_turns"),
                })

    errors = []
    if len(root_threads) != 1:
        errors.append(f"expected one coordinator payload.thread_id, found {len(root_threads)}")
    coordinator_thread_id = next(iter(root_threads)) if len(root_threads) == 1 else None
    if len(root_turns) != 1:
        errors.append(f"expected one coordinator payload.turn_id across native child events, found {len(root_turns)}")
    coordinator_turn_id = next(iter(root_turns)) if len(root_turns) == 1 else None
    if len(task_started) != 1:
        errors.append(f"expected one coordinator task_started event, found {len(task_started)}")
    if len(task_complete) != 1:
        errors.append(f"expected one coordinator task_complete event, found {len(task_complete)}")
    if task_started and coordinator_thread_id and task_started[0].get("thread_id") not in (None, coordinator_thread_id):
        errors.append("coordinator task_started payload.thread_id differs from native child events")
    if task_started and coordinator_turn_id and task_started[0].get("turn_id") not in (None, coordinator_turn_id):
        errors.append("coordinator task_started payload.turn_id differs from native child events")
    if forbidden:
        errors.append("coordinator used followup_task/resume; every queue action must be a fresh spawn")
    if len(spawns) != task_count:
        errors.append(f"expected {task_count} spawn_agent calls, found {len(spawns)}")
    call_ids = [spawn.get("call_id") for spawn in spawns]
    valid_call_ids = [value for value in call_ids if isinstance(value, str) and value]
    if len(valid_call_ids) != len(call_ids) or len(set(valid_call_ids)) != len(valid_call_ids):
        errors.append("spawn_agent call_id values are missing or duplicated")
    task_names = [spawn.get("task_name") for spawn in spawns]
    valid_task_names = [value for value in task_names if isinstance(value, str) and value]
    if len(valid_task_names) != len(task_names) or len(set(valid_task_names)) != len(valid_task_names):
        errors.append("spawn_agent task_name values are missing or duplicated")
    if any(spawn.get("fork_turns") != "none" for spawn in spawns):
        errors.append("every native queue action must set fork_turns to none")
    if len(starts) != task_count:
        errors.append(f"expected {task_count} typed native started events, found {len(starts)}")
    if len(completions) != task_count:
        errors.append(f"expected {task_count} typed native completed events, found {len(completions)}")

    spawn_by_call = {spawn["call_id"]: spawn for spawn in spawns
                     if isinstance(spawn.get("call_id"), str) and spawn["call_id"]}
    start_by_child = {}
    started_call_ids = []
    for event in starts:
        call_id = event.get("id")
        child_id, path = event.get("agent_thread_id"), event.get("agent_path")
        if not isinstance(call_id, str) or not call_id:
            errors.append(f"started child at line {event['line']} has a missing spawn call ID")
        elif call_id not in spawn_by_call:
            errors.append(f"started child at line {event['line']} has no matching spawn_agent call_id")
        started_call_ids.append(call_id if isinstance(call_id, str) and call_id else None)
        if not isinstance(child_id, str) or not child_id or not isinstance(path, str) or not path:
            errors.append(f"started child at line {event['line']} lacks agent_thread_id or agent_path")
            continue
        if child_id in start_by_child:
            errors.append(f"native child thread was started more than once: {child_id}")
        start_by_child[child_id] = event
        if coordinator_thread_id and event.get("thread_id") != coordinator_thread_id:
            errors.append(f"started child at line {event['line']} belongs to a different coordinator")
    if (len(set(started_call_ids)) != len(started_call_ids)
            or set(started_call_ids) != set(valid_call_ids)):
        errors.append("every spawn_agent call_id must join exactly one typed native started event")

    completion_by_child = {}
    completion_ids = set()
    for event in completions:
        child_id = event.get("agent_thread_id")
        if not isinstance(child_id, str) or not child_id:
            errors.append(f"completed child at line {event['line']} lacks agent_thread_id")
            continue
        if child_id in completion_by_child:
            errors.append(f"native child thread completed more than once: {child_id}")
        completion_by_child[child_id] = event
        event_id = event.get("id")
        if (not isinstance(event_id, str) or not event_id.startswith("subagent-completed-")
                or not event_id.removeprefix("subagent-completed-")):
            errors.append(f"completed child at line {event['line']} has a malformed lifecycle event ID")
        elif event_id in completion_ids:
            errors.append(f"native child completion event ID is duplicated: {event_id}")
        else:
            completion_ids.add(event_id)
        if coordinator_thread_id and event.get("thread_id") != coordinator_thread_id:
            errors.append(f"completed child at line {event['line']} belongs to a different coordinator")
    if set(start_by_child) != set(completion_by_child):
        missing = sorted(set(start_by_child) - set(completion_by_child))
        extra = sorted(set(completion_by_child) - set(start_by_child))
        errors.append(f"native start/completion IDs do not join; missing completions={missing}, extra completions={extra}")
    children = []
    intervals = []
    for child_id, start in start_by_child.items():
        finish = completion_by_child.get(child_id)
        if finish is None:
            continue
        if start.get("agent_path") != finish.get("agent_path"):
            errors.append(f"native child path changed across lifecycle for {child_id}")
        if start.get("id") not in spawn_by_call:
            errors.append(f"native child start event ID does not join a spawn call for {child_id}")
        try:
            start_epoch, start_at = _timestamp(start.get("timestamp"), f"started child line {start['line']}")
            finish_epoch, finish_at = _timestamp(finish.get("timestamp"), f"completed child line {finish['line']}")
        except ExperimentError as exc:
            errors.append(str(exc))
            continue
        if finish_epoch < start_epoch or finish["line"] <= start["line"]:
            errors.append(f"native child {child_id} completion precedes its recorded start")
        # Equal timestamps do not erase the journal's ordering. A new start
        # recorded before a completion still consumes a concurrent slot.
        intervals.append((start_epoch, start["line"], "start", child_id))
        intervals.append((finish_epoch, finish["line"], "finish", child_id))
        spawn = spawn_by_call.get(start.get("id"), {})
        children.append({
            "spawn_call_id": start.get("id"),
            "task_name": spawn.get("task_name"),
            "fork_turns": spawn.get("fork_turns"),
            "agent_thread_id": child_id,
            "agent_path": start.get("agent_path"),
            "completion_event_id": finish.get("id"),
            "started": {"line": start["line"], "timestamp": start_at},
            "completed": {"line": finish["line"], "timestamp": finish_at},
        })

    active = set()
    peak = 0
    for _, line_number, event_kind, child_id in sorted(intervals, key=lambda item: (item[0], item[1])):
        if event_kind == "finish":
            if child_id not in active:
                errors.append(f"completion for inactive native child {child_id}")
            active.discard(child_id)
        else:
            if child_id in active:
                errors.append(f"native child started while already active: {child_id}")
            active.add(child_id)
            peak = max(peak, len(active))
    if active:
        errors.append(f"native children remain active at end of journal: {sorted(active)}")
    if peak > capacity:
        errors.append(f"observed native peak {peak} exceeds expected capacity {capacity}")

    latest_finish = max((row[0] for row in intervals if row[2] == "finish"), default=None)
    for message in final_messages:
        try:
            message_epoch, _ = _timestamp(message.get("timestamp"), f"final answer line {message['line']}")
            if latest_finish is not None and message_epoch < latest_finish:
                errors.append(f"coordinator emitted final answer at line {message['line']} before all native children completed")
        except ExperimentError as exc:
            errors.append(str(exc))
        if coordinator_thread_id and message.get("thread_id") != coordinator_thread_id:
            errors.append(f"final answer at line {message['line']} belongs to a different thread")
    if not final_messages:
        errors.append("coordinator rollout has no typed AgentMessage final_answer event")
    terminal_evidence = None
    if task_complete:
        terminal = task_complete[0]
        try:
            terminal_epoch, terminal_at = _timestamp(terminal.get("timestamp"), f"task_complete line {terminal['line']}")
            if latest_finish is not None and terminal_epoch < latest_finish:
                errors.append("coordinator task_complete occurred before every native child completed")
        except ExperimentError as exc:
            errors.append(str(exc))
            terminal_epoch, terminal_at = None, terminal.get("timestamp")
        if final_messages and terminal.get("turn_id") not in {message.get("turn_id") for message in final_messages}:
            errors.append("coordinator task_complete turn_id does not join its final answer event")
        if coordinator_turn_id and terminal.get("turn_id") not in (None, coordinator_turn_id):
            errors.append("coordinator task_complete turn_id differs from native child events")
        terminal_evidence = {"line": terminal["line"], "timestamp": terminal_at,
                             "turn_id": terminal.get("turn_id"),
                             "all_children_completed_before_terminal": terminal_epoch is not None and latest_finish is not None and terminal_epoch >= latest_finish}

    if errors:
        raise ExperimentError("Native rollout audit failed: " + "; ".join(errors))
    return {
        "status": "PASS",
        "snapshot_sha256": snapshot_sha256,
        "coordinator_thread_id": coordinator_thread_id,
        "coordinator_turn_id": coordinator_turn_id,
        "capacity": capacity,
        "native_child_count": len(children),
        "peak_active_children": peak,
        "children": sorted(children, key=lambda child: child["started"]["line"]),
        "terminal": terminal_evidence,
    }


def _regular_artifact(locator: object, expected_sha: object, label: str,
                      repo_root: Path) -> tuple[Path, dict]:
    if not isinstance(locator, str) or not Path(locator).is_absolute():
        raise ExperimentError(f"{label}.locator must be an absolute path")
    path = Path(locator)
    if path.is_symlink() or not path.is_file():
        raise ExperimentError(f"{label} is missing or redirected: {path}")
    if _is_within(path.resolve(), repo_root):
        raise ExperimentError(f"{label} must be retained outside the source checkout: {path}")
    digest = _sha(path.read_bytes())
    if not isinstance(expected_sha, str) or digest != expected_sha:
        raise ExperimentError(f"{label} SHA-256 does not match its retained bytes: {path}")
    return path.resolve(), {"locator": str(path.resolve()), "sha256": digest}


def _json_artifact(locator: object, expected_sha: object, label: str,
                   repo_root: Path) -> tuple[dict, dict]:
    path, retained = _regular_artifact(locator, expected_sha, label, repo_root)
    return _require_object(_read_json(path), label), retained


def _artifact_evidence(evidence: dict, name: str, task_id: str, attempt_id: str,
                       native_handle: str, state: str, expected_path: Path,
                       repo_root: Path) -> tuple[dict, dict]:
    item = _require_object(evidence.get(name), f"task {task_id}.evidence.{name}")
    for key, want in (("state", state), ("task_id", task_id),
                      ("attempt_id", attempt_id), ("native_handle", native_handle)):
        if item.get(key) != want:
            raise ExperimentError(f"aggregate task {task_id} evidence {name}.{key} must match {want!r}")
    path, retained = _regular_artifact(item.get("locator"), item.get("sha256"),
                                       f"task {task_id} {name} evidence", repo_root)
    if path != expected_path.resolve():
        raise ExperimentError(f"task {task_id} {name} evidence must reference its actual harness artifact: {expected_path}")
    actual = _require_object(_read_json(path), f"task {task_id} actual {name} artifact")
    return actual, retained


def validate_aggregate(aggregate: object, expected: dict, capacity: int,
                       result_evidence_role: str,
                       repo_root: Path, fixture_root: Path,
                       coordinator_root: Path, children: list[dict]) -> dict:
    if result_evidence_role not in {"coordinator-response", "dispatcher-artifact"}:
        raise ExperimentError(f"unsupported result evidence role: {result_evidence_role!r}")
    aggregate = _require_object(aggregate, "aggregate")
    if aggregate.get("schema") != AGGREGATE_SCHEMA:
        raise ExperimentError(f"aggregate.schema must be {AGGREGATE_SCHEMA}")
    request = _require_object(aggregate.get("request"), "aggregate.request")
    expected_tasks = expected["modules"]
    task_count = len(expected_tasks)
    for key, want in (("task_count", task_count), ("capacity", capacity),
                      ("mode", "report-only"), ("workspace", "current")):
        if request.get(key) != want:
            raise ExperimentError(f"aggregate.request.{key} must be {want!r}; found {request.get(key)!r}")
    request_tasks = request.get("tasks")
    if not isinstance(request_tasks, list) or len(request_tasks) != task_count:
        raise ExperimentError(f"aggregate.request.tasks must contain exactly {task_count} tasks")
    expected_by_module = {row["module"]: row for row in expected_tasks}
    task_id_by_module = {}
    request_map = {}
    for row in request_tasks:
        row = _require_object(row, "aggregate.request.tasks[]")
        task_id, module = row.get("task_id"), row.get("module")
        if not isinstance(task_id, str) or not isinstance(module, str):
            raise ExperimentError("aggregate.request.tasks[] must have string task_id and module fields")
        if task_id in request_map:
            raise ExperimentError(f"duplicate request task_id: {task_id!r}")
        if module not in expected_by_module:
            raise ExperimentError(f"aggregate request has unexpected module: {module!r}")
        if module in task_id_by_module:
            raise ExperimentError(f"aggregate request duplicates module: {module!r}")
        request_map[task_id] = module
        task_id_by_module[module] = task_id
    if set(request_map.values()) != set(expected_by_module):
        raise ExperimentError("aggregate.request.tasks does not list each expected module exactly once")

    run = _require_object(aggregate.get("run"), "aggregate.run")
    for key, want in (("status", "SUCCEEDED"), ("mode", "report-only"), ("workspace", "current")):
        if run.get(key) != want:
            raise ExperimentError(f"aggregate.run.{key} must be {want!r}; found {run.get(key)!r}")
    final_path = run.get("final_run_path")
    if not isinstance(final_path, str) or not Path(final_path).is_absolute():
        raise ExperimentError("aggregate.run.final_run_path must be an absolute path")
    final_run_path = Path(final_path)
    if final_run_path.is_symlink() or not final_run_path.is_dir():
        raise ExperimentError(f"aggregate final harness run root is missing or redirected: {final_run_path}")
    if _is_within(final_run_path.resolve(), repo_root):
        raise ExperimentError("aggregate final harness run root must be external to the source checkout")

    run_manifest_path = final_run_path / "run.json"
    result_manifest_path = final_run_path / "result.json"
    run_manifest = _require_object(_read_json(run_manifest_path), "harness run.json")
    result_manifest = _require_object(_read_json(result_manifest_path), "harness result.json")
    run_request = _require_object(run_manifest.get("request"), "harness run.json.request")
    for key, want in (("capacity", capacity), ("mode", "report-only"), ("workspace", "current")):
        if run_request.get(key) != want:
            raise ExperimentError(f"harness run.json.request.{key} must be {want!r}")
    if run_manifest.get("schema") != "agent-harness/v1":
        raise ExperimentError("harness run.json.schema must be agent-harness/v1")
    if result_manifest.get("status") != "SUCCEEDED" or result_manifest.get("run") != str(final_run_path.resolve()):
        raise ExperimentError("harness result.json must report SUCCEEDED for this exact run root")
    if result_manifest.get("schema") != "agent-harness.delivery.v1":
        raise ExperimentError("harness result.json.schema must be agent-harness.delivery.v1")
    integration = _require_object(result_manifest.get("integration"), "harness result.json.integration")
    if integration.get("application_attempted") is not False:
        raise ExperimentError("harness result.json.integration.application_attempted must be false for report-only")
    if integration.get("applied_paths") != []:
        raise ExperimentError("harness result.json.integration.applied_paths must be empty for report-only")
    run_tasks = run_request.get("tasks")
    if not isinstance(run_tasks, list) or len(run_tasks) != task_count:
        raise ExperimentError("harness run.json.request.tasks must contain the exact task count")
    run_task_map = {}
    for task in run_tasks:
        task = _require_object(task, "harness run.json.request.tasks[]")
        task_id, objective = task.get("id"), task.get("objective")
        if not isinstance(task_id, str) or not task_id or not isinstance(objective, str):
            raise ExperimentError("harness run request task needs string id and objective")
        if task_id in run_task_map:
            raise ExperimentError(f"harness run request duplicates task id: {task_id!r}")
        write_set = task.get("write_set")
        if not isinstance(write_set, list) or write_set:
            raise ExperimentError(f"harness run request task {task_id!r} must have an empty write_set")
        run_task_map[task_id] = objective
    if set(run_task_map) != set(request_map):
        raise ExperimentError("aggregate task IDs do not match the actual harness run request IDs")
    for task_id, module in request_map.items():
        if module not in run_task_map[task_id]:
            raise ExperimentError(f"harness run request task {task_id!r} objective does not identify {module!r}")
    worker_rows = result_manifest.get("workers")
    if not isinstance(worker_rows, list) or len(worker_rows) != task_count:
        raise ExperimentError("harness result.json.workers must contain the exact task count")
    worker_map = {}
    for worker in worker_rows:
        worker = _require_object(worker, "harness result.json.workers[]")
        worker_id = worker.get("id")
        if not isinstance(worker_id, str) or worker_id in worker_map:
            raise ExperimentError("harness result.json has a missing or duplicate worker task ID")
        worker_map[worker_id] = worker
    if set(worker_map) != set(request_map):
        raise ExperimentError("harness result.json worker IDs do not match its request")
    native_handles = set()
    for child in children:
        handle = child.get("agent_path")
        if not isinstance(handle, str) or not handle or handle in native_handles:
            raise ExperimentError("native child agent_path values must be unique non-empty strings")
        native_handles.add(handle)
    if len(native_handles) != task_count:
        raise ExperimentError("typed native child paths must contain exactly one child per task")

    rows = aggregate.get("tasks")
    if not isinstance(rows, list) or len(rows) != task_count:
        raise ExperimentError(f"aggregate.tasks must contain exactly {task_count} rows")
    expected_by_id = {task_id: expected_by_module[module] for task_id, module in request_map.items()}
    seen_ids, seen_attempts, seen_handles = set(), set(), set()
    validated_rows = []
    for row in rows:
        row = _require_object(row, "aggregate.tasks[]")
        task_id = row.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ExperimentError("aggregate.tasks[] must have a non-empty string task_id")
        if task_id in seen_ids:
            raise ExperimentError(f"duplicate aggregate task_id: {task_id!r}")
        seen_ids.add(task_id)
        if task_id not in expected_by_id:
            raise ExperimentError(f"unexpected aggregate task_id: {task_id!r}")
        want = expected_by_id[task_id]
        for key in ("module", "a", "b", "zero", "four"):
            value = row.get(key)
            if key in {"a", "b", "zero", "four"} and type(value) is not int:
                raise ExperimentError(f"aggregate task {task_id}.{key} must be an integer")
            if value != want[key]:
                raise ExperimentError(f"aggregate task {task_id}.{key} expected {want[key]!r}, found {value!r}")
        if row.get("state") != "accepted":
            raise ExperimentError(f"aggregate task {task_id} must have state 'accepted'")
        if row.get("task_id") != task_id_by_module.get(want["module"]):
            raise ExperimentError(f"aggregate task {task_id} module does not join its request task ID")
        attempt_id, native_handle = row.get("attempt_id"), row.get("native_handle")
        if not isinstance(attempt_id, str) or not attempt_id or attempt_id in seen_attempts:
            raise ExperimentError(f"aggregate task {task_id} has a missing or duplicate attempt_id")
        if not isinstance(native_handle, str) or not native_handle or native_handle in seen_handles:
            raise ExperimentError(f"aggregate task {task_id} has a missing or duplicate native_handle")
        if native_handle not in native_handles:
            raise ExperimentError(f"aggregate task {task_id} native_handle is absent from the typed native lifecycle")
        seen_attempts.add(attempt_id)
        seen_handles.add(native_handle)
        evidence = _require_object(row.get("evidence"), f"aggregate task {task_id}.evidence")
        if set(evidence) != {"packet", "collected", "verified"}:
            raise ExperimentError(f"aggregate task {task_id}.evidence must contain packet, collected, and verified")
        evidence_status = {"packet": "prepared", "collected": "collected", "verified": "verified"}
        artifact_paths = {
            "packet": final_run_path / "packets" / f"{attempt_id}.json",
            "collected": final_run_path / "collected" / f"{attempt_id}.json",
            "verified": final_run_path / "verified" / f"{attempt_id}.json",
        }
        retained = {}
        actual = {}
        for name, status in evidence_status.items():
            actual[name], retained[name] = _artifact_evidence(
                evidence, name, task_id, attempt_id, native_handle, status,
                artifact_paths[name], repo_root)

        packet = actual["packet"]
        packet_task = _require_object(packet.get("task"), f"task {task_id} packet.task")
        packet_workspace = _require_object(packet.get("workspace"), f"task {task_id} packet.workspace")
        if packet.get("status") != "READY_TO_LAUNCH" or packet_task.get("mode") != "report-only":
            raise ExperimentError(f"task {task_id} actual packet is not prepared in report-only mode")
        if want["module"] not in packet_task.get("objective", ""):
            raise ExperimentError(f"task {task_id} actual packet objective does not identify its module")
        if packet_workspace.get("route") != "current" or Path(packet_workspace.get("root", "")).resolve() != fixture_root.resolve():
            raise ExperimentError(f"task {task_id} actual packet does not target the pinned current fixture")

        collected = actual["collected"]
        collected_result = _require_object(collected.get("result"), f"task {task_id} collected.result")
        if collected_result.get("status") != "SUCCEEDED" or collected_result.get("native_terminal") is not True:
            raise ExperimentError(f"task {task_id} actual collected record is not a successful terminal worker result")
        if collected_result.get("native_handle") != native_handle:
            raise ExperimentError(f"task {task_id} collected record native_handle does not match the native trace")

        verified = actual["verified"]
        if verified.get("passed") is not True or not isinstance(verified.get("reason"), str) or not verified["reason"].strip():
            raise ExperimentError(f"task {task_id} actual verification artifact did not pass with a reason")
        verified_evidence = verified.get("evidence")
        if not isinstance(verified_evidence, list) or not verified_evidence:
            raise ExperimentError(f"task {task_id} verified.evidence must be a non-empty list")
        checked_evidence = []
        for evidence_index, item_value in enumerate(verified_evidence):
            item = _require_object(item_value, f"task {task_id} verified.evidence[{evidence_index}]")
            evidence_path, evidence_pin = _regular_artifact(
                item.get("path"), item.get("sha256"),
                f"task {task_id} verifier evidence {evidence_index}", repo_root)
            # Runtimes may pin JSON or text. For JSON objects, validate identity
            # fields when present without requiring a runtime-specific schema.
            if evidence_path.suffix.lower() == ".json":
                try:
                    evidence_content = json.loads(evidence_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    raise ExperimentError(f"task {task_id} verifier evidence JSON is unreadable: {evidence_path}") from exc
                if isinstance(evidence_content, dict):
                    for key, identity in (("task_id", task_id), ("attempt_id", attempt_id),
                                          ("native_handle", native_handle)):
                        if key in evidence_content and evidence_content[key] != identity:
                            raise ExperimentError(f"task {task_id} verifier evidence {key} does not match its row")
                    if "module" in evidence_content and evidence_content["module"] not in (want["module"], Path(want["module"]).stem):
                        raise ExperimentError(f"task {task_id} verifier evidence module does not match its row")
            checked_evidence.append(evidence_pin)

        collected_verified = _require_object(collected.get("verified"), f"task {task_id} collected.verified")
        workspace_evidence = _require_object(collected_verified.get("workspace_evidence"),
                                             f"task {task_id} collected.verified.workspace_evidence")
        if (collected_verified.get("status") != "READY_FOR_PARENT_ACCEPTANCE"
                or workspace_evidence.get("status") != "ok"
                or workspace_evidence.get("verdict") != "unchanged"
                or workspace_evidence.get("head_moved") is not False
                or Path(workspace_evidence.get("root", "")).resolve() != fixture_root.resolve()):
            raise ExperimentError(f"task {task_id} collected filesystem verification is not unchanged for the fixture")

        inbox_path = final_run_path / "dispatcher" / "inbox" / f"{attempt_id}.json"
        inbox = _require_object(_read_json(inbox_path), f"task {task_id} Dispatcher inbox record")
        if inbox.get("attempt") != attempt_id or inbox.get("step") != task_id or inbox.get("status") != "SUCCEEDED":
            raise ExperimentError(f"task {task_id} Dispatcher inbox record does not accept its exact attempt")
        expected_result_path = final_run_path / "dispatcher" / "artifacts" / attempt_id / "result.json"
        inbox_evidence = _require_object(inbox.get("evidence"), f"task {task_id} Dispatcher inbox evidence")
        inbox_result_path, inbox_result_pin = _regular_artifact(
            inbox_evidence.get("path"), inbox_evidence.get("sha256"),
            f"task {task_id} accepted Dispatcher result", repo_root)
        if inbox_result_path != expected_result_path.resolve():
            raise ExperimentError(f"task {task_id} Dispatcher inbox does not reference its actual accepted result")
        inbox_result = _require_object(_read_json(inbox_result_path), f"task {task_id} actual Dispatcher result")
        if (inbox_result.get("status") != "SUCCEEDED"
                or inbox_result.get("native_handle") != native_handle
                or inbox_result.get("native_terminal") is not True):
            raise ExperimentError(f"task {task_id} actual Dispatcher result does not match its accepted native worker")
        result_evidence_path, result_evidence_pin = _regular_artifact(
            row.get("raw_result_path"), row.get("raw_result_sha256"),
            f"task {task_id} result evidence", repo_root)
        if result_evidence_role == "coordinator-response":
            if not _is_within(result_evidence_path, (coordinator_root / "raw-results").resolve()):
                raise ExperimentError(f"task {task_id} coordinator response must be retained under coordinator/raw-results")
        else:
            if result_evidence_path != expected_result_path.resolve():
                raise ExperimentError(f"task {task_id} legacy dispatcher-artifact role must pin its exact Dispatcher result")
            if result_evidence_pin["sha256"] != inbox_result_pin["sha256"]:
                raise ExperimentError(f"task {task_id} legacy Dispatcher result pin does not match the separately pinned inbox artifact")
        result_json = _require_object(_read_json(result_evidence_path), f"task {task_id} result evidence artifact")
        if result_json.get("status") != "SUCCEEDED" or result_json.get("native_handle") != native_handle or result_json.get("native_terminal") is not True:
            raise ExperimentError(f"task {task_id} result evidence does not match its accepted native worker")
        worker = worker_map[task_id]
        if Path(worker.get("packet_path", "")).resolve() != artifact_paths["packet"].resolve():
            raise ExperimentError(f"task {task_id} final result manifest packet path does not match its packet artifact")
        if worker.get("packet_sha256") != retained["packet"]["sha256"]:
            raise ExperimentError(f"task {task_id} final result manifest packet hash does not match the packet artifact")
        validated_rows.append({"task_id": task_id, "attempt_id": attempt_id,
                               "native_handle": native_handle, "module": row["module"],
                               "evidence": retained, "verifier_evidence": checked_evidence,
                               "dispatcher_result": inbox_result_pin,
                               "result_evidence": {"role": result_evidence_role,
                                                   **result_evidence_pin}})
    if seen_ids != set(expected_by_id):
        raise ExperimentError(f"aggregate task set differs; missing={sorted(set(expected_by_id)-seen_ids)}")
    if seen_handles != native_handles:
        raise ExperimentError("aggregate task native_handle set does not exactly match typed native child paths")

    totals = _require_object(aggregate.get("totals"), "aggregate.totals")
    expected_totals = expected["totals"]
    for key in ("a", "b", "zero", "four"):
        value = totals.get(key)
        if type(value) is not int or value != expected_totals[key]:
            raise ExperimentError(f"aggregate.totals.{key} expected {expected_totals[key]}, found {value!r}")
    diagnostics = aggregate.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise ExperimentError("aggregate.diagnostics must be a list, including when no diagnostics were needed")
    validated_diagnostics = []
    for index, diagnostic in enumerate(diagnostics):
        diagnostic = _require_object(diagnostic, f"aggregate.diagnostics[{index}]")
        _, artifact = _regular_artifact(diagnostic.get("path"), diagnostic.get("sha256"),
                                        f"diagnostic {index}", repo_root)
        validated = {"path": artifact["locator"], "sha256": artifact["sha256"]}
        if "summary" in diagnostic:
            summary = diagnostic["summary"]
            if not isinstance(summary, str) or not summary.strip():
                raise ExperimentError(f"aggregate.diagnostics[{index}].summary must be a non-empty string when present")
            validated["summary"] = summary
        validated_diagnostics.append(validated)
    return {"status": "PASS", "result_evidence_role": result_evidence_role,
            "request_task_count": task_count,
            "request_capacity": capacity, "accepted_tasks": len(validated_rows),
            "final_run_path": str(final_run_path.resolve()), "tasks": validated_rows,
            "totals": expected_totals, "diagnostics": validated_diagnostics}


def _prompt_result_evidence_role(prompt: str) -> str:
    dispatcher_example = (
        '"raw_result_path": "/absolute/harness-run-root/dispatcher/artifacts/'
        'actual-attempt-id/result.json"'
    )
    dispatcher_direction = (
        "point `raw_result_path` at the actual\n"
        "`dispatcher/artifacts/<attempt>/result.json`."
    )
    dispatcher_match = dispatcher_example in prompt and dispatcher_direction in prompt

    coordinator_examples = (
        '"raw_result_path": "/absolute/coordinator/raw-results/actual-task-id.json"',
        '"raw_result_path": "/absolute/coordinator/raw-results/module-01.json"',
    )
    coordinator_directions = (
        "result_evidence_role=coordinator-response",
        "Preserve the raw worker responses as files under\n"
        "`coordinator/raw-results/`, and set `raw_result_path` to each\n"
        "actual response file.",
        "Retain the actual worker responses under\n`coordinator/raw-results/`",
    )
    coordinator_match = (any(example in prompt for example in coordinator_examples)
                         and any(direction in prompt for direction in coordinator_directions))
    matches = [role for role, matched in (
        ("dispatcher-artifact", dispatcher_match),
        ("coordinator-response", coordinator_match),
    ) if matched]
    if len(matches) != 1:
        if len(matches) > 1:
            raise ExperimentError("result evidence role is ambiguous in the hash-verified prompt")
        raise ExperimentError("hash-verified prompt does not match a known result evidence contract")
    return matches[0]


def _resolve_result_evidence_role(configuration: dict, prompt: str) -> tuple[str, str]:
    if "result_evidence_role" in configuration:
        configured_role = configuration["result_evidence_role"]
        if configured_role != "coordinator-response":
            raise ExperimentError("case.configuration.result_evidence_role must be 'coordinator-response' for new cases")
        prompt_role = _prompt_result_evidence_role(prompt)
        if prompt_role != configured_role:
            raise ExperimentError("case configuration result evidence role conflicts with its hash-verified prompt")
        return configured_role, "case.configuration"
    return _prompt_result_evidence_role(prompt), "hash-verified prompt.txt"


def _verify_case(case_dir: Path) -> tuple[dict, dict, dict]:
    case = _require_object(_read_json(case_dir / "case.json"), "case.json")
    if case.get("schema") != CASE_SCHEMA:
        raise ExperimentError(f"case.json.schema must be {CASE_SCHEMA}")
    supplied_integrity = case.get("integrity_sha256")
    unsigned = dict(case)
    unsigned.pop("integrity_sha256", None)
    if supplied_integrity != _sha(_canonical(unsigned)):
        raise ExperimentError("case.json integrity_sha256 does not match its immutable contents")
    expected = _require_object(_read_json(case_dir / "expected.json"), "expected.json")
    if expected.get("schema") != "in-parallel-native-queue-oracle/v1" or expected.get("case_id") != case.get("case_id"):
        raise ExperimentError("parent-only expected.json does not match the prepared case identity")
    if _sha((case_dir / "expected.json").read_bytes()) != case.get("oracle_sha256"):
        raise ExperimentError("parent-only expected.json bytes changed after preparation")
    prompt_path = case_dir / "prompt.txt"
    if prompt_path.is_symlink() or not prompt_path.is_file():
        raise ExperimentError("prompt.txt is missing, redirected, or differs from its prepared hash")
    prompt_bytes = prompt_path.read_bytes()
    if _sha(prompt_bytes) != case.get("prompt_sha256"):
        raise ExperimentError("prompt.txt is missing, redirected, or differs from its prepared hash")
    try:
        prompt = prompt_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise ExperimentError("hash-verified prompt.txt is not UTF-8") from exc
    config = _require_object(case.get("configuration"), "case.configuration")
    source = _require_object(case.get("source"), "case.source")
    result_evidence_role, result_evidence_role_source = _resolve_result_evidence_role(config, prompt)
    return case, expected, {"configuration": config, "source": source,
                            "result_evidence_role": result_evidence_role,
                            "result_evidence_role_source": result_evidence_role_source}


def _source_check(source: dict) -> dict:
    repo_root = Path(source.get("repository_root", ""))
    fixture = Path(source.get("fixture_root", ""))
    if not repo_root.is_absolute() or not fixture.is_absolute():
        raise ExperimentError("case source pins must contain absolute repository_root and fixture_root")
    if fixture.is_symlink() or _is_within(fixture.resolve(), repo_root.resolve()):
        raise ExperimentError("prepared synthetic fixture is redirected into the selected skill source checkout")
    expected = {key: source.get(key) for key in ("head", "index_sha256", "files", "status")}
    actual = _fixture_snapshot(fixture)
    expected_files = expected["files"]
    observed_files = actual["files"]
    added_paths = sorted(set(observed_files) - set(expected_files))
    missing_paths = sorted(set(expected_files) - set(observed_files))
    changed_paths = sorted(path for path in set(expected_files) & set(observed_files)
                           if expected_files[path] != observed_files[path])
    file_deltas = {
        "added": [{"path": path, "observed_sha256": observed_files[path]}
                  for path in added_paths],
        "missing": [{"path": path, "expected_sha256": expected_files[path]}
                    for path in missing_paths],
        "changed": [{"path": path, "expected_sha256": expected_files[path],
                     "observed_sha256": observed_files[path]}
                    for path in changed_paths],
    }
    skills_ok = True
    skill_results = {}
    recorded_skills = _require_object(source.get("skills"), "case.source.skills")
    for name in SKILL_NAMES:
        old = _require_object(recorded_skills.get(name), f"case.source.skills.{name}")
        package = Path(old.get("root", ""))
        if not package.is_absolute() or not package.is_dir():
            skills_ok = False
            skill_results[name] = False
            continue
        current = _tree_pin(package)
        same = current["files"] == old.get("files") and current["tree_sha256"] == old.get("tree_sha256")
        skill_results[name] = same
        skills_ok = skills_ok and same
    head_ok = actual["head"] == expected["head"]
    index_ok = actual["index_sha256"] == expected["index_sha256"]
    files_ok = actual["files"] == expected["files"]
    status_ok = actual["status"] == expected["status"] == ""
    return {"fixture_root": str(fixture.resolve()),
            "head_unchanged": head_ok, "index_unchanged": index_ok,
            "source_files_unchanged": files_ok, "git_status_unchanged": status_ok,
            "file_deltas": file_deltas,
            "selected_skills_unchanged": skills_ok, "skill_packages": skill_results,
            "expected_head": expected["head"], "observed_head": actual["head"],
            "expected_index_sha256": expected["index_sha256"],
            "observed_index_sha256": actual["index_sha256"],
            "observed_status": actual["status"]}


def audit_case(case_arg: str, rollout_arg: str, aggregate_arg: str, output_arg: str) -> dict:
    case_dir = _absolute(case_arg, "--case")
    rollout = _absolute(rollout_arg, "--coordinator-rollout")
    aggregate_path = _absolute(aggregate_arg, "--aggregate")
    output = _absolute(output_arg, "--output")
    if output.exists() or output.is_symlink():
        raise ExperimentError(f"--output must name a new JSON file; already exists: {output}")
    if not output.parent.is_dir():
        raise ExperimentError(f"--output parent directory must already exist: {output.parent}")
    if _is_within(output, APPARATUS_REPO):
        raise ExperimentError(f"--output must be external to the experiment source checkout: {output}")
    report = {"schema": "in-parallel-native-queue-audit/v1", "status": "FAIL",
              "case": str(case_dir), "coordinator_rollout": str(rollout),
              "aggregate": str(aggregate_path), "proof_scope": PROOF_SCOPE, "errors": []}
    try:
        case, expected, values = _verify_case(case_dir)
        config, source = values["configuration"], values["source"]
        result_evidence_role = values["result_evidence_role"]
        report["result_evidence_role"] = {
            "role": result_evidence_role,
            "resolved_from": values["result_evidence_role_source"],
        }
        repo_root = Path(source["repository_root"])
        if _is_within(output, repo_root):
            raise ExperimentError(f"--output must be external to the selected skill checkout: {output}")
        source_report = _source_check(source)
        report["source_preservation"] = source_report
        for key, ok in source_report.items():
            if key.endswith("_unchanged") and not ok:
                report["errors"].append(f"prepared source pin changed: {key}")
        task_count = _require_int(config.get("task_count"), "case.configuration.task_count")
        capacity = _require_int(config.get("effective_capacity"), "case.configuration.effective_capacity")
        expected_capacity = config.get("requested_capacity")
        if expected_capacity is None:
            expected_capacity = min(DEFAULT_CAPACITY, task_count)
        if capacity != expected_capacity:
            report["errors"].append("case effective capacity differs from its explicit/default capacity rule")
        try:
            trace = audit_native_rollout(str(rollout), task_count, capacity)
            report["native_trace"] = trace
        except ExperimentError as exc:
            report["errors"].append(str(exc))
            trace = None
        try:
            aggregate = _read_json(aggregate_path)
            children = trace["children"] if trace else []
            aggregate_report = validate_aggregate(aggregate, expected, capacity,
                                                  result_evidence_role, repo_root,
                                                  Path(source["fixture_root"]),
                                                  case_dir / "coordinator", children)
            report["aggregate_validation"] = aggregate_report
        except ExperimentError as exc:
            report["errors"].append(str(exc))
        if not report["errors"]:
            report["status"] = "PASS"
    except (ExperimentError, OSError, TypeError, ValueError, KeyError, IndexError) as exc:
        report["errors"].append(str(exc))
    _write_json_new(output, report)
    report["output"] = str(output)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="create a new prompt-led synthetic queue case")
    prepare.add_argument("--case", required=True, help="new absolute external case directory")
    prepare.add_argument("--skill-root", required=True, help="absolute skills/ directory containing the selected packages")
    prepare.add_argument("--tasks", required=True, type=int, help="number of deterministic modules; must exceed capacity")
    prepare.add_argument("--capacity", type=int, help="optional explicit concurrent worker cap")
    audit = sub.add_parser("audit", help="offline audit of retained aggregate and native coordinator rollout")
    audit.add_argument("--case", required=True, help="absolute prepared case directory")
    audit.add_argument("--coordinator-rollout", required=True, help="absolute coordinator Codex JSONL rollout")
    audit.add_argument("--aggregate", required=True, help="absolute retained coordinator aggregate.json")
    audit.add_argument("--output", required=True, help="new absolute audit JSON path, external to the source checkout")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_case(args.case, args.skill_root, args.tasks, args.capacity)
        elif args.command == "audit":
            result = audit_case(args.case, args.coordinator_rollout, args.aggregate, args.output)
        else:  # pragma: no cover - subparsers constrain this
            parser.error(f"unsupported command: {args.command}")
    except (ExperimentError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"PREPARED", "PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
