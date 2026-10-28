#!/usr/bin/env python3
"""Prepare, launch one authorized root model, and audit agent-harness trials.

The root CLI is the only model process this program starts. Native children are
launched and collected by the model under the selected skills.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SKILL_ROOT = REPO / "skills"
LEGACY = REPO / "test" / "experiments" / "ask_agent_parallel_worktrees"
PACKAGES = {
    "agent_harness": SKILL_ROOT / "in-parallel" / "SKILL.md",
    "ask_agent": SKILL_ROOT / "ask-agent" / "SKILL.md",
    "plan_dispatcher": SKILL_ROOT / "plan-dispatcher" / "SKILL.md",
}
EXTERNAL_APPARATUS = (
    LEGACY / "claude_controller.py", LEGACY / "claude_hooks.py",
    LEGACY / "controller.py", LEGACY / "native_trace.py",
)
FORMULAS = ((2, 3), (3, 5), (5, 7), (7, 11), (11, 13))
DEFAULT_WORKER_CAPACITY = 5
RESOURCE_FIXTURE_VERSION = "module-json/v1"


class ExperimentError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _write_new(path: Path, value, *, binary: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value if binary else (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _read(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ExperimentError(f"Expected regular evidence file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _regular_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ExperimentError(f"Expected regular non-symlink evidence file: {path}")
    return path.read_bytes()


def _normalized_request(raw: dict) -> dict:
    sys.path.insert(0, str(SKILL_ROOT / "in-parallel" / "scripts"))
    import harness
    return harness.normalized_request(raw)[0]


def _validate_launch_identity(case_dir: Path, case: dict, launch: dict, process: dict) -> None:
    manifest_path = case_dir / "manifest.json"
    request_path = case_dir / "harness-request.json"
    prompt_path = case_dir / "operator" / "parent-prompt.txt"
    if _read(manifest_path) != case:
        raise ExperimentError("Retained manifest and case identity differ")
    if launch.get("manifest_sha256") != _sha(_regular_bytes(manifest_path)):
        raise ExperimentError("Root launch is not bound to the retained manifest bytes")
    if _sha(_regular_bytes(request_path)) != case.get("request_sha256"):
        raise ExperimentError("Frozen synthetic request bytes changed")
    if _sha(_regular_bytes(prompt_path)) != case.get("prompt_sha256") or launch.get("prompt_sha256") != case.get("prompt_sha256"):
        raise ExperimentError("Root launch is not bound to the retained prompt bytes")
    if launch.get("freeze_sha256") not in (None, case.get("freeze_sha256")):
        raise ExperimentError("Root launch source-freeze identity differs from the prepared case")
    if launch.get("session_id") is None or not isinstance(launch.get("argv"), list) or not launch["argv"]:
        raise ExperimentError("Root launch lacks its native session id or exact argv")
    expected_effort = launch.get("effort", launch.get("reasoning_effort"))
    if (launch.get("cwd") != case.get("caller") or launch.get("model") != case.get("model")
            or expected_effort != case.get("effort")):
        raise ExperimentError("Root launch cwd/model/effort differs from the prepared case")
    process_pid, launch_pid = process.get("pid"), launch.get("pid")
    pid_mismatch = ((launch_pid is not None and
                     (type(launch_pid) is not int or process_pid not in (None, launch_pid)))
                    or (launch_pid is None and type(process_pid) is not int))
    if type(process.get("exit_code")) is not int or pid_mismatch:
        raise ExperimentError("Root process result is not bound to its retained launch process")
    if launch.get("started_epoch") != process.get("started_epoch", launch.get("started_epoch")):
        raise ExperimentError("Root process start time differs from its retained launch")
    if case["provider"] == "claude":
        sys.path.insert(0, str(LEGACY))
        import claude_controller
        expected_argv = claude_controller.build_launch_argv(
            launch["argv"][0], launch["session_id"], case_dir / "operator" / "claude-native" / "settings.json",
            model=case["model"], effort=case["effort"],
        )
        if launch["argv"] != expected_argv:
            raise ExperimentError("Claude root argv differs from the pinned bounded CLI invocation")
        if (not isinstance(launch.get("version"), str)
                or launch["version"].split(maxsplit=1)[0] != "2.1.296"):
            raise ExperimentError("Claude runtime version does not match the recorded 2.1.296 pin")
        settings = case_dir / "operator" / "claude-native" / "settings.json"
        _read(settings)
        if launch.get("settings_sha256") != _sha(_regular_bytes(settings)):
            raise ExperimentError("Claude native settings bytes differ from the launched settings")
        if launch.get("binary_sha256") != _sha(_regular_bytes(Path(launch["argv"][0]))):
            raise ExperimentError("Claude executable bytes differ from the recorded launch hash")
    elif case["provider"] == "grok":
        if launch.get("manifest_sha256") != _sha(manifest_path.read_bytes()):
            raise ExperimentError("Grok root launch manifest hash differs")
        if not isinstance(launch.get("version"), str) or not launch["version"].strip():
            raise ExperimentError("Grok root launch lacks its CLI version")
        if "grok_permission_mode" in case:
            if case["grok_permission_mode"] != "default":
                raise ExperimentError("new Grok cases require the recorded default permission mode")
            sys.path.insert(0, str(LEGACY))
            import controller
            expected_argv = controller.build_launch_argv(
                launch["argv"][0], launch["session_id"], case_dir,
                model=case["model"], effort=case["effort"],
            )
            if launch["argv"] != expected_argv:
                raise ExperimentError("Grok root argv differs from the pinned normal-permission invocation")
            if any(flag in launch["argv"] for flag in ("--always-approve", "--yolo", "--dangerously-skip-permissions")):
                raise ExperimentError("new Grok launch contains a permission-bypass flag")
    else:
        raise ExperimentError("Unknown root provider in retained launch")


def _tree_pin(card: Path) -> dict:
    root = card.resolve(strict=True).parent
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ExperimentError(f"Selected skill packages may not contain symlinks: {path}")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            files[str(path.relative_to(root))] = _sha(path.read_bytes())
    return {"card": str(card.resolve()), "root": str(root), "files": files}


def source_freeze() -> dict:
    packages = {name: _tree_pin(card) for name, card in PACKAGES.items()}
    apparatus = {}
    for path in (HERE / "experiment.py", HERE / "test_audit.py", HERE / "README.md", *EXTERNAL_APPARATUS):
        if not path.is_file() or path.is_symlink():
            raise ExperimentError(f"Selected experiment apparatus is missing or redirected: {path}")
        apparatus[str(path.resolve())] = _sha(path.read_bytes())
    frozen = {"schema": "agent-harness-experiment.freeze/v1", "packages": packages, "apparatus": apparatus}
    frozen["sha256"] = _sha(_canonical(frozen))
    return frozen


def _git(root: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True,
                          env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    if check and proc.returncode:
        raise ExperimentError(f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout.strip()


def _formula(index: int) -> tuple[int, int]:
    if index < 1:
        raise ExperimentError("synthetic task indexes start at one")
    if index <= len(FORMULAS):
        return FORMULAS[index - 1]
    return index + 1, 2 * index + 3


def _task_count(case: dict) -> int:
    return case.get("task_count", case["workers"])


def _effective_capacity(case: dict) -> int:
    return case.get("effective_capacity", case["workers"])


def _resource_metadata(module: str, factor: int, offset: int) -> dict:
    return {"module": module, "factor": factor, "offset": offset,
            "transform_0": offset, "transform_4": factor * 4 + offset}


def _fixture(root: Path, count: int, mode: str = "edit") -> dict:
    root.mkdir(parents=True)
    (root / ".gitignore").write_text("__pycache__/\n*.tmp\n")
    (root / ".claspignore").write_text("node_modules/\n")
    (root / "context").mkdir()
    (root / "context" / "brief.md").write_text("Synthetic fixture only.\n")
    feedback_backlog = root / "tasks" / "in-progress" / "prompt-improvements-backlog.md"
    feedback_backlog.parent.mkdir(parents=True)
    feedback_backlog.write_text("# Prompt Improvement Backlog\n\nGenerated by feedback-collector plugin.\n\n")
    (root / "src").mkdir()
    (root / "src" / "__init__.py").write_text("\"\"\"Synthetic modules for isolated agent-harness trials.\"\"\"\n")
    (root / "scratch").mkdir()
    (root / "scratch" / ".keep").write_text("Synthetic scratch directory.\n")
    expected = []
    for index in range(1, count + 1):
        factor, offset = _formula(index)
        module = f"module_{index:02}.py"
        metadata = f"module_{index:02}.json"
        if mode == "report-only":
            contents = f"def transform(value):\n    return value * {factor} + {offset}\n"
        else:
            contents = "# Implement the formula specified in the task packet.\nraise NotImplementedError\n"
        (root / "src" / module).write_text(contents)
        metadata_path = root / "src" / metadata
        if mode == "report-only":
            metadata_path.write_text(json.dumps(_resource_metadata(f"src/{module}", factor, offset),
                                               sort_keys=True) + "\n")
        else:
            metadata_path.write_text('{"pending": true}\n')
        expected.append((f"src/{module}", factor, offset))
    verifier = [
        "import json",
        "from importlib import import_module",
        "FORMULAS = " + repr(expected),
        "SAMPLES = (-3, 0, 4, 11)",
        "for index, (relative, factor, offset) in enumerate(FORMULAS, 1):",
        "    module = import_module(f'src.module_{index:02}')",
        "    for value in SAMPLES:",
        "        assert module.transform(value) == factor * value + offset, (index, value, module.transform(value))",
        "    with open(relative[:-3] + '.json', encoding='utf-8') as stream:",
        "        metadata = json.load(stream)",
        "    expected_metadata = {'module': relative, 'factor': factor, 'offset': offset,",
        "                         'transform_0': offset, 'transform_4': factor * 4 + offset}",
        "    assert metadata == expected_metadata, (index, metadata)",
        "print(f'PASS: {len(FORMULAS)} complete module/resource pairs')",
    ]
    (root / "verify_modules.py").write_text("\n".join(verifier) + "\n")
    _git(root, "init", "-q")
    _git(root, "config", "--local", "user.name", "Experiment Fixture")
    _git(root, "config", "--local", "user.email", "fixture.invalid")
    _git(root, "add", "--", ".gitignore", ".claspignore", "context/brief.md", "tasks/in-progress/prompt-improvements-backlog.md",
         "src", "scratch", "verify_modules.py")
    _git(root, "commit", "-qm", "synthetic fixture baseline")
    baseline_head = _git(root, "rev-parse", "HEAD")
    (root / ".claspignore").write_text("node_modules/\ncontext/\n")
    (root / "context" / "brief.md").write_text("Synthetic fixture only.\nStaged context change.\n")
    _git(root, "add", "--", ".claspignore", "context/brief.md")
    (root / ".gitignore").write_text("__pycache__/\n*.tmp\nlocal-only/\n")
    (root / ".claspignore").write_text("node_modules/\ncontext/\nlocal-output/\n")
    (root / "context" / "brief.md").write_text("Synthetic fixture only.\nStaged context change.\nUnstaged context change.\n")
    status = _git(root, "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=all")
    status_paths = {entry[3:] for entry in status.split("\0") if entry}
    cached = set(_git(root, "diff", "--cached", "--name-only", "--").splitlines())
    if not {".gitignore", ".claspignore", "context/brief.md"}.issubset(status_paths):
        raise ExperimentError("Synthetic fixture did not retain all dirty controls")
    if cached != {".claspignore", "context/brief.md"}:
        raise ExperimentError(f"Synthetic staged controls differ from the contract: {sorted(cached)}")
    return {
        "head": baseline_head,
        "staged_paths": sorted(cached),
        "required_dirty_paths": [".claspignore", ".gitignore", "context/brief.md"],
        "control_sha256": {path: _sha((root / path).read_bytes())
                           for path in (".claspignore", ".gitignore", "context/brief.md")},
        "owned_paths": [path for i in range(1, count + 1)
                        for path in (f"src/module_{i:02}.py", f"src/module_{i:02}.json")],
        "resource_paths": [f"src/module_{i:02}.json" for i in range(1, count + 1)],
        "verifier": "verify_modules.py",
    }


def _request(case: dict, mode: str, workspace: str, integration: str) -> dict:
    source = Path(case["caller"])
    tasks = []
    task_count = _task_count(case)
    for index in range(1, task_count + 1):
        factor, offset = _formula(index)
        task_id = f"module-{index:02}"
        target = f"src/module_{index:02}.py"
        metadata = f"src/module_{index:02}.json"
        if mode == "edit":
            expected_metadata = _resource_metadata(target, factor, offset)
            objective = (f"Implement transform(value) in {target} as value * {factor} + {offset}, and write {metadata} "
                         f"as JSON with exactly these fields and values: {json.dumps(expected_metadata, sort_keys=True)}. "
                         f"Keep all edits inside {target} and {metadata}.")
            expected = (f"{target} defines transform(value) returning value * {factor} + {offset}, and {metadata} "
                        f"contains exactly {json.dumps(expected_metadata, sort_keys=True)}.")
            writes = [target, metadata]
        elif mode == "ephemeral":
            target = f"scratch/findings_{index:02}.md"
            objective = (f"Inspect the known synthetic formula for module {index:02}: transform(value) = value * {factor} + {offset}. "
                         f"Write a concise findings note to {target} stating that formula, transform(0) = {offset}, and "
                         f"transform(4) = {factor * 4 + offset}. Do not change src/ or commit any files.")
            expected = (f"{target} states transform(value) = value * {factor} + {offset}, transform(0) = {offset}, "
                        f"and transform(4) = {factor * 4 + offset}; no source contribution is imported and no worker commit is created.")
            writes = [target]
        else:
            objective = f"Report the exact implementation for {target}, transform(0), and transform(4). Do not edit any files."
            expected = f"Findings state transform(value) = value * {factor} + {offset}, transform(0) = {offset}, and transform(4) = {factor * 4 + offset}."
            writes = []
        tasks.append({"id": task_id, "objective": objective, "expected_result": expected, "write_set": writes})
    request = {
        "objective": f"Complete {task_count} independent synthetic module tasks using in-parallel in {case['arm']} mode.",
        "source": str(source.resolve()), "workspace": workspace, "mode": mode,
        "tasks": tasks, "integration": integration,
        "checks": [["python3", "-B", "verify_modules.py"]] if mode == "edit" and integration == "apply" else [],
        "writers_quiescent": True if workspace == "worktree" else None,
        "exclusive_writer": True if workspace == "current" and mode == "edit" else None,
        "current_learnings": "The only source payload is this generated synthetic fixture. Preserve its staged and unstaged control files. For native trace instrumentation, run worker-start and worker-finish each in a separate Bash call containing only the exact pinned command, optionally preceded by cd to the assigned cwd and &&. Do not combine these phase calls with edits, checks, commits, output redirection, or other operations.",
        "authorization": "Authorized bounded live experiment: selected root model may delegate only the stated synthetic task through the selected native host and skills.",
    }
    if case.get("capacity_explicit", True):
        request["capacity"] = case.get("requested_capacity", case["workers"])
    return request


def _parent_prompt(case: dict, request_path: Path) -> str:
    task_count = _task_count(case)
    capacity_text = (f"Requested worker capacity: {case['requested_capacity']}; normalized effective capacity: {case['effective_capacity']}."
                     if case.get("capacity_explicit", True) else
                     f"Worker capacity is omitted from the request; production default and mode normalization yield {case['effective_capacity']}.")
    skill_paths = "\n".join(f"- {name}: {path}" for name, path in PACKAGES.items())
    init = _init_argv(case, request_path)
    role = (
        "You are the direct coordinator. Read and follow the complete selected in-parallel skill. "
        "You own init, native worker launch/collection, independent checks, acceptance, and finish."
        if case["arm"] == "direct" else
        "You are the initiating root. Start exactly ONE fresh native coordinator agent and wait for its terminal result. "
        "Pass that child this complete request, all selected absolute skill paths, and the exact init command below. "
        "Do not initialize the harness, start task workers yourself, or start another coordinator."
    )
    coordinator = (
        "The coordinator must read the selected in-parallel SKILL.md and its references/contract.md and "
        "references/hosts.md. The selected Ask Agent and Plan Dispatcher cards below are pinned helper dependencies; "
        "read only their relevant task/dispatcher contract sections if needed, not their complete script trees. "
        "Inspect the live native tool schema; initialize with the exact command; and drive the full recorded lifecycle. "
        "Use one fresh native worker per task, launch every assignment in a returned Dispatcher batch before waiting, and "
        "after any completion refill available capacity while other workers continue; do not add artificial waits or batch barriers. "
        "Have every worker run its exact packet-pinned worker-start and worker-finish "
        "commands in its actual assigned context, each as a standalone shell call (only an optional exact cd cwd && prefix). This is a trace instrumentation requirement; preserve the exact prepared worker prompt. Retain native handles and terminal results, independently verify, accept, "
        "and finish. Do not invoke a model CLI or external API for workers; do not use fake workers or a second root CLI. "
        "For edit mode run the combined verifier after integration. For report-only make no filesystem changes. For ephemeral "
        "mode retain findings in scratch worktrees and import no scratch files. Preserve failed or blocked outcomes."
    )
    return f"""Bounded synthetic agent-harness experiment. No production repository payload is in scope.

