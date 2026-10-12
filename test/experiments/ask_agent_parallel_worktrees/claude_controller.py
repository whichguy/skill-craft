#!/usr/bin/env python3
"""Prepare, launch, and capture one Claude Code Sonnet compact-v4 parent run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
DEFAULT_CLAUDE_BINARY = None
FROZEN_FILES = (
    "claude_controller.py", "claude_briefs.py", "claude_hooks.py",
    "claude_suite.py", "claude_native_trace.py",
)
COMMON_APPARATUS = (
    "fixture.py", "probe-fixture.py", "operations.py", "native_trace.py", "suite.py", "controller.py",
    "prompts.py", "diagnostics.py", "CONTRACT.md", "briefs.py", "worker_phase.py",
)
AGENT_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class ClaudeControllerError(ValueError):
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
        raise ClaudeControllerError(f"Expected a regular non-symlink JSON file: {source}")
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClaudeControllerError(f"Cannot read {source}: {type(exc).__name__}: {exc}") from exc


def _failure_details(run):
    root = Path(run).expanduser().resolve()
    operator = root / "operator"
    native = operator / "claude-native"
    paths = {
        "run": root,
        "manifest": root / "manifest.json",
        "operator": operator,
        "operator_launch": operator / "launch.json",
        "settings": native / "settings.json",
        "hooks": native / "hooks",
        "operator_stdout": operator / "stdout.jsonl",
        "operator_stderr": operator / "stderr.log",
        "process_result": operator / "process-result.json",
        "prepare_attempt": operator / "claude-prepare-attempt",
        "launch_attempt": operator / "launch-attempt",
        "capture_attempt": operator / "capture-attempt",
        "transcript_index": native / "transcript-index.json",
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


def _q(value) -> str:
    return shlex.quote(str(value))


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ClaudeControllerError(f"Compact-v4 prompt expected one {label} clause; found {count}")
    return text.replace(old, new, 1)


def transform_parent_prompt(common_prompt, run, workers, mode, delivery_mode):
    """Adapt only the exact compact-v4 host transport clauses and retain the full common procedure."""
    run = Path(run).expanduser().resolve()
    operator = run / "operator"
    briefs = operator / "briefs.py"
    claude_briefs = operator / "claude_briefs.py"
    tick = chr(96)
    prompt = str(common_prompt)
    prompt = _replace_once(
        prompt,
        "This is a fresh Grok-medium parent and fresh general-purpose native background workers.",
        "This is a fresh Claude Code Sonnet-medium parent and fresh general-purpose Claude Agent background workers.",
        "parent host identity",
    )
    old_build = (
        "Build assignments once with " + tick + f"python3 -B {_q(briefs)} --run {_q(run)} --compact" + tick
        + ". It validates each binding and retains one bounded native argument JSON file per worker."
    )
    new_build = (
        "Build assignments once with " + tick + f"python3 -B {_q(claude_briefs)} --run {_q(run)} --compact" + tick
        + ". This adapter calls the unchanged common compact briefs, preserves their binding evidence, and retains "
        "each exact Claude Agent argument mapping with source and transformed prompt hashes in "
        + tick + f"{operator / 'claude-dispatch/index.json'}" + tick + "."
    )
    prompt = _replace_once(prompt, old_build, new_build, "compact assignment builder")
    old_emit = (
        f"For each ID from 1 through {workers}, invoke " + tick
        + f"python3 -B {_q(briefs)} --run {_q(run)} --emit-worker ID" + tick
        + " in its own tool call, read that complete single-worker JSON, and pass its exact "
        + tick + "native_arguments" + tick
        + " object directly to the native spawn tool. Do not emit all worker prompts in one Bash result, "
        "hand-edit a prompt, omit fields, or infer a binding."
    )
    new_emit = (
        f"For each ID from 1 through {workers}, invoke " + tick
        + f"python3 -B {_q(claude_briefs)} --run {_q(run)} --emit-worker ID" + tick
        + " in its own tool call, read that complete single-worker JSON, and pass its exact "
        + tick + "agent_arguments" + tick
        + " object unchanged to Claude Code's native " + tick + "Agent" + tick
        + " tool. Do not edit a prompt, omit fields, or infer a binding. The Claude Agent call has no cwd field; "
        "the exact worktree is bound in its prompt prefix and every worker Bash call."
    )
    prompt = _replace_once(prompt, old_emit, new_emit, "per-worker compact assignment emitter")
    old_host = (
        "Use only host-native background worker spawn and terminal collection tools, with "
        + tick + "background=true" + tick
        + ", exact description/prompt/cwd, no resume, and fresh context. Never shell-launch models."
    )
    new_host = (
        "Use Claude Code's native " + tick + "Agent" + tick
        + " tool with the exact emitted " + tick + "description" + tick + ", "
        + tick + "subagent_type" + tick + ", " + tick + "run_in_background" + tick + ", and "
        + tick + "prompt" + tick
        + " fields, with no resume and fresh context. Claude Agent has no cwd field; enforce the assigned "
        "worktree through the prompt's Bash prefix. Keep each returned native task handle and collect actual "
        "terminal results from Claude's task notifications. Rely on those native notifications; do not poll "
        "files or shell-launch child models."
    )
    prompt = _replace_once(prompt, old_host, new_host, "native launch and collection")
    if "Grok" in prompt:
        raise ClaudeControllerError("Compact-v4 prompt still contains a Grok host reference after adaptation")
    return prompt, {
        "schema": "ask-agent.claude-parent-prompt-map/v1",
        "source_path": str(operator / "claude-common-parent-prompt.txt"),
        "source_sha256": _sha(str(common_prompt).encode("utf-8")),
        "transformed_path": str(operator / "parent-prompt.txt"),
        "transformed_sha256": _sha(prompt.encode("utf-8")),
        "replacements": [
            "parent host identity",
            "compact assignment builder",
            "per-worker compact assignment emitter",
            "native launch and collection",
        ],
        "workers": workers,
        "mode": mode,
        "delivery_mode": delivery_mode,
    }


def _check_compact_treatment(run):
    manifest = _read_json(Path(run) / "manifest.json")
    treatment_path = Path(run) / "operator" / "treatment.json"
    treatment = _read_json(treatment_path)
    expected = {
        "treatment": "compact",
        "version": 4,
        "verification_output": "summary-v1",
        "delivery_mode": manifest.get("delivery_mode", "patch"),
        "workers": manifest.get("workers"),
        "mode": manifest.get("mode"),
    }
    if (not isinstance(treatment, dict)
            or any(treatment.get(key) != value for key, value in expected.items())
            or type(treatment.get("version")) is not int):
        raise ClaudeControllerError(
            f"Compact v4 treatment does not match frozen manifest: expected {expected!r}, observed {treatment!r}"
        )
    return manifest, treatment


def prepare(run, *, source_dir=None):
    """Freeze common compact-v4 inputs, adapt the parent prompt, and create local hooks."""
    run = Path(run).expanduser().resolve()
    operator = run / "operator"
    if not operator.is_dir():
        raise ClaudeControllerError(f"Prepared run has no operator directory: {operator}")
    source = Path(source_dir or HERE).resolve()
    attempt = operator / "claude-prepare-attempt"
    if attempt.exists() or attempt.is_symlink():
        raise ClaudeControllerError(f"Claude preparation attempt already exists; preserve it: {attempt}")
    if any((operator / name).exists() for name in (
            "parent-prompt.txt", "treatment.json", "launch.json", "claude-prompt-map.json",
            "claude-preparation.json", "claude-native")):
        raise ClaudeControllerError("Claude prepare requires a fresh operator directory without prior prompt or attempt evidence")
    attempt.mkdir()
    manifest = _read_json(run / "manifest.json")
    if manifest.get("workers") not in (3, 5) or manifest.get("mode") not in ("parallel", "sequential"):
        raise ClaudeControllerError("Claude compact v4 requires a frozen 3/5-worker parallel or sequential manifest")
    delivery_mode = manifest.get("delivery_mode", "patch")
    if delivery_mode not in ("patch", "commits", "ephemeral"):
        raise ClaudeControllerError(f"Unsupported frozen delivery mode: {delivery_mode!r}")
    for name in FROZEN_FILES:
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ClaudeControllerError(f"Required Claude apparatus is missing or not a regular file: {path}")
    prompts_path = source / "prompts.py"
    if prompts_path.is_symlink() or not prompts_path.is_file():
        raise ClaudeControllerError(f"Common prompt builder is missing or not a regular file: {prompts_path}")
    argv = [
        sys.executable, "-B", str(prompts_path), "--run", str(run),
        "--workers", str(manifest["workers"]), "--mode", manifest["mode"],
        "--treatment", "compact", "--delivery-mode", delivery_mode,
    ]
    result = subprocess.run(argv, cwd=run, capture_output=True, text=True)
    if result.returncode != 0:
        raise ClaudeControllerError(
            f"Common compact prompt builder failed with exit {result.returncode}: {result.stderr.strip()}"
        )
    common_prompt_path = operator / "parent-prompt.txt"
    common_prompt = common_prompt_path.read_text(encoding="utf-8")
    common_bytes = common_prompt.encode("utf-8")
    _write_exclusive(operator / "claude-common-parent-prompt.txt", common_bytes)
    transformed, mapping = transform_parent_prompt(
        common_prompt, run, manifest["workers"], manifest["mode"], delivery_mode,
    )
    prompt_bytes = transformed.encode("utf-8")
    common_prompt_path.write_bytes(prompt_bytes)
    mapping["source_sha256"] = _sha(common_bytes)
    mapping["transformed_sha256"] = _sha(prompt_bytes)
    map_bytes = _write_json(operator / "claude-prompt-map.json", mapping)

    for name in FROZEN_FILES:
        src, dest = source / name, operator / name
        if dest.exists() or dest.is_symlink():
            raise ClaudeControllerError(f"Frozen Claude apparatus destination already exists: {dest}")
        shutil.copy2(src, dest)
    native_dir = operator / "claude-native"
    native_dir.mkdir()
    hooks_dir = native_dir / "hooks"
    hooks_dir.mkdir()
    settings_path = native_dir / "settings.json"
    import claude_hooks
    claude_hooks.write_settings(
        settings_path, hooks_dir, script_path=operator / "claude_hooks.py",
    )
    preparation = {
        "schema": "ask-agent.claude-preparation/v1",
        "status": "PREPARED",
        "run_id": manifest.get("run_id"),
        "workers": manifest["workers"],
        "mode": manifest["mode"],
        "delivery_mode": delivery_mode,
        "model": "sonnet",
        "effort": "medium",
        "common_prompt_sha256": _sha(common_bytes),
        "prompt_sha256": _sha(prompt_bytes),
        "prompt_map_sha256": _sha(map_bytes),
        "settings_path": str(settings_path.resolve()),
        "settings_sha256": _sha(settings_path.read_bytes()),
        "frozen_files": {
            name: _sha((operator / name).read_bytes()) for name in FROZEN_FILES
        },
    }
    _write_json(operator / "claude-preparation.json", preparation)
    return preparation


def build_launch_argv(binary, session_id, settings_path, *, model="sonnet", effort="medium"):
    return [
        str(binary), "--print", "--model", model, "--effort", effort,
        "--session-id", session_id, "--output-format", "stream-json", "--verbose",
        "--forward-subagent-text", "--include-hook-events", "--setting-sources", "",
        "--settings", str(settings_path), "--strict-mcp-config", "--mcp-config",
        '{"mcpServers":{}}', "--permission-mode", "acceptEdits",
        "--allowedTools", "Bash,Agent,Read,Edit,Write",
    ]


def _frozen_hashes(operator):
    names = list(COMMON_APPARATUS) + list(FROZEN_FILES) + [
        "treatment.json", "parent-prompt.txt", "claude-common-parent-prompt.txt",
        "claude-prompt-map.json", "claude-preparation.json", "claude-native/settings.json",
    ]
    hashes = {}
    for name in names:
        path = operator / name
        if path.is_file() and not path.is_symlink():
            hashes[name] = _sha(path.read_bytes())
    return hashes


def _resolve_binary(binary):
    executable = binary or shutil.which("claude") or (Path.home() / ".claude" / "tools" / "claude")
    if not executable:
        raise ClaudeControllerError("Claude Code CLI is unavailable")
    return Path(executable).expanduser().resolve(strict=True)


def launch(run, claude_binary=None, model="sonnet", effort="medium"):
    """Launch only the parent; native Agent calls remain inside Claude Code."""
    run = Path(run).expanduser().resolve()
    operator = run / "operator"
    prompt_path = operator / "parent-prompt.txt"
    if prompt_path.is_symlink() or not prompt_path.is_file():
        raise ClaudeControllerError(f"Missing reviewed Claude parent prompt: {prompt_path}")
    preparation = _read_json(operator / "claude-preparation.json")
    if preparation.get("status") != "PREPARED":
        raise ClaudeControllerError("Claude launch requires successful frozen preparation")
    _check_compact_treatment(run)
    if preparation.get("prompt_sha256") != _sha(prompt_path.read_bytes()):
        raise ClaudeControllerError("Prepared Claude parent prompt changed after preparation")
    if model != "sonnet" or effort != "medium":
        raise ClaudeControllerError("Synthetic Sonnet runs are pinned to model sonnet and medium effort")
    if any((operator / name).exists() for name in (
            "launch.json", "stdout.jsonl", "observed.jsonl", "stderr.log", "process-result.json",
            "claude-native/capture_result.json", "launch-attempt")):
        raise ClaudeControllerError("Claude launch evidence already exists; preserve the attempt and use a fresh run")
    (operator / "launch-attempt").mkdir()
    binary = _resolve_binary(claude_binary)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["CLAUDE_CODE_FORK_SUBAGENT"] = "0"
    env["DISABLE_AUTOUPDATER"] = "1"
    removed = []
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if key in env:
            removed.append(key)
            env.pop(key)
    version_result = subprocess.run(
        [str(binary), "--version"], capture_output=True, text=True, check=True, env=env,
    )
    session_id = str(uuid.uuid4())
    settings_path = operator / "claude-native" / "settings.json"
    argv = build_launch_argv(binary, session_id, settings_path, model=model, effort=effort)
    prompt_bytes = prompt_path.read_bytes()
    prompt_map_path = operator / "claude-prompt-map.json"
    identity = {
        "schema": "ask-agent.claude-launch/v1",
        "session_id": session_id,
        "argv": argv,
        "cwd": str((run / "caller").resolve()),
        "started_epoch": time.time(),
        "model": model,
        "effort": effort,
        "version": version_result.stdout.strip(),
        "binary_sha256": _sha(binary.read_bytes()),
        "prompt_sha256": _sha(prompt_bytes),
        "source_prompt_sha256": preparation["common_prompt_sha256"],
        "prompt_map_sha256": _sha(prompt_map_path.read_bytes()),
        "manifest_sha256": _sha((run / "manifest.json").read_bytes()),
        "apparatus_sha256": _frozen_hashes(operator),
        "environment_overrides": {
            "PYTHONDONTWRITEBYTECODE": "1",
            "CLAUDE_CODE_FORK_SUBAGENT": "0",
            "DISABLE_AUTOUPDATER": "1",
            "removed_auth_environment_keys": removed,
        },
    }
    _write_json(operator / "launch.json", identity)
    for name in ("stdout.jsonl", "observed.jsonl", "stderr.log", "process-result.json"):
        path = operator / name
        if path.exists() or path.is_symlink():
            raise ClaudeControllerError(f"Claude launch output already exists: {path}")
    started_clock = time.monotonic()
    with prompt_path.open("rb") as prompt_stream, \
            (operator / "stdout.jsonl").open("xb") as raw_out, \
            (operator / "observed.jsonl").open("xb") as observed_out, \
            (operator / "stderr.log").open("xb") as stderr_out:
        process = subprocess.Popen(
            argv, cwd=run / "caller", env=env, stdin=prompt_stream,
            stdout=subprocess.PIPE, stderr=stderr_out,
        )
        for raw_line in process.stdout:
            observed_epoch = time.time()
            raw_out.write(raw_line)
            raw_out.flush()
            try:
                event = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                event = {"unparsed": raw_line.decode("utf-8", errors="replace").rstrip("\n")}
            observation = {
                "observed_epoch": observed_epoch,
                "elapsed_s": time.monotonic() - started_clock,
                "event": event,
            }
            observed_out.write((json.dumps(observation, ensure_ascii=False) + "\n").encode("utf-8"))
            observed_out.flush()
        exit_code = process.wait()
    finished_epoch = time.time()
    elapsed = time.monotonic() - started_clock
    _write_json(operator / "process-result.json", {
        "exit_code": exit_code,
        "pid": process.pid,
        "finished_epoch": finished_epoch,
        "elapsed_s": elapsed,
    })
    capture_result = capture(run)
    capture_passed = capture_result.get("passed") is True
    result = {
        "session_id": session_id,
        "exit_code": exit_code,
        "elapsed_s": elapsed,
        "capture_passed": capture_passed,
        "capture_result": str((operator / "claude-native" / "capture_result.json").resolve()),
        "status": "PASS" if exit_code == 0 and capture_passed else "FAIL",
    }
    if result["status"] == "FAIL":
        errors = []
        if exit_code != 0:
            errors.append(f"Claude parent exited with code {exit_code}")
        if not capture_passed:
            errors.append(f"Transcript capture failed: {capture_result.get('error', 'see capture result')}")
        result["error"] = "; ".join(errors)
        result.update(_failure_details(run))
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result["status"] == "PASS" else 2


def _record_payload(path):
    if path.is_symlink() or not path.is_file():
        raise ClaudeControllerError(f"Hook record is missing or not a regular file: {path}")
    record = _read_json(path)
    if record.get("schema") != "ask-agent.claude-hook/v1":
        raise ClaudeControllerError(f"Unexpected hook record schema: {path}")
    payload = record.get("payload")
    if not isinstance(payload, dict) or record.get("parse_error"):
        raise ClaudeControllerError(f"Hook record has no valid payload: {path}")
    return record, payload


def _bound_transcript(value, label):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ClaudeControllerError(f"{label} transcript path must be absolute: {value!r}")
    path = Path(value)
    if path.is_symlink() or not path.is_file():
        raise ClaudeControllerError(f"{label} transcript is missing or not a regular file: {path}")
    return path.resolve(strict=True)


def _stream_events(path, session_id):
    events = []
    with path.open("rb") as stream:
        for number, raw_line in enumerate(stream, 1):
            try:
                event = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ClaudeControllerError(f"Malformed Claude stream event at {path}:{number}: {exc}") from exc
            if not isinstance(event, dict) or event.get("session_id") != session_id:
                raise ClaudeControllerError(f"Claude stream event at {path}:{number} is not bound to session {session_id}")
            events.append(event)
    return events


def _dispatch_rows(run):
    operator = run / "operator"
    index_path = operator / "claude-dispatch" / "index.json"
    index = _read_json(index_path)
    if index.get("schema") != "ask-agent.claude-dispatch-index/v1":
        raise ClaudeControllerError(f"Unexpected Claude dispatch index: {index_path}")
    manifest = _read_json(run / "manifest.json")
    workers = manifest.get("workers")
    expected_ids = [str(index) for index in range(1, workers + 1)] if type(workers) is int and workers > 0 else []
    rows = index.get("assignments")
    if not expected_ids or not isinstance(rows, list) or [str(row.get("worker_id")) for row in rows] != expected_ids:
        raise ClaudeControllerError("Claude dispatch index worker IDs do not match frozen manifest order")
    import claude_briefs
    result = {}
    for row in rows:
        worker_id = str(row["worker_id"])
        assignment_path = Path(row.get("assignment_path", ""))
        payload = assignment_path.read_bytes()
        if assignment_path.is_symlink() or _sha(payload) != row.get("sha256"):
            raise ClaudeControllerError(f"Claude dispatch assignment hash mismatch for worker {worker_id}")
        assignment = _read_json(assignment_path)
        source_path = Path(assignment.get("source_assignment_path", ""))
        source = _read_json(source_path)
        if (_sha(source_path.read_bytes()) != assignment.get("source_assignment_sha256")
                or source.get("worker_id") != worker_id):
            raise ClaudeControllerError(f"Common source assignment mismatch for worker {worker_id}")
        expected_arguments = claude_briefs.agent_arguments(source.get("native_arguments"))
        if assignment.get("agent_arguments") != expected_arguments:
            raise ClaudeControllerError(f"Claude Agent prompt mapping mismatch for worker {worker_id}")
        prompt_sha256 = _sha(expected_arguments["prompt"].encode("utf-8"))
        if (assignment.get("prompt_sha256") != prompt_sha256
                or row.get("prompt_sha256") != prompt_sha256
                or assignment.get("source_prompt_sha256") != _sha(source["native_arguments"]["prompt"].encode("utf-8"))):
            raise ClaudeControllerError(f"Claude dispatch prompt hashes mismatch for worker {worker_id}")
        result[worker_id] = {
            "agent_arguments": expected_arguments,
            "assignment_path": str(assignment_path.resolve()),
            "assignment_sha256": row["sha256"],
        }
    return result


def agent_arguments_match(observed, expected):
    """Match Agent identity fields while retaining the host's display label."""
    keys = {"description", "subagent_type", "run_in_background", "prompt"}
    if (not isinstance(observed, dict) or not isinstance(expected, dict)
            or set(observed) != keys or set(expected) != keys):
        return False
    if (not isinstance(observed["description"], str) or not observed["description"].strip()
            or not isinstance(expected["description"], str) or not expected["description"].strip()
            or not isinstance(observed["prompt"], str) or not isinstance(expected["prompt"], str)
            or not isinstance(observed["subagent_type"], str) or not isinstance(expected["subagent_type"], str)
            or type(observed["run_in_background"]) is not bool
            or type(expected["run_in_background"]) is not bool):
        return False
    return all(observed[key] == expected[key]
               for key in ("prompt", "subagent_type", "run_in_background"))


