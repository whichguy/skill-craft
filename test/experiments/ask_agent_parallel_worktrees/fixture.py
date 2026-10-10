#!/usr/bin/env python3
"""Build and verify an isolated ask-agent worktree experiment fixture."""

from __future__ import annotations

import argparse
from diagnostics import emit_diagnostics, evidence_reference, make_diagnostic, report_check_diagnostics

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKER_COUNTS = (3, 5)
DIRTY_PATHS = ("dual.txt", "added.txt", "deleted.txt", "notes.txt", ".gitignore")
EXPECTED_BASE_STATUS = {
    "added.txt": "A ",
    "deleted.txt": " D",
    "dual.txt": "MM",
    "notes.txt": "??",
}
PIPELINE_INPUTS = [-7, -1, 0, 1, 9, 100]
ORACLE_INPUTS = [-10**30, -999, -7, -1, 0, 1, 9, 100, 10**30]
IGNORE_DIRS = {"__pycache__"}
MARKER_RELATIVE_PATH = ".experiment-local/owner.txt"
MIN_PARALLEL_HOLD_OVERLAP_SECONDS = 0.1
STATE_CHECK_KEYS = (
    "root_is_distinct_from_parent",
    "common_dir_matches_fixture",
    "head_matches_caller_snapshot",
    "index_entries_tree_and_staged_layer_match",
    "unstaged_dirty_input_diffs_match",
    "dirty_status_layers_match",
    "working_tree_matches_except_owned_step",
    "nonowner_source_files_unchanged",
    "owner_changed_from_baseline",
)


class FixtureError(RuntimeError):
    pass


def default_skill_root() -> Path:
    """Find skills/ask-agent relative to this checkout or the current Git repo."""
    for ancestor in Path(__file__).resolve().parents:
        candidate = ancestor / "skills" / "ask-agent"
        if candidate.is_dir():
            return candidate
    try:
        repository = Path(git(Path.cwd(), "rev-parse", "--show-toplevel")).resolve()
        candidate = repository / "skills" / "ask-agent"
        if candidate.is_dir():
            return candidate
    except FixtureError:
        pass
    raise FixtureError("cannot find skills/ask-agent; pass --skill-root explicitly")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_exclusive(path: Path, payload: bytes) -> None:
    """Publish a complete file atomically without replacing existing evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise FixtureError(f"refusing to replace existing file: {path}") from exc
    except OSError as exc:
        raise FixtureError(f"cannot publish {path}: {exc}") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_exclusive_text(path: Path, value: str) -> None:
    write_exclusive(path, value.encode("utf-8"))


def write_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    write_exclusive_text(path, payload)


def run_process(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float = 20,
    text: bool = True,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    child_environment = os.environ.copy()
    child_environment["GIT_OPTIONAL_LOCKS"] = "0"
    if environment:
        child_environment.update(environment)
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            timeout=timeout,
            text=text,
            env=child_environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FixtureError(f"command failed to run: {args!r}: {exc}") from exc
    if check and result.returncode:
        stdout = result.stdout if isinstance(result.stdout, str) else ""
        stderr = result.stderr if isinstance(result.stderr, str) else ""
        raise FixtureError(
            f"command exited {result.returncode}: {args!r}\n{stdout}\n{stderr}".strip()
        )
    return result


def git(
    root: Path,
    *args: str,
    check: bool = True,
    timeout: float = 20,
    environment: dict[str, str] | None = None,
) -> str:
    result = run_process(
        ["git", "-C", str(root), *args],
        check=check,
        timeout=timeout,
        environment=environment,
    )
    return result.stdout.strip()


def resolve_git_path(root: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


def package_tree_sha256(root: Path) -> str:
    """Hash relative names and bytes, excluding Python cache artifacts."""
    root = root.resolve()
    digest = hashlib.sha256()
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in IGNORE_DIRS)
        current_path = Path(current)
        for name in sorted(filenames):
            path = current_path / name
            if path.suffix == ".pyc":
                continue
            relative = path.relative_to(root).as_posix().encode("utf-8")
            if path.is_symlink():
                marker = b"symlink:"
                content = os.readlink(path).encode("utf-8")
            else:
                marker = b"file:"
                content = path.read_bytes()
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(marker)
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
    return digest.hexdigest()


def worktree_snapshot(root: Path, *, worker_mode: bool = False) -> dict[str, Any]:
    """Hash files and record directories, skipping Git metadata and Python caches."""
    root = root.resolve()
    files: dict[str, str] = {}
    directories: list[str] = []
    for current, names, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root).as_posix()
        if relative_dir == ".":
            relative_dir = ""

        retained: list[str] = []
        for name in sorted(names):
            relative = f"{relative_dir}/{name}".strip("/")
            if name == ".git" or name in IGNORE_DIRS:
                continue
            if worker_mode and relative == ".experiment-local":
                # The owner marker itself is separately verified. Descend so any
                # extra ignored evidence is still visible to the snapshot check.
                retained.append(name)
                continue
            retained.append(name)
            directories.append(relative)
        names[:] = retained

        for name in sorted(filenames):
            path = current_path / name
            relative = f"{relative_dir}/{name}".strip("/")
            if relative == ".git" or (worker_mode and relative == MARKER_RELATIVE_PATH):
                continue
            if path.is_symlink():
                files[relative] = "symlink:" + os.readlink(path)
            else:
                files[relative] = "sha256:" + sha256_file(path)
    return {"files": files, "directories": sorted(directories)}


def raw_index_sha256(index_path: Path) -> str:
    if not index_path.is_file():
        raise FixtureError(f"Git index is missing: {index_path}")
    return sha256_file(index_path)


def private_index_tree(root: Path, index_path: Path) -> str:
    """Compute the staged tree from a private index copy without locking the shared index."""
    temporary_root = Path(tempfile.gettempdir()).resolve()
    try:
        temporary_root.relative_to(root)
    except ValueError:
        pass
    else:
        raise FixtureError("system temporary directory is inside the Git worktree")

    try:
        with tempfile.TemporaryDirectory(prefix="ask-agent-index-tree-") as temporary_dir:
            private_index = Path(temporary_dir) / "index"
            shutil.copyfile(index_path, private_index)
            return git(
                root,
                "write-tree",
                environment={"GIT_INDEX_FILE": str(private_index.resolve())},
            )
    except OSError as exc:
        raise FixtureError(f"cannot compute index tree from a private index copy: {exc}") from exc


def status_entries(root: Path) -> dict[str, str]:
    output = run_process(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    entries: dict[str, str] = {}
    for line in output.splitlines():
        if len(line) < 4:
            raise FixtureError(f"unrecognized porcelain status line: {line!r}")
        entries[line[3:]] = line[:2]
    return entries


def diff_sha256(root: Path, *, cached: bool = False, path: str | None = None) -> str:
    args = ["diff", "--binary", "--full-index", "--no-ext-diff", "--no-textconv"]
    if cached:
        args.append("--cached")
    if path is not None:
        args.extend(["--", path])
    result = run_process(["git", "-C", str(root), *args], text=False)
    return sha256_bytes(result.stdout)


def capture_repo_state(root: Path, *, worker_mode: bool = False) -> dict[str, Any]:
    root = Path(git(root, "rev-parse", "--show-toplevel")).resolve()
    common_dir = resolve_git_path(root, git(root, "rev-parse", "--git-common-dir"))
    index_path = resolve_git_path(root, git(root, "rev-parse", "--git-path", "index"))
    branch_result = run_process(
        ["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "HEAD"],
        check=False,
    )
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    entries = git(root, "ls-files", "--stage", "--full-name").splitlines()
    head = git(root, "rev-parse", "HEAD")
    index_tree = private_index_tree(root, index_path)
    cached_diff = diff_sha256(root, cached=True)
    unstaged_diffs = {
        path: diff_sha256(root, path=path) for path in DIRTY_PATHS if path != "notes.txt"
    }
    status = status_entries(root)
    index_sha = raw_index_sha256(index_path)
    return {
        "root": str(root),
        "common_dir": str(common_dir),
        "index_path": str(index_path),
        "index_raw_sha256": index_sha,
        "branch": branch,
        "head": head,
        "index_entries": entries,
        "index_entries_sha256": sha256_bytes("\n".join(entries).encode("utf-8")),
        "index_tree": index_tree,
        "cached_diff_sha256": cached_diff,
        "unstaged_dirty_diffs": unstaged_diffs,
        "status": status,
        "working_tree": worktree_snapshot(root, worker_mode=worker_mode),
    }


def source_identity(source_skill: Path) -> dict[str, Any]:
    source_skill = source_skill.resolve()
    identity: dict[str, Any] = {
        "skill_path": str(source_skill),
        "repository": None,
        "revision": None,
        "skill_status": None,
    }
    try:
        repository = Path(git(source_skill, "rev-parse", "--show-toplevel")).resolve()
        revision = git(source_skill, "rev-parse", "HEAD")
        relative = source_skill.relative_to(repository).as_posix()
        status = git(repository, "status", "--porcelain=v1", "--", relative)
        identity.update(
            {
                "repository": str(repository),
                "revision": revision,
                "skill_status": status.splitlines(),
            }
        )
    except (FixtureError, ValueError):
        # Tests may supply a synthetic source tree without a Git repository.
        pass
    return identity


def formula(task_id: int, value: int) -> int:
    return (task_id + 1) * value + task_id * task_id


def generated_pipeline(worker_count: int) -> str:
    imports = "\n".join(
        f"from src.step_{task_id} import transform as transform_{task_id}"
        for task_id in range(1, worker_count + 1)
    )
    transforms = ", ".join(f"transform_{task_id}" for task_id in range(1, worker_count + 1))
    return f'''"""Apply every task transform in ascending task order."""

import json

{imports}

INPUTS = {PIPELINE_INPUTS!r}
TRANSFORMS = ({transforms},)


def transform_value(value):
    for transform in TRANSFORMS:
        value = transform(value)
    return value


def outputs():
    return [transform_value(value) for value in INPUTS]


if __name__ == "__main__":
    print(json.dumps(outputs()))
'''


def generated_checks(worker_count: int) -> str:
    return f'''"""Stdlib checks for the synthetic task fixture.