{role}

Case: {case['case_id']}
Arm: {case['arm']}
Provider/model/effort: {case['provider']} / {case['model']} / {case['effort']}
Independent task count: {task_count}
{capacity_text}
Mode/workspace/integration: {case['mode']} / {case['workspace']} / {case['integration']}
Synthetic checkout: {case['caller']}
External harness run: {case['harness_run']}
Request file: {request_path}

Selected absolute skill card paths:
{skill_paths}

Exact production harness initialization command (run from the synthetic checkout):
{shlex.join(init)}

{coordinator}

The fixture tasks implement independent known functions in their declared write sets. In edit mode, each task owns one module and its JSON metadata file; the combined verifier checks every pair after integration. Complete all {task_count} task IDs even when the task list exceeds the worker capacity. Keep all changes in the synthetic checkout or helper-managed worktrees. The checkout deliberately starts with staged and unstaged changes in context/brief.md, .gitignore, and .claspignore; do not reset, stash, overwrite, or “clean up” them. The audit checks those bytes and the original parent HEAD/index separately from native evidence.

Use only the synthetic fixture and the selected skill instructions. Do not inspect or include unrelated project files, credentials, or conversation history. Return a concise final outcome and evidence paths; the offline auditor will independently inspect retained host traces and Git state.
"""


def _init_argv(case: dict, request_path: Path) -> list[str]:
    return [sys.executable, "-B", str(SKILL_ROOT / "in-parallel/scripts/harness.py"), "init",
            "--run", case["harness_run"], "--request", str(request_path),
            "--ask-agent-card", str(PACKAGES["ask_agent"]), "--dispatcher-card", str(PACKAGES["plan_dispatcher"])]


def prepare_case(args) -> dict:
    out = args.case.resolve()
    if out.exists() or out.is_symlink():
        raise ExperimentError(f"Case destination already exists; preserve it and choose a fresh directory: {out}")
    if args.provider == "grok" and args.arm != "direct":
        raise ExperimentError("This bounded apparatus supports Grok direct cases only")
    requested_capacity = getattr(args, "workers", None)
    requested_tasks = getattr(args, "tasks", None)
    task_count = requested_tasks if requested_tasks is not None else (requested_capacity if requested_capacity is not None else 3)
    if type(task_count) is not int or task_count < 1:
        raise ExperimentError("task count must be a positive integer")
    if requested_capacity is not None and (type(requested_capacity) is not int or requested_capacity < 1):
        raise ExperimentError("worker capacity must be a positive integer")
    capacity_explicit = requested_capacity is not None
    effective_capacity = requested_capacity if capacity_explicit else min(DEFAULT_WORKER_CAPACITY, task_count)
    model, effort = ("sonnet", "medium") if args.provider == "claude" else ("grok-4.7", "medium")
    workspace = args.workspace or ("worktree" if args.mode in ("edit", "ephemeral") else "current")
    integration = args.integration or ("return-only" if args.mode == "ephemeral" else "apply")
    if workspace == "current" and args.mode == "edit":
        effective_capacity = 1
    if args.mode == "ephemeral" and workspace != "worktree":
        raise ExperimentError("ephemeral mode requires worktree workspace")
    out.mkdir(parents=True)
    case = {
        "schema": "agent-harness-experiment.case/v1", "case_id": str(uuid.uuid4()),
        "provider": args.provider, "model": model, "effort": effort, "arm": args.arm,
        "workers": task_count, "task_count": task_count,
        "requested_capacity": requested_capacity, "effective_capacity": effective_capacity,
        "capacity_explicit": capacity_explicit, "fixture_version": RESOURCE_FIXTURE_VERSION,
        **({"grok_permission_mode": "default"} if args.provider == "grok" else {}),
        "mode": args.mode, "workspace": workspace, "integration": integration,
        "caller": str((out / "caller").resolve()), "harness_run": str((out / "harness").resolve()),
        "prepared_epoch": time.time(),
    }
    case["fixture"] = _fixture(Path(case["caller"]), task_count, args.mode)
    sys.path.insert(0, str(SKILL_ROOT / "in-parallel" / "scripts"))
    import delivery
    case["parent_snapshot"] = delivery.capture(case["caller"])
    case["parent_index_sha256"] = _sha((Path(case["caller"]) / ".git" / "index").read_bytes())
    request = _request(case, args.mode, workspace, integration)
    normalized_request = _normalized_request(request)
    if normalized_request.get("capacity") != effective_capacity:
        raise ExperimentError("normalized request capacity differs from the prepared case")
    # Freeze what init is expected to record, including documented defaults and capacity adjustments.
    request_path = out / "harness-request.json"
    _write_new(request_path, request)
    operator = out / "operator"
    operator.mkdir()
    _write_new(operator / "parent-prompt.txt", _parent_prompt(case, request_path).encode(), binary=True)
    manifest = {**case, "request_path": str(request_path.resolve()),
                "request_sha256": _sha(request_path.read_bytes()),
                "normalized_request_sha256": _sha(_canonical(normalized_request)),
                "prompt_sha256": _sha((operator / "parent-prompt.txt").read_bytes())}
    manifest["source_freeze"] = source_freeze()
    manifest["freeze_sha256"] = manifest["source_freeze"]["sha256"]
    _write_new(out / "case.json", manifest)
    _write_new(out / "manifest.json", manifest)
    return {"status": "PREPARED", "case": str(out), "case_id": case["case_id"],
            "task_count": task_count, "requested_capacity": requested_capacity,
            "effective_capacity": effective_capacity,
            "freeze_sha256": manifest["freeze_sha256"], "prompt": str((operator / "parent-prompt.txt").resolve()),
            "launch": [sys.executable, "-B", str(HERE / "experiment.py"), "launch", "--case", str(out),
                       "--expected-freeze-sha256", manifest["freeze_sha256"], "--authorized-case", case["case_id"]]}


def _claude_launch(case_dir: Path, case: dict, binary: str | None) -> int:
    sys.path.insert(0, str(LEGACY))
    import claude_controller
    import claude_hooks
    operator = case_dir / "operator"
    native = operator / "claude-native"
    hooks = native / "hooks"
    hooks.mkdir(parents=True)
    settings = native / "settings.json"
    claude_hooks.write_settings(settings, hooks, script_path=LEGACY / "claude_hooks.py")
    executable = claude_controller._resolve_binary(binary)
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "CLAUDE_CODE_FORK_SUBAGENT": "0", "DISABLE_AUTOUPDATER": "1"})
    removed = [key for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN") if key in env]
    for key in removed:
        env.pop(key, None)
    version = subprocess.run([str(executable), "--version"], check=True, capture_output=True, text=True, env=env).stdout.strip()
    version_number = version.split(maxsplit=1)[0] if version else ""
    if version_number != "2.1.296":
        raise ExperimentError(f"This Sonnet trial is pinned to Claude Code 2.1.296; observed {version!r}")
    session = str(uuid.uuid4())
    argv = claude_controller.build_launch_argv(executable, session, settings, model=case["model"], effort=case["effort"])
    started = time.time()
    _write_new(operator / "launch.json", {
        "schema": "agent-harness-experiment.claude-launch/v1", "session_id": session, "argv": argv,
        "cwd": case["caller"], "started_epoch": started, "model": case["model"], "effort": case["effort"],
        "version": version, "binary_sha256": _sha(executable.read_bytes()),
        "prompt_sha256": case["prompt_sha256"], "freeze_sha256": case["freeze_sha256"],
        "manifest_sha256": _sha((case_dir / "manifest.json").read_bytes()),
        "settings_sha256": _sha(settings.read_bytes()),
        "environment_overrides": {"PYTHONDONTWRITEBYTECODE": "1", "CLAUDE_CODE_FORK_SUBAGENT": "0",
                                  "DISABLE_AUTOUPDATER": "1", "removed_auth_environment_keys": removed},
    })
    prompt_path = operator / "parent-prompt.txt"
    clock = time.monotonic()
    with prompt_path.open("rb") as prompt, (operator / "stdout.jsonl").open("xb") as stdout, \
            (operator / "observed.jsonl").open("xb") as observed, (operator / "stderr.log").open("xb") as stderr:
        proc = subprocess.Popen(argv, cwd=case["caller"], env=env, stdin=prompt, stdout=subprocess.PIPE, stderr=stderr)
        for raw in proc.stdout:
            now = time.time()
            stdout.write(raw); stdout.flush()
            try:
                event = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                event = {"unparsed": raw.decode("utf-8", errors="replace").rstrip()}
            observed.write((json.dumps({"observed_epoch": now, "elapsed_s": time.monotonic() - clock,
                                        "event": event}, ensure_ascii=False) + "\n").encode())
            observed.flush()
        code = proc.wait()
    finished = time.time()
    events = []
    for line in (operator / "stdout.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
        try: events.append(json.loads(line))
        except json.JSONDecodeError: pass
    usage = [e.get("usage") for e in events if e.get("type") == "result" and isinstance(e.get("usage"), dict)]
    fields = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")
    reported = {key: sum(row[key] for row in usage)
                for key in fields if usage and all(type(row.get(key)) is int for row in usage)}
    complete_input = all(key in reported for key in fields[:3])
    tokens = {
        "scope": "root Claude CLI result events only; child model token totals are unavailable",
        "status": "unavailable" if not usage else ("complete" if complete_input and "output_tokens" in reported else "incomplete"),
        "root_cli": {
            "result_event_count": len(usage),
            "reported_input_tokens": reported.get("input_tokens", "unavailable"),
            "cache_read_input_tokens": reported.get("cache_read_input_tokens", "unavailable"),
            "cache_creation_input_tokens": reported.get("cache_creation_input_tokens", "unavailable"),
            "total_input_tokens": (sum(reported[key] for key in fields[:3]) if complete_input else "incomplete"),
            "output_tokens": reported.get("output_tokens", "unavailable"),
            "raw_usage": usage,
        },
        "child_model_totals": "unavailable",
    }
    _write_new(operator / "process-result.json", {"exit_code": code, "pid": proc.pid,
        "started_epoch": started, "finished_epoch": finished, "elapsed_s": time.monotonic() - clock,
        "tokens": tokens})
    return code


def launch_case(args) -> int:
    case_dir = args.case.resolve(strict=True)
    case = _read(case_dir / "case.json")
    if args.authorized_case != case.get("case_id"):
        raise ExperimentError("Live launch guard requires the exact prepared case id")
    if args.expected_freeze_sha256 != case.get("freeze_sha256"):
        raise ExperimentError("Live launch guard requires the exact prepared source-freeze SHA-256")
    current = source_freeze()
    if current != case.get("source_freeze"):
        raise ExperimentError("Selected skill or experiment apparatus changed after case preparation; keep this attempt and prepare a fresh case")
    if _read(case_dir / "manifest.json") != case:
        raise ExperimentError("Prepared manifest changed; do not launch from mutated case inputs")
    if case.get("request_sha256") != _sha(_regular_bytes(case_dir / "harness-request.json")):
        raise ExperimentError("Prepared request bytes changed; do not launch from mutated case inputs")
    if case.get("prompt_sha256") != _sha(_regular_bytes(case_dir / "operator" / "parent-prompt.txt")):
        raise ExperimentError("Prepared prompt bytes changed; do not launch from mutated case inputs")
    operator = case_dir / "operator"
    if case["provider"] == "claude":
        marker = operator / "experiment-launch-attempt"
        marker.mkdir()
        return _claude_launch(case_dir, case, args.claude_binary)
    if case["provider"] == "grok":
        # The existing external controller starts only the one root CLI and captures its native stream.
        if any((operator / name).exists() for name in ("launch.json", "launch-attempt", "stdout.jsonl", "process-result.json")):
            raise ExperimentError("Grok launch evidence already exists; preserve it and use a new case directory")
        sys.path.insert(0, str(LEGACY))
        import controller
        try:
            return controller.launch(case_dir, args.grok_binary, case["model"], case["effort"])
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            raise
    raise ExperimentError(f"Unsupported provider: {case.get('provider')}")


def _jsonl(path: Path) -> list[dict]:
    if path.is_symlink() or not path.is_file():
        raise ExperimentError(f"Missing native trace: {path}")
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try: row = json.loads(line)
        except json.JSONDecodeError as exc: raise ExperimentError(f"Malformed JSONL {path}:{number}: {exc}") from exc
        if not isinstance(row, dict): raise ExperimentError(f"Non-object JSONL {path}:{number}")
        rows.append(row)
    if not rows: raise ExperimentError(f"Empty native trace: {path}")
    return rows


def audit_native_graph(case: dict, nodes: list[dict]) -> dict:
    """Validate a normalized tree made only from native host events and transcripts."""
    task_count = _task_count(case)
    capacity = _effective_capacity(case)
    expected_workers = {f"module-{i:02}" for i in range(1, task_count + 1)}
    errors = []
    if type(capacity) is not int or capacity < 1:
        errors.append("effective worker capacity is not a positive integer")
        capacity = 0
    by_id = {}
    intervals_by_node = {}
    invalid_interval_nodes = set()
    for node in nodes:
        ident = node.get("id")
        if not isinstance(ident, str) or not ident or ident in by_id:
            errors.append("native node id is missing or duplicated")
        else: by_id[ident] = node
        for key in ("start_epoch", "finish_epoch"):
            if type(node.get(key)) not in (int, float) or node[key] <= 0:
                errors.append(f"native node {ident!r} lacks typed {key}")
        if node.get("terminal") is not True:
            errors.append(f"native node {ident!r} has no terminal event")
        if node.get("finish_epoch", 0) < node.get("start_epoch", 0):
            errors.append(f"native node {ident!r} has a reversed interval")
            invalid_interval_nodes.add(id(node))
        invocation_intervals = node.get("invocation_intervals")
        if invocation_intervals is None:
            invocation_intervals = [{"start_epoch": node.get("start_epoch"),
                                     "finish_epoch": node.get("finish_epoch")}]
        if not isinstance(invocation_intervals, list) or not invocation_intervals:
            errors.append(f"native node {ident!r} lacks invocation intervals")
            intervals_by_node[id(node)] = []
            invalid_interval_nodes.add(id(node))
        else:
            parsed_intervals = []
            for invocation in invocation_intervals:
                if not isinstance(invocation, dict):
                    errors.append(f"native node {ident!r} has an invalid invocation interval")
                    invalid_interval_nodes.add(id(node))
                    continue
                start, finish = invocation.get("start_epoch"), invocation.get("finish_epoch")
                if (type(start) not in (int, float)
                        or type(finish) not in (int, float) or start <= 0 or finish < start):
                    errors.append(f"native node {ident!r} has an invalid invocation interval")
                    invalid_interval_nodes.add(id(node))
                    continue
                parsed_intervals.append((start, finish))
            if parsed_intervals != sorted(parsed_intervals):
                errors.append(f"native node {ident!r} invocation intervals are unordered")
                invalid_interval_nodes.add(id(node))
            if any(parsed_intervals[i][0] < parsed_intervals[i - 1][1]
                   for i in range(1, len(parsed_intervals))):
                errors.append(f"native node {ident!r} has overlapping resumed invocations")
                invalid_interval_nodes.add(id(node))
            if (parsed_intervals and (node.get("start_epoch") != parsed_intervals[0][0]
                                      or node.get("finish_epoch") != parsed_intervals[-1][1])):
                errors.append(f"native node {ident!r} bounds differ from its invocation intervals")
                invalid_interval_nodes.add(id(node))
            intervals_by_node[id(node)] = parsed_intervals
        if node.get("role") == "worker":
            phases = node.get("phase_evidence")
            if (not isinstance(phases, dict)
                    or set(phases) != {"worker-start", "worker-finish"}
                    or phases.get("worker-start", {}).get("status") != "WORKER_CONTEXT_READY"
                    or phases.get("worker-finish", {}).get("status") != "READY_FOR_PARENT_ACCEPTANCE"):
                errors.append(f"native worker {ident!r} lacks exact production worker-start/worker-finish proof")
        if case.get("provider") == "claude" and node.get("role") in {"worker", "coordinator"}:
            launches = node.get("agent_launches")
            if not isinstance(launches, list) or not launches:
                errors.append(f"Claude native child {ident!r} lacks launch-state evidence")
            else:
                for launch in launches:
                    expected_types = {"general-purpose"} if node.get("role") == "worker" else {"claude", "general-purpose"}
                    if (not isinstance(launch, dict) or launch.get("subagent_type") not in expected_types
                            or type(launch.get("effective_is_backgrounded")) is not bool):
                        errors.append(f"Claude native {node.get('role')} {ident!r} has invalid role-specific launch evidence")
                    elif node.get("role") == "worker" and launch["effective_is_backgrounded"] is not True:
                        errors.append(f"Claude native worker {ident!r} was not effectively backgrounded")
    roots = [node for node in nodes if node.get("role") == "root"]
    if len(roots) != 1:
        errors.append("exactly one root CLI session is required")
        root = {}
    else: root = roots[0]
    coordinators = [node for node in nodes if node.get("role") == "coordinator"]
    workers = [node for node in nodes if node.get("role") == "worker"]
    expected_node_count = 1 + task_count + (1 if case["arm"] == "nested" else 0)
    if len(nodes) != expected_node_count:
        errors.append("native tree contains missing or unexpected child sessions")
    task_ids = [node.get("task_id") for node in workers]
    valid_task_ids = [task_id for task_id in task_ids if isinstance(task_id, str)]
    if (len(workers) != task_count or set(valid_task_ids) != expected_workers
            or len(valid_task_ids) != len(task_ids) or len(set(valid_task_ids)) != len(valid_task_ids)):
        errors.append("native worker identities do not equal the requested independent task set")
    if case["arm"] == "direct":
        if coordinators: errors.append("direct arm unexpectedly contains a separate coordinator")
        if any(node.get("parent_id") != root.get("id") for node in workers):
            errors.append("direct native workers are not children of the root coordinator")
    else:
        if len(coordinators) != 1: errors.append("nested arm requires exactly one fresh native coordinator")
        coordinator = coordinators[0] if len(coordinators) == 1 else {}
        if coordinator.get("parent_id") != root.get("id"):
            errors.append("nested coordinator is not the root's native child")
        if any(node.get("parent_id") != coordinator.get("id") for node in workers):
            errors.append("nested native workers are not children of the separate coordinator")
        if coordinator and workers and coordinator.get("finish_epoch", 0) < max(node.get("finish_epoch", 0) for node in workers):
            errors.append("nested coordinator terminated before all native workers")
        worker_finish = max((node.get("finish_epoch", 0) for node in workers), default=0)
        coordinator_stops = coordinator.get("terminal_stop_epochs")
        if case.get("provider") == "claude" and (
                not isinstance(coordinator_stops, list) or not coordinator_stops
                or any(type(epoch) not in (int, float) for epoch in coordinator_stops)):
            errors.append("nested Claude coordinator lacks exact native terminal-stop evidence")
            coordinator_stops = []
        elif case.get("provider") == "claude":
            expected_stops = [finish for _, finish in intervals_by_node.get(id(coordinator), [])]
            if coordinator_stops != expected_stops:
                errors.append("nested Claude coordinator terminal stops differ from its native invocation intervals")
        early_stops = [epoch for epoch in (coordinator_stops or [])
                       if type(epoch) in (int, float) and epoch < worker_finish]
        if early_stops:
            errors.append("nested coordinator returned before all native workers reached terminal hooks")
    if root and workers and root.get("finish_epoch", 0) < max(node.get("finish_epoch", 0) for node in workers):
        errors.append("root CLI terminated before a native worker")
    starts = [node["start_epoch"] for node in workers if isinstance(node.get("start_epoch"), (int, float))]
    intervals = sorted((start, finish, node.get("id") if isinstance(node.get("id"), str) else "", index)
                       for node in workers
                       for index, (start, finish) in enumerate(intervals_by_node.get(id(node), [])))
    points = []
    for start, stop, ident, index in intervals:
        invocation_id = (ident, index)
        points.extend(((start, 1, invocation_id), (stop, -1, invocation_id)))
    def peak_for_tie_order(start_first: bool) -> int:
        active, peak = set(), 0
        for _, delta, ident in sorted(points, key=lambda item: (item[0], -item[1] if start_first else item[1])):
            if delta < 0:
                active.discard(ident)
            else:
                active.add(ident)
                peak = max(peak, len(active))
        return peak

    peak = peak_for_tie_order(False)
    possible_peak = peak_for_tie_order(True)
    coordinator_stops = coordinators[0].get("terminal_stop_epochs", []) if coordinators else []
    worker_intervals_complete = bool(workers) and all(
        id(node) not in invalid_interval_nodes and isinstance(node.get("id"), str)
        for node in workers
    )
    worker_invocation_counts = {
        node.get("task_id"): len(intervals_by_node.get(id(node), [])) for node in workers
    }
    resumed_tasks = sorted(task_id for task_id, count in worker_invocation_counts.items()
                           if isinstance(task_id, str) and count > 1)
    if case.get("fixture_version") == RESOURCE_FIXTURE_VERSION and resumed_tasks:
        errors.append("queued fixture requires one native invocation per task; resumed worker contexts were observed")
    measured_peak = peak if worker_intervals_complete and intervals else "unavailable"
    possible_measured_peak = possible_peak if worker_intervals_complete and intervals else "unavailable"
    if worker_intervals_complete and intervals:
        if peak > capacity:
            errors.append(f"native worker overlap exceeded effective capacity: peak {peak}, capacity {capacity}")
        elif possible_peak > capacity:
            errors.append("native worker capacity cannot be proven because equal-timestamp lifecycle order is unavailable")
    queued_workers = []
    refill_boundary_ambiguous = False
    timed_workers = [node for node in workers if type(node.get("start_epoch")) in (int, float)]
    for node in timed_workers:
        start_epoch = node["start_epoch"]
        earlier = sum(other["start_epoch"] < start_epoch for other in timed_workers)
        tied = sum(other["start_epoch"] == start_epoch for other in timed_workers)
        if earlier >= capacity:
            queued_workers.append(node)
        elif earlier < capacity < earlier + tied:
            refill_boundary_ambiguous = True
    refill_observed = False if queued_workers else None
    for queued in queued_workers:
        launch_epoch = queued.get("start_epoch")
        if type(launch_epoch) not in (int, float):
            continue
        for peer in workers:
            if peer is queued:
                continue
            for start, finish in intervals_by_node.get(id(peer), []):
                if start < launch_epoch < finish:
                    refill_observed = True
                elif start <= launch_epoch <= finish and launch_epoch in (start, finish):
                    refill_boundary_ambiguous = True
    if not queued_workers and task_count > capacity:
        refill_observed = False
    return {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "root_id": root.get("id"), "coordinator_ids": [n.get("id") for n in coordinators],
            "child_ids": sorted(node.get("id") for node in nodes if node.get("role") != "root"),
            "worker_session_ids": sorted(node.get("id") for node in workers),
            "task_ids": sorted(expected_workers),
            "effective_worker_capacity": capacity,
            "native_invocation_count": sum(worker_invocation_counts.values()),
            "resumed_worker_task_ids": resumed_tasks,
            "worker_start_spread_seconds": round(max(starts) - min(starts), 6) if len(starts) == len(workers) and starts else "unavailable",
            "peak_native_worker_overlap": measured_peak,
            "possible_peak_with_equal_timestamp_order_reversed": possible_measured_peak,
            "reached_capacity": peak == capacity if measured_peak != "unavailable" else "unavailable",
            "queued_refill_observed": refill_observed,
            "queued_refill_timestamp_ambiguous": refill_boundary_ambiguous,
            "proof_scope": "Strict native child start/finish intervals; equal timestamps have unknown event order, and tool-call issue times or CPU parallelism are not measured.",
            "coordinator_terminal_stop_epochs": coordinator_stops,
            "worker_intervals": [{"id": n.get("id"), "task_id": n.get("task_id"),
                                  "start_epoch": n.get("start_epoch"), "finish_epoch": n.get("finish_epoch"),
                                  "invocation_intervals": n.get("invocation_intervals", [])} for n in workers]}


def _claude_agent_launch(arguments: dict, event: dict, hook_agent_type: str, role: str | None = None) -> dict:
    """Validate actual native launch identity and keep requested/effective state distinct."""
    if not isinstance(arguments, dict) or not isinstance(event, dict):
        raise ExperimentError("Claude native Agent call lacks an input object")
    agent_type = arguments.get("subagent_type")
    if not isinstance(agent_type, str) or not agent_type or agent_type == "fork":
        raise ExperimentError("Claude native Agent call is not a typed non-fork subagent")
    if (event.get("task_type") != "local_agent"
            or event.get("subagent_type") != agent_type
            or hook_agent_type != agent_type):
        raise ExperimentError("Claude Agent input, task_started event, and lifecycle hook types differ")
    effective = event.get("is_backgrounded")
    if type(effective) is not bool:
        raise ExperimentError("Claude task_started event lacks typed effective background state")
    requested = arguments.get("run_in_background")
    requested_present = "run_in_background" in arguments
    requested_value = requested if requested_present else "omitted"
    if requested_present and type(requested_value) is not bool:
        raise ExperimentError("Claude Agent run_in_background input, when present, is not boolean")
    if role == "worker":
        if agent_type != "general-purpose":
            raise ExperimentError("Claude task worker must use the general-purpose native subagent")
        if effective is not True:
            raise ExperimentError("Claude task worker was not effectively backgrounded by the host")
    elif role == "coordinator" and agent_type not in {"claude", "general-purpose"}:
        raise ExperimentError("Claude nested coordinator must use a tool-capable native subagent")
    elif role is None and agent_type not in {"claude", "general-purpose"}:
        raise ExperimentError("Claude experiment child has an unsupported native subagent type")
    return {"subagent_type": agent_type,
            "requested_run_in_background": requested_value,
            "effective_is_backgrounded": effective,
            "task_type": event.get("task_type"),
            "task_id": event.get("task_id"),
            "tool_use_id": event.get("tool_use_id"),
            "parent_task_id": event.get("parent_task_id")}


def _capture_claude(case_dir: Path, case: dict, retained_dir: Path | None = None) -> tuple[list[dict], dict]:
    operator = case_dir / "operator"
    launch = _read(operator / "launch.json")
    process = _read(operator / "process-result.json")
    _validate_launch_identity(case_dir, case, launch, process)
    events = _jsonl(operator / "stdout.jsonl")
    session = launch.get("session_id")
    if not session or process.get("exit_code") != 0: raise ExperimentError("Claude root CLI did not complete successfully")
    observed = []
    for row in _jsonl(operator / "observed.jsonl"):
        event = row.get("event")
        if not isinstance(event, dict) or event.get("session_id") != session:
            raise ExperimentError("Claude stream event has missing or foreign root session identity")
        observed.append((row, event))
    if events != [event for _, event in observed]:
        raise ExperimentError("Retained Claude raw stdout and observed stream disagree")
    final_rows = [(row, event) for row, event in observed if event.get("type") == "result"]
    if len(final_rows) != 1 or final_rows[0][1].get("is_error") is True:
        raise ExperimentError("Claude stream must retain one successful native root result event")
    root_finished = final_rows[0][0].get("observed_epoch")
    if type(root_finished) not in (int, float) or root_finished > process.get("finished_epoch", 0):
        raise ExperimentError("Claude root result event is not bound before process termination")
    hooks_dir = operator / "claude-native" / "hooks"
    hooks = []
    for path in sorted(hooks_dir.glob("*.json")):
        hook = _read(path)
        payload = hook.get("payload")
        try: raw = json.loads(hook.get("raw_input", ""))
        except (TypeError, ValueError): raw = None
        if hook.get("schema") != "ask-agent.claude-hook/v1" or payload != raw or not isinstance(payload, dict) or payload.get("session_id") != session:
            raise ExperimentError(f"Claude hook is malformed or belongs to another root session: {path}")
        hooks.append((path, hook, payload))
    root_starts = [p for _, _, p in hooks if p.get("hook_event_name") == "SessionStart"]
    root_ends = [p for _, _, p in hooks if p.get("hook_event_name") == "SessionEnd"]
    if len(root_starts) != 1 or len(root_ends) != 1: raise ExperimentError("Claude root session hooks are incomplete or duplicated")
    root_source = Path(root_starts[0].get("transcript_path", ""))
    if not root_source.is_absolute() or not root_source.is_file(): raise ExperimentError("Claude root transcript path is missing")
    root_id = session
    child_hooks = {}
    for path, hook, payload in hooks:
        kind = payload.get("hook_event_name")
        if kind not in ("SubagentStart", "SubagentStop"): continue
        ident = payload.get("agent_id")
        if not isinstance(ident, str) or not ident: raise ExperimentError(f"Claude {kind} hook lacks agent_id")
        row = child_hooks.setdefault(ident, {"starts": [], "stops": []})
        key = "starts" if kind == "SubagentStart" else "stops"
        row[key].append({"path": path, "record": hook, "payload": payload})
    if not child_hooks: raise ExperimentError("No Claude native child hooks were retained")
    retained = retained_dir or (operator / "claude-native" / "retained")
    retained.mkdir(parents=True)
    _write_new(retained / "root.jsonl", root_source.read_bytes(), binary=True)
    transcript_by_id = {}
    hook_parent_by_id = {}
    hook_intervals = {}
    hook_type_by_id = {}
    for ident, pair in child_hooks.items():
        starts = sorted(pair["starts"], key=lambda row: row["record"].get("observed_epoch", 0))
        stops = sorted(pair["stops"], key=lambda row: row["record"].get("observed_epoch", 0))
        if not starts or len(starts) != len(stops):
            raise ExperimentError(f"Claude native lifecycle start/stop counts differ for {ident}")
        intervals, parent_for_id, source_for_id, agent_type = [], None, None, None
        previous_stop = 0
        for start, stop in zip(starts, stops):
            a, b = start["payload"], stop["payload"]
            start_epoch, stop_epoch = start["record"].get("observed_epoch"), stop["record"].get("observed_epoch")
            if type(start_epoch) not in (int, float) or type(stop_epoch) not in (int, float) or start_epoch >= stop_epoch:
                raise ExperimentError(f"Claude native hook interval is missing or reversed for {ident}")
            if start_epoch < previous_stop:
                raise ExperimentError(f"Claude native child {ident} has overlapping resumed invocations")
            if not isinstance(b.get("last_assistant_message"), str) or not b["last_assistant_message"].strip():
                raise ExperimentError(f"Claude child stop hook lacks terminal assistant result for {ident}")
            current_type = a.get("agent_type")
            if not isinstance(current_type, str) or not current_type or b.get("agent_type") != current_type:
                raise ExperimentError(f"Claude native agent type changed or is missing for {ident}")
            if agent_type is not None and current_type != agent_type:
                raise ExperimentError(f"Claude native agent type changed across invocations for {ident}")
            agent_type = current_type
            parent_path = Path(a.get("transcript_path", ""))
            if not parent_path.is_absolute() or str(parent_path) != b.get("transcript_path"):
                raise ExperimentError(f"Claude parent transcript binding changed for {ident}")
            source = Path(b.get("agent_transcript_path", ""))
            if not source.is_absolute() or not source.is_file(): raise ExperimentError(f"Claude child transcript missing for {ident}")
            if parent_for_id is not None and parent_path.resolve() != parent_for_id:
                raise ExperimentError(f"Claude native child {ident} changed parent transcript across invocations")
            if source_for_id is not None and source.resolve() != source_for_id:
                raise ExperimentError(f"Claude native child {ident} changed transcript across invocations")
            parent_for_id, source_for_id = parent_path.resolve(), source.resolve()
            intervals.append({"start_epoch": start_epoch, "finish_epoch": stop_epoch})
            previous_stop = stop_epoch
        destination = retained / f"{ident}.jsonl"
        _write_new(destination, source_for_id.read_bytes(), binary=True)
        transcript_by_id[ident] = source_for_id
        hook_parent_by_id[ident] = parent_for_id
        hook_intervals[ident] = intervals
        hook_type_by_id[ident] = agent_type
    known_parents = {root_source.resolve(), *[p.resolve() for p in transcript_by_id.values()]}
    if any(path not in known_parents for path in hook_parent_by_id.values()): raise ExperimentError("Claude child hook parent transcript is not in the retained native tree")
    # Confirm every hook invocation corresponds to one Agent tool use plus task_started event.
    event_by_parent = {root_source.resolve(): events}
    for ident, source in transcript_by_id.items(): event_by_parent[source.resolve()] = _jsonl(source)
    children_by_parent = {}
    for ident, parent_path in hook_parent_by_id.items(): children_by_parent.setdefault(parent_path, []).append(ident)
    task_starts_by_tool = {}
    task_starts_by_id = {}
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "task_started":
            task_starts_by_tool.setdefault(event.get("tool_use_id"), []).append(event)
            task_starts_by_id.setdefault(event.get("task_id"), []).append(event)
    native_nodes = [{"id": root_id, "parent_id": None, "role": "root", "start_epoch": launch.get("started_epoch"),
                     "finish_epoch": root_finished, "terminal": process.get("exit_code") == 0,
                     "transcript_path": str(root_source)}]
    launch_to_child = {}
    launch_parent_path = {}
    launch_records_by_child = {ident: [] for ident in child_hooks}
    for parent_path, ids in children_by_parent.items():
        parent_events = event_by_parent[parent_path]
        calls = {}
        for event in parent_events:
            if event.get("type") == "assistant":
                message = event.get("message", {})
                for block in message.get("content", []) if isinstance(message, dict) and isinstance(message.get("content"), list) else []:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Agent":
                        if not isinstance(block.get("id"), str) or block["id"] in calls:
                            raise ExperimentError("Claude parent transcript has a missing or duplicate Agent tool-use id")
                        calls[block["id"]] = block
        matched_ids = set()
        parent_agent_id = next((parent_id for parent_id, path in transcript_by_id.items()
                                if path.resolve() == parent_path), None)
        all_child_events = [event for ident in ids for event in task_starts_by_id.get(ident, [])]
        if parent_path != root_source.resolve() and any(
                event.get("parent_task_id") != parent_agent_id for event in all_child_events):
            raise ExperimentError("Claude task_started parent id differs from its native parent transcript")
        for ident in ids:
            candidates = [event for event in task_starts_by_id.get(ident, [])
                          if event.get("tool_use_id") in calls]
            if len(candidates) != len(hook_intervals[ident]):
                raise ExperimentError(f"Claude child {ident} hook count does not match its native task_started events")
            if any(event.get("task_type") != "local_agent" for event in candidates):
                raise ExperimentError(f"Claude child {ident} was not started as a native local agent")
            for event in candidates:
                tool_id = event.get("tool_use_id")
                if tool_id in matched_ids:
                    raise ExperimentError("Claude Agent tool use is ambiguously reused")
                block = calls[tool_id]
                arguments = block.get("input") if isinstance(block, dict) else None
                evidence = _claude_agent_launch(arguments, event, hook_type_by_id[ident])
                launch_records_by_child[ident].append({"arguments": arguments, "event": event, "evidence": evidence})
                matched_ids.add(tool_id)
                launch_to_child[tool_id] = ident
                launch_parent_path[tool_id] = parent_path
        if len(calls) != len(matched_ids):
            raise ExperimentError("Claude parent transcript has unbound or extra native Agent calls")
        if len(all_child_events) != len(calls):
            raise ExperimentError("Claude parent transcript and native task_started events have different call counts")
        for ident in ids:
            launch_records_by_child[ident].sort(key=lambda row: list(calls).index(row["evidence"]["tool_use_id"]))
            if len(launch_records_by_child[ident]) != len(hook_intervals[ident]):
                raise ExperimentError(f"Claude native child {ident} has missing launch input evidence")
    forwarded = 0
    for _, event in observed:
        parent_tool = event.get("parent_tool_use_id")
        forwarded_agent = event.get("agent_id")
        if parent_tool is None and forwarded_agent is None:
            continue
        if (not isinstance(parent_tool, str) or not parent_tool
                or not isinstance(forwarded_agent, str) or not forwarded_agent
                or launch_to_child.get(parent_tool) != forwarded_agent
                or forwarded_agent not in hook_parent_by_id
                or launch_parent_path.get(parent_tool) != hook_parent_by_id[forwarded_agent]):
            raise ExperimentError("Claude forwarded parent_tool_use_id/agent_id does not match the hook-bound native tree")
        forwarded += 1
    prepared_rows = []
    harness = Path(case["harness_run"])
    for prepared_path in sorted((harness / "prepared").glob("*.json")):
        prepared_rows.append(_read(prepared_path))
    if len(prepared_rows) != case["workers"]: raise ExperimentError("Production harness did not retain one prepared task per worker")
    packets_by_scope = {}
    for prepared in prepared_rows:
        commands = prepared.get("commands", {})
        packet = _read(Path(prepared["packet"]["path"])) if isinstance(prepared.get("packet"), dict) else None
        task = packet.get("task") if isinstance(packet, dict) else None
        writes = task.get("write_set") if isinstance(task, dict) else None
        if not isinstance(writes, list) or len(writes) > 1: raise ExperimentError("Prepared worker packet has ambiguous write scope")
        key = writes[0] if writes else task.get("expected_result")
        packets_by_scope[key] = commands
    child_nodes = {}
    for ident, transcript_path in transcript_by_id.items():
        records = _jsonl(transcript_path)
        phase_matches = []
        for key, commands in packets_by_scope.items():
            phases = _claude_phase_evidence(records, commands, case)
            if phases: phase_matches.append((key, phases))
        if len(phase_matches) > 1: raise ExperimentError(f"Claude child {ident} matches multiple prepared tasks")
        if case["arm"] == "direct" and len(phase_matches) != 1:
            raise ExperimentError(f"Claude direct worker {ident} lacks exact standalone successful start/finish evidence; compound shell phase invocations are not qualified by this auditor")
        role = "worker" if len(phase_matches) == 1 else "coordinator"
        launch_records = launch_records_by_child[ident]
        if not launch_records:
            raise ExperimentError(f"Claude native child {ident} has no correlated Agent launch")
        agent_launches = []
        invocation_intervals = []
        for launch_record, interval in zip(launch_records, hook_intervals[ident]):
            evidence = _claude_agent_launch(launch_record["arguments"], launch_record["event"],
                                            hook_type_by_id[ident], role=role)
            agent_launches.append({"subagent_type": evidence["subagent_type"],
                                   "requested_run_in_background": evidence["requested_run_in_background"],
                                   "effective_is_backgrounded": evidence["effective_is_backgrounded"],
                                   "task_type": evidence["task_type"],
                                   "task_id": evidence["task_id"],
                                   "tool_use_id": evidence["tool_use_id"],
                                   "parent_task_id": evidence["parent_task_id"]})
            invocation_intervals.append({**interval, "tool_use_id": evidence["tool_use_id"]})
        task_id = None
        if role == "worker":
            key, phases = phase_matches[0]
            task_id = next((t["id"] for t in _read(case_dir / "harness-request.json")["tasks"]
                            if key in t["write_set"] or (not t["write_set"] and t["expected_result"] == key)), None)
            if not task_id: raise ExperimentError(f"Claude worker {ident} cannot map to exact task id")
            start_epoch = invocation_intervals[0]["start_epoch"]
            finish_epoch = invocation_intervals[-1]["finish_epoch"]
            child_nodes[ident] = {"id": ident, "parent_id": None, "role": role, "task_id": task_id,
                                  "start_epoch": start_epoch, "finish_epoch": finish_epoch, "terminal": True,
                                  "invocation_intervals": invocation_intervals,
                                  "terminal_stop_epochs": [row["finish_epoch"] for row in invocation_intervals],
                                  "agent_launches": agent_launches,
                                  "phase_evidence": phases, "transcript_path": str(transcript_path),
                                  "transcript_sha256": _sha((retained / f"{ident}.jsonl").read_bytes())}
        else:
            start_epoch = invocation_intervals[0]["start_epoch"]
            finish_epoch = invocation_intervals[-1]["finish_epoch"]
            if case["arm"] == "nested" and hook_parent_by_id[ident] == root_source.resolve():
                coordinator_prompt = launch_records[0]["arguments"].get("prompt")
                request_path = case_dir / "harness-request.json"
                required = [case["case_id"], case["caller"], case["harness_run"],
                            str(request_path.resolve()), shlex.join(_init_argv(case, request_path)),
                            *(str(path.resolve()) for path in PACKAGES.values())]
                if not isinstance(coordinator_prompt, str) or any(value not in coordinator_prompt for value in required):
                    raise ExperimentError("Nested root Agent prompt does not bind the exact case, request, paths, and production init command")
            child_nodes[ident] = {"id": ident, "parent_id": None, "role": role,
                                  "start_epoch": start_epoch, "finish_epoch": finish_epoch,
                                  "initial_finish_epoch": invocation_intervals[0]["finish_epoch"],
                                  "invocation_intervals": invocation_intervals,
                                  "terminal_stop_epochs": [row["finish_epoch"] for row in invocation_intervals],
                                  "agent_launches": agent_launches,
                                  "terminal": True, "transcript_path": str(transcript_path),
                                  "transcript_sha256": _sha((retained / f"{ident}.jsonl").read_bytes())}
    for ident, node in child_nodes.items():
        parent_path = hook_parent_by_id[ident]
        if parent_path == root_source.resolve(): node["parent_id"] = root_id
        else:
            parent_ids = [candidate for candidate, path in transcript_by_id.items() if path.resolve() == parent_path]
            if len(parent_ids) != 1: raise ExperimentError(f"Native parent agent for {ident} is ambiguous")
            node["parent_id"] = parent_ids[0]
    if case["arm"] == "nested":
        coordinator_candidates = [node for node in child_nodes.values() if node["role"] == "coordinator" and node["parent_id"] == root_id]
        if len(coordinator_candidates) != 1: raise ExperimentError("Nested root did not start exactly one native coordinator")
        coordinator_candidates[0]["role"] = "coordinator"
    nodes = [native_nodes[0], *child_nodes.values()]
    # Every direct native worker must execute its pinned production start and finish commands.
    if any(node.get("role") != "worker" for node in nodes[1:] if node.get("parent_id") != root_id and case["arm"] == "direct"):
        raise ExperimentError("Direct arm contains a non-worker native child")
    return nodes, {"hooks": len(hooks), "retained_transcripts": len(transcript_by_id) + 1,
                   "forwarded_events_correlated": forwarded,
                   "root_session_id": session, "native_evidence": str(retained),
                   "root_launch": {key: launch.get(key) for key in
                                   ("argv", "cwd", "model", "effort", "version", "binary_sha256",
                                    "manifest_sha256", "prompt_sha256", "freeze_sha256", "started_epoch")},
                   "root_process": {key: process.get(key) for key in
                                    ("pid", "exit_code", "started_epoch", "finished_epoch", "elapsed_s")}}


def _claude_phase_evidence(records: list[dict], commands: dict, case: dict):
    found = {}
    calls, results = _claude_calls(records)
    if any(call["name"] == "Bash" and _contains_external_model_cli(call.get("input", {}).get("command", "")) for call in calls):
        raise ExperimentError("A Claude native child transcript shell-launched another model CLI")
    for phase in ("worker-start", "worker-finish"):
        expected = commands.get(phase)
        if not isinstance(expected, dict): return None
        expected_argv, cwd = expected.get("argv"), expected.get("cwd")
        if not isinstance(expected_argv, list) or not isinstance(cwd, str): return None
        expected_command = shlex.join(expected_argv)
        matching = [call for call in calls if call["name"] == "Bash" and _command_matches(
            call.get("input", {}).get("command", ""), cwd, expected_command)]
        if len(matching) != 1: return None
        call = matching[0]
        rows = results.get(call.get("id"), [])
        if len(rows) != 1 or rows[0].get("is_error") is not False: return None
        text = _content_text(rows[0].get("content"))
        try:
            value = json.loads(text.strip().splitlines()[-1])
        except (ValueError, IndexError): return None
        status = "WORKER_CONTEXT_READY" if phase == "worker-start" else "READY_FOR_PARENT_ACCEPTANCE"
        if value.get("status") != status or (phase == "worker-finish" and value.get("command") != "worker-finish"): return None
        found[phase] = {"argv": expected_argv, "cwd": cwd, "tool_use_id": call["id"], "status": status}
    return found


def _claude_calls(records):
    calls, results = [], {}
    for event in records:
        if event.get("type") == "assistant":
            message = event.get("message", {})
            content = message.get("content", []) if isinstance(message, dict) else []
            for item in content if isinstance(content, list) else []:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    calls.append({"id": item.get("id"), "name": item.get("name"), "input": item.get("input", {})})
        message = event.get("message", {})
        content = message.get("content", []) if isinstance(message, dict) else []
        for item in content if isinstance(content, list) else []:
            if isinstance(item, dict) and item.get("type") == "tool_result":
                results.setdefault(item.get("tool_use_id"), []).append(item)
    return calls, results


def _content_text(content):
    if isinstance(content, str): return content
    if isinstance(content, list): return "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
    return ""


def _command_matches(observed: str, cwd: str, expected: str) -> bool:
    """Require a standalone phase invocation; arbitrary shell programs are unqualified."""
    try:
        tokens = shlex.split(observed)
    except ValueError:
        return False
    if len(tokens) >= 4 and tokens[0] == "cd" and Path(tokens[1]).resolve() == Path(cwd).resolve() and tokens[2] == "&&":
        observed = shlex.join(tokens[3:])
    return observed.strip() == expected


def _contains_external_model_cli(command: str) -> bool:
    try: tokens = shlex.split(command)
    except ValueError: return True
    forbidden = {"claude", "codex", "grok", "gemini", "aider"}
    return any(Path(token).name.lower() in forbidden for token in tokens)


def _capture_grok(case_dir: Path, case: dict, session_root: Path | None, *, retained_dir: Path | None = None):
    sys.path.insert(0, str(LEGACY))
    import native_trace
    operator = case_dir / "operator"
    launch, process = _read(operator / "launch.json"), _read(operator / "process-result.json")
    _validate_launch_identity(case_dir, case, launch, process)
    if process.get("exit_code") != 0: raise ExperimentError("Grok root CLI did not complete successfully")
    root_path = native_trace._session_updates_path(case_dir, launch, session_root or (Path.home() / ".grok" / "sessions"))
    retained_base = retained_dir or (operator / "native-evidence")
    retained = retained_base / "root-updates.jsonl"
    native_trace._retain_transcript(root_path, retained)
    updates = native_trace._root_updates(retained, launch["session_id"])
    calls = [row for row in updates if row["update"].get("sessionUpdate") == "tool_call"
             and row["update"].get("title") == "spawn_subagent"]
    receipts = [row for row in updates if row["update"].get("sessionUpdate") == "subagent_spawned"]
    finishes = [row for row in updates if row["update"].get("sessionUpdate") == "subagent_finished"]
    if len(calls) != case["workers"] or len(receipts) != case["workers"] or len(finishes) != case["workers"]:
        raise ExperimentError("Grok direct native spawn/receipt/terminal counts do not equal requested worker count")
    nodes = [{"id": launch["session_id"], "parent_id": None, "role": "root",
              "start_epoch": launch.get("started_epoch"), "finish_epoch": process.get("finished_epoch"),
              "terminal": True, "transcript_path": str(retained)}]
    child_root = retained_base / "children"
    child_root.mkdir(parents=True)
    tasks = _read(case_dir / "harness-request.json")["tasks"]
    child_by_id = {}
    for receipt_row in receipts:
        receipt = receipt_row["update"]
        child_id = receipt.get("child_session_id")
        if not isinstance(child_id, str) or receipt.get("parent_session_id") != launch["session_id"] or receipt.get("subagent_id") != child_id:
            raise ExperimentError("Grok native child receipt is not bound to exact root session")
        if receipt.get("effective_context_source") != "new" or receipt.get("subagent_type") != "general-purpose":
            raise ExperimentError("Grok worker receipt does not prove a fresh general-purpose native context")
        if child_id in child_by_id: raise ExperimentError("Grok duplicated a native child session")
        child_by_id[child_id] = receipt
    matched_tasks = set()
    for call_row in calls:
        update = call_row["update"]
        raw = update.get("rawInput")
        if not isinstance(raw, dict): raise ExperimentError("Grok spawn call lacks typed native input")
        description = raw.get("description")
        candidates = [row for row in receipts if row["update"].get("description") == description]
        if len(candidates) != 1: raise ExperimentError("Grok native spawn call does not uniquely match a receipt")
        receipt = candidates[0]["update"]
        matches = [task for task in tasks if task["objective"] in str(raw.get("prompt", ""))
                   or task["id"] in str(raw.get("prompt", "")) or any(path in str(raw.get("prompt", "")) for path in task["write_set"])]
        if len(matches) != 1: raise ExperimentError("Grok native spawn prompt does not uniquely bind to one task")
        task = matches[0]
        if task["id"] in matched_tasks: raise ExperimentError("Grok launched one task more than once")
        matched_tasks.add(task["id"])
        child_id = receipt["child_session_id"]
        cwd = raw.get("cwd")
        if not isinstance(cwd, str) or not Path(cwd).is_absolute(): raise ExperimentError("Grok native worker cwd is missing")
        source = native_trace._child_updates_path(cwd, child_id, session_root or (Path.home() / ".grok" / "sessions"))
        destination = child_root / child_id / "updates.jsonl"
        destination.parent.mkdir(parents=True)
        native_trace._retain_transcript(source, destination)
        child_updates = native_trace._root_updates(destination, child_id)
        prepared = _find_prepared(case_dir / "harness", task["id"])
        commands = prepared.get("commands", {})
        phases = _grok_phase_evidence(child_updates, commands)
        journal = _jsonl(retained)
        start_epoch = _native_grok_time(journal, launch["session_id"], "subagent_spawned", child_id)
        finish_epoch = _native_grok_time(journal, launch["session_id"], "subagent_finished", child_id)
        nodes.append({"id": child_id, "parent_id": launch["session_id"], "role": "worker", "task_id": task["id"],
                      "start_epoch": start_epoch, "finish_epoch": finish_epoch, "terminal": finish_epoch is not None,
                      "phase_evidence": phases, "transcript_path": str(destination),
                      "transcript_sha256": _sha(destination.read_bytes())})
    if matched_tasks != {task["id"] for task in tasks}: raise ExperimentError("Grok native children do not cover every task")
    _grok_completion_order(updates, finishes)
    return nodes, {"root_session_id": launch["session_id"], "retained_root": str(retained),
                   "retained_children": len(child_by_id),
                   "root_launch": {key: launch.get(key) for key in
                                   ("argv", "cwd", "model", "reasoning_effort", "version", "binary_sha256",
                                    "manifest_sha256", "prompt_sha256", "started_epoch")},
                   "root_process": {key: process.get(key) for key in
                                    ("pid", "exit_code", "started_epoch", "finished_epoch", "elapsed_s")}}


def _grok_completion_order(updates: list[dict], finishes: list[dict]) -> None:
    turns = [row for row in updates if row["update"].get("sessionUpdate") == "turn_completed"]
    if (not turns or not finishes or turns[-1]["update"].get("stop_reason") != "end_turn"
            or max(row["line"] for row in finishes) >= turns[-1]["line"]
            or any(row["update"].get("status") != "completed" for row in finishes)):
        raise ExperimentError("Grok root native trace does not prove every worker completed before coordinator final")


def _find_prepared(harness: Path, task_id: str):
    for path in sorted((harness / "prepared").glob("*.json")):
        prepared = _read(path)
        packet_path = prepared.get("packet", {}).get("path")
        if packet_path:
            packet = _read(Path(packet_path))
            task = packet.get("task", {})
            if task_id in str(task.get("objective", "")) or any(task_id in p for p in task.get("write_set", [])):
                return prepared
            # Task IDs are coordinator-owned, so map by the exact frozen objective/write set below.
    request = _read(harness.parent / "harness-request.json")
    expected = next(task for task in request["tasks"] if task["id"] == task_id)
    for path in sorted((harness / "prepared").glob("*.json")):
        prepared = _read(path)
        packet_path = prepared.get("packet", {}).get("path")
        packet = _read(Path(packet_path)) if packet_path else {}
        task = packet.get("task", {})
        if task.get("expected_result") == expected["expected_result"] and task.get("write_set") == expected["write_set"]:
            return prepared
    raise ExperimentError(f"No prepared production packet matches {task_id}")


def _grok_phase_evidence(updates: list[dict], commands: dict) -> dict:
    evidence = {}
    for phase in ("worker-start", "worker-finish"):
        command = commands.get(phase, {})
        argv, cwd = command.get("argv"), command.get("cwd")
        if not isinstance(argv, list) or not argv or not isinstance(cwd, str):
            raise ExperimentError(f"Grok prepared packet lacks an exact {phase} argv/cwd")
        expected = shlex.join(argv)
        matches = []
        for row in updates:
            update = row["update"]
            if update.get("sessionUpdate") != "tool_call": continue
            raw = update.get("rawInput")
            observed = raw.get("command") if isinstance(raw, dict) else None
            if (isinstance(observed, str) and update.get("title") == "run_terminal_command"
                    and _command_matches(observed, cwd, expected)):
                matches.append((row, update))
        if len(matches) != 1: raise ExperimentError(f"Grok worker transcript does not record exactly one pinned {phase} command")
        call, update = matches[0]
        tool_id = update.get("toolCallId")
        terminals = [row["update"] for row in updates if row["update"].get("sessionUpdate") == "tool_call_update"
                     and row["update"].get("toolCallId") == tool_id
                     and row["update"].get("status") in {"completed", "failed", "cancelled", "canceled"}]
        if len(terminals) != 1: raise ExperimentError(f"Grok {phase} native command has no unique terminal tool result")
        terminal = terminals[0]
        output = terminal.get("rawOutput")
        if (terminal.get("status") != "completed" or not isinstance(output, dict)
                or output.get("type") != "Bash" or type(output.get("exit_code")) is not int
                or output.get("exit_code") != 0 or output.get("truncated") is not False):
            raise ExperimentError(f"Grok {phase} native command did not return an untruncated zero-exit Bash result")
        try:
            payload = output.get("output")
            if isinstance(payload, list) and all(type(value) is int and 0 <= value <= 255 for value in payload):
                payload = bytes(payload).decode("utf-8")
            if not isinstance(payload, str):
                raise TypeError("Bash output must be text or a UTF-8 byte array")
            result = json.loads(payload.strip())
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ExperimentError(f"Grok {phase} terminal output is not the production command's JSON result") from exc
        status = "WORKER_CONTEXT_READY" if phase == "worker-start" else "READY_FOR_PARENT_ACCEPTANCE"
        if (not isinstance(result, dict) or result.get("status") != status
                or (phase == "worker-finish" and result.get("command") != "worker-finish")):
            raise ExperimentError(f"Grok {phase} terminal JSON does not carry the exact production success result")
        evidence[phase] = {"argv": argv, "cwd": cwd, "tool_call_id": tool_id,
                           "call_line": call.get("line"), "terminal_status": terminal.get("status"),
                           "exit_code": output["exit_code"], "status": status}
    return evidence


def _read_observed(path: Path):
    rows = _jsonl(path)
    return rows


def _ephemeral_worker_audit(case_dir: Path, case: dict, raw_request: dict, prepared_rows: list[dict]) -> dict:
    """Verify findings against each packet's exact inherited workspace baseline."""
    errors = []
    tasks = raw_request.get("tasks")
    mode = raw_request.get("mode")
    if not isinstance(tasks, list) or mode != "ephemeral":
        return {"status": "FAIL", "errors": ["ephemeral request lacks a typed task list or top-level ephemeral mode"], "workers": []}
    run_root = (Path(case["harness_run"]) / "workspaces" / "attempts").resolve()
    packet_root = (Path(case["harness_run"]) / "packets").resolve()
    expected_store = (Path(case["harness_run"]) / "workspaces").resolve()
    sys.path.insert(0, str(SKILL_ROOT / "ask-agent" / "scripts"))
    import ask_agent_workspace
    prepared_by_task = {}
    for prepared in prepared_rows:
        packet_info = prepared.get("packet")
        packet_path = Path(packet_info.get("path", "")) if isinstance(packet_info, dict) else Path()
        if not packet_path.is_absolute() or packet_path.is_symlink() or not packet_path.is_file():
            errors.append("ephemeral prepared task lacks its retained regular packet")
            continue
        try:
            packet_path.resolve(strict=True).relative_to(packet_root)
        except (OSError, ValueError):
            errors.append("ephemeral prepared packet escapes the harness packet store")
            continue
        packet = _read(packet_path)
        packet_task = packet.get("task") if isinstance(packet, dict) else None
        matches = [task for task in tasks if isinstance(packet_task, dict) and all(
            packet_task.get(key) == task.get(key) for key in ("objective", "expected_result", "write_set"))
            and packet_task.get("mode") == mode]
        if len(matches) != 1:
            errors.append("ephemeral prepared packet does not uniquely match the frozen request")
            continue
        task_id = matches[0].get("id")
        if task_id in prepared_by_task:
            errors.append(f"ephemeral task {task_id!r} has duplicate prepared worktrees")
            continue
        prepared_by_task[task_id] = (matches[0], prepared, packet)
    expected_ids = {task.get("id") for task in tasks if isinstance(task, dict)}
    if set(prepared_by_task) != expected_ids:
        errors.append("ephemeral prepared worktrees do not equal the requested task set")
    workers = []
    baseline_head = case.get("fixture", {}).get("head")
    for task in tasks:
        if not isinstance(task, dict) or task.get("id") not in prepared_by_task:
            continue
        task_id, writes = task.get("id"), task.get("write_set")
        task_row, prepared, packet = prepared_by_task[task_id]
        record = None
        workspace_delta = []
        status_paths = []
        launch = prepared.get("launch", {})
        commands = prepared.get("commands", {})
        workspace = packet.get("workspace", {})
        start, finish = commands.get("worker-start", {}), commands.get("worker-finish", {})
        cwd_value = start.get("cwd") if isinstance(start, dict) else None
        if (launch.get("mode") != "ephemeral" or launch.get("delivery_header") != "No commit — findings only"
                or not isinstance(writes, list) or len(writes) != 1):
            errors.append(f"ephemeral worker {task_id} lacks findings-only launch scope")
            continue
        if not isinstance(cwd_value, str) or not cwd_value or finish.get("cwd") != cwd_value or launch.get("cwd") != cwd_value:
            errors.append(f"ephemeral worker {task_id} start/finish/launch contexts differ")
            continue
        cwd = Path(cwd_value)
        try:
            resolved_cwd = cwd.resolve(strict=True)
            resolved_cwd.relative_to(run_root)
        except (OSError, ValueError):
            errors.append(f"ephemeral worker {task_id} context escapes retained attempt worktrees")
            continue
        if (not isinstance(workspace, dict) or workspace.get("route") != "worktree"
                or workspace.get("source") != case.get("caller")
                or workspace.get("root") != str(resolved_cwd)
                or workspace.get("launch_cwd") != str(resolved_cwd)):
            errors.append(f"ephemeral worker {task_id} packet workspace does not bind its assigned worktree")
            continue
        write_path = writes[0]
        task_match = re.fullmatch(r"module-(\d{2})", task_id or "")
        if not isinstance(write_path, str) or not task_match:
            errors.append(f"ephemeral worker {task_id} has an unexpected findings path or id")
            continue
        expected_path = f"scratch/findings_{int(task_match.group(1)):02}.md"
        if write_path != expected_path:
            errors.append(f"ephemeral worker {task_id} write scope differs from the synthetic findings path")
        note_path = resolved_cwd / write_path
        note_text = None
        note_sha = None
        if note_path.is_symlink() or not note_path.is_file():
            errors.append(f"ephemeral worker {task_id} has no retained regular findings note")
        else:
            note_bytes = note_path.read_bytes()
            note_text = note_bytes.decode("utf-8", errors="replace")
            note_sha = _sha(note_bytes)
            index = int(task_match.group(1))
            if not 1 <= index <= _task_count(case):
                errors.append(f"ephemeral worker {task_id} has no known synthetic formula")
            else:
                factor, offset = _formula(index)
                compact = re.sub(r"\s+", "", note_text).lower()
                expected_formula = f"transform(value)=value*{factor}+{offset}".lower()
                if expected_formula not in compact:
                    errors.append(f"ephemeral findings note for {task_id} omits the exact known formula")
                if not re.search(rf"transform\s*\(\s*0\s*\)\s*=\s*{offset}(?!\d)", note_text, re.IGNORECASE):
                    errors.append(f"ephemeral findings note for {task_id} omits the correct transform(0) value")
                if not re.search(rf"transform\s*\(\s*4\s*\)\s*=\s*{factor * 4 + offset}(?!\d)", note_text, re.IGNORECASE):
                    errors.append(f"ephemeral findings note for {task_id} omits the correct transform(4) value")
        try:
            sys.path.insert(0, str(SKILL_ROOT / "ask-agent" / "scripts"))
            import ask_agent_workspace
            receipt_path = Path(workspace.get("receipt", ""))
            receipt_path.resolve(strict=True).relative_to(run_root)
            record = ask_agent_workspace._load_receipt(receipt_path)
            baseline_state = record["baseline_data"]["worker_state"]
            current_state = ask_agent_workspace._worker_state(resolved_cwd)
            workspace_delta = ask_agent_workspace._changes(baseline_state, current_state)
            worker_head = _git(resolved_cwd, "rev-parse", "HEAD")
            if (worker_head != baseline_head or worker_head != baseline_state.get("head")
                    or current_state.get("branch") != baseline_state.get("branch")):
                errors.append(f"ephemeral worker {task_id} created or switched to a contribution commit")
            if (record.get("receipt_path") != workspace.get("receipt")
                    or record.get("baseline_path") != workspace.get("baseline")
                    or record.get("worktree") != str(resolved_cwd)
                    or record.get("store_path") != expected_store
                    or record["baseline_data"].get("worker_state_fingerprint") != workspace.get("prepared_fingerprint")):
                errors.append(f"ephemeral worker {task_id} packet, receipt, and prepared baseline differ")
            expected_delta = [{"path": expected_path, "change": "added", "layers": ["filesystem"]}]
            if workspace_delta != expected_delta:
                errors.append(f"ephemeral worker {task_id} changed inherited workspace state beyond its findings note: {workspace_delta}")
            status = _git(resolved_cwd, "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=all")
            status_paths = sorted(entry[3:] for entry in status.split("\0") if entry)
        except (ExperimentError, ask_agent_workspace.WorkspaceError, OSError, ValueError,
                KeyError, TypeError, subprocess.SubprocessError) as exc:
            worker_head = "unavailable"
            status_paths, workspace_delta = [], []
            errors.append(f"ephemeral worker {task_id} baseline/Git evidence failed: {exc}")
        source_checks = []
        for source_rel in case.get("fixture", {}).get("owned_paths", []):
            source_path = resolved_cwd / source_rel
            try:
                baseline = subprocess.run(["git", "-C", str(resolved_cwd), "show", f"{baseline_head}:{source_rel}"],
                                          capture_output=True, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
                unchanged = baseline.returncode == 0 and not source_path.is_symlink() and source_path.is_file() and source_path.read_bytes() == baseline.stdout
            except OSError:
                unchanged = False
            source_checks.append({"path": source_rel, "unchanged_from_baseline": unchanged})
            if not unchanged:
                errors.append(f"ephemeral worker {task_id} changed or lost source file {source_rel}")
        workers.append({"task_id": task_id, "worktree": str(resolved_cwd), "findings_path": write_path,
                        "findings_sha256": note_sha or "unavailable", "worker_head": worker_head,
                        "changed_paths": status_paths, "workspace_delta": workspace_delta,
                        "workspace_baseline_fingerprint": (record["baseline_data"].get("worker_state_fingerprint")
                                                            if record is not None else "unavailable"),
                        "source_checks": source_checks})
    return {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "baseline_head": baseline_head, "workers": workers}


def _native_grok_time(rows: list[dict], session_id: str, kind: str, child_id: str):
    """Read one exact lifecycle timestamp from the session-bound native journal."""
    matches = []
    for row in rows:
        params = row.get("params", {})
        update = params.get("update", {})
        if (params.get("sessionId") != session_id or update.get("sessionUpdate") != kind
                or update.get("subagent_id") != child_id):
            continue
        millis = params.get("_meta", {}).get("agentTimestampMs")
        value = millis / 1000 if type(millis) in (int, float) else row.get("timestamp")
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ExperimentError("Grok native lifecycle timestamp is missing or invalid")
        matches.append(value)
    if len(matches) != 1:
        raise ExperimentError("Grok native lifecycle timestamp is missing or ambiguous")
    return matches[0]


def _new_fixture_delivery_audit(case: dict, harness_path: Path, final_result: dict,
                               delivery_result: dict, status_result: dict,
                               native_nodes: list[dict], raw_request: dict) -> dict:
    """Join the new fixture's native, accepted, delivered, and cleanup records."""
    # Production records canonical paths; callers may use a directory alias
    # (including macOS /var -> /private/var). Compare the same path identity.
    harness_path = harness_path.resolve(strict=True)
    errors = []
    tasks = raw_request.get("tasks", [])
    expected = {task.get("id") for task in tasks if isinstance(task, dict)}
    if len(expected) != len(tasks) or len(tasks) != _task_count(case):
        errors.append("queued frozen request does not contain the exact task count and unique task ids")

    progress = status_result.get("progress", {})
    completed = progress.get("completed", []) if isinstance(progress, dict) else []
    completed_ids = {row.get("step") for row in completed if isinstance(row, dict)}
    if (status_result.get("workers_accepted") is not True or completed_ids != expected
            or status_result.get("active") != []):
        errors.append("production status does not show every requested task accepted with no active worker")

    native_by_task = {node.get("task_id"): node for node in native_nodes if node.get("role") == "worker"}
    if set(native_by_task) != expected or len(native_by_task) != sum(node.get("role") == "worker" for node in native_nodes):
        errors.append("native child handles do not map one-to-one to every frozen task")

    prepared_by_task = {}
    prepared_paths = sorted((harness_path / "prepared").glob("*.json"))
    for prepared_path in prepared_paths:
        prepared = _read(prepared_path)
        packet_info = prepared.get("packet")
        packet_path = Path(packet_info.get("path", "")) if isinstance(packet_info, dict) else Path()
        if not packet_path.is_absolute() or packet_path.is_symlink() or not packet_path.is_file():
            errors.append(f"prepared attempt {prepared_path.stem!r} lacks a retained regular packet")
            continue
        packet_bytes = _regular_bytes(packet_path)
        if packet_info.get("sha256") != _sha(packet_bytes):
            errors.append(f"prepared attempt {prepared_path.stem!r} packet bytes differ from their pinned hash")
            continue
        packet = _read(packet_path)
        packet_task = packet.get("task") if isinstance(packet, dict) else None
        matches = [task for task in tasks if isinstance(task, dict) and isinstance(packet_task, dict)
                   and packet_task.get("objective") == task.get("objective")
                   and packet_task.get("expected_result") == task.get("expected_result")
                   and isinstance(task.get("write_set"), list)
                   and packet_task.get("write_set") == sorted(task["write_set"])]
        if len(matches) != 1 or matches[0].get("id") in prepared_by_task:
            errors.append(f"prepared attempt {prepared_path.stem!r} does not uniquely map to one frozen task")
            continue
        prepared_by_task[matches[0]["id"]] = (prepared_path.stem, prepared, packet)
    if set(prepared_by_task) != expected or len(prepared_paths) != len(tasks):
        errors.append("prepared attempts do not cover the frozen task set exactly once")

    collected_paths = sorted((harness_path / "collected").glob("*.json"))
    verified_paths = sorted((harness_path / "verified").glob("*.json"))
    accepted = []
    for task in tasks:
        if not isinstance(task, dict) or task.get("id") not in prepared_by_task:
            continue
        task_id = task["id"]
        attempt, prepared, packet = prepared_by_task[task_id]
        collected_path = harness_path / "collected" / f"{attempt}.json"
        verified_path = harness_path / "verified" / f"{attempt}.json"
        if not collected_path.is_file() or collected_path.is_symlink():
            errors.append(f"task {task_id} lacks its collected native terminal record")
            continue
        if not verified_path.is_file() or verified_path.is_symlink():
            errors.append(f"task {task_id} lacks its independent acceptance record")
            continue
        record, verdict = _read(collected_path), _read(verified_path)
        result = record.get("result", {})
        node = native_by_task.get(task_id, {})
        native_id = node.get("id")
        if (record.get("native_evidence_kind") != "coordinator_attestation"
                or result.get("native_terminal") is not True
                or result.get("status") != "SUCCEEDED"
                or not isinstance(result.get("native_handle"), str)
                or result.get("native_handle") != native_id):
            errors.append(f"task {task_id} collected terminal handle does not match its native child session")
        if (verdict.get("passed") is not True or not isinstance(verdict.get("reason"), str)
                or not verdict.get("reason", "").strip()
                or not isinstance(verdict.get("evidence"), list) or not verdict["evidence"]):
            errors.append(f"task {task_id} lacks a passing independent verification record")
        if not isinstance(record.get("verified"), dict) or record["verified"].get("status") != "READY_FOR_PARENT_ACCEPTANCE":
            errors.append(f"task {task_id} lacks a successful Ask Agent verify-return record")
        criteria = result.get("criteria", [])
        expected_result = task.get("expected_result")
        if (not isinstance(criteria, list) or not any(
                isinstance(row, dict) and row.get("criterion") == expected_result
                and row.get("level") in {"confirmed", "inspected"} for row in criteria)):
            errors.append(f"task {task_id} has no confirmed native result for its exact expected criterion")
        verify_return = record.get("verified")
        workspace_evidence = (verify_return.get("workspace_evidence", {})
                              if isinstance(verify_return, dict) else {})
        inspection = (workspace_evidence.get("inspection", {})
                      if isinstance(workspace_evidence, dict) else {})
        accepted.append({"id": task_id, "attempt": attempt, "native_id": native_id,
                         "native_handle": result.get("native_handle"),
                         "collected_path": str(collected_path),
                         "collected_sha256": _sha(_regular_bytes(collected_path)),
                         "verified_path": str(verified_path),
                         "verified_sha256": _sha(_regular_bytes(verified_path)),
                         "inspection_fingerprint": inspection.get("fingerprint"),
                         "verified": verdict.get("passed") is True})

    if len(collected_paths) != len(tasks) or len(verified_paths) != len(tasks):
        errors.append("retained collection and verification records are not exactly one per queued task")

    delivery_workers = delivery_result.get("workers", [])
    delivery_by_id = {row.get("id"): row for row in delivery_workers if isinstance(row, dict)}
    if set(delivery_by_id) != expected or len(delivery_workers) != len(tasks):
        errors.append("immutable delivery rows do not cover the frozen task set exactly once")
    if delivery_result.get("status") != "SUCCEEDED":
        errors.append("immutable delivery result is not SUCCEEDED")

    applied = case.get("mode") == "edit" and case.get("workspace") == "worktree" and case.get("integration") == "apply"
    if applied:
        expected_paths = set(case.get("fixture", {}).get("owned_paths", []))
        integration = delivery_result.get("integration", {})
        applied_paths = integration.get("applied_paths", [])
        if (integration.get("outcome") != "applied" or not isinstance(applied_paths, list)
                or len(applied_paths) != len(expected_paths) or set(applied_paths) != expected_paths):
            errors.append("delivery applied-path union does not equal every required module and JSON resource")
        integration_workers = integration.get("workers", [])
        per_worker_paths = {row.get("id"): row.get("paths", [])
                            for row in integration_workers if isinstance(row, dict)}
        for task in tasks:
            task_id = task.get("id")
            expected_write_set = task.get("write_set", [])
            expected_write_set = sorted(expected_write_set) if isinstance(expected_write_set, list) else expected_write_set
            if (not isinstance(expected_write_set, list)
                    or per_worker_paths.get(task_id) != expected_write_set):
                errors.append(f"delivery row for task {task_id} does not apply its complete declared resource set")
            saved_row = delivery_by_id.get(task_id, {})
            if saved_row.get("write_set") != expected_write_set:
                errors.append(f"immutable delivery worker {task_id} differs from its prepared write set")
        checks = delivery_result.get("checks", [])
        expected_check_count = len(raw_request.get("checks", []))
        if (len(checks) != expected_check_count
                or any(row.get("status") != "PASSED" or row.get("exit_code") != 0 for row in checks)):
            errors.append("immutable delivery does not retain every successful combined check")

        if final_result.get("cleanup_status") != "complete" or final_result.get("status") != "SUCCEEDED":
            errors.append("successful queued edit delivery did not complete its cleanup phase")
        cleanup = final_result.get("cleanup", {})
        cleanup_rows = cleanup.get("workers", []) if isinstance(cleanup, dict) else []
        cleanup_by_id = {row.get("id"): row for row in cleanup_rows if isinstance(row, dict)}
        final_workers = final_result.get("workers", [])
        final_by_id = {row.get("id"): row for row in final_workers if isinstance(row, dict)}
        if set(cleanup_by_id) != expected or len(cleanup_rows) != len(tasks):
            errors.append("cleanup outcomes do not cover the accepted task set exactly once")
        if set(final_by_id) != expected or len(final_workers) != len(tasks):
            errors.append("final result workers do not cover the accepted task set exactly once")
        sys.path.insert(0, str(SKILL_ROOT / "in-parallel" / "scripts"))
        import harness as production_harness
        delivery_path = harness_path / "delivery" / "result.json"
        delivery_sha = _sha(_regular_bytes(delivery_path))
        source = Path(case["caller"])
        accepted_by_id = {row["id"]: row for row in accepted}
        for task_id in sorted(expected):
            cleanup_row = cleanup_by_id.get(task_id, {})
            delivered = delivery_by_id.get(task_id, {})
            final_worker = final_by_id.get(task_id, {})
            accepted_row = accepted_by_id.get(task_id, {})
            attempt = accepted_row.get("attempt")
            packet_workspace = prepared_by_task.get(task_id, (None, {}, {}))[2].get("workspace", {})
            delivery_detail = delivered.get("delivery", {})
            expected_worktree = packet_workspace.get("root")
            expected_receipt = packet_workspace.get("receipt")
            worktree = cleanup_row.get("worktree")
            branch = delivered.get("branch")
            commits = delivery_detail.get("commits", []) if isinstance(delivery_detail, dict) else []
            if (cleanup_row.get("status") != "closed"
                    or cleanup_row.get("worktree_path_status") != "removed"
                    or cleanup_row.get("attempt") != attempt
                    or cleanup_row.get("receipt") != expected_receipt
                    or not isinstance(expected_worktree, str)
                    or worktree != expected_worktree
                    or cleanup_row.get("branch") != branch
                    or not isinstance(worktree, str) or Path(worktree).exists()
                    or Path(expected_worktree).exists()
                    or production_harness._git_worktree_registered(source, expected_worktree) is not False):
                errors.append(f"accepted task {task_id} worktree remains or is still registered after cleanup")
            if (final_worker.get("attempt") != attempt
                    or delivered.get("worktree") != expected_worktree
                    or delivered.get("receipt") != expected_receipt
                    or packet_workspace.get("branch") != branch):
                errors.append(f"accepted task {task_id} final result and delivery are not bound to its prepared workspace")
            if (not isinstance(branch, str)
                    or not production_harness._git_reference_present(source, "branch", branch)
                    or not isinstance(commits, list) or not commits
                    or any(not production_harness._git_reference_present(source, "commit", commit) for commit in commits)):
                errors.append(f"accepted task {task_id} branch or delivered commit was not retained")
            if cleanup_row.get("branch") != branch or cleanup_row.get("commits") != commits:
                errors.append(f"accepted task {task_id} cleanup evidence differs from retained branch/commit delivery")
            outcome = cleanup_row.get("helper_outcome", {})
            if outcome.get("status") != "closed" or outcome.get("removed") is not True:
                errors.append(f"accepted task {task_id} lacks successful close-helper removal evidence")
            acceptance_info = cleanup_row.get("acceptance")
            if isinstance(acceptance_info, dict) and isinstance(acceptance_info.get("path"), str):
                acceptance_path = Path(acceptance_info["path"])
                if (acceptance_path.is_symlink() or not acceptance_path.is_file()
                        or _sha(_regular_bytes(acceptance_path)) != acceptance_info.get("sha256")):
                    errors.append(f"accepted task {task_id} cleanup acceptance bytes do not match their retained hash")
                else:
                    acceptance = _read(acceptance_path)
                    delivery_reference = f"{delivery_path} sha256={delivery_sha}"
                    completion_reference = (f"native terminal handle {accepted_row.get('native_handle')} in "
                                            f"{accepted_row.get('collected_path')} "
                                            f"sha256={accepted_row.get('collected_sha256')}")
                    verification_reference = (f"accepted verification {accepted_row.get('verified_path')} "
                                              f"sha256={accepted_row.get('verified_sha256')}")
                    if (acceptance.get("decision") != "integrated" or acceptance.get("workers_stopped") is not True
                            or acceptance.get("inspection_fingerprint") != accepted_row.get("inspection_fingerprint")
                            or cleanup_row.get("inspection_fingerprint") != accepted_row.get("inspection_fingerprint")
                            or completion_reference not in acceptance.get("completion_reference", "")
                            or delivery_reference not in acceptance.get("acceptance_reference", "")
                            or verification_reference not in acceptance.get("acceptance_reference", "")):
                        errors.append(f"accepted task {task_id} cleanup is not bound to its terminal result, verification, delivery, and inspection")
            else:
                errors.append(f"accepted task {task_id} lacks retained cleanup acceptance bytes")
            close_path = cleanup_row.get("close_evidence")
            if isinstance(close_path, str) and Path(close_path).is_file() and not Path(close_path).is_symlink():
                close = _read(Path(close_path))
                if (close.get("status") != "closed" or close.get("removed") is not True
                        or close.get("receipt") != expected_receipt
                        or close.get("worktree") != expected_worktree
                        or close.get("branch") != branch
                        or close.get("inspection_fingerprint") != accepted_row.get("inspection_fingerprint")):
                    errors.append(f"accepted task {task_id} close evidence does not prove removal")
            else:
                errors.append(f"accepted task {task_id} lacks retained close-helper evidence")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "task_acceptance": accepted, "delivery_worker_ids": sorted(delivery_by_id),
            "applied_paths": sorted(delivery_result.get("integration", {}).get("applied_paths", [])),
            "cleanup_worker_ids": sorted((row.get("id") for row in final_result.get("cleanup", {}).get("workers", [])
                                           if isinstance(row, dict)))}