def _agent_tool_map(events, dispatch):
    by_tool_id = {}
    by_worker = {}
    descriptions = {}
    for event in events:
        if event.get("type") != "assistant":
            continue
        message = event.get("message")
        content = message.get("content", []) if isinstance(message, dict) else []
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_use" or item.get("name") != "Agent":
                continue
            arguments = item.get("input")
            matching = [worker_id for worker_id, row in dispatch.items()
                        if agent_arguments_match(arguments, row["agent_arguments"])]
            if len(matching) != 1:
                raise ClaudeControllerError("Claude Agent tool input is missing, duplicate, or differs from dispatch mapping")
            worker_id = matching[0]
            tool_use_id = item.get("id")
            if (not isinstance(tool_use_id, str) or not tool_use_id
                    or tool_use_id in by_tool_id or worker_id in by_worker):
                raise ClaudeControllerError(f"Duplicate or missing Claude Agent tool_use_id for worker {worker_id}")
            by_tool_id[tool_use_id] = worker_id
            by_worker[worker_id] = tool_use_id
            descriptions[worker_id] = arguments["description"]
    if set(by_worker) != set(dispatch):
        raise ClaudeControllerError(f"Claude Agent calls do not cover dispatch workers: {sorted(by_worker)}")
    return by_tool_id, by_worker, descriptions