The baseline intentionally fails until workers replace their stubs.
"""

import argparse
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

WORKER_COUNT = {worker_count}
INPUTS = {ORACLE_INPUTS!r}
PIPELINE_INPUTS = {PIPELINE_INPUTS!r}


def expected(task_id, value):
    return (task_id + 1) * value + task_id * task_id


def load_transform(task_id):
    path = Path(__file__).parent / "src" / f"step_{{task_id}}.py"
    spec = importlib.util.spec_from_file_location(f"fixture_step_{{task_id}}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.transform


class FormulaCheck(unittest.TestCase):
    def __init__(self, task_id):
        super().__init__("runTest")
        self.task_id = task_id

    def runTest(self):
        transform = load_transform(self.task_id)
        for value in INPUTS:
            with self.subTest(task_id=self.task_id, value=value):
                result = transform(value)
                self.assertIs(type(result), int)
                self.assertEqual(result, expected(self.task_id, value))


class PipelineCheck(unittest.TestCase):
    def runTest(self):
        root = Path(__file__).parent
        result = subprocess.run(
            [sys.executable, str(root / "pipeline.py")],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        actual = json.loads(result.stdout)
        expected_values = []
        for original in PIPELINE_INPUTS:
            value = original
            for task_id in range(1, WORKER_COUNT + 1):
                value = expected(task_id, value)
            expected_values.append(value)
        self.assertEqual(actual, expected_values)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--worker", type=int)
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.worker is not None and not 1 <= args.worker <= WORKER_COUNT:
        parser.error(f"--worker must be in 1..{{WORKER_COUNT}}")
    suite = unittest.TestSuite()
    worker_ids = range(1, WORKER_COUNT + 1) if args.all else [args.worker]
    for task_id in worker_ids:
        suite.addTest(FormulaCheck(task_id))
    if args.all:
        suite.addTest(PipelineCheck())
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
'''


def ignored_python_cache(directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORE_DIRS or name.endswith(".pyc")}


def create_fixture_source(root: Path, worker_count: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".gitignore").write_text(".experiment-local/\n__pycache__/\n", encoding="utf-8")
    (root / "dual.txt").write_text("head\n", encoding="utf-8")
    (root / "deleted.txt").write_text("initial file to delete\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    for task_id in range(1, worker_count + 1):
        (root / "src" / f"step_{task_id}.py").write_text(
            f'''def transform(x):
    raise NotImplementedError("task {task_id} must implement transform(x)")
''',
            encoding="utf-8",
        )
    (root / "pipeline.py").write_text(generated_pipeline(worker_count), encoding="utf-8")
    (root / "checks.py").write_text(generated_checks(worker_count), encoding="utf-8")


def fixture_paths(run_path: Path) -> dict[str, str]:
    return {
        "run": str(run_path),
        "primary": str(run_path / "primary"),
        "caller": str(run_path / "caller"),
        "package": str(run_path / "package" / "ask-agent"),
        "probes": str(run_path / "operator" / "probes"),
        "verification": str(run_path / "operator" / "verification.json"),
    }


def prepare_fixture(
    run_path: Path | str,
    workers: int,
    mode: str,
    hold_seconds: float = 0,
    *,
    source_skill: Path | str | None = None,
    seed_feedback_backlog: bool = False,
    seed_compact_ignore_controls: bool = False,
) -> dict[str, Any]:
    if workers not in WORKER_COUNTS:
        raise FixtureError(f"workers must be one of {WORKER_COUNTS}")
    if mode not in {"parallel", "sequential"}:
        raise FixtureError("mode must be parallel or sequential")
    if not math.isfinite(hold_seconds) or hold_seconds < 0:
        raise FixtureError("hold-seconds must be a finite nonnegative number")
    if type(seed_feedback_backlog) is not bool:
        raise FixtureError("seed-feedback-backlog must be a boolean")
    if type(seed_compact_ignore_controls) is not bool:
        raise FixtureError("seed-compact-ignore-controls must be a boolean")

    run_path = Path(run_path).expanduser().resolve()
    if run_path.exists() and any(run_path.iterdir()):
        raise FixtureError(f"run directory must be absent or empty: {run_path}")
    run_path.mkdir(parents=True, exist_ok=True)

    source_skill = Path(source_skill).expanduser().resolve() if source_skill else default_skill_root()
    if not source_skill.is_dir():
        raise FixtureError(f"ask-agent source skill directory is missing: {source_skill}")
    package_path = run_path / "package" / "ask-agent"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_skill, package_path, ignore=ignored_python_cache, symlinks=True)
    source_digest = package_tree_sha256(source_skill)
    package_digest = package_tree_sha256(package_path)
    if source_digest != package_digest:
        raise FixtureError("copied ask-agent package does not match source tree digest")

    primary = run_path / "primary"
    run_process(["git", "init", "-b", "main", str(primary)])
    git(primary, "config", "user.name", "Ask Agent Fixture")
    git(primary, "config", "user.email", "ask-agent-fixture@example.invalid")
    create_fixture_source(primary, workers)
    backlog_path = "tasks/in-progress/prompt-improvements-backlog.md"
    if seed_feedback_backlog:
        backlog = primary / backlog_path
        backlog.parent.mkdir(parents=True, exist_ok=True)
        backlog.write_bytes(
            b"# Prompt Improvement Backlog\n\n"
            b"Generated by feedback-collector plugin.\n\n"
        )
    initial_paths = [
        ".gitignore",
        "dual.txt",
        "deleted.txt",
        "pipeline.py",
        "checks.py",
        "src/__init__.py",
        *[f"src/step_{task_id}.py" for task_id in range(1, workers + 1)],
    ]
    if seed_feedback_backlog:
        initial_paths.append(backlog_path)
    git(primary, "add", *initial_paths)
    git(primary, "commit", "-m", "fixture baseline")
    primary_snapshot = capture_repo_state(primary)

    caller = run_path / "caller"
    git(primary, "worktree", "add", "-b", "experiment", str(caller), "main")
    run_id = uuid.uuid4().hex
    marker = f"run={run_id}\nbranch=experiment\n"
    (caller / "unique-ahead-marker.txt").write_text(marker, encoding="utf-8")
    git(caller, "add", "unique-ahead-marker.txt")
    git(caller, "commit", "-m", "unique caller marker")
    (caller / "dual.txt").write_text("staged\n", encoding="utf-8")
    git(caller, "add", "dual.txt")
    (caller / "dual.txt").write_text("unstaged\n", encoding="utf-8")
    (caller / "notes.txt").write_text("snapshot notes\n", encoding="utf-8")
    (caller / "added.txt").write_text("staged add\n", encoding="utf-8")
    git(caller, "add", "added.txt")
    (caller / "deleted.txt").unlink()
    if seed_compact_ignore_controls:
        gitignore = caller / ".gitignore"
        gitignore.write_text(
            gitignore.read_text(encoding="utf-8") + "/.claspignore\n/unrelated-ignored-input.txt\n",
            encoding="utf-8",
        )
        (caller / ".claspignore").write_text("dist/\n", encoding="utf-8")
        (caller / "unrelated-ignored-input.txt").write_text("omit from worker snapshot\n", encoding="utf-8")
    caller_snapshot = capture_repo_state(caller)
    expected_dirty_status = dict(EXPECTED_BASE_STATUS)
    if seed_compact_ignore_controls:
        expected_dirty_status[".gitignore"] = " M"
    if caller_snapshot["status"] != expected_dirty_status:
        raise FixtureError(
            f"fixture dirty layers were not created as expected: {caller_snapshot['status']!r}"
        )
    ahead = int(git(caller, "rev-list", "--count", "main..experiment"))
    if ahead != 1:
        raise FixtureError(f"caller branch should be exactly one commit ahead of main, got {ahead}")

    probes = run_path / "operator" / "probes"
    probes.mkdir(parents=True)
    assignments = []
    for task_id in range(1, workers + 1):
        assignments.append(
            {
                "worker_id": str(task_id),
                "task_index": task_id,
                "path": f"src/step_{task_id}.py",
                "assignment": (
                    f"Implement only src/step_{task_id}.py. Define transform(x) for every "
                    f"integer x as ({task_id}+1)*x+{task_id}*{task_id}. "
                    "Do not modify other files or dirty inputs."
                ),
                "marker_value": f"run={run_id};task={task_id}\n",
            }
        )

    source = source_identity(source_skill)
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at_utc": utc_now(),
        "mode": mode,
        "workers": workers,
        "seed_feedback_backlog": seed_feedback_backlog,
        "seed_compact_ignore_controls": seed_compact_ignore_controls,
        "worker_ids": [str(task_id) for task_id in range(1, workers + 1)],
        "hold_seconds": hold_seconds,
        "instrumentation_hold_excluded_from_timing_comparisons": True,
        "paths": fixture_paths(run_path),
        "source": {
            **source,
            "logical_card": "SKILL.md",
            "helper": "scripts/ask_agent_workspace.py",
            "package_tree_sha256": package_digest,
        },
        "caller_ahead_of_main_commits": ahead,
        "caller_marker": marker,
        "caller_snapshot": caller_snapshot,
        "primary_snapshot": primary_snapshot,
        "expected_dirty_status": expected_dirty_status,
        "dirty_inputs": [*DIRTY_PATHS[:-1], *([".gitignore"] if seed_compact_ignore_controls else [])],
        "compact_ignore_controls": {
            "ignored_root_control": ".claspignore" if seed_compact_ignore_controls else None,
            "ignored_unrelated_input": "unrelated-ignored-input.txt" if seed_compact_ignore_controls else None,
        },
        "task_assignments": assignments,
        "pipeline_inputs": PIPELINE_INPUTS,
        "oracle_inputs": ORACLE_INPUTS,
        "verification_notes": [
            "Worker ids and task indices are one-based.",
            "Each worker must use its own linked worktree and index.",
            "Child index bytes may differ because Git stores worktree-specific stat-cache data; entries, index tree, staged diff, and dirty input layers are compared.",
            "Raw index SHA differences are reported; entries, index tree, and staged diff determine semantic index preservation.",
            "The optional feedback backlog is seeded fixture content; it does not disable hooks or plugins.",
            "Probe hold intervals are instrumentation and excluded from model timing comparisons.",
            "Parallel runs with a positive hold require at least 0.1 seconds of overlap across every worker; sequential runs do not.",
            "Verification establishes fixture behavior and raw child events remain the controller's responsibility.",
        ],
    }
    manifest_path = run_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_manifest(run_path: Path) -> dict[str, Any]:
    path = run_path / "manifest.json"
    if not path.is_file():
        raise FixtureError(f"manifest is missing: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FixtureError(f"manifest is unreadable: {exc}") from exc
    if manifest.get("schema_version") != 1:
        raise FixtureError("unsupported manifest schema version")
    return manifest


def task_for(manifest: dict[str, Any], worker_id: str) -> dict[str, Any]:
    for task in manifest["task_assignments"]:
        if task["worker_id"] == worker_id:
            return task
    raise FixtureError(f"unknown worker id {worker_id!r}")


def marker_matches(marker_path: Path, expected: str) -> bool:
    try:
        return marker_path.is_file() and marker_path.read_text(encoding="utf-8") == expected
    except (OSError, UnicodeDecodeError):
        return False


def _compare_file_snapshot(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    allowed_file: str | None = None,
) -> tuple[bool, bool]:
    actual_files = actual["files"]
    expected_files = expected["files"]
    same_outside_allowed = True
    allowed_changed = False
    keys = set(actual_files) | set(expected_files)
    for key in keys:
        if key == allowed_file:
            if actual_files.get(key) != expected_files.get(key):
                allowed_changed = True
            elif key not in actual_files:
                same_outside_allowed = False
            continue
        if actual_files.get(key) != expected_files.get(key):
            same_outside_allowed = False
    if actual.get("directories") != expected.get("directories"):
        same_outside_allowed = False
    return same_outside_allowed, allowed_changed


def state_checks(
    state: dict[str, Any],
    manifest: dict[str, Any],
    worker_id: str,
    phase: str,
) -> tuple[dict[str, bool], dict[str, Any]]:
    baseline = manifest["caller_snapshot"]
    owner_path = task_for(manifest, worker_id)["path"]
    allow_owner = phase == "finish"
    expected_working_tree = _probe_baseline_working_tree(manifest)
    files_match, owner_changed = _compare_file_snapshot(
        state["working_tree"],
        expected_working_tree,
        allowed_file=owner_path if allow_owner else None,
    )

    source_files = state["working_tree"]["files"]
    expected_source_files = baseline["working_tree"]["files"]
    nonowner_source_unchanged = all(
        source_files.get(task["path"]) == expected_source_files.get(task["path"])
        for task in manifest["task_assignments"]
        if task["worker_id"] != worker_id
    )
    index_matches = (
        state["index_entries"] == baseline["index_entries"]
        and state["index_tree"] == baseline["index_tree"]
        and state["cached_diff_sha256"] == baseline["cached_diff_sha256"]
    )
    dirty_inputs = manifest.get("dirty_inputs", DIRTY_PATHS)
    dirty_diff_matches = all(
        state["unstaged_dirty_diffs"].get(path)
        == baseline["unstaged_dirty_diffs"].get(path)
        for path in dirty_inputs
        if path != "notes.txt"
    )
    expected_status = dict(manifest["expected_dirty_status"])
    if allow_owner and owner_changed:
        expected_status[owner_path] = " M"
    status_matches = state["status"] == expected_status
    expected_head = baseline["head"]
    checks = {
        "root_is_distinct_from_parent": state["root"]
        not in {manifest["paths"]["caller"], manifest["paths"]["primary"]},
        "common_dir_matches_fixture": state["common_dir"]
        == manifest["primary_snapshot"]["common_dir"],
        "head_matches_caller_snapshot": state["head"] == expected_head,
        "index_entries_tree_and_staged_layer_match": index_matches,
        "unstaged_dirty_input_diffs_match": dirty_diff_matches,
        "dirty_status_layers_match": status_matches,
        "working_tree_matches_except_owned_step": files_match,
        "nonowner_source_files_unchanged": nonowner_source_unchanged,
        "owner_changed_from_baseline": owner_changed if allow_owner else not owner_changed,
    }
    if manifest.get("seed_compact_ignore_controls"):
        expected_root_control = baseline["working_tree"]["files"].get(".claspignore")
        checks["ignored_root_control_preserved"] = (
            isinstance(expected_root_control, str)
            and state["working_tree"]["files"].get(".claspignore") == expected_root_control
        )
        checks["unrelated_ignored_input_omitted"] = (
            "unrelated-ignored-input.txt" not in state["working_tree"]["files"]
        )
    details = {
        "expected_head": expected_head,
        "expected_status": expected_status,
        "actual_status": state["status"],
        "owner_path": owner_path,
        "owner_changed": owner_changed,
        "compact_ignore_controls": {
            "root_control_expected": expected_root_control if manifest.get("seed_compact_ignore_controls") else None,
            "root_control_actual": state["working_tree"]["files"].get(".claspignore"),
            "unrelated_ignored_input_present": "unrelated-ignored-input.txt" in state["working_tree"]["files"],
        },
    }
    return checks, details


def _probe_baseline_working_tree(manifest: dict[str, Any]) -> dict[str, Any]:
    expected = manifest["caller_snapshot"]["working_tree"]
    if manifest.get("seed_compact_ignore_controls"):
        expected = {**expected, "files": dict(expected["files"])}
        expected["files"].pop("unrelated-ignored-input.txt", None)
    return expected


_ORACLE_PROGRAM = r'''
import contextlib
import importlib.util
import io
import json
import sys

path, task_text, values_text = sys.argv[1:4]
task_id = int(task_text)
values = json.loads(values_text)
cases = []
try:
    spec = importlib.util.spec_from_file_location("fixture_worker", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load task module")
    module = importlib.util.module_from_spec(spec)
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
        spec.loader.exec_module(module)
        transform = module.transform
        for value in values:
            actual = transform(value)
            expected = (task_id + 1) * value + task_id * task_id
            display = actual
            if not isinstance(actual, (str, int, float, bool, type(None))):
                display = repr(actual)
            cases.append({
                "input": value,
                "expected": expected,
                "actual": display,
                "passed": type(actual) is int and actual == expected,
            })
    result = {"passed": bool(cases) and all(case["passed"] for case in cases), "cases": cases}
except BaseException as exc:
    result = {
        "passed": False,
        "error": type(exc).__name__ + ": " + str(exc),
        "cases": cases,
    }
print(json.dumps(result))
'''


def check_module_oracle(
    module_path: Path, task_id: int, *, timeout: float = 10
) -> dict[str, Any]:
    """Check task output in a bounded child process to isolate interpreter globals."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                _ORACLE_PROGRAM,
                str(module_path.resolve()),
                str(task_id),
                json.dumps(ORACLE_INPUTS),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "timed_out": True,
            "error": f"oracle process timed out after {timeout:g} seconds",
            "cases": [],
        }
    except OSError as exc:
        return {"passed": False, "error": f"{type(exc).__name__}: {exc}", "cases": []}
    if result.returncode != 0:
        return {
            "passed": False,
            "error": f"oracle process exited {result.returncode}",
            "stderr": result.stderr[-4000:],
            "cases": [],
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "passed": False,
            "error": f"oracle process returned invalid JSON: {exc}",
            "stdout": result.stdout[-4000:],
            "cases": [],
        }
    if not isinstance(payload, dict) or type(payload.get("passed")) is not bool:
        return {"passed": False, "error": "oracle result has an invalid shape", "cases": []}
    return payload