def _filesystem_audit(case_dir: Path, case: dict, native_nodes: list[dict] | None = None) -> dict:
    sys.path.insert(0, str(SKILL_ROOT / "in-parallel" / "scripts"))
    import delivery
    root = Path(case["caller"])
    baseline = _read(case_dir / "case.json")["fixture"]
    harness = Path(case["harness_run"])
    run = _read(harness / "run.json")
    result = _read(harness / "result.json")
    before = run.get("baseline")
    after = delivery.capture(root)
    errors = []
    raw_request = _read(case_dir / "harness-request.json")
    normalized_request = _normalized_request(raw_request)
    if run.get("request") != normalized_request: errors.append("production harness request differs from the normalized frozen synthetic request")
    if case.get("normalized_request_sha256") != _sha(_canonical(normalized_request)):
        errors.append("normalized synthetic request differs from the prepared request hash")
    if case.get("request_sha256") != _sha((case_dir / "harness-request.json").read_bytes()):
        errors.append("raw synthetic request bytes differ from their prepared hash")
    if case.get("prompt_sha256") != _sha((case_dir / "operator" / "parent-prompt.txt").read_bytes()):
        errors.append("root prompt bytes differ from their prepared hash")
    if before != case.get("parent_snapshot") or before.get("head") != baseline.get("head"):
        errors.append("production harness baseline differs from the independently captured synthetic parent snapshot")
    if result.get("status") != "SUCCEEDED": errors.append(f"production harness final delivery status is not SUCCEEDED: {result.get('status')!r}")
    paths_before = {item["path"]: item for item in before.get("files", [])}
    paths_after = {item["path"]: item for item in after.get("files", [])}
    changed = sorted(path for path in set(paths_before) | set(paths_after) if paths_before.get(path) != paths_after.get(path))
    if after.get("head") != baseline.get("head"): errors.append("parent HEAD moved")
    if after.get("index_entries") != before.get("index_entries"): errors.append("parent Git index changed")
    if after.get("cached_diff_sha256") != before.get("cached_diff_sha256"): errors.append("staged parent diff changed")
    if case.get("parent_index_sha256") is not None:
        index_path = root / ".git" / "index"
        if index_path.is_symlink() or not index_path.is_file() or _sha(_regular_bytes(index_path)) != case["parent_index_sha256"]:
            errors.append("parent Git index bytes changed")
    allowed = set(baseline.get("owned_paths", [])) if case["mode"] == "edit" and case["integration"] == "apply" else set()
    if sorted(set(changed) - allowed): errors.append(f"parent changes escaped declared module outputs: {sorted(set(changed) - allowed)}")
    for path in baseline.get("required_dirty_paths", []):
        if paths_before.get(path) != paths_after.get(path): errors.append(f"dirty control changed: {path}")
    for path, digest in baseline.get("control_sha256", {}).items():
        control = root / path
        if control.is_symlink() or not control.is_file() or _sha(_regular_bytes(control)) != digest:
            errors.append(f"dirty control bytes changed: {path}")
    check_results = []
    ephemeral_worker_evidence = None
    if case["mode"] == "edit" and case["integration"] == "apply":
        check = subprocess.run(["python3", "-B", "verify_modules.py"], cwd=root, capture_output=True, text=True)
        check_results.append({"argv": ["python3", "-B", "verify_modules.py"], "cwd": str(root),
                              "exit_code": check.returncode, "stdout": check.stdout, "stderr": check.stderr})
        if check.returncode: errors.append("independent combined synthetic module verifier failed")
    if case["mode"] == "ephemeral":
        prepared_rows = [_read(path) for path in sorted((harness / "prepared").glob("*.json"))]
        ephemeral_worker_evidence = _ephemeral_worker_audit(case_dir, case, raw_request, prepared_rows)
        if ephemeral_worker_evidence["status"] != "PASS":
            errors.extend(ephemeral_worker_evidence["errors"])
    delivery_result = _read(harness / "delivery" / "result.json") if (harness / "delivery" / "result.json").is_file() else result
    queued_audit = None
    if case.get("fixture_version") == RESOURCE_FIXTURE_VERSION:
        sys.path.insert(0, str(SKILL_ROOT / "in-parallel" / "scripts"))
        import harness as production_harness
        status_result = production_harness.execute("status", run=str(harness))
        queued_audit = _new_fixture_delivery_audit(
            case, harness, result, delivery_result, status_result, native_nodes or [], raw_request)
        errors.extend(queued_audit["errors"])
        if case["mode"] == "edit" and case["integration"] == "apply":
            if set(changed) != set(baseline.get("owned_paths", [])):
                errors.append("parent changed paths do not equal the complete declared module/resource union")
    if case["mode"] == "ephemeral" and list((case_dir / "caller" / "scratch").glob("findings_*.md")):
        errors.append("ephemeral scratch finding was imported into parent checkout")
    if case["mode"] == "ephemeral" and delivery_result.get("integration", {}).get("outcome") not in ("not-requested", "return-only", "no-import", "not-started"):
        # The required invariant is that no scratch contribution entered the caller.
        if set(changed) & set(baseline.get("owned_paths", [])): errors.append("ephemeral mode imported a source module")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "baseline_head": before.get("head"), "after_head": after.get("head"),
            "baseline_index_entries": before.get("index_entries"), "after_index_entries": after.get("index_entries"),
            "baseline_cached_diff_sha256": before.get("cached_diff_sha256"),
            "after_cached_diff_sha256": after.get("cached_diff_sha256"),
            "changed_paths": changed, "independent_check_commands": check_results,
            "queued_lifecycle": queued_audit,
            "ephemeral_worker_evidence": ephemeral_worker_evidence,
            "harness_delivery_status": delivery_result.get("status"), "snapshot_sha256": _sha(_canonical(after))}