def filter_local_bash_task_events(events):
    """Remove only fully bound local_bash task lifecycle rows from Claude events."""
    bash_calls = {}
    for event in events:
        if event.get("type") != "assistant":
            continue
        message = event.get("message")
        content = message.get("content", []) if isinstance(message, dict) else []
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_use" or item.get("name") != "Bash":
                continue
            tool_use_id = item.get("id")
            arguments = item.get("input")
            command = arguments.get("command") if isinstance(arguments, dict) else None
            if isinstance(tool_use_id, str) and tool_use_id:
                bash_calls.setdefault(tool_use_id, []).append((command, arguments.get("description", command)))

    starts = {}
    start_indices = set()
    labels = {}
    for index, event in enumerate(events):
        if event.get("type") != "system" or event.get("subtype") != "task_started":
            continue
        if event.get("task_type") != "local_bash":
            continue
        tool_use_id = event.get("tool_use_id")
        task_id = event.get("task_id")
        commands = bash_calls.get(tool_use_id, [])
        if (not isinstance(tool_use_id, str) or not tool_use_id or len(commands) != 1
                or not isinstance(commands[0][0], str) or not commands[0][0]
                or not isinstance(commands[0][1], str) or not commands[0][1]
                or not isinstance(task_id, str) or not task_id
                or event.get("description") != commands[0][1]):
            raise ClaudeControllerError("Claude local_bash start is not bound to one matching Bash tool call")
        if tool_use_id in starts or any(row["task_id"] == task_id for row in starts.values()):
            raise ClaudeControllerError("Duplicate Claude local_bash tool or task ID")
        starts[tool_use_id] = {"task_id": task_id, "command": commands[0][0]}
        labels[tool_use_id] = commands[0][1]
        start_indices.add(index)

    notification_indices = set()
    notifications = set()
    for index, event in enumerate(events):
        if event.get("type") != "system" or event.get("subtype") != "task_notification":
            continue
        tool_use_id = event.get("tool_use_id")
        if tool_use_id not in starts:
            continue
        expected = starts[tool_use_id]
        if (tool_use_id in notifications or event.get("task_id") != expected["task_id"]
                or event.get("task_type") not in (None, "local_bash")
                or event.get("status") != "completed" or event.get("summary") != labels[tool_use_id]):
            raise ClaudeControllerError("Claude local_bash notification does not match its started Bash task")
        notifications.add(tool_use_id)
        notification_indices.add(index)
    if notifications != set(starts):
        raise ClaudeControllerError("Claude local_bash start is missing its completed notification")

    filtered = [event for index, event in enumerate(events)
                if index not in start_indices and index not in notification_indices]
    return filtered, starts