def probe_run(
    run_path: Path | str,
    worker_id: str,
    phase: str,
    *,
    cwd: Path | str | None = None,
) -> dict[str, Any]:
    if phase not in {"start", "finish"}:
        raise FixtureError("phase must be start or finish")
    run_path = Path(run_path).expanduser().resolve()
    manifest = load_manifest(run_path)
    task = task_for(manifest, worker_id)
    current = Path(cwd or Path.cwd()).resolve()
    root = Path(git(current, "rev-parse", "--show-toplevel")).resolve()
    try:
        current.relative_to(root)
    except ValueError as exc:
        raise FixtureError(f"probe cwd is outside its Git root: {current}") from exc
    if str(root) in {manifest["paths"]["caller"], manifest["paths"]["primary"]}:
        raise FixtureError("probe must run from a distinct child worktree")
    common_dir = resolve_git_path(root, git(root, "rev-parse", "--git-common-dir"))
    if str(common_dir) != manifest["primary_snapshot"]["common_dir"]:
        raise FixtureError("probe Git common directory does not match the prepared fixture")

    record_path = run_path / "operator" / "probes" / f"worker-{worker_id}-{phase}.json"
    marker_path = root / MARKER_RELATIVE_PATH
    if record_path.exists():
        raise FixtureError(f"{phase} probe already exists: {record_path}")
    if phase == "start" and marker_path.exists():
        raise FixtureError(f"worker marker already exists: {marker_path}")
    errors: list[str] = []
    checks: dict[str, bool] = {}
    hold_started = None
    hold_started_monotonic = None
    hold_finished = None
    hold_finished_monotonic = None
    hold_elapsed = None
    start_record: dict[str, Any] | None = None

    if phase == "start":
        initial_state = capture_repo_state(root, worker_mode=True)
        initial_checks, initial_details = state_checks(initial_state, manifest, worker_id, "start")
        checks.update({f"before_hold.{key}": value for key, value in initial_checks.items()})
        if any(not value for value in initial_checks.values()):
            errors.append("child snapshot did not match the prepared caller state")
        if not errors:
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            write_exclusive_text(marker_path, task["marker_value"])
        hold_started = utc_now()
        hold_started_monotonic = time.monotonic()
        if not errors and manifest["hold_seconds"] > 0:
            time.sleep(manifest["hold_seconds"])
        marker_intact = marker_matches(marker_path, task["marker_value"])
        hold_finished = utc_now()
        hold_finished_monotonic = time.monotonic()
        hold_elapsed = round(hold_finished_monotonic - hold_started_monotonic, 6)
        final_state = capture_repo_state(root, worker_mode=True)
        final_checks, final_details = state_checks(final_state, manifest, worker_id, "start")
        checks.update({f"after_hold.{key}": value for key, value in final_checks.items()})
        checks["marker_intact_after_hold"] = marker_intact
        if not marker_intact:
            errors.append("owner marker changed or disappeared during the hold interval")
        if any(not value for value in final_checks.values()):
            errors.append("child snapshot changed during the hold interval")
        state = final_state
        details = {"before_hold": initial_details, "after_hold": final_details}
        start_record = None
    else:
        start_path = run_path / "operator" / "probes" / f"worker-{worker_id}-start.json"
        if not start_path.is_file():
            errors.append(f"start probe is missing: {start_path}")
        else:
            try:
                start_record = json.loads(start_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"start probe is unreadable: {exc}")
        marker_intact = marker_matches(marker_path, task["marker_value"])
        state = capture_repo_state(root, worker_mode=True)
        final_checks, details = state_checks(state, manifest, worker_id, "finish")
        checks.update(final_checks)
        checks["marker_intact_at_finish"] = marker_intact
        if not marker_intact:
            errors.append("owner marker changed or disappeared before finish")
        if any(not value for value in final_checks.values()):
            errors.append("child finish snapshot did not match the allowed task changes")
        if start_record and start_record.get("root") != str(root):
            checks["same_root_as_start"] = False
            errors.append("finish probe root differs from start probe root")
        elif start_record:
            checks["same_root_as_start"] = True
        else:
            checks["same_root_as_start"] = False
        task_oracle = check_module_oracle(root / task["path"], int(worker_id))
        checks["task_result_oracle"] = task_oracle["passed"]
        if not task_oracle["passed"]:
            errors.append("owned task module failed its independent result oracle")
        hold_started = start_record.get("hold_started_at_utc") if start_record else None
        hold_finished = start_record.get("hold_finished_at_utc") if start_record else None
        hold_elapsed = start_record.get("hold_elapsed_seconds") if start_record else None
        hold_started_monotonic = (
            start_record.get("hold_started_monotonic_seconds") if start_record else None
        )
        hold_finished_monotonic = (
            start_record.get("hold_finished_monotonic_seconds") if start_record else None
        )

    record = {
        "schema_version": 1,
        "run_id": manifest["run_id"],
        "worker_id": worker_id,
        "phase": phase,
        "recorded_at_utc": utc_now(),
        "cwd": str(current),
        "root": str(root),
        "common_dir": state["common_dir"],
        "branch": state["branch"],
        "head": state["head"],
        "index_path": state["index_path"],
        "index_tree": state["index_tree"],
        "index_entries_sha256": state["index_entries_sha256"],
        "index_raw_sha256": state["index_raw_sha256"],
        "status": state["status"],
        "working_tree": state["working_tree"],
        "checks": checks,
        "details": details,
        "errors": errors,
        "marker_relative_path": MARKER_RELATIVE_PATH,
        "marker_value": task["marker_value"],
        "marker_intact": marker_intact,
        "hold_started_at_utc": hold_started,
        "hold_finished_at_utc": hold_finished,
        "hold_started_monotonic_seconds": hold_started_monotonic,
        "hold_finished_monotonic_seconds": hold_finished_monotonic,
        "hold_elapsed_seconds": hold_elapsed,
        "instrumentation_hold_excluded_from_timing_comparisons": True,
    }
    if phase == "start":
        record["hold_seconds_requested"] = manifest["hold_seconds"]
        record["initial_snapshot_checks"] = initial_checks
        record["initial_snapshot_details"] = initial_details
    else:
        record["task_oracle"] = task_oracle
        record["start_record_path"] = str(
            run_path / "operator" / "probes" / f"worker-{worker_id}-start.json"
        )

    write_exclusive_json(record_path, record)
    return record