def audit_case(args) -> dict:
    case_dir = args.case.resolve(strict=True)
    case = _read(case_dir / "case.json")
    if (case_dir / "audit.json").exists() or (case_dir / "audit.json").is_symlink():
        raise ExperimentError(f"Audit evidence already exists; preserve it and use a fresh case: {case_dir / 'audit.json'}")
    report = {"schema": "agent-harness-experiment.audit/v1", "case_id": case.get("case_id"),
              "status": "FAIL", "checks": {}, "audit_started_epoch": time.time()}
    report["input_identity"] = {
        "case_manifest_sha256": _sha(_regular_bytes(case_dir / "manifest.json")),
        "request_sha256": case.get("request_sha256"), "prompt_sha256": case.get("prompt_sha256"),
        "source_freeze_sha256": case.get("freeze_sha256"),
        "source_freeze": case.get("source_freeze"),
    }
    try:
        freeze_now = source_freeze()
        report["checks"]["source_freeze"] = {"status": "PASS" if freeze_now == case.get("source_freeze") else "FAIL",
                                              "expected_sha256": case.get("freeze_sha256"), "observed_sha256": freeze_now.get("sha256")}
        if freeze_now != case.get("source_freeze"): raise ExperimentError("selected packages or apparatus changed after the live launch")
        if case["provider"] == "claude": nodes, native = _capture_claude(case_dir, case)
        elif case["provider"] == "grok": nodes, native = _capture_grok(case_dir, case, args.session_root)
        else: raise ExperimentError("unknown provider")
        graph = audit_native_graph(case, nodes)
        report["native_trace"] = {"status": graph["status"], "graph": graph, "nodes": nodes, "host_evidence": native}
        report["checks"]["native_trace"] = {"status": graph["status"], "errors": graph["errors"]}
        if graph["status"] != "PASS": raise ExperimentError("native event graph failed strict tree audit")
        filesystem = _filesystem_audit(case_dir, case, nodes)
        report["filesystem_git"] = filesystem
        report["checks"]["filesystem_git"] = {"status": filesystem["status"], "errors": filesystem["errors"]}
        if filesystem["status"] != "PASS": raise ExperimentError("filesystem/Git checks failed")
        report["elapsed_s"] = _elapsed(case_dir, case)
        report["token_usage"] = _tokens(case_dir, case)
        report["status"] = "PASS"
    except (OSError, ValueError, KeyError, TypeError, ExperimentError, subprocess.SubprocessError) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["checks"].setdefault("audit", {"status": "FAIL", "error": report["error"]})
    report["audit_finished_epoch"] = time.time()
    _write_new(case_dir / "audit.json", report)
    return report