def _task_maps(events, by_tool_id):
    started = {}
    notifications = {}
    for event in events:
        if event.get("type") != "system":
            continue
        subtype = event.get("subtype")
        if subtype == "task_started":
            tool_use_id = event.get("tool_use_id")
            task_id = event.get("task_id")
            if tool_use_id not in by_tool_id or not isinstance(task_id, str) or not task_id:
                raise ClaudeControllerError("Claude task_started event has an unknown tool or missing task_id")
            if tool_use_id in started or task_id in started.values():
                raise ClaudeControllerError("Duplicate Claude task_started tool or task ID")
            started[tool_use_id] = task_id
        elif subtype == "task_notification":
            tool_use_id = event.get("tool_use_id")
            task_id = event.get("task_id")
            if tool_use_id not in by_tool_id or not isinstance(task_id, str) or not task_id:
                raise ClaudeControllerError("Claude task_notification has an unknown tool or missing task_id")
            if tool_use_id in notifications:
                raise ClaudeControllerError("Duplicate Claude task_notification for one Agent call")
            notifications[tool_use_id] = {
                "task_id": task_id,
                "status": event.get("status"),
            }
    if set(started) != set(by_tool_id) or set(notifications) != set(by_tool_id):
        raise ClaudeControllerError("Claude stream is missing task_started or task_notification evidence")
    for tool_use_id in by_tool_id:
        if notifications[tool_use_id] != {"task_id": started[tool_use_id], "status": "completed"}:
            raise ClaudeControllerError(f"Claude task notification is not terminal-success for {tool_use_id}")
    return started