def expected_pipeline(worker_count: int) -> list[int]:
    result: list[int] = []
    for original in PIPELINE_INPUTS:
        value = original
        for task_id in range(1, worker_count + 1):
            value = formula(task_id, value)
        result.append(value)
    return result


def pipeline_oracle(root: Path, worker_count: int) -> dict[str, Any]:
    try:
        result = run_process(
            [sys.executable, str(root / "pipeline.py")],
            cwd=root,
            check=False,
            timeout=10,
        )
        if result.returncode:
            return {
                "passed": False,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        actual = json.loads(result.stdout)
        expected = expected_pipeline(worker_count)
        return {
            "passed": actual == expected,
            "actual": actual,
            "expected": expected,
            "stderr": result.stderr,
        }
    except (FixtureError, json.JSONDecodeError, TypeError) as exc:
        return {"passed": False, "error": f"{type(exc).__name__}: {exc}"}


def _read_probe(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, f"missing probe: {path}"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            return None, f"probe is not a JSON object: {path}"
        return record, None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"unreadable probe {path}: {exc}"


PROBE_BASE_FIELDS = {
    "schema_version", "run_id", "worker_id", "phase", "recorded_at_utc",
    "cwd", "root", "common_dir", "branch", "head", "index_path", "index_tree",
    "index_entries_sha256", "index_raw_sha256", "status", "working_tree", "checks",
    "details", "errors", "marker_relative_path", "marker_value", "marker_intact",
    "hold_started_at_utc", "hold_finished_at_utc", "hold_started_monotonic_seconds",
    "hold_finished_monotonic_seconds", "hold_elapsed_seconds",
    "instrumentation_hold_excluded_from_timing_comparisons",
}


def state_check_keys(manifest: dict[str, Any] | None = None) -> set[str]:
    keys = set(STATE_CHECK_KEYS)
    if manifest and manifest.get("seed_compact_ignore_controls"):
        keys.update({"ignored_root_control_preserved", "unrelated_ignored_input_omitted"})
    return keys


def required_probe_checks(phase: str, manifest: dict[str, Any] | None = None) -> set[str]:
    state_keys = state_check_keys(manifest)
    if phase == "start":
        return (
            {f"before_hold.{key}" for key in state_keys}
            | {f"after_hold.{key}" for key in state_keys}
            | {"marker_intact_after_hold"}
        )
    return state_keys | {
        "marker_intact_at_finish", "same_root_as_start", "task_result_oracle"
    }


def valid_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def finite_number(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(value)


def validate_probe_record(
    record: dict[str, Any],
    manifest: dict[str, Any],
    task: dict[str, Any],
    phase: str,
    run_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    extras = (
        {"hold_seconds_requested", "initial_snapshot_checks", "initial_snapshot_details"}
        if phase == "start"
        else {"task_oracle", "start_record_path"}
    )
    expected_fields = PROBE_BASE_FIELDS | extras
    actual_fields = set(record)
    if actual_fields != expected_fields:
        errors.append(
            f"field set differs: missing={sorted(expected_fields - actual_fields)}, "
            f"extra={sorted(actual_fields - expected_fields)}"
        )
    for key, expected in (
        ("schema_version", 1),
        ("run_id", manifest["run_id"]),
        ("worker_id", task["worker_id"]),
        ("phase", phase),
        ("marker_relative_path", MARKER_RELATIVE_PATH),
        ("marker_value", task["marker_value"]),
        ("instrumentation_hold_excluded_from_timing_comparisons", True),
    ):
        if record.get(key) != expected:
            errors.append(f"{key} does not match the prepared {phase} probe")

    root = record.get("root")
    cwd = record.get("cwd")
    if not isinstance(root, str) or not Path(root).is_absolute():
        errors.append("root must be an absolute path")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        errors.append("cwd must be an absolute path")
    if isinstance(root, str) and isinstance(cwd, str):
        try:
            Path(cwd).resolve().relative_to(Path(root).resolve())
        except (OSError, ValueError):
            errors.append("cwd must resolve inside root")
    for key in ("common_dir", "index_path"):
        value = record.get(key)
        if not isinstance(value, str) or not Path(value).is_absolute():
            errors.append(f"{key} must be an absolute path")
    for key in ("head", "index_tree", "index_entries_sha256", "index_raw_sha256"):
        if not isinstance(record.get(key), str) or not record[key]:
            errors.append(f"{key} must be a nonempty string")
    if "branch" not in record or (record["branch"] is not None and not isinstance(record["branch"], str)):
        errors.append("branch must be a string or null")
    if not isinstance(record.get("status"), dict):
        errors.append("status must be an object")
    tree = record.get("working_tree")
    if not isinstance(tree, dict) or set(tree) != {"files", "directories"}:
        errors.append("working_tree must contain files and directories")
    elif not isinstance(tree.get("files"), dict) or not isinstance(tree.get("directories"), list):
        errors.append("working_tree files/directories have invalid types")
    if not isinstance(record.get("details"), dict):
        errors.append("details must be an object")
    if not isinstance(record.get("errors"), list) or any(
        not isinstance(value, str) for value in record.get("errors", [])
    ):
        errors.append("errors must be a list of strings")
    if record.get("errors"):
        errors.append("probe recorded errors")
    if record.get("marker_intact") is not True:
        errors.append("marker_intact must be true")
    if not valid_iso_timestamp(record.get("recorded_at_utc")):
        errors.append("recorded_at_utc is invalid")
    for key in ("hold_started_at_utc", "hold_finished_at_utc"):
        if not valid_iso_timestamp(record.get(key)):
            errors.append(f"{key} is invalid")
    for key in (
        "hold_started_monotonic_seconds", "hold_finished_monotonic_seconds", "hold_elapsed_seconds"
    ):
        if not finite_number(record.get(key)) or record[key] < 0:
            errors.append(f"{key} must be a finite nonnegative number")

    probe_checks = record.get("checks")
    required_checks = required_probe_checks(phase, manifest)
    if not isinstance(probe_checks, dict) or set(probe_checks) != required_checks:
        errors.append("checks do not match the required phase schema")
    elif any(type(value) is not bool for value in probe_checks.values()):
        errors.append("all checks must be booleans")
    elif not all(value is True for value in probe_checks.values()):
        errors.append("one or more required checks failed")

    if phase == "start":
        requested_hold = record.get("hold_seconds_requested")
        if not finite_number(requested_hold) or requested_hold != manifest["hold_seconds"]:
            errors.append("hold_seconds_requested differs from manifest")
        baseline = manifest["caller_snapshot"]
        start_snapshot_matches = (
            record.get("working_tree") == _probe_baseline_working_tree(manifest)
            and record.get("status") == manifest["expected_dirty_status"]
            and record.get("head") == baseline["head"]
            and record.get("index_tree") == baseline["index_tree"]
            and record.get("index_entries_sha256") == baseline["index_entries_sha256"]
            and record.get("common_dir") == manifest["primary_snapshot"]["common_dir"]
        )
        if not start_snapshot_matches:
            errors.append("start snapshot does not match the prepared caller baseline")
        snapshot_checks = record.get("initial_snapshot_checks")
        if not isinstance(snapshot_checks, dict) or set(snapshot_checks) != state_check_keys(manifest):
            errors.append("initial_snapshot_checks do not match the required schema")
        elif any(type(value) is not bool for value in snapshot_checks.values()):
            errors.append("initial_snapshot_checks values must be booleans")
        elif not all(value is True for value in snapshot_checks.values()):
            errors.append("initial snapshot checks failed")
        if not isinstance(record.get("initial_snapshot_details"), dict):
            errors.append("initial_snapshot_details must be an object")
        try:
            wall_seconds = (
                datetime.fromisoformat(record["hold_finished_at_utc"])
                - datetime.fromisoformat(record["hold_started_at_utc"])
            ).total_seconds()
            monotonic_seconds = (
                record["hold_finished_monotonic_seconds"]
                - record["hold_started_monotonic_seconds"]
            )
            if wall_seconds < 0 or monotonic_seconds < 0:
                errors.append("hold interval has negative duration")
            if abs(monotonic_seconds - record["hold_elapsed_seconds"]) > 0.05:
                errors.append("hold_elapsed_seconds differs from monotonic endpoints")
        except (KeyError, TypeError, ValueError):
            errors.append("hold interval endpoints are invalid")
    else:
        expected_start_path = str(run_path / "operator" / "probes" / f"worker-{task['worker_id']}-start.json")
        if record.get("start_record_path") != expected_start_path:
            errors.append("start_record_path does not point to this worker's start probe")
        task_oracle = record.get("task_oracle")
        if (
            not isinstance(task_oracle, dict)
            or task_oracle.get("passed") is not True
            or not isinstance(task_oracle.get("cases"), list)
            or len(task_oracle["cases"]) != len(ORACLE_INPUTS)
        ):
            errors.append("task_oracle is missing or incomplete")
        elif any(
            not isinstance(case, dict)
            or case.get("input") != expected_input
            or case.get("passed") is not True
            or case.get("expected") != formula(int(task["worker_id"]), expected_input)
            or type(case.get("actual")) is not int
            or case.get("actual") != case.get("expected")
            for case, expected_input in zip(task_oracle["cases"], ORACLE_INPUTS)
        ):
            errors.append("task_oracle cases do not match the required inputs")

    return {"passed": not errors, "errors": errors}


def validate_probe_pair(
    start: dict[str, Any], finish: dict[str, Any]
) -> dict[str, Any]:
    fields = (
        "root", "common_dir", "branch", "head", "index_path", "index_tree",
        "index_entries_sha256", "marker_relative_path", "marker_value",
        "hold_started_at_utc", "hold_finished_at_utc", "hold_started_monotonic_seconds",
        "hold_finished_monotonic_seconds", "hold_elapsed_seconds",
    )
    differing = [key for key in fields if start.get(key) != finish.get(key)]
    return {"passed": not differing, "differing_fields": differing}


def verify_fixture(run_path: Path | str) -> dict[str, Any]:
    run_path = Path(run_path).expanduser().resolve()
    manifest = load_manifest(run_path)
    errors: list[str] = []
    checks: dict[str, bool] = {}

    package_path = Path(manifest["paths"]["package"])
    package_digest = package_tree_sha256(package_path) if package_path.is_dir() else None
    checks["frozen_package_hash_unchanged"] = (
        package_digest == manifest["source"]["package_tree_sha256"]
    )
    if not checks["frozen_package_hash_unchanged"]:
        errors.append("frozen ask-agent package digest changed or package is missing")

    primary_path = Path(manifest["paths"]["primary"])
    caller_path = Path(manifest["paths"]["caller"])
    primary_index_raw_observation: dict[str, Any] | None = None
    try:
        primary_now = capture_repo_state(primary_path)
        primary_expected = manifest["primary_snapshot"]
        primary_fields = (
            "root", "common_dir", "index_path", "branch", "head", "index_entries",
            "index_tree", "cached_diff_sha256", "status", "working_tree",
        )
        primary_semantic_index_unchanged = all(
            primary_now.get(field) == primary_expected.get(field)
            for field in ("index_entries", "index_tree", "cached_diff_sha256")
        )
        primary_index_raw_observation = {
            "unchanged": primary_now["index_raw_sha256"] == primary_expected["index_raw_sha256"],
            "semantic_index_unchanged": primary_semantic_index_unchanged,
            "expected_sha256": primary_expected["index_raw_sha256"],
            "actual_sha256": primary_now["index_raw_sha256"],
            "metadata_only_difference": (
                primary_now["index_raw_sha256"] != primary_expected["index_raw_sha256"]
                and primary_semantic_index_unchanged
            ),
        }
        checks["primary_pristine_fingerprint_preserved"] = all(
            primary_now.get(field) == primary_expected.get(field) for field in primary_fields
        ) and primary_semantic_index_unchanged
    except Exception as exc:
        primary_now = None
        checks["primary_pristine_fingerprint_preserved"] = False
        errors.append(f"cannot recapture primary fingerprint: {type(exc).__name__}: {exc}")
    if not checks["primary_pristine_fingerprint_preserved"]:
        errors.append("primary working tree, HEAD, index, or fingerprint changed")

    worker_results: list[dict[str, Any]] = []
    start_records: dict[str, dict[str, Any]] = {}
    finish_records: dict[str, dict[str, Any]] = {}
    probe_complete = True
    roots: list[str] = []
    index_paths: list[str] = []
    common_dirs: list[str] = []
    markers: list[tuple[str, str]] = []
    hold_checks: list[bool] = []
    hold_intervals: dict[str, dict[str, float]] = {}
    snapshot_checks: list[bool] = []
    per_worker_oracles: list[bool] = []
    finish_owner_hashes: dict[str, str] = {}

    for task in manifest["task_assignments"]:
        worker_id = task["worker_id"]
        start_path = run_path / "operator" / "probes" / f"worker-{worker_id}-start.json"
        finish_path = run_path / "operator" / "probes" / f"worker-{worker_id}-finish.json"
        start, start_error = _read_probe(start_path)
        finish, finish_error = _read_probe(finish_path)
        if start_error or finish_error:
            probe_complete = False
            errors.extend(error for error in (start_error, finish_error) if error)
        result: dict[str, Any] = {"worker_id": worker_id}
        if start is None or finish is None:
            result["passed"] = False
            result["errors"] = [error for error in (start_error, finish_error) if error]
            worker_results.append(result)
            continue

        start_records[worker_id] = start
        finish_records[worker_id] = finish
        start_schema = validate_probe_record(start, manifest, task, "start", run_path)
        finish_schema = validate_probe_record(finish, manifest, task, "finish", run_path)
        pair_schema = validate_probe_pair(start, finish)
        if not start_schema["passed"] or not finish_schema["passed"] or not pair_schema["passed"]:
            probe_complete = False
            errors.extend(
                f"worker {worker_id} start schema: {value}"
                for value in start_schema["errors"]
            )
            errors.extend(
                f"worker {worker_id} finish schema: {value}"
                for value in finish_schema["errors"]
            )
            if not pair_schema["passed"]:
                errors.append(
                    f"worker {worker_id} start/finish fields differ: "
                    f"{pair_schema['differing_fields']}"
                )
        root = finish.get("root")
        index_path = finish.get("index_path")
        common_dir = finish.get("common_dir")
        roots.append(root if isinstance(root, str) else "")
        index_paths.append(index_path if isinstance(index_path, str) else "")
        common_dirs.append(common_dir if isinstance(common_dir, str) else "")
        markers.append((finish.get("marker_relative_path", ""), finish.get("marker_value", "")))

        start_checks = start.get("checks") if isinstance(start.get("checks"), dict) else {}
        finish_checks = finish.get("checks") if isinstance(finish.get("checks"), dict) else {}
        record_checks = {
            **{f"start.{key}": value for key, value in start_checks.items()},
            **{f"finish.{key}": value for key, value in finish_checks.items()},
        }
        start_errors = start.get("errors") if isinstance(start.get("errors"), list) else ["invalid errors field"]
        finish_errors = finish.get("errors") if isinstance(finish.get("errors"), list) else ["invalid errors field"]
        record_ok = (
            start_schema["passed"]
            and finish_schema["passed"]
            and pair_schema["passed"]
            and not start_errors
            and not finish_errors
            and bool(record_checks)
            and all(value is True for value in record_checks.values())
        )
        result["record_checks"] = record_checks
        result["record_schema"] = {
            "start": start_schema,
            "finish": finish_schema,
            "pair": pair_schema,
        }
        result["record_errors"] = start_errors + finish_errors
        result["recorded_snapshots_pass"] = record_ok

        valid_root = isinstance(root, str) and bool(root)
        try:
            if not valid_root:
                raise FixtureError("finish probe has no child root")
            actual_root = Path(git(Path(root), "rev-parse", "--show-toplevel")).resolve()
            actual_common = resolve_git_path(actual_root, git(actual_root, "rev-parse", "--git-common-dir"))
            actual_index = resolve_git_path(actual_root, git(actual_root, "rev-parse", "--git-path", "index"))
            root_matches = str(actual_root) == root
            common_matches = str(actual_common) == common_dir == manifest["primary_snapshot"]["common_dir"]
            index_matches = str(actual_index) == index_path
            recaptured = capture_repo_state(actual_root, worker_mode=True)
            recaptured_checks, recaptured_details = state_checks(recaptured, manifest, worker_id, "finish")
            recaptured_ok = all(recaptured_checks.values())
            finish_tree = finish.get("working_tree")
            finish_snapshot_matches = (
                isinstance(finish_tree, dict)
                and recaptured["branch"] == finish.get("branch")
                and recaptured["head"] == finish.get("head")
                and recaptured["index_tree"] == finish.get("index_tree")
                and recaptured["index_entries_sha256"] == finish.get("index_entries_sha256")
                and recaptured["status"] == finish.get("status")
                and recaptured["working_tree"] == finish_tree
            )
            marker_path = actual_root / MARKER_RELATIVE_PATH
            marker_ok = marker_matches(marker_path, task["marker_value"])
            owner_hash = recaptured["working_tree"]["files"].get(task["path"])
            finish_owner_hashes[worker_id] = owner_hash or ""
            owner_hash_matches_record = (
                owner_hash == finish.get("working_tree", {}).get("files", {}).get(task["path"])
            )
            module_oracle = check_module_oracle(actual_root / task["path"], int(worker_id))
        except Exception as exc:
            root_matches = common_matches = index_matches = recaptured_ok = False
            finish_snapshot_matches = False
            marker_ok = owner_hash_matches_record = False
            recaptured_checks = {}
            recaptured_details = {}
            module_oracle = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
            errors.append(f"worker {worker_id} root recheck failed: {type(exc).__name__}: {exc}")

        root_integration_checks = {
            "root_matches_actual_git_root": root_matches,
            "common_dir_is_shared_fixture_common_dir": common_matches,
            "index_path_matches_actual_git_index": index_matches,
            "current_snapshot_still_matches_finish": recaptured_ok,
            "finish_snapshot_matches_record": finish_snapshot_matches,
            "marker_intact": marker_ok,
            "owner_hash_matches_finish_record": owner_hash_matches_record,
        }
        result["root_rechecks"] = root_integration_checks
        result["recaptured_snapshot_checks"] = recaptured_checks
        result["recaptured_snapshot_details"] = recaptured_details
        result["task_oracle"] = module_oracle
        finish_task_oracle = finish.get("task_oracle")
        finish_oracle_ok = (
            isinstance(finish_task_oracle, dict)
            and finish_task_oracle.get("passed") is True
        )
        snapshot_checks.append(
            record_ok and recaptured_ok and root_matches and common_matches and index_matches
            and finish_snapshot_matches and marker_ok and owner_hash_matches_record
        )
        per_worker_oracles.append(
            bool(module_oracle.get("passed")) and finish_oracle_ok
        )

        marker_content_ok = finish.get("marker_value") == task["marker_value"]
        if finish.get("marker_relative_path") == MARKER_RELATIVE_PATH and marker_content_ok and marker_ok:
            result["collision_marker"] = True
        else:
            result["collision_marker"] = False

        hold_ok = False
        if start.get("phase") == "start" and manifest["hold_seconds"] == 0:
            hold_ok = True
        elif start.get("phase") == "start":
            try:
                started = datetime.fromisoformat(start["hold_started_at_utc"])
                ended = datetime.fromisoformat(start["hold_finished_at_utc"])
                wall_seconds = (ended - started).total_seconds()
                recorded_seconds = float(start["hold_elapsed_seconds"])
                monotonic_started = float(start["hold_started_monotonic_seconds"])
                monotonic_ended = float(start["hold_finished_monotonic_seconds"])
                monotonic_seconds = monotonic_ended - monotonic_started
                hold_intervals[worker_id] = {
                    "start": monotonic_started,
                    "end": monotonic_ended,
                }
                hold_ok = (
                    wall_seconds >= manifest["hold_seconds"] - 0.05
                    and recorded_seconds >= manifest["hold_seconds"] - 0.05
                    and monotonic_seconds >= manifest["hold_seconds"] - 0.05
                    and abs(monotonic_seconds - recorded_seconds) <= 0.05
                    and start.get("instrumentation_hold_excluded_from_timing_comparisons") is True
                )
                result["hold_interval"] = {
                    "started_at_utc": start["hold_started_at_utc"],
                    "finished_at_utc": start["hold_finished_at_utc"],
                    "wall_seconds": wall_seconds,
                    "monotonic_seconds": recorded_seconds,
                    "monotonic_interval_seconds": monotonic_seconds,
                    "requested_seconds": manifest["hold_seconds"],
                }
            except (KeyError, TypeError, ValueError):
                hold_ok = False
        hold_checks.append(hold_ok)
        result["hold_interval_passed"] = hold_ok
        result["passed"] = (
            record_ok
            and all(root_integration_checks.values())
            and bool(module_oracle.get("passed"))
            and finish_oracle_ok
            and result["collision_marker"]
            and hold_ok
        )
        worker_results.append(result)

    checks["worker_probe_completeness"] = probe_complete and len(start_records) == manifest["workers"] and len(finish_records) == manifest["workers"]
    checks["worker_roots_distinct_from_parent_and_each_other"] = (
        len(roots) == manifest["workers"]
        and len(set(roots)) == manifest["workers"]
        and all(root not in {str(primary_path.resolve()), str(caller_path.resolve())} for root in roots)
    )
    base_index_paths = {
        manifest["primary_snapshot"]["index_path"],
        manifest["caller_snapshot"]["index_path"],
    }
    checks["worker_index_paths_unique"] = (
        len(index_paths) == manifest["workers"]
        and len(set(index_paths)) == manifest["workers"]
        and not (set(index_paths) & base_index_paths)
    )
    checks["worker_common_dirs_match_fixture"] = (
        len(common_dirs) == manifest["workers"]
        and all(path == manifest["primary_snapshot"]["common_dir"] for path in common_dirs)
    )
    checks["worker_snapshots_clean_and_exact_dirty_layers"] = (
        len(snapshot_checks) == manifest["workers"] and all(snapshot_checks)
    )
    checks["collision_markers_use_same_path_and_unique_values"] = (
        len(markers) == manifest["workers"]
        and all(path == MARKER_RELATIVE_PATH for path, _ in markers)
        and len({value for _, value in markers}) == manifest["workers"]
        and all(result.get("collision_marker") for result in worker_results)
    )
    checks["per_task_result_oracles_pass"] = (
        len(per_worker_oracles) == manifest["workers"] and all(per_worker_oracles)
    )
    checks["hold_intervals_valid"] = len(hold_checks) == manifest["workers"] and all(hold_checks)

    overlap_required = manifest["mode"] == "parallel" and manifest["hold_seconds"] > 0
    overlap_seconds: float | None = None
    if len(hold_intervals) == manifest["workers"]:
        overlap_seconds = min(item["end"] for item in hold_intervals.values()) - max(
            item["start"] for item in hold_intervals.values()
        )
    overlap_passed = (
        overlap_seconds is not None
        and overlap_seconds >= MIN_PARALLEL_HOLD_OVERLAP_SECONDS
        if overlap_required
        else True
    )
    parallel_overlap = {
        "required": overlap_required,
        "required_overlap_seconds": MIN_PARALLEL_HOLD_OVERLAP_SECONDS,
        "overlap_seconds": overlap_seconds,
        "passed": overlap_passed,
        "intervals": hold_intervals,
    }
    checks["parallel_hold_intervals_overlap"] = overlap_passed
    if overlap_required and not overlap_passed:
        errors.append("parallel worker hold intervals did not overlap by at least 0.1 seconds")

    caller_checks: dict[str, Any] = {}
    caller_index_raw_observation: dict[str, Any] | None = None
    try:
        caller_now = capture_repo_state(caller_path)
        baseline = manifest["caller_snapshot"]
        allowed_paths = {task["path"] for task in manifest["task_assignments"]}
        actual_files = caller_now["working_tree"]["files"]
        expected_files = baseline["working_tree"]["files"]
        directories_unchanged = (
            caller_now["working_tree"]["directories"]
            == baseline["working_tree"]["directories"]
        )
        actual_changes = sorted(
            key for key in set(actual_files) | set(expected_files)
            if actual_files.get(key) != expected_files.get(key)
        )
        exact_changes = set(actual_changes) == allowed_paths
        all_module_files_present = all(path in actual_files for path in allowed_paths)
        expected_status = dict(manifest["expected_dirty_status"])
        for path in allowed_paths:
            if actual_files.get(path) != expected_files.get(path):
                expected_status[path] = " M"
        status_exact = caller_now["status"] == expected_status
        index_unchanged = (
            caller_now["index_entries"] == baseline["index_entries"]
            and caller_now["index_tree"] == baseline["index_tree"]
            and caller_now["cached_diff_sha256"] == baseline["cached_diff_sha256"]
        )
        caller_index_raw_observation = {
            "unchanged": caller_now["index_raw_sha256"] == baseline["index_raw_sha256"],
            "semantic_index_unchanged": index_unchanged,
            "expected_sha256": baseline["index_raw_sha256"],
            "actual_sha256": caller_now["index_raw_sha256"],
            "metadata_only_difference": (
                caller_now["index_raw_sha256"] != baseline["index_raw_sha256"]
                and index_unchanged
            ),
        }
        caller_identity_unchanged = (
            caller_now["root"] == baseline["root"]
            and caller_now["branch"] == baseline["branch"]
            and caller_now["head"] == baseline["head"]
        )
        dirty_inputs_unchanged = all(
            actual_files.get(path) == expected_files.get(path) for path in DIRTY_PATHS
        ) and all(
            caller_now["unstaged_dirty_diffs"].get(path)
            == baseline["unstaged_dirty_diffs"].get(path)
            for path in DIRTY_PATHS
            if path != "notes.txt"
        )
        caller_checks = {
            "only_allowed_step_files_changed": exact_changes and all_module_files_present,
            "caller_directories_unchanged": directories_unchanged,
            "caller_index_and_staged_layer_unchanged": index_unchanged,
            "caller_head_branch_and_root_unchanged": caller_identity_unchanged,
            "dirty_input_content_and_unstaged_layers_unchanged": dirty_inputs_unchanged,
            "caller_status_has_only_expected_changes": status_exact,
        }
        checks["exact_allowed_caller_source_changes"] = all(caller_checks.values())
        if not checks["exact_allowed_caller_source_changes"]:
            errors.append(f"caller state changed outside the permitted task edits: {caller_checks}")
    except Exception as exc:
        caller_now = None
        checks["exact_allowed_caller_source_changes"] = False
        errors.append(f"cannot verify caller state: {type(exc).__name__}: {exc}")
    if not checks["exact_allowed_caller_source_changes"]:
        checks["caller_dirty_head_index_and_content_preserved"] = False
    else:
        checks["caller_dirty_head_index_and_content_preserved"] = True

    integration_matches = True
    integration_details: dict[str, Any] = {}
    if caller_now is not None:
        caller_files = caller_now["working_tree"]["files"]
        for task in manifest["task_assignments"]:
            worker_id = task["worker_id"]
            child_hash = finish_owner_hashes.get(worker_id)
            caller_hash = caller_files.get(task["path"])
            matches = bool(child_hash) and child_hash == caller_hash
            integration_details[worker_id] = {
                "path": task["path"],
                "worker_sha256": child_hash,
                "caller_sha256": caller_hash,
                "matches": matches,
            }
            integration_matches = integration_matches and matches
    else:
        integration_matches = False
    checks["integrated_modules_match_worker_outputs"] = integration_matches
    checks["caller_dirty_head_index_and_content_preserved"] = bool(
        checks.get("caller_dirty_head_index_and_content_preserved")
        and checks["exact_allowed_caller_source_changes"]
    )
    if not integration_matches:
        errors.append("caller task modules do not match the worker finish snapshots")

    integrated_oracles = {
        task["worker_id"]: check_module_oracle(
            caller_path / task["path"], int(task["worker_id"])
        )
        for task in manifest["task_assignments"]
    }
    checks["integrated_per_task_result_oracles_pass"] = all(
        result.get("passed") for result in integrated_oracles.values()
    )
    if not checks["integrated_per_task_result_oracles_pass"]:
        errors.append("one or more integrated task modules failed the independent oracle")

    pipeline_result = pipeline_oracle(caller_path, manifest["workers"])
    checks["combined_pipeline_oracle_passes"] = bool(pipeline_result.get("passed"))
    if not checks["combined_pipeline_oracle_passes"]:
        errors.append("combined pipeline output failed the independent mathematical oracle")

    report = {
        "schema_version": 1,
        "run_id": manifest["run_id"],
        "run_path": str(run_path),
        "verified_at_utc": utc_now(),
        "passed": all(checks.values()),
        "checks": checks,
        "errors": errors,
        "source": {
            "revision": manifest["source"].get("revision"),
            "source_package_tree_sha256": manifest["source"]["package_tree_sha256"],
            "verified_package_tree_sha256": package_digest,
        },
        "caller_checks": caller_checks,
        "caller_index_raw_observation": caller_index_raw_observation,
        "worker_results": worker_results,
        "parallel_overlap": parallel_overlap,
        "integrated_task_oracles": integrated_oracles,
        "integration_hashes": integration_details,
        "combined_pipeline": pipeline_result,
        "primary_fingerprint": {
            "expected": manifest["primary_snapshot"],
            "actual": primary_now,
            "index_raw_observation": primary_index_raw_observation,
        },
        "timing_note": "Probe hold intervals are instrumentation and excluded from timing comparisons.",
        "evidence_scope_note": (
            "This verifier checks fixture invariants and independent code results. "
            "A separate controller must validate raw native lifecycle events."
        ),
    }
    verification_path = Path(manifest["paths"]["verification"])
    verification_path.parent.mkdir(parents=True, exist_ok=True)
    verification_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--run", required=True, type=Path)
    prepare_parser.add_argument("--workers", required=True, type=int, choices=WORKER_COUNTS)
    prepare_parser.add_argument("--mode", required=True, choices=("parallel", "sequential"))
    prepare_parser.add_argument("--hold-seconds", type=float, default=0)
    prepare_parser.add_argument(
        "--seed-feedback-backlog",
        action="store_true",
        help="seed the tracked feedback backlog file in the primary baseline",
    )
    prepare_parser.add_argument(
        "--seed-compact-ignore-controls",
        action="store_true",
        help="seed a dirty .gitignore, ignored root .claspignore, and unrelated ignored input",
    )
    prepare_parser.add_argument(
        "--skill-root",
        type=Path,
        help="source skills/ask-agent directory; defaults to the current fixture repository",
    )

    probe_parser = subparsers.add_parser("probe")
    probe_parser.add_argument("--run", required=True, type=Path)
    probe_parser.add_argument("--worker", required=True)
    probe_parser.add_argument("--phase", required=True, choices=("start", "finish"))

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--run", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_fixture(
                args.run,
                args.workers,
                args.mode,
                args.hold_seconds,
                source_skill=args.skill_root,
                seed_feedback_backlog=args.seed_feedback_backlog,
                seed_compact_ignore_controls=args.seed_compact_ignore_controls,
            )
        elif args.command == "probe":
            result = probe_run(args.run, args.worker, args.phase)
        else:
            result = verify_fixture(args.run)
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.command in ('probe','verify'):
            report_path = args.run/'operator'/('verification.json' if args.command=='verify' else f'probes/worker-{args.worker}-{args.phase}.json')
            diagnostics = report_check_diagnostics(result, report_path, phase=args.command)
            if (result.get('passed') is False or result.get('errors')) and not diagnostics:
                diagnostics=[make_diagnostic(code='FIXTURE_CHECK_FAILED',severity='error',phase=args.command,
                    expected='Every required fixture check passes with no reported errors',observed={'checks':result.get('checks'),'errors':result.get('errors')},
                    rationale='A failed fixture invariant prevents this run from proving isolated contribution delivery.',
                    rationale_ref='CONTRACT.md#pass-gates',evidence=[evidence_reference(report_path)],
                    recovery='Inspect the named checks and retained snapshots before a new run.',retry_safety='Do not repeat probes or integration in this run.')]
            # Probe writers each have their own diagnostic log; there is no shared append race.
            log=report_path.with_suffix('.diagnostics.jsonl')
            emit_diagnostics(diagnostics,jsonl_path=log)

        if args.command == "probe":
            return 0 if not result["errors"] and all(result["checks"].values()) else 1
        if args.command == "verify":
            return 0 if result["passed"] else 1
        return 0
    except (FixtureError, OSError, ValueError, KeyError) as exc:
        emit_diagnostics([make_diagnostic(code='FIXTURE_OPERATION_FAILED',severity='error',phase=args.command,
            expected='The requested fixture phase has valid inputs and satisfies its preconditions',
            observed={'exception':type(exc).__name__,'detail':str(exc)},
            rationale='Incomplete or malformed fixture evidence cannot qualify workspace preservation.',
            rationale_ref='CONTRACT.md#phase-sequence',evidence=[evidence_reference(args.run/'manifest.json')],
            recovery='Inspect the cited manifest and exception; retain the failed attempt.',retry_safety='A new run is required after a partially completed setup or probe.')])
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