def reaudit_case(args) -> dict:
    """Re-evaluate retained native evidence without changing the original attempt."""
    if args.case.is_symlink():
        raise ExperimentError("Re-audit case path may not be a symlink")
    case_dir = args.case.resolve(strict=True)
    if not case_dir.is_dir():
        raise ExperimentError("Re-audit case must be a directory")
    output_arg = args.output_dir
    if output_arg.exists() or output_arg.is_symlink():
        raise ExperimentError(f"Re-audit output must be a fresh path: {output_arg}")
    output_dir = output_arg.resolve(strict=False)
    if (output_dir == case_dir or case_dir in output_dir.parents or output_dir in case_dir.parents):
        raise ExperimentError("Re-audit output must be separate from the retained case directory")
    if not isinstance(args.provenance, str) or not args.provenance.strip():
        raise ExperimentError("Re-audit requires explicit correction provenance")
    case = _read(case_dir / "case.json")
    if case.get("provider") not in {"claude", "grok"}:
        raise ExperimentError("Offline re-audit requires retained Claude or Grok evidence")
    output_dir.mkdir(parents=True)
    original_audit_path = case_dir / "audit.json"
    original_audit_sha = _sha(_regular_bytes(original_audit_path)) if original_audit_path.exists() else None
    report = {
        "schema": "agent-harness-experiment.reaudit/v1",
        "mode": "offline-retained-evidence-reaudit",
        "status": "DIAGNOSTIC_ONLY",
        "qualification": "This re-audit is a diagnostic under the current apparatus; it never replaces the frozen original audit.",
        "evidence_status": "FAIL",
        "case_id": case.get("case_id"),
        "case_dir": str(case_dir),
        "output_dir": str(output_dir),
        "correction_provenance": args.provenance.strip(),
        "source_freeze_comparison": {
            "status": "UNAVAILABLE",
            "expected_sha256": case.get("freeze_sha256"),
            "observed_before_sha256": "unavailable",
            "observed_after_sha256": "unavailable",
        },
        "input_identity": {
            "manifest_sha256": _sha(_regular_bytes(case_dir / "manifest.json")),
            "request_sha256": case.get("request_sha256"),
            "prompt_sha256": case.get("prompt_sha256"),
            "original_audit_path": str(original_audit_path),
            "original_audit_sha256_before": original_audit_sha,
        },
        "checks": {},
        "reaudit_started_epoch": time.time(),
    }
    try:
        before = source_freeze()
        report["source_freeze_comparison"] = {
            "status": "UNCHANGED" if before == case.get("source_freeze") else "DRIFTED",
            "expected_sha256": case.get("freeze_sha256"),
            "observed_before_sha256": before.get("sha256"),
            "observed_after_sha256": "unavailable",
        }
        if case["provider"] == "claude":
            nodes, native = _capture_claude(case_dir, case, retained_dir=output_dir / "retained")
        else:
            nodes, native = _capture_grok(case_dir, case, None, retained_dir=output_dir / "retained")
        graph = audit_native_graph(case, nodes)
        report["native_trace"] = {"status": graph["status"], "graph": graph,
                                  "nodes": nodes, "host_evidence": native}
        report["checks"]["native_trace"] = {"status": graph["status"], "errors": graph["errors"]}
        filesystem = _filesystem_audit(case_dir, case, nodes)
        report["filesystem_git"] = filesystem
        report["checks"]["filesystem_git"] = {"status": filesystem["status"], "errors": filesystem["errors"]}
        report["elapsed_s"] = _elapsed(case_dir, case)
        report["token_usage"] = _tokens(case_dir, case)
        after = source_freeze()
        report["source_freeze_comparison"]["observed_after_sha256"] = after.get("sha256")
        report["source_freeze_comparison"]["stable_during_reaudit"] = before == after
        if before != after:
            report["checks"]["source_stability"] = {"status": "FAIL", "error": "experiment source changed during diagnostic re-audit"}
        else:
            report["checks"]["source_stability"] = {"status": "PASS"}
        report["checks"]["original_audit_immutable"] = {
            "status": "PASS" if original_audit_sha == (
                _sha(_regular_bytes(original_audit_path)) if original_audit_path.exists() else None) else "FAIL",
            "sha256_before": original_audit_sha,
            "sha256_after": _sha(_regular_bytes(original_audit_path)) if original_audit_path.exists() else None,
        }
        report["evidence_status"] = ("PASS" if graph["status"] == "PASS" and filesystem["status"] == "PASS"
                                     and before == after and report["checks"]["original_audit_immutable"]["status"] == "PASS"
                                     else "FAIL")
    except (OSError, ValueError, KeyError, TypeError, ExperimentError, subprocess.SubprocessError) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["checks"].setdefault("reaudit", {"status": "FAIL", "error": report["error"]})
        if original_audit_path.exists():
            current_sha = _sha(_regular_bytes(original_audit_path))
            report["checks"]["original_audit_immutable"] = {
                "status": "PASS" if current_sha == original_audit_sha else "FAIL",
                "sha256_before": original_audit_sha, "sha256_after": current_sha,
            }
    report["reaudit_finished_epoch"] = time.time()
    _write_new(output_dir / "reaudit.json", report)
    return report