def _copy_transcript(source, destination):
    payload = source.read_bytes()
    _write_exclusive(destination, payload)
    if destination.read_bytes() != payload:
        raise ClaudeControllerError(f"Copied transcript bytes differ from source: {source}")
    return _sha(payload)


def _capture_impl(run, launch, process):
    operator = run / "operator"
    native_dir = operator / "claude-native"
    hooks_dir = native_dir / "hooks"
    records = []
    for path in sorted(hooks_dir.glob("*.json")):
        record, payload = _record_payload(path)
        if payload.get("session_id") != launch.get("session_id"):
            raise ClaudeControllerError(f"Hook record is replayed or belongs to another session: {path}")
        records.append({
            "path": path,
            "record": record,
            "payload": payload,
            "sha256": _sha(path.read_bytes()),
        })
    session_id = launch.get("session_id")
    if not session_id or process.get("exit_code") is None:
        raise ClaudeControllerError("Capture requires a bound session ID and terminal process result")
    events_by_name = {}
    for row in records:
        payload = row["payload"]
        event_name = payload.get("hook_event_name")
        if event_name not in ("SessionStart", "SubagentStart", "SubagentStop", "SessionEnd"):
            raise ClaudeControllerError(f"Unexpected Claude hook event in {row['path']}: {event_name!r}")
        events_by_name.setdefault(event_name, []).append(row)
    if len(events_by_name.get("SessionStart", [])) != 1 or len(events_by_name.get("SessionEnd", [])) != 1:
        raise ClaudeControllerError("Capture requires exactly one SessionStart and one SessionEnd hook record")
    parent_start = events_by_name["SessionStart"][0]
    parent_end = events_by_name["SessionEnd"][0]
    parent_path = _bound_transcript(parent_start["payload"].get("transcript_path"), "Parent")
    if _bound_transcript(parent_end["payload"].get("transcript_path"), "Parent end") != parent_path:
        raise ClaudeControllerError("SessionEnd parent transcript path differs from SessionStart")
    for row in records:
        path_value = row["payload"].get("transcript_path")
        if path_value and _bound_transcript(path_value, "Hook parent") != parent_path:
            raise ClaudeControllerError(f"Hook parent transcript path is ambiguous: {row['path']}")

    stream_path = operator / "stdout.jsonl"
    events = _stream_events(stream_path, session_id)
    dispatch = _dispatch_rows(run)
    by_tool_id, by_worker, descriptions = _agent_tool_map(events, dispatch)
    filtered_events, local_bash_tasks = filter_local_bash_task_events(events)
    if set(local_bash_tasks) & set(by_tool_id):
        raise ClaudeControllerError("Claude local_bash tool ID conflicts with an Agent tool ID")
    started = _task_maps(filtered_events, by_tool_id)
    if set(started.values()) & {row["task_id"] for row in local_bash_tasks.values()}:
        raise ClaudeControllerError("Claude local_bash task ID conflicts with an Agent task ID")
    start_rows = events_by_name.get("SubagentStart", [])
    stop_rows = events_by_name.get("SubagentStop", [])
    starts, stops = {}, {}
    for row in start_rows:
        payload = row["payload"]
        agent_id = payload.get("agent_id")
        if (not isinstance(agent_id, str) or not AGENT_ID.fullmatch(agent_id)
                or agent_id in starts or payload.get("agent_type") != "general-purpose"):
            raise ClaudeControllerError(f"Missing, duplicate, or invalid SubagentStart agent ID: {row['path']}")
        starts[agent_id] = row
    for row in stop_rows:
        payload = row["payload"]
        agent_id = payload.get("agent_id")
        if (not isinstance(agent_id, str) or not AGENT_ID.fullmatch(agent_id)
                or agent_id in stops or payload.get("agent_type") != "general-purpose"):
            raise ClaudeControllerError(f"Missing, duplicate, or invalid SubagentStop agent ID: {row['path']}")
        stops[agent_id] = row
    expected_agent_ids = set(started.values())
    if set(starts) != expected_agent_ids or set(stops) != expected_agent_ids:
        raise ClaudeControllerError("SubagentStart/Stop IDs do not match Claude task handles")
    worker_by_agent = {}
    for worker_id, tool_use_id in by_worker.items():
        task_id = started[tool_use_id]
        if task_id in worker_by_agent:
            raise ClaudeControllerError(f"Claude task ID maps to multiple workers: {task_id}")
        worker_by_agent[task_id] = worker_id
        if starts[task_id]["payload"].get("agent_id") != task_id:
            raise ClaudeControllerError(f"SubagentStart ID does not match Claude task handle {task_id}")
    if set(worker_by_agent) != expected_agent_ids:
        raise ClaudeControllerError("Claude task IDs do not map one-to-one to dispatch workers")

    index_rows = []
    parent_destination = native_dir / "parent.jsonl"
    parent_sha = _copy_transcript(parent_path, parent_destination)
    parent_hook_refs = [
        {"path": str(row["path"].resolve()), "sha256": row["sha256"]}
        for row in (parent_start, parent_end)
    ]
    index_rows.append({
        "kind": "parent",
        "session_id": session_id,
        "source_path": str(parent_path),
        "source_sha256": parent_sha,
        "retained_path": str(parent_destination.resolve()),
        "sha256": parent_sha,
        "hook_refs": parent_hook_refs,
    })
    for agent_id in sorted(expected_agent_ids, key=lambda value: value):
        start_row, stop_row = starts[agent_id], stops[agent_id]
        stop_payload = stop_row["payload"]
        source_path = _bound_transcript(
            stop_payload.get("agent_transcript_path") or stop_payload.get("transcript_path"),
            f"Worker {worker_by_agent[agent_id]}",
        )
        if source_path == parent_path:
            raise ClaudeControllerError(f"Worker {agent_id} transcript resolves to parent transcript")
        destination = native_dir / f"worker-{agent_id}.jsonl"
        transcript_sha = _copy_transcript(source_path, destination)
        start_hook = start_row["path"]
        stop_hook = stop_row["path"]
        index_rows.append({
            "kind": "worker",
            "session_id": session_id,
            "worker_id": worker_by_agent[agent_id],
            "agent_id": agent_id,
            "task_id": agent_id,
            "tool_use_id": by_worker[worker_by_agent[agent_id]],
            "agent_description": descriptions[worker_by_agent[agent_id]],
            "source_path": str(source_path),
            "source_sha256": transcript_sha,
            "retained_path": str(destination.resolve()),
            "sha256": transcript_sha,
            "hook_refs": [
                {"path": str(start_hook.resolve()), "sha256": start_row["sha256"]},
                {"path": str(stop_hook.resolve()), "sha256": stop_row["sha256"]},
            ],
        })
    index = {
        "schema": "ask-agent.claude-transcript-index/v1",
        "session_id": session_id,
        "parent_source_path": str(parent_path),
        "worker_count": len(expected_agent_ids),
        "rows": index_rows,
    }
    index_path = native_dir / "transcript-index.json"
    index_bytes = _write_json(index_path, index)
    return {
        "schema": "ask-agent.claude-capture-result/v1",
        "status": "PASS",
        "passed": True,
        "session_id": session_id,
        "transcript_index_path": str(index_path.resolve()),
        "transcript_index_sha256": _sha(index_bytes),
        "captured_transcripts": len(index_rows),
    }


def capture(run):
    """Capture only exact parent/child transcript paths bound by this session's hooks."""
    run = Path(run).expanduser().resolve()
    operator = run / "operator"
    result_path = operator / "claude-native" / "capture_result.json"
    attempt = operator / "capture-attempt"
    if result_path.exists() or result_path.is_symlink():
        raise ClaudeControllerError(f"Capture result already exists; preserve it: {result_path}")
    if attempt.exists() or attempt.is_symlink():
        raise ClaudeControllerError(f"Capture attempt already exists; preserve it: {attempt}")
    attempt.mkdir()
    try:
        launch_record = _read_json(operator / "launch.json")
        process = _read_json(operator / "process-result.json")
        result = _capture_impl(run, launch_record, process)
    except (OSError, KeyError, TypeError, ClaudeControllerError, ValueError) as exc:
        result = {
            "schema": "ask-agent.claude-capture-result/v1",
            "status": "FAIL",
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
            **_failure_details(run),
        }
    _write_json(result_path, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "launch", "capture"))
    parser.add_argument("--run", required=True)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--effort", default="medium", choices=("low", "medium", "high"))
    parser.add_argument("--claude-binary")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.run)
            print(json.dumps(result, sort_keys=True))
            return 0
        if args.command == "launch":
            return launch(args.run, args.claude_binary, args.model, args.effort)
        result = capture(args.run)
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("passed") is True else 2
    except (OSError, KeyError, TypeError, subprocess.SubprocessError, ClaudeControllerError) as exc:
        print(json.dumps({
            "schema": "ask-agent.claude-controller-error/v1",
            "command": args.command,
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            **_failure_details(args.run),
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