def _elapsed(case_dir: Path, case: dict):
    path = case_dir / "operator" / ("process-result.json" if case["provider"] == "claude" else "process-result.json")
    try: return _read(path).get("elapsed_s", "unavailable")
    except (OSError, ValueError, ExperimentError): return "unavailable"


def _tokens(case_dir: Path, case: dict):
    if case["provider"] == "claude":
        try: return _read(case_dir / "operator" / "process-result.json").get("tokens", "unavailable")
        except (OSError, ValueError, ExperimentError): return "unavailable"
    try:
        text = (case_dir / "operator" / "usage.txt").read_text(encoding="utf-8")
        # Keep token claims conservative until the host's usage schema is stable.
        return {"usage_text_sha256": _sha(text.encode()), "tokens": "unavailable"}
    except OSError:
        return "unavailable"


def write_report(args) -> dict:
    cases = [Path(value).resolve(strict=True) for value in args.cases]
    rows = []
    for case_path in cases:
        case, audit = _read(case_path / "case.json"), _read(case_path / "audit.json")
        rows.append({"case_id": case.get("case_id"), "provider": case.get("provider"), "model": case.get("model"),
                     "effort": case.get("effort"), "arm": case.get("arm"), "workers": case.get("workers"),
                     "task_count": _task_count(case), "requested_capacity": case.get("requested_capacity"),
                     "effective_capacity": _effective_capacity(case),
                     "mode": case.get("mode"), "status": audit.get("status"),
                     "source_freeze_sha256": case.get("freeze_sha256"),
                     "elapsed_s": audit.get("elapsed_s", "unavailable"),
                     "start_spread_s": audit.get("native_trace", {}).get("graph", {}).get("worker_start_spread_seconds", "unavailable"),
                     "peak_overlap": audit.get("native_trace", {}).get("graph", {}).get("peak_native_worker_overlap", "unavailable"),
                     "reached_capacity": audit.get("native_trace", {}).get("graph", {}).get("reached_capacity", "unavailable"),
                     "queued_refill_observed": audit.get("native_trace", {}).get("graph", {}).get("queued_refill_observed", "unavailable"),
                     "tokens": audit.get("token_usage", "unavailable"), "audit": str((case_path / "audit.json").resolve())})
    report = {"schema": "agent-harness-experiment.report/v1", "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL", "cases": rows}
    output = args.output.resolve()
    _write_new(output, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="create a synthetic dirty Git case and frozen request")
    prepare.add_argument("--case", type=Path, required=True)
    prepare.add_argument("--provider", choices=("claude", "grok"), required=True)
    prepare.add_argument("--arm", choices=("direct", "nested"), required=True)
    prepare.add_argument("--tasks", type=int, help="independent task count; defaults to --workers or the legacy count of 3")
    prepare.add_argument("--workers", type=int, help="explicit positive concurrent-worker capacity; omit to use the production default")
    prepare.add_argument("--mode", choices=("edit", "report-only", "ephemeral"), default="edit")
    prepare.add_argument("--workspace", choices=("current", "worktree"))
    prepare.add_argument("--integration", choices=("apply", "return-only"))
    launch = commands.add_parser("launch", help="start exactly one authorized root model CLI")
    launch.add_argument("--case", type=Path, required=True)
    launch.add_argument("--expected-freeze-sha256", required=True)
    launch.add_argument("--authorized-case", required=True)
    launch.add_argument("--claude-binary")
    launch.add_argument("--grok-binary")
    audit = commands.add_parser("audit", help="strictly audit retained native events and Git state")
    audit.add_argument("--case", type=Path, required=True)
    audit.add_argument("--session-root", type=Path)
    reaudit = commands.add_parser("reaudit", help="write a separate diagnostic audit of retained native evidence")
    reaudit.add_argument("--case", type=Path, required=True)
    reaudit.add_argument("--output-dir", type=Path, required=True)
    reaudit.add_argument("--provenance", required=True,
                         help="explicit reason for re-evaluating an already-retained attempt")
    report = commands.add_parser("report", help="write an immutable summary for audited cases")
    report.add_argument("--cases", nargs="+", required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare": result = prepare_case(args)
        elif args.command == "launch": return launch_case(args)
        elif args.command == "audit": result = audit_case(args)
        elif args.command == "reaudit": result = reaudit_case(args)
        else: result = write_report(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("status") in ("PREPARED", "PASS", "DIAGNOSTIC_ONLY") else 1
    except (OSError, ValueError, KeyError, TypeError, ExperimentError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
